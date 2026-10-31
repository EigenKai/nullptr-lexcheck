// Private local research uses its own server-issued token, never the reviewer session.
export function createResearchClient(fetcher = fetch) {
  let token = null;
  let profileEnabled = false;
  let chatEnabled = false;
  const base = "/workspace-research";
  async function call(path, options = {}) {
    if (!token) throw new Error("Workspace nghiên cứu chưa kết nối.");
    let response;
    try {
      response = await fetcher(`${base}/api/${path}`, {
        ...options,
        headers: { "X-Workspace-Token": token, ...options.headers },
        signal: options.signal || AbortSignal.timeout(20000),
      });
    } catch (error) {
      if (error.name === "AbortError") throw error;
      throw new Error("Không kết nối được API workspace. Hãy thử lại.");
    }
    if (!response.ok) {
      const messages = {
        503: "Model hoặc chức năng chat chưa sẵn sàng. Kiểm tra cấu hình trên server rồi thử lại; không có câu trả lời mẫu thay thế.",
        401: "Phiên nghiên cứu đã đổi. Tải lại trang để kết nối.",
        409: "Yêu cầu trước đang xử lý hoặc dữ liệu đã thay đổi. Chờ rồi thử lại.",
        413: "Workbook vượt giới hạn 15 MB.",
        422: "Yêu cầu hoặc bằng chứng chưa đủ để xử lý. Kiểm tra dữ liệu rồi thử lại.",
      };
      throw new Error(
        messages[response.status] || "Chưa tải được dữ liệu workspace.",
      );
    }
    return response;
  }
  return {
    async connect() {
      try {
        const response = await fetcher(`${base}/session`, {
          signal: AbortSignal.timeout(8000),
        });
        if (!response.ok) return false;
        const session = await response.json();
        token = session.token || null;
        profileEnabled = Boolean(session.profile_enabled);
        chatEnabled = Boolean(session.chat_enabled);
        return Boolean(token);
      } catch {
        return false;
      }
    },
    profileEnabled: () => profileEnabled,
    chatEnabled: () => chatEnabled,
    conversations: async (id, signal) =>
      (
        await call(`workspaces/${encodeURIComponent(id)}/conversations`, {
          signal,
        })
      ).json(),
    newConversation: async (id, title) =>
      (
        await call(`workspaces/${encodeURIComponent(id)}/conversations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(title ? { title } : {}),
        })
      ).json(),
    conversation: async (id, conversationId, signal) =>
      (
        await call(
          `workspaces/${encodeURIComponent(id)}/conversations/${encodeURIComponent(conversationId)}`,
          { signal },
        )
      ).json(),
    message: async (id, conversationId, question) =>
      (
        await call(
          `workspaces/${encodeURIComponent(id)}/conversations/${encodeURIComponent(conversationId)}/messages`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
            signal: AbortSignal.timeout(90000),
          },
        )
      ).json(),
    ensureDemo: async () =>
      (await call("workspaces/demo", { method: "POST" })).json(),
    createWorkspace: async (name, description) =>
      (
        await call("workspaces", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, description }),
        })
      ).json(),
    documents: async (id) =>
      (await call(`workspaces/${encodeURIComponent(id)}/documents`)).json(),
    document: async (id, documentId) =>
      (
        await call(
          `workspaces/${encodeURIComponent(id)}/documents/${encodeURIComponent(documentId)}`,
        )
      ).json(),
    uploadDocument: async (id, collection, file) =>
      (
        await call(
          `workspaces/${encodeURIComponent(id)}/documents/${collection}`,
          {
            method: "POST",
            headers: {
              "X-File-Name": encodeURIComponent(file.name),
              "Content-Type": "application/octet-stream",
            },
            body: file,
          },
        )
      ).json(),
    context: async (id, documentId, enabled) =>
      (
        await call(
          `workspaces/${encodeURIComponent(id)}/documents/${encodeURIComponent(documentId)}/context`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled }),
          },
        )
      ).json(),
    original: async (id, documentId) =>
      (
        await call(
          `workspaces/${encodeURIComponent(id)}/documents/${encodeURIComponent(documentId)}/raw`,
        )
      ).blob(),
    profile: async (id) =>
      (
        await call(`workspaces/${encodeURIComponent(id)}/profile`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ live: true }),
        })
      ).json(),
    updateWorkspace: async (id, name, description) =>
      (
        await call(`workspaces/${encodeURIComponent(id)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, description }),
        })
      ).json(),
    list: async () => (await call("workspaces")).json(),
    detail: async (id, signal) =>
      (await call(`workspaces/${encodeURIComponent(id)}`, { signal })).json(),
    create: async (name, file) =>
      (
        await call("workspaces?research=true", {
          method: "POST",
          headers: {
            "X-Workspace-Name": encodeURIComponent(name),
            "Content-Type": "application/octet-stream",
          },
          body: file,
        })
      ).json(),
    start: async (id) =>
      (
        await call(`workspaces/${encodeURIComponent(id)}/research`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ live: true }),
        })
      ).json(),
    rename: async (id, name) =>
      (
        await call(`workspaces/${encodeURIComponent(id)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        })
      ).json(),
    source: async (id, hash) =>
      (
        await call(
          `workspaces/${encodeURIComponent(id)}/sources/${encodeURIComponent(hash)}`,
        )
      ).blob(),
  };
}

export const researchClient = createResearchClient();
