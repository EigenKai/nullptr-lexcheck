# LexCheck · NULLPTR

Review a synthetic company's health-supplement dossier and marketing records, trace findings to versioned clauses and evidence, and recheck dependent records when a dossier changes. A human decides.

## Status

Bootstrap only: typed contracts, synthetic fixtures and API previews. All legal rules are disabled pending the rule owner's source verification. `mode=fixture` is a preview, not a legal check or a measured model result. The full build is organized in four gated layers; feature work starts after the team's review checkpoints. No live deployment yet.

## Run

Reference: Python 3.11, Git and Make (Windows: WSL). No API key is needed. If only Python 3.12 is installed, use `make setup PYTHON=python3.12`; CI stays on 3.11.

```sh
make setup
make test
make lint
make eval
make run
```

Open http://127.0.0.1:8000/docs; `/health` and `/api/demo` are ready. `make smoke` exercises the fixture API; `make schemas` exports the contracts. `make eval` currently validates fixtures only and reports no accuracy number. The UI owner builds on [PR #1](https://github.com/EigenKai/nullptr-lexcheck/pull/1) after human review/merge (Vite/React, JavaScript and CSS; JSDoc/schema client checks). One FastAPI service serves the build.

## Team workflow

Read [AGENTS.md](AGENTS.md). Canonical plan: [docs/plan](docs/plan/). After the start signal, use one branch/worktree per member and pull requests only. Do not change contracts or another owner's folders inside a feature PR. Keep final evaluation cases outside this repository; Codex must not inspect them.

## Built during the hackathon

This repository was created on 31 October 2026. Product code, schema, synthetic fixtures and tests are written on site with Codex. Existing preparation consists of the idea, legal reading notes and process guidance. No earlier project code or schema is reused. Track actual work in [the build ledger](docs/build-ledger.md).

## Declarations

Existing libraries: [FastAPI](https://github.com/fastapi/fastapi) (MIT), [Pydantic](https://github.com/pydantic/pydantic) (MIT), [Uvicorn](https://github.com/encode/uvicorn) (BSD-3-Clause), [HTTPX](https://github.com/encode/httpx) (BSD-3-Clause), [pytest](https://github.com/pytest-dev/pytest) (MIT), [pytest-cov](https://github.com/pytest-dev/pytest-cov) (MIT), [Ruff](https://github.com/astral-sh/ruff) (MIT), [OpenAI Python SDK](https://github.com/openai/openai-python) (Apache-2.0), [pip-audit](https://github.com/pypa/pip-audit) (Apache-2.0). Add frontend libraries and their licenses when used. The framework examples were consulted; no project implementation was copied. Keep this declaration consistent with the submission and declarations PDF.

Only synthetic/staged company records are included. Public legal source links are documented in the plan. A missing connected record is a request for evidence, not a claim about what happened outside the connected records. No private company data, credentials or identity documents belong here.

## Layer gates

The plan covers the full Today scope with working checkpoints: records and rechecks (layer 0), cited chat and baselines (1), a preloaded legal update (2), then demo permission groups and reviewed feedback (3). Later flags default to off. `make smoke LAYER=0` through `LAYER=3` are live gates; the bootstrap intentionally cannot pass these yet. `make smoke` validates the current completed mode. See [the plan](docs/plan/plan.md) and the three member jobs. Baseline figures remain unmeasured at bootstrap.

Use `make frontend-test`, `make frontend-build` and `make e2e` after the UI package exists. Environment settings are supplied by the shell or hosting service; `.env.example` is a template, not automatically loaded. The final evaluation command is for a human only, on a pinned commit at 15:15.

Run `make fmt` before committing (contributors restrict FORMAT_PATHS to owned code). Coverage is reported without blocking CI; test failures and the current smoke gate still block delivery.
