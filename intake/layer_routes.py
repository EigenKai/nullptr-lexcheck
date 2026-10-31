"""Later-layer routes stay off until prerequisites and operators enable them."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from contracts.models import (
    ApiError,
    ChatRequest,
    ChatResponse,
    CheckRequest,
    CheckResult,
    DemoLoginRequest,
    DemoSession,
    EvaluationReport,
    FeatureFlags,
    FeedbackRequest,
    LegalActivationRequest,
    LegalChangeEvent,
    LegalChangeResponse,
    LegalChangeState,
    LegalReviewRequest,
    Pattern,
    PatternResponse,
    PatternReviewRequest,
    RecordsResponse,
)
from intake import auth, service
from intake.features import feature_flags
from intake.store import AuditEntry, put_immutable

router = APIRouter(prefix="/api")
ERRORS = {code: {"model": ApiError} for code in (401, 403, 404, 409, 422, 503)}


def disabled():
    raise HTTPException(status_code=404, detail="feature_disabled")


def gate(layer):
    flags = feature_flags(service.runtime_mode() == "live")
    if not getattr(flags, f"layer{layer}"):
        disabled()


@router.get("/features", response_model=FeatureFlags)
def features():
    return feature_flags(service.runtime_mode() == "live")


@router.post("/session", response_model=DemoSession, responses=ERRORS)
def session(request: DemoLoginRequest, http_request: Request):
    return auth.issue(http_request, request.user_id)


@router.get("/records", response_model=RecordsResponse, responses=ERRORS)
def records(http_request: Request):
    person = auth.principal(http_request)
    store = http_request.app.state.store
    with store.lock:
        visible = tuple(r for r in store.records.values() if auth.visible_record(r, person))
        ids = {r.id for r in visible}
        versions = tuple(v for v in store.versions.values() if v.record_id in ids)
        safe = {v.id for v in versions}
        while True:
            remaining = {v.id for v in versions if v.id in safe and set(v.reference_ids) <= safe}
            if remaining == safe:
                break
            safe = remaining
        versions = tuple(v for v in versions if v.id in safe)
        return RecordsResponse(records=visible, versions=versions)


@router.get("/checks/{check_id}", response_model=CheckResult, responses=ERRORS)
def get_check(check_id: str, http_request: Request):
    person = auth.principal(http_request)
    store = http_request.app.state.store
    with store.lock:
        return auth.get_check(store, check_id, person)


@router.post("/chat", response_model=ChatResponse, responses=ERRORS)
def chat(request: ChatRequest, http_request: Request):
    gate(1)
    person = auth.principal(http_request, required=True)
    store = http_request.app.state.store
    with store.lock:
        check = auth.get_check(store, request.check_id, person)
        try:
            answer = service.owner_module("detect.chat").answer(request, check)
        except HTTPException as exc:
            if exc.status_code != 503:
                raise
            return ChatResponse(
                status="needs_evidence",
                answer="Chat service is unavailable. No answer was generated.",
                citations=(),
                model_status="unavailable",
            )
        clauses = {c.id: c for c in check.clause_snapshots}
        versions = {v.id: v for v in check.snapshot.versions}
        for citation in answer.citations:
            clause = clauses.get(citation.clause_version_id)
            evidence = citation.evidence
            if clause is None or citation.quote not in clause.text:
                return ChatResponse(
                    status="needs_evidence",
                    answer="not enough information",
                    citations=(),
                    model_status="unavailable",
                )
            if evidence:
                source = versions.get(evidence.record_version_id)
                if (
                    source is None
                    or evidence.quote is not None
                    and evidence.quote not in source.text
                ):
                    return ChatResponse(
                        status="needs_evidence",
                        answer="not enough information",
                        citations=(),
                        model_status="unavailable",
                    )
        return answer


@router.get("/evaluation", response_model=EvaluationReport, responses=ERRORS)
def evaluation(http_request: Request):
    gate(1)
    auth.principal(http_request, manager=True)
    path = Path("eval/results/latest.json")
    if not path.exists():
        return EvaluationReport(phase="bootstrap", n=0, note="No detection performance measured.")
    try:
        return EvaluationReport.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise HTTPException(503, "not_ready") from exc


@router.post("/legal-changes", response_model=LegalChangeResponse, responses=ERRORS)
def legal_change(request: LegalChangeEvent, http_request: Request):
    gate(2)
    auth.principal(http_request, manager=True)
    store = http_request.app.state.store
    with store.transaction():
        existing = store.legal_changes.get(request.id)
        if existing and existing.event != request:
            raise HTTPException(409, "conflict")
        state = existing or LegalChangeState(event=request)
        store.legal_changes[state.event.id] = state
        return LegalChangeResponse(state=state, mode="live")


@router.post(
    "/legal-changes/{event_id}/review", response_model=LegalChangeResponse, responses=ERRORS
)
def review_legal_change(event_id: str, request: LegalReviewRequest, http_request: Request):
    gate(2)
    person = auth.principal(http_request, manager=True)
    if not request.note.strip():
        raise HTTPException(422, "invalid_request")
    store = http_request.app.state.store
    with store.transaction():
        state = store.legal_changes.get(event_id)
        if state is None:
            raise HTTPException(404, "not_found")
        if state.status != "pending":
            raise HTTPException(409, "conflict")
        accepted = request.action == "accept"
        if accepted and (
            state.event.new_clause.verification_status != "verified"
            or any(r.verification_status != "verified" for r in state.event.proposed_rules)
        ):
            raise HTTPException(409, "conflict")
        state = state.model_copy(
            update={
                "interpretation": "accepted" if accepted else "rejected",
                "status": "ready" if accepted else "rejected",
                "reviewed_by": person.user_id,
                "reviewed_at": auth.now(),
            }
        )
        store.legal_changes[event_id] = state
        store.data.audit += (
            AuditEntry(
                action=f"legal_{request.action}",
                entity_id=event_id,
                user_id=person.user_id,
                note=request.note,
                created_at=auth.now(),
            ),
        )
        return LegalChangeResponse(state=state, mode="live")


@router.post(
    "/legal-changes/{event_id}/activate", response_model=LegalChangeResponse, responses=ERRORS
)
def activate_legal_change(event_id: str, request: LegalActivationRequest, http_request: Request):
    gate(2)
    auth.principal(http_request, manager=True)
    store = http_request.app.state.store
    with store.transaction():
        state = store.legal_changes.get(event_id)
        if state is None:
            raise HTTPException(404, "not_found")
        if state.status == "active":
            return LegalChangeResponse(
                state=state,
                queue=tuple(q for q in store.queue.values() if q.event_id == event_id),
                mode="live",
            )
        activated = service.can_activate(state, request.review_date)
        if not activated or any(
            not r.enabled
            or r.verification_status != "verified"
            or r.clause_version_id != state.event.new_clause.id
            for r in activated
        ):
            raise HTTPException(409, "conflict")
        items = service.owner_module("rules.legal").affected_checks(
            state.event, tuple(store.checks.values())
        )
        for item in items:
            put_immutable(store.queue, item)
        state = state.model_copy(update={"status": "active", "activated_at": auth.now()})
        store.legal_changes[event_id] = state
        store.activations[event_id] = activated
        for key, pattern in store.patterns.items():
            if (
                pattern.clause_version_id == state.event.previous_clause_version_id
                and pattern.state == "active"
            ):
                store.patterns[key] = pattern.model_copy(update={"state": "suspended"})
        return LegalChangeResponse(state=state, queue=items, mode="live")


@router.post("/feedback", response_model=PatternResponse, responses=ERRORS)
def feedback(request: FeedbackRequest, http_request: Request):
    gate(3)
    auth.principal(http_request, manager=True)
    store = http_request.app.state.store
    with store.transaction():
        decision = store.decisions.get(request.decision_id)
        if decision is None:
            raise HTTPException(404, "not_found")
        if decision.request.action != "confirm":
            raise HTTPException(409, "conflict")
        check = store.checks[decision.request.check_id]
        finding = next(f for f in check.findings if f.id == decision.request.finding_id)
        if not any(ev.quote and request.phrase in ev.quote for ev in finding.evidence):
            raise HTTPException(422, "invalid_request")
        groups = set.intersection(*(set(r.access_groups) for r in check.snapshot.records))
        pattern = Pattern(
            id=service.identifier("PAT"),
            company_id=check.snapshot.profile.company_id,
            source_decision_id=decision.id,
            rule_id=finding.rule_id,
            rule_version=finding.rule_version,
            clause_version_id=finding.clause_version_id,
            phrase=request.phrase,
            polarity=request.polarity,
            access_groups=tuple(sorted(groups)),
        )
        put_immutable(store.patterns, pattern)
        return PatternResponse(pattern=pattern, mode="live")


@router.post("/patterns/{pattern_id}/review", response_model=PatternResponse, responses=ERRORS)
def review_pattern(pattern_id: str, request: PatternReviewRequest, http_request: Request):
    gate(3)
    person = auth.principal(http_request, manager=True)
    if not request.note.strip():
        raise HTTPException(422, "invalid_request")
    store = http_request.app.state.store
    with store.transaction():
        pattern = store.patterns.get(pattern_id)
        if pattern is None:
            raise HTTPException(404, "not_found")
        if pattern.state != "candidate":
            raise HTTPException(409, "conflict")
        if request.action == "reject":
            pattern = pattern.model_copy(
                update={"state": "rejected", "reviewed_by": person.user_id}
            )
        else:
            module = service.owner_module("rules.patterns")
            path = Path(__file__).resolve().parents[1] / "rules/examples/pattern-guard.json"
            if not path.exists():
                raise HTTPException(503, "not_ready")
            cases = tuple(
                CheckRequest.model_validate(v) for v in json.loads(path.read_text(encoding="utf-8"))
            )
            if len(cases) < 4:
                raise HTTPException(503, "not_ready")
            pattern = module.review(
                pattern.model_copy(update={"reviewed_by": person.user_id}),
                cases,
            )
            if pattern.state != "active" or not pattern.test_report_sha256:
                raise HTTPException(409, "conflict")
        store.patterns[pattern_id] = pattern
        store.data.audit += (
            AuditEntry(
                action=f"pattern_{request.action}",
                entity_id=pattern_id,
                user_id=person.user_id,
                note=request.note,
                created_at=auth.now(),
            ),
        )
        return PatternResponse(pattern=pattern, mode="live")
