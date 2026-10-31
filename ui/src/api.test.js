import { describe, expect, it, vi } from "vitest";
import { request, resultLabel, evidenceParts } from "./api.js";

describe("review safety", () => {
  it("does not turn zero checks or skipped rules into a clean result", () => {
    expect(
      resultLabel({
        status: "no_issue_found",
        rules_checked: [],
        findings: [],
        skipped_rule_ids: [],
      }),
    ).toBe("Chưa đủ thông tin");
    expect(
      resultLabel({
        status: "no_issue_found",
        rules_checked: ["R-01"],
        findings: [],
        skipped_rule_ids: ["R-02"],
      }),
    ).toBe("Chưa đủ thông tin");
    expect(
      resultLabel({
        status: "no_issue_found",
        rules_checked: ["R-01"],
        findings: [],
        skipped_rule_ids: [],
      }),
    ).toBe("No issue found under 1 encoded rules");
  });
  it("highlights only evidence that matches its original Unicode offsets", () => {
    expect(
      evidenceParts("Hỗ trợ tiêu hóa.", { start: 0, end: 6, quote: "Hỗ trợ" }),
    ).toEqual(["", "Hỗ trợ", " tiêu hóa."]);
    expect(
      evidenceParts("Hỗ trợ tiêu hóa.", {
        start: 0,
        end: 6,
        quote: "chữa bệnh",
      }),
    ).toBeNull();
    expect(
      evidenceParts("Hỗ trợ", { kind: "missing_field", field: "warning" }),
    ).toBeNull();
  });
  it("reports unavailable actions without claiming they were saved", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    await expect(request("/decisions", {}, fetcher)).rejects.toThrow(
      "chưa sẵn sàng",
    );
  });
});
