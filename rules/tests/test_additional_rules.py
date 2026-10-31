"""Synthetic R-05..08 behavior; production source gates remain independent."""

import unicodedata
from datetime import date

import pytest

from contracts.models import ClauseVersion, Rule
from detect.validator import validate_findings
from rules.engine import evaluate
from rules.tests.test_engine import case, change_version


@pytest.fixture
def pack():
    clauses = tuple(
        ClauseVersion(
            id=f"CV-extra-{i}",
            clause_id=f"CL-extra-{i}",
            document="Synthetic test basis",
            article="test only",
            text=f"Synthetic requirement{i}, not a legal quotation.",
            source_url="https://example.invalid/test",
            source_sha256="0" * 64,
            retrieved_at="2026-10-31T00:00:00Z",
            valid_from="2026-01-01",
            verification_status="verified",
            in_force="in_force",
            verified_by="test-only",
            verified_at="2026-10-31T00:00:00Z",
            status_note="Synthetic only",
        )
        for i in range(5, 9)
    )
    rules = tuple(
        Rule(
            id=f"R-0{i}",
            version=1,
            clause_version_id=clause.id,
            title=kind,
            check_type=kind,
            method="deterministic",
            activities=("advertising",) if i == 5 else ("ad_registration",),
            verification_status="verified",
            enabled=True,
        )
        for i, kind, clause in zip(
            range(5, 9), ("medicinal", "receipt", "authority_review", "label_copy"), clauses
        )
    )
    return rules, clauses


def run(request, pack, index):
    return evaluate(request, rules=(pack[0][index],), clauses=(pack[1][index],))


@pytest.mark.parametrize("text", ["Sản phẩm chữa khỏi tiểu đường.", "Sản phẩm đặc trị viêm khớp."])
def test_r05_positive_cases(pack, text):
    result = run(change_version(case(), text=text), pack, 0)
    assert result.rules_checked == ("R-05",) and result.findings
    assert all(f.status == "needs_review" and f.evidence[0].quote in text for f in result.findings)


@pytest.mark.parametrize(
    "text",
    [
        "Thực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
        "Hỗ trợ tiêu hóa. Không có tác dụng điều trị bệnh.",
    ],
)
def test_r05_negative_cases(pack, text):
    result = run(change_version(case(), text=text), pack, 0)
    assert result.rules_checked == ("R-05",) and not result.findings


def registration():
    request = case()
    return request.model_copy(
        update={
            "profile": request.profile.model_copy(update={"activity": "ad_registration"}),
            "target_version_ids": ("RV-02-v1",),
        }
    )


def add_context(request, kind, *, product="P-01", selected=True, linked=True, revision=False):
    record = request.records[0].model_copy(
        update={"id": "REC-extra", "kind": kind, "product_id": product}
    )
    version = request.versions[0].model_copy(
        update={
            "id": "RV-extra-v1",
            "record_id": record.id,
            "text": "Synthetic connected document",
            "reference_ids": (),
        }
    )
    versions = request.versions + (version,)
    chosen = version.id
    if revision:
        newer = version.model_copy(
            update={"id": "RV-extra-v2", "version": 2, "supersedes": version.id}
        )
        versions += (newer,)
        chosen = newer.id
    target = next(v for v in request.versions if v.id == "RV-02-v1")
    result = request.model_copy(
        update={
            "records": request.records + (record,),
            "versions": versions,
            "context_version_ids": request.context_version_ids + ((chosen,) if selected else ()),
        }
    )
    return change_version(
        result, reference_ids=target.reference_ids + ((version.id,) if linked else ())
    )


@pytest.mark.parametrize(
    "index,kind,field",
    [(1, "registration_receipt", "registration_receipt"), (3, "label", "label_copy")],
)
@pytest.mark.parametrize("other_product", [False, True])
def test_r06_r08_positive_cases(pack, index, kind, field, other_product):
    request = registration()
    if other_product:
        request = add_context(request, kind, product="P-other")
    result = run(request, pack, index)
    assert result.rules_checked == (pack[0][index].id,)
    assert len(result.findings) == 1
    evidence = result.findings[0].evidence[0]
    assert evidence.kind == "missing_field" and evidence.field == field and evidence.quote is None
    assert result.findings[0].status == "needs_evidence"


@pytest.mark.parametrize("index,kind", [(1, "registration_receipt"), (3, "label")])
@pytest.mark.parametrize("revision", [False, True])
def test_r06_r08_negative_cases(pack, index, kind, revision):
    request = add_context(registration(), kind, revision=revision)
    result = run(request, pack, index)
    assert result.rules_checked == (pack[0][index].id,) and result.findings == ()


@pytest.mark.parametrize("index,kind", [(1, "registration_receipt"), (3, "label")])
@pytest.mark.parametrize("scope", ["unlinked", "unselected"])
def test_unconnected_attachments_cannot_clear_missing_evidence(pack, index, kind, scope):
    sample = add_context(
        registration(), kind, selected=scope != "unselected", linked=scope != "unlinked"
    )
    result = run(sample, pack, index)
    assert len(result.findings) == 1


@pytest.mark.parametrize("index", [1, 2, 3])
def test_registration_rules_never_run_on_ordinary_advertising(pack, index):
    assert run(case(), pack, index).rules_checked == ()


def authority_request(
    *,
    confirmed_on=date(2026, 7, 2),
    authority="national_food_admin",
    text="Cục An toàn thực phẩm cấp giấy xác nhận quảng cáo.",
):
    request = registration().model_copy(
        update={"target_version_ids": ("RV-04-v1",), "context_version_ids": ("RV-01-v1",)}
    )
    return change_version(
        request, "RV-04-v1", confirmation_date=confirmed_on, issuing_authority=authority, text=text
    )


@pytest.mark.parametrize("authority", ["national_food_admin", "unknown"])
def test_r07_positive_cases(pack, authority):
    result = run(authority_request(authority=authority), pack, 2)
    assert result.rules_checked == ("R-07",) and result.findings
    assert all(
        "void" not in f.message.lower() or "not" in f.message.lower() for f in result.findings
    )


@pytest.mark.parametrize(
    "sample",
    [
        authority_request(confirmed_on=date(2026, 6, 30)),
        authority_request(
            authority="provincial_chair", text="Chủ tịch Ủy ban nhân dân cấp tỉnh cấp giấy."
        ),
    ],
)
def test_r07_negative_cases(pack, sample):
    before = sample.model_dump_json()
    result = run(sample, pack, 2)
    assert result.rules_checked == ("R-07",) and result.findings == ()
    assert sample.model_dump_json() == before


def test_r05_preserves_decomposed_raw_quote_offsets(pack):
    phrase = unicodedata.normalize("NFD", "đặc trị")
    text = "🧪 Sản phẩm " + phrase + " bệnh."
    result = run(change_version(case(), text=text), pack, 0)
    evidence = result.findings[0].evidence[0]
    assert text[evidence.start : evidence.end] == evidence.quote == phrase


@pytest.mark.parametrize("index", [0, 2])
def test_supported_new_findings_pass_shared_validator(pack, index):
    sample = (
        change_version(case(), text="Sản phẩm đặc trị bệnh.") if index == 0 else authority_request()
    )
    result = run(sample, pack, index)
    validation = validate_findings(
        result.findings, sample, result.rule_snapshots, result.clause_snapshots
    )
    assert validation.findings == result.findings and not validation.rejected


def test_shared_authority_source_does_not_duplicate_finding_ids(pack):
    sample = change_version(
        registration(),
        "RV-04-v1",
        confirmation_date=date(2026, 7, 2),
        issuing_authority="national_food_admin",
        text="Cục An toàn thực phẩm",
    )
    sample = sample.model_copy(update={"target_version_ids": ("RV-02-v1", "RV-03-v1")})
    result = run(sample, pack, 2)
    assert len(result.findings) == len({f.id for f in result.findings}) == 2


def test_unlinked_authority_source_is_uncertain_and_not_counted(pack):
    sample = change_version(registration(), reference_ids=())
    result = run(sample, pack, 2)
    assert not result.rules_checked and not result.findings
    assert result.applicability == "not_enough_information"


def test_new_catalog_entries_are_implemented_but_default_off():
    import json
    from pathlib import Path

    root = Path(__file__).parents[1]
    entries = [
        Rule.model_validate(item)
        for item in json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    ]
    basis = {
        item["id"]: ClauseVersion.model_validate(item)
        for item in json.loads((root / "clauses.json").read_text(encoding="utf-8"))
    }
    extra = [entry for entry in entries if entry.id in ("R-05", "R-06", "R-07", "R-08")]
    assert len(extra) == 4
    for entry in extra:
        assert entry.version == 2 and entry.method == "deterministic" and not entry.enabled
        assert len(entry.positive_examples) >= 2 and len(entry.negative_examples) >= 2
        assert "PENDING VERIFICATION" not in basis[entry.clause_version_id].text
