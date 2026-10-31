# Hợp đồng LexCheck
v0 — trước proposal final. Nguồn thực thi: `contracts/models.py`; JSON Schema được xuất bằng `make schemas`.

## Bất biến
- Python 3.11, FastAPI, Pydantic v2; JSON UTF-8; tên trường snake_case; từ chối trường lạ.
- Ngày hiệu lực dùng `[valid_from, valid_to)`; null = chưa biết ngày kết thúc, không có nghĩa đã xác minh hiệu lực hiện tại. Timestamp ISO 8601 có timezone, lưu UTC, giao diện +07:00.
- Record và phiên bản tách ID; snapshot cũ không sửa. Offset span là Unicode code point, bắt đầu từ 0, end-exclusive trên chuỗi gốc. UI dùng Array.from(text) để cắt span; không dùng offset UTF-16 trực tiếp.
- Record thiếu trong kho kết nối không có nghĩa chưa từng tồn tại. Evidence thiếu trường không có quote. LLM chỉ đưa gợi ý và không đóng task.
- Rule chỉ chạy nếu enabled, verified, clause verified, in_force và đúng khoảng ngày. Bootstrap tắt mọi rule chờ Dũng kiểm.
- Không gửi hồ sơ cá nhân; chỉ company DEMO và product P-01/P-02 tổng hợp. Mọi fixture và màn demo mang `synthetic/staged`.
- `mode=fixture` là preview không phải kiểm luật; job 3 thay service bằng kết quả thật và test `test_live_pipeline_uses_rule_engine` phải chứng minh.

## Điểm cắm cố định
- Dũng: `rules.engine.evaluate(request: CheckRequest) -> RuleEvaluation`; tự nạp `rules/catalog.json` và `rules/clauses.json`.
- Tuấn Anh: `detect.service.suggest(request: CheckRequest, evaluation: RuleEvaluation) -> DetectionResult`; `detect.validator.validate_findings(findings, request, rules, clauses) -> ValidationResult`.
- Khanh: `intake.router.router` được đăng ký sẵn trong `app/main.py`; `intake.service` ghép evaluate → suggest → validate, giữ snapshot qua `intake.store`.
- UI gọi `/api/*` cùng origin; dev proxy Vite tới `127.0.0.1:8000`; FastAPI phục vụ `ui/dist` sau API routes.
- Không thêm router ở file chung. Không gọi model ngoài `detect/client.py`. Không người nào sửa thư mục của người khác.

## Mã lỗi chung
`{"code":"not_found","message":"Resource not found."}`. HTTP 404: ID không tồn tại; 409: stale version / duplicate ID khác nội dung / chuyển trạng thái sai; 422: schema hoặc reference sai; 503: engine/LLM/tính năng chưa sẵn sàng. Không echo input hoặc secret trong lỗi. Lỗi model không làm hỏng kiểm tất định.

## Model và endpoint
Bảng schema và JSON mẫu đầy đủ được sinh từ model thật ở bước bootstrap bên dưới. Mọi thay đổi phải qua một PR hợp đồng riêng, cả đội đọc trước khi merge.

<!-- generated-contracts -->

## Endpoint cố định (v1)
| Method/path | Request | Response thành công | Bootstrap |
|---|---|---|---|
| GET /health | không | HealthResponse, 200 | fixture |
| GET /api/demo | không | DemoBundle, 200 | fixture thật trên đĩa |
| POST /api/check | CheckRequest | CheckResult, 200 | chỉ request demo; khác input → 503 |
| POST /api/changes | ChangeEvent | ChangeResponse, 200 | 503 chưa có store |
| POST /api/rechecks | RecheckRequest | CheckResult, 200 | 503 chưa có engine |
| POST /api/decisions | DecisionRequest | Decision, 201 | 503 chưa có store |
| GET /api/history | không | HistoryResponse, 200 | preview, arrays còn lại rỗng |

`/openapi.json` và `/docs` là tài liệu FastAPI. API thành công trả trực tiếp typed model; lỗi trả ApiError (không bọc detail). GET sai path → 404. Tất cả POST có 422 input; feature pending → 503. Bản live: ID/version không tồn tại → 404, trùng ID khác payload/stale/closure chưa recheck →409. Không đổi HTTP shape khi thay adapter fixture.

ID: CO-DEMO công ty; P-01 sản phẩm; REC-01 record; RV-01-v1 version; CL-01 clause; CV-01-v1 clause version; R-01 rule; F-<check suffix>-01 finding; CHK-<uuid> check; DEC-<uuid> decision; EV-<uuid> event; RQ-<uuid> queue. Regex Id chỉ ràng buộc cú pháp; prefix và quan hệ được service kiểm. Check và finding do server tạo; event ID do client tạo để retry idempotent. Cùng event ID + cùng nội dung trả response cũ; khác nội dung 409.

File rule/catalog và clauses là JSON array của Rule/ClauseVersion. Snapshot request là CheckRequest JSON. `uses` là dữ kiện fixture đã gán nhãn, không tự coi là kết quả trích xuất ngôn ngữ tự do. Lưu text gốc; validate mọi use có mặt trong text khi nạp live; trường rỗng không suy “không có claim”.

## Quy tắc nghiệp vụ cần hiện thực
POST check lưu CheckResult + snapshot bất biến. Mỗi target quảng cáo chạy subset rule theo profile, ngày, nguồn. N = số rule ID duy nhất thực chạy; skipped có ID và giải thích qua applicability, không được no_issue_found. LLM findings status suggestion/needs_evidence.
POST changes append version; tìm mọi check từng phụ thuộc dossier cũ, kể cả check không findings. Xét reference_ids và product fallback; queue unique (event_id, previous_check_id, target_version_id), không đưa sản phẩm khác vào. Event không sửa snapshot cũ.
POST rechecks dùng snapshot cũ, thay dossier bằng v2, cập nhật reference_ids liên quan trong snapshot mới; tạo check mới có parent_check_id. History giữ cả hai. Recheck cùng item đã completed trả check cũ.
POST decisions confirm/assign không đóng task; reject cần note và task dismissed. close cần closure_check_id có parent đúng, target đúng và không còn finding liên quan/chưa rõ; trường hợp vẫn thiếu chứng cứ trả409. P0 reviewer là vai trò demo công khai, không giả là phân quyền thật.

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
      "synthetic": true
    },
    {
      "id": "REC-02",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "marketing",
      "title": "Synthetic marketing",
      "synthetic": true
    },
    {
      "id": "REC-03",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "marketing",
      "title": "Synthetic marketing control",
      "synthetic": true
    },
    {
      "id": "REC-04",
      "company_id": "CO-DEMO",
      "product_id": "P-01",
      "kind": "evidence_index",
      "title": "Synthetic confirmation index; no official certificate",
      "synthetic": true
    },
    {
      "id": "REC-05",
      "company_id": "CO-DEMO",
      "product_id": "P-02",
      "kind": "marketing",
      "title": "Unrelated product control",
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
      "supersedes": null
    }
  ],
  "target_version_ids": [
    "RV-02-v1",
    "RV-03-v1"
  ],
  "review_date": "2026-10-31",
  "llm_mode": "off"
}
```
Response /api/check (preview):
```json
{
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
    "R-05"
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
        "synthetic": true
      },
      {
        "id": "REC-02",
        "company_id": "CO-DEMO",
        "product_id": "P-01",
        "kind": "marketing",
        "title": "Synthetic marketing",
        "synthetic": true
      },
      {
        "id": "REC-03",
        "company_id": "CO-DEMO",
        "product_id": "P-01",
        "kind": "marketing",
        "title": "Synthetic marketing control",
        "synthetic": true
      },
      {
        "id": "REC-04",
        "company_id": "CO-DEMO",
        "product_id": "P-01",
        "kind": "evidence_index",
        "title": "Synthetic confirmation index; no official certificate",
        "synthetic": true
      },
      {
        "id": "REC-05",
        "company_id": "CO-DEMO",
        "product_id": "P-02",
        "kind": "marketing",
        "title": "Unrelated product control",
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
        "supersedes": null
      }
    ],
    "target_version_ids": [
      "RV-02-v1",
      "RV-03-v1"
    ],
    "review_date": "2026-10-31",
    "llm_mode": "off"
  },
  "model_status": "off",
  "created_at": "2026-10-31T05:00:00Z",
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
