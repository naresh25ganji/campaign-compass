import numpy as np
import pandas as pd
import pytest

from campaign_compass.analytics import SUM_COLUMNS, aggregate, cohort_curve, filter_facts, metrics
from campaign_compass.data import DataError, export_bundle, load_bundle, validate


def test_ledger_join_does_not_multiply_spend(dataset, full):
    assert len(full) == len(dataset.performance)
    assert full.spend.sum() == pytest.approx(dataset.performance.spend.sum())
    assert full.purchases.sum() == len(dataset.orders)
    expected_revenue = (dataset.orders.gross_revenue - dataset.orders.discount - dataset.orders.refund).sum()
    expected_cost = (dataset.orders.product_cost - dataset.orders.recovered_cost + dataset.orders.fulfillment_cost).sum()
    assert full.net_revenue.sum() == pytest.approx(expected_revenue)
    assert full.contribution.sum() == pytest.approx(expected_revenue - expected_cost - dataset.performance.spend.sum())


def test_rates_use_totals_not_average_of_rates():
    frame = pd.DataFrame(0.0, index=range(2), columns=SUM_COLUMNS)
    frame["sessions"] = [10, 1000]
    frame["purchases"] = [5, 10]
    frame["spend"] = [50, 500]
    result = metrics(frame)
    assert result["cvr"] == pytest.approx(15 / 1010)
    assert result["cpa"] == pytest.approx(550 / 15)
    assert np.isnan(result["ctr"])


def test_filters_and_empty_choices(full):
    filtered = filter_facts(full, "2026-08-01", "2026-08-31", ["Pinterest"], ["Sales"], ["New customers"])
    assert filtered.channel.eq("Pinterest").all()
    assert filtered.date.between("2026-08-01", "2026-08-31").all()
    assert aggregate(filtered, "channel").spend.sum() == pytest.approx(filtered.spend.sum())
    assert filter_facts(full, "2026-08-01", "2026-08-31", [], ["Sales"], ["New customers"]).empty


def test_zero_orders_keep_spend(dataset):
    no_orders = dataset.orders.iloc[:0].copy()
    from campaign_compass.analytics import facts
    frame = facts(validate(dataset.campaigns, dataset.performance, no_orders, dataset.manifest))
    assert frame.purchases.sum() == 0
    assert frame.spend.sum() == pytest.approx(dataset.performance.spend.sum())
    assert metrics(frame)["contribution"] == pytest.approx(-frame.spend.sum())
    assert np.isnan(metrics(frame)["cpa"])


def test_bundle_round_trip(dataset):
    restored = load_bundle(export_bundle(dataset))
    assert len(restored.orders) == len(dataset.orders)
    assert restored.performance.spend.sum() == pytest.approx(dataset.performance.spend.sum())


@pytest.mark.parametrize("failure", ["duplicate", "bad_spend", "bad_order", "future", "bad_counts", "bad_refund"])
def test_invalid_data_explains_failure(dataset, failure):
    c, p, o = dataset.campaigns.copy(), dataset.performance.copy(), dataset.orders.copy()
    if failure == "duplicate":
        p = pd.concat([p, p.iloc[:1]])
    elif failure == "bad_spend":
        p.loc[0, "spend"] = np.nan
    elif failure == "bad_order":
        o.loc[0, "campaign_id"] = "MISSING"
    elif failure == "future":
        p.loc[0, "date"] = pd.Timestamp("2027-01-01")
    elif failure == "bad_counts":
        p.loc[0, "clicks"] = p.loc[0, "impressions"] + 1
    else:
        o.loc[0, "refund"] = o.loc[0, "gross_revenue"] + 1
    with pytest.raises(DataError):
        validate(c, p, o, dataset.manifest)


def test_equal_age_cohorts_exclude_recent_sessions(dataset, full):
    curve = cohort_curve(dataset, full)
    pin = curve.loc[(curve.channel == "Pinterest") & (curve.day == 21)].iloc[0]
    eligible = full.loc[(full.channel == "Pinterest") & (full.cohort_age >= 21)]
    assert pin.sessions == eligible.sessions.sum()
    eligible_ids = set(map(tuple, eligible[["date", "campaign_id", "creative_id"]].to_numpy()))
    o = dataset.orders
    expected = sum((r.acquisition_date, r.campaign_id, r.creative_id) in eligible_ids
                   and (r.order_date - r.acquisition_date).days <= 21 for r in o.itertuples())
    assert pin.purchases == expected


def test_synthetic_economics_scenario(full):
    mature = full.loc[full.cohort_age >= 56]
    trap = metrics(mature.loc[mature.campaign_id == "NC-02"])
    healthy = metrics(mature.loc[mature.campaign_id == "NC-07"])
    assert trap["roas"] > 1
    assert trap["contribution"] < 0
    assert healthy["contribution"] > 0
