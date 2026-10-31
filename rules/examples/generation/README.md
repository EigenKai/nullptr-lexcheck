# Mẫu đầu ra cho hệ thống tự sinh rule

Đây là **development references**, do developer biên soạn để mô tả hệ thống cần sinh được gì từ văn bản. Các rule mẫu không được nạp vào engine, catalog hay API. `reference.json` không phải kết quả model, không phải bộ luật được xác minh và không phải tập đánh giá cuối.

Ba ví dụ: cảnh báo trong quảng cáo chữ; công dụng ngoài hồ sơ cần chứng cứ; chứng cứ xác nhận quảng cáo có liên kết. Mỗi ví dụ gồm đoạn nguồn có số trang/hash, một `Rule` và `ClauseVersion` theo contract chung, giải thích phạm vi/ngoại lệ, và ít nhất 2 ca cần xem + 2 ca không bị rule đó đánh dấu. Tất cả hồ sơ công ty đều tổng hợp.

## Dùng để xây bộ sinh rule

1. Đưa **chỉ `input` và prompt** cho model; không đưa `expected_rule`, `expected_clause`, `expected_semantics` hoặc `cases.expected` vào lượt đánh giá.
2. Yêu cầu model sinh ứng viên từ nguồn đang cấp. Người dùng có thể đưa luật mới; các ID mẫu không phải danh sách luật được hỗ trợ.
3. Dùng `contracts.models.Rule.model_json_schema()` và `ClauseVersion.model_json_schema()` làm cấu trúc đầu ra. Không tạo bản sao model chung.
4. Đối chiếu nguyên văn/offset trên source text; giữ page/hash để kiểm lại ảnh gốc. Nguồn được chép từ ảnh không tự trở thành nguồn đã được người giữ rule xác minh.
5. Chạy checker phát triển và đánh giá hành vi trên ca mẫu khi generic executor/model adapter có sẵn. Khớp cấu trúc không chứng minh diễn giải pháp luật đúng.
6. User/reviewer xem và chấp nhận ứng viên; runtime chỉ dùng nguồn và rule đã được xác minh theo cơ chế của app. Không tự sao chép các mẫu này vào catalog.

Mẫu dùng `enabled=false`, `to_be_verified`, `in_force=unknown` và không ghi người xác minh. Hash chứng minh nhận diện file nguồn, không chứng minh hiệu lực hiện hành. Các ngày trong ví dụ là metadata lịch sử, không phải xác nhận phạm vi đến ngày chạy.

## Kiểm tra local

```sh
python -m rules.example_validation rules/examples/generation/reference.json
python -m pytest rules/tests/test_generation_examples.py -q
```

Windows dùng `.venv/Scripts/python.exe -X utf8` thay cho `python` nếu cần. Checker chỉ chạy khi được gọi rõ ràng. Nó kiểm contract, quote/offset, phạm vi loại hoạt động và trạng thái ứng viên. Nó **không** chạy phép kiểm pháp lý hay báo accuracy của bộ sinh rule.

`rules/tests/test_generation_examples.py` chứng minh ID mẫu không xuất hiện trong catalog, bộ demo hoặc kết quả engine mặc định. Bộ mẫu không yêu cầu API key và không gọi mạng/model.

## Nguồn

[NĐ 15/2018 bản ký](https://datafiles.chinhphu.vn/cpp/files/vbpq/2018/02/15.signed.pdf), trang PDF 19–21, Điều 26–27. Có thể đọc thêm [bản Công báo](https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2018/2/25858/21320-1-2018375-37615-2018-nd-cp.pdf), trang PDF 20–22. PDF/ZIP và bản nháp OCR được giữ trong cache local, không kèm bộ mẫu.

Nguồn về hiệu lực/phân cấp còn cần đối chiếu trước khi dùng thật: NQ 15/2026, NQ 21/2026 và các văn bản liên quan hiện hành. Không mặc định mọi nhãn là quảng cáo; không suy thiếu file trong kho là thủ tục ngoài đời chưa từng xảy ra.
