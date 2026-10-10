import numpy as np
import pytest
from campaign_compass.planner import feasible_baseline, optimize, planning_inputs, response


def test_response_anchors_and_saturates(full):
    inputs = planning_inputs(full)
    base, value = inputs.baseline_spend, inputs.baseline_before_ad
    assert response(base, base, value) == pytest.approx(value)
    assert response(np.zeros(len(inputs)), base, value) == pytest.approx(np.zeros(len(inputs)))
    assert np.all(response(base * 2, base, value) < value * 2)


@pytest.mark.parametrize("budget_factor", [.9, 1.0, 1.1])
def test_budget_bounds_locks_and_total(full, budget_factor):
    inputs = planning_inputs(full)
    budget = round(inputs.baseline_spend.sum() * budget_factor, 2)
    locked = [inputs.campaign_id.iloc[0]]
    plan = optimize(inputs, budget, .35, 1.5, locked)
    assert plan.proposed_spend.sum() == pytest.approx(budget, abs=.00001)
    assert (plan.proposed_spend >= plan.lower_bound - .00001).all()
    assert (plan.proposed_spend <= plan.upper_bound + .00001).all()
    assert plan.loc[plan.locked, "proposed_spend"].iloc[0] == pytest.approx(round(inputs.baseline_spend.iloc[0], 2))


def test_optimal_plan_beats_feasible_equal_baseline(full):
    inputs = planning_inputs(full)
    budget = round(inputs.baseline_spend.sum(), 2)
    plan = optimize(inputs, budget)
    assert plan.proposed_contribution.sum() >= inputs.baseline_before_ad.sum() - inputs.baseline_spend.sum() - .01


def test_infeasible_budget_and_empty_calibration(full):
    inputs = planning_inputs(full)
    with pytest.raises(ValueError, match="feasible"):
        optimize(inputs, 1)
    with pytest.raises(ValueError, match="No eligible"):
        optimize(inputs.iloc[:0], 100)
    assert planning_inputs(full.loc[full.cohort_age < 56]).empty


def test_all_locked_can_preserve_total(full):
    inputs = planning_inputs(full)
    total = float(inputs.baseline_spend.round(2).sum())
    plan = optimize(inputs, total, locked=inputs.campaign_id.tolist())
    assert plan.proposed_spend.sum() == pytest.approx(total)


def test_zero_flexibility_is_a_valid_unchanged_plan(full):
    inputs = planning_inputs(full)
    total = float(inputs.baseline_spend.round(2).sum())
    plan = optimize(inputs, total, flexibility=0)
    assert plan.proposed_spend.to_numpy() == pytest.approx(inputs.baseline_spend.round(2).to_numpy())


@pytest.mark.parametrize("budget_factor", [.8, 1., 1.2])
def test_constraint_matched_baseline_preserves_locks_bounds_and_total(full, budget_factor):
    inputs = planning_inputs(full)
    budget = round(inputs.baseline_spend.sum() * budget_factor, 2)
    plan = optimize(inputs, budget, locked=[inputs.campaign_id.iloc[0]])
    baseline = feasible_baseline(plan, budget)
    assert baseline.comparator_spend.sum() == pytest.approx(budget, abs=.00001)
    assert (baseline.comparator_spend >= baseline.lower_bound - .00001).all()
    assert (baseline.comparator_spend <= baseline.upper_bound + .00001).all()
    assert baseline.loc[baseline.locked, 'comparator_spend'].to_numpy() == pytest.approx(plan.loc[plan.locked, 'proposed_spend'].to_numpy())
    assert plan.proposed_contribution.sum() >= baseline.comparator_contribution.sum() - .02


def test_all_locked_baseline_and_zero_flexibility(full):
    inputs = planning_inputs(full)
    total = float(inputs.baseline_spend.round(2).sum())
    for plan in [optimize(inputs, total, locked=inputs.campaign_id.tolist()), optimize(inputs, total, flexibility=0)]:
        baseline = feasible_baseline(plan, total)
        assert baseline.comparator_spend.to_numpy() == pytest.approx(inputs.baseline_spend.round(2).to_numpy())
