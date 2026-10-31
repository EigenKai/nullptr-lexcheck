"""Generate public synthetic fixtures; never generates final evaluation data."""

import json
from pathlib import Path

from contracts.models import CheckRequest, DemoBundle

ROOT = Path(__file__).resolve().parents[1]
STAMP = "2026-10-31T05:00:00Z"
WARNING = "Thực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh."
USES = ["Hỗ trợ tiêu hóa.", "Hỗ trợ giảm cholesterol."]


def write_json(path, value):
    (ROOT / path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def build():
    records = [
        {
            "id": "REC-01",
            "company_id": "CO-DEMO",
            "product_id": "P-01",
            "kind": "dossier",
            "title": "Synthetic dossier",
        },
        {
            "id": "REC-02",
            "company_id": "CO-DEMO",
            "product_id": "P-01",
            "kind": "marketing",
            "title": "Synthetic marketing",
        },
        {
            "id": "REC-03",
            "company_id": "CO-DEMO",
            "product_id": "P-01",
            "kind": "marketing",
            "title": "Synthetic marketing control",
        },
        {
            "id": "REC-04",
            "company_id": "CO-DEMO",
            "product_id": "P-01",
            "kind": "evidence_index",
            "title": "Synthetic confirmation index; no official certificate",
        },
        {
            "id": "REC-05",
            "company_id": "CO-DEMO",
            "product_id": "P-02",
            "kind": "marketing",
            "title": "Unrelated product control",
        },
    ]
    versions = [
        {
            "id": "RV-01-v1",
            "record_id": "REC-01",
            "version": 1,
            "text": "\n".join(USES),
            "uses": USES,
            "received_at": STAMP,
        },
        {
            "id": "RV-02-v1",
            "record_id": "REC-02",
            "version": 1,
            "text": "\n".join(USES + [WARNING]),
            "uses": USES,
            "reference_ids": ["RV-01-v1", "RV-04-v1"],
            "received_at": STAMP,
        },
        {
            "id": "RV-03-v1",
            "record_id": "REC-03",
            "version": 1,
            "text": USES[0] + "\n" + WARNING,
            "uses": [USES[0]],
            "reference_ids": ["RV-01-v1", "RV-04-v1"],
            "received_at": STAMP,
        },
        {
            "id": "RV-04-v1",
            "record_id": "REC-04",
            "version": 1,
            "text": "Synthetic index links marketing RV-02-v1. No official receipt or certificate is reproduced.",
            "received_at": STAMP,
        },
        {
            "id": "RV-05-v1",
            "record_id": "REC-05",
            "version": 1,
            "text": WARNING,
            "received_at": STAMP,
        },
    ]
    request = CheckRequest.model_validate(
        {
            "profile": {
                "company_id": "CO-DEMO",
                "product_group": "tpbvsk",
                "activity": "advertising",
                "role": "domestic_distributor",
                "confirmed": True,
            },
            "records": records,
            "versions": versions,
            "target_version_ids": ["RV-02-v1", "RV-03-v1"],
            "review_date": "2026-10-31",
        }
    ).model_dump(mode="json")
    articles = [
        "27(3)(a)",
        "27(2), 27(4)(đ)",
        "26(1), 27(1), 27(6)",
        "27(2)",
        "Exact provision pending verification",
    ]
    types = ["warning", "uses", "confirmation", "endorsement", "medicinal"]
    clauses = [
        {
            "id": f"CV-{i:02}-v1",
            "clause_id": f"CL-{i:02}",
            "document": "NĐ 15/2018/NĐ-CP" if i < 5 else "Basis pending verification",
            "article": article,
            "text": f"SOURCE TEXT PENDING VERIFICATION: {article}",
            "source_url": "https://datafiles.chinhphu.vn/cpp/files/vbpq/2018/02/15.signed.pdf",
            "retrieved_at": STAMP,
            "valid_from": "2018-02-02",
            "status_note": "Source text and current applicability must be verified by rule owner before activation.",
        }
        for i, article in enumerate(articles, 1)
    ]
    rules = [
        {
            "id": f"R-{i:02}",
            "version": 1,
            "clause_version_id": f"CV-{i:02}-v1",
            "title": kind,
            "check_type": kind,
            "method": "llm" if i == 5 else "deterministic",
            "enabled": False,
        }
        for i, kind in enumerate(types, 1)
    ]
    preview = {
        "id": "CHK-preview",
        "mode": "fixture",
        "status": "not_enough_information",
        "summary": "Synthetic fixture preview; legal rules await source verification.",
        "rules_checked": [],
        "skipped_rule_ids": [r["id"] for r in rules],
        "findings": [],
        "snapshot": request,
        "model_status": "off",
        "created_at": STAMP,
    }
    event = {
        "id": "EV-01",
        "record_id": "REC-01",
        "previous_version_id": "RV-01-v1",
        "new_version": {
            **versions[0],
            "id": "RV-01-v2",
            "version": 2,
            "text": USES[0],
            "uses": [USES[0]],
            "supersedes": "RV-01-v1",
        },
        "received_at": STAMP,
    }
    bundle = DemoBundle.model_validate(
        {"request": request, "preview": preview, "event": event, "rules": rules, "clauses": clauses}
    )
    write_json("data/fixtures/demo.json", bundle.model_dump(mode="json"))
    write_json("rules/catalog.json", [r.model_dump(mode="json") for r in bundle.rules])
    write_json("rules/clauses.json", [c.model_dump(mode="json") for c in bundle.clauses])
    cases = {"clean": request}
    for name in (
        "missing-warning",
        "extra-use",
        "missing-confirmation",
        "endorsement",
        "unknown-profile",
    ):
        case = json.loads(json.dumps(request))
        if name == "missing-warning":
            case["versions"][1]["text"] = "\n".join(USES)
        elif name == "extra-use":
            case["versions"][1]["uses"] = USES + ["Hỗ trợ giấc ngủ."]
            case["versions"][1]["text"] += "\nHỗ trợ giấc ngủ."
        elif name == "missing-confirmation":
            case["versions"][1]["reference_ids"] = ["RV-01-v1"]
            case["versions"][2]["reference_ids"] = ["RV-01-v1"]
            case["records"] = [r for r in case["records"] if r["id"] != "REC-04"]
            case["versions"] = [v for v in case["versions"] if v["record_id"] != "REC-04"]
        elif name == "endorsement":
            case["versions"][1]["text"] += "\nBác sĩ khuyên dùng sản phẩm này."
        else:
            case["profile"]["activity"] = "unknown"
            case["profile"]["confirmed"] = False
        cases[name] = CheckRequest.model_validate(case).model_dump(mode="json")
    for name, case in cases.items():
        write_json(f"data/fixtures/cases/{name}.json", case)
    quote = "Hỗ trợ giấc ngủ."
    text = cases["extra-use"]["versions"][1]["text"]
    preview_finding = {
        "id": "F-preview-01",
        "rule_id": "R-02",
        "rule_version": 1,
        "clause_version_id": "CV-02-v1",
        "record_version_id": "RV-02-v1",
        "status": "needs_evidence",
        "source": "rule",
        "severity": "medium",
        "message": "Synthetic fixture: supporting evidence not found in the connected records.",
        "clause_quote": clauses[1]["text"],
        "evidence": [
            {
                "record_version_id": "RV-02-v1",
                "kind": "span",
                "quote": quote,
                "start": text.index(quote),
                "end": text.index(quote) + len(quote),
            }
        ],
    }
    from contracts.models import CheckResult

    showcase = CheckResult.model_validate(
        {
            **preview,
            "id": "CHK-finding-preview",
            "snapshot": cases["extra-use"],
            "findings": [preview_finding],
        }
    )
    write_json("data/fixtures/finding-preview.json", showcase.model_dump(mode="json"))
    write_json(
        "data/fixtures/answers.json",
        {
            "label": "synthetic/staged; conditional on verified rules",
            "cases": {
                "clean": [],
                "missing-warning": ["R-01"],
                "extra-use": ["R-02"],
                "missing-confirmation": ["R-03"],
                "endorsement": ["R-04"],
                "unknown-profile": [],
            },
            "change_targets": ["RV-02-v1", "RV-03-v1"],
            "unrelated_target": "RV-05-v1",
        },
    )


if __name__ == "__main__":
    build()
