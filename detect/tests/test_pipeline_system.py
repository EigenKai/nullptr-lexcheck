from pathlib import Path

from contracts.models import CheckRequest
from detect.service import suggest
from detect.validator import validate_findings
from rules.engine import evaluate


def test_pipeline_system(basis):
    rule, clause, finding = basis
    paths = (Path(__file__).resolve().parents[2] / "data/fixtures/cases").glob("*.json")
    for path in paths:
        request = CheckRequest.model_validate_json(path.read_text())
        evaluation = evaluate(request, rules=(rule,), clauses=(clause,))
        detection = suggest(request, evaluation)
        candidates = (
            evaluation.findings
            + detection.findings
            + (
                finding.model_copy(update={"id": "F-quote", "clause_quote": "fabricated"}),
                finding.model_copy(update={"id": "F-rule", "rule_id": "R-absent"}),
                finding.model_copy(
                    update={
                        "id": "F-span",
                        "evidence": (finding.evidence[0].model_copy(update={"start": 1}),),
                    }
                ),
            )
        )
        result = validate_findings(candidates, request, (rule,), (clause,))
        assert {"F-quote", "F-rule", "F-span"} <= {r.finding_id for r in result.rejected}
        assert all(f.evidence and f.clause_quote for f in result.findings)
    request = CheckRequest.model_validate_json((path.parent / "clean.json").read_text())
    assert validate_findings((finding,), request, (rule,), (clause,)).findings == (finding,)
