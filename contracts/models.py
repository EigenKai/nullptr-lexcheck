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
    activity: Literal["advertising", "ad_registration", "label_only", "unknown"]
    role: Literal["domestic_distributor", "producer", "importer", "unknown"]
    confirmed: bool
    synthetic: Literal[True] = True


class Record(Contract):
    id: Id
    company_id: Id
    product_id: Id
    kind: Literal[
        "dossier",
        "marketing",
        "customer_script",
        "evidence_index",
        "scientific_evidence",
        "label",
        "registration_receipt",
        "ad_confirmation",
    ]
    title: Text
    access_groups: tuple[Literal["manager", "operations"], ...] = ("manager", "operations")
    synthetic: Literal[True] = True


class RecordVersion(Contract):
    id: Id
    record_id: Id
    version: int = Field(ge=1)
    text: str = Field(max_length=20000)
    uses: tuple[Text, ...] = ()
    reference_ids: tuple[Id, ...] = ()
    received_at: AwareDatetime
    confirmation_date: date | None = None
    issuing_authority: Literal["national_food_admin", "provincial_chair", "unknown"] = "unknown"
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
    check_type: Literal[
        "warning",
        "uses",
        "confirmation",
        "endorsement",
        "medicinal",
        "receipt",
        "authority_review",
        "label_copy",
    ]
    activities: tuple[Literal["advertising", "ad_registration"], ...] = ("advertising",)
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
    pattern_id: Id | None = None
    id: Id
    rule_id: Id
    rule_version: int = Field(ge=1)
    clause_version_id: Id
    record_version_id: Id
    applicability: Literal["applies", "not_enough_information"] = "applies"
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
    context_version_ids: tuple[Id, ...] = ()
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
        if len(set(self.context_version_ids)) != len(self.context_version_ids):
            raise ValueError("duplicate context version")
        if any(v not in versions for v in self.context_version_ids):
            raise ValueError("unknown context version")
        if set(self.context_version_ids) & set(self.target_version_ids):
            raise ValueError("context and targets must be distinct")
        selected_records = tuple(versions[v].record_id for v in self.context_version_ids)
        if len(set(selected_records)) != len(selected_records):
            raise ValueError("choose one authoritative version per context record")
        if any(ref not in versions for v in self.versions for ref in v.reference_ids):
            raise ValueError("unknown reference version; represent absent evidence explicitly")
        return self


class RuleEvaluation(Contract):
    pattern_ids_used: tuple[Id, ...] = ()
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
    pattern_ids_used: tuple[Id, ...] = ()
    validator_rejections: tuple[ValidationRejection, ...] = ()
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
    applicability: Literal["applies", "does_not_apply", "not_enough_information"] = (
        "not_enough_information"
    )
    applicability_reason: Text = "Applicability awaits review."
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
    actor_user_id: Id = "U-MANAGER"
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
    reason: Literal["direct_dependency", "product_fallback", "legal_dependency"]
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
    legal_changes: tuple["LegalChangeState", ...] = ()
    patterns: tuple["Pattern", ...] = ()
    checks: tuple[CheckResult, ...]
    decisions: tuple[Decision, ...]
    events: tuple[ChangeEvent, ...]
    queue: tuple[RecheckItem, ...]
    mode: Mode


class HealthResponse(Contract):
    status: Literal["ok"] = "ok"
    mode: Mode


class ApiError(Contract):
    code: Literal[
        "not_found",
        "conflict",
        "invalid_request",
        "not_ready",
        "unauthenticated",
        "forbidden",
        "feature_disabled",
    ]
    message: Text


class DemoBundle(Contract):
    label: Literal["synthetic/staged"] = "synthetic/staged"
    request: CheckRequest
    preview: CheckResult
    event: ChangeEvent
    rules: tuple[Rule, ...]
    clauses: tuple[ClauseVersion, ...]


class FeatureFlags(Contract):
    layer0_ready: bool = False
    layer1: bool = False
    layer2: bool = False
    layer3: bool = False

    @model_validator(mode="after")
    def validate_order(self):
        if (
            (self.layer1 and not self.layer0_ready)
            or (self.layer2 and not self.layer1)
            or (self.layer3 and not self.layer2)
        ):
            raise ValueError("later layers require all prior layers")
        return self


class DemoLoginRequest(Contract):
    user_id: Literal["U-MANAGER", "U-OPS"]


class DemoSession(Contract):
    user_id: Literal["U-MANAGER", "U-OPS"]
    group: Literal["manager", "operations"]
    token: str = Field(min_length=20)
    expires_at: AwareDatetime


class RecordsResponse(Contract):
    records: tuple[Record, ...]
    versions: tuple[RecordVersion, ...]


class ChatRequest(Contract):
    check_id: Id
    question: str = Field(min_length=1, max_length=1000)


class ChatCitation(Contract):
    clause_version_id: Id
    quote: Text
    evidence: Evidence | None = None


class ChatResponse(Contract):
    status: Literal["answered", "needs_evidence"]
    answer: Text
    citations: tuple[ChatCitation, ...]
    model_status: Literal["off", "cached", "live", "unavailable"] = "off"

    @model_validator(mode="after")
    def validate_citations(self):
        if self.status == "answered" and not self.citations:
            raise ValueError("answered chat requires citations")
        return self


class LegalChangeEvent(Contract):
    id: Id
    kind: Literal["law_changed"] = "law_changed"
    label: Literal["preloaded"] = "preloaded"
    previous_clause_version_id: Id
    new_clause: ClauseVersion
    proposed_rules: tuple[Rule, ...] = Field(min_length=1)
    issued_on: date
    effective_on: date
    received_at: AwareDatetime

    @model_validator(mode="after")
    def validate_legal_change(self):
        if self.new_clause.id == self.previous_clause_version_id:
            raise ValueError("new clause needs a new version ID")
        if self.effective_on != self.new_clause.valid_from:
            raise ValueError("event date must match clause effective date")
        if any(r.clause_version_id != self.new_clause.id for r in self.proposed_rules):
            raise ValueError("proposed rules must cite the new clause")
        return self


class LegalReviewRequest(Contract):
    action: Literal["accept", "reject"]
    note: Text


class LegalActivationRequest(Contract):
    review_date: date


class LegalChangeState(Contract):
    event: LegalChangeEvent
    interpretation: Literal["pending", "accepted", "rejected"] = "pending"
    reviewed_by: Id | None = None
    reviewed_at: AwareDatetime | None = None
    activated_at: AwareDatetime | None = None
    status: Literal["pending", "ready", "active", "rejected"] = "pending"


class LegalChangeResponse(Contract):
    state: LegalChangeState
    queue: tuple[RecheckItem, ...] = ()
    mode: Mode


class FeedbackRequest(Contract):
    decision_id: Id
    phrase: Text
    polarity: Literal["positive", "negative"]


class Pattern(Contract):
    id: Id
    company_id: Id
    pack: Literal["tpbvsk"] = "tpbvsk"
    source_decision_id: Id
    rule_id: Id
    rule_version: int = Field(ge=1)
    clause_version_id: Id
    phrase: Text
    polarity: Literal["positive", "negative"]
    state: Literal["candidate", "active", "rejected", "suspended"] = "candidate"
    test_report_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    reviewed_by: Id | None = None
    access_groups: tuple[Literal["manager", "operations"], ...] = ("manager",)

    @model_validator(mode="after")
    def validate_promotion(self):
        if self.state == "active" and not (self.test_report_sha256 and self.reviewed_by):
            raise ValueError("active pattern needs reviewer and test report")
        return self


class PatternReviewRequest(Contract):
    action: Literal["accept", "reject"]
    note: Text


class PatternResponse(Contract):
    pattern: Pattern
    mode: Mode


class SystemScore(Contract):
    system: Literal["keyword", "plain_chat", "lexcheck"]
    evaluated_cases: int = Field(ge=0)
    true_positive: int = Field(ge=0)
    false_positive: int = Field(ge=0)
    false_negative: int = Field(ge=0)
    false_flags_on_clean: int = Field(ge=0)
    precision: float | None = Field(default=None, ge=0, le=1)
    recall: float | None = Field(default=None, ge=0, le=1)
    model_calls: int = Field(ge=0)
    failed_calls: int = Field(ge=0)
    latency_ms: float | None = Field(default=None, ge=0)


class EvaluationReport(Contract):
    phase: Literal["bootstrap", "dev", "held_out"]
    n: int = Field(ge=0)
    git_sha: str | None = None
    dataset_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    model: str | None = None
    rule_ids: tuple[Id, ...] = ()
    systems: tuple[SystemScore, ...] = ()
    note: Text


HistoryResponse.model_rebuild()
