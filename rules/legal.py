"""Pure activation checks and legal-dependency queues over immutable snapshots."""

import json
from datetime import date
from pathlib import Path

from contracts.models import (
    CheckResult,
    ClauseVersion,
    LegalChangeEvent,
    LegalChangeState,
    RecheckItem,
    Rule,
)
from rules.impact import _identity


def validate_activation(state: LegalChangeState, review_date: date) -> tuple[Rule, ...]:
    """Return an enabled overlay only after accepted, verified, effective review.

    The caller authorizes the reviewer, checks the actual system date (as intake's
    can_activate already does), persists activation time/queue and keeps history.
    This function does not access clocks, files, models, stores or environment.
    """
    try:
        state = LegalChangeState.model_validate(state.model_dump(mode="json"))
    except ValueError:
        return ()
    event, clause = state.event, state.event.new_clause
    if state.interpretation != "accepted" or state.status not in ("ready", "active"):
        return ()
    if not state.reviewed_by or state.reviewed_at is None:
        return ()
    if state.reviewed_at < event.received_at or state.reviewed_at.date() > review_date:
        return ()
    if (
        clause.verification_status != "verified"
        or clause.in_force != "in_force"
        or not clause.source_sha256
        or not clause.verified_by
        or clause.verified_at is None
        or clause.verified_at > state.reviewed_at
    ):
        return ()
    if event.effective_on > review_date or (
        clause.valid_to is not None and review_date >= clause.valid_to
    ):
        return ()
    if len({rule.id for rule in event.proposed_rules}) != len(event.proposed_rules):
        return ()
    if any(
        rule.verification_status != "verified" or rule.method != "deterministic"
        for rule in event.proposed_rules
    ):
        return ()
    return tuple(
        Rule.model_validate({**rule.model_dump(mode="json"), "enabled": True})
        for rule in event.proposed_rules
    )


def affected_checks(
    event: LegalChangeEvent, checks: tuple[CheckResult, ...]
) -> tuple[RecheckItem, ...]:
    """Queue actual old-clause dependencies, including previous clean results.

    Queuing requests a fresh review; it never invalidates a confirmation, changes
    an old result, decides the new finding, or activates pending interpretation.
    The caller invokes this only after activation has passed its separate gate.
    """
    event = LegalChangeEvent.model_validate(event.model_dump(mode="json"))
    unique = {}
    for check in checks:
        if check.id in unique and unique[check.id] != check:
            raise ValueError("Check ID has conflicting immutable snapshots.")
        unique[check.id] = check
    affected_ids = {rule.id for rule in event.proposed_rules}
    activities = {activity for rule in event.proposed_rules for activity in rule.activities}
    items = []
    for check in unique.values():
        profile = check.snapshot.profile
        if (
            not profile.confirmed
            or profile.product_group != "tpbvsk"
            or profile.role == "unknown"
            or profile.activity not in activities
        ):
            continue
        dependent = any(
            rule.id in affected_ids and rule.clause_version_id == event.previous_clause_version_id
            for rule in check.rule_snapshots
        )
        if not dependent:
            continue
        for target_id in check.snapshot.target_version_ids:
            items.append(
                RecheckItem(
                    id=_identity(event.id, check.id, target_id),
                    event_id=event.id,
                    previous_check_id=check.id,
                    target_version_id=target_id,
                    reason="legal_dependency",
                    status="queued",
                )
            )
    return tuple(sorted(items, key=lambda item: (item.previous_check_id, item.target_version_id)))


def load_preloaded() -> tuple[ClauseVersion, LegalChangeState]:
    """Load the explicitly preloaded, source-verified but inactive demo event."""
    payload = json.loads(
        Path(__file__).with_name("nq21-preloaded.json").read_text(encoding="utf-8")
    )
    old = ClauseVersion.model_validate(payload["previous_clause"])
    state = LegalChangeState.model_validate(payload["state"])
    if (
        old.id != state.event.previous_clause_version_id
        or old.clause_id != state.event.new_clause.clause_id
    ):
        raise ValueError("Preloaded clause history does not match the event.")
    return old, state
