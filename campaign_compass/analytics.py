"""All views share the same acquisition-cohort facts and metric definitions."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import Dataset

SUM_COLUMNS = ["spend", "impressions", "clicks", "sessions", "purchases", "new_customers",
               "gross_revenue", "discount", "refund", "net_revenue", "net_product_cost",
               "fulfillment_cost", "before_ad", "contribution", "returned_orders"]


def facts(dataset: Dataset) -> pd.DataFrame:
    o = dataset.orders.copy()
    o["purchases"] = 1
    o["new_customers"] = o.is_new_customer.astype(int)
    o["returned_orders"] = o.refund.gt(0).astype(int)
    o["net_revenue"] = o.gross_revenue - o.discount - o.refund
    o["net_product_cost"] = o.product_cost - o.recovered_cost
    o["before_ad"] = o.net_revenue - o.net_product_cost - o.fulfillment_cost
    fields = [c for c in SUM_COLUMNS if c not in ["spend", "impressions", "clicks", "sessions", "contribution"]]
    totals = o.groupby(["acquisition_date", "campaign_id", "creative_id"])[fields].sum().reset_index()
    totals = totals.rename(columns={"acquisition_date": "date"})
    df = dataset.performance.merge(totals, on=["date", "campaign_id", "creative_id"], how="left", validate="one_to_one")
    df[fields] = df[fields].fillna(0)
    df = df.merge(dataset.campaigns, on="campaign_id", validate="many_to_one")
    df["contribution"] = df.before_ad - df.spend
    df["cohort_age"] = (pd.Timestamp(dataset.manifest["as_of"]) - df.date).dt.days
    return df


def filter_facts(df: pd.DataFrame, start, end, channels, goals, audiences, mature_only=False) -> pd.DataFrame:
    mask = df.date.between(pd.Timestamp(start), pd.Timestamp(end))
    for column, selections in [("channel", channels), ("goal", goals), ("audience", audiences)]:
        mask &= df[column].isin(selections)  # Empty selection intentionally means no results.
    if mature_only:
        mask &= df.cohort_age >= 56  # Up to 21 purchase-lag days + 35 return-lag days in the demo.
    return df.loc[mask].copy()


def ratio(numerator, denominator):
    return numerator / denominator if denominator > 0 else np.nan


def metrics(df: pd.DataFrame) -> dict:
    result = {col: float(df[col].sum()) for col in SUM_COLUMNS}
    result.update(ctr=ratio(result["clicks"], result["impressions"]),
                  cpc=ratio(result["spend"], result["clicks"]),
                  cvr=ratio(result["purchases"], result["sessions"]),
                  cpa=ratio(result["spend"], result["purchases"]),
                  cac=ratio(result["spend"], result["new_customers"]),
                  roas=ratio(result["net_revenue"], result["spend"]),
                  contribution_roi=ratio(result["contribution"], result["spend"]),
                  refund_rate=ratio(result["returned_orders"], result["purchases"]),
                  aov=ratio(result["net_revenue"], result["purchases"]))
    return result


def aggregate(df: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    keys = [by] if isinstance(by, str) else by
    if df.empty:
        return pd.DataFrame(columns=keys + list(metrics(df)))
    rows = []
    for group, part in df.groupby(keys, observed=True, sort=True):
        values = group if isinstance(group, tuple) else (group,)
        rows.append({**dict(zip(keys, values)), **metrics(part)})
    return pd.DataFrame(rows)


def previous_period(all_facts, start, end, channels, goals, audiences, mature_only=False):
    days = (pd.Timestamp(end) - pd.Timestamp(start)).days + 1
    prior_end = pd.Timestamp(start) - pd.Timedelta(days=1)
    prior_start = prior_end - pd.Timedelta(days=days - 1)
    return filter_facts(all_facts, prior_start, prior_end, channels, goals, audiences, mature_only), prior_start, prior_end


def investigations(current: pd.DataFrame, previous: pd.DataFrame) -> list[dict]:
    """Evidence rules flag hypotheses. They never infer causes from correlations."""
    findings = []
    for cid, part in current.groupby("campaign_id"):
        now = metrics(part)
        before = metrics(previous.loc[previous.campaign_id == cid])
        name = part.campaign_name.iloc[0]
        common = dict(campaign_id=cid, campaign_name=name)
        if part.goal.iloc[0] == "Sales" and now["contribution"] < 0 and now["purchases"] >= 10:
            findings.append({**common, "title": "Revenue is not covering costs", "kind": "Economics",
                             "evidence": f"${now['net_revenue']:,.0f} net revenue, ${now['contribution']:,.0f} contribution after ads; {now['refund_rate']:.1%} of orders refunded.",
                             "action": "Review product margins, discounts, and returns before adding budget.",
                             "priority": abs(now["contribution"])})
        if now["sessions"] >= 300 and before["purchases"] >= 10 and before["cvr"] > 0:
            change = now["cvr"] / before["cvr"] - 1
            if change < -.22:
                recent_share = part.loc[part.cohort_age < 21, "spend"].sum() / now["spend"] if now["spend"] else 0
                findings.append({**common, "title": "Purchase conversion rate declined", "kind": "Conversion",
                                 "evidence": f"Session CVR {before['cvr']:.1%} → {now['cvr']:.1%}; {recent_share:.0%} of selected spend has less than 21 days of observation.",
                                 "action": "Compare equal-age cohorts, then inspect landing-page or traffic changes. This is a hypothesis, not a causal finding.",
                                 "priority": now["spend"] * abs(change)})
        if before["ctr"] > 0 and now["impressions"] >= 5000 and now["ctr"] < before["ctr"] * .78:
            findings.append({**common, "title": "Ad engagement declined", "kind": "Creative",
                             "evidence": f"CTR {before['ctr']:.2%} → {now['ctr']:.2%} against the preceding period.",
                             "action": "Compare creatives and audience mix. Test a refresh rather than assuming fatigue is the cause.",
                             "priority": now["spend"] * .25})
    return sorted(findings, key=lambda f: f["priority"], reverse=True)


def cohort_curve(dataset: Dataset, selected: pd.DataFrame) -> pd.DataFrame:
    """Equal-age purchase curves: only cohorts observed for the full horizon enter."""
    keys = selected[["date", "campaign_id", "creative_id"]].rename(columns={"date": "acquisition_date"})
    orders = dataset.orders.merge(keys, on=["acquisition_date", "campaign_id", "creative_id"], validate="many_to_one")
    orders["lag"] = (orders.order_date - orders.acquisition_date).dt.days
    rows = []
    for horizon in [0, 1, 3, 7, 14, 21]:
        eligible = selected.loc[selected.cohort_age >= horizon]
        eligible_keys = eligible[["date", "campaign_id", "creative_id"]].rename(columns={"date": "acquisition_date"})
        observed = orders.merge(eligible_keys, on=["acquisition_date", "campaign_id", "creative_id"], validate="many_to_one")
        for channel, group in eligible.groupby("channel"):
            ids = group.campaign_id.unique()
            count = len(observed.loc[observed.campaign_id.isin(ids) & observed.lag.le(horizon)])
            rows.append(dict(day=horizon, channel=channel, purchases=count,
                             sessions=int(group.sessions.sum()), cvr=ratio(count, group.sessions.sum())))
    return pd.DataFrame(rows)
