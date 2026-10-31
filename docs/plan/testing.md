# Kế hoạch kiểm thử
v1 — theo proposal final đã nhận 12:48:37 và quyết định chia tầng của user 12:58, 31/10/2026.

## Lệnh và tầng test
- `make setup`: Python 3.11 + venv, dependency ghim. `make test`: pytest, contract + API + smoke không cần key, coverage báo cáo phần Python đã triển khai, mục tiêu≥80% nhưng không chặn CI bằng tỷ lệ. `make lint`: Ruff. `make schemas`: xuất schema/OpenAPI. `make eval`: kiểm fixture lúc bootstrap, bảng dev thật sau job 1; tuyệt đối không gọi preview là kết quả model.
- `make smoke`: một lệnh chạy demo từ fixture qua API trong TestClient. Sau job 3: load → check → decision → version change → queue → recheck → history. Tất cả không key.
- Unit rule: mỗi R-xx ≥2 dương + ≥2 âm, gồm phủ định, profile unknown, khác pack, ngày biên, rule chưa xác minh; R-02 có tài liệu hỗ trợ vẫn cần người đánh giá, không tự kết luận đủ giá trị khoa học.
- Contract: every model extra=forbid, enums chặt, immutable, span/missing_field loại trừ nhau, khoảng ngày, schema checked-in khớp model. `tests/contracts/test_models.py`, `test_schema_snapshot.py`.
- API: TestClient, 200/201/404/409/422/503; không echo input độc hại; ID/version sai; snapshot cũ giữ nguyên. `intake/tests/test_api.py`.
- Grounding: rule/clause lạ, quote bịa, span sai, missing field thực có, clause ngoài ngày, rule disabled; không fuzzy. `detect/tests/test_validator.py`.
- Wording: scan response JSON và UI source cho các từ cấm, kể cả Unicode/case; validate input không để lỗi trả nguyên văn câu cấm. `tests/contracts/test_wording.py`; `ui/src/wording.test.ts` khi UI có.
- No key: bỏ OPENAI_API_KEY, disable network/model path, chạy `tests/smoke/test_demo.py`. Fixture/cache được ghi nhãn; không chạy model khi key trống.
- UI: `ui/src/api.test.js::usesLiveApiWhenAvailable` và `showsFixtureBadgeOnStaticFallback` bắt buộc: API sẵn sàng phải dùng response API, fallback file tĩnh phải hiện fixture. Chạy `npm --prefix ui test -- --run src/api.test.js`. Vitest rendering fixture/error/loading/evidence và Playwright browser flow khi frontend sẵn sàng. Một smoke script đủ, không dựng nhiều tầng framework. Makefile đã có `make frontend-test`, `make frontend-build`, `make e2e`; CI tự bật frontend khi ui/package-lock.json xuất hiện. `make eval-final` có điểm cắm nhưng chưa chạy được trước khi job 1 viết eval/final.py.

## Chứng minh bỏ fixture
`rules/tests/test_engine.py::test_verified_rules_change_with_input` phải thay text và nhận output khác, N chính xác; `intake/tests/test_api.py::test_live_pipeline_uses_rule_engine` phải assert mode=live, dùng engine thật, không patch engine; `test_changed_dossier_requeues_clean_prior_decision` giữ snapshot cũ. Không xóa/skip contract test để đạt xanh.

## Eval và baseline
Tuấn Anh sở hữu `eval/`, `detect/`, `data/dev/`. Keyword baseline công khai cùng input, từ khóa không cố ý yếu. Dev gồm ca sạch, explicit, implied, use mismatch, missing evidence, profile unknown và injection. So cặp (record, rule), precision/recall theo rule, false flags ca sạch, validator rejects theo nguyên nhân, N thực chạy, gold queue precision/recall, stability 3 lần, latency/calls/cache. Mọi mẫu số ghi rõ; N=0 ghi null/not_measured, không 100%.

Baseline model thuần là bắt buộc cho gate tầng 1: cùng model OPENAI_MODEL và cùng hồ sơ/điều khoản, không graph/tool routing; giữ raw response + prompt hash + input hash, timeout và refusal là lỗi đo, không âm tính. B+/RAG chưa triển khai hôm nay; không nhận là đã đo. Mọi call chỉ qua detect/client.py; cache key gồm schema+prompt version+model+review date+record hashes+rule/clause versions. Không gắn output giả vào cache.

Merge gate: chạy dev trên main và PR cùng input/rule scope/model mode, không tụt recall hay tăng false flags/grounding errors; nếu thay phạm vi rule thì báo scope change riêng, không so hai mẫu số khác. Ghi ledger pr-blocked nếu tụt. Bootstrap `make eval` chỉ fixture validation, chưa có số so sánh.

## Tập cuối ngoài repo
Con người tự viết và gán nhãn ở `~/nullptr-test-final/`; Codex không mở/list/đọc hoặc tạo dữ liệu ở đó. Mục tiêu khả thi 15–24 ca, ≥1/3 sạch; số thực phải ghi và không gọi là tập 40–60 nếu chưa có. Con người khóa manifest sha256 lúc 14:15, ghi ledger; chạy một lần 15:15 bằng lệnh job 1 cung cấp `make eval-final FINAL_DIR=...` (human only). Log chỉ metrics, dataset hash, git SHA, model/rules/prompt hashes; không in nội dung. Sau lần chạy, con người quyết định công bố dataset tổng hợp. Ca đã dùng sửa lỗi chuyển dev, mất nhãn held-out. Sửa lõi sau eval phải ghi số thuộc SHA trước sửa, không chạy lại để làm đẹp số.

## Xanh theo mốc
- Bootstrap: test contract/API fixture, lint, eval validation, CI, clone sạch; không đồng nghĩa tính năng hoàn tất.
- 14:05: P0 thật, ≥3 rule đã kiểm (nếu ít hơn ghi đúng), validator, fixture replacement test, no-key smoke.
- 14:15: deploy dùng mode=live + badge synthetic; load/check/change/recheck giữ history; nếu thiếu báo thật trong WIP 14:25.
- 15:15: regression dev xanh, nguồn kiểm xong; human chạy final một lần.
- 15:30: freeze SHA; 16:15 link/public README/PDF/video/credentials scan.

Contract test thích nghi với runtime_mode fixture/live để các job thay adapter trong thư mục riêng, không cần sửa test chung. Test chuyển sang live bắt buộc ở intake/tests không được condition/skip; fixture gate không thay test tính năng.

## Gate theo tầng và smoke thực
CI chạy make test + make smoke + lint + eval; khi ui/package-lock.json có thì thêm frontend test/build. make smoke không được bỏ qua test chưa có: bootstrap chỉ có fixture smoke; explicit LAYER=0..3 phải có intake/tests/test_smoke_layers.py và mode live. Dispatcher bật flags prerequisite trong child process để thử tầng mới trước khi bật deployment. Không skip/xfail smoke; test không được mock checker/store/validator. Model transport có thể dùng recorded real dev cache cho smoke no-key, ghi cached rõ; test lỗi dùng stub riêng và không đi vào số eval.

| Tầng | Test smoke bắt buộc | Cửa chặn quan trọng |
|---|---|---|
| 0 | intake/tests/test_smoke_layers.py::test_layer0_smoke | profile→>=3 verified rules→decision→dossier event→N=2 queue/K=1 finding→manual revision→fresh recheck→authorized close; old hash giữ nguyên; P-02 không queued; no key |
| 1 | test_layer1_smoke | layer0 vẫn chạy; validator 5 kiểm; report dev có cả3systems và n thật hoặc gate không đạt; cited chat; assignment không close; timeout/refusal không mất deterministic result |
| 2 | test_layer2_smoke | pending legal change không đổi rule active; verified+accepted+effective mới activate; before/after date; cùngevent retry không nhân queue; old result giữbasis; 5–8 distinct verified rule nếu đủ nguồn |
| 3 | test_layer3_smoke | operations không đọc được manager sentinel qua records/check/history/chat/cache/demo; role giả không close; reviewed Pattern qua guard mới active; old/new+model-call delta thật |

Luật chặn merge: mỗi PR make test + smoke của tầng đang bật đều xanh; feature mới off thì vẫn phải có unit/integration tests của thay đổi. Muốn bật tầng N phải chạy explicit smoke N trên main ở chính SHA đó, browser smoke, và ghi flagstate+SHA vào ledger. Người merge kiểm git diff cả branch; agent không merge PR người khác. Khi tắt lower layer phải tắt upper layers.

## Ma trận quyền và cache
Test cả401 no token,403 action cấm,404 private ID,422 schema,409 stale,503 unavailable và404 feature_disabled. Kiểm nested snapshot/evidence, /api/demo, /api/records, /api/checks/{id}, /api/history, /api/chat, /api/evaluation, /api/feedback và legal routes. API authorization trước retrieval/cache; text private không xuất hiện trong response/error/log. UI user switch xóa dữ liệu người trước. Demo session selector không là production auth; mọi record tổng hợp.

## Khóa 15:15 độc lập tầng 3
15:10 human ghi EVAL_SHA/flags/rule hashes; checkout riêng đúng SHA, chỉ đọc bản đó trong final run. Không merge thay đổi vào working directory của lần đo. Human final đúng15:15 kể cả tầng 2 chưa đạt (đo tầng cao nhất đã hoàn tất). Dataset thực bao nhiêu ghi bấy nhiêu; proposal40–60 là mục tiêu, không bịa. Tầng 3 vẫn có thể hoàn tất15:30 nhưng chỉ báo smoke/dev của nó; metrics held-out gắn SHA15:10, không đánh tráo sangSHA freeze. Nếu không thể lấy model response, ghi failed/unavailable, không rerun để làm đẹp số.

## Tự review khởi tạo
Đã sửa: context_version_ids rõ căn cứ mới mà không đổi record cũ; snapshots giữ cả rule/clause khi không finding; health runtime extension tránh đổi file chung; per-app state để test không nhiễm; các endpoint tầng sau khóa404. Chưa phải bằng chứng tính năng live. Baseline/e2e/per-rule tests trong job files là nghiệm thu cần triển khai, không báo là đã chạy.

Sau review vòng1: make lint chạy Ruff check; formatting sửa bằng make fmt trước commit, không là gate format riêng. Coverage report-only; lỗi hành vi và smoke vẫn chặn merge. Không giảm các test bất biến để làm CI xanh.
