import { describe, it, expect, vi } from "vitest";
import { createResearchClient } from "./research.js";

describe("private research client", () => {
  it("loads a session and uses its token for the mounted API", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: "test-session" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [{ id: "WS-example" }],
      });
    const client = createResearchClient(fetcher);
    expect(await client.connect()).toBe(true);
    expect(await client.list()).toEqual([{ id: "WS-example" }]);
    expect(fetcher.mock.calls[1][0]).toBe("/workspace-research/api/workspaces");
    expect(fetcher.mock.calls[1][1].headers["X-Workspace-Token"]).toBe(
      "test-session",
    );
  });

  it("does not substitute fixture data when the feature is off or API fails", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: false, status: 404 });
    const client = createResearchClient(fetcher);
    expect(await client.connect()).toBe(false);
    await expect(client.list()).rejects.toThrow("chưa kết nối");
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("uploads the workbook as bytes and starts live research only on request", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: "test-session" }),
      })
      .mockResolvedValue({
        ok: true,
        json: async () => ({ id: "WS-example" }),
      });
    const client = createResearchClient(fetcher);
    await client.connect();
    const file = new Blob(["synthetic workbook"]);
    await client.create("Nhà trọ ví dụ", file);
    expect(fetcher.mock.calls[1][0]).toContain("research=true");
    expect(fetcher.mock.calls[1][1].body).toBe(file);
    await client.start("WS-example");
    expect(JSON.parse(fetcher.mock.calls[2][1].body)).toEqual({ live: true });
  });
});
