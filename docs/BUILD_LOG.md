# Development evidence

## Scope

The user selected option 2 and requested an original app with deeper data and analysis. Reviewed the handout, solution document, 60-row spreadsheet, and https://github.com/The-Gen-Academy/1B-Ad-Campaign-Performance-Analyzer, including both its Streamlit and React implementations.

This app was written independently. Reference code and data are not included. Review informed stronger validation, widget-state filter reset, well-defined rates, and contribution analysis.

## First implementation

- Original seeded generator with separate purchases and refunds.
- Strict dataset contract and in-memory ZIP import/export.
- Spend-preserving acquisition-cohort facts.
- Six views with shared filters and campaign investigation navigation.
- Contribution waterfall, creative trends, driver comparisons, and equal-age purchase curves.
- Assumed budget-response model with locks, bounds, exact totals, and sensitivity.

## Verification

The completed implementation passed 30 tests, including all six views, empty filter/reset, investigation navigation, literal search, and infeasible budget handling. It reported upstream pandas/NumPy timedelta deprecation warnings but no failures.

## Remaining submission work

Capture actual prompts/screenshots, prepare the Google Doc, and record the video. Randomized experiment analysis is deferred; no causal-lift feature is claimed.

## Chrome verification

Chrome access became available after retry. Verified investigation navigation, campaign selection, empty filters and reset, and a locked budget matching its baseline. Found dollar-sign pairs rendering as math markup in evidence text. Escaped currency in prose and feasibility messages, added reader-facing table labels/units, and changed weekly overview trends to averages per observed acquisition day so partial weeks do not look like full-week volume declines. The nine app-interaction tests passed after these changes.

## Submission improvements on October 8

Added visible clicks, purchase conversions, and contribution ROI to Overview, plus a spend/conversion trend with separate labeled axes and partial-week averages. Added contribution ROI to platform comparison and campaign tables. Added a self-contained HTML decision brief that carries the filter scope and evidence; the planner version carries the actual budget settings, locks, allocations, comparator, and sensitivity assumptions. Uploaded labels are escaped before HTML export.

Added tests for filtered source totals, exported budget totals and locks, HTML escaping, undefined ratios, and overview metrics following channel filters. All 35 tests passed locally. Prepared deployment instructions; native Google Doc import requires the Google Drive connection, and the video still needs a recorded live walkthrough.
