# Hợp đồng LexCheck
v1 — proposal final + quyết định user12:58: toàn bộToday theo tầng. Nguồn thực thi: `contracts/models.py`; JSON Schema được xuất bằng `make schemas`.

## Bất biến
- Python 3.11, FastAPI, Pydantic v2; JSON UTF-8; tên trường snake_case; từ chối trường lạ.
- Ngày hiệu lực dùng `[valid_from, valid_to)`; null = chưa biết ngày kết thúc, không có nghĩa đã xác minh hiệu lực hiện tại. Timestamp ISO 8601 có timezone, lưu UTC, giao diện +07:00.
- Record và phiên bản tách ID; snapshot cũ không sửa. Offset span là Unicode code point, bắt đầu từ 0, end-exclusive trên chuỗi gốc. UI dùng Array.from(text) để cắt span; không dùng offset UTF-16 trực tiếp.
- Record thiếu trong kho kết nối không có nghĩa chưa từng tồn tại. Evidence thiếu trường không có quote. LLM chỉ đưa gợi ý và không đóng task.
- Rule chỉ chạy nếu enabled, verified, clause verified, in_force và đúng khoảng ngày. Bootstrap tắt mọi rule chờ Dũng kiểm.
- Không gửi hồ sơ cá nhân; chỉ company DEMO và product P-01/P-02 tổng hợp. Mọi fixture và màn demo mang `synthetic/staged`.
- `mode=fixture` là preview không phải kiểm luật; job 3 thay service bằng kết quả thật và test `test_live_pipeline_uses_rule_engine` phải chứng minh.

`context_version_ids` chỉ rõ dossier/chứng cứ được người duyệt chọn cho lần kiểm; không dùng ngày mới nhất làm quyền ưu tiên. `reference_ids` là liên kết nguồn của record và không đổi khi recheck.

## Điểm cắm cố định
- Dũng: `rules.engine.evaluate(request: CheckRequest, *, rules=None, clauses=None, patterns=()) -> RuleEvaluation`; tự nạp `rules/catalog.json` và `rules/clauses.json`.
- Tuấn Anh: `detect.service.suggest(request: CheckRequest, evaluation: RuleEvaluation) -> DetectionResult`; `detect.validator.validate_findings(findings, request, rules, clauses) -> ValidationResult`.
- Khanh: `intake.router.router` được đăng ký sẵn trong `app/main.py`; `intake.service` ghép evaluate → suggest → validate, giữ snapshot qua `intake.store`.
- `intake.router.runtime_mode()` trả fixture/live cho health, Khanh sở hữu. Khi ui/dist tồn tại, app tự phục vụ build sau API routes; UI dùng hash navigation.
- UI gọi `/api/*` cùng origin; dev proxy Vite tới `127.0.0.1:8000`; FastAPI phục vụ `ui/dist` sau API routes.
- Không thêm router ở file chung. Không gọi model ngoài `detect/client.py`. Không người nào sửa thư mục của người khác.

## Mã lỗi chung
`{"code":"not_found","message":"Resource not found."}`. HTTP 404: ID không tồn tại; 409: stale version / duplicate ID khác nội dung / chuyển trạng thái sai; 422: schema hoặc reference sai; 503: engine/LLM/tính năng chưa sẵn sàng. Không echo input hoặc secret trong lỗi. Lỗi model không làm hỏng kiểm tất định.

## Model và endpoint
Bảng schema và JSON mẫu đầy đủ được sinh từ model thật ở bước bootstrap bên dưới. Mọi thay đổi phải qua một PR hợp đồng riêng, cả đội đọc trước khi merge.

## Hợp đồng tầng và authorization
FeatureFlags gồm layer0_ready, layer1, layer2, layer3; tầng sau cần tất cả tầng trước. L0 ready lấy từ runtime_mode live. Env LEXCHECK_LAYER1_ENABLED/2/3 mặc định0; /api/features không chứa secret. Endpoint tầng chưa bật trả404 feature_disabled, không gọi model hay đổi state. Không có HTTP endpoint bật flag.
create_app() gọi intake.runtime.configure_app(app) để tạo state/middleware riêng. Header Authorization: Bearer <opaque token> đã khai trong OpenAPI. Tầng0 POST/session chỉ cấp U-MANAGER; decision/change/recheck cần token reviewer do server cấp. Tầng3 mở U-OPS; group và expiry lấy từ token, không tin actor/user_id/group trong request. Account selector chỉ dùng dữ liệu tổng hợp.
Manager xem và tác động mọi demo record. Operations chỉ xem record có access_groups chứa operations và task marketing/document_control; không close, review law, promote Pattern hay đổi ACL. Private ID trả404, action cấm403, thiếu token401. Tầng3 /api/demo chỉ manager; history/checks/chat kiểm toàn bộ nested snapshot/evidence và source trước retrieval/cache. Evaluation chỉ manager. State/key/cache không mount static. ACL trên request không được thay canonical ACL của store.

## Catalog, phiên bản và N
Rule.activities giới hạn advertising/ad_registration; profile unknown trả chưa đủ thông tin. Disabled và rule ngoài phạm vi không thuộc selected set; N chỉ đếm ID rule thực chạy. skipped_rule_ids là rule trong phạm vi cần chạy nhưng thiếu nguồn/evidence hoặc update chưa triển khai; khi đó không báo no_issue_found. R-06..08 không áp nhầm lên marketing thông thường.
RuleEvaluation/CheckResult giữ rule_snapshots, clause_snapshots; result và finding ghi applicability. validator_rejections chỉ ghi ID/mã lý do, không raw secret. context_version_ids do người duyệt chọn, không lấy ngày mới nhất làm quyền ưu tiên. Sửa ma két tạo RecordVersion mới; check mới có parent là check chứa finding đang đóng. Không sửa version/reference cũ.

## Đổi luật và feedback
LegalChangeEvent tách issued_on/effective_on/received_at, label preloaded; effective_on bằng new_clause.valid_from; proposed_rules cite new clause ID. Nạp → pending; chỉ accept sau khi Dũng kiểm nguồn và diễn giải. Activation cần accepted, verified, ngày hiệu lực đã tới theo review_date và ngày hệ thống. Lưu overlay runtime, không ghi ngược rules/catalog.json. HistoryResponse giữ legal_changes riêng với record events; RecheckItem.reason có legal_dependency và dedup chung. Biết có update đã effective nhưng chưa triển khai thì manual/not_enough_information; không dùng rule cũ để báo sạch. Giấy xác nhận cũ không tự mất giá trị.
FeedbackRequest phải trỏ decision confirm thật, phrase phải có trong evidence. Tạo Pattern candidate chưa đổi kết quả. Manager review gọi guard tests trong rules; server tạo report hash; chỉ active khi guard pass và căn cứ còn hiệu lực. Scope gồm company/pack/rule_version/clause_version/access_groups; đổi luật suspend Pattern liên quan. CheckResult.pattern_ids_used và Finding.pattern_id chứng minh reuse. POST/check tạo kết quả mới cho ca tương tự, giữ old/new; feedback không tự đóng task.

## Điểm cắm bổ sung
- Dũng: rules.impact.enqueue(event, checks) → tuple[RecheckItem,...]; apply_event(snapshot,event) → CheckRequest; rules.legal.validate_activation(state, review_date) → tuple[Rule,...]; affected_checks(event,checks) → tuple[RecheckItem,...]; rules.patterns.review(pattern,cases) → Pattern. Caller cung cấp reviewer từ session; pure function không tự cấp quyền.
- Tuấn Anh: detect.chat.answer(request: ChatRequest, check: CheckResult) → ChatResponse. Chỉ đọc snapshot đã authorize; citation quote có trong clause version đó. Không đủ căn cứ → needs_evidence. Model call qua detect/client.py, structured outputs; refusal/timeout trả unavailable, không đoán. [SDK guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).
- Khanh: intake/layer_routes.py đã mount; runtime.py giữ state/auth; features.py đọc flag. GET/evaluation đọc EvaluationReport thật từ eval/results/latest.json; chưa đo trả phase bootstrap/n0. UI cùng origin; app tự mount ui/dist khi có.
- make smoke LAYER=N chỉ bật prerequisite flags trong tiến trình test, không đổi deployment. make smoke auto dùng flag hiện tại. Explicit gate phải lỗi nếu chưa live hoặc chưa có test. PR UI đầu thêm package-lock; CI tự bật frontend checks.

## Lỗi và JSON
DTO đầy đủ được sinh từ model/fixture phía dưới. Model frozen, extra=forbid; null/default thể hiện trong schema. Datetime có timezone; date YYYY-MM-DD. Lỗi422 không echo input. ApiError codes: not_found, conflict, invalid_request, not_ready, unauthenticated, forbidden, feature_disabled. Lỗi nguồn phải có câu “could not confirm updates from this source”, giữ trạng thái chưa xác nhận; không suy “no changes”. Chữ sản phẩm tuân theo AGENTS.md.

<!-- generated-contracts -->

## Endpoint cố định (v1)
| Method/path | Request | Response thành công | Tầng | Bootstrap |
|---|---|---|---|---|
| GET /health | không | HealthResponse, 200 | all | fixture |
| GET /api/demo | không | DemoBundle, 200 | 0 | fixture thật trên đĩa |
| POST /api/check | CheckRequest | CheckResult, 200 | 0 | chỉ request demo; khác input → 503 |
| POST /api/changes | ChangeEvent | ChangeResponse, 200 | 0 | 503 chưa có store |
| POST /api/rechecks | RecheckRequest | CheckResult, 200 | 0 | 503 chưa có engine |
| POST /api/decisions | DecisionRequest | Decision, 201 | 0 | 503 chưa có store |
| GET /api/history | không | HistoryResponse, 200 | 0 | preview, arrays còn lại rỗng |
| GET /api/features | none | FeatureFlags, 200 | all | false flags |
| POST /api/session | DemoLoginRequest | DemoSession, 200 | 0 / operations at 3 | 503 pending |
| GET /api/records | none | RecordsResponse, 200 | 0 | 503 pending |
| GET /api/checks/{check_id} | none | CheckResult, 200 | 0 | 503 pending |
| POST /api/chat | ChatRequest | ChatResponse, 200 | 1 | 404 feature_disabled |
| GET /api/evaluation | none | EvaluationReport, 200 | 1 | 404 feature_disabled |
| POST /api/legal-changes | LegalChangeEvent | LegalChangeResponse, 200 | 2 | 404 feature_disabled |
| POST /api/legal-changes/{event_id}/review | LegalReviewRequest | LegalChangeResponse, 200 | 2 | 404 feature_disabled |
| POST /api/legal-changes/{event_id}/activate | LegalActivationRequest | LegalChangeResponse, 200 | 2 | 404 feature_disabled |
| POST /api/feedback | FeedbackRequest | PatternResponse, 200 | 3 | 404 feature_disabled |
| POST /api/patterns/{pattern_id}/review | PatternReviewRequest | PatternResponse, 200 | 3 | 404 feature_disabled |


`/openapi.json` và `/docs` là tài liệu FastAPI. API thành công trả trực tiếp typed model; lỗi trả ApiError (không bọc detail). GET sai path → 404. Tất cả POST có 422 input; feature pending → 503. Bản live: ID/version không tồn tại → 404, trùng ID khác payload/stale/closure chưa recheck →409. Không đổi HTTP shape khi thay adapter fixture.

ID: CO-DEMO công ty; P-01 sản phẩm; REC-01 record; RV-01-v1 version; CL-01 clause; CV-01-v1 clause version; R-01 rule; F-<check suffix>-01 finding; CHK-<uuid> check; DEC-<uuid> decision; EV-<uuid> event; RQ-<uuid> queue. Regex Id chỉ ràng buộc cú pháp; prefix và quan hệ được service kiểm. Check và finding do server tạo; event ID do client tạo để retry idempotent. Cùng event ID + cùng nội dung trả response cũ; khác nội dung 409.

File rule/catalog và clauses là JSON array của Rule/ClauseVersion. Snapshot request là CheckRequest JSON. `uses` là dữ kiện fixture đã gán nhãn, không tự coi là kết quả trích xuất ngôn ngữ tự do. Lưu text gốc; validate mọi use có mặt trong text khi nạp live; trường rỗng không suy “không có claim”.

## Quy tắc nghiệp vụ cần hiện thực
POST check lưu CheckResult + snapshot bất biến. Mỗi target quảng cáo chạy subset rule theo profile, ngày, nguồn. N = số rule ID duy nhất thực chạy; skipped có ID và giải thích qua applicability, không được no_issue_found. LLM findings status suggestion/needs_evidence.
POST changes append version; tìm mọi check từng phụ thuộc dossier cũ, kể cả check không findings. Xét reference_ids và product fallback; queue unique (event_id, previous_check_id, target_version_id), không đưa sản phẩm khác vào. Event không sửa snapshot cũ.
POST rechecks dùng snapshot cũ, append dossier v2, đổi context_version_ids từ v1 sang v2, giữ nguyên text/reference_ids của mọi RecordVersion cũ; tạo check mới có parent_check_id. History giữ cả hai. Recheck cùng item đã completed trả check cũ.
POST decisions confirm/assign không đóng task; reject cần note và task dismissed. close cần closure_check_id có parent đúng, target đúng và không còn finding liên quan/chưa rõ; trường hợp vẫn thiếu chứng cứ trả409. Tầng0 chỉ U-MANAGER có reviewer token; tầng3 thêm phân quyền hai nhóm. Actor trong body không cấp quyền.

## Toàn bộ model (khớp từng chữ với source)
```python
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
    action: Literal["confirm", "reject", "assign", "acknowledge", "close"]
    actor: Literal["reviewer"]
    owner: Literal["marketing", "legal", "document_control"] | None = None
    note: Text
    closure_check_id: Id | None = None
    internal_due_on: date | None = None
    legal_due_on: date | None = None
    legal_clause_version_id: Id | None = None
    legal_deadline_quote: Text | None = None
    closure_conditions: Text | None = None
    closure_conditions_met: bool = False

    @model_validator(mode="after")
    def validate_action(self):
        if self.action == "assign" and self.owner is None:
            raise ValueError("assignment requires owner")
        if self.action == "close" and self.closure_check_id is None:
            raise ValueError("closure requires a fresh check")
        legal = (self.legal_due_on, self.legal_clause_version_id, self.legal_deadline_quote)
        if any(value is not None for value in legal) and not all(
            value is not None for value in legal
        ):
            raise ValueError("legal deadline requires a date, clause version and quote")
        if self.closure_conditions_met and self.action != "close":
            raise ValueError("closure conditions can only be confirmed while closing")
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
    remediation: bool = False
    task_dashboard: bool = False

    @model_validator(mode="after")
    def validate_order(self):
        if (
            (self.layer1 and not self.layer0_ready)
            or (self.layer2 and not self.layer1)
            or (self.layer3 and not self.layer2)
            or (self.remediation and not self.layer0_ready)
            or (self.task_dashboard and not self.remediation)
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
```

## JSON mẫu request/response
GET /api/demo = data/fixtures/demo.json (đầy đủ, kiểm bằng test); POST /api/check request:
```json
{
  "profile": {
    "company_id": "CO-DEMO",
    "product_group": "tpbvsk",
    "activity": "advertising",
    "role": "domestic_distributor",
    "confirmed": true,
    "synthetic": true
  },
  "records": [
    {
      "id": "REC-01",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "dossier",
      "title": "Synthetic dossier",
      "access_groups": [
        "manager",
        "operations"
      ],
      "synthetic": true
    },
    {
      "id": "REC-02",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "marketing",
      "title": "Synthetic marketing",
      "access_groups": [
        "manager",
        "operations"
      ],
      "synthetic": true
    },
    {
      "id": "REC-03",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "marketing",
      "title": "Synthetic marketing control",
      "access_groups": [
        "manager",
        "operations"
      ],
      "synthetic": true
    },
    {
      "id": "REC-04",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "ad_confirmation",
      "title": "Synthetic confirmation index; no official certificate",
      "access_groups": [
        "manager",
        "operations"
      ],
      "synthetic": true
    },
    {
      "id": "REC-05",
      "company_id": "CO-DEMO",
      "product_id": "P-02",
      "kind": "marketing",
      "title": "Unrelated product control",
      "access_groups": [
        "manager",
        "operations"
      ],
      "synthetic": true
    }
  ],
  "versions": [
    {
      "id": "RV-01-v1",
      "record_id": "REC-01",
      "version": 1,
      "text": "Hỗ trợ tiêu hóa.\nHỗ trợ giảm cholesterol.",
      "uses": [
        "Hỗ trợ tiêu hóa.",
        "Hỗ trợ giảm cholesterol."
      ],
      "reference_ids": [],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": null
    },
    {
      "id": "RV-02-v1",
      "record_id": "REC-02",
      "version": 1,
      "text": "Hỗ trợ tiêu hóa.\nHỗ trợ giảm cholesterol.\nThực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
      "uses": [
        "Hỗ trợ tiêu hóa.",
        "Hỗ trợ giảm cholesterol."
      ],
      "reference_ids": [
        "RV-01-v1",
        "RV-04-v1"
      ],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": null
    },
    {
      "id": "RV-03-v1",
      "record_id": "REC-03",
      "version": 1,
      "text": "Hỗ trợ tiêu hóa.\nThực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
      "uses": [
        "Hỗ trợ tiêu hóa."
      ],
      "reference_ids": [
        "RV-01-v1",
        "RV-04-v1"
      ],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": null
    },
    {
      "id": "RV-04-v1",
      "record_id": "REC-04",
      "version": 1,
      "text": "Synthetic index links marketing RV-02-v1. No official receipt or certificate is reproduced.",
      "uses": [],
      "reference_ids": [],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": null
    },
    {
      "id": "RV-05-v1",
      "record_id": "REC-05",
      "version": 1,
      "text": "Thực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
      "uses": [],
      "reference_ids": [],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": null
    }
  ],
  "target_version_ids": [
    "RV-02-v1",
    "RV-03-v1"
  ],
  "context_version_ids": [
    "RV-01-v1",
    "RV-04-v1"
  ],
  "review_date": "2026-10-31",
  "llm_mode": "off"
}
```
Response /api/check (preview):
```json
{
  "pattern_ids_used": [],
  "validator_rejections": [],
  "rule_snapshots": [],
  "clause_snapshots": [],
  "id": "CHK-preview",
  "mode": "fixture",
  "status": "not_enough_information",
  "summary": "Synthetic fixture preview; legal rules await source verification.",
  "rules_checked": [],
  "skipped_rule_ids": [
    "R-01",
    "R-02",
    "R-03",
    "R-04",
    "R-05",
    "R-06",
    "R-07",
    "R-08"
  ],
  "findings": [],
  "snapshot": {
    "profile": {
      "company_id": "CO-DEMO",
      "product_group": "tpbvsk",
      "activity": "advertising",
      "role": "domestic_distributor",
      "confirmed": true,
      "synthetic": true
    },
    "records": [
      {
        "id": "REC-01",
        "company_id": "CO-DEMO",
        "product_id": "P-01",
        "kind": "dossier",
        "title": "Synthetic dossier",
        "access_groups": [
          "manager",
          "operations"
        ],
        "synthetic": true
      },
      {
        "id": "REC-02",
        "company_id": "CO-DEMO",
        "product_id": "P-01",
        "kind": "marketing",
        "title": "Synthetic marketing",
        "access_groups": [
          "manager",
          "operations"
        ],
        "synthetic": true
      },
      {
        "id": "REC-03",
        "company_id": "CO-DEMO",
        "product_id": "P-01",
        "kind": "marketing",
        "title": "Synthetic marketing control",
        "access_groups": [
          "manager",
          "operations"
        ],
        "synthetic": true
      },
      {
        "id": "REC-04",
        "company_id": "CO-DEMO",
        "product_id": "P-01",
        "kind": "ad_confirmation",
        "title": "Synthetic confirmation index; no official certificate",
        "access_groups": [
          "manager",
          "operations"
        ],
        "synthetic": true
      },
      {
        "id": "REC-05",
        "company_id": "CO-DEMO",
        "product_id": "P-02",
        "kind": "marketing",
        "title": "Unrelated product control",
        "access_groups": [
          "manager",
          "operations"
        ],
        "synthetic": true
      }
    ],
    "versions": [
      {
        "id": "RV-01-v1",
        "record_id": "REC-01",
        "version": 1,
        "text": "Hỗ trợ tiêu hóa.\nHỗ trợ giảm cholesterol.",
        "uses": [
          "Hỗ trợ tiêu hóa.",
          "Hỗ trợ giảm cholesterol."
        ],
        "reference_ids": [],
        "received_at": "2026-10-31T05:00:00Z",
        "confirmation_date": null,
        "issuing_authority": "unknown",
        "supersedes": null
      },
      {
        "id": "RV-02-v1",
        "record_id": "REC-02",
        "version": 1,
        "text": "Hỗ trợ tiêu hóa.\nHỗ trợ giảm cholesterol.\nThực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
        "uses": [
          "Hỗ trợ tiêu hóa.",
          "Hỗ trợ giảm cholesterol."
        ],
        "reference_ids": [
          "RV-01-v1",
          "RV-04-v1"
        ],
        "received_at": "2026-10-31T05:00:00Z",
        "confirmation_date": null,
        "issuing_authority": "unknown",
        "supersedes": null
      },
      {
        "id": "RV-03-v1",
        "record_id": "REC-03",
        "version": 1,
        "text": "Hỗ trợ tiêu hóa.\nThực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
        "uses": [
          "Hỗ trợ tiêu hóa."
        ],
        "reference_ids": [
          "RV-01-v1",
          "RV-04-v1"
        ],
        "received_at": "2026-10-31T05:00:00Z",
        "confirmation_date": null,
        "issuing_authority": "unknown",
        "supersedes": null
      },
      {
        "id": "RV-04-v1",
        "record_id": "REC-04",
        "version": 1,
        "text": "Synthetic index links marketing RV-02-v1. No official receipt or certificate is reproduced.",
        "uses": [],
        "reference_ids": [],
        "received_at": "2026-10-31T05:00:00Z",
        "confirmation_date": null,
        "issuing_authority": "unknown",
        "supersedes": null
      },
      {
        "id": "RV-05-v1",
        "record_id": "REC-05",
        "version": 1,
        "text": "Thực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
        "uses": [],
        "reference_ids": [],
        "received_at": "2026-10-31T05:00:00Z",
        "confirmation_date": null,
        "issuing_authority": "unknown",
        "supersedes": null
      }
    ],
    "target_version_ids": [
      "RV-02-v1",
      "RV-03-v1"
    ],
    "context_version_ids": [
      "RV-01-v1",
      "RV-04-v1"
    ],
    "review_date": "2026-10-31",
    "llm_mode": "off"
  },
  "model_status": "off",
  "created_at": "2026-10-31T05:00:00Z",
  "applicability": "not_enough_information",
  "applicability_reason": "Applicability awaits review.",
  "parent_check_id": null
}
```
POST /api/changes request:
```json
{
  "id": "EV-01",
  "kind": "record_changed",
  "record_id": "REC-01",
  "previous_version_id": "RV-01-v1",
  "new_version": {
    "id": "RV-01-v2",
    "record_id": "REC-01",
    "version": 2,
    "text": "Hỗ trợ tiêu hóa.",
    "uses": [
      "Hỗ trợ tiêu hóa."
    ],
    "reference_ids": [],
    "received_at": "2026-10-31T05:00:00Z",
    "confirmation_date": null,
    "issuing_authority": "unknown",
    "supersedes": "RV-01-v1"
  },
  "received_at": "2026-10-31T05:00:00Z"
}
```
Response changes live (ví dụ queue, không phải kết quả bootstrap):
```json
{
  "event": {
    "id": "EV-01",
    "kind": "record_changed",
    "record_id": "REC-01",
    "previous_version_id": "RV-01-v1",
    "new_version": {
      "id": "RV-01-v2",
      "record_id": "REC-01",
      "version": 2,
      "text": "Hỗ trợ tiêu hóa.",
      "uses": [
        "Hỗ trợ tiêu hóa."
      ],
      "reference_ids": [],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": "RV-01-v1"
    },
    "received_at": "2026-10-31T05:00:00Z"
  },
  "mode": "live",
  "queue": [
    {
      "id": "RQ-01",
      "event_id": "EV-01",
      "previous_check_id": "CHK-01",
      "target_version_id": "RV-02-v1",
      "reason": "direct_dependency",
      "status": "queued",
      "new_check_id": null
    }
  ]
}
```
POST /api/rechecks request; response cùng CheckResult ở trên, ID mới và parent_check_id cũ:
```json
{
  "item_id": "RQ-01",
  "llm_mode": "off"
}
```
POST /api/decisions request:
```json
{
  "check_id": "CHK-01",
  "finding_id": "F-01",
  "action": "assign",
  "actor": "reviewer",
  "owner": "marketing",
  "note": "Please supply connected evidence.",
  "closure_check_id": null
}
```
Response decision live:
```json
{
  "id": "DEC-01",
  "request": {
    "check_id": "CHK-01",
    "finding_id": "F-01",
    "action": "assign",
    "actor": "reviewer",
    "owner": "marketing",
    "note": "Please supply connected evidence.",
    "closure_check_id": null
  },
  "task_status": "assigned",
  "created_at": "2026-10-31T07:00:00Z"
}
```
GET /api/history shape (live trống):
```json
{
  "checks": [],
  "decisions": [],
  "events": [],
  "queue": [],
  "mode": "live"
}
```
GET /health:
```json
{
  "status": "ok",
  "mode": "fixture"
}
```

## JSON mẫu các tầng bổ sung
Các ví dụ là typed fixture; không giả kết quả live. CheckResult example dùng preview ở trên. Server kiểm Authorization theo tầng.

### FeatureFlags JSON mẫu
```json
{
  "layer0_ready": false,
  "layer1": false,
  "layer2": false,
  "layer3": false
}
```

### DemoLoginRequest JSON mẫu
```json
{
  "user_id": "U-MANAGER"
}
```

### DemoSession JSON mẫu
```json
{
  "user_id": "U-MANAGER",
  "group": "manager",
  "token": "synthetic-fixture-session-only",
  "expires_at": "2026-10-31T17:00:00Z"
}
```

### RecordsResponse JSON mẫu
```json
{
  "records": [
    {
      "id": "REC-01",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "dossier",
      "title": "Synthetic dossier",
      "access_groups": [
        "manager",
        "operations"
      ],
      "synthetic": true
    },
    {
      "id": "REC-02",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "marketing",
      "title": "Synthetic marketing",
      "access_groups": [
        "manager",
        "operations"
      ],
      "synthetic": true
    },
    {
      "id": "REC-03",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "marketing",
      "title": "Synthetic marketing control",
      "access_groups": [
        "manager",
        "operations"
      ],
      "synthetic": true
    },
    {
      "id": "REC-04",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "ad_confirmation",
      "title": "Synthetic confirmation index; no official certificate",
      "access_groups": [
        "manager",
        "operations"
      ],
      "synthetic": true
    },
    {
      "id": "REC-05",
      "company_id": "CO-DEMO",
      "product_id": "P-02",
      "kind": "marketing",
      "title": "Unrelated product control",
      "access_groups": [
        "manager",
        "operations"
      ],
      "synthetic": true
    }
  ],
  "versions": [
    {
      "id": "RV-01-v1",
      "record_id": "REC-01",
      "version": 1,
      "text": "Hỗ trợ tiêu hóa.\nHỗ trợ giảm cholesterol.",
      "uses": [
        "Hỗ trợ tiêu hóa.",
        "Hỗ trợ giảm cholesterol."
      ],
      "reference_ids": [],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": null
    },
    {
      "id": "RV-02-v1",
      "record_id": "REC-02",
      "version": 1,
      "text": "Hỗ trợ tiêu hóa.\nHỗ trợ giảm cholesterol.\nThực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
      "uses": [
        "Hỗ trợ tiêu hóa.",
        "Hỗ trợ giảm cholesterol."
      ],
      "reference_ids": [
        "RV-01-v1",
        "RV-04-v1"
      ],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": null
    },
    {
      "id": "RV-03-v1",
      "record_id": "REC-03",
      "version": 1,
      "text": "Hỗ trợ tiêu hóa.\nThực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
      "uses": [
        "Hỗ trợ tiêu hóa."
      ],
      "reference_ids": [
        "RV-01-v1",
        "RV-04-v1"
      ],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": null
    },
    {
      "id": "RV-04-v1",
      "record_id": "REC-04",
      "version": 1,
      "text": "Synthetic index links marketing RV-02-v1. No official receipt or certificate is reproduced.",
      "uses": [],
      "reference_ids": [],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": null
    },
    {
      "id": "RV-05-v1",
      "record_id": "REC-05",
      "version": 1,
      "text": "Thực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.",
      "uses": [],
      "reference_ids": [],
      "received_at": "2026-10-31T05:00:00Z",
      "confirmation_date": null,
      "issuing_authority": "unknown",
      "supersedes": null
    }
  ]
}
```

### ChatRequest JSON mẫu
```json
{
  "check_id": "CHK-finding-preview",
  "question": "Cần bổ sung hồ sơ nào?"
}
```

### ChatResponse JSON mẫu
```json
{
  "status": "needs_evidence",
  "answer": "Source verification is pending.",
  "citations": [],
  "model_status": "off"
}
```

### LegalChangeEvent JSON mẫu
```json
{
  "id": "EV-L01",
  "kind": "law_changed",
  "label": "preloaded",
  "previous_clause_version_id": "CV-07-v1",
  "new_clause": {
    "id": "CV-07-v2",
    "clause_id": "CL-07",
    "document": "NQ 21/2026/NQ-CP",
    "article": "2(1)(a), 6(2)",
    "text": "SOURCE TEXT PENDING VERIFICATION: NQ 21/2026 Article 2(1)(a).",
    "source_url": "https://xdcs.cdnchinhphu.vn/446259493575335936/2026/5/5/21-nqcp-signed-1777970679563128188225.pdf",
    "source_sha256": null,
    "retrieved_at": "2026-10-31T06:00:00Z",
    "valid_from": "2026-07-01",
    "valid_to": "2028-01-01",
    "verification_status": "to_be_verified",
    "in_force": "unknown",
    "verified_by": null,
    "verified_at": null,
    "status_note": "Preloaded historical update; rule owner must verify text and dates."
  },
  "proposed_rules": [
    {
      "id": "R-07",
      "version": 2,
      "clause_version_id": "CV-07-v2",
      "title": "Confirmation authority review",
      "check_type": "authority_review",
      "activities": [
        "ad_registration"
      ],
      "method": "deterministic",
      "severity": "medium",
      "verification_status": "to_be_verified",
      "enabled": false,
      "patterns": [],
      "positive_examples": [],
      "negative_examples": []
    }
  ],
  "issued_on": "2026-04-29",
  "effective_on": "2026-07-01",
  "received_at": "2026-10-31T06:00:00Z"
}
```

### LegalReviewRequest JSON mẫu
```json
{
  "action": "accept",
  "note": "Review original text and effective dates before acceptance."
}
```

### LegalActivationRequest JSON mẫu
```json
{
  "review_date": "2026-10-31"
}
```

### LegalChangeResponse JSON mẫu
```json
{
  "state": {
    "event": {
      "id": "EV-L01",
      "kind": "law_changed",
      "label": "preloaded",
      "previous_clause_version_id": "CV-07-v1",
      "new_clause": {
        "id": "CV-07-v2",
        "clause_id": "CL-07",
        "document": "NQ 21/2026/NQ-CP",
        "article": "2(1)(a), 6(2)",
        "text": "SOURCE TEXT PENDING VERIFICATION: NQ 21/2026 Article 2(1)(a).",
        "source_url": "https://xdcs.cdnchinhphu.vn/446259493575335936/2026/5/5/21-nqcp-signed-1777970679563128188225.pdf",
        "source_sha256": null,
        "retrieved_at": "2026-10-31T06:00:00Z",
        "valid_from": "2026-07-01",
        "valid_to": "2028-01-01",
        "verification_status": "to_be_verified",
        "in_force": "unknown",
        "verified_by": null,
        "verified_at": null,
        "status_note": "Preloaded historical update; rule owner must verify text and dates."
      },
      "proposed_rules": [
        {
          "id": "R-07",
          "version": 2,
          "clause_version_id": "CV-07-v2",
          "title": "Confirmation authority review",
          "check_type": "authority_review",
          "activities": [
            "ad_registration"
          ],
          "method": "deterministic",
          "severity": "medium",
          "verification_status": "to_be_verified",
          "enabled": false,
          "patterns": [],
          "positive_examples": [],
          "negative_examples": []
        }
      ],
      "issued_on": "2026-04-29",
      "effective_on": "2026-07-01",
      "received_at": "2026-10-31T06:00:00Z"
    },
    "interpretation": "pending",
    "reviewed_by": null,
    "reviewed_at": null,
    "activated_at": null,
    "status": "pending"
  },
  "queue": [],
  "mode": "fixture"
}
```

### FeedbackRequest JSON mẫu
```json
{
  "decision_id": "DEC-01",
  "phrase": "Hỗ trợ giấc ngủ.",
  "polarity": "positive"
}
```

### PatternReviewRequest JSON mẫu
```json
{
  "action": "accept",
  "note": "Run positive and clean guard cases before activation."
}
```

### PatternResponse JSON mẫu
```json
{
  "pattern": {
    "id": "PAT-01",
    "company_id": "CO-DEMO",
    "pack": "tpbvsk",
    "source_decision_id": "DEC-01",
    "rule_id": "R-02",
    "rule_version": 1,
    "clause_version_id": "CV-02-v1",
    "phrase": "Hỗ trợ giấc ngủ.",
    "polarity": "positive",
    "state": "candidate",
    "test_report_sha256": null,
    "reviewed_by": null,
    "access_groups": [
      "manager"
    ]
  },
  "mode": "fixture"
}
```

### EvaluationReport JSON mẫu
```json
{
  "phase": "bootstrap",
  "n": 0,
  "git_sha": null,
  "dataset_sha256": null,
  "model": null,
  "rule_ids": [],
  "systems": [],
  "note": "No model performance measured."
}
```
