"""Strict dataset loading. Invalid rows are explained, never silently zero-filled."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
import pandas as pd


class DataError(ValueError):
    pass


@dataclass
class Dataset:
    campaigns: pd.DataFrame
    performance: pd.DataFrame
    orders: pd.DataFrame
    manifest: dict


REQUIRED = {
    "campaigns": ["campaign_id", "campaign_name", "channel", "goal", "audience", "daily_budget", "target_cpa"],
    "performance": ["date", "campaign_id", "creative_id", "spend", "impressions", "clicks", "sessions"],
    "orders": ["order_id", "campaign_id", "creative_id", "acquisition_date", "order_date", "refund_date",
               "gross_revenue", "discount", "refund", "product_cost", "recovered_cost", "fulfillment_cost", "is_new_customer"],
}
NUMERIC = {"campaigns": ["daily_budget", "target_cpa"],
           "performance": ["spend", "impressions", "clicks", "sessions"],
           "orders": ["gross_revenue", "discount", "refund", "product_cost", "recovered_cost", "fulfillment_cost"]}


def validate(campaigns: pd.DataFrame, performance: pd.DataFrame, orders: pd.DataFrame, manifest: dict) -> Dataset:
    frames = {"campaigns": campaigns.copy(), "performance": performance.copy(), "orders": orders.copy()}
    if manifest.get("schema_version") != 1 or manifest.get("currency") != "USD":
        raise DataError("Manifest requires schema_version 1 and currency USD.")
    if not isinstance(manifest.get("synthetic"), bool):
        raise DataError("Manifest must declare synthetic as true or false.")
    as_of = pd.to_datetime(manifest.get("as_of"), errors="coerce")
    if pd.isna(as_of):
        raise DataError("Manifest requires a valid as_of date.")
    for name, df in frames.items():
        missing = sorted(set(REQUIRED[name]) - set(df.columns))
        if missing:
            raise DataError(f"{name}.csv is missing: {', '.join(missing)}")
        if name != "orders" and df.empty:
            raise DataError(f"{name}.csv cannot be empty.")
        for col in NUMERIC[name]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if (~np.isfinite(df[col]) | (df[col] < 0)).any():
                raise DataError(f"{name}.{col} requires finite nonnegative numbers; no rows were discarded.")
        for col in [c for c in REQUIRED[name] if c.endswith("_id") or c in ["channel", "goal", "audience", "campaign_name"]]:
            if df[col].isna().any() or df[col].astype(str).str.strip().eq("").any():
                raise DataError(f"{name}.{col} has missing identifiers or labels.")
        for col in [c for c in REQUIRED[name] if c == "date" or c.endswith("_date")]:
            raw = df[col]
            parsed = pd.to_datetime(raw, errors="coerce")
            allow_empty = col == "refund_date"
            present = raw.notna() & raw.astype(str).str.strip().ne("")
            if (parsed.isna() & (present if allow_empty else True)).any():
                raise DataError(f"{name}.{col} has an invalid date.")
            df[col] = parsed.dt.normalize()
            if (df[col] > as_of).any():
                raise DataError(f"{name}.{col} contains events after the as_of date.")
    c, p, o = frames["campaigns"], frames["performance"], frames["orders"]
    if c.campaign_id.duplicated().any() or o.order_id.duplicated().any():
        raise DataError("Campaign and order IDs must be unique in their source tables.")
    if p.duplicated(["date", "campaign_id", "creative_id"]).any():
        raise DataError("Duplicate daily campaign/creative rows would double-count spend.")
    for name, df in [("performance", p), ("orders", o)]:
        if not df.campaign_id.isin(c.campaign_id).all():
            raise DataError(f"{name} has campaign IDs absent from campaigns.csv.")
    for col in ["impressions", "clicks", "sessions"]:
        if (p[col] % 1 != 0).any():
            raise DataError(f"performance.{col} must contain integer counts.")
    if ((p.clicks > p.impressions) | (p.sessions > p.clicks)).any():
        raise DataError("Sessions must not exceed clicks; clicks must not exceed impressions.")
    truth = o.is_new_customer.astype(str).str.lower()
    if not truth.isin(["true", "false"]).all():
        raise DataError("orders.is_new_customer must be true or false.")
    o["is_new_customer"] = truth.eq("true")
    if ((o.order_date < o.acquisition_date) | (o.refund_date < o.order_date)).any():
        raise DataError("Order and refund events must follow acquisition chronologically.")
    if ((o.discount > o.gross_revenue) | (o.refund > o.gross_revenue - o.discount + .001)
        | (o.recovered_cost > o.product_cost)).any():
        raise DataError("Discounts, refunds, or recovered product costs exceed their source amounts.")
    if ((o.refund.gt(0) != o.refund_date.notna()) | (o.recovered_cost.gt(0) & o.refund.eq(0))).any():
        raise DataError("Refund events and recovered costs need matching refund amounts/dates.")
    keys = p.set_index(["date", "campaign_id", "creative_id"]).index
    order_keys = pd.MultiIndex.from_frame(o[["acquisition_date", "campaign_id", "creative_id"]])
    if not order_keys.isin(keys).all():
        raise DataError("An order's acquisition date/campaign/creative is absent from performance.csv.")
    observed = o.groupby(["acquisition_date", "campaign_id", "creative_id"]).size()
    capacity = p.set_index(["date", "campaign_id", "creative_id"]).sessions
    if (observed > capacity.reindex(observed.index)).any():
        raise DataError("Purchases exceed sessions for a daily creative cohort.")
    return Dataset(c, p, o, {**manifest, "as_of": as_of.date().isoformat()})


def load_directory(path: Path) -> Dataset:
    return validate(*(pd.read_csv(path / f"{name}.csv") for name in REQUIRED),
                    json.loads((path / "manifest.json").read_text()))


def load_bundle(content: bytes) -> Dataset:
    try:
        with ZipFile(BytesIO(content)) as archive:
            if len(archive.infolist()) > 10 or sum(f.file_size for f in archive.infolist()) > 30_000_000:
                raise DataError("Dataset ZIP exceeds the 30 MB expanded-size or 10-file limit.")
            names = [f"{name}.csv" for name in REQUIRED] + ["manifest.json"]
            if not set(names).issubset(archive.namelist()):
                raise DataError("ZIP must contain campaigns.csv, performance.csv, orders.csv, and manifest.json at its root.")
            return validate(*(pd.read_csv(BytesIO(archive.read(f"{name}.csv"))) for name in REQUIRED),
                            json.loads(archive.read("manifest.json")))
    except DataError:
        raise
    except Exception as exc:
        raise DataError(f"Could not read dataset ZIP: {exc}") from exc


def export_bundle(dataset: Dataset) -> bytes:
    buf = BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as archive:
        for name in REQUIRED:
            archive.writestr(f"{name}.csv", getattr(dataset, name).to_csv(index=False))
        archive.writestr("manifest.json", json.dumps(dataset.manifest, indent=2))
    return buf.getvalue()
