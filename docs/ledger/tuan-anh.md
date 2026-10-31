| time (+07) | member | kind | what | result | link |
|---|---|---|---|---|---|
| 14:07 | Tuấn Anh | task | Grounding validator and offline pipeline | 62 tests; 26 owned tests; validator 95%; offline eval bootstrap N=0; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/4 |
| 14:11 | Tuấn Anh | task | Structured proposals, scoped cache, snapshot citations and draft development evaluation | 91 tests; 55 owned tests; runtime detect/eval coverage 93%; 15 draft cases, executed scope empty, scores unmeasured; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/5 |
| 14:14 | Tuấn Anh | task | Single-use final evaluation CLI with private aggregate output | 98 tests; 62 owned tests; runtime detect/eval coverage 93%; temporary dev copies only; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/6 |
| 14:19 | Tuấn Anh | task | Version-aware basis assessment and final-run preflight | Preflight preserves run allowance; effective pending clauses require evidence; old checks replay stored basis; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/6 |

Final operator commands (credentials and model supplied by the owner; layer 3 remains off):

```sh
.venv/bin/python -B -m eval.final --directory "$HOME/nullptr-test-final" --mode live --check
LEXCHECK_LAYER3_ENABLED=0 LEXCHECK_LLM_MODE=live make eval-final FINAL_DIR="$HOME/nullptr-test-final"
```

Run the second command once on the pinned clean revision. Input shape: `cases/<name>.json` contains a CheckRequest; `answers.json` contains `{"cases":{"<name>":{"gold":[["RV-ID","R-ID"]]}}}`. Preflight reports hashes/counts only.
| 14:16 | Tuấn Anh | task | Grounded rule proposals from source-only reference inputs | 103 tests; 67 owned tests; offline reference n=3, unavailable=3; no legal accuracy measured; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/7 |
| 15:28 | Tuấn Anh | task | Lex identity for the reviewer UI on top of #13 (presentation only): brand tokens measured from the existing mascot asset, sidebar mark, favicon and lighter hero/avatar images cut from it, review desk band, status-coloured finding cards, trace map, magnifier highlight, Vietnamese serif and mono fonts; code head e9220be | vitest 13/13; vite build ok; Playwright 17/17 locally (7 existing unchanged + 10 in ui/e2e/brand.spec.js, run with PW_CHANNEL=chrome and the fixture API on :8000); CI (unit + build) green; no logic, API or label change; needs deploy after merge | https://github.com/EigenKai/nullptr-lexcheck/pull/21 |
