from fastapi import APIRouter, HTTPException

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
from intake.fixtures import load_demo

router = APIRouter(prefix="/api")
ERRORS = {code: {"model": ApiError} for code in (404, 409, 422, 503)}


def pending():
    raise HTTPException(status_code=503, detail="not_ready")


@router.get("/demo", response_model=DemoBundle)
def demo():
    return load_demo()


@router.post("/check", response_model=CheckResult, responses=ERRORS)
def check(request: CheckRequest):
    fixture = load_demo()
    if request != fixture.request:
        pending()
    return fixture.preview


@router.post("/changes", response_model=ChangeResponse, responses=ERRORS)
def change(event: ChangeEvent):
    pending()


@router.post("/rechecks", response_model=CheckResult, responses=ERRORS)
def recheck(request: RecheckRequest):
    pending()


@router.post("/decisions", response_model=Decision, status_code=201, responses=ERRORS)
def decide(request: DecisionRequest):
    pending()


@router.get("/history", response_model=HistoryResponse)
def history():
    return HistoryResponse(
        checks=(load_demo().preview,), decisions=(), events=(), queue=(), mode="fixture"
    )
