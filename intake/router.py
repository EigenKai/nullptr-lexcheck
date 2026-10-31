from fastapi import APIRouter, HTTPException, Request

from contracts.models import (
    ApiError,
    ChangeEvent,
    ChangeResponse,
    CheckRequest,
    CheckResult,
    Decision,
    DecisionRequest,
    DemoBundle,
    HistoryResponse,
    RecheckRequest,
)
from intake import auth, service
from intake.features import feature_flags
from intake.fixtures import load_demo

router = APIRouter(prefix="/api")
ERRORS = {code: {"model": ApiError} for code in (404, 409, 422, 503)}


def runtime_mode():
    return service.runtime_mode()


def pending():
    raise HTTPException(status_code=503, detail="not_ready")


def write_access(http_request):
    if runtime_mode() != "live":
        auth.principal(http_request)
        pending()
    return auth.principal(http_request, manager=True)


@router.get("/demo", response_model=DemoBundle)
def demo(http_request: Request):
    person = auth.principal(http_request)
    if feature_flags(runtime_mode() == "live").layer3 and person.group != "manager":
        raise HTTPException(403, "forbidden")
    bundle = load_demo()
    evaluated = service.engine.evaluate(bundle.request)
    if evaluated.mode == "live":
        return bundle.model_copy(
            update={"rules": evaluated.rule_snapshots, "clauses": evaluated.clause_snapshots}
        )
    return bundle


@router.post("/check", response_model=CheckResult, responses=ERRORS)
def check(request: CheckRequest, http_request: Request):
    person = auth.principal(http_request)
    store = http_request.app.state.store
    with store.lock:
        auth.authorize_input(request, person, store)
        return service.evaluate(request, store, person=person)


@router.post("/changes", response_model=ChangeResponse, responses=ERRORS)
def change(event: ChangeEvent, http_request: Request):
    write_access(http_request)
    queue = service.change(event, http_request.app.state.store)
    return ChangeResponse(event=event, queue=queue, mode="live")


@router.post("/rechecks", response_model=CheckResult, responses=ERRORS)
def recheck(request: RecheckRequest, http_request: Request):
    person = write_access(http_request)
    return service.recheck(
        request.item_id, request.llm_mode, http_request.app.state.store, person=person
    )


@router.post("/decisions", response_model=Decision, status_code=201, responses=ERRORS)
def decide(request: DecisionRequest, http_request: Request):
    person = write_access(http_request)
    return service.decide(request, person, http_request.app.state.store)


@router.get("/history", response_model=HistoryResponse)
def history(http_request: Request):
    person = auth.principal(http_request)
    store = http_request.app.state.store
    with store.lock:
        checks = tuple(c for c in store.checks.values() if auth.visible_check(c, person, store))
        ids = {c.id for c in checks}
        manager = person is None or person.group == "manager"
        decisions = tuple(
            d
            for d in store.decisions.values()
            if d.request.check_id in ids
            and (manager or d.request.owner in ("marketing", "document_control"))
        )
        queue = tuple(
            q
            for q in store.queue.values()
            if q.previous_check_id in ids and (q.new_check_id is None or q.new_check_id in ids)
        )
        event_ids = {q.event_id for q in queue}
        visible_versions = {
            v.id
            for v in store.versions.values()
            if auth.visible_record(store.records[v.record_id], person)
        }
        events = tuple(
            e
            for e in store.events.values()
            if manager
            or (
                e.id in event_ids
                and e.record_id in store.records
                and auth.visible_record(store.records[e.record_id], person)
                and set(e.new_version.reference_ids) <= visible_versions
            )
        )
        if not manager:
            safe_events = {e.id for e in events}
            queue = tuple(q for q in queue if q.event_id in safe_events)
        return HistoryResponse(
            checks=checks
            or ((load_demo().preview,) if runtime_mode() == "fixture" and manager else ()),
            decisions=decisions,
            events=events,
            queue=queue,
            legal_changes=tuple(store.legal_changes.values()) if manager else (),
            patterns=tuple(
                p
                for p in store.patterns.values()
                if manager
                or (
                    person.group in p.access_groups
                    and p.source_decision_id in {d.id for d in decisions}
                )
            ),
            mode=runtime_mode(),
        )
