import pytest

from campaign_compass.planner import optimize, planning_inputs, response
from campaign_compass.scenarios import compare, snapshot


def test_saved_snapshot_is_independent_and_common_assumption_is_used(full):
    inputs = planning_inputs(full)
    settings = dict(budget=round(inputs.baseline_spend.sum(), 2), flexibility=.35, saturation=1.5)
    plan = optimize(inputs, **settings)
    saved = snapshot(plan, settings, 'same-data')
    settings['saturation'] = 2.5
    # Keep the allocation fixed while changing the response assumption.
    plan['proposed_before_ad'] = response(plan.proposed_spend, plan.baseline_spend, plan.baseline_before_ad, 2.5)
    plan['proposed_contribution'] = plan.proposed_before_ad - plan.proposed_spend
    assert saved['settings']['saturation'] == 1.5
    assert not plan.proposed_before_ad.equals(saved['plan'].proposed_before_ad)
    summary, allocations = compare(saved, plan, settings, 'same-data')
    result = "Modeled contribution at B's saturation ($)"
    assert summary[result].iloc[0] == pytest.approx(summary[result].iloc[1])
    assert allocations['B minus A ($)'].abs().max() == 0


def test_changed_scope_and_budget_cannot_compare(full):
    inputs = planning_inputs(full)
    settings = dict(budget=round(inputs.baseline_spend.sum(), 2), flexibility=.35, saturation=1.5)
    plan = optimize(inputs, **settings)
    saved = snapshot(plan, settings, 'old')
    with pytest.raises(ValueError, match='different data or filters'):
        compare(saved, plan, settings, 'new')
    with pytest.raises(ValueError, match='same total budget'):
        compare(saved, plan, dict(settings, budget=settings['budget']+100), 'old')
