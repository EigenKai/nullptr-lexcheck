"""Offline adapter; detection owner adds validated, cached suggestions."""

from contracts.models import CheckRequest, DetectionResult, RuleEvaluation


def suggest(request: CheckRequest, evaluation: RuleEvaluation) -> DetectionResult:
    return DetectionResult(model_status="off")
