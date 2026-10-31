export async function request(path, options = {}, fetcher = fetch) {
  let response;
  try {
    response = await fetcher(`/api${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    throw new Error("Không kết nối được API. Kiểm tra dịch vụ rồi thử lại.");
  }
  if (!response.ok) {
    const messages = {
      503: "Chức năng này chưa sẵn sàng trên backend. Chưa lưu thay đổi.",
      409: "Phiên bản đã thay đổi. Hãy tải lại lịch sử trước khi tiếp tục.",
      422: "Dữ liệu chưa đúng cấu trúc yêu cầu. Kiểm tra hồ sơ và thử lại.",
    };
    throw new Error(
      messages[response.status] ||
        `Không thực hiện được yêu cầu (${response.status}).`,
    );
  }
  return response.json();
}

export function resultLabel(result) {
  if (!result) return "Chưa chạy kiểm tra";
  if (result.findings.length)
    return `${result.findings.length} mục cần xem xét`;
  if (
    result.status === "no_issue_found" &&
    result.rules_checked.length &&
    !result.skipped_rule_ids.length
  ) {
    return `No issue found under ${result.rules_checked.length} encoded rules`;
  }
  return "Chưa đủ thông tin";
}

export function evidenceParts(text, evidence) {
  const { start, end, quote } = evidence;
  // Python contract offsets count Unicode code points, rather than UTF-16 units.
  const chars = Array.from(text);
  if (
    !Number.isInteger(start) ||
    !Number.isInteger(end) ||
    start < 0 ||
    end <= start ||
    end > chars.length
  )
    return null;
  if (chars.slice(start, end).join("") !== quote) return null;
  return [chars.slice(0, start).join(""), quote, chars.slice(end).join("")];
}
