# Dataset contract

Upload a ZIP containing these four files at its root. The app reads entries in memory without extracting archive paths. Limits: 20 MB compressed, 30 MB expanded, ten entries.

## Campaigns

`campaigns.csv`: one row per unique campaign_id.

| Fields | Meaning |
| --- | --- |
| campaign_id, campaign_name | Nonempty unique ID and display name |
| channel, goal, audience | Grouping labels; the planner uses goal `Sales` |
| daily_budget, target_cpa | Nonnegative USD source settings |

Budget and CPA settings are metadata, not actual spend or statistical thresholds.

## Performance

`performance.csv`: one row per date/campaign_id/creative_id.

| Fields | Meaning |
| --- | --- |
| date | Acquisition day, YYYY-MM-DD |
| campaign_id, creative_id | Campaign foreign key and creative ID |
| spend | Actual USD spend for the row |
| impressions, clicks, sessions | Nonnegative integer counts |

The contract uses sessions ≤ clicks ≤ impressions. Other tracking conventions need a revised schema rather than forced conversion.

## Orders

`orders.csv`: one row per unique order_id, assigned to one campaign/creative cohort.

| Fields | Meaning |
| --- | --- |
| order_id | Unique purchase ID |
| campaign_id, creative_id, acquisition_date | Links to a daily performance row |
| order_date | Observed purchase date, on/after acquisition |
| refund_date | Blank unless a refund was observed |
| gross_revenue, discount, refund | USD amounts; gross revenue excludes taxes |
| product_cost, recovered_cost | Original product cost and observed recovery on return |
| fulfillment_cost | Fulfillment, payment, and applicable return handling costs |
| is_new_customer | true/false first-purchase flag |

Refund cannot exceed revenue less discount. Recovered cost cannot exceed product cost and requires a refund. Purchases cannot exceed sessions under the demo's one-purchase-per-session convention. Empty orders are allowed with the complete header schema.

The contract has no customer ID, so the app cannot deduplicate customers. Real customer CAC requires trustworthy first-purchase flags from a customer-level source.

## Manifest

```json
{
  "schema_version": 1,
  "brand": "Northstar Outdoor",
  "synthetic": true,
  "currency": "USD",
  "as_of": "2026-09-30",
  "attribution": "Single campaign and creative credit per order; acquisition-date cohorts."
}
```

No purchase/refund date may follow the as-of date. Dates are calendar days without mixed time zones. The author's synthetic/real declaration is not independently verified.

## Calculation flow

Orders are aggregated to acquisition date/campaign/creative before joining to performance. A validated one-to-one join preserves spend. No-purchase cohorts retain spend. Raw source tables remain separate from computed facts.

Date filters select cohorts, not transaction-date financial reports. Snapshots may revise older cohorts when delayed purchases/refunds arrive. All views share the same calculations.

Validation rejects missing columns, invalid/future dates, duplicate keys, invalid numbers, impossible counts, orphan ledger links, and inconsistent refunds. Source errors are never silently zero-filled or dropped.
