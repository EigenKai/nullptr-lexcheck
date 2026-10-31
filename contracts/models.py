"""Canonical immutable contracts. Export with make schemas."""

from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

Id = Annotated[str, Field(pattern=r"^[A-Z][A-Za-z0-9-]{1,79}$")]
Text = Annotated[str, Field(min_length=1, max_length=20000)]
Verification = Literal["to_be_verified", "verified"]
FindingStatus = Literal["needs_review", "needs_evidence", "suggestion"]
ResultStatus = Literal["needs_review", "not_enough_information", "no_issue_found"]
Mode = Literal["fixture", "live"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CompanyProfile(Contract):
    company_id: Id
    product_group: Literal["tpbvsk", "other", "unknown"]
    activity: Literal["advertising", "label_only", "unknown"]
    role: Literal["domestic_distributor", "producer", "importer", "unknown"]
    confirmed: bool
    synthetic: Literal[True] = True


class Record(Contract):
    id: Id
    company_id: Id
    product_id: Id
    kind: Literal[
        "dossier", "marketing", "customer_script", "evidence_index", "scientific_evidence"
    ]
    title: Text
    synthetic: Literal[True] = True


class RecordVersion(Contract):
    id: Id
    record_id: Id
    version: int = Field(ge=1)
    text: str = Field(max_length=20000)
    uses: tuple[Text, ...] = ()
    reference_ids: tuple[Id, ...] = ()
    received_at: AwareDatetime
    supersedes: Id | None = None


class ClauseVersion(Contract):
    id: Id
    clause_id: Id
    document: Text
    article: Text
    text: Text
    source_url: HttpUrl
    source_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    retrieved_at: AwareDatetime
    valid_from: date
    valid_to: date | None = None
    verification_status: Verification = "to_be_verified"
    in_force: Literal["in_force", "suspended", "superseded", "unknown"] = "unknown"
    verified_by: str | None = None
    verified_at: AwareDatetime | None = None
    status_note: Text

    @model_validator(mode="after")
    def validate_interval(self):
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("invalid effective interval")
        if self.verification_status == "verified" and not (
            self.verified_by and self.verified_at and self.source_sha256
        ):
            raise ValueError("verification requires reviewer, time and source hash")
        return self


class Rule(Contract):
    id: Id
    version: int = Field(ge=1)
    clause_version_id: Id
    title: Text
    check_type: Literal["warning", "uses", "confirmation", "endorsement", "medicinal"]
    method: Literal["deterministic", "llm"] = "deterministic"
    severity: Literal["low", "medium", "high"] = "medium"
    verification_status: Verification = "to_be_verified"
    enabled: bool = False
    patterns: tuple[Text, ...] = ()
    positive_examples: tuple[Text, ...] = ()
    negative_examples: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def validate_activation(self):
        if self.enabled and self.verification_status != "verified":
            raise ValueError("unverified rule cannot run")
        return self


class Evidence(Contract):
    record_version_id: Id
    kind: Literal["span", "missing_field", "cell", "page"]
    quote: Text | None = None
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=1)
    field: str | None = None
    sheet: str | None = None
    cell: str | None = None
    page: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_location(self):
        if self.kind == "missing_field":
            if not self.field or any(
                x is not None
                for x in (self.quote, self.start, self.end, self.sheet, self.cell, self.page)
            ):
                raise ValueError("missing field has no quote or position")
        elif self.kind == "span":
            if not self.quote or self.start is None or self.end is None or self.end <= self.start:
                raise ValueError("span needs a quote and ordered offsets")
            if any(x is not None for x in (self.field, self.sheet, self.cell, self.page)):
                raise ValueError("span has only offsets")
        elif self.kind == "cell":
            if not self.sheet or not self.cell or not self.quote:
                raise ValueError("cell evidence needs sheet, cell and quote")
            if any(x is not None for x in (self.start, self.end, self.field, self.page)):
                raise ValueError("cell has no other location")
        elif (
            not self.page
            or not self.quote
            or any(x is not None for x in (self.start, self.end, self.field, self.sheet, self.cell))
        ):
            raise ValueError("page evidence needs page and quote only")
        return self


class Finding(Contract):
    id: Id
    rule_id: Id
    rule_version: int = Field(ge=1)
    clause_version_id: Id
    record_version_id: Id
    status: FindingStatus
    source: Literal["rule", "llm"]
    severity: Literal["low", "medium", "high"]
    message: Text
    clause_quote: Text
    evidence: tuple[Evidence, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_suggestion(self):
        if self.source == "llm" and self.status not in ("suggestion", "needs_evidence"):
            raise ValueError("model output is only a reviewer suggestion")
        return self


class CheckRequest(Contract):
    profile: CompanyProfile
    records: tuple[Record, ...] = Field(min_length=1, max_length=50)
    versions: tuple[RecordVersion, ...] = Field(min_length=1, max_length=100)
    target_version_ids: tuple[Id, ...] = Field(min_length=1, max_length=50)
    review_date: date
    llm_mode: Literal["off", "cache", "live"] = "off"

    @model_validator(mode="after")
    def validate_references(self):
        records = {r.id: r for r in self.records}
        versions = {v.id: v for v in self.versions}
        if len(records) != len(self.records) or len(versions) != len(self.versions):
            raise ValueError("duplicate record or version ID")
        if len(set(self.target_version_ids)) != len(self.target_version_ids):
            raise ValueError("duplicate target ID")
        if any(r.company_id != self.profile.company_id for r in self.records):
            raise ValueError("mixed company snapshot")
        if any(v.record_id not in records for v in self.versions):
            raise ValueError("version references unknown record")
        if any(v not in versions for v in self.target_version_ids):
            raise ValueError("unknown target version")
        if any(ref not in versions for v in self.versions for ref in v.reference_ids):
            raise ValueError("unknown reference version; represent absent evidence explicitly")
        return self


class RuleEvaluation(Contract):
    rule_snapshots: tuple[Rule, ...] = ()
    clause_snapshots: tuple[ClauseVersion, ...] = ()
    mode: Mode
    rules_checked: tuple[Id, ...] = ()
    skipped_rule_ids: tuple[Id, ...] = ()
    findings: tuple[Finding, ...] = ()
    applicability: Literal["applies", "does_not_apply", "not_enough_information"]
    reason: Text


class DetectionResult(Contract):
    findings: tuple[Finding, ...] = ()
    model_status: Literal["off", "cached", "live", "unavailable"] = "off"
    cache_key: str | None = None


class ValidationRejection(Contract):
    finding_id: Id
    reason: Literal[
        "unknown_rule",
        "unknown_clause",
        "inactive_clause",
        "unverified_rule",
        "quote_mismatch",
        "evidence_mismatch",
        "missing_field_present",
    ]


class ValidationResult(Contract):
    findings: tuple[Finding, ...] = ()
    rejected: tuple[ValidationRejection, ...] = ()


class CheckResult(Contract):
    rule_snapshots: tuple[Rule, ...] = ()
    clause_snapshots: tuple[ClauseVersion, ...] = ()
    id: Id
    mode: Mode
    status: ResultStatus
    summary: Text
    rules_checked: tuple[Id, ...]
    skipped_rule_ids: tuple[Id, ...]
    findings: tuple[Finding, ...]
    snapshot: CheckRequest
    model_status: Literal["off", "cached", "live", "unavailable"]
    created_at: AwareDatetime
    parent_check_id: Id | None = None

    @model_validator(mode="after")
    def validate_summary(self):
        if self.mode == "live":
            if set(self.rules_checked) != {r.id for r in self.rule_snapshots}:
                raise ValueError("live results require exact rule snapshots")
            clauses = {c.id for c in self.clause_snapshots}
            if any(r.clause_version_id not in clauses for r in self.rule_snapshots):
                raise ValueError("live results require clause snapshots")
        if len(set(self.rules_checked)) != len(self.rules_checked):
            raise ValueError("rules counted once")
        if self.status == "no_issue_found":
            expected = f"no issue found under {len(self.rules_checked)} encoded rules"
            if (
                not self.rules_checked
                or self.findings
                or self.skipped_rule_ids
                or self.summary != expected
            ):
                raise ValueError("no-issue wording requires nonempty completed checks")
        return self


class DecisionRequest(Contract):
    check_id: Id
    finding_id: Id
    action: Literal["confirm", "reject", "assign", "close"]
    actor: Literal["reviewer"]
    owner: Literal["marketing", "legal", "document_control"] | None = None
    note: Text
    closure_check_id: Id | None = None

    @model_validator(mode="after")
    def validate_action(self):
        if self.action == "assign" and self.owner is None:
            raise ValueError("assignment requires owner")
        if self.action == "close" and self.closure_check_id is None:
            raise ValueError("closure requires a fresh check")
        return self


class Decision(Contract):
    id: Id
    request: DecisionRequest
    task_status: Literal["open", "assigned", "dismissed", "closed"]
    created_at: AwareDatetime


class ChangeEvent(Contract):
    id: Id
    kind: Literal["record_changed"] = "record_changed"
    record_id: Id
    previous_version_id: Id
    new_version: RecordVersion
    received_at: AwareDatetime

    @model_validator(mode="after")
    def validate_change(self):
        if self.new_version.record_id != self.record_id:
            raise ValueError("change must refer to the same record")
        if self.new_version.id == self.previous_version_id:
            raise ValueError("new version must have a new ID")
        if self.new_version.supersedes != self.previous_version_id:
            raise ValueError("new version must name its predecessor")
        return self


class RecheckItem(Contract):
    id: Id
    event_id: Id
    previous_check_id: Id
    target_version_id: Id
    reason: Literal["direct_dependency", "product_fallback"]
    status: Literal["queued", "completed"]
    new_check_id: Id | None = None


class ChangeResponse(Contract):
    event: ChangeEvent
    queue: tuple[RecheckItem, ...]
    mode: Mode


class RecheckRequest(Contract):
    item_id: Id
    llm_mode: Literal["off", "cache", "live"] = "off"


class HistoryResponse(Contract):
    checks: tuple[CheckResult, ...]
    decisions: tuple[Decision, ...]
    events: tuple[ChangeEvent, ...]
    queue: tuple[RecheckItem, ...]
    mode: Mode


class HealthResponse(Contract):
    status: Literal["ok"] = "ok"
    mode: Mode


class ApiError(Contract):
    code: Literal["not_found", "conflict", "invalid_request", "not_ready"]
    message: Text


class DemoBundle(Contract):
    label: Literal["synthetic/staged"] = "synthetic/staged"
    request: CheckRequest
    preview: CheckResult
    event: ChangeEvent
    rules: tuple[Rule, ...]
    clauses: tuple[ClauseVersion, ...]
