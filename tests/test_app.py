from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "app.py"


@pytest.mark.parametrize("page", ["Overview", "Platform Comparison", "Campaign Details", "Time Series", "Budget Planner", "Data & Methodology"])
def test_each_view_renders(page):
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.radio(key="view").set_value(page).run()
    assert not app.exception, [e.message for e in app.exception]
    if page == "Budget Planner":
        assert len(app.metric) == 3


def test_empty_filter_and_reset_restore_results():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.multiselect(key="channels").set_value([]).run()
    assert not app.exception
    assert any("No data for selected filters" in item.value for item in app.info)
    next(b for b in app.button if b.label == "Reset filters").click().run()
    assert len(app.multiselect(key="channels").value) == 4
    assert len(app.metric) == 7
    assert not app.exception


def test_investigate_preserves_filter_context():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.multiselect(key="channels").set_value(["Facebook"]).run()
    next(b for b in app.button if b.label == "Investigate").click().run()
    assert app.radio(key="view").value == "Campaign Details"
    assert app.multiselect(key="channels").value == ["Facebook"]
    assert not app.exception


def test_search_literal_regex_and_infeasible_plan():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.radio(key="view").set_value("Campaign Details").run()
    app.text_input(key="campaign_search").set_value("[").run()
    assert not app.exception
    assert any("No campaigns match" in item.value for item in app.info)
    app.radio(key="view").set_value("Budget Planner").run()
    app.number_input[0].set_value(1.0).run()
    assert not app.exception
    assert any("feasible range" in item.value for item in app.warning)


def test_overview_metrics_follow_channel_filters():
    from campaign_compass.analytics import facts, metrics
    from campaign_compass.data import load_directory
    full = facts(load_directory(APP.parent / "data"))
    selected = full.loc[full.channel.eq("Pinterest") & full.date.ge("2026-07-03")]
    expected = metrics(selected)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.multiselect(key="channels").set_value(["Pinterest"]).run()
    shown = {m.label: m.value for m in app.metric}
    assert shown["Clicks"] == f"{expected['clicks']:,.0f}"
    assert shown["Purchase conversions"] == f"{expected['purchases']:,.0f}"
    assert shown["Contribution ROI"] == f"{expected['contribution_roi']:.1%}"
    assert not app.exception


def test_mature_comparison_and_investigation_are_not_recent_empty_windows():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.checkbox(key='mature').set_value(True).run()
    assert not app.exception
    captions = ' '.join(item.value for item in app.caption)
    assert 'Jul 03, 2026–Aug 05, 2026 versus May 30, 2026–Jul 02, 2026 (34 calendar days each)' in captions
    assert '2026-07-09–2026-08-05 with 2026-06-11–2026-07-08' in captions
    assert '-63.6%' not in str(next(m for m in app.metric if m.label == 'Ad spend').delta)
    assert any(b.label == 'Investigate' for b in app.button)


def test_guided_presets_set_the_intended_filters_and_view():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    next(b for b in app.button if b.label == '1 · High ROAS, losing money').click().run()
    assert app.radio(key='view').value == 'Campaign Details'
    assert app.selectbox(key='campaign_pick').value == 'NC-02'
    assert app.checkbox(key='mature').value is True
    next(b for b in app.button if b.label == '2 · Delayed purchases').click().run()
    assert app.radio(key='view').value == 'Time Series'
    assert app.multiselect(key='channels').value == ['Pinterest']
    assert app.checkbox(key='mature').value is False
    next(b for b in app.button if b.label == '3 · Reallocate with constraints').click().run()
    assert app.radio(key='view').value == 'Budget Planner'
    assert len(app.multiselect(key='channels').value) == 4
    assert not app.exception


def test_saved_scenario_survives_navigation_and_checks_scope_and_budget():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.radio(key='view').set_value('Budget Planner').run()
    app.button(key='save_scenario_a').click().run()
    app.multiselect(key='locked').set_value(['NC-01']).run()
    assert any('B minus A, at B' in item.value for item in app.markdown)
    app.radio(key='view').set_value('Overview').run()
    app.radio(key='view').set_value('Budget Planner').run()
    assert any('B minus A, at B' in item.value for item in app.markdown)
    budget = app.number_input[0].value
    app.number_input[0].set_value(budget + 100).run()
    assert any('same total budget' in item.value for item in app.info)
    app.button(key='restore_scenario_budget').click().run()
    assert app.number_input[0].value == budget
    app.multiselect(key='channels').set_value(['Pinterest']).run()
    assert any('different data or filters' in item.value for item in app.info)
    assert not app.exception
