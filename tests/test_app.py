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
    assert len(app.metric) == 4
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
