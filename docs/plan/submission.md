# Nộp bài
v1 — theo proposal final đã nhận 12:48:37 và quyết định chia tầng của user 12:58, 31/10/2026.

Giữ quy trình ngày thi đã chốt: **Tuấn Anh gửi**, Dũng dự phòng; chỉ một người gửi. Agent không nộp form, gửi email hay liên hệ BTC. Tuấn Anh hỏi trực tiếp kênh WIP/form cuối và ghi link nội bộ.

| Giờ +07 | Chủ | Đầu ra |
|---|---|---|
| 14:15 | cả đội | README hiện trạng thật; repo, demo, một câu đã chạy/chưa chạy |
| 14:25 | Tuấn Anh | gửi WIP theo kênh BTC; hạn agenda 14:30 |
| 15:15 | Tuấn Anh | human final eval một lần, n + hash + SHA |
| 15:30 | cả đội | đóng băng, chỉ sửa lỗi chặn demo |
| 15:30–16:00 | Khanh | live URL mở máy khác + quay video dự phòng |
| 15:30–16:00 | Dũng | Declarations PDF; link OSS/license; đọc lại README |
| 15:30–16:00 | Tuấn Anh | write-up dùng proposal final; sửa bảng Today theo tầng thật bật và chênh lệch trong plan.md; bổ sung kết quả đã đo, giới hạn và ledger |
| 16:00 | cả đội | tập demo 6 phút + Q&A 2 phút |
| 16:15 | cả đội | checklist dưới |
| 16:30 | Tuấn Anh | bấm gửi, lưu ảnh xác nhận, giờ và links; Dũng dự phòng |
| 16:30–17:00 | cả đội | tập hai lượt, thử video; hạn BTC 17:00 không dời |

README tiếng Anh: product + scope/status; Python/Node versions; make setup/test/lint/eval/run/smoke; API fixture caveat; live demo link khi có; synthetic label; how Codex was used + ledger; Built during the hackathon; Declarations; model mode/cache; verified/disabled rules và giới hạn. Không đưa file review nội bộ vào repo.

Declarations PDF: khai FastAPI, Pydantic, Uvicorn, OpenAI SDK, pytest, Ruff và frontend library thực dùng, repo nguồn và license. Không tái dùng code/schema dự án cũ; nếu có thay đổi quyết định phải khai nhất quán trong README/form/PDF. Khai ý tưởng, ghi chú pháp lý và hướng dẫn quy trình đã chuẩn bị trước ngày thi bằng mô tả chung, không chép ghi chú nội bộ. Chỉ code xây trong ngày được tính.

Ledger: mỗi người append file riêng `docs/ledger/tuan-anh.md`, `dung.md`, `khanh.md`; leader tổng hợp `docs/build-ledger.md` để không xung đột. Cột time/member/kind/what/result/link. kind: task, pr-merged, pr-blocked, review, eval. Chỉ ghi số thật, link task/commit/PR, tiêu chí nghiệm thu.

Checklist 16:15:
- [ ] Repo mới public, README và branch main chạy từ clone sạch; no secret/private file; các dependency có license/link.
- [ ] Write-up PDF final và Declarations PDF mở được, không lỗi font, link đúng; chỉ mô tả tính năng thật chạy.
- [ ] Demo live/prototype mở ẩn danh máy khác; video dự phòng không chứa key, cache được ghi nhãn.
- [ ] Ledger, eval n/hash/SHA và giới hạn đã khớp; đủ cả ba thành viên tới hết ngày.
- [ ] Một người gửi trước 16:30, ảnh xác nhận và URL lưu nội bộ. Không dựa vào agent để bấm form.

15:30 bắt buộc đối chiếu write-up: tier nào flag off thì chuyển nội dung đó sang roadmap; số rule verified và Nthực chạy tách nhau; held-out n thực thay mục tiêu40–60; metrics gắn EVAL_SHA còn demo gắn FREEZE_SHA. Nếu hai SHA khác nhau nói rõ. Không nhận quyền backend, feedback reuse, graph advantage hay baseline thắng nếu chỉ có màn preview. Phương pháp ViHERMES được proposal dẫn như tài liệu nghiên cứu; không sao chép code/schema từ đó trong build này. Nếu đội đổi quyết định reuse phải khai source/license/phần extension nhất quán trước nộp.

Dũng xác nhận với leader liệu mình có phải đồng tác giả “Dung N. H. Le” của ViHERMES (proposal §8). Dù là đồng tác giả, mọi code/schema tái dùng vẫn phải khai README + form + Declarations; mặc định build này không tái dùng.
