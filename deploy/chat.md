# Chat runtime and verification

Chat is restricted to validated findings and evidence in one saved check. Run a
check in the reviewer screen, select its result, then open Trợ lý Lex. A check
without grounded findings returns an evidence-needed response without calling a
model. This is not a general company-document question-answering endpoint.

`LEXCHECK_LAYER1_ENABLED` controls whether the route is available, after the
actual deterministic engine is ready. It does not prove that a model is
connected. The response's `model_status` distinguishes `off`, `live`, `cached`
and `unavailable`.

The server controls chat generation through `LEXCHECK_LLM_MODE`:

| Value | Chat behavior |
| --- | --- |
| absent, `off`, or an unknown value | Cited deterministic fallback; no model call |
| `cache` | Read the scoped cache only; a miss is `unavailable`, with no live call |
| `live` | Read cache first, otherwise call the configured model |

The saved check's `snapshot.llm_mode` records how detection was requested. It
does not control a subsequent chat request. Chat creates a temporary context;
the saved check and its rule, clause and record snapshots remain unchanged.
Live and cache-only chat share a cache identity for the same question/context.

For an operator-authorized demo after the integration gates pass, configure:

```text
LEXCHECK_LAYER1_ENABLED=1
LEXCHECK_LLM_MODE=live
OPENAI_MODEL=<model available to the team's API project>
OPENAI_API_KEY=<server-side secret>
LEXCHECK_CACHE_DIR=cache/model
LEXCHECK_LLM_TIMEOUT_SECONDS=60
```

Keep defaults off until those gates pass. Setting a local `.env` file alone does
not configure an already-running Uvicorn process; pass the environment to the
server process explicitly. On Render, update the service environment and restart
only after approval of the tested main SHA. Never place the key in frontend
variables, browser storage, documentation or commits. See the
[official OpenAI authentication documentation](https://developers.openai.com/api/reference/overview#authentication).

The model client permits one retry and a configured attempt timeout of up to
180 seconds. The browser allows chat up to 390 seconds, instead of aborting it
after the ordinary 15-second API budget. The backend normally returns sooner.
A browser timeout asks the user to reload state before retrying, since an
in-flight request may still finish on the server.

## Local gates

```sh
make test
make lint
make smoke LAYER=0
make smoke LAYER=1
make frontend-test
make frontend-build
LEXCHECK_LLM_MODE=off make eval
```

On Windows, use `mingw32-make` with `PY=<absolute-path-to-venv>/Scripts/python.exe`
and `PYTHONUTF8=1`. No `LEXCHECK_RUNTIME_MODE` override is used: readiness comes
from the real engine evaluation. The smoke dispatcher executes
`intake/tests/test_smoke_layers.py::test_layer1_smoke`; its helper exercises the
real HTTP routes, engine, validator, store, session, scoped model client and
citations. Only the model transport is stubbed. Missing credentials are also
tested through the real model-client fallback, without network access.

These checks do not establish deployed same-SHA smoke, API-project model access,
real model latency or production authentication. Keep the deployed gate separate
and record its exact main SHA, flags and outcome.
