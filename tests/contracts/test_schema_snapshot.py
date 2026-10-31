import json
from pathlib import Path

from app.main import app
from contracts import models
from scripts.export_contracts import contract_models

ROOT = Path(__file__).resolve().parents[2]


def test_json_schemas_match_models():
    for model in contract_models():
        stored = json.loads((ROOT / f"schemas/{model.__name__}.schema.json").read_text())
        assert stored == model.model_json_schema()


def test_openapi_matches_routes():
    assert json.loads((ROOT / "schemas/openapi.json").read_text()) == app.openapi()


def test_documented_models_are_exact_source():
    source = Path(models.__file__).read_text().strip()
    doc = (ROOT / "docs/plan/contracts.md").read_text()
    assert f"```python\n{source}\n```" in doc
