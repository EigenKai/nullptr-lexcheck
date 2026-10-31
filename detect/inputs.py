"""Public case input, deliberately independent of labels and transport mode."""


def model_input(request, rules, clauses):
    return {
        "request": request.model_dump(mode="json", exclude={"llm_mode"}),
        "rules": [r.model_dump(mode="json") for r in rules],
        "clauses": [c.model_dump(mode="json") for c in clauses],
    }
