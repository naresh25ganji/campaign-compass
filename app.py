from __future__ import annotations

import hashlib
import html
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from campaign_compass.analytics import (aggregate, cohort_curve, facts, filter_facts,
                                        investigations, metrics, previous_period)
from campaign_compass.charts import CHANNEL_COLORS, finish, line, waterfall
from campaign_compass.data import DataError, export_bundle, load_bundle, load_directory
from campaign_compass.planner import optimize, planning_inputs, response

ROOT = Path(__file__).parent
st.set_page_config(page_title="Campaign Compass", page_icon="🧭", layout="wide")
st.markdown("""<style>
.block-container {padding-top:4rem; padding-bottom:3rem; max-width:1500px;}
h1 {letter-spacing:-1.4px; font-weight:750 !important;}
h2,h3 {letter-spacing:-.4px;}
[data-testid="stMetric"] {background:#fff; border:1px solid #E2E8F0; border-radius:12px; padding:18px 20px;}
[data-testid="stMetricLabel"] {color:#607084;}
[data-testid="stMetricValue"] {font-size:1.9rem;}
[data-testid="stSidebar"] {border-right:1px solid #E2E8F0;}
.eyebrow {font-size:11px; letter-spacing:2px; color:#147D71; font-weight:700; margin:0 0 8px;}
.scope {font-size:13px; color:#63758A; margin-bottom:20px;}
.hero-copy {font-size:17px; color:#63758A; margin-top:-10px; margin-bottom:24px;}
</style>""", unsafe_allow_html=True)


@st.cache_data
def default_dataset():
    return load_directory(ROOT / "data")


@st.cache_data
def uploaded_dataset(content: bytes):
    return load_bundle(content)


@st.cache_data
def prepared(dataset):
    return facts(dataset)


def money(value):
    return "—" if pd.isna(value) else f"{'−' if value < 0 else ''}${abs(value):,.0f}"


def number(value):
    return "—" if pd.isna(value) else f"{value:,.0f}"


def pct(value):
    return "—" if pd.isna(value) else f"{value:.1%}"


def chart(fig, key, description):
    st.plotly_chart(fig, width="stretch", key=key, config={"displayModeBar": False}, alt=description)


def reset_filters():
    for key in ["date_start", "date_end", "channels", "goals", "audiences", "mature", "campaign_pick", "locked"]:
        st.session_state.pop(key, None)


def go_campaign(cid):
    st.session_state["view"] = "Campaign Details"
    st.session_state["campaign_pick"] = cid
    st.session_state["campaign_search"] = ""


def csv_download(df, label, filename, key):
    # Escape spreadsheet formula prefixes in string values on export.
    export = df.copy()
    for col in export.select_dtypes(include=["object", "string"]):
        export[col] = export[col].map(lambda v: "'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v)
    st.download_button(label, export.to_csv(index=False).encode(), filename, "text/csv", key=key)


def show_table(df, keys):
    labels = {"campaign_name": "Campaign", "creative_id": "Creative", "channel": "Channel", "goal": "Goal", "audience": "Audience",
              "spend": "Ad spend ($)", "purchases": "Purchases", "net_revenue": "Net revenue ($)",
              "contribution": "Contribution ($)", "cpa": "CPA ($)", "roas": "Net ROAS (×)",
              "cvr": "Session CVR (%)", "refund_rate": "Refunded orders (%)", "ctr": "CTR (%)",
              "cpc": "CPC ($)", "impressions": "Impressions", "new_customers": "New customers"}
    view = df[keys].copy()
    for col in ["cvr", "refund_rate", "ctr"]:
        if col in view:
            view[col] *= 100
    configs = {labels.get(col, col): st.column_config.NumberColumn(format="%.2f")
               for col in keys if col in ["spend", "net_revenue", "contribution", "cpa", "roas", "cvr", "refund_rate", "ctr", "cpc"]}
    st.dataframe(view.rename(columns=labels), hide_index=True, width="stretch", column_config=configs)


def overview(selected, previous, full, dataset, context):
    st.title("Every dollar has a destination.")
    st.markdown('<p class="hero-copy">Follow campaign revenue through costs, find what needs attention, and plan your next move.</p>', unsafe_allow_html=True)
    m, prior = metrics(selected), metrics(previous)
    previous_complete = context["prior_complete"]
    cards = [("Ad spend", "spend", money), ("Net revenue", "net_revenue", money),
             ("Contribution after ads", "contribution", money), ("Net ROAS", "roas", lambda x: "—" if pd.isna(x) else f"{x:.2f}×")]
    for column, (label, key, formatter) in zip(st.columns(4), cards):
        delta = None
        if previous_complete and np.isfinite(prior[key]) and prior[key] != 0:
            delta = f"{(m[key] - prior[key]) / abs(prior[key]):+.1%} vs previous period"
        column.metric(label, formatter(m[key]), delta, delta_color="off" if key == "spend" else "normal")
    st.caption("Net ROAS = net attributed revenue ÷ spend. Contribution excludes overhead and is not a measure of causal advertising lift.")
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Where revenue goes")
        chart(waterfall(m), "overview_waterfall", "Revenue waterfall subtracting discounts, refunds, product costs, fulfillment, and advertising.")
    with right:
        st.subheader("Revenue and contribution")
        daily = aggregate(selected, "date")
        daily["week"] = daily.date.dt.to_period("W").dt.start_time
        daily = daily.groupby("week")[["net_revenue", "contribution"]].mean().reset_index().rename(columns={"week": "date"})
        daily = daily.melt("date", var_name="Measure", value_name="USD")
        daily["Measure"] = daily.Measure.map({"net_revenue": "Net revenue", "contribution": "Contribution"})
        chart(finish(px.line(daily, x="date", y="USD", color="Measure", labels={"date": "Week starting", "USD": "USD per acquisition day"}), height=360, money=True),
              "overview_trend", "Weekly average daily net revenue and contribution after advertising, in dollars per acquisition day.")
        st.caption("Weekly averages per observed acquisition day keep partial weeks comparable. Recent cohorts can still develop.")
    st.subheader("Investigate next")
    recent_start = max(pd.Timestamp(context["start"]), pd.Timestamp(context["end"]) - pd.Timedelta(days=27))
    recent = selected.loc[selected.date >= recent_start]
    prior_recent, ps, pe = previous_period(full, recent_start, context["end"], context["channels"], context["goals"], context["audiences"], context["mature"])
    st.caption(f"Evidence compares {recent_start:%b %d}–{pd.Timestamp(context['end']):%b %d} with {ps:%b %d}–{pe:%b %d}, using the same audience, channel, and goal filters. Rules flag hypotheses, not statistical significance.")
    findings = investigations(recent, prior_recent)
    if not findings:
        st.info("No campaign meets the investigation rules for this selection. Explore campaign details or broaden the period.")
    for finding in findings[:3]:
        with st.container(border=True):
            a, b = st.columns([5, 1])
            with a:
                st.markdown(f"**{finding['campaign_name']} · {finding['title']}**")
                st.write(finding["evidence"].replace("$", r"\$"))
                st.caption(finding["action"])
            b.button("Investigate", key=f"investigate_{finding['campaign_id']}_{finding['kind']}",
                     on_click=go_campaign, args=(finding["campaign_id"],), width="stretch")
    if selected.cohort_age.lt(56).any():
        st.info("Some acquisition cohorts are still developing. Purchases can arrive up to day 21 and returns up to 35 days after purchase in the demo. Use fully observed cohorts for settled economics.")


def platforms(selected):
    st.title("Compare channels on equal terms.")
    st.caption("Use the goal filter to compare similar objectives. Awareness campaigns are not ranked as acquisition failures.")
    grouped = aggregate(selected, "channel")
    metric = st.selectbox("Compare by", ["Contribution after ads", "Net ROAS", "CPA", "CTR"], key="platform_metric")
    field, label = {"Contribution after ads": ("contribution", "Contribution ($)"), "Net ROAS": ("roas", "Net ROAS (×)"),
                    "CPA": ("cpa", "CPA ($)"), "CTR": ("ctr", "CTR (%)")}[metric]
    plotting = grouped.copy()
    if field == "ctr":
        plotting[field] *= 100
    a, b = st.columns(2)
    with a:
        chart(finish(px.bar(plotting, x="channel", y=field, color="channel", color_discrete_map=CHANNEL_COLORS,
                            labels={"channel": "", field: label}), money=field in ["contribution", "cpa"]), "platform_rank", f"Channels compared by {label}.")
    with b:
        chart(finish(px.scatter(grouped, x="spend", y="contribution", color="channel", size="net_revenue",
                                color_discrete_map=CHANNEL_COLORS, hover_name="channel",
                                labels={"spend": "Ad spend ($)", "contribution": "Contribution ($)", "net_revenue": "Net revenue ($)"}), money=True),
              "platform_scatter", "Channel contribution versus ad spend; bubble size represents net revenue.")
    st.subheader("Channel economics")
    show_table(grouped, ["channel", "spend", "purchases", "net_revenue", "contribution", "roas", "cpa", "cvr", "refund_rate"])
    csv_download(grouped, "Export channel metrics", "channel-metrics.csv", "channel_export")


def campaigns(selected, previous):
    st.title("Follow the evidence.")
    grouped = aggregate(selected, ["campaign_id", "campaign_name", "channel", "goal", "audience"])
    search = st.text_input("Search campaigns", placeholder="Campaign name or ID", key="campaign_search")
    if search:
        grouped = grouped.loc[grouped.campaign_name.str.contains(search, case=False, regex=False)
                              | grouped.campaign_id.str.contains(search, case=False, regex=False)]
    show_table(grouped, ["campaign_name", "channel", "goal", "spend", "purchases", "roas", "contribution", "cpa"])
    csv_download(grouped, "Export campaign metrics", "campaign-metrics.csv", "campaign_export")
    if grouped.empty:
        st.info("No campaigns match that search.")
        return
    options = grouped.campaign_id.tolist()
    if st.session_state.get("campaign_pick") not in options:
        st.session_state["campaign_pick"] = options[0]
    labels = grouped.set_index("campaign_id").campaign_name.to_dict()
    cid = st.selectbox("Investigate a campaign", options, format_func=lambda v: labels[v], key="campaign_pick")
    part = selected.loc[selected.campaign_id == cid]
    earlier = previous.loc[previous.campaign_id == cid]
    m, old = metrics(part), metrics(earlier)
    st.subheader(labels[cid])
    for col, label, field, formatter in zip(st.columns(4), ["CTR", "Cost per click", "Session CVR", "Refunded orders"],
                                          ["ctr", "cpc", "cvr", "refund_rate"], [pct, lambda x: "—" if pd.isna(x) else f"${x:.2f}", pct, pct]):
        col.metric(label, formatter(m[field]), delta_color="off")
    with st.expander("Compare the drivers with the preceding period", expanded=True):
        drivers = pd.DataFrame([{"Driver": label, "Previous": formatter(old[field]), "Selected": formatter(m[field])}
                                for label, field, formatter in [("Cost per click", "cpc", lambda x: "—" if pd.isna(x) else f"${x:.2f}"),
                                                               ("Session conversion rate", "cvr", pct), ("Net revenue per order", "aov", money),
                                                               ("Refunded order rate", "refund_rate", pct)]])
        st.dataframe(drivers, hide_index=True, width="stretch")
        st.caption("Changes describe observed outcomes. Traffic mix, seasonality, conversion delay, and other changes may explain them.")
    a, b = st.columns(2)
    with a:
        st.subheader("Contribution breakdown")
        chart(waterfall(m), "campaign_waterfall", "Selected campaign's revenue and cost breakdown.")
    with b:
        st.subheader("Creative engagement")
        creative = part.copy()
        creative["week"] = creative.date.dt.to_period("W").dt.start_time
        weekly = aggregate(creative, ["week", "creative_id"])
        weekly["ctr_percent"] = weekly.ctr * 100
        chart(line(weekly, "week", "ctr_percent", "CTR (%)", "creative_id"), "creative_ctr", "Weekly click-through rates by creative.")
    st.subheader("Creative economics")
    creative_totals = aggregate(part, "creative_id")
    show_table(creative_totals, ["creative_id", "spend", "purchases", "net_revenue", "contribution", "cpa"])


def trends(selected, dataset):
    st.title("Give outcomes time to develop.")
    mode = st.selectbox("Trend metric", ["Contribution", "Spend", "Purchases", "Session CVR"], key="trend_metric")
    field, label = {"Contribution": ("contribution", "Contribution ($)"), "Spend": ("spend", "Spend ($)"),
                    "Purchases": ("purchases", "Purchases"), "Session CVR": ("cvr", "Session CVR (%)")}[mode]
    period = st.radio("Group by", ["Day", "Week"], horizontal=True, key="trend_group")
    working = selected.copy()
    working["period"] = working.date if period == "Day" else working.date.dt.to_period("W").dt.start_time
    grouped = aggregate(working, ["period", "channel"])
    if field == "cvr":
        grouped[field] *= 100
    chart(line(grouped, "period", field, label, "channel", field in ["spend", "contribution"]), "trend_main", f"{label} by channel and time period.")
    st.caption("Dates represent acquisition cohorts. Purchases and returns observed by the dataset's as-of date are credited to the acquisition date, not the transaction date.")
    st.subheader("Compare purchase outcomes at equal ages")
    st.write("Each point includes only cohorts observed for at least that many days. A newly acquired cohort cannot enter the day-21 calculation.")
    curve = cohort_curve(dataset, selected)
    if curve.empty:
        st.info("No eligible cohorts for this selection.")
    else:
        curve["cvr_percent"] = curve.cvr * 100
        chart(line(curve, "day", "cvr_percent", "Observed session CVR (%)", "channel"), "cohort_curve", "Observed purchase conversion rate at day 0, 1, 3, 7, 14, and 21 by channel.")
        st.caption("The population can change between points as newer cohorts become ineligible. These curves show purchase delay, not lifetime value or refund-adjusted profit.")
        with st.expander("See cohort denominators"):
            st.dataframe(curve[["day", "channel", "sessions", "purchases", "cvr_percent"]], hide_index=True, width="stretch")


def planner(selected):
    st.title("Plan the next seven days.")
    st.write("Explore a budget allocation using settled sales cohorts and an assumed diminishing-return curve.")
    inputs = planning_inputs(selected)
    if inputs.empty:
        st.info("Broaden the date filter to include cohorts at least 56 days old. Planning requires 7 observed days, 20 purchases, and positive contribution before advertising per sales campaign.")
        return
    baseline = float(inputs.baseline_spend.sum())
    a, b, c = st.columns(3)
    # Namespace budget by campaign set and baseline so filters cannot silently retain an unrelated total.
    scope = hashlib.sha256(inputs[["campaign_id", "baseline_spend"]].to_csv(index=False).encode()).hexdigest()[:10]
    budget = a.number_input("Seven-day sales budget ($)", min_value=1.0, value=round(baseline, 2), step=100.0, key=f"budget_{scope}")
    flexibility = b.slider("Maximum change per campaign", 0, 100, 35, step=5, format="%d%%", key="flexibility") / 100
    saturation = c.slider("Saturation assumption", .5, 4.0, 1.5, .1, key="saturation",
                          help="Curve scale as a multiple of baseline spend. Smaller values assume stronger diminishing returns; this parameter is not learned from the data.")
    labels = inputs.set_index("campaign_id").campaign_name.to_dict()
    if "locked" in st.session_state:
        st.session_state["locked"] = [v for v in st.session_state["locked"] if v in labels]
    locked = st.multiselect("Keep these campaign budgets unchanged", inputs.campaign_id.tolist(), format_func=lambda v: labels[v], key="locked")
    st.caption(f"Calibration uses {inputs.observed_days.min():.0f}–{inputs.observed_days.max():.0f} fully observed days per eligible campaign within the selected dates. Awareness and insufficient-data campaigns are excluded; the budget applies only to the listed sales campaigns.")
    try:
        plan = optimize(inputs, budget, flexibility, saturation, locked)
    except ValueError as exc:
        st.warning(str(exc).replace("$", r"\$"))
        return
    # A proportional comparator with the same total makes unequal budgets comparable.
    comparator = inputs.baseline_spend.to_numpy() * budget / baseline
    comparator_before = response(comparator, inputs.baseline_spend, inputs.baseline_before_ad, saturation)
    current_result = float(comparator_before.sum() - budget)
    proposed_result = float(plan.proposed_contribution.sum())
    a, b, c = st.columns(3)
    a.metric("Proposed spend", money(plan.proposed_spend.sum()))
    b.metric("Modeled contribution", money(proposed_result))
    c.metric("Change vs proportional allocation", money(proposed_result - current_result), delta_color="off")
    st.caption("Comparator distributes the same total in historical proportions; it may not satisfy your locks. Results are model outputs, not forecasts or measured incremental lift.")
    plotting = plan[["campaign_name", "baseline_spend", "proposed_spend"]].melt("campaign_name", var_name="Allocation", value_name="USD")
    plotting.Allocation = plotting.Allocation.map({"baseline_spend": "Historical seven-day baseline", "proposed_spend": "Proposed"})
    chart(finish(px.bar(plotting, x="campaign_name", y="USD", color="Allocation", barmode="group", labels={"campaign_name": ""}), money=True),
          "plan_allocations", "Historical baseline and proposed seven-day spend by campaign.")
    plan_display = plan[["campaign_name", "channel", "baseline_spend", "proposed_spend", "change", "lower_bound", "upper_bound", "locked"]].rename(columns={
        "campaign_name": "Campaign", "channel": "Channel", "baseline_spend": "Baseline ($)",
        "proposed_spend": "Proposed ($)", "change": "Change ($)", "lower_bound": "Minimum ($)",
        "upper_bound": "Maximum ($)", "locked": "Locked"})
    money_columns = {col: st.column_config.NumberColumn(format="$ %.2f") for col in plan_display.columns if "($)" in col}
    st.dataframe(plan_display, hide_index=True, width="stretch", column_config=money_columns)
    st.subheader("Stress-test the assumptions")
    stress = pd.DataFrame([{"Scenario": name, "Before-ad contribution multiplier": factor,
                            "Proposed contribution ($)": float(plan.proposed_before_ad.sum() * factor - budget)}
                           for name, factor in [("Downside", .85), ("Base", 1.0), ("Upside", 1.15)]])
    st.dataframe(stress, hide_index=True, width="stretch", column_config={
        "Proposed contribution ($)": st.column_config.NumberColumn(format="$ %.2f"),
        "Before-ad contribution multiplier": st.column_config.NumberColumn(format="%.2f")})
    st.caption("±15% sensitivity in contribution before ads is an illustrative assumption, not a confidence interval. The allocation is held fixed across these scenarios.")
    with st.expander("How the model works"):
        st.write("For each campaign, historical contribution before ads anchors a saturating exponential curve. The solver allocates a fixed budget to maximize summed modeled contribution within the limits and locks. Allocation is reconciled to cents.")
        st.code("before_ad(x) = baseline_before_ad * (1 - exp(-x / scale)) / (1 - exp(-baseline_spend / scale))\nscale = baseline_spend * saturation_assumption\ncontribution(x) = before_ad(x) - x", language="text")
        st.write("A recommendation to increase spend means the assumed curve has a higher marginal return within the current constraints. Historical outcomes are observational; the response shape and future stability have not been established by an experiment.")
    export = plan.copy()
    export["saturation_assumption"] = saturation
    export["horizon_days"] = 7
    export["total_budget"] = budget
    export["result_type"] = "Assumption-based scenario; not a forecast"
    csv_download(export, "Export budget scenario and assumptions", "budget-scenario.csv", "plan_export")


def methodology(dataset, full):
    st.title("Know what the numbers mean.")
    a, b, c = st.columns(3)
    a.metric("Campaigns", number(len(dataset.campaigns)))
    b.metric("Daily creative records", number(len(dataset.performance)))
    c.metric("Recorded orders", number(len(dataset.orders)))
    st.write(f"{dataset.manifest.get('brand', 'Uploaded dataset')} · USD · events observed through {dataset.manifest['as_of']}")
    st.info("Original synthetic demonstration data. No real customer records or measured platform results." if dataset.manifest["synthetic"] else "User-provided data. Check provenance, definitions, and attribution before using conclusions.")
    definitions = pd.DataFrame([
        ("CTR", "Total clicks / total impressions", "%"), ("CPC", "Ad spend / total clicks", "USD"),
        ("Session CVR", "Recorded purchases / sessions in acquisition cohort", "%"),
        ("CPA", "Ad spend / recorded purchases", "USD"), ("New-customer acquisition cost", "Ad spend / orders marked as a new customer", "USD"),
        ("Net revenue", "Gross revenue - discounts - observed refunds", "USD"),
        ("Net ROAS", "Net attributed revenue / ad spend", "Multiple"),
        ("Contribution after ads", "Net revenue - (product cost - recovery) - fulfillment/payment/return costs - ad spend", "USD"),
        ("Contribution return on ad spend", "Contribution after ads / ad spend", "%"),
        ("Refunded order rate", "Orders with an observed refund / recorded purchases", "%")], columns=["Metric", "Definition", "Unit"])
    st.dataframe(definitions, hide_index=True, width="stretch")
    st.write("Undefined ratios display a dash, not zero. Rates are calculated from summed numerators and denominators. Contribution excludes fixed overhead, taxes, and lifetime value. Order-level attribution assigns one campaign and creative per purchase and does not establish causality.")
    st.write("Date filters select acquisition dates. Related order and refund events are included only through the declared as-of date. In the bundled simulation, fully observed cohorts are at least 56 days old (21 purchase-lag days plus 35 return-lag days). Uploaded data must meet this observation-window assumption or be interpreted separately.")
    st.subheader("Data validation")
    st.success("Required fields, identifiers, dates, numeric values, ledger links, count bounds, and refund reconciliation passed validation.")
    st.caption("Validation checks structural consistency. It does not certify that uploaded records are true or that marketing effects are causal.")
    st.download_button("Download complete dataset ZIP", export_bundle(dataset), "campaign-compass-dataset.zip", "application/zip", key="dataset_export")
    with st.expander("Dataset contract"):
        st.write("Upload a ZIP with campaigns.csv, performance.csv, orders.csv, and manifest.json at its root. Download the demo bundle to inspect the schema. Invalid uploads show an explanation and do not replace the last valid dataset.")
        st.json({k: v for k, v in dataset.manifest.items() if k != "scenario_notes"})


def main():
    st.sidebar.markdown("### Campaign Compass")
    st.sidebar.caption("NORTHSTAR OUTDOOR · MARKETING")
    upload = st.sidebar.file_uploader("Upload dataset ZIP", type=["zip"], key="dataset_upload")
    dataset = default_dataset()
    fingerprint = "default"
    if upload:
        content = upload.getvalue()
        try:
            dataset = uploaded_dataset(content)
            fingerprint = hashlib.sha256(content).hexdigest()
            st.session_state["last_valid_dataset"] = dataset
            st.session_state["last_valid_fingerprint"] = fingerprint
        except DataError as exc:
            st.sidebar.error(str(exc))
            dataset = st.session_state.get("last_valid_dataset", dataset)
            fingerprint = st.session_state.get("last_valid_fingerprint", "default")
    if st.session_state.get("data_fingerprint") != fingerprint:
        reset_filters()
        st.session_state["data_fingerprint"] = fingerprint
    full = prepared(dataset)
    view = st.sidebar.radio("Explore", ["Overview", "Platform Comparison", "Campaign Details", "Time Series", "Budget Planner", "Data & Methodology"], key="view")
    st.sidebar.divider()
    st.sidebar.markdown("**Shared filters**")
    min_day, max_day = full.date.min().date(), full.date.max().date()
    start = st.sidebar.date_input("Acquisition from", value=max(min_day, (pd.Timestamp(max_day) - pd.Timedelta(days=89)).date()), min_value=min_day, max_value=max_day, key="date_start")
    end = st.sidebar.date_input("Acquisition through", value=max_day, min_value=min_day, max_value=max_day, key="date_end")
    channels = st.sidebar.multiselect("Channels", sorted(full.channel.unique()), default=sorted(full.channel.unique()), key="channels")
    goals = st.sidebar.multiselect("Campaign goals", sorted(full.goal.unique()), default=sorted(full.goal.unique()), key="goals")
    audiences = st.sidebar.multiselect("Audiences", sorted(full.audience.unique()), default=sorted(full.audience.unique()), key="audiences")
    mature = st.sidebar.checkbox("Fully observed cohorts only", key="mature", help="At least 56 days old for the demo's purchase and return windows.")
    st.sidebar.button("Reset filters", on_click=reset_filters, width="stretch")
    st.sidebar.caption("An empty channel, audience, or goal selection means no results.")
    source = "SYNTHETIC DEMO" if dataset.manifest["synthetic"] else "UPLOADED DATA"
    st.markdown(f'<p class="eyebrow">CAMPAIGN COMPASS / {source}</p>', unsafe_allow_html=True)
    if start > end:
        st.warning("The start date must be on or before the end date.")
        return
    selected = filter_facts(full, start, end, channels, goals, audiences, mature)
    previous, prior_start, prior_end = previous_period(full, start, end, channels, goals, audiences, mature)
    context = dict(start=start, end=end, channels=channels, goals=goals, audiences=audiences, mature=mature,
                   prior_complete=prior_start >= full.date.min() and not previous.empty)
    st.markdown(f'<p class="scope">{start:%b %d, %Y} – {end:%b %d, %Y} · {selected.campaign_id.nunique()} campaigns · {len(selected):,} daily creative records · observed through {html.escape(dataset.manifest["as_of"])}</p>', unsafe_allow_html=True)
    if view == "Data & Methodology":
        methodology(dataset, full)
        return
    if selected.empty:
        st.info("No data for selected filters. Adjust the dates, select a channel/audience/goal, or reset filters.")
        return
    if not context["prior_complete"] and view in ["Overview", "Campaign Details"]:
        st.caption("The preceding period has incomplete source coverage; overview deltas are hidden and available driver values are descriptive only.")
    if view == "Overview":
        overview(selected, previous, full, dataset, context)
    elif view == "Platform Comparison":
        platforms(selected)
    elif view == "Campaign Details":
        campaigns(selected, previous)
    elif view == "Time Series":
        trends(selected, dataset)
    elif view == "Budget Planner":
        planner(selected)


if __name__ == "__main__":
    main()
