/** HTTP failures never trigger offline fallback; only a failed network transport does. */
export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status;
  }
}

export async function request(path, options = {}, fetcher = fetch) {
  let response;
  try {
    response = await fetcher(`/api${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    throw new ApiError("Không kết nối được API. Kiểm tra dịch vụ rồi thử lại.");
  }
  if (!response.ok) {
    const messages = {
      503: "Chức năng này chưa sẵn sàng trên backend. Chưa lưu thay đổi.",
      409: "Phiên bản đã thay đổi. Hãy tải lại lịch sử trước khi tiếp tục.",
      422: "Dữ liệu chưa đúng cấu trúc yêu cầu. Kiểm tra hồ sơ và thử lại.",
      401: "Phiên demo đã hết hạn. Hãy kết nối lại tài khoản mẫu.",
      403: "Tài khoản mẫu không có quyền thực hiện thao tác này.",
      404: "Không tìm thấy dữ liệu hoặc tính năng chưa được bật.",
    };
    throw new ApiError(
      messages[response.status] ||
        `Không thực hiện được yêu cầu (${response.status}).`,
      response.status,
    );
  }
  return response.json();
}

/** @returns {Promise<{bundle: object, history: object|null, historyError: string, offline: boolean, mode: string}>} */
export async function loadWorkspace(fetcher = fetch, headers = {}) {
  const [dossier, log] = await Promise.allSettled([
    request("/demo", { headers }, fetcher),
    request("/history", { headers }, fetcher),
  ]);
  if (dossier.status === "rejected") {
    if (!(dossier.reason instanceof ApiError) || dossier.reason.status !== 0)
      throw dossier.reason;
    const response = await fetcher("/demo.json");
    if (!response.ok)
      throw new ApiError(
        "Không tải được bản mẫu ngoại tuyến.",
        response.status,
      );
    return {
      bundle: await response.json(),
      history: null,
      historyError: "",
      offline: true,
      mode: "fixture",
    };
  }
  return {
    bundle: dossier.value,
    history: log.status === "fulfilled" ? log.value : null,
    historyError: log.status === "rejected" ? log.reason.message : "",
    offline: false,
    mode: log.status === "fulfilled" ? log.value.mode || "fixture" : "fixture",
  };
}

export function resultLabel(result) {
  if (!result) return "Chưa chạy kiểm tra";
  if (result.findings.length)
    return `${result.findings.length} mục cần xem xét`;
  if (
    result.status === "no_issue_found" &&
    result.mode === "live" &&
    result.applicability === "applies" &&
    !result.validator_rejections?.length &&
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
