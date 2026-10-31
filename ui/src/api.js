import { N_, translate } from "./i18n.jsx";

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
      // Chat may use two model attempts, each configured up to 180 seconds.
      signal: AbortSignal.timeout(path === "/chat" ? 390000 : 15000),
    });
  } catch (error) {
    if (error?.name === "TimeoutError") {
      throw new ApiError(
        N_("API phản hồi quá thời gian chờ. Hãy tải lại trạng thái trước khi thử lại."),
      );
    }
    throw new ApiError(N_("Không kết nối được API. Kiểm tra dịch vụ rồi thử lại."));
  }
  if (!response.ok) {
    const messages = {
      503: N_("Chức năng này chưa sẵn sàng trên backend. Chưa lưu thay đổi."),
      409: N_("Phiên bản đã thay đổi. Hãy tải lại lịch sử trước khi tiếp tục."),
      422: N_("Dữ liệu chưa đúng cấu trúc yêu cầu. Kiểm tra hồ sơ và thử lại."),
      401: N_("Phiên demo đã hết hạn. Hãy kết nối lại tài khoản mẫu."),
      403: N_("Tài khoản mẫu không có quyền thực hiện thao tác này."),
      404: N_("Không tìm thấy dữ liệu hoặc tính năng chưa được bật."),
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
        N_("Không tải được bản mẫu ngoại tuyến."),
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

const vietnamese = (text, values) => translate("vi", text, values);

/** Pass the screen's translator as `t` so the label follows the chosen language. */
export function resultLabel(result, t = vietnamese) {
  if (!result) return t("Chưa chạy kiểm tra");
  if (result.findings.length)
    return t("{count} mục cần xem xét", { count: result.findings.length });
  if (
    result.status === "no_issue_found" &&
    result.mode === "live" &&
    result.applicability === "applies" &&
    !result.validator_rejections?.length &&
    result.rules_checked.length &&
    !result.skipped_rule_ids.length
  ) {
    return t("No issue found under {count} encoded rules", {
      count: result.rules_checked.length,
    });
  }
  return t("Chưa đủ thông tin");
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
