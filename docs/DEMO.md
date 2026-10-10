# Five minute demo

Tell the complete story from source data to a reviewable marketing decision. All bundled results are synthetic illustrations. Target 4:40 including navigation, with a 20-second buffer; rehearse the full flow.

| Time | Show | Explain |
| --- | --- | --- |
| 0:00–0:20 | Overview | The question: can strong advertising revenue hide a contribution loss? |
| 0:20–1:05 | Data & Methodology; Dataset contract | The team sample informed requirements. Our original seeded generator creates 12 campaigns, 4,320 daily creative records, and 13,365 orders. Explain campaigns, performance, orders, and the manifest; data is observed through September 30, 2026. |
| 1:05–1:35 | Data validation and formulas; Overview; Platform Comparison | Validate inputs, aggregate orders before the spend-preserving join, calculate weighted rates, and apply shared date/channel/goal/audience filters. |
| 1:35–2:15 | Preset 1; Last chance packs row; Contribution breakdown | Point to 10.68× Net ROAS and −USD 12,861.97 Contribution in the campaign table. Show equal 34-day windows, then the cost waterfall. |
| 2:15–2:45 | Preset 2; cohort denominators | Pinterest: 2.46% at day 7 and 2.96% at day 21, with different eligible populations. Delayed outcomes require observation-age context; no causal conclusion is claimed. |
| 2:45–3:35 | Preset 3; save A, lock Summit for B; A/B, baseline, sensitivity | Both budgets USD 8,226.77; Summit B locked at USD 1,494.36. Approximately USD 42 lower modeled contribution under the same saturation assumption. Show a baseline respecting B constraints. |
| 3:35–4:00 | Download and independently open the current budget brief | Carry the scope, evidence, allocations, constraints, and assumptions into a shareable decision. |
| 4:00–4:40 | GitHub generator/contract, passing tests, actual prompts/build log; return to live app | Describe Codex collaboration, the 34-versus-90-day comparison fix, synchronized resets, 48 tests, and byte-identical local/hosted data. |

The default 90-day Overview includes 2,160 daily creative records; the full 180-day source dataset contains 4,320. Show the full counts in Data & Methodology when describing the dataset. Campaign findings are computed from records, not generator scenario labels. Reproducibility and structural checks do not establish real-world accuracy or causal advertising effects.

Use actual prompts, screens, bugs, and fixes. Do not invent experimental results or user feedback. The assignment requires a Google Doc, a live demo video up to five minutes, and a GitHub code link by October 11, 2026 at 11:59 PM Pacific. Upload the recording to Google Drive, enable viewer link access, and check signed-out playback. The form requires identity, GitHub, Video Demo Drive Link, and Project Documentation Drive Link. The recording and form submission remain.

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
