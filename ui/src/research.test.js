import { describe, it, expect, vi } from "vitest";
import { createResearchClient } from "./research.js";

describe("private research client", () => {
  it("scopes conversations and sends messages with a 90-second timeout", async () => {
    const timeout = vi.spyOn(AbortSignal, "timeout");
    const fetcher = vi
      .fn()
      .mockResolvedValue({
        ok: true,
        json: async () => ({ token: "session", chat_enabled: true }),
      });
    const client = createResearchClient(fetcher);
    await client.connect();
    expect(client.chatEnabled()).toBe(true);
    await client.conversations("WS-test");
    await client.newConversation("WS-test");
    await client.conversation("WS-test", "CONV-test");
    await client.message("WS-test", "CONV-test", "Question from user");
    expect(fetcher.mock.calls[1][0]).toBe(
      "/workspace-research/api/workspaces/WS-test/conversations",
    );
    expect(fetcher.mock.calls[2][1].method).toBe("POST");
    expect(fetcher.mock.calls[3][0]).toBe(
      "/workspace-research/api/workspaces/WS-test/conversations/CONV-test",
    );
    expect(fetcher.mock.calls[4][0]).toBe(
      "/workspace-research/api/workspaces/WS-test/conversations/CONV-test/messages",
    );
    expect(JSON.parse(fetcher.mock.calls[4][1].body)).toEqual({
      question: "Question from user",
    });
    expect(timeout).toHaveBeenCalledWith(90000);
    timeout.mockRestore();
  });
  it("keeps both document collections on the same workspace API without starting research", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ token: "session" }),
    });
    const client = createResearchClient(fetcher);
    await client.connect();
    await client.createWorkspace("Any company", "From the user");
    const file = Object.assign(new Blob(["Synthetic document"]), {
      name: "source.txt",
    });
    await client.uploadDocument("WS-example", "business", file);
    await client.uploadDocument("WS-example", "legal", file);
    expect(fetcher.mock.calls[1][0]).toBe("/workspace-research/api/workspaces");
    expect(fetcher.mock.calls[2][0]).toBe(
      "/workspace-research/api/workspaces/WS-example/documents/business",
    );
    expect(fetcher.mock.calls[3][0]).toBe(
      "/workspace-research/api/workspaces/WS-example/documents/legal",
    );
    expect(fetcher.mock.calls[2][1].body).toBe(file);
    expect(
      fetcher.mock.calls
        .slice(1)
        .some(([path]) => path.includes("research=true")),
    ).toBe(false);
    expect(client.profileEnabled()).toBe(false);
  });
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
