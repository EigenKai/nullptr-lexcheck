# Dữ liệu demo
v0 — trước proposal final.

## Chọn bộ hồ sơ
Chọn hồ sơ TPBVSK **tổng hợp từ cấu trúc Mẫu 02 + chỉ mục Mẫu 10/11** của NĐ 15/2018. Company DEMO phân phối trong nước, product P-01. Chỉ dùng JSON/chữ trong P0; không tạo giấy có dấu/chữ ký/mã giấy phép thật. Không cào sàn, không nạp dữ liệu doanh nghiệp thật.

Ưu điểm: giữ pack đã đăng ký; chủ động có đáp án chính xác; không đòi OCR; so sánh quan hệ dossier/marketing/chứng cứ; không gán lỗi cho doanh nghiệp thật. Không chọn quyết định 138/QĐ-ATTP làm cảnh chính: ghép nó với một marketing register vẫn là dàn dựng và cần giải thích rút hồ sơ không phải vi phạm. NQ 21/2026 chỉ là thay đổi thẩm quyền, không đủ để kết luận giấy cũ mất hiệu lực.

**Một sự kiện bắt buộc:** dossier v1 → v2 bỏ một công dụng. Dossier v1 có `Hỗ trợ tiêu hóa.` và `Hỗ trợ giảm cholesterol.`; v2 chỉ giữ câu đầu. Marketing M-01 và marketing M-02 từng phụ thuộc v1 phải được đưa vào queue, kể cả kết quả cũ không có finding. M-02 chỉ dùng công dụng còn giữ nên được recheck nhưng không phát sinh R-02; N=2 record rà lại, K=1 cần xem. P-02 không liên quan không vào queue. Khi thiếu liên kết chắc chắn, mở rộng tới mọi record của P-01. Giữ nguyên decision cũ; recheck sinh decision mới.

## File, nhãn và đáp án
| File | Nội dung | Đáp án dự kiến sau khi rule được xác minh |
|---|---|---|
| `data/fixtures/finding-preview.json` | CheckResult fixture có finding R-02 + span đúng cho UI và validator | chỉ preview synthetic, không đánh giá luật |
| `data/fixtures/demo.json` | bundle: profile, record metadata, versions, request, preview, event | preview chỉ để UI dựng, `mode=fixture`, không là kết quả đo |
| `data/fixtures/cases/clean.json` | marketing chỉ công dụng trong dossier, đủ cảnh báo/chứng cứ liên kết | không finding theo các rule thực chạy |
| `data/fixtures/cases/missing-warning.json` | bỏ toàn bộ cảnh báo | R-01 needs_review, missing_field, không quote |
| `data/fixtures/cases/extra-use.json` | công dụng ngoài dossier, không evidence hỗ trợ | R-02 needs_evidence; span đúng đoạn marketing |
| `data/fixtures/cases/missing-confirmation.json` | không có record chứng cứ xác nhận | R-03 needs_evidence; “not found in the connected records” |
| `data/fixtures/cases/endorsement.json` | thêm câu bác sĩ khuyên dùng tổng hợp | R-04 needs_review nếu đủ căn cứ; không suy từ từ khóa “bác sĩ” trong câu phủ định |
| `data/fixtures/cases/unknown-profile.json` | activity unknown hoặc chưa xác nhận profile | not_enough_information; không chạy rule quảng cáo |
| `data/fixtures/answers.json` | ID case → expected rule IDs/status, gold queue | nhãn dev có điều kiện rule enabled; không phải held-out |
| `rules/catalog.json`, `rules/clauses.json` | rule/căn cứ có version, source URL, ngày, trạng thái | tất cả to_be_verified và disabled khi bootstrap |

Nhãn trên mọi màn: `synthetic/staged`. P0 không có dữ liệu thật. Nếu sau này ghép nguồn thật thì luôn giữ nhãn ghép dàn dựng và không hiện cáo buộc trên tên doanh nghiệp thật. Không có email, địa chỉ, điện thoại, tên người đại diện hay chữ ký trong fixture.

## Căn cứ và người kiểm
| Rule | Kiểm hẹp | Căn cứ cần đối chiếu | Trạng thái bootstrap | Chủ/hạn |
|---|---|---|---|---|
| R-01 | cảnh báo TPBVSK | NĐ 15/2018 Điều 27(3)(a); ngoại lệ hình thức phải xét | to_be_verified, disabled | Dũng trước 13:30 |
| R-02 | công dụng ngoài dossier cần chứng cứ | Điều 27(2), 27(4)(đ) | to_be_verified, disabled | Dũng trước 13:30 |
| R-03 | thiếu chứng cứ đăng ký/xác nhận trong kho | Điều 26(1), 27(1), 27(6) | to_be_verified, disabled | Dũng trước 13:30 |
| R-04 | endorsement y tế trong quảng cáo chữ | Điều 27(2) | to_be_verified, disabled | Dũng trước 13:30 |
| R-05 | gợi ý gây hiểu nhầm như thuốc | căn cứ chính xác từ luật/quy định quảng cáo cần Dũng tìm | to_be_verified, disabled; cắt trước | Dũng trước 14:05 |

Nguồn đọc: [NĐ 15 bản ký, trang PDF 19–20, 35–36, 44–45](https://datafiles.chinhphu.vn/cpp/files/vbpq/2018/02/15.signed.pdf), [thuộc tính](https://chinhphu.vn/?docid=192829&pageid=27160), [NQ 15/2026, Điều 1–2,5](https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/15-nqcp.signed.pdf), [thủ tục VFA](https://vfa.gov.vn/thu-tuc-hanh-chinh/dang-ky-xac-nhan-noi-dung-quang-cao-doi-voi-thuc-pham-bao-ve-suc-khoe.html). Các nguồn đã được đọc trong quá trình chuẩn bị ngày 31/10; điều đó không thay Dũng kiểm nguyên văn và hiệu lực đến ngày demo. Dũng ghi `verified_by`, `verified_at`, `status_note`, source hash và cập nhật rule qua PR; thiếu xác minh thì bỏ rule, không bịa quote.

Không kích hoạt rule dựa riêng vào ngày văn bản. Khi dùng Điều 27, rà NQ 15/2026 và phân cấp NQ 21/2026, không hardcode cơ quan cấp cũ. `valid_to=null` không chứng minh không có văn bản sửa đổi.
