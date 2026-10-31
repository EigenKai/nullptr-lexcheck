from datetime import date

import pytest
from pydantic import ValidationError

from contracts.models import Evidence
from detect.validator import validate_findings


def check(request, basis, **changes):
    rule, clause, finding = basis
    return validate_findings(
        (finding.model_copy(update=changes) if changes else finding,), request, (rule,), (clause,)
    )


def test_rejects_unknown_rule(request_data, basis):
    assert check(request_data, basis, rule_id="R-absent").rejected[0].reason == "unknown_rule"


def test_rejects_fabricated_quote(request_data, basis):
    assert (
        check(request_data, basis, clause_quote="invented").rejected[0].reason == "quote_mismatch"
    )


@pytest.mark.parametrize(
    "day,accepted",
    [("2025-12-31", False), ("2026-01-01", True), ("2026-12-31", True), ("2027-01-01", False)],
)
def test_rejects_inactive_clause(request_data, basis, day, accepted):
    result = check(request_data.model_copy(update={"review_date": date.fromisoformat(day)}), basis)
    assert bool(result.findings) == accepted
    if not accepted:
        assert result.rejected[0].reason == "inactive_clause"


@pytest.mark.parametrize("state", ["suspended", "superseded", "unknown"])
def test_inactive_states(request_data, basis, state):
    rule, clause, finding = basis
    assert (
        check(request_data, (rule, clause.model_copy(update={"in_force": state}), finding))
        .rejected[0]
        .reason
        == "inactive_clause"
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"enabled": False},
        {"version": 2},
        {"verification_status": "to_be_verified", "enabled": False},
    ],
)
def test_unverified_rule(request_data, basis, changes):
    rule, clause, finding = basis
    assert (
        check(request_data, (rule.model_copy(update=changes), clause, finding)).rejected[0].reason
        == "unverified_rule"
    )


def test_missing_field_has_no_quote():
    with pytest.raises(ValidationError):
        Evidence(record_version_id="RV-01", kind="missing_field", field="uses", quote="fake")


@pytest.mark.parametrize("field", ["uses", "reference_ids", "warning"])
def test_missing_field_present(request_data, basis, field):
    finding = basis[2]
    evidence = Evidence(
        record_version_id=finding.record_version_id, kind="missing_field", field=field
    )
    assert (
        check(request_data, basis, evidence=(evidence,)).rejected[0].reason
        == "missing_field_present"
    )


@pytest.mark.parametrize("field", ["confirmation_date", "issuing_authority"])
def test_missing_field_absent(request_data, basis, field):
    evidence = Evidence(
        record_version_id=basis[2].record_version_id, kind="missing_field", field=field
    )
    assert check(request_data, basis, evidence=(evidence,)).findings


def test_unknown_field_rejected(request_data, basis):
    evidence = Evidence(
        record_version_id=basis[2].record_version_id, kind="missing_field", field="invented"
    )
    assert (
        check(request_data, basis, evidence=(evidence,)).rejected[0].reason == "evidence_mismatch"
    )


def test_evidence_outside_snapshot(request_data, basis):
    finding = basis[2]
    ev = finding.evidence[0].model_copy(update={"record_version_id": "RV-05-v1"})
    assert check(request_data, basis, evidence=(ev,)).rejected[0].reason == "evidence_mismatch"
    assert (
        check(request_data, basis, record_version_id="RV-05-v1").rejected[0].reason
        == "evidence_mismatch"
    )


def test_unicode_span_maps_to_original(request_data, basis):
    finding = basis[2]
    text = "a Tiếng Việt"
    versions = tuple(
        v.model_copy(update={"text": text}) if v.id == finding.record_version_id else v
        for v in request_data.versions
    )
    request = request_data.model_copy(update={"versions": versions})
    evidence = finding.evidence[0].model_copy(update={"quote": text[2:9], "start": 2, "end": 9})
    assert check(request, basis, evidence=(evidence,)).findings
    assert (
        check(request, basis, evidence=(evidence.model_copy(update={"start": 3}),))
        .rejected[0]
        .reason
        == "evidence_mismatch"
    )


def test_valid_finding_unchanged(request_data, basis):
    assert check(request_data, basis).findings[0] is basis[2]


def test_llm_same_checks(request_data, basis):
    assert check(request_data, basis, source="llm", status="suggestion").findings
    assert check(
        request_data, basis, source="llm", status="suggestion", clause_quote="fake"
    ).rejected


def test_rejects_clause_not_returned_this_turn(request_data, basis):
    rule, _, finding = basis
    assert (
        validate_findings((finding,), request_data, (rule,), ()).rejected[0].reason
        == "unknown_clause"
    )


def test_missing_warning_not_cancelled_by_another_target(request_data, basis):
    from pathlib import Path

    from contracts.models import CheckRequest

    path = Path(__file__).resolve().parents[2] / "data/fixtures/cases/missing-warning.json"
    request = CheckRequest.model_validate_json(path.read_text())
    missing = Evidence(record_version_id="RV-02-v1", kind="missing_field", field="warning")
    assert check(request, basis, evidence=(missing,)).findings
    present = missing.model_copy(update={"record_version_id": "RV-03-v1"})
    assert check(request, basis, evidence=(present,)).rejected[0].reason == "missing_field_present"


@pytest.mark.parametrize("field", ["warning", "uses", "text", "issuing_authority"])
def test_local_field_not_cancelled_by_context(request_data, basis, field):
    versions = tuple(
        v.model_copy(update={"text": "", "uses": (), "issuing_authority": "unknown"})
        if v.id == basis[2].record_version_id
        else v
        for v in request_data.versions
    )
    missing = Evidence(
        record_version_id=basis[2].record_version_id, kind="missing_field", field=field
    )
    assert check(
        request_data.model_copy(update={"versions": versions}), basis, evidence=(missing,)
    ).findings


@pytest.mark.parametrize("suffix", ["", "!", "\n"])
def test_warning_punctuation_and_nfd(request_data, basis, suffix):
    import unicodedata

    from detect.validator import WARNING

    versions = tuple(
        v.model_copy(update={"text": unicodedata.normalize("NFD", WARNING) + suffix})
        if v.id == basis[2].record_version_id
        else v
        for v in request_data.versions
    )
    missing = Evidence(
        record_version_id=basis[2].record_version_id, kind="missing_field", field="warning"
    )
    assert (
        check(request_data.model_copy(update={"versions": versions}), basis, evidence=(missing,))
        .rejected[0]
        .reason
        == "missing_field_present"
    )


def test_confirmation_checks_record_kind(request_data, basis):
    rule, clause, finding = basis
    confirmation_basis = (rule.model_copy(update={"check_type": "confirmation"}), clause, finding)
    missing = Evidence(
        record_version_id=finding.record_version_id, kind="missing_field", field="confirmation_date"
    )
    assert (
        check(request_data, confirmation_basis, evidence=(missing,)).rejected[0].reason
        == "missing_field_present"
    )
    request = request_data.model_copy(update={"context_version_ids": ("RV-01-v1",)})
    assert check(request, confirmation_basis, evidence=(missing,)).findings
