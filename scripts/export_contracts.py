"""Export schemas and documentation from the canonical models and fixture examples."""

import inspect
import json
from pathlib import Path

from app.main import app
from contracts import models
from intake.fixtures import load_demo

ROOT = Path(__file__).resolve().parents[1]
MARKER = "\n<!-- generated-contracts -->\n"


def contract_models():
    return tuple(
        value
        for _, value in inspect.getmembers(models, inspect.isclass)
        if issubclass(value, models.Contract) and value is not models.Contract
    )


def json_block(value):
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```\n"


def main():
    for model in contract_models():
        (ROOT / f"schemas/{model.__name__}.schema.json").write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2) + "\n"
        )
    (ROOT / "schemas/openapi.json").write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"
    )
    path = ROOT / "docs/plan/contracts.md"
    prefix = path.read_text().split(MARKER)[0]
    bundle = load_demo().model_dump(mode="json")
    endpoints = """
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
"""
    text = (
        prefix
        + MARKER
        + endpoints
        + "```python\n"
        + (ROOT / "contracts/models.py").read_text().strip()
        + "\n```\n"
    )
    text += (
        "\n## JSON mẫu request/response\nGET /api/demo = data/fixtures/demo.json (đầy đủ, kiểm bằng test); POST /api/check request:\n"
        + json_block(bundle["request"])
    )
    text += "Response /api/check (preview):\n" + json_block(bundle["preview"])
    text += "POST /api/changes request:\n" + json_block(bundle["event"])
    text += "Response changes live (ví dụ queue, không phải kết quả bootstrap):\n" + json_block(
        {
            "event": bundle["event"],
            "mode": "live",
            "queue": [
                {
                    "id": "RQ-01",
                    "event_id": "EV-01",
                    "previous_check_id": "CHK-01",
                    "target_version_id": "RV-02-v1",
                    "reason": "direct_dependency",
                    "status": "queued",
                    "new_check_id": None,
                }
            ],
        }
    )
    text += (
        "POST /api/rechecks request; response cùng CheckResult ở trên, ID mới và parent_check_id cũ:\n"
        + json_block({"item_id": "RQ-01", "llm_mode": "off"})
    )
    decision = {
        "check_id": "CHK-01",
        "finding_id": "F-01",
        "action": "assign",
        "actor": "reviewer",
        "owner": "marketing",
        "note": "Please supply connected evidence.",
        "closure_check_id": None,
    }
    text += "POST /api/decisions request:\n" + json_block(decision)
    text += "Response decision live:\n" + json_block(
        {
            "id": "DEC-01",
            "request": decision,
            "task_status": "assigned",
            "created_at": "2026-10-31T07:00:00Z",
        }
    )
    text += "GET /api/history shape (live trống):\n" + json_block(
        {"checks": [], "decisions": [], "events": [], "queue": [], "mode": "live"}
    )
    text += "GET /health:\n" + json_block({"status": "ok", "mode": "fixture"})
    path.write_text(text)


if __name__ == "__main__":
    main()
