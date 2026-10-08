"""Self-contained, escaped HTML decision brief suitable for sharing and printing."""
from __future__ import annotations

from html import escape
import math

from .analytics import aggregate, metrics
from .planner import response


def text(value):
    return escape(str(value), quote=True)


def money(value):
    return "—" if not math.isfinite(value) else f"{'−' if value < 0 else ''}${abs(value):,.2f}"


def percent(value):
    return "—" if not math.isfinite(value) else f"{value:.1%}"


def table(headers, rows):
    return "<table><thead><tr>" + "".join(f"<th>{text(v)}</th>" for v in headers) + "</tr></thead><tbody>" + "".join(
        "<tr>" + "".join(f"<td>{text(v)}</td>" for v in row) + "</tr>" for row in rows) + "</tbody></table>"


def decision_brief(selected, manifest, context, findings, comparison, plan=None, scenario=None):
    """Export observations in current scope; optionally include the actual planner scenario."""
    m = metrics(selected)
    scope = table(["Selection", "Value"], [
        ("Acquisition dates", f"{context['start']} through {context['end']}"),
        ("Channels", ", ".join(context['channels'])), ("Goals", ", ".join(context['goals'])),
        ("Audiences", ", ".join(context['audiences'])),
        ("Cohorts", "At least 56 days old" if context['mature'] else "All selected ages"),
        ("Events observed through", manifest['as_of']),
        ("Source", "Synthetic demonstration" if manifest['synthetic'] else "User-provided dataset"),
    ])
    totals = table(["Metric", "Selected total"], [
        ("Ad spend", money(m['spend'])), ("Clicks", f"{m['clicks']:,.0f}"),
        ("Recorded purchase conversions", f"{m['purchases']:,.0f}"),
        ("Net revenue", money(m['net_revenue'])), ("Contribution after ads", money(m['contribution'])),
        ("Net ROAS", "—" if not math.isfinite(m['roas']) else f"{m['roas']:.2f}×"),
        ("Contribution ROI", percent(m['contribution_roi'])),
    ])
    observations = "".join(f"<article><h3>{text(f['campaign_name'])} · {text(f['title'])}</h3>"
                           f"<p>{text(f['evidence'])}</p><p><strong>Next step:</strong> {text(f['action'])}</p></article>"
                           for f in findings[:3]) or "<p>No campaign meets the investigation rules in this scope.</p>"
    recent_spend = selected.loc[selected.cohort_age.lt(56), 'spend'].sum()
    observation_note = (f"{percent(recent_spend / m['spend']) if m['spend'] else '—'} of selected spend belongs to cohorts under 56 days old. "
                        "Their purchases or returns may still develop.")
    economics = aggregate(selected, ['campaign_id', 'campaign_name', 'channel', 'goal']).sort_values('contribution')
    campaigns = table(["Campaign", "Channel", "Goal", "Spend", "Purchases", "Net ROAS", "Contribution", "Contribution ROI"], [
        (r.campaign_name, r.channel, r.goal, money(r.spend), f"{r.purchases:,.0f}",
         "—" if not math.isfinite(r.roas) else f"{r.roas:.2f}×", money(r.contribution), percent(r.contribution_roi))
        for r in economics.itertuples()])
    planning = "<p>No budget scenario is included. Download a brief from Budget Planner to include its current settings and allocation.</p>"
    if plan is not None and scenario is not None:
        budget = scenario['budget']
        proportional = plan.baseline_spend.to_numpy() * budget / plan.baseline_spend.sum()
        comparator = float(response(proportional, plan.baseline_spend, plan.baseline_before_ad, scenario['saturation']).sum() - budget)
        proposed = float(plan.proposed_contribution.sum())
        settings = table(["Assumption or result", "Value"], [
            ("Planning horizon", "7 days"), ("Total sales budget", money(budget)),
            ("Maximum campaign change", percent(scenario['flexibility'])),
            ("Saturation assumption", f"{scenario['saturation']:.2f}× baseline spend"),
            ("Modeled contribution", money(proposed)), ("Same-budget proportional comparator", money(comparator)),
            ("Modeled difference", money(proposed - comparator)),
            ("Locked campaigns", ", ".join(plan.loc[plan.locked, 'campaign_name']) or "None"),
        ])
        allocation = table(["Campaign", "Channel", "Observed days", "Baseline", "Proposed", "Change", "Minimum", "Maximum", "Locked"], [
            (r.campaign_name, r.channel, f"{r.observed_days:.0f}", money(r.baseline_spend), money(r.proposed_spend),
             money(r.change), money(r.lower_bound), money(r.upper_bound), "Yes" if r.locked else "No") for r in plan.itertuples()])
        sensitivity = table(["Before-ad assumption", "Modeled contribution"], [
            (name, money(float(plan.proposed_before_ad.sum() * factor - budget)))
            for name, factor in [('Downside −15%', .85), ('Base', 1), ('Upside +15%', 1.15)]])
        planning = (settings + "<p>Calibration uses selected sales cohorts at least 56 days old, with 7 observed days, "
                    "20 purchases, and positive contribution before ads. Excluded campaigns receive no allocation in this scenario. "
                    "Locks retain the rounded historical seven-day baseline.</p>" + allocation +
                    "<h3>Sensitivity with allocation held fixed</h3>" + sensitivity +
                    "<p>These are assumption-based scenarios, not forecasts, confidence intervals, or measured incremental lift. "
                    "The proportional comparator uses the same total budget but may not satisfy the locks.</p>")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campaign Compass decision brief</title><style>
body{{font:15px/1.55 Arial,sans-serif;color:#18283b;background:#f7f8fa;margin:0}}main{{max-width:1120px;margin:32px auto;padding:40px;background:white}}
h1{{font-size:30px;margin-top:0}}h2{{margin-top:30px;color:#147d71}}h3{{font-size:17px}}.label{{color:#147d71;font-weight:bold;letter-spacing:1px;font-size:12px}}
table{{border-collapse:collapse;width:100%;margin:16px 0;font-size:13px}}th,td{{padding:9px;border:1px solid #d9e2e8;text-align:left;overflow-wrap:anywhere}}th{{background:#edf4f3}}article{{border-bottom:1px solid #d9e2e8;padding:4px 0}}
@media(max-width:700px){{main{{margin:0;padding:18px}}table{{font-size:11px}}th,td{{padding:5px}}}}
@media print{{body{{background:white}}main{{padding:0;margin:0;max-width:none}}h2,h3{{break-after:avoid}}tr,article{{break-inside:avoid}}thead{{display:table-header-group}}}}
@page{{size:A4 landscape;margin:16mm}}
</style></head><body><main><p class="label">CAMPAIGN COMPASS · {text('SYNTHETIC DEMO' if manifest['synthetic'] else 'UPLOADED DATA')}</p>
<h1>Campaign performance decision brief</h1><p>{text(manifest.get('brand', 'Uploaded dataset'))}. Review campaign economics, investigate observed changes, and share the next budget scenario.</p>
<h2>Selection and observation window</h2>{scope}<h2>Performance in the selected scope</h2>{totals}<p>{text(observation_note)}</p>
<h2>Investigate next</h2><p>{text(comparison)} Evidence rules flag hypotheses, not statistical significance.</p>{observations}
<h2>Campaign economics</h2><p>Sorted by contribution after ads. Compare similar campaign goals when interpreting acquisition metrics.</p>{campaigns}
<h2>Budget scenario</h2>{planning}
<h2>Definitions and limits</h2><p>Net revenue = gross revenue − discounts − observed refunds. Contribution after ads = net revenue − net product costs − fulfillment, payment and return costs − advertising. Contribution ROI = contribution after ads ÷ ad spend. Net ROAS = net revenue ÷ ad spend. Undefined ratios display a dash.</p>
<p>Dates select acquisition cohorts; recorded purchases and refunds are credited through the declared as-of date. Fully observed demo cohorts are at least 56 days old. Contribution excludes overhead, taxes, and lifetime value. Single-campaign attribution and historical observations do not establish causality.</p>
<p>Open this file in a browser to share or print it. All currency amounts are USD.</p></main></body></html>'''
