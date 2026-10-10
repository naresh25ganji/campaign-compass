# Five minute demo

Show a complete decision journey. All bundled results are synthetic illustrations.

1. **0:00–0:35:** Introduce the marketer's question and synthetic-data label. Define contribution after ads.
2. **0:35–1:25:** Click **1 · High ROAS, losing money**. Inspect Last chance packs: 10.68× ROAS, but a USD 12,861.97 contribution loss over 34 fully observed days. Show the cost waterfall and explicit 34-day selected/prior windows.
3. **1:25–2:10:** Click **2 · Delayed purchases**. Show equal-age purchase curves and day-7/day-21 denominators. The coverage panel shows recent cohorts still developing; these patterns are hypotheses, not causal findings.
4. **2:10–3:20:** Click **3 · Reallocate with constraints**. Save the initial plan as A, then lock Summit essentials for B. Both budgets equal USD 8,226.77; B retains USD 1,494.36 for Summit essentials. At the shared saturation assumption, that lock costs about USD 42 in modeled contribution versus A. Show the baseline satisfying B's own constraints and the sensitivity table.
5. **3:20–3:55:** Download and open the budget brief. Show coverage, both saved/current settings and allocations, and the constraint-matched baseline. These are model outputs, not forecasts or measured improvement.
6. **3:55–4:30:** Show source structure and 48-test evidence. Explain the real comparison bug: 34 mature days were compared to 90 prior days; the fix compares 34 with 34 and suppresses deltas when date coverage is incomplete.

Capture actual prompts, screenshots, bugs/fixes, and final screens during development. Do not invent model accuracy, experimental evidence, user feedback, or advertising results.

The assignment requires a Google Doc, a live demo video up to five minutes, and a GitHub code link by October 11, 2026 at 11:59 PM PT.

The submission form requires a **Video Demo Drive Link**. Upload the finished recording to Google Drive, give viewers link access, and check that it plays while signed out. The form also requires full name, email, GitHub repository link, and the project documentation Drive link. The documentation is ready; the recording and form submission remain.

## Verified recording reference

Validated against local and hosted screens on October 10 using the bundled dataset observed through September 30. Start with no uploaded data, reset filters, and select Overview. Follow presets in order; save A only after selecting preset 3. Keep the preset budget, 35% maximum change, and 1.50× saturation unchanged before locking Summit essentials.

| Moment | Expected value |
| --- | --- |
| Default Overview | 263,453 clicks; 6,477 purchases; 5.83× ROAS; 130.2% contribution ROI |
| Last chance packs | 10.68× ROAS; USD 12,861.97 contribution loss; 34 fully observed days |
| Pinterest day 7 | 994 purchases / 40,436 sessions; 2.46% session conversion |
| Pinterest day 21 | 977 purchases / 33,026 sessions; 2.96% session conversion; different eligible population |
| Both scenario budgets | USD 8,226.77 |
| Summit essentials locked in B | USD 1,494.36 |
| Modeled contribution A / B | USD 19,157.35 / USD 19,115.29 |
| B minus A | −USD 42.06, displayed rounded as −USD 42 |

The top budget card rounds to USD 8,227 while the input and comparison table retain USD 8,226.77. The narration rounds the campaign loss to USD 12,862 and lock cost to USD 42. These model outputs illustrate assumptions, not measured improvement. Dataset hashes and verification scope are recorded in [VALIDATION.json](VALIDATION.json).
