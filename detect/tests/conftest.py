import json
from pathlib import Path

import pytest

from contracts.models import CheckRequest, ClauseVersion, Evidence, Finding, Rule

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def request_data():
    return CheckRequest.model_validate_json((ROOT / "data/fixtures/cases/clean.json").read_text())


@pytest.fixture
def basis(request_data):
    data = json.loads((Path(__file__).parent / "fixtures/basis.json").read_text())
    rule = Rule.model_validate(data["rule"])
    clause = ClauseVersion.model_validate(data["clause"])
    version = next(v for v in request_data.versions if v.id in request_data.target_version_ids)
    finding = Finding(
        id="F-test",
        rule_id=rule.id,
        rule_version=1,
        clause_version_id=clause.id,
        record_version_id=version.id,
        status="needs_review",
        source="rule",
        severity="medium",
        message="Test-only review item.",
        clause_quote=clause.text,
        evidence=(
            Evidence(
                record_version_id=version.id, kind="span", quote=version.text[:5], start=0, end=5
            ),
        ),
    )
    return rule, clause, finding
