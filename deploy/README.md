# Deployment

The existing public bootstrap is at https://nullptr-lexcheck.onrender.com/docs.
It is a fixture preview, not a completed live review pipeline.

After local review, configure one Render/Railway Python service:

- Branch: the human-reviewed main commit.
- Build: `bash deploy/build.sh` (includes the UI only when its lockfile exists).
- Start: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`.
- Health path: `/health`.
- Environment: `PYTHON_VERSION=3.11.14`, `NODE_VERSION=22.15.0`, `PYTHONUTF8=1`.
- `LEXCHECK_LAYER1_ENABLED`, `LEXCHECK_LAYER2_ENABLED`, `LEXCHECK_LAYER3_ENABLED`: `0`.
- `LEXCHECK_STATE_FILE=cache/demo-state.json`. Sessions are ephemeral and never persisted.

Local preview: build the UI, restart the API, open `/` and `/docs` on port 8000.
For Windows use the workspace tasks, or set `PYTHONUTF8=1` and override Make's
Python command with `PY=.venv/Scripts/python.exe`.

Enable a layer only after its owner dependencies, genuine integration smoke,
frontend checks, and human review pass on the same main SHA. Restart after env
changes. A free instance has ephemeral storage: atomic snapshots survive process
restarts while the file exists, but a redeploy or instance replacement may lose
them. This is a single-worker synthetic demo, not durable production storage.

Khanh authorized publishing the branch and opening a review PR on 2026-10-31.
This does not enable any layer or deploy this feature branch. Keep the existing
public fixture deployment until the integrated main SHA passes its real gates.

Integration baseline: main `2049c21` includes detection, cited chat and dev eval
(PRs #4–#8). The rule engine remains bootstrap; impact/legal/pattern adapters
await their owners. The scoped-cache PR #10 still needs current-session
authorization callback integration before layer 3 can be accepted. Intake now
passes server user/group and hashes of canonical ACL/active patterns to the
existing model client; no client-supplied role is trusted.

Windows verification currently has 10 upstream final-CLI test failures because
`eval/final.py` uses POSIX-only `os.O_NOFOLLOW`; report these to the eval owner.
This branch does not change the owner's evaluator or access the final dataset.
