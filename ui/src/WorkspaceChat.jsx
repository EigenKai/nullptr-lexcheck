import React, { useEffect, useRef, useState } from "react";
import { researchClient } from "./research.js";
import "./workspace-chat.css";

const statusLabel = {
  answered: "LLM · Thông tin tham khảo",
  not_enough_information: "Chưa đủ thông tin",
  unavailable: "Model chưa sẵn sàng",
};

export function WorkspaceConversations({
  workspaceId,
  selectedId,
  refresh,
  disabled,
  onSelect,
}) {
  const [threads, setThreads] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    setThreads([]);
    setError("");
    if (!workspaceId || workspaceId === "new") return;
    const controller = new AbortController();
    let active = true;
    researchClient
      .conversations(workspaceId, controller.signal)
      .then((value) => {
        if (!active) return;
        if (!Array.isArray(value))
          throw Error("Không đọc được danh sách hội thoại từ API.");
        setThreads(value);
      })
      .catch((e) => {
        if (active && e.name !== "AbortError") setError(e.message);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [workspaceId, refresh]);
  return (
    <section className="workspace-recents" aria-label="Trò chuyện gần đây">
      <div className="nav-caption">TRÒ CHUYỆN GẦN ĐÂY</div>
      {error ? (
        <p className="recent-hint" role="status">
          {error}
        </p>
      ) : threads.length ? (
        threads.map((thread) => (
          <button
            key={thread.id}
            disabled={disabled}
            aria-current={selectedId === thread.id ? "page" : undefined}
            onClick={() => onSelect(thread.id)}
          >
            <span>{thread.title || "Hội thoại chưa có tiêu đề"}</span>
            <small>
              {thread.turn_count} lượt ·{" "}
              {new Date(
                thread.updated_at || thread.created_at,
              ).toLocaleDateString("vi-VN")}
            </small>
          </button>
        ))
      ) : (
        <p className="recent-hint">
          Chưa có hội thoại đã lưu trong workspace này.
        </p>
      )}
    </section>
  );
}

export function WorkspaceChat({
  workspace,
  conversationId,
  newConversationNonce,
  onConversationSelected,
  onTurnSaved,
  onBusyChange,
  onNavigate,
  onDocumentsChanged = () => {},
}) {
  const workspaceId = workspace.id;
  const [conversation, setConversation] = useState(null);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTurn, setActiveTurn] = useState(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [documentPreview, setDocumentPreview] = useState(null);
  const [documentBusy, setDocumentBusy] = useState(false);
  const alive = useRef(true);
  const createdHere = useRef(null);
  const messagesEnd = useRef(null);
  const documents = workspace.documents || [];
  const companyCount = documents.filter(
    (doc) => doc.collection === "business" && doc.context_enabled,
  ).length;
  const lawCount = documents.filter((doc) => doc.collection === "legal").length;
  const turns =
    conversation && (!conversationId || conversation.id === conversationId)
      ? conversation.turns || []
      : [];
  const shownTurn =
    turns.find((turn) => turn.id === activeTurn) || turns.at(-1);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      onBusyChange(false);
    };
  }, [workspaceId, onBusyChange]);
  useEffect(() => {
    setQuestion("");
    setError("");
    setActiveTurn(null);
    if (!conversationId) {
      setConversation(null);
      return;
    }
    if (createdHere.current === conversationId) {
      createdHere.current = null;
      return;
    }
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setConversation(null);
    researchClient
      .conversation(workspaceId, conversationId, controller.signal)
      .then((value) => {
        if (!active) return;
        if (value.workspace_id !== workspaceId || value.id !== conversationId)
          throw Error("Hội thoại không thuộc workspace đang chọn.");
        setConversation(value);
      })
      .catch((e) => {
        if (active && e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [workspaceId, conversationId, newConversationNonce]);
  useEffect(() => {
    messagesEnd.current?.scrollIntoView({
      block: "nearest",
      behavior: "smooth",
    });
  }, [turns.length, busy]);

  async function send(event) {
    event.preventDefault();
    const text = question.trim();
    if (!text || busy || loading || !researchClient.chatEnabled()) return;
    if (conversationId && conversation?.id !== conversationId) return;
    setBusy(true);
    onBusyChange(true);
    setError("");
    setQuestion("");
    setPendingQuestion(text);
    try {
      let target = conversation;
      if (!target) {
        target = await researchClient.newConversation(workspaceId);
        if (!alive.current) return;
        if (target.workspace_id !== workspaceId)
          throw Error("Hội thoại không thuộc workspace đang chọn.");
        createdHere.current = target.id;
        setConversation(target);
        onConversationSelected(target.id);
      }
      const turn = await researchClient.message(workspaceId, target.id, text);
      if (!alive.current) return;
      setConversation((previous) => ({
        ...target,
        ...previous,
        turns: [
          ...(previous?.id === target.id
            ? previous.turns || []
            : target.turns || []),
          turn,
        ],
      }));
      setActiveTurn(turn.id);
      onTurnSaved();
    } catch (e) {
      if (alive.current) {
        setError(e.message);
        setQuestion(text);
      }
    } finally {
      if (alive.current) {
        setBusy(false);
        setPendingQuestion("");
        onBusyChange(false);
      }
    }
  }
  async function download(citation) {
    setError("");
    try {
      const blob = await researchClient.original(
        workspaceId,
        citation.document_id,
      );
      if (!alive.current) return;
      const url = URL.createObjectURL(blob),
        link = document.createElement("a");
      link.href = url;
      link.download = citation.title;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
      if (alive.current) setError(e.message);
    }
  }

  async function documentAction(callback) {
    setDocumentBusy(true);
    setError("");
    try {
      const value = await callback();
      if (alive.current) setDocumentPreview(value);
      await onDocumentsChanged();
    } catch (e) {
      if (alive.current) setError(e.message);
    } finally {
      if (alive.current) setDocumentBusy(false);
    }
  }

  return (
    <div className="workspace-chat-layout">
      <section
        className={`workspace-chat-main ${turns.length ? "with-turns" : ""}`}
        aria-label="Trợ lý Lex"
      >
        {!turns.length && !loading ? (
          <div className="workspace-chat-welcome">
            <div className="eyebrow">
              <span className="status-dot" /> KHÔNG GIAN DOANH NGHIỆP ·{" "}
              {workspace.name}
            </div>
            <section className="hero">
              <div className="hero-copy">
                <h1>
                  Chào bạn,
                  <br />
                  mình kiểm tra
                  <br />
                  <em>điều gì hôm nay?</em>
                </h1>
                <p>
                  Hỏi từ tài liệu doanh nghiệp đã chọn và nguồn luật trong
                  workspace. Bạn cũng có thể hỏi đáp thông thường; nguồn tham khảo là tùy chọn.
                </p>
              </div>
              <div className="mascot-wrap">
                <img
                  className="mascot"
                  src="/assets/mascot.png"
                  alt="Lex cầm kính lúp và bảng kiểm"
                  width="240"
                  height="240"
                />
              </div>
            </section>
            <div className="workspace-chat-doclinks">
              <button onClick={() => onNavigate("business")}>
                Tài liệu doanh nghiệp <span>{companyCount} bản được chọn</span>
              </button>
              <button onClick={() => onNavigate("legal")}>
                Tài liệu luật <span>{lawCount} bản trong kho</span>
              </button>
            </div>
          </div>
        ) : null}
        {loading && (
          <p className="workspace-chat-loading" role="status">
            Đang tải hội thoại đã lưu từ API…
          </p>
        )}
        <div className="workspace-chat-turns" aria-live="polite">
          {turns.map((turn) => (
            <article className="workspace-chat-turn" key={turn.id}>
              <div className="workspace-chat-question">
                <span>Bạn</span>
                <p>{turn.question}</p>
              </div>
              <div className="workspace-chat-answer">
                <div className="workspace-chat-answer-head">
                  <b>Lex</b>
                  <span className={`chat-answer-status ${turn.status}`}>
                    {statusLabel[turn.status] || turn.status}
                  </span>
                </div>
                <p>{turn.answer || "API chưa trả về nội dung câu trả lời."}</p>
                <div className="workspace-chat-citations">
                  {(turn.citations || []).map((citation, index) => (
                    <button
                      key={`${citation.document_id}-${index}`}
                      onClick={() => {
                        setActiveTurn(turn.id);
                        setEvidenceOpen(true);
                      }}
                    >
                      [{index + 1}] {citation.title} · tr. {citation.page}
                    </button>
                  ))}
                </div>
                <div className="workspace-chat-provenance">
                  <span>
                    {turn.provenance?.model || "Chưa có model"} ·{" "}
                    {turn.provenance?.status || turn.status}
                  </span>
                  <button
                    onClick={() => {
                      setActiveTurn(turn.id);
                      setEvidenceOpen(true);
                    }}
                  >
                    Xem nguồn & công cụ
                  </button>
                </div>
              </div>
            </article>
          ))}
          {busy && (
            <div className="workspace-chat-waiting" role="status">
              <p>Bạn: {pendingQuestion}</p>
              <b>Lex đang xử lý yêu cầu…</b>
              <span>
                Đang chờ kết quả tìm/đọc chỉ mục tài liệu và phản hồi từ model.
                Dấu vết công cụ sẽ hiện khi API trả về.
              </span>
            </div>
          )}
          <div ref={messagesEnd} />
        </div>
        <div className="workspace-chat-compose-area">
          {error && (
            <p className="research-error" role="alert">
              {error}
            </p>
          )}
          {!researchClient.chatEnabled() && (
            <p className="workspace-chat-hint">
              Chat bằng model đang tắt hoặc chưa kết nối. Bạn vẫn có thể xem tài
              liệu và lịch sử đã lưu; không có câu trả lời mẫu thay thế.
            </p>
          )}
          {!companyCount && (
            <p className="workspace-chat-hint">
              Để hỏi về doanh nghiệp, mở{" "}
              <button onClick={() => onNavigate("business")}>
                Tài liệu doanh nghiệp
              </button>
              , xem nội dung file và chọn làm ngữ cảnh model.
            </p>
          )}
          {documents.some((doc) => doc.collection === "business") && (
            <details className="chat-document-selection" open={!companyCount}>
              <summary>Đã có trong workspace · chọn tài liệu cho chat</summary>
              {documents.filter((doc) => doc.collection === "business").map((doc) => (
                <div className="chat-document-row" key={doc.id}>
                  <span><b>{doc.name}</b><small>{doc.id} · v{doc.version} · {doc.context_enabled ? "Đã chọn" : "Chưa chọn cho model"}</small></span>
                  <button className="button" disabled={busy || documentBusy} onClick={() => documentAction(() => researchClient.document(workspaceId, doc.id))}>
                    Xem và chọn nội dung file
                  </button>
                </div>
              ))}
              <p className="research-note">File đã được lưu; không cần tải lên lại. Model đọc nội dung file được chọn; che thông tin cá nhân là tùy chọn.</p>
            </details>
          )}
          {documentPreview && (
            <section className="chat-document-preview" aria-label="Duyệt tài liệu cho model">
              <div className="section-head"><h3>{documentPreview.name} · v{documentPreview.version}</h3><button className="button" onClick={() => setDocumentPreview(null)}>Đóng</button></div>
              <p>{documentPreview.redact_personal === false ? "Nội dung đầy đủ từ file đã chọn, gồm văn bản và các ô dữ liệu." : "Đang dùng bản có che thông tin cá nhân. Tắt tùy chọn bên dưới để dùng nội dung đầy đủ."}</p>
              <label className="document-checkbox"><input type="checkbox" checked={documentPreview.redact_personal !== false} disabled={busy || documentBusy} onChange={(event) => documentAction(() => researchClient.context(workspaceId, documentPreview.id, documentPreview.context_enabled, event.target.checked))} />Che thông tin cá nhân (tùy chọn)</label>
              {documentPreview.method === "xlsx-cell-text-limited" && <button className="button" disabled={busy || documentBusy} onClick={() => documentAction(() => researchClient.refreshExtraction(workspaceId, documentPreview.id))}>Cập nhật bản trích XLSX an toàn</button>}
              {(documentPreview.model_pages || []).map((text, index) => <details key={index}><summary>Trang / Sheet {index + 1}</summary><pre>{text || "Chưa có text để đọc"}</pre></details>)}
              <button className="button primary" disabled={busy || documentBusy || !documentPreview.model_pages?.some((text) => text.trim()) || documentPreview.method === "xlsx-cell-text-limited"} onClick={() => documentAction(() => researchClient.context(workspaceId, documentPreview.id, !documentPreview.context_enabled))}>
                {documentBusy ? "Đang lưu…" : documentPreview.context_enabled ? "Bỏ chọn khỏi model" : "Dùng nội dung file cho chat"}
              </button>
            </section>
          )}
          <form className="composer" onSubmit={send}>
            <textarea
              aria-label="Câu hỏi cho Lex"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Hỏi Lex từ những tài liệu workspace đã lưu…"
              maxLength={2500}
              rows={3}
              disabled={busy || documentBusy || loading || !researchClient.chatEnabled()}
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  !event.shiftKey &&
                  !event.nativeEvent.isComposing
                ) {
                  event.preventDefault();
                  event.currentTarget.form.requestSubmit();
                }
              }}
            />
            <div className="composer-bottom">
              <span className="composer-context">
                Workspace hiện tại · Nguồn tham khảo tùy chọn
              </span>
              <button
                className="send"
                type="submit"
                aria-label="Gửi câu hỏi"
                disabled={
                  busy ||
                  loading ||
                  !question.trim() ||
                  !researchClient.chatEnabled()
                }
              >
                {busy ? "…" : "↑"}
              </button>
            </div>
          </form>
          <div className="composer-note">
            LLM đưa thông tin tham khảo, không tự xác nhận hiệu lực nguồn luật
            hoặc quyết định thay người duyệt.
          </div>
          <button
            className="workspace-chat-evidence-toggle"
            onClick={() => setEvidenceOpen((value) => !value)}
            aria-expanded={evidenceOpen}
          >
            Nguồn & tri thức{" "}
            {shownTurn?.citations?.length
              ? `(${shownTurn.citations.length})`
              : ""}
          </button>
        </div>
      </section>
      <aside
        className={`workspace-chat-evidence ${evidenceOpen ? "open" : ""}`}
        aria-label="Nguồn trích dẫn và công cụ"
      >
        <div className="workspace-chat-evidence-title">
          <span>TRI THỨC ĐƯỢC KẾT NỐI</span>
          <button
            aria-label="Đóng nguồn trích dẫn"
            onClick={() => setEvidenceOpen(false)}
          >
            ×
          </button>
        </div>
        {shownTurn ? (
          <>
            <h2>Nguồn của câu trả lời</h2>
            <p className="workspace-chat-evidence-note">
              Trích dẫn từ lượt đang chọn. Nguồn luật vẫn cần xác minh hiệu lực
              và cách áp dụng.
            </p>
            {(shownTurn.citations || []).length ? (
              shownTurn.citations.map((citation, index) => (
                <article
                  className="workspace-chat-source"
                  key={`${citation.document_id}-${index}`}
                >
                  <small>
                    [{index + 1}]{" "}
                    {citation.collection === "legal"
                      ? "Tài liệu luật · chưa xác minh"
                      : citation.collection === "metadata"
                        ? "Chỉ mục workspace"
                        : "Tài liệu doanh nghiệp"}
                  </small>
                  <h3>{citation.title}</h3>
                  <p>
                    {citation.worksheet || `Trang ${citation.page}`} · Phiên bản {citation.version}
                    {citation.cells?.length ? ` · Ô ${citation.cells.join(", ")}` : ""}
                  </p>
                  <blockquote>{citation.quote}</blockquote>
                  {/^https:\/\//.test(citation.official_url || "") && (
                    <p className="workspace-chat-source-link">
                      <a href={citation.official_url} target="_blank" rel="noopener noreferrer">
                        Mở nguồn chính thức ↗
                      </a>
                      <small>Chưa xác minh hiệu lực và phạm vi áp dụng</small>
                    </p>
                  )}
                  <code>
                    Đoạn [{citation.start}, {citation.end}) · Unicode
                    <br />
                    SHA-256 {citation.sha256}
                  </code>
                  {/^FILE-[a-f0-9]{24}$/.test(citation.document_id) && (
                    <button onClick={() => download(citation)}>
                      Tải tài liệu nguồn ↗
                    </button>
                  )}
                </article>
              ))
            ) : (
              <div className="workspace-chat-source-empty">
                Lượt này không kèm nguồn tham khảo. Bạn có thể yêu cầu nguồn nếu cần.
              </div>
            )}
            <details className="workspace-chat-trace">
              <summary>Dấu vết công cụ</summary>
              {(shownTurn.tool_trace || []).map((tool, index) => (
                <div key={index}>
                  <b>{tool.tool}</b>
                  {tool.query && <p>{tool.query}</p>}
                  {tool.document_id && <code>{tool.document_id}</code>}
                  {(tool.sources || []).filter((source) => /^https:\/\//.test(source.url || "")).map((source) => (
                    <p className="workspace-chat-source-link" key={source.url}>
                      <a href={source.url} target="_blank" rel="noopener noreferrer">
                        {source.url}
                      </a>
                      <small>
                        {source.retrieval_status === "ingested_unverified"
                          ? "Đã đọc nội dung nguồn"
                          : source.retrieval_status === "search_observation_only"
                            ? "Kết quả tìm kiếm web · Chưa mở bản gốc"
                            : "Chưa đọc được nội dung nguồn"}
                      </small>
                    </p>
                  ))}
                  {tool.hits !== undefined && (
                    <small>
                      {Array.isArray(tool.hits)
                        ? tool.hits.length
                        : typeof tool.hits === "number"
                          ? tool.hits
                          : "Chưa ghi nhận số"}{" "}
                      kết quả
                    </small>
                  )}
                </div>
              ))}
              {!shownTurn.tool_trace?.length && (
                <p>API chưa trả về dấu vết công cụ.</p>
              )}
            </details>
            <div className="workspace-chat-index-meta">
              <p>Model: {shownTurn.provenance?.model || "Chưa có"}</p>
              <p>
                Trạng thái: {shownTurn.provenance?.status || shownTurn.status}
              </p>
              <p>
                Lượt gọi model:{" "}
                {shownTurn.provenance?.model_calls ?? "Chưa ghi nhận"}
              </p>
              {shownTurn.provenance?.agent_model_calls !== undefined && (
                <p>
                  Trợ lý: {shownTurn.provenance.agent_model_calls} · Tìm kiếm: {shownTurn.provenance.public_search_model_calls ?? "Chưa ghi nhận"}
                  {shownTurn.provenance.public_search_http_calls !== undefined && ` · Brave HTTP: ${shownTurn.provenance.public_search_http_calls}`}
                </p>
              )}
              <code>
                Index: {shownTurn.provenance?.index_sha256 || "Chưa ghi nhận"}
              </code>
            </div>
          </>
        ) : (
          <div className="workspace-chat-evidence-intro">
            <div className="workspace-chat-network-mark">◈</div>
            <h2>Tri thức luôn ở đây.</h2>
            <p>
              Chat mới vẫn dùng những tài liệu doanh nghiệp bạn đã chọn và nguồn
              luật workspace đã lưu.
            </p>
            <dl>
              <dt>Tài liệu doanh nghiệp được chọn</dt>
              <dd>{companyCount}</dd>
              <dt>Tài liệu luật trong kho</dt>
              <dd>{lawCount}</dd>
            </dl>
            <button onClick={() => onNavigate("knowledge")}>
              Khám phá kho tri thức ↗
            </button>
            <p className="workspace-chat-evidence-note">
              Nguồn, nguyên văn và dấu vết công cụ sẽ xuất hiện khi bạn chọn một
              câu trả lời.
            </p>
          </div>
        )}
      </aside>
    </div>
  );
}
