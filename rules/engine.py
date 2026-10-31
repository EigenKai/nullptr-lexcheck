"""Bootstrap adapter. Rule owner replaces this with verified checks."""

from contracts.models import CheckRequest, RuleEvaluation


def evaluate(request: CheckRequest) -> RuleEvaluation:
    return RuleEvaluation(
        mode="fixture",
        applicability="not_enough_information",
        reason="Rule implementation and source verification pending.",
    )
