"""Typed synthetic examples for later layers; all features remain disabled."""

import json
from pathlib import Path

from contracts import models as m
from intake.fixtures import load_demo

ROOT = Path(__file__).resolve().parents[1]
STAMP = "2026-10-31T06:00:00Z"


def build():
    bundle = load_demo()
    clause = m.ClauseVersion(
        id="CV-07-v2",
        clause_id="CL-07",
        document="NQ 21/2026/NQ-CP",
        article="2(1)(a), 6(2)",
        text="SOURCE TEXT PENDING VERIFICATION: NQ 21/2026 Article 2(1)(a).",
        source_url="https://xdcs.cdnchinhphu.vn/446259493575335936/2026/5/5/21-nqcp-signed-1777970679563128188225.pdf",
        retrieved_at=STAMP,
        valid_from="2026-07-01",
        valid_to="2028-01-01",
        status_note="Preloaded historical update; rule owner must verify text and dates.",
    )
    rule = m.Rule(
        id="R-07",
        version=2,
        clause_version_id=clause.id,
        title="Confirmation authority review",
        check_type="authority_review",
        activities=("ad_registration",),
    )
    event = m.LegalChangeEvent(
        id="EV-L01",
        previous_clause_version_id="CV-07-v1",
        new_clause=clause,
        proposed_rules=(rule,),
        issued_on="2026-04-29",
        effective_on="2026-07-01",
        received_at=STAMP,
    )
    pattern = m.Pattern(
        id="PAT-01",
        company_id="CO-DEMO",
        source_decision_id="DEC-01",
        rule_id="R-02",
        rule_version=1,
        clause_version_id="CV-02-v1",
        phrase="Hỗ trợ giấc ngủ.",
        polarity="positive",
    )
    objects = {
        "FeatureFlags": m.FeatureFlags(),
        "DemoLoginRequest": m.DemoLoginRequest(user_id="U-MANAGER"),
        "DemoSession": m.DemoSession(
            user_id="U-MANAGER",
            group="manager",
            token="synthetic-fixture-session-only",
            expires_at="2026-10-31T17:00:00Z",
        ),
        "RecordsResponse": m.RecordsResponse(
            records=bundle.request.records, versions=bundle.request.versions
        ),
        "ChatRequest": m.ChatRequest(
            check_id="CHK-finding-preview", question="Cần bổ sung hồ sơ nào?"
        ),
        "ChatResponse": m.ChatResponse(
            status="needs_evidence", answer="Source verification is pending.", citations=()
        ),
        "LegalChangeEvent": event,
        "LegalReviewRequest": m.LegalReviewRequest(
            action="accept", note="Review original text and effective dates before acceptance."
        ),
        "LegalActivationRequest": m.LegalActivationRequest(review_date="2026-10-31"),
        "LegalChangeResponse": m.LegalChangeResponse(
            state=m.LegalChangeState(event=event), mode="fixture"
        ),
        "FeedbackRequest": m.FeedbackRequest(
            decision_id="DEC-01", phrase=pattern.phrase, polarity="positive"
        ),
        "PatternReviewRequest": m.PatternReviewRequest(
            action="accept", note="Run positive and clean guard cases before activation."
        ),
        "PatternResponse": m.PatternResponse(pattern=pattern, mode="fixture"),
        "EvaluationReport": m.EvaluationReport(
            phase="bootstrap", n=0, note="No model performance measured."
        ),
    }
    path = ROOT / "data/fixtures/layers.json"
    path.write_text(
        json.dumps(
            {name: obj.model_dump(mode="json") for name, obj in objects.items()},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    shared = bundle.request.model_dump(mode="json")
    shared["records"] = [r for r in shared["records"] if r["id"] != "REC-05"]
    shared["versions"] = [v for v in shared["versions"] if v["record_id"] != "REC-05"]
    private = bundle.request.model_dump(mode="json")
    private["target_version_ids"] = ["RV-05-v1"]
    private["context_version_ids"] = []
    private["records"] = [
        {**r, "access_groups": ["manager"]} for r in private["records"] if r["id"] == "REC-05"
    ]
    private["versions"] = [v for v in private["versions"] if v["record_id"] == "REC-05"]
    access = {
        "label": "synthetic/staged",
        "shared_request": m.CheckRequest.model_validate(shared).model_dump(mode="json"),
        "manager_request": m.CheckRequest.model_validate(private).model_dump(mode="json"),
    }
    (ROOT / "data/fixtures/access.json").write_text(
        json.dumps(access, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    build()
