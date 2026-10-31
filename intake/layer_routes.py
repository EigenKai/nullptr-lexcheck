"""Typed endpoints reserved for the layered implementation. No feature is enabled here."""

from fastapi import APIRouter, HTTPException

from contracts.models import (
    ApiError,
    ChatRequest,
    ChatResponse,
    CheckResult,
    DemoLoginRequest,
    DemoSession,
    EvaluationReport,
    FeatureFlags,
    FeedbackRequest,
    LegalActivationRequest,
    LegalChangeEvent,
    LegalChangeResponse,
    LegalReviewRequest,
    PatternResponse,
    PatternReviewRequest,
    RecordsResponse,
)
from intake.features import feature_flags

router = APIRouter(prefix="/api")
ERRORS = {code: {"model": ApiError} for code in (401, 403, 404, 409, 422, 503)}


def disabled():
    raise HTTPException(status_code=404, detail="feature_disabled")


@router.get("/features", response_model=FeatureFlags)
def features():
    from intake.router import runtime_mode

    return feature_flags(runtime_mode() == "live")


@router.post("/session", response_model=DemoSession, responses=ERRORS)
def session(request: DemoLoginRequest):
    raise HTTPException(status_code=503, detail="not_ready")


@router.get("/records", response_model=RecordsResponse, responses=ERRORS)
def records():
    raise HTTPException(status_code=503, detail="not_ready")


@router.get("/checks/{check_id}", response_model=CheckResult, responses=ERRORS)
def get_check(check_id: str):
    raise HTTPException(status_code=503, detail="not_ready")


@router.post("/chat", response_model=ChatResponse, responses=ERRORS)
def chat(request: ChatRequest):
    disabled()


@router.get("/evaluation", response_model=EvaluationReport, responses=ERRORS)
def evaluation():
    disabled()


@router.post("/legal-changes", response_model=LegalChangeResponse, responses=ERRORS)
def legal_change(request: LegalChangeEvent):
    disabled()


@router.post(
    "/legal-changes/{event_id}/review", response_model=LegalChangeResponse, responses=ERRORS
)
def review_legal_change(event_id: str, request: LegalReviewRequest):
    disabled()


@router.post(
    "/legal-changes/{event_id}/activate", response_model=LegalChangeResponse, responses=ERRORS
)
def activate_legal_change(event_id: str, request: LegalActivationRequest):
    disabled()


@router.post("/feedback", response_model=PatternResponse, responses=ERRORS)
def feedback(request: FeedbackRequest):
    disabled()


@router.post("/patterns/{pattern_id}/review", response_model=PatternResponse, responses=ERRORS)
def review_pattern(pattern_id: str, request: PatternReviewRequest):
    disabled()
