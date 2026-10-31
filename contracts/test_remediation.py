"""Additive task metadata contracts; no legal deadline is inferred."""

import pytest
from pydantic import ValidationError

from contracts.models import DecisionRequest, FeatureFlags


def request(**changes):
    return DecisionRequest(
        check_id="CHK-test",
        finding_id="F-test",
        action="assign",
        actor="reviewer",
        owner="marketing",
        note="Synthetic",
        **changes,
    )


def test_internal_deadline_is_independent_from_legal_deadline():
    task = request(internal_due_on="2026-11-01", closure_conditions="Fresh deterministic recheck.")
    assert task.internal_due_on.isoformat() == "2026-11-01"
    assert task.legal_due_on is None


@pytest.mark.parametrize(
    "changes",
    [
        {"legal_due_on": "2026-11-02"},
        {"legal_clause_version_id": "CV-test"},
        {"legal_due_on": "2026-11-02", "legal_clause_version_id": "CV-test"},
    ],
)
def test_legal_deadline_requires_a_version_and_verbatim_quote(changes):
    with pytest.raises(ValidationError):
        request(**changes)


def test_legal_deadline_keeps_its_source():
    task = request(
        legal_due_on="2026-11-02",
        legal_clause_version_id="CV-test",
        legal_deadline_quote="Synthetic deadline evidence.",
    )
    assert task.legal_clause_version_id == "CV-test"


def test_acknowledgement_is_a_distinct_action():
    task = request().model_copy(update={"action": "acknowledge"})
    assert DecisionRequest.model_validate_json(task.model_dump_json()).action == "acknowledge"


def test_task_features_default_off_and_need_a_live_base():
    assert not FeatureFlags().remediation
    assert not FeatureFlags().task_dashboard
    with pytest.raises(ValidationError):
        FeatureFlags(remediation=True)
    with pytest.raises(ValidationError):
        FeatureFlags(layer0_ready=True, task_dashboard=True)
