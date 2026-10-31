// Private local research uses its own server-issued token, never the reviewer session.
async function readMessageStream(response, onEvent) {
  if (!response.body) throw new Error("API chưa trả về luồng phản hồi.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let turn = null;
  function dispatch(frame) {
    let type = "message";
    const lines = [];
    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith("event:")) type = line.slice(6).trim();
      if (line.startsWith("data:")) lines.push(line.slice(5).trimStart());
    }
    if (!lines.length) return;
    const data = JSON.parse(lines.join("\n"));
    if (type === "error") throw new Error(data.message || "Luồng phản hồi bị gián đoạn.");
    if (type === "done") turn = data.turn;
    onEvent({ ...data, type });
  }
  try {
    while (!turn) {
      const chunk = await reader.read();
      buffer += decoder.decode(chunk.value, { stream: !chunk.done });
      let separator;
      while ((separator = /\r?\n\r?\n/.exec(buffer))) {
        dispatch(buffer.slice(0, separator.index));
        buffer = buffer.slice(separator.index + separator[0].length);
        if (turn) break;
      }
      if (chunk.done) break;
    }
    if (!turn) throw new Error("Kết nối kết thúc trước khi câu trả lời được lưu. Hãy thử lại.");
    return turn;
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

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
        422: "Dữ liệu gửi chưa đúng định dạng. Kiểm tra yêu cầu rồi thử lại.",
      };
      const error = new Error(
        messages[response.status] || "Chưa tải được dữ liệu workspace.",
      );
      error.status = response.status;
      throw error;
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
            signal: AbortSignal.timeout(300000),
          },
        )
      ).json(),
    async streamMessage(id, conversationId, question, onEvent, signal) {
      const path = `workspaces/${encodeURIComponent(id)}/conversations/${encodeURIComponent(conversationId)}/messages`;
      const options = {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
            body: JSON.stringify({ question }),
            signal: signal
              ? AbortSignal.any([signal, AbortSignal.timeout(300000)])
              : AbortSignal.timeout(300000),
      };
      let response;
      try {
        response = await call(`${path}/stream`, options);
      } catch (error) {
        if (error.status !== 404 && error.status !== 405) throw error;
        const turn = await (await call(path, options)).json();
        onEvent?.({ type: "done", turn });
        return turn;
      }
      return readMessageStream(response, onEvent || (() => {}));
    },
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
    context: async (id, documentId, enabled, redactPersonal) =>
      (
        await call(
          `workspaces/${encodeURIComponent(id)}/documents/${encodeURIComponent(documentId)}/context`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled, ...(typeof redactPersonal === "boolean" ? { redact_personal: redactPersonal } : {}) }),
          },
        )
      ).json(),
    refreshExtraction: async (id, documentId) =>
      (await call(`workspaces/${encodeURIComponent(id)}/documents/${encodeURIComponent(documentId)}/extract`, {
        method: "POST",
      })).json(),
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
