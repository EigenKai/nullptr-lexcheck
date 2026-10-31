# LexCheck · NULLPTR

Review a synthetic company's health-supplement dossier and marketing records, trace findings to versioned clauses and evidence, and recheck dependent records when a dossier changes. A human decides.

## Status

Bootstrap only: typed contracts, synthetic fixtures and API previews. All legal rules are disabled pending the rule owner's source verification. `mode=fixture` is a preview, not a legal check or a measured model result. Feature work starts after the team's review checkpoints. No live deployment yet.

## Run

Requires Python 3.11, Git and Make (Windows: WSL). No API key is needed.

```sh
make setup
make test
make lint
make eval
make run
```

Open http://127.0.0.1:8000/docs; `/health` and `/api/demo` are ready. `make smoke` exercises the fixture API; `make schemas` exports the contracts. `make eval` currently validates fixtures only and reports no accuracy number. Frontend implementation is the UI owner's first package (Vite, React, Tailwind; one FastAPI service serves its build).

## Team workflow

Read [AGENTS.md](AGENTS.md). Canonical plan: [docs/plan](docs/plan/). After the start signal, use one branch/worktree per member and pull requests only. Do not change contracts or another owner's folders inside a feature PR. Keep final evaluation cases outside this repository; Codex must not inspect them.

## Built during the hackathon

This repository was created on 31 October 2026. Product code, schema, synthetic fixtures and tests are written on site with Codex. Existing preparation consists of the idea, legal reading notes and process guidance. No earlier project code or schema is reused. Track actual work in [the build ledger](docs/build-ledger.md).

## Declarations

Existing libraries: [FastAPI](https://github.com/fastapi/fastapi) (MIT), [Pydantic](https://github.com/pydantic/pydantic) (MIT), [Uvicorn](https://github.com/encode/uvicorn) (BSD-3-Clause), [HTTPX](https://github.com/encode/httpx) (BSD-3-Clause), [pytest](https://github.com/pytest-dev/pytest) (MIT), [pytest-cov](https://github.com/pytest-dev/pytest-cov) (MIT), [Ruff](https://github.com/astral-sh/ruff) (MIT), [OpenAI Python SDK](https://github.com/openai/openai-python) (Apache-2.0), [pip-audit](https://github.com/pypa/pip-audit) (Apache-2.0). Add frontend libraries and their licenses when used. The framework examples were consulted; no project implementation was copied. Keep this declaration consistent with the submission and declarations PDF.

Only synthetic/staged company records are included. Public legal source links are documented in the plan. A missing connected record is a request for evidence, not a claim about what happened outside the connected records. No private company data, credentials or identity documents belong here.
