"""Synthetic, test-only verified rules; never activate the runtime catalog."""

import json
import unicodedata
from datetime import date
from pathlib import Path

import pytest

from contracts.models import CheckRequest, ClauseVersion, Rule, RuleEvaluation
from detect.validator import WARNING, validate_findings
from rules.engine import evaluate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def pack():
    clauses = tuple(
        ClauseVersion(
            id=f"CV-test-{n}",
            clause_id=f"CL-test-{n}",
            document="Synthetic test only",
            article=str(n),
            text=f"Synthetic test requirement {n}; not a legal source.",
            source_url="https://example.org/test-only",
            source_sha256="a" * 64,
            retrieved_at="2026-10-31T05:00:00Z",
            valid_from="2026-01-01",
            valid_to="2027-01-01",
            verification_status="verified",
            in_force="in_force",
            verified_by="test-only",
            verified_at="2026-10-31T05:00:00Z",
            status_note="Test only; never a catalog source.",
        )
        for n in range(1, 4)
    )
    rules = tuple(
        Rule(
            id=f"R-0{n}",
            version=1,
            clause_version_id=clause.id,
            title=f"Test {kind}",
            check_type=kind,
            enabled=True,
            verification_status="verified",
        )
        for n, (kind, clause) in enumerate(zip(("warning", "uses", "confirmation"), clauses), 1)
    )
    return rules, clauses


def case(name="clean"):
    return CheckRequest.model_validate_json(
        (ROOT / "data/fixtures/cases" / f"{name}.json").read_text()
    )


def change_version(request, version_id="RV-02-v1", **changes):
    return request.model_copy(
        update={
            "versions": tuple(
                v.model_copy(update=changes) if v.id == version_id else v for v in request.versions
            )
        }
    )


def checked(request, pack):
    rules, clauses = pack
    result = evaluate(request, rules=rules, clauses=clauses)
    validation = validate_findings(
        result.findings, request, result.rule_snapshots, result.clause_snapshots
    )
    assert validation.rejected == ()
    assert validation.findings == result.findings
    return result


@pytest.mark.parametrize(
    "name,rule_id,kind,status",
    [
        ("missing-warning", "R-01", "missing_field", "needs_review"),
        ("extra-use", "R-02", "span", "needs_evidence"),
        ("missing-confirmation", "R-03", "missing_field", "needs_evidence"),
    ],
)
def test_each_rule_fires_on_positive_case(pack, name, rule_id, kind, status):
    result = checked(case(name), pack)
    assert result.mode == "live" and result.applicability == "applies"
    assert result.rules_checked == ("R-01", "R-02", "R-03")
    expected_targets = ("RV-02-v1", "RV-03-v1") if rule_id == "R-03" else ("RV-02-v1",)
    assert {(f.record_version_id, f.rule_id) for f in result.findings} == {
        (target, rule_id) for target in expected_targets
    }
    finding = result.findings[0]
    assert finding.source == "rule" and finding.status == status
    assert finding.evidence[0].kind == kind
    if kind == "missing_field":
        assert finding.evidence[0].quote is None
        assert finding.evidence[0].start is finding.evidence[0].end is None


def test_all_rules_stay_silent_on_negative_case(pack):
    result = checked(case(), pack)
    assert result.findings == ()
    assert result.applicability == "applies"
    assert result.rule_snapshots == pack[0] and result.clause_snapshots == pack[1]


@pytest.mark.parametrize("text", [WARNING, WARNING + ".", unicodedata.normalize("NFD", WARNING)])
def test_warning_presence_matches_validator(pack, text):
    request = change_version(case("missing-warning"), text=text)
    result = checked(request, ((pack[0][0],), (pack[1][0],)))
    assert result.rules_checked == ("R-01",) and result.findings == ()


def test_verified_rules_change_with_input(pack):
    clean = case()
    changed = change_version(clean, text="Không có khuyến cáo.")
    original = clean.model_dump_json()
    assert checked(clean, pack).findings == ()
    result = checked(changed, pack)
    assert [f.rule_id for f in result.findings] == ["R-01"]
    assert clean.model_dump_json() == original
    assert checked(changed, pack) == result


def test_uses_offsets_are_raw_code_points(pack):
    use = unicodedata.normalize("NFD", "Hỗ trợ giấc ngủ.")
    prefix = "🧪 " + unicodedata.normalize("NFD", "Sản phẩm:") + "\n"
    request = change_version(case(), text=prefix + use + "\n" + WARNING, uses=(use,))
    result = checked(request, pack)
    assert len(result.findings) == 1
    evidence = result.findings[0].evidence[0]
    assert (evidence.start, evidence.end, evidence.quote) == (len(prefix), len(prefix + use), use)


def test_supporting_science_does_not_clear_extra_use(pack):
    request = case("extra-use")
    source = request.records[0].model_copy(
        update={"id": "REC-science", "kind": "scientific_evidence"}
    )
    version = request.versions[0].model_copy(
        update={"id": "RV-science", "record_id": source.id, "uses": ("Hỗ trợ giấc ngủ.",)}
    )
    request = request.model_copy(
        update={
            "records": request.records + (source,),
            "versions": request.versions + (version,),
            "context_version_ids": request.context_version_ids + (version.id,),
        }
    )
    target = next(v for v in request.versions if v.id == "RV-02-v1")
    request = change_version(request, reference_ids=target.reference_ids + (version.id,))
    result = checked(request, pack)
    assert [(f.rule_id, f.status) for f in result.findings] == [("R-02", "needs_evidence")]


@pytest.mark.parametrize("change", ["unlinked", "unselected", "receipt"])
def test_confirmation_requires_selected_linked_confirmation(pack, change):
    request = case()
    if change == "unlinked":
        request = change_version(request, reference_ids=("RV-01-v1",))
    elif change == "unselected":
        request = request.model_copy(update={"context_version_ids": ("RV-01-v1",)})
    else:
        request = request.model_copy(
            update={
                "records": tuple(
                    r.model_copy(update={"kind": "registration_receipt"}) if r.id == "REC-04" else r
                    for r in request.records
                )
            }
        )
    result = checked(request, ((pack[0][2],), (pack[1][2],)))
    assert result.findings and all(f.rule_id == "R-03" for f in result.findings)
    assert all(f.evidence[0].field == "confirmation_date" for f in result.findings)


@pytest.mark.parametrize(
    "change",
    [{"enabled": False}, {"verification_status": "to_be_verified"}, {"method": "llm"}],
)
def test_disabled_or_unverified_rule_produces_nothing(pack, change):
    rule = pack[0][0].model_copy(update=change)
    result = checked(case("missing-warning"), ((rule,), pack[1]))
    assert result.findings == result.rules_checked == result.rule_snapshots == ()
    assert result.applicability == "not_enough_information"


@pytest.mark.parametrize(
    "change",
    [
        {"verification_status": "to_be_verified"},
        {"in_force": "suspended"},
        {"in_force": "superseded"},
        {"in_force": "unknown"},
        {"valid_from": date(2026, 11, 1)},
        {"valid_to": date(2026, 10, 31)},
    ],
)
def test_inactive_clause_produces_nothing(pack, change):
    result = checked(
        case("missing-warning"), ((pack[0][0],), (pack[1][0].model_copy(update=change),))
    )
    assert result.findings == result.rules_checked == ()
    assert result.applicability == "not_enough_information"


def test_valid_from_inclusive_and_valid_to_exclusive(pack):
    request = case("missing-warning")
    basis = ((pack[0][0],), (pack[1][0],))
    assert checked(request.model_copy(update={"review_date": date(2026, 1, 1)}), basis).findings
    assert not checked(request.model_copy(update={"review_date": date(2027, 1, 1)}), basis).findings


def test_missing_or_newer_pending_clause_prevents_old_rule(pack):
    request = case("missing-warning")
    assert not checked(request, ((pack[0][0],), ())).rules_checked
    pending = pack[1][0].model_copy(
        update={
            "id": "CV-pending",
            "valid_from": date(2026, 10, 1),
            "verification_status": "to_be_verified",
        }
    )
    result = checked(request, ((pack[0][0],), (pack[1][0], pending)))
    assert result.rules_checked == () and result.applicability == "not_enough_information"


@pytest.mark.parametrize(
    "profile",
    [
        {"confirmed": False},
        {"product_group": "unknown"},
        {"activity": "unknown"},
        {"role": "unknown"},
    ],
)
def test_unknown_profile_runs_no_ad_rules(pack, profile):
    request = case("missing-warning")
    request = request.model_copy(update={"profile": request.profile.model_copy(update=profile)})
    result = checked(request, pack)
    assert not result.findings and not result.rules_checked
    assert result.applicability == "not_enough_information"


def test_scope_and_count_are_exact(pack):
    rules = (pack[0][0], pack[0][1].model_copy(update={"enabled": False}), pack[0][2])
    result = checked(case(), (rules, pack[1]))
    assert result.rules_checked == ("R-01", "R-03")
    assert result.rule_snapshots == (rules[0], rules[2])
    assert result.clause_snapshots == (pack[1][0], pack[1][2])


def test_unselected_records_cannot_supply_dossier_or_extra_targets(pack):
    request = case("extra-use").model_copy(update={"context_version_ids": ("RV-04-v1",)})
    result = checked(request, ((pack[0][1],), (pack[1][1],)))
    assert result.findings == result.rules_checked == ()
    assert result.applicability == "not_enough_information"


def test_unquoted_use_is_uncertain_not_clean(pack):
    request = change_version(case(), uses=("Absent from raw text",))
    result = checked(request, ((pack[0][1],), (pack[1][1],)))
    assert result.findings == () and result.applicability == "not_enough_information"


def test_selected_dossier_revision_changes_result(pack):
    request = case()
    old = request.versions[0]
    revised = old.model_copy(
        update={"id": "RV-01-v2", "version": 2, "uses": (old.uses[0],), "supersedes": old.id}
    )
    request = request.model_copy(
        update={
            "versions": request.versions + (revised,),
            "context_version_ids": (revised.id, "RV-04-v1"),
        }
    )
    result = checked(request, pack)
    assert [(f.record_version_id, f.rule_id) for f in result.findings] == [("RV-02-v1", "R-02")]


def test_disabled_catalog_preserves_bootstrap_output():
    catalog = json.loads((ROOT / "rules/catalog.json").read_text())
    # A disabled copy keeps this regression useful after the owner verifies the catalog.
    disabled = tuple(
        Rule.model_validate(rule).model_copy(update={"enabled": False}) for rule in catalog
    )
    clauses = tuple(
        ClauseVersion.model_validate(c)
        for c in json.loads((ROOT / "rules/clauses.json").read_text())
    )
    expected = RuleEvaluation(
        mode="fixture",
        applicability="not_enough_information",
        reason="Rule implementation and source verification pending.",
    )
    assert evaluate(case(), rules=disabled, clauses=clauses) == expected
    assert evaluate(case(), rules=(), clauses=()) == expected


def test_default_catalog_loader_executes_supplied_verified_pack(monkeypatch, tmp_path, pack):
    from rules import engine

    (tmp_path / "catalog.json").write_text(json.dumps([r.model_dump(mode="json") for r in pack[0]]))
    (tmp_path / "clauses.json").write_text(json.dumps([c.model_dump(mode="json") for c in pack[1]]))
    monkeypatch.setattr(engine, "CATALOG_DIR", tmp_path, raising=False)
    assert evaluate(case("extra-use")).rules_checked == ("R-01", "R-02", "R-03")


@pytest.mark.parametrize("contents", [None, "not json", "{}", "null", '[{"enabled":true}]'])
def test_unreadable_or_invalid_catalog_fails_closed(monkeypatch, tmp_path, contents):
    from rules import engine

    if contents is not None:
        (tmp_path / "catalog.json").write_text(contents)
    monkeypatch.setattr(engine, "CATALOG_DIR", tmp_path)
    result = evaluate(case())
    assert result.applicability == "not_enough_information" and result.findings == ()


@pytest.mark.parametrize("duplicate", ["rule", "clause"])
def test_ambiguous_identifiers_fail_closed(pack, duplicate):
    rules, clauses = pack
    if duplicate == "rule":
        rules += (rules[0],)
    else:
        clauses += (clauses[0],)
    result = checked(case("missing-warning"), (rules, clauses))
    assert not result.rules_checked and not result.findings


def test_no_advertising_target_runs_no_rules(pack):
    request = case().model_copy(update={"target_version_ids": ("RV-05-v1",)})
    request = request.model_copy(
        update={
            "records": tuple(
                r.model_copy(update={"kind": "label"}) if r.id == "REC-05" else r
                for r in request.records
            )
        }
    )
    result = checked(request, pack)
    assert not result.findings and not result.rules_checked


@pytest.mark.parametrize(
    "change", [{"check_type": "medicinal"}, {"activities": ("ad_registration",)}]
)
def test_unimplemented_or_other_activity_rule_is_not_counted(pack, change):
    result = checked(case("missing-warning"), ((pack[0][0].model_copy(update=change),), pack[1]))
    assert not result.findings and not result.rules_checked


def test_duplicate_claim_generates_one_stable_finding(pack):
    request = case("extra-use")
    target = next(v for v in request.versions if v.id == "RV-02-v1")
    request = change_version(request, uses=target.uses + (target.uses[-1],))
    result = checked(request, pack)
    assert len(result.findings) == 1
    assert result == checked(request, pack)


def test_unrelated_dossier_cannot_clear_claim_or_create_rejected_finding(pack):
    request = case("extra-use")
    record = request.records[0].model_copy(
        update={"id": "REC-other-dossier", "product_id": "P-other"}
    )
    version = request.versions[0].model_copy(
        update={"id": "RV-other-dossier", "record_id": record.id, "uses": ("Hỗ trợ giấc ngủ.",)}
    )
    request = request.model_copy(
        update={
            "records": request.records + (record,),
            "versions": request.versions + (version,),
            "context_version_ids": request.context_version_ids + (version.id,),
        }
    )
    result = checked(request, pack)
    assert result.applicability == "not_enough_information"


def test_verified_engine_to_offline_eval_system(monkeypatch, tmp_path, pack):
    import socket

    from eval.run import evaluate_cases
    from rules import engine

    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden")

    (tmp_path / "catalog.json").write_text(json.dumps([r.model_dump(mode="json") for r in pack[0]]))
    (tmp_path / "clauses.json").write_text(json.dumps([c.model_dump(mode="json") for c in pack[1]]))
    monkeypatch.setattr(engine, "CATALOG_DIR", tmp_path)
    monkeypatch.setattr(socket, "socket", forbidden)
    samples = (
        ("clean", case(), {"gold": []}),
        ("missing-warning", case("missing-warning"), {"gold": [["RV-02-v1", "R-01"]]}),
        ("extra-use", case("extra-use"), {"gold": [["RV-02-v1", "R-02"]]}),
        (
            "missing-confirmation",
            case("missing-confirmation"),
            {"gold": [["RV-02-v1", "R-03"], ["RV-03-v1", "R-03"]]},
        ),
    )
    report, trace = evaluate_cases(samples, mode="off")
    result = next(s for s in report.systems if s.system == "lexcheck")
    assert report.rule_ids == ("R-01", "R-02", "R-03")
    assert result.evaluated_cases == 4 and result.true_positive == 4
    assert result.false_positive == result.false_negative == result.model_calls == 0
    assert all(not row["rejected"] for row in trace if "case" in row)
