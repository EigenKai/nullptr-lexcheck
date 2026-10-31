"""Deterministic advertising checks over an immutable, verified rule snapshot."""

import hashlib
import json
import unicodedata
from pathlib import Path

from contracts.models import (
    CheckRequest,
    ClauseVersion,
    Evidence,
    Finding,
    Pattern,
    Rule,
    RuleEvaluation,
)
from detect.validator import WARNING

CATALOG_DIR = Path(__file__).resolve().parent
CHECK_TYPES = ("warning", "uses", "confirmation", "endorsement")


def _pending(reason="Rule implementation and source verification pending."):
    return RuleEvaluation(mode="fixture", applicability="not_enough_information", reason=reason)


def _load(name, model):
    return tuple(
        model.model_validate(item)
        for item in json.loads((CATALOG_DIR / name).read_text(encoding="utf-8"))
    )


def _active(rule, clause, clauses, review_date):
    return (
        rule.enabled
        and rule.verification_status == "verified"
        and rule.method == "deterministic"
        and rule.check_type in CHECK_TYPES
        and clause is not None
        and clause.verification_status == "verified"
        and clause.in_force == "in_force"
        and clause.valid_from <= review_date
        and (clause.valid_to is None or review_date < clause.valid_to)
        and not any(
            other.clause_id == clause.clause_id
            and other.id != clause.id
            and clause.valid_from < other.valid_from <= review_date
            for other in clauses
        )
    )


def _finding(rule, clause, evidence):
    messages = {
        "warning": "Mandatory warning not found in the advertising record.",
        "uses": "Claimed use is outside the connected dossier; supporting evidence needs human review.",
        "confirmation": "Advertising confirmation not found in the connected records.",
        "endorsement": "Medical endorsement or medical identity in advertising text needs human review.",
    }
    identity = json.dumps(
        [rule.id, rule.version, clause.id, evidence.model_dump(mode="json")], sort_keys=True
    )
    return Finding(
        id="F-" + hashlib.sha256(identity.encode()).hexdigest()[:32],
        rule_id=rule.id,
        rule_version=rule.version,
        clause_version_id=clause.id,
        record_version_id=evidence.record_version_id,
        status="needs_review"
        if rule.check_type in ("warning", "endorsement")
        else "needs_evidence",
        source="rule",
        severity=rule.severity,
        message=messages[rule.check_type],
        clause_quote=clause.text,
        evidence=(evidence,),
    )


def _use_evidence(version, request, records, selected):
    # A changed dossier is selected by record identity; old reference IDs stay immutable.
    linked_records = {v.record_id for v in request.versions if v.id in version.reference_ids}
    dossiers = tuple(
        v
        for v in selected
        if v.id in request.context_version_ids
        and v.record_id in linked_records
        and records[v.record_id].kind == "dossier"
        and records[v.record_id].product_id == records[version.record_id].product_id
    )
    if len(dossiers) != 1:
        return (), False
    extra_uses = tuple(dict.fromkeys(use for use in version.uses if use not in dossiers[0].uses))
    if any(use not in version.text for use in extra_uses):
        return (), False
    # The current validator compares uses across all selected context dossiers.
    # Conflicting dossier scope must stay uncertain until that scope is narrowed.
    if any(
        use in other.uses
        for use in extra_uses
        for other in selected
        if other.id in request.context_version_ids
        and other.id != dossiers[0].id
        and records[other.record_id].kind == "dossier"
    ):
        return (), False
    return tuple(
        Evidence(
            record_version_id=version.id,
            kind="span",
            quote=use,
            start=version.text.index(use),
            end=version.text.index(use) + len(use),
        )
        for use in extra_uses
    ), True


def _evidence(rule, version, request, records, selected):
    if rule.check_type == "endorsement":
        from rules.endorsement import spans

        return tuple(
            Evidence(
                record_version_id=version.id,
                kind="span",
                quote=version.text[start:end],
                start=start,
                end=end,
            )
            for start, end in spans(version.text)
        ), True
    if rule.check_type == "uses":
        return _use_evidence(version, request, records, selected)
    if rule.check_type == "warning":
        # Normalize only for presence; evidence offsets always use untouched text.
        present = WARNING in " ".join(unicodedata.normalize("NFC", version.text).split())
        field = "warning"
    else:
        present = any(
            v.id in version.reference_ids
            and records[v.record_id].kind == "ad_confirmation"
            and records[v.record_id].product_id == records[version.record_id].product_id
            for v in selected
        )
        field = "confirmation_date"
    evidence = (
        ()
        if present
        else (Evidence(record_version_id=version.id, kind="missing_field", field=field),)
    )
    return evidence, True


def _execute(request, rules, clauses, targets, records, selected):
    checked, findings = [], []
    incomplete = False
    for rule in rules:
        executed = False
        for version in targets:
            evidence, complete = _evidence(rule, version, request, records, selected)
            incomplete |= not complete
            executed |= complete
            findings.extend(_finding(rule, clauses[rule.clause_version_id], e) for e in evidence)
        if executed:
            checked.append(rule)
    return tuple(checked), tuple(findings), incomplete


def evaluate(
    request: CheckRequest,
    *,
    rules: tuple[Rule, ...] | None = None,
    clauses: tuple[ClauseVersion, ...] | None = None,
    patterns: tuple[Pattern, ...] = (),
) -> RuleEvaluation:
    """Run only implemented, active rules on selected advertising targets.

    Patterns do not affect these deterministic checks. Missing comparison
    inputs remain uncertain; no ungrounded span or clean conclusion is emitted.
    """
    try:
        rules = _load("catalog.json", Rule) if rules is None else rules
        clauses = _load("clauses.json", ClauseVersion) if clauses is None else clauses
    except (OSError, ValueError, TypeError):
        return _pending("Could not load the verified rule snapshot.")
    clause_map = {c.id: c for c in clauses}
    if len(clause_map) != len(clauses) or len({r.id for r in rules}) != len(rules):
        return _pending("Rule or clause version identifiers are ambiguous.")
    profile = request.profile
    if not (
        profile.confirmed
        and profile.product_group == "tpbvsk"
        and profile.activity == "advertising"
        and profile.role != "unknown"
    ):
        return _pending("A confirmed advertising profile is required.")
    active = tuple(
        rule
        for rule in rules
        if profile.activity in rule.activities
        and _active(rule, clause_map.get(rule.clause_version_id), clauses, request.review_date)
    )
    if not active:
        return _pending()
    records = {r.id: r for r in request.records}
    selected = tuple(
        v
        for v in request.versions
        if v.id in request.target_version_ids + request.context_version_ids
    )
    targets = tuple(
        v
        for v in selected
        if v.id in request.target_version_ids
        and records[v.record_id].kind in ("marketing", "customer_script")
    )
    if not targets:
        return _pending("No selected advertising record to check.")
    checked, findings, incomplete = _execute(
        request, active, clause_map, targets, records, selected
    )
    clause_ids = tuple(dict.fromkeys(r.clause_version_id for r in checked))
    return RuleEvaluation(
        mode="live",
        applicability="not_enough_information" if incomplete else "applies",
        reason="Connected dossier or exact use text is missing or ambiguous."
        if incomplete
        else "Verified advertising checks executed on the selected records.",
        rules_checked=tuple(r.id for r in checked),
        skipped_rule_ids=tuple(
            r.id
            for r in rules
            if r.enabled and profile.activity in r.activities and r not in checked
        ),
        rule_snapshots=checked,
        clause_snapshots=tuple(clause_map[cid] for cid in clause_ids),
        findings=findings,
    )
