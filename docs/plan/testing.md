# Kế hoạch kiểm thử
v0 — trước proposal final.

## Lệnh và tầng test
- `make setup`: Python 3.11 + venv, dependency ghim. `make test`: pytest, contract + API + smoke không cần key, coverage ≥80% phần Python đã triển khai. `make lint`: Ruff. `make schemas`: xuất schema/OpenAPI. `make eval`: kiểm fixture lúc bootstrap, bảng dev thật sau job 1; tuyệt đối không gọi preview là kết quả model.
- `make smoke`: một lệnh chạy demo từ fixture qua API trong TestClient. Sau job 3: load → check → decision → version change → queue → recheck → history. Tất cả không key.
- Unit rule: mỗi R-xx ≥2 dương + ≥2 âm, gồm phủ định, profile unknown, khác pack, ngày biên, rule chưa xác minh; R-02 có tài liệu hỗ trợ vẫn cần người đánh giá, không tự kết luận đủ giá trị khoa học.
- Contract: every model extra=forbid, enums chặt, immutable, span/missing_field loại trừ nhau, khoảng ngày, schema checked-in khớp model. `tests/contracts/test_models.py`, `test_schema_snapshot.py`.
- API: TestClient, 200/201/404/409/422/503; không echo input độc hại; ID/version sai; snapshot cũ giữ nguyên. `intake/tests/test_api.py`.
- Grounding: rule/clause lạ, quote bịa, span sai, missing field thực có, clause ngoài ngày, rule disabled; không fuzzy. `detect/tests/test_validator.py`.
- Wording: scan response JSON và UI source cho các từ cấm, kể cả Unicode/case; validate input không để lỗi trả nguyên văn câu cấm. `tests/contracts/test_wording.py`; `ui/src/wording.test.ts` khi UI có.
- No key: bỏ OPENAI_API_KEY, disable network/model path, chạy `tests/smoke/test_demo.py`. Fixture/cache được ghi nhãn; không chạy model khi key trống.
- UI: Vitest rendering fixture/error/loading/evidence và Playwright browser flow khi frontend sẵn sàng. Một smoke script đủ, không dựng nhiều tầng framework.

## Chứng minh bỏ fixture
`rules/tests/test_engine.py::test_verified_rules_change_with_input` phải thay text và nhận output khác, N chính xác; `intake/tests/test_api.py::test_live_pipeline_uses_rule_engine` phải assert mode=live, dùng engine thật, không patch engine; `test_changed_dossier_requeues_clean_prior_decision` giữ snapshot cũ. Không xóa/skip contract test để đạt xanh.

## Eval và baseline
Tuấn Anh sở hữu `eval/`, `detect/`, `data/dev/`. Keyword baseline công khai cùng input, từ khóa không cố ý yếu. Dev gồm ca sạch, explicit, implied, use mismatch, missing evidence, profile unknown và injection. So cặp (record, rule), precision/recall theo rule, false flags ca sạch, validator rejects theo nguyên nhân, N thực chạy, gold queue precision/recall, stability 3 lần, latency/calls/cache. Mọi mẫu số ghi rõ; N=0 ghi null/not_measured, không 100%.

Baseline model thuần (P1 nếu proposal cho phép): cùng model OPENAI_MODEL và cùng hồ sơ/điều khoản, không graph/tool routing; giữ raw response + prompt hash + input hash, timeout và refusal là lỗi đo, không âm tính. B+/RAG là P2. Mọi call chỉ qua detect/client.py; cache key gồm schema+prompt version+model+review date+record hashes+rule/clause versions. Không gắn output giả vào cache.

Merge gate: chạy dev trên main và PR cùng input/rule scope/model mode, không tụt recall hay tăng false flags/grounding errors; nếu thay phạm vi rule thì báo scope change riêng, không so hai mẫu số khác. Ghi ledger pr-blocked nếu tụt. Bootstrap `make eval` chỉ fixture validation, chưa có số so sánh.

## Tập cuối ngoài repo
Con người tự viết và gán nhãn ở `~/nullptr-test-final/`; Codex không mở/list/đọc hoặc tạo dữ liệu ở đó. Mục tiêu khả thi 15–24 ca, ≥1/3 sạch; số thực phải ghi và không gọi là tập 40–60 nếu chưa có. Con người khóa manifest sha256 lúc 14:15, ghi ledger; chạy một lần 15:15 bằng lệnh job 1 cung cấp `make eval-final FINAL_DIR=...` (human only). Log chỉ metrics, dataset hash, git SHA, model/rules/prompt hashes; không in nội dung. Sau lần chạy, con người quyết định công bố dataset tổng hợp. Ca đã dùng sửa lỗi chuyển dev, mất nhãn held-out. Sửa lõi sau eval phải ghi số thuộc SHA trước sửa, không chạy lại để làm đẹp số.

## Xanh theo mốc
- Bootstrap: test contract/API fixture, lint, eval validation, CI, clone sạch; không đồng nghĩa tính năng hoàn tất.
- 14:05: P0 thật, ≥3 rule đã kiểm (nếu ít hơn ghi đúng), validator, fixture replacement test, no-key smoke.
- 14:15: deploy dùng mode=live + badge synthetic; load/check/change/recheck giữ history; nếu thiếu báo thật trong WIP 14:25.
- 15:15: regression dev xanh, nguồn kiểm xong; human chạy final một lần.
- 15:30: freeze SHA; 16:15 link/public README/PDF/video/credentials scan.
