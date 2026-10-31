import React from "react";
const paths = {
  chat: "M5 4h14v14H9l-5 3V4ZM8 8h8M8 12h5",
  library: "M4 4h4v16H4zM11 4h4v16h-4zM18 4l3 15",
  check: "M8 3h8v4H8zM8 5H5v16h14V5h-3M8 13l3 3 5-6",
  refresh: "M20 7V3l-4 1M20 4A9 9 0 0 0 4 8M4 17v4l4-1M4 20a9 9 0 0 0 16-4",
  clock: "M12 8v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0",
  network:
    "M7 6l11 4M7 7l4 12M18 11l-6 8M8 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0M22 11a3 3 0 1 1-6 0 3 3 0 0 1 6 0M14 20a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
  menu: "M4 6h16M4 12h16M4 18h16",
  panel: "M4 4h16v16H4zM15 4v16",
  file: "M5 3h9l5 5v13H5zM14 3v6h5M8 13h8M8 17h5",
  arrow: "M7 17 17 7M7 7h10v10",
  plus: "M12 5v14M5 12h14",
};
export function Icon({ name }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d={paths[name] || paths.file} />
    </svg>
  );
}
export const tabs = [
  ["chat", "Trợ lý Lex"],
  ["knowledge", "Kho tri thức"],
  ["reviews", "Rà soát hồ sơ"],
  ["updates", "Cập nhật nguồn"],
  ["history", "Lịch sử quyết định"],
];
export const recordNames = {
  dossier: "Hồ sơ công bố",
  marketing: "Nội dung quảng cáo",
  evidence_index: "Mục lục chứng từ",
  ad_confirmation: "Hồ sơ xác nhận quảng cáo",
  customer_script: "Kịch bản chăm sóc",
  scientific_evidence: "Tài liệu khoa học",
};
export const ruleNames = {
  warning: "Cảnh báo bắt buộc",
  uses: "Đối chiếu công dụng",
  confirmation: "Bằng chứng xác nhận",
  endorsement: "Hình ảnh / bảo chứng",
  medicinal: "Tuyên bố chữa bệnh",
};
export const date = (value) =>
  value
    ? new Date(value).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })
    : "Chưa có";
export function Page({ eyebrow, title, action, children }) {
  return (
    <div className="content-page appear">
      <div className="page-eyebrow">{eyebrow}</div>
      <div className="page-title-row">
        <h1 className="page-title">{title}</h1>
        {action}
      </div>
      {children}
    </div>
  );
}
export function Badge({ children, neutral = false }) {
  return <span className={`badge ${neutral ? "" : "warn"}`}>{children}</span>;
}
