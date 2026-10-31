import { describe, expect, it, vi } from "vitest";
import { request, resultLabel, evidenceParts, loadWorkspace } from "./api.js";

describe("review safety", () => {
  it("does not render uncertain applicability as a clean result", () => {
    expect(
      resultLabel({
        mode: "live",
        status: "no_issue_found",
        rules_checked: ["R-01"],
        findings: [],
        skipped_rule_ids: [],
        applicability: "not_enough_information",
      }),
    ).toBe("Chưa đủ thông tin");
  });
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
        mode: "live",
        applicability: "applies",
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

const demo = {
  request: { profile: { company_id: "CO-LIVE" }, records: [], versions: [] },
};
const response = (body, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => body,
});

describe("workspace loading", () => {
  it("usesLiveApiWhenAvailable", async () => {
    const fetcher = vi.fn(async (path) =>
      response(path === "/api/demo" ? demo : { checks: [] }),
    );
    const loaded = await loadWorkspace(fetcher);
    expect(loaded.bundle).toEqual(demo);
    expect(loaded.offline).toBe(false);
    expect(fetcher).not.toHaveBeenCalledWith("/demo.json");
  });
  it("keeps live dossier when only history fails", async () => {
    const fetcher = vi.fn(async (path) =>
      path === "/api/history" ? response({}, 503) : response(demo),
    );
    const loaded = await loadWorkspace(fetcher);
    expect(loaded.bundle).toEqual(demo);
    expect(loaded.offline).toBe(false);
    expect(loaded.historyError).toContain("chưa sẵn sàng");
  });
  it("does not replace a 401 or 503 dossier response with bundled data", async () => {
    for (const status of [401, 503]) {
      const fetcher = vi.fn(async () => response({}, status));
      await expect(loadWorkspace(fetcher)).rejects.toThrow();
      expect(fetcher.mock.calls.some(([p]) => p === "/demo.json")).toBe(false);
    }
  });
  it("showsFixtureBadgeOnStaticFallback", async () => {
    const fetcher = vi.fn(async (path) => {
      if (path.startsWith("/api/")) throw new TypeError("network disconnected");
      return response(demo);
    });
    const loaded = await loadWorkspace(fetcher);
    expect(loaded.offline).toBe(true);
    expect(loaded.mode).toBe("fixture");
  });
});
