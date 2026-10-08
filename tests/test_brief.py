from html.parser import HTMLParser
import pandas as pd
import pytest

from campaign_compass.analytics import filter_facts
from campaign_compass.brief import decision_brief, money
from campaign_compass.planner import optimize, planning_inputs


class Tables(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ['td', 'th']:
            self.cell = ''

    def handle_data(self, value):
        if self.cell is not None:
            self.cell += value

    def handle_endtag(self, tag):
        if tag in ['td', 'th']:
            self.row.append(self.cell)
            self.cell = None
        elif tag == 'tr':
            self.rows.append(self.row)


def scope(full, **changes):
    context = dict(start='2026-07-03', end='2026-09-30', channels=['Pinterest'],
                   goals=['Sales'], audiences=sorted(full.audience.unique()), mature=False)
    context.update(changes)
    selected = filter_facts(full, context['start'], context['end'], context['channels'], context['goals'], context['audiences'], context['mature'])
    return context, selected


def test_brief_uses_filtered_source_totals(dataset, full):
    context, selected = scope(full)
    rows = Tables(decision_brief(selected, dataset.manifest, context, [], 'Comparison period')).rows
    totals = dict(r for r in rows if len(r) == 2)
    source = dataset.performance
    ids = dataset.campaigns.loc[(dataset.campaigns.channel == 'Pinterest') & (dataset.campaigns.goal == 'Sales'), 'campaign_id']
    direct = source.loc[source.campaign_id.isin(ids) & source.date.between(pd.Timestamp(context['start']), pd.Timestamp(context['end']))]
    assert totals['Ad spend'] == money(direct.spend.sum())
    assert totals['Clicks'] == f'{direct.clicks.sum():,.0f}'
    assert totals['Channels'] == 'Pinterest'
    assert totals['Goals'] == 'Sales'
    assert 'No budget scenario is included' in decision_brief(selected, dataset.manifest, context, [], '')


def test_brief_exports_actual_locks_and_budget(dataset, full):
    context, selected = scope(full, channels=sorted(full.channel.unique()))
    inputs = planning_inputs(selected)
    budget = round(inputs.baseline_spend.sum(), 2)
    locked_id = inputs.campaign_id.iloc[0]
    plan = optimize(inputs, budget, .35, 1.5, [locked_id])
    content = decision_brief(selected, dataset.manifest, context, [], '', plan, dict(budget=budget, flexibility=.35, saturation=1.5))
    rows = Tables(content).rows
    allocation = [r for r in rows if len(r) == 9 and r[-1] in ['Yes', 'No']]
    def dollars(v):
        return float(v.replace('−', '-').replace('$', '').replace(',', ''))
    assert sum(dollars(r[4]) for r in allocation) == pytest.approx(budget)
    locked = next(r for r in allocation if r[-1] == 'Yes')
    assert locked[3] == locked[4] == locked[6] == locked[7]
    settings = dict(r for r in rows if len(r) == 2)
    assert settings['Total sales budget'] == money(budget)
    assert settings['Saturation assumption'] == '1.50× baseline spend'
    assert 'not forecasts' in content


def test_brief_escapes_uploaded_labels_and_findings(dataset, full):
    context, selected = scope(full)
    hostile = '<script>alert("test")</script>'
    selected = selected.copy()
    selected['campaign_name'] = hostile
    manifest = dict(dataset.manifest, brand=hostile)
    finding = dict(campaign_name=hostile, title=hostile, evidence=hostile, action=hostile)
    content = decision_brief(selected, manifest, context, [finding], hostile)
    assert hostile not in content
    assert '<script>' not in content
    assert '&lt;script&gt;' in content


def test_brief_handles_zero_spend_without_infinite_ratios(dataset, full):
    context, selected = scope(full)
    selected = selected.copy()
    selected['spend'] = 0
    rows = Tables(decision_brief(selected, dataset.manifest, context, [], '')).rows
    totals = dict(r for r in rows if len(r) == 2)
    assert totals['Net ROAS'] == '—'
    assert totals['Contribution ROI'] == '—'
