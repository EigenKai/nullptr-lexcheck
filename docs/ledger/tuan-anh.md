| time (+07) | member | kind | what | result | link |
|---|---|---|---|---|---|
| 14:07 | Tuấn Anh | task | Grounding validator and offline pipeline | 62 tests; 26 owned tests; validator 95%; offline eval bootstrap N=0; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/4 |
| 14:11 | Tuấn Anh | task | Structured proposals, scoped cache, snapshot citations and draft development evaluation | 91 tests; 55 owned tests; runtime detect/eval coverage 93%; 15 draft cases, executed scope empty, scores unmeasured; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/5 |
| 14:14 | Tuấn Anh | task | Single-use final evaluation CLI with private aggregate output | 98 tests; 62 owned tests; runtime detect/eval coverage 93%; temporary dev copies only; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/6 |
| 14:19 | Tuấn Anh | task | Version-aware basis assessment and final-run preflight | Preflight preserves run allowance; effective pending clauses require evidence; old checks replay stored basis; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/6 |
| 14:21 | Tuấn Anh | task | Cache authorization before reads and transport; group, ACL and pattern isolation | 120 tests; 84 owned tests; runtime detect/eval coverage 94%; self-review complete; session integration pending | https://github.com/EigenKai/nullptr-lexcheck/pull/10 |
| 14:48 | Tuấn Anh | task | Deterministic verified warning, uses and linked-confirmation checks | 189 tests; 47 engine tests; engine statement/branch coverage 100%; fmt/test/lint/smoke/eval and dependency audit passed; disabled catalog unchanged; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/15 |
| 15:12 | Tuấn Anh | task | Align validator warning whitespace and confirmation product scope | 255 tests; 13 reference pipeline cases with zero rejections; 125 owned tests; runtime detect/eval coverage 95%; fmt/test/lint/smoke/offline eval and dependency audit passed; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/20 |

Final operator commands (credentials and model supplied by the owner; layer 3 remains off):

```sh
.venv/bin/python -B -m eval.final --directory "$HOME/nullptr-test-final" --mode live --check
LEXCHECK_LAYER3_ENABLED=0 LEXCHECK_LLM_MODE=live make eval-final FINAL_DIR="$HOME/nullptr-test-final"
```

Run the second command once on the pinned clean revision. Input shape: `cases/<name>.json` contains a CheckRequest; `answers.json` contains `{"cases":{"<name>":{"gold":[["RV-ID","R-ID"]]}}}`. Preflight reports hashes/counts only.
| 14:16 | Tuấn Anh | task | Grounded rule proposals from source-only reference inputs | 103 tests; 67 owned tests; offline reference n=3, unavailable=3; no legal accuracy measured; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/7 |

| 14:33 | Tuấn Anh | eval | Integrated regression, pair traces, measured call latency and three-run development stability | 152 tests; 97 owned tests; runtime detect/eval coverage 95%; dev n=15 with zero executed scope; stability unmeasured; self-review complete | https://github.com/EigenKai/nullptr-lexcheck/pull/10 |
| 15:36 | Tuan Anh | task | Add plain_chat_web and retrieval to SystemScore; regenerate schemas and update contract reference. Existing names remain accepted; unknown names remain rejected. | RED: 1 failed/5 passed; GREEN: 314 tests, 92% repository coverage; fmt/lint/smoke/offline eval pass; second schema export byte-identical. Self-review complete. | branch feat/tuan-anh-eval-system-names |
