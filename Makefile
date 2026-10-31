PYTHON ?= python3.11
PY = .venv/bin/python
LAYER ?= auto
.PHONY: setup test lint eval run schemas smoke audit
setup:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install -r requirements.txt
test:
	$(PY) -m pytest -q --cov --cov-report=term-missing
lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
eval:
	$(PY) -m eval.run
run:
	$(PY) -m uvicorn app.main:app --host 127.0.0.1 --port 8000
schemas:
	$(PY) -m scripts.export_contracts
smoke:
	$(PY) -m scripts.smoke --layer $(LAYER)
audit:
	$(PY) -m pip_audit -r requirements.txt

frontend-test:
	cd ui && npm ci && npm test -- --run
frontend-build:
	cd ui && npm ci && npm run build
e2e:
	cd ui && npm run test:e2e
eval-final:
	$(PY) -m eval.final --directory "$(FINAL_DIR)"
