// English for the app shell, shared labels, API messages and settings.
// Keys are the Vietnamese source strings.
export default {
  // App shell
  "LexCheck · Rà soát hồ sơ doanh nghiệp": "LexCheck · Company record review",
  "Đến nội dung chính": "Skip to main content",
  "Đóng menu": "Close menu",
  "Mở menu": "Open menu",
  "Cuộc trò chuyện mới": "New conversation",
  "KHÔNG GIAN LÀM VIỆC": "WORKSPACE",
  "Không gian làm việc": "Workspace",
  "Điều hướng chính": "Main navigation",
  "Cài đặt": "Settings",
  "Reviewer mẫu": "Sample reviewer",
  "Chế độ trải nghiệm": "Demo mode",
  "Đổi tài khoản mẫu": "Switch sample account",
  "Tài khoản mẫu": "Sample account",
  "Quản lý": "Manager",
  "Kế toán + vận hành": "Accounting + operations",
  "Bản mẫu ngoại tuyến": "Offline sample",
  "Dữ liệu tổng hợp": "Synthetic data",
  "Mở bằng chứng và tri thức": "Open evidence and knowledge",
  "Tri thức và bằng chứng": "Knowledge and evidence",
  "API mất kết nối · Chỉ xem bản mẫu đi kèm":
    "API unreachable · Showing the bundled sample only",
  "Engine chưa sẵn sàng · đang dùng fixture":
    "Engine not ready · using fixture data",
  "Tải lại": "Reload",
  "Kết nối hồ sơ": "Connecting records",
  "Chưa có dữ liệu.": "No data yet.",
  // Busy, notice and error messages set by the shell
  "Tài khoản đã thay đổi. Bỏ kết quả của phiên cũ.":
    "The account changed. Results from the previous session were discarded.",
  "Đang tải hồ sơ và lịch sử từ API…": "Loading records and history from the API…",
  "Đang mở finding minh hoạ…": "Opening the sample finding…",
  "Không tải được finding minh hoạ.": "Could not load the sample finding.",
  "Finding minh hoạ từ fixture: chưa chạy engine, không lưu quyết định.":
    "Sample finding from a fixture: the engine did not run and nothing is saved.",
  "Chưa kết nối chatbot. Câu hỏi chưa được gửi.":
    "Chat is not connected. The question was not sent.",
  "Chọn một kết quả kiểm tra trước khi hỏi.": "Select a check result before asking.",
  "Đang tra cứu căn cứ trong kết quả đã chọn…":
    "Looking up the basis in the selected result…",
  "Nhập ghi chú trước khi lưu quyết định.": "Add a note before saving the decision.",
  "Đang lưu quyết định của reviewer…": "Saving the reviewer's decision…",
  "Đã lưu quyết định vào lịch sử API.": "Decision saved to the API history.",
  "Chỉnh nội dung hoặc công dụng trước khi tạo phiên bản mới.":
    "Edit the text or the uses before creating a new version.",
  "Đang tạo phiên bản mới và hàng đợi rà lại…":
    "Creating the new version and its recheck queue…",
  "Đã tạo phiên bản mới. Chạy lại mục tương ứng trong hàng đợi.":
    "New version created. Recheck its items in the queue.",
  // Shared labels (components/shared.jsx)
  "Trợ lý Lex": "Lex assistant",
  "Kho tri thức": "Knowledge base",
  "Rà soát hồ sơ": "Record review",
  "Cập nhật nguồn": "Source updates",
  "Lịch sử quyết định": "Decision history",
  "Hồ sơ công bố": "Product declaration",
  "Nội dung quảng cáo": "Advertising content",
  "Mục lục chứng từ": "Evidence index",
  "Hồ sơ xác nhận quảng cáo": "Ad content confirmation",
  "Kịch bản chăm sóc": "Customer care script",
  "Tài liệu khoa học": "Scientific evidence",
  "Cảnh báo bắt buộc": "Mandatory warning",
  "Đối chiếu công dụng": "Declared uses",
  "Bằng chứng xác nhận": "Confirmation evidence",
  "Hình ảnh / bảo chứng": "Images / endorsements",
  "Tuyên bố chữa bệnh": "Medicinal claims",
  "Chưa có": "None yet",
  // API messages (api.js)
  "Không kết nối được API. Kiểm tra dịch vụ rồi thử lại.":
    "Cannot reach the API. Check the service and try again.",
  "Chức năng này chưa sẵn sàng trên backend. Chưa lưu thay đổi.":
    "This feature is not ready on the backend. Nothing was saved.",
  "Phiên bản đã thay đổi. Hãy tải lại lịch sử trước khi tiếp tục.":
    "The version changed. Reload the history before continuing.",
  "Dữ liệu chưa đúng cấu trúc yêu cầu. Kiểm tra hồ sơ và thử lại.":
    "The data does not match the required structure. Check the records and try again.",
  "Phiên demo đã hết hạn. Hãy kết nối lại tài khoản mẫu.":
    "The demo session expired. Reconnect the sample account.",
  "Tài khoản mẫu không có quyền thực hiện thao tác này.":
    "The sample account may not do this.",
  "Không tìm thấy dữ liệu hoặc tính năng chưa được bật.":
    "Data not found, or the feature is not enabled.",
  "Không tải được bản mẫu ngoại tuyến.": "Could not load the offline sample.",
  "Chưa chạy kiểm tra": "No check run yet",
  "{count} mục cần xem xét": "To review: {count}",
  "No issue found under {count} encoded rules":
    "No issue found under {count} encoded rules",
  "Chưa đủ thông tin": "Not enough information",
  // Settings
  "Tuỳ chọn": "Preferences",
  "Ngôn ngữ": "Language",
  "Điều khoản và nội dung hồ sơ giữ nguyên văn gốc.":
    "Legal clauses and record text stay in the original Vietnamese.",
  "Dữ liệu": "Data",
  "Nguồn": "Source",
  "Gói luật": "Rule pack",
  "Mất kết nối · đang xem bản mẫu đi kèm": "Unreachable · showing the bundled sample",
  "Đã kết nối · live": "Connected · live",
  "Đã kết nối · engine chưa sẵn sàng": "Connected · engine not ready",
  "Dữ liệu tổng hợp (synthetic/staged)": "Synthetic data (synthetic/staged)",
  "Thực phẩm bảo vệ sức khỏe (TPBVSK)": "Health supplements (TPBVSK)",
  "Tải lại dữ liệu": "Reload data",
};
