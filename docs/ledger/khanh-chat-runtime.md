# Khanh — isolated chat runtime fix

| time (Asia/Ho_Chi_Minh) | member | kind | what | result | link |
| --- | --- | --- | --- | --- | --- |
| 2026-10-31 16:13 | Khanh / Codex | task | Honor server chat mode independently of saved detection mode; preserve immutable check; permit scoped cache replay; fix premature browser timeout | Red-first reproduced 7 Python and 2 frontend failures. Then 19 focused Python tests, 15 frontend tests, production build, Ruff and editor diagnostics passed. Full Windows suite: 377 passed, 11 existing final-CLI failures due to POSIX-only os.O_NOFOLLOW; no evaluator changes. | [Chat regression tests](../../intake/tests/test_chat_runtime.py) |
| 2026-10-31 16:13 | Khanh / Codex | task | Connect real layer-1 smoke to existing dispatcher; keep layer 0 green | make smoke LAYER=0 and LAYER=1 each executed one passing test with one other-layer deselection; no skips. Real engine, validator, store, session, citations and no-key fallback; model transport stub only. Flags stay off outside test subprocesses; no deployment. | [Layer smoke](../../intake/tests/test_smoke_layers.py) |
| 2026-10-31 16:13 | Khanh / Codex | eval | Run development harness with LLM mode off | n=15 loaded, 14 scored under R-01..R-04; keyword and deterministic LexCheck each TP=4, FP=0, FN=0, false flags on clean=0; zero model calls. Model baselines and real latency unmeasured. No held-out access. | [Operator and gate notes](../../deploy/chat.md) |

Worktree: `nullptr-lexcheck-chat`; branch: `fix/khanh-chat-runtime`; base:
`86fbb03bc2030ebffe4199b53d0c1fdfc4f64cf9`. Dashboard edits and the shared Khanh ledger
were left untouched. The dashboard owner aggregates these entries after review.
