"""Snapshots and same-budget comparisons of fixed allocations under common assumptions."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pandas as pd

from .planner import response


def scope_key(context, fingerprint, inputs):
    filters = {k: context[k] for k in ["start", "end", "channels", "goals", "audiences", "mature"]}
    for k in ["channels", "goals", "audiences"]:
        filters[k] = sorted(filters[k])
    content = json.dumps(filters, sort_keys=True, default=str) + fingerprint
    content += inputs[["campaign_id", "baseline_spend", "baseline_before_ad", "observed_days"]].to_csv(index=False)
    return hashlib.sha256(content.encode()).hexdigest()


def snapshot(plan, settings, key):
    return dict(plan=plan.copy(deep=True), settings=deepcopy(settings), scope=key)


def compare(saved, plan, settings, key):
    if saved["scope"] != key:
        raise ValueError("Scenario A uses different data or filters. Restore its scope or save a new A.")
    if round(saved["settings"]["budget"], 2) != round(settings["budget"], 2):
        raise ValueError("Use the same total budget for A and B before comparing.")
    old = saved["plan"].set_index("campaign_id").loc[plan.campaign_id].reset_index()
    # Hold allocations fixed and evaluate both under B's current saturation assumption.
    a_before = response(old.proposed_spend, plan.baseline_spend, plan.baseline_before_ad, settings["saturation"])
    allocation = pd.DataFrame({"Campaign": plan.campaign_name, "Channel": plan.channel,
                               "A spend ($)": old.proposed_spend.to_numpy(), "B spend ($)": plan.proposed_spend,
                               "B minus A ($)": plan.proposed_spend.to_numpy() - old.proposed_spend.to_numpy()})
    rows = []
    for name, candidate, config, before in [("A · saved", old, saved["settings"], a_before),
                                            ("B · current", plan, settings, plan.proposed_before_ad)]:
        rows.append({"Scenario": name, "Budget ($)": round(config["budget"], 2),
                     "Maximum change (%)": config["flexibility"] * 100,
                     "Saturation assumption": config["saturation"],
                     "Locked campaigns": ", ".join(candidate.loc[candidate.locked, "campaign_name"]) or "None",
                     "Modeled contribution at B's saturation ($)": float(before.sum() - config["budget"])})
    return pd.DataFrame(rows), allocation
