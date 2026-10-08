"""Constrained allocation for a disclosed assumed concave response model.

Historical outcomes anchor the curve. Saturation is an editable assumption,
not a causal estimate. The objective is contribution, with fixed total spend.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .analytics import aggregate


def planning_inputs(selected: pd.DataFrame, days: int = 7) -> pd.DataFrame:
    eligible = selected.loc[(selected.goal == "Sales") & (selected.cohort_age >= 56)]
    grouped = aggregate(eligible, ["campaign_id", "campaign_name", "channel"])
    if grouped.empty:
        return pd.DataFrame()
    active_days = eligible.groupby("campaign_id").date.nunique()
    grouped["observed_days"] = grouped.campaign_id.map(active_days)
    grouped = grouped.loc[(grouped.purchases >= 20) & (grouped.observed_days >= 7) & (grouped.spend > 0) & (grouped.before_ad > 0)].copy()
    grouped["baseline_spend"] = grouped.spend / grouped.observed_days * days
    grouped["baseline_before_ad"] = grouped.before_ad / grouped.observed_days * days
    return grouped.reset_index(drop=True)


def response(spend, baseline_spend, baseline_before_ad, saturation: float = 1.5):
    scale = np.asarray(baseline_spend, dtype=float) * saturation
    return np.asarray(baseline_before_ad) * (-np.expm1(-np.asarray(spend) / scale)) / (-np.expm1(-np.asarray(baseline_spend) / scale))


def optimize(inputs: pd.DataFrame, budget: float, flexibility: float = .35,
             saturation: float = 1.5, locked: list[str] | None = None) -> pd.DataFrame:
    if inputs.empty:
        raise ValueError("No eligible sales campaigns with mature outcomes and sufficient observations.")
    if not 0 <= flexibility <= 1 or saturation <= 0 or not np.isfinite(budget) or budget <= 0:
        raise ValueError("Budget and saturation must be positive; flexibility must be between 0 and 1.")
    out = inputs.copy()
    base = out.baseline_spend.to_numpy(float)
    value = out.baseline_before_ad.to_numpy(float)
    if not np.all(np.isfinite(base) & (base > 0) & np.isfinite(value) & (value > 0)):
        raise ValueError("Every baseline must have positive, finite spend and before-ad contribution.")
    reference = np.round(base, 2)
    lower = np.ceil(reference * (1 - flexibility) * 100 - 1e-8) / 100
    upper = np.floor(reference * (1 + flexibility) * 100 + 1e-8) / 100
    is_locked = out.campaign_id.isin(locked or []).to_numpy()
    lower[is_locked] = upper[is_locked] = np.round(base[is_locked], 2)
    budget = round(budget, 2)
    if budget < lower.sum() - .001 or budget > upper.sum() + .001:
        raise ValueError(f"Budget is outside the feasible range ${lower.sum():,.2f}–${upper.sum():,.2f}. Increase flexibility or unlock campaigns.")
    scale = base * saturation
    ceiling = value / (-np.expm1(-base / scale))
    marginal = ceiling / scale
    lo, hi = 0.0, float(marginal.max()) * 10
    for _ in range(150):
        multiplier = (lo + hi) / 2
        allocation = np.clip(scale * np.log(marginal / max(multiplier, 1e-15)), lower, upper)
        if allocation.sum() > budget:
            lo = multiplier
        else:
            hi = multiplier
    allocation = np.round(allocation, 2)
    # Reconcile cents without violating any bound or lock.
    cents = int(round((budget - allocation.sum()) * 100))
    while cents:
        direction = 1 if cents > 0 else -1
        candidates = np.where((allocation + direction * .01 >= lower - 1e-8)
                              & (allocation + direction * .01 <= upper + 1e-8) & ~is_locked)[0]
        if not len(candidates):
            raise ValueError("Cannot reconcile budget to cents within the selected constraints.")
        derivatives = marginal[candidates] * np.exp(-allocation[candidates] / scale[candidates])
        index = candidates[np.argmax(derivatives) if direction > 0 else np.argmin(derivatives)]
        allocation[index] += direction * .01
        cents -= direction
    out["lower_bound"], out["upper_bound"] = lower, upper
    out["proposed_spend"] = np.round(allocation, 2)
    out["change"] = out.proposed_spend - base
    out["current_contribution"] = value - base
    out["proposed_before_ad"] = response(allocation, base, value, saturation)
    out["proposed_contribution"] = out.proposed_before_ad - allocation
    out["locked"] = is_locked
    return out
