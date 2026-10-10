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

## Public deployment on October 8

Deployed to https://campaign-compass.streamlit.app/ through Chrome after the user completed GitHub authentication and authorization. Used `main`, `app.py`, and Python 3.12. Verified all six hosted views, investigation navigation, empty filters and reset, and Summit essentials locked at USD 1494.36. Downloaded both HTML briefs from the hosted app and opened the budget brief independently to verify its selected lock and assumptions. Prepared a visually verified five-page submission document and a timed narration script; the video remains to be recorded.

## Comparison and guided-decision improvements on October 10

Corrected mature-only periods before selecting the preceding comparison. The default maturity filter now compares July 3–August 5 with May 30–July 2, 34 calendar days each. Spend changes by −4.4%, replacing the misleading −63.6% from a 34-versus-90-day comparison. Mature investigations use July 9–August 5 versus June 11–July 8. Missing date coverage hides overview deltas.

Added visible included/eligible dates, fully observed dates, and developing spend, with explicit observation-age partitions. Three guided presets demonstrate high ROAS with a loss, delayed purchases, and constrained reallocation. Added deep-copied Scenario A, equal-budget and identical-scope guards, common-saturation evaluation of fixed A/B allocations, and CSV/HTML exports retaining both settings and allocations. A separate proportional baseline satisfies the current budget, limits, and locks.

All 48 tests passed locally. Chrome verified the maturity comparison and all three presets. Saving the unlocked USD 8226.77 plan as A and locking Summit essentials for B showed approximately USD 42 less modeled contribution for B; the lock remained at USD 1494.36. Downloaded and independently opened the A/B brief in Chrome, confirming coverage, both budgets, constraints, and allocations. Updated the demo narration and submission document to match these features.

Published commit `b5a7693`; GitHub Actions [38086937660](https://github.com/naresh25ganji/campaign-compass/actions/runs/38086937660) passed 48 tests. The cloud process retained an older imported analytics module after pulling the update; the logs showed the missing new export. Rebooted through Manage app, then verified the new public coverage panel and saved A/B comparison in Chrome. Refreshed both repository screenshots from the hosted version.

## Final validation on October 10

Rechecked the required views, global filters, units, empty states, documentation, public repository, and hosted app against the handout. Replaced scalar pandas day-duration construction with Python's `datetime.timedelta` in the app, comparisons, and generator to remove the installed NumPy version's generic-duration deprecation warnings. All 48 tests pass with deprecation warnings treated as errors. Regenerating all four dataset files produced byte-identical content; campaign results and demo values are unchanged. The installed dependency set is compatible.

An additional diagnostic exercised 100 reproducible feasible budgets with varied bounds, locks, and saturation assumptions. Both optimized and proportional allocations preserved each total to cents, stayed within bounds, and retained locked budgets. The optimized modeled contribution was no worse than the constraint-matched baseline in those scenarios. This checks implementation behavior, not causal advertising performance.

Chrome confirmed all six public views, saved A/B comparison, and Google Doc access without signing in. The submission form was inspected through the existing signed-in Google session; it requires a Video Demo Drive Link along with identity, code, and documentation fields. No response was submitted. Updated the recording checklist accordingly and clarified Python 3.12 in the setup instructions because the pinned NumPy dependency requires it. The narration contains 412 spoken words, approximately 3.2 minutes at 130 words per minute before navigation.

The final visual reset check found a browser/server mismatch: deleting filter keys restored default server totals but left visible Sales and maturity controls selected after a guided preset. Reset now writes explicit data-derived widget values, including search and locks. Presets use the same reset, and the budget preset explicitly restores its derived starting total. Date and budget widgets read their initialized state without a competing default. Extended the guided-preset interaction check to verify reset, overview totals after navigation, and the budget preset after changing its total.
