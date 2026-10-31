"""API orchestration; legal checks belong exclusively to rules/ and detect/."""

import json
from datetime import date
from importlib import import_module
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from contracts.models import CheckResult, ClauseVersion, Decision, Rule
from detect import service as detection
from detect import validator
from intake.auth import now, visible_check
from intake.features import feature_flags
from intake.fixtures import load_demo
from intake.store import put_immutable
from rules import engine


def identifier(prefix):
    return f"{prefix}-{uuid4().hex}"


def owner_module(name):
    try:
        return import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name == name:
            raise HTTPException(503, "not_ready") from exc
        raise


def runtime_mode():
    evaluation = engine.evaluate(load_demo().request)
    return "live" if evaluation.mode == "live" else "fixture"


def evaluate(snapshot, store, *, parent=None, persist=True, person=None):
    with store.lock:
        if any(use not in version.text for version in snapshot.versions for use in version.uses):
            raise HTTPException(422, "invalid_request")
        overlays = tuple(s for s in store.legal_changes.values() if s.status == "active")
        patterns = tuple(
            p
            for p in store.patterns.values()
            if p.state == "active"
            and (
                person is None
                or person.group == "manager"
                or (
                    person.group in p.access_groups
                    and p.source_decision_id in store.decisions
                    and store.decisions[p.source_decision_id].request.check_id in store.checks
                    and visible_check(
                        store.checks[store.decisions[p.source_decision_id].request.check_id],
                        person,
                        store,
                    )
                )
            )
        )
        options = {}
        if overlays:
            root = Path(__file__).resolve().parents[1]
            rules = {
                r.id: r
                for r in (
                    Rule.model_validate(v)
                    for v in json.loads((root / "rules/catalog.json").read_text(encoding="utf-8"))
                )
            }
            clauses = {
                c.id: c
                for c in (
                    ClauseVersion.model_validate(v)
                    for v in json.loads((root / "rules/clauses.json").read_text(encoding="utf-8"))
                )
            }
            for state in overlays:
                if state.event.effective_on <= snapshot.review_date:
                    clauses[state.event.new_clause.id] = state.event.new_clause
                    activated = store.activations.get(state.event.id)
                    if not activated:
                        raise HTTPException(503, "not_ready")
                    rules.update({r.id: r for r in activated})
            options.update(rules=tuple(rules.values()), clauses=tuple(clauses.values()))
        if patterns:
            options["patterns"] = patterns
        evaluation = engine.evaluate(snapshot, **options)
        if evaluation.mode != "live":
            fixture = load_demo()
            if snapshot == fixture.request and parent is None:
                return fixture.preview
            raise HTTPException(503, "not_ready")
        # Default off regardless of client llm_mode. No direct model calls here.
        flags = feature_flags(True)
        model_snapshot = (
            snapshot if flags.layer1 else snapshot.model_copy(update={"llm_mode": "off"})
        )
        suggestions = detection.suggest(model_snapshot, evaluation)
        checked = validator.validate_findings(
            evaluation.findings + suggestions.findings,
            snapshot,
            evaluation.rule_snapshots,
            evaluation.clause_snapshots,
        )
        findings = tuple(f.model_copy(update={"id": identifier("F")}) for f in checked.findings)
        gap = any(
            s.event.effective_on <= snapshot.review_date
            and s.status != "active"
            and snapshot.profile.product_group == "tpbvsk"
            and any(snapshot.profile.activity in r.activities for r in s.event.proposed_rules)
            for s in store.legal_changes.values()
        )
        uncertain = (
            not evaluation.rules_checked
            or bool(evaluation.skipped_rule_ids)
            or evaluation.applicability != "applies"
            or bool(checked.rejected)
            or gap
            or (snapshot.llm_mode != "off" and suggestions.model_status == "unavailable")
        )
        status = (
            "needs_review"
            if findings
            else "not_enough_information"
            if uncertain
            else "no_issue_found"
        )
        summary = (
            f"no issue found under {len(evaluation.rules_checked)} encoded rules"
            if status == "no_issue_found"
            else "Legal update requires manual review."
            if gap
            else "Review the cited findings."
            if findings
            else "not enough information"
        )
        result = CheckResult(
            id=identifier("CHK"),
            mode="live",
            status=status,
            summary=summary,
            rules_checked=evaluation.rules_checked,
            skipped_rule_ids=evaluation.skipped_rule_ids,
            findings=findings,
            snapshot=snapshot,
            model_status=suggestions.model_status,
            rule_snapshots=evaluation.rule_snapshots,
            clause_snapshots=evaluation.clause_snapshots,
            validator_rejections=checked.rejected,
            pattern_ids_used=evaluation.pattern_ids_used,
            applicability=evaluation.applicability,
            applicability_reason=evaluation.reason,
            created_at=now(),
            parent_check_id=parent,
        )
        if persist:
            store.save_check(result)
        return result


def change(event, store):
    with store.transaction():
        old = store.events.get(event.id)
        if old:
            if old != event:
                raise HTTPException(409, "conflict")
            return tuple(q for q in store.queue.values() if q.event_id == event.id)
        impact = owner_module("rules.impact")
        previous = store.versions.get(event.previous_version_id)
        if previous is None or previous.record_id != event.record_id:
            raise HTTPException(404, "not_found")
        latest = max(v.version for v in store.versions.values() if v.record_id == event.record_id)
        if previous.version != latest or event.new_version.version != latest + 1:
            raise HTTPException(409, "conflict")
        items = impact.enqueue(event, tuple(store.checks.values()))
        put_immutable(store.versions, event.new_version)
        put_immutable(store.events, event)
        seen = {
            (q.event_id, q.previous_check_id, q.target_version_id) for q in store.queue.values()
        }
        for item in items:
            key = (item.event_id, item.previous_check_id, item.target_version_id)
            if key not in seen:
                item = item.model_copy(update={"id": identifier("RQ")})
                put_immutable(store.queue, item)
                seen.add(key)
        return tuple(q for q in store.queue.values() if q.event_id == event.id)


def recheck(item_id, llm_mode, store):
    with store.transaction():
        item = store.queue.get(item_id)
        if item is None:
            raise HTTPException(404, "not_found")
        if item.status == "completed":
            return store.checks[item.new_check_id]
        previous = store.checks[item.previous_check_id]
        if item.reason == "legal_dependency":
            snapshot = previous.snapshot
        else:
            event = store.events[item.event_id]
            snapshot = owner_module("rules.impact").apply_event(previous.snapshot, event)
            target = (
                event.new_version.id
                if item.target_version_id == event.previous_version_id
                else item.target_version_id
            )
            snapshot = snapshot.model_copy(update={"target_version_ids": (target,)})
        snapshot = snapshot.model_copy(update={"llm_mode": llm_mode})
        result = evaluate(snapshot, store, parent=previous.id, persist=False)
        if result.mode != "live":
            raise HTTPException(503, "not_ready")
        put_immutable(store.checks, result)
        for record in snapshot.records:
            put_immutable(store.records, record)
        for version in snapshot.versions:
            put_immutable(store.versions, version)
        store.queue[item.id] = item.model_copy(
            update={"status": "completed", "new_check_id": result.id}
        )
        return result


def decide(payload, person, store):
    with store.transaction():
        if person is None or person.group != "manager":
            raise HTTPException(403, "forbidden")
        if not payload.note.strip():
            raise HTTPException(422, "invalid_request")
        check = store.checks.get(payload.check_id)
        finding = (
            next((f for f in check.findings if f.id == payload.finding_id), None) if check else None
        )
        if finding is None:
            raise HTTPException(404, "not_found")
        prior = [d for d in store.decisions.values() if d.request.finding_id == finding.id]
        if prior and prior[-1].task_status in ("closed", "dismissed"):
            raise HTTPException(409, "conflict")
        if payload.action == "close":
            fresh = store.checks.get(payload.closure_check_id)
            original = next(v for v in check.snapshot.versions if v.id == finding.record_version_id)
            if (
                fresh is None
                or fresh.parent_check_id != check.id
                or fresh.created_at <= check.created_at
                or fresh.mode != "live"
                or fresh.status == "not_enough_information"
                or fresh.applicability != "applies"
                or fresh.skipped_rule_ids
                or fresh.validator_rejections
                or finding.rule_id not in fresh.rules_checked
                or not any(
                    v.record_id == original.record_id and v.id in fresh.snapshot.target_version_ids
                    for v in fresh.snapshot.versions
                )
                or any(f.rule_id == finding.rule_id for f in fresh.findings)
            ):
                raise HTTPException(409, "conflict")
            current_version = max(
                (v for v in store.versions.values() if v.record_id == original.record_id),
                key=lambda v: v.version,
            )
            if current_version.id not in fresh.snapshot.target_version_ids:
                raise HTTPException(409, "conflict")
            if any(
                q.status == "queued"
                and q.previous_check_id in (check.id, fresh.id)
                and store.versions.get(q.target_version_id)
                and store.versions[q.target_version_id].record_id == original.record_id
                for q in store.queue.values()
            ):
                raise HTTPException(409, "conflict")
        decision = Decision(
            id=identifier("DEC"),
            request=payload,
            actor_user_id=person.user_id,
            task_status={
                "confirm": "open",
                "assign": "assigned",
                "reject": "dismissed",
                "close": "closed",
            }[payload.action],
            created_at=now(),
        )
        put_immutable(store.decisions, decision)
        return decision


def can_activate(state, review_date):
    if state.interpretation != "accepted" or state.event.effective_on > min(
        review_date, date.today()
    ):
        raise HTTPException(409, "conflict")
    return owner_module("rules.legal").validate_activation(state, review_date)
