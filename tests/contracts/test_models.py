import pytest
from pydantic import ValidationError

from contracts.models import ClauseVersion, Evidence, Rule


def test_missing_evidence_cannot_invent_quote():
    with pytest.raises(ValidationError):
        Evidence(
            record_version_id="RV-01-v1", kind="missing_field", field="warning", quote="invented"
        )


def test_span_requires_order_and_exact_location():
    with pytest.raises(ValidationError):
        Evidence(record_version_id="RV-01-v1", kind="span", quote="x", start=4, end=3)


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        Evidence(record_version_id="RV-01-v1", kind="missing_field", field="warning", alien=1)


def test_clause_dates_are_half_open():
    with pytest.raises(ValidationError):
        ClauseVersion(
            id="CV-01-v1",
            clause_id="CL-01",
            document="demo",
            article="27",
            text="pending",
            source_url="https://chinhphu.vn/",
            retrieved_at="2026-10-31T05:00:00Z",
            valid_from="2026-10-31",
            valid_to="2026-10-31",
            status_note="pending",
        )


def test_unverified_rule_cannot_be_enabled():
    with pytest.raises(ValidationError):
        Rule(
            id="R-01",
            version=1,
            clause_version_id="CV-01-v1",
            title="warning",
            check_type="warning",
            enabled=True,
        )


def test_models_are_frozen():
    item = Evidence(record_version_id="RV-01-v1", kind="missing_field", field="warning")
    with pytest.raises(ValidationError):
        item.field = "other"
