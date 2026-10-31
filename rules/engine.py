"""Bootstrap adapter. Rule owner replaces this with verified checks."""

from contracts.models import CheckRequest, ClauseVersion, Pattern, Rule, RuleEvaluation


def evaluate(
    request: CheckRequest,
    *,
    rules: tuple[Rule, ...] | None = None,
    clauses: tuple[ClauseVersion, ...] | None = None,
    patterns: tuple[Pattern, ...] = (),
) -> RuleEvaluation:
    return RuleEvaluation(
        mode="fixture",
        applicability="not_enough_information",
        reason="Rule implementation and source verification pending.",
    )
