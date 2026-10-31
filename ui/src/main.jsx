import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/nunito-sans";
import "./prototype.css";
import "./style.css";
import { request, resultLabel, evidenceParts } from "./api.js";
import { researchClient } from "./research.js";
import { DocumentWorkspace } from "./DocumentWorkspace.jsx";
import { WorkspaceChat, WorkspaceConversations } from "./WorkspaceChat.jsx";

const initialWorkspace =
  location.hash.match(/^#workspace\/(WS-[a-f0-9]{24}|new)$/)?.[1] || "demo";
const researchTabs = [
  ["chat", "Trợ lý Lex"],
  ["overview", "Tổng quan"],
  ["business", "Tài liệu doanh nghiệp"],
  ["legal", "Tài liệu luật"],
  ["knowledge", "Kho tri thức"],
  ["settings", "Thông tin workspace"],
];

const paths = {
  chat: "M5 4h14v14H9l-5 3V4ZM8 8h8M8 12h5",
  library: "M4 4h4v16H4zM11 4h4v16h-4zM18 4l3 15",
  check: "M8 3h8v4H8zM8 5H5v16h14V5h-3M8 13l3 3 5-6",
  refresh: "M20 7V3l-4 1M20 4A9 9 0 0 0 4 8M4 17v4l4-1M4 20a9 9 0 0 0 16-4",
  clock: "M12 8v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0",
  network:
    "M7 6l11 4M7 7l4 12M18 11l-6 8M8 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0M22 11a3 3 0 1 1-6 0 3 3 0 0 1 6 0M14 20a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
  menu: "M4 6h16M4 12h16M4 18h16",
  panel: "M4 4h16v16H4zM15 4v16",
  file: "M5 3h9l5 5v13H5zM14 3v6h5M8 13h8M8 17h5",
  arrow: "M7 17 17 7M7 7h10v10",
  plus: "M12 5v14M5 12h14",
};
function Icon({ name }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d={paths[name] || paths.file} />
    </svg>
  );
}
const tabs = [
  ["chat", "Trợ lý Lex"],
  ["knowledge", "Kho tri thức"],
  ["reviews", "Rà soát hồ sơ"],
  ["updates", "Cập nhật nguồn"],
  ["history", "Lịch sử quyết định"],
];
const recordNames = {
  dossier: "Hồ sơ công bố",
  marketing: "Nội dung quảng cáo",
  evidence_index: "Mục lục chứng từ",
  ad_confirmation: "Hồ sơ xác nhận quảng cáo",
  customer_script: "Kịch bản chăm sóc",
  scientific_evidence: "Tài liệu khoa học",
};
const ruleNames = {
  warning: "Cảnh báo bắt buộc",
  uses: "Đối chiếu công dụng",
  confirmation: "Bằng chứng xác nhận",
  endorsement: "Hình ảnh / bảo chứng",
  medicinal: "Tuyên bố chữa bệnh",
};
const date = (value) =>
  value ? new Date(value).toLocaleString("vi-VN") : "Chưa có";
function Page({ eyebrow, title, action, children }) {
  return (
    <div className="content-page appear">
      <div className="page-eyebrow">{eyebrow}</div>
      <div className="page-title-row">
        <h1 className="page-title">{title}</h1>
        {action}
      </div>
      {children}
    </div>
  );
}
function Badge({ children, neutral = false }) {
  return <span className={`badge ${neutral ? "" : "warn"}`}>{children}</span>;
}
function App() {
  const [view, setView] = useState("chat");
  const [conversationId, setConversationId] = useState(null);
  const [chatRefresh, setChatRefresh] = useState(0);
  const [newConversationNonce, setNewConversationNonce] = useState(0);
  const [chatBusy, setChatBusy] = useState(false);
  const [workspaceId, setWorkspaceId] = useState(initialWorkspace);
  const [researchReady, setResearchReady] = useState(false);
  const [researchWorkspaces, setResearchWorkspaces] = useState([]);
  const [bundle, setBundle] = useState(null);
  const [draft, setDraft] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState(null);
  const [offline, setOffline] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState(null);
  const [mobile, setMobile] = useState(false);
  const [panel, setPanel] = useState(false);
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [oldNew, setOldNew] = useState(false);
  const [note, setNote] = useState("");
  const [owner, setOwner] = useState("marketing");
  const isResearchWorkspace = researchReady || workspaceId !== "demo";
  const currentTabs = isResearchWorkspace ? researchTabs : tabs;
  const effectiveWorkspaceId =
    workspaceId === "demo"
      ? researchWorkspaces.find(
          (workspace) => workspace.reference_key === "fixture:CO-DEMO",
        )?.id
      : workspaceId;
  const currentWorkspace = researchWorkspaces.find(
    (workspace) => workspace.id === effectiveWorkspaceId,
  );
  const workspaceName = currentWorkspace?.name;
  const refreshConversations = useCallback(
    () => setChatRefresh((value) => value + 1),
    [],
  );
  const createdConversation = useCallback((id) => {
    setConversationId(id);
    setChatRefresh((value) => value + 1);
  }, []);
  const selectConversation = useCallback((id) => {
    setConversationId(id);
    setView("chat");
    setMobile(false);
  }, []);
  const loadResearchWorkspaces = useCallback(async () => {
    try {
      setResearchWorkspaces(await researchClient.list());
    } catch (e) {
      setError(e.message);
    }
  }, []);
  function chooseWorkspace(id) {
    setWorkspaceId(id);
    setView(id === "new" ? "overview" : "chat");
    setConversationId(null);
    setChatBusy(false);
    setNewConversationNonce((value) => value + 1);
    setSelected(null);
    setPanel(false);
    setError("");
    setNotice("");
    setMobile(false);
    window.history.replaceState(
      null,
      "",
      location.pathname +
        location.search +
        (id === "demo" ? "" : `#workspace/${id}`),
    );
  }
  const go = (next) => {
    setView(next);
    setMobile(false);
    setError("");
    setNotice("");
  };
  async function load() {
    setBusy("Đang tải hồ sơ và lịch sử từ API…");
    setError("");
    try {
      const [demo, log] = await Promise.all([
        request("/demo"),
        request("/history"),
      ]);
      setBundle(demo);
      setDraft(structuredClone(demo.request));
      setHistory(log);
      setOffline(false);
    } catch {
      try {
        const response = await fetch("/demo.json");
        if (!response.ok) throw new Error();
        const demo = await response.json();
        setBundle(demo);
        setDraft(structuredClone(demo.request));
        setHistory(null);
        setOffline(true);
      } catch {
        setError("Không tải được hồ sơ mẫu. Hãy khởi động API rồi tải lại.");
      }
    } finally {
      setBusy("");
    }
  }
  useEffect(() => {
    load();
  }, []);
  useEffect(() => {
    let active = true;
    researchClient.connect().then(async (connected) => {
      if (!active) return;
      setResearchReady(connected);
      if (connected) {
        try {
          await researchClient.ensureDemo();
          await loadResearchWorkspaces();
          if (active) setView("chat");
        } catch (e) {
          if (active) setError(e.message);
        }
      } else if (initialWorkspace !== "demo") {
        setError(
          "Chưa kết nối được API workspace. Không dùng dữ liệu mẫu thay thế cho workspace đang chọn.",
        );
      }
    });
    return () => {
      active = false;
    };
  }, [loadResearchWorkspaces]);
  useEffect(() => {
    const escape = (e) => {
      if (e.key === "Escape") {
        setMobile(false);
        setPanel(false);
      }
    };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, []);
  async function act(label, callback) {
    if (busy) return;
    setBusy(label);
    setError("");
    setNotice("");
    try {
      await callback();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }
  function inspect(item) {
    setSelected(item);
    setPanel(true);
  }
  function ask(text) {
    if (!text.trim()) return;
    setError(
      "Chat chưa kết nối API workspace. Kiểm tra cấu hình server và tải lại trang.",
    );
  }
  const versions = bundle?.request.versions || [];
  const current = selected?.type === "finding" ? selected.value : null;
  const check = selected?.check || result;
  const clausePool = check?.clause_snapshots?.length
    ? check.clause_snapshots
    : bundle?.clauses || [];
  const clause = current
    ? clausePool.find((c) => c.id === current.clause_version_id)
    : selected?.type === "clause"
      ? selected.value
      : null;
  function updateText(id, text) {
    setDraft((prev) => ({
      ...prev,
      versions: prev.versions.map((v) =>
        v.id === id ? { ...v, text: text.normalize("NFC") } : v,
      ),
    }));
    setResult(null);
    setSelected(null);
  }
  async function decide(action) {
    if (!note.trim()) {
      setError("Nhập ghi chú trước khi lưu quyết định.");
      return;
    }
    await act("Đang lưu quyết định của reviewer…", async () => {
      await request("/decisions", {
        method: "POST",
        body: JSON.stringify({
          check_id: check.id,
          finding_id: current.id,
          action,
          actor: "reviewer",
          note: note.trim(),
          ...(action === "assign" ? { owner } : {}),
        }),
      });
      setHistory(await request("/history"));
      setNotice("Đã lưu quyết định vào lịch sử API.");
      setNote("");
    });
  }
  const evidencePanel = (
    <>
      <div className="panel-heading">
        <Icon name="network" />
        {selected ? "CHI TIẾT & BẰNG CHỨNG" : "TRI THỨC ĐƯỢC KẾT NỐI"}
        <button
          className="icon-button close-panel"
          onClick={() => setPanel(false)}
          aria-label="Đóng bảng bằng chứng"
        >
          ×
        </button>
      </div>
      {selected && (
        <button className="back-link" onClick={() => setSelected(null)}>
          ← Tổng quan tri thức
        </button>
      )}
      {!selected && (
        <>
          <div className="panel-intro">
            <h2>
              Mỗi phát hiện,
              <br />
              đều có điểm tựa.
            </h2>
            <p>Hồ sơ, điều khoản và quyết định cùng giữ đường truy lại.</p>
          </div>
          <div className="trace-map">
            <div>
              Điều khoản <small>Phiên bản & ngày hiệu lực</small>
            </div>
            <span>↓ DERIVED_FROM</span>
            <div>
              Rule <small>Trạng thái kiểm chứng</small>
            </div>
            <span>↓ EVIDENCE</span>
            <div>
              Hồ sơ doanh nghiệp{" "}
              <small>Bản gốc → phát hiện → người quyết định</small>
            </div>
          </div>
          <div className="panel-callout">
            <b>Phạm vi hiện tại</b>
            <p>
              Pack thực phẩm bảo vệ sức khỏe. Dữ liệu công ty được dựng cho
              demo. Chưa có đăng nhập hoặc phân quyền backend.
            </p>
          </div>
          <p className="footnote">
            {bundle?.rules.filter((r) => r.enabled).length || 0} rule đã bật ·
            LLM tắt
          </p>
        </>
      )}
      {selected?.type === "record" && (
        <>
          <h2>{recordNames[selected.value.kind]}</h2>
          <code>{selected.value.id}</code>
          {versions
            .filter((v) => v.record_id === selected.value.id)
            .map((v) => (
              <section key={v.id}>
                <h3>
                  {v.id} · v{v.version}
                </h3>
                <p className="record-text">{v.text}</p>
                <p className="footnote">Nhận: {date(v.received_at)}</p>
                <p>Tham chiếu: {v.reference_ids.join(", ") || "Chưa có"}</p>
              </section>
            ))}
        </>
      )}
      {current && (
        <>
          <h2>
            {current.rule_id} · v{current.rule_version}
          </h2>
          <Badge neutral={current.status === "needs_evidence"}>
            {current.source === "llm"
              ? "Suggestion · Người duyệt quyết định"
              : "Rule · Kiểm tra bằng code"}
          </Badge>
          <p>{current.message}</p>
          <p>
            Mức độ: {current.severity} · Trạng thái: {current.status}
          </p>
          {current.evidence.map((ev, i) => {
            const source = check?.snapshot.versions.find(
              (v) => v.id === ev.record_version_id,
            );
            const parts = source ? evidenceParts(source.text, ev) : null;
            return (
              <section className="evidence-step" key={i}>
                <b>{ev.record_version_id}</b>
                {ev.kind === "missing_field" ? (
                  <p>
                    Không tìm thấy trường <code>{ev.field}</code> trong các hồ
                    sơ đã kết nối.
                  </p>
                ) : (
                  <>
                    <p className="record-text">
                      {parts ? (
                        <>
                          {parts[0]}
                          <mark>{parts[1]}</mark>
                          {parts[2]}
                        </>
                      ) : (
                        ev.quote
                      )}
                    </p>
                    <small>
                      {ev.kind === "span"
                        ? `Vị trí ${ev.start}–${ev.end}`
                        : ev.kind === "cell"
                          ? `${ev.sheet} · ${ev.cell}`
                          : `Trang ${ev.page}`}
                    </small>
                    {!parts && ev.kind === "span" && (
                      <p>Chưa xác nhận vị trí trích dẫn.</p>
                    )}
                  </>
                )}
              </section>
            );
          })}
        </>
      )}
      {clause && (
        <section className="clause">
          <Badge neutral>
            {clause.verification_status === "verified"
              ? "Nguồn đã kiểm chứng"
              : "Nguồn chờ kiểm chứng"}
          </Badge>
          <h3>
            {clause.document} · {clause.article}
          </h3>
          <code>{clause.id}</code>
          <p>
            Từ {clause.valid_from} đến{" "}
            {clause.valid_to || "chưa ghi ngày kết thúc"} · {clause.in_force}
          </p>
          <blockquote>{current?.clause_quote || clause.text}</blockquote>
          <a
            href={
              /^https?:\/\//.test(clause.source_url)
                ? clause.source_url
                : undefined
            }
            target="_blank"
            rel="noreferrer"
          >
            Mở văn bản nguồn ↗
          </a>
          <p className="footnote">{clause.status_note}</p>
        </section>
      )}
      {current && (
        <section className="decision-form">
          <h3>Quyết định của reviewer</h3>
          <label htmlFor="decisionNote">Ghi chú xử lý</label>
          <textarea
            id="decisionNote"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <label htmlFor="owner">Người phụ trách</label>
          <select
            id="owner"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
          >
            <option value="marketing">Marketing</option>
            <option value="legal">Pháp chế</option>
            <option value="document_control">Quản lý hồ sơ</option>
          </select>
          <div className="action-row">
            {[
              ["confirm", "Xác nhận phát hiện"],
              ["reject", "Bác bỏ"],
              ["assign", "Giao xử lý"],
            ].map(([a, label]) => (
              <button
                className="button secondary"
                disabled={!!busy || offline}
                key={a}
                onClick={() => decide(a)}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="footnote">
            Đóng việc cần một lượt kiểm tra lại mới. Đọc phát hiện không tự đóng
            việc.
          </p>
        </section>
      )}
    </>
  );
  return (
    <>
      <a className="skip" href="#main">
        Đến nội dung chính
      </a>
      <div className="app">
        {mobile && (
          <button
            className="nav-scrim"
            aria-label="Đóng menu"
            onClick={() => setMobile(false)}
          />
        )}
        <aside className={`sidebar ${mobile ? "open" : ""}`}>
          <a
            className="brand"
            href="#"
            onClick={(e) => {
              e.preventDefault();
              go("chat");
            }}
          >
            <span className="brand-mark">◈</span>lexcheck
            <span className="brand-dot">.</span>
          </a>
          <div className="workspace">
            <span className="workspace-logo">N</span>
            {researchReady ? (
              <label className="workspace-select">
                <select
                  aria-label="Chọn workspace"
                  value={workspaceId}
                  onChange={(event) => chooseWorkspace(event.target.value)}
                >
                  <option value="demo">NULLPTR Demo · TPBVSK</option>
                  {researchWorkspaces
                    .filter(
                      (workspace) =>
                        workspace.reference_key !== "fixture:CO-DEMO",
                    )
                    .map((workspace) => (
                      <option key={workspace.id} value={workspace.id}>
                        {workspace.name}
                      </option>
                    ))}
                  <option value="new">+ Tạo workspace</option>
                </select>
                <small>
                  {currentWorkspace?.synthetic
                    ? "Dữ liệu mẫu tổng hợp"
                    : "Hồ sơ riêng cục bộ"}
                </small>
              </label>
            ) : (
              <span>
                <b>NULLPTR Demo</b>
                <small>Doanh nghiệp TPBVSK · Dữ liệu mẫu</small>
              </span>
            )}
          </div>
          <button
            className="new-chat"
            disabled={
              chatBusy ||
              (isResearchWorkspace &&
                (!effectiveWorkspaceId || effectiveWorkspaceId === "new"))
            }
            onClick={() => {
              if (isResearchWorkspace) {
                setConversationId(null);
                setNewConversationNonce((value) => value + 1);
                go("chat");
                return;
              }
              setMessages([]);
              go("chat");
            }}
          >
            <Icon name="plus" />
            Cuộc trò chuyện mới
          </button>
          <div className="nav-caption">KHÔNG GIAN LÀM VIỆC</div>
          <nav aria-label="Điều hướng chính">
            {currentTabs.map(([key, label]) => (
              <button
                className={`nav-item ${view === key ? "active" : ""}`}
                aria-current={view === key ? "page" : undefined}
                key={key}
                onClick={() => go(key)}
              >
                <Icon
                  name={
                    key === "knowledge"
                      ? "library"
                      : key === "reviews"
                        ? "check"
                        : key === "updates"
                          ? "refresh"
                          : key === "history"
                            ? "clock"
                            : "chat"
                  }
                />
                {label}
              </button>
            ))}
          </nav>
          {isResearchWorkspace && (
            <WorkspaceConversations
              workspaceId={effectiveWorkspaceId}
              selectedId={conversationId}
              refresh={chatRefresh}
              disabled={chatBusy}
              onSelect={selectConversation}
            />
          )}
          <div className="sidebar-bottom">
            <div className="memory-note">
              <Icon name="network" />
              <b>Tri thức có phiên bản.</b>
              <p>
                Kết quả luôn đi cùng hồ sơ và nguồn được dùng ở thời điểm kiểm
                tra.
              </p>
            </div>
            <div className="profile">
              <span className="avatar">R</span>
              <span>
                <b>Reviewer mẫu</b>
                <small>Chế độ trải nghiệm</small>
              </span>
            </div>
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <div className="breadcrumb">
              <button
                className="icon-button mobile-menu"
                onClick={() => setMobile(!mobile)}
                aria-label="Mở menu"
                aria-expanded={mobile}
              >
                <Icon name="menu" />
              </button>
              <span className="muted">Không gian làm việc</span>
              <span className="slash">/</span>
              <b>
                {currentTabs.find((t) => t[0] === view)?.[1] || "Tổng quan"}
              </b>
            </div>
            <div className="top-actions">
              <span className="demo-pill">
                {isResearchWorkspace
                  ? currentWorkspace?.synthetic
                    ? "Dữ liệu mẫu tổng hợp"
                    : "Workspace riêng"
                  : offline
                    ? "Mẫu ngoại tuyến"
                    : "Dữ liệu tổng hợp"}
              </span>
              {!isResearchWorkspace && (
                <button
                  className="icon-button"
                  onClick={() => setPanel(!panel)}
                  aria-label="Mở bằng chứng và tri thức"
                >
                  <Icon name="panel" />
                </button>
              )}
            </div>
          </header>
          <div className="status-strip">
            <span>{isResearchWorkspace ? "WORKSPACE" : "TPBVSK"}</span>
            <span>
              {isResearchWorkspace
                ? `${workspaceName || "Workspace mới"} · Dữ liệu từ kho tài liệu/API`
                : offline
                  ? "API mất kết nối · Chỉ xem bản mẫu đi kèm"
                  : "API kết nối · Backend hiện ở chế độ fixture"}
            </span>
            <button
              onClick={isResearchWorkspace ? loadResearchWorkspaces : load}
              disabled={!!busy}
            >
              Tải lại
            </button>
          </div>
          {busy && (
            <div className="feedback" role="status">
              {busy}
            </div>
          )}
          {error && (
            <div className="feedback error" role="alert">
              {error}
            </div>
          )}
          {notice && (
            <div className="feedback" role="status">
              {notice}
            </div>
          )}
          <div
            className={`body-layout ${isResearchWorkspace ? "research-body" : ""}`}
          >
            <main id="main" tabIndex="-1">
              {isResearchWorkspace ? (
                effectiveWorkspaceId &&
                view === "chat" &&
                effectiveWorkspaceId !== "new" &&
                currentWorkspace ? (
                  <WorkspaceChat
                    key={`${effectiveWorkspaceId}:${newConversationNonce}`}
                    workspace={currentWorkspace}
                    conversationId={conversationId}
                    newConversationNonce={newConversationNonce}
                    onConversationSelected={createdConversation}
                    onTurnSaved={refreshConversations}
                    onBusyChange={setChatBusy}
                    onNavigate={go}
                  />
                ) : effectiveWorkspaceId ? (
                  <DocumentWorkspace
                    key={effectiveWorkspaceId}
                    id={effectiveWorkspaceId}
                    view={view}
                    onNavigate={go}
                    onUpdated={loadResearchWorkspaces}
                    onCreated={(workspace) => {
                      setResearchWorkspaces((previous) => [
                        ...previous,
                        workspace,
                      ]);
                      chooseWorkspace(workspace.id);
                    }}
                  />
                ) : (
                  <p className="content-page" role="status">
                    Đang tải workspace từ API…
                  </p>
                )
              ) : !bundle ? (
                <Page title="Kết nối hồ sơ">
                  <p>
                    {busy || "Chưa có dữ liệu. Bấm Tải lại để thử kết nối."}
                  </p>
                </Page>
              ) : (
                <>
                  {view === "chat" && (
                    <div className="chat-page">
                      <div className="eyebrow">
                        <span className="status-dot" />
                        KHÔNG GIAN DOANH NGHIỆP · CO-DEMO
                      </div>
                      {!messages.length ? (
                        <>
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
                                Cùng Lex tìm đúng căn cứ,
                                <br />
                                hiểu rõ hồ sơ và tiếp nối công việc.
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
                          <div className="context-line">
                            <Icon name="network" />
                            <b>{versions.length} phiên bản hồ sơ</b>
                            <span>·</span>
                            <button onClick={() => go("knowledge")}>
                              Xem kho tri thức ↗
                            </button>
                          </div>
                          <div className="suggestion-label">
                            BẮT ĐẦU TỪ MỘT VIỆC CỤ THỂ
                          </div>
                          <div className="suggestions">
                            {[
                              [
                                "check",
                                "Rà soát nội dung",
                                "Đối chiếu hồ sơ công bố",
                                () => go("reviews"),
                              ],
                              [
                                "library",
                                "Hỏi từ kho tri thức",
                                "Tìm hồ sơ và nguồn đang có",
                                () => ask("Có hồ sơ nào trong kho?"),
                              ],
                              [
                                "refresh",
                                "Có gì vừa thay đổi?",
                                "So sánh công dụng v1 / v2",
                                () => go("updates"),
                              ],
                              [
                                "clock",
                                "Tiếp tục việc còn dở",
                                "Xem quyết định đã ghi nhận",
                                () => go("history"),
                              ],
                            ].map(([i, t, sub, fn]) => (
                              <button
                                className="suggestion"
                                key={t}
                                onClick={fn}
                              >
                                <span>
                                  <Icon name={i} />
                                </span>
                                <div>
                                  <b>{t}</b>
                                  <small>{sub}</small>
                                </div>
                                <span className="arrow">↗</span>
                              </button>
                            ))}
                          </div>
                          <div className="section-head">
                            <h2>Tài liệu bạn đang làm việc</h2>
                            <button onClick={() => go("knowledge")}>
                              Xem tất cả ↗
                            </button>
                          </div>
                          <div className="file-list">
                            {bundle.request.records.slice(0, 2).map((r) => (
                              <button
                                className="file-row"
                                key={r.id}
                                onClick={() =>
                                  inspect({ type: "record", value: r })
                                }
                              >
                                <span className="file-icon">
                                  <Icon name="file" />
                                </span>
                                <span className="file-info">
                                  <b>{recordNames[r.kind]}</b>
                                  <small>
                                    {r.id} · {r.product_id}
                                  </small>
                                </span>
                                <Badge neutral>Mẫu</Badge>
                              </button>
                            ))}
                          </div>
                        </>
                      ) : (
                        <>
                          <h1 className="chat-title">Hỏi từ kho tri thức</h1>
                          <div className="messages" aria-live="polite">
                            {messages.map((m, i) => (
                              <React.Fragment key={i}>
                                <div className="message user">{m.question}</div>
                                <div className="message assistant">
                                  <div className="assistant-heading">
                                    <img
                                      src="/assets/mascot.png"
                                      alt=""
                                      width="30"
                                      height="30"
                                    />
                                    Lex{" "}
                                    <Badge neutral>Tóm tắt dữ liệu mẫu</Badge>
                                  </div>
                                  <p>{m.answer}</p>
                                  <button
                                    className="button secondary"
                                    onClick={() => go("knowledge")}
                                  >
                                    Xem hồ sơ nguồn ↗
                                  </button>
                                </div>
                              </React.Fragment>
                            ))}
                          </div>
                        </>
                      )}
                      <div className="composer-area">
                        <form
                          className="composer"
                          onSubmit={(e) => {
                            e.preventDefault();
                            ask(prompt);
                          }}
                        >
                          <label className="sr-only" htmlFor="prompt">
                            Nhập câu hỏi cho Lex
                          </label>
                          <textarea
                            id="prompt"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Hỏi về hồ sơ, công dụng hoặc việc cần xử lý…"
                            rows="2"
                          />
                          <div className="composer-bottom">
                            <span className="composer-context">
                              <Icon name="network" />
                              Kho tri thức CO-DEMO
                            </span>
                            <button
                              className="send"
                              type="submit"
                              aria-label="Gửi câu hỏi"
                            >
                              ↑
                            </button>
                          </div>
                        </form>
                        <p className="composer-note">
                          Trả lời theo kịch bản từ dữ liệu mẫu · Chưa kết nối AI
                          chat
                        </p>
                      </div>
                    </div>
                  )}
                  {view === "knowledge" && (
                    <Page
                      eyebrow="BỘ NHỚ CỦA DOANH NGHIỆP"
                      title="Kho tri thức"
                    >
                      <p className="page-description">
                        Hồ sơ doanh nghiệp và điều khoản pháp luật, mỗi nguồn
                        một phiên bản rõ ràng.
                      </p>
                      <div className="metrics">
                        <div className="metric">
                          <strong>{bundle.request.records.length}</strong>
                          <small>Hồ sơ mẫu</small>
                        </div>
                        <div className="metric">
                          <strong>{bundle.rules.length}</strong>
                          <small>Rule trong pack</small>
                        </div>
                        <div className="metric">
                          <strong>
                            {bundle.rules.filter((r) => r.enabled).length}
                          </strong>
                          <small>Rule đã bật</small>
                        </div>
                      </div>
                      <label htmlFor="docSearch">
                        Tìm hồ sơ hoặc điều khoản
                      </label>
                      <input
                        className="search full"
                        id="docSearch"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Tên hồ sơ, mã phiên bản…"
                      />
                      <h2>Hồ sơ doanh nghiệp</h2>
                      <div className="document-table">
                        {bundle.request.records
                          .filter((r) =>
                            `${r.id} ${recordNames[r.kind]} ${r.title}`
                              .toLocaleLowerCase("vi")
                              .includes(query.toLocaleLowerCase("vi")),
                          )
                          .map((r) => (
                            <button
                              className="doc-row doc-button"
                              key={r.id}
                              onClick={() =>
                                inspect({ type: "record", value: r })
                              }
                            >
                              <span className="doc-row-main">
                                <span className="file-icon">
                                  <Icon name="file" />
                                </span>
                                <span>
                                  <b>{recordNames[r.kind]}</b>
                                  <small>
                                    {r.id} · {r.product_id} · v
                                    {
                                      versions.find((v) => v.record_id === r.id)
                                        ?.version
                                    }
                                  </small>
                                </span>
                              </span>
                              <Badge neutral>Dữ liệu tổng hợp</Badge>
                            </button>
                          ))}
                      </div>
                      <h2>Điều khoản & rule</h2>
                      {bundle.rules
                        .filter(
                          (r) =>
                            `${r.id} ${ruleNames[r.check_type]}`
                              .toLowerCase()
                              .includes(query.toLowerCase()) ||
                            bundle.clauses
                              .find((c) => c.id === r.clause_version_id)
                              ?.document.toLowerCase()
                              .includes(query.toLowerCase()),
                        )
                        .map((r) => (
                          <button
                            className="source-card full doc-button"
                            key={r.id}
                            onClick={() =>
                              inspect({
                                type: "clause",
                                value: bundle.clauses.find(
                                  (c) => c.id === r.clause_version_id,
                                ),
                              })
                            }
                          >
                            <Icon name="file" />
                            <span>
                              <b>
                                {r.id} · {ruleNames[r.check_type]}
                              </b>
                              <small>
                                {r.clause_version_id} · v{r.version}
                              </small>
                            </span>
                            <Badge>
                              {r.enabled ? "Đang bật" : "Chờ kiểm chứng"}
                            </Badge>
                          </button>
                        ))}
                      <p className="footnote">
                        Nhập PDF, OCR, Drive và phân quyền tài liệu chưa được
                        triển khai trên backend.
                      </p>
                    </Page>
                  )}
                  {view === "reviews" && (
                    <Page
                      eyebrow="TỪ HỒ SƠ ĐẾN PHÁT HIỆN CÓ CĂN CỨ"
                      title="Rà soát hồ sơ"
                      action={
                        <button
                          className="button"
                          disabled={!!busy || offline}
                          onClick={() =>
                            act("Đang đối chiếu hồ sơ qua API…", async () => {
                              const r = await request("/check", {
                                method: "POST",
                                body: JSON.stringify(draft),
                              });
                              setResult(r);
                              setSelected(null);
                              setHistory(await request("/history"));
                            })
                          }
                        >
                          <Icon name="check" />
                          Chạy kiểm tra
                        </button>
                      }
                    >
                      <p className="page-description">
                        Xác nhận bối cảnh và nội dung trước khi đối chiếu. Người
                        duyệt quyết định từng phát hiện.
                      </p>
                      <section className="form-panel">
                        <h2>01 · Hồ sơ hoạt động</h2>
                        <div className="form-grid">
                          <label>
                            Nhóm sản phẩm
                            <select
                              value={draft.profile.product_group}
                              onChange={(e) => {
                                setDraft({
                                  ...draft,
                                  profile: {
                                    ...draft.profile,
                                    product_group: e.target.value,
                                  },
                                });
                                setResult(null);
                              }}
                            >
                              <option value="tpbvsk">
                                Thực phẩm bảo vệ sức khỏe
                              </option>
                              <option value="other">Nhóm khác</option>
                              <option value="unknown">Chưa rõ</option>
                            </select>
                          </label>
                          <label>
                            Hoạt động
                            <select
                              value={draft.profile.activity}
                              onChange={(e) => {
                                setDraft({
                                  ...draft,
                                  profile: {
                                    ...draft.profile,
                                    activity: e.target.value,
                                  },
                                });
                                setResult(null);
                              }}
                            >
                              <option value="advertising">Quảng cáo</option>
                              <option value="label_only">Chỉ có nhãn</option>
                              <option value="unknown">Chưa rõ</option>
                            </select>
                          </label>
                        </div>
                        <label className="check-label">
                          <input
                            type="checkbox"
                            checked={draft.profile.confirmed}
                            onChange={(e) => {
                              setDraft({
                                ...draft,
                                profile: {
                                  ...draft.profile,
                                  confirmed: e.target.checked,
                                },
                              });
                              setResult(null);
                            }}
                          />
                          Đã xác nhận bối cảnh công ty mẫu
                        </label>
                        <p className="footnote">
                          Vai trò: nhà phân phối trong nước · Ngày rà soát{" "}
                          {draft.review_date} · LLM tắt
                        </p>
                      </section>
                      <section className="form-panel">
                        <h2>02 · Nội dung cần đối chiếu</h2>
                        {draft.target_version_ids.map((id) => (
                          <label className="text-field" key={id}>
                            {id}
                            <textarea
                              value={
                                draft.versions.find((v) => v.id === id).text
                              }
                              onChange={(e) => updateText(id, e.target.value)}
                              rows="5"
                            />
                          </label>
                        ))}
                        <p className="footnote">
                          API fixture chỉ nhận bộ mẫu gốc. Nội dung chỉnh sửa
                          được gửi tới API và có thể nhận trạng thái chưa sẵn
                          sàng.
                        </p>
                        <button
                          className="back-link"
                          onClick={() => {
                            setDraft(structuredClone(bundle.request));
                            setResult(null);
                            setSelected(null);
                          }}
                        >
                          Khôi phục bộ mẫu gốc
                        </button>
                      </section>
                      <section className="result-section" aria-live="polite">
                        <h2>03 · {resultLabel(result)}</h2>
                        {result ? (
                          <>
                            <div className="action-row">
                              <Badge neutral>
                                {result.mode === "fixture"
                                  ? "Fixture · Xem trước"
                                  : "Kết quả API"}
                              </Badge>
                              <Badge neutral>
                                {result.rules_checked.length} rule đã chạy
                              </Badge>
                              <Badge>
                                {result.skipped_rule_ids.length} rule chưa kiểm
                              </Badge>
                            </div>
                            <p>
                              {result.mode === "fixture"
                                ? "Các rule đang chờ chủ sở hữu kiểm chứng nguồn. Đây là dữ liệu xem trước, chưa phải kết quả kiểm tra pháp lý."
                                : result.summary}
                            </p>
                            {result.skipped_rule_ids.length > 0 && (
                              <p>
                                Chưa kiểm: {result.skipped_rule_ids.join(", ")}
                              </p>
                            )}
                            {result.findings.map((f) => (
                              <button
                                className="review-card finding-button"
                                key={f.id}
                                onClick={() =>
                                  inspect({
                                    type: "finding",
                                    value: f,
                                    check: result,
                                  })
                                }
                              >
                                <Badge neutral={f.status === "needs_evidence"}>
                                  {f.source === "llm" ? "Suggestion" : "Rule"} ·{" "}
                                  {f.status}
                                </Badge>
                                <h3>
                                  {f.rule_id} · {f.message}
                                </h3>
                                <p>
                                  {f.record_version_id} · {f.clause_version_id}
                                </p>
                                <span>Xem bằng chứng & quyết định ↗</span>
                              </button>
                            ))}
                          </>
                        ) : (
                          <p>
                            Chạy kiểm tra để nhận kết quả từ API. Không có phát
                            hiện hiển thị trước khi kiểm tra.
                          </p>
                        )}
                      </section>
                    </Page>
                  )}
                  {view === "updates" && (
                    <Page
                      eyebrow="THAY ĐỔI MỘT NGUỒN · KIỂM TRA LẠI PHỤ THUỘC"
                      title="Cập nhật nguồn"
                    >
                      <p className="page-description">
                        Giữ bản cũ, xem nội dung đổi và hàng đợi hồ sơ cần rà
                        soát lại.
                      </p>
                      <div className="source-card">
                        <Icon name="refresh" />
                        <span>
                          <b>Nguồn pháp luật chính thức</b>
                          <small>
                            Chưa kết nối watcher · Chưa có lần kiểm tra thành
                            công
                          </small>
                        </span>
                        <Badge>Chưa kết nối</Badge>
                      </div>
                      <article className="review-card">
                        <Badge neutral>
                          Sự kiện hồ sơ dựng sẵn · Chưa áp dụng
                        </Badge>
                        <h2>Hồ sơ công bố có phiên bản mới</h2>
                        <p>
                          {bundle.event.previous_version_id} →{" "}
                          {bundle.event.new_version.id}
                        </p>
                        <button
                          className="button secondary"
                          onClick={() => setOldNew(!oldNew)}
                          aria-expanded={oldNew}
                        >
                          Xem bản cũ / mới
                        </button>
                        {oldNew && (
                          <div className="diff-grid">
                            <section>
                              <h3>Bản cũ · v1</h3>
                              <p className="record-text">
                                {
                                  versions.find(
                                    (v) =>
                                      v.id === bundle.event.previous_version_id,
                                  )?.text
                                }
                              </p>
                            </section>
                            <section>
                              <h3>Bản mới · v2</h3>
                              <p className="record-text">
                                {bundle.event.new_version.text}
                              </p>
                            </section>
                          </div>
                        )}
                        <p className="footnote">
                          Công dụng được bỏ: Hỗ trợ giảm cholesterol. API quyết
                          định phạm vi ảnh hưởng; UI không tự tạo hàng đợi.
                        </p>
                        <button
                          className="button"
                          disabled={!!busy || offline}
                          onClick={() =>
                            act(
                              "Đang gửi sự kiện và lấy hàng đợi…",
                              async () => {
                                await request("/changes", {
                                  method: "POST",
                                  body: JSON.stringify(bundle.event),
                                });
                                setHistory(await request("/history"));
                                setNotice("API đã ghi nhận thay đổi.");
                              },
                            )
                          }
                        >
                          Gửi sự kiện mẫu tới API
                        </button>
                      </article>
                      <h2>Hàng đợi kiểm tra lại</h2>
                      {history?.queue.length ? (
                        history.queue.map((q) => (
                          <article className="review-card" key={q.id}>
                            <Badge neutral>{q.status}</Badge>
                            <h3>{q.target_version_id}</h3>
                            <p>
                              {q.reason} · Kết quả gốc {q.previous_check_id}
                            </p>
                            <button
                              className="button secondary"
                              disabled={
                                !!busy || offline || q.status !== "queued"
                              }
                              onClick={() =>
                                act(
                                  "Đang kiểm tra lại hồ sơ phụ thuộc…",
                                  async () => {
                                    const r = await request("/rechecks", {
                                      method: "POST",
                                      body: JSON.stringify({
                                        item_id: q.id,
                                        llm_mode: "off",
                                      }),
                                    });
                                    setResult(r);
                                    setHistory(await request("/history"));
                                    setView("reviews");
                                  },
                                )
                              }
                            >
                              Kiểm tra lại
                            </button>
                          </article>
                        ))
                      ) : (
                        <p className="empty-state">
                          {offline
                            ? "Không lấy được hàng đợi khi API mất kết nối."
                            : "API chưa có hồ sơ trong hàng đợi."}
                        </p>
                      )}
                    </Page>
                  )}
                  {view === "history" && (
                    <Page
                      eyebrow="KẾT QUẢ CŨ & QUYẾT ĐỊNH ĐƯỢC GIỮ LẠI"
                      title="Lịch sử quyết định"
                    >
                      <p className="page-description">
                        Mỗi lượt kiểm tra giữ snapshot đầu vào, phiên bản nguồn
                        và quyết định của người duyệt.
                      </p>
                      {!history ? (
                        <p>Chưa lấy được lịch sử từ API.</p>
                      ) : (
                        <>
                          <div className="metrics">
                            <div className="metric">
                              <strong>{history.checks.length}</strong>
                              <small>Lượt kiểm tra</small>
                            </div>
                            <div className="metric">
                              <strong>{history.decisions.length}</strong>
                              <small>Quyết định</small>
                            </div>
                            <div className="metric">
                              <strong>{history.events.length}</strong>
                              <small>Sự kiện</small>
                            </div>
                          </div>
                          {history.checks.map((c) => (
                            <details className="review-card" key={c.id}>
                              <summary>
                                {c.id} · {resultLabel(c)}{" "}
                                <Badge neutral>{c.mode}</Badge>
                              </summary>
                              <p>
                                {date(c.created_at)} · {c.rules_checked.length}{" "}
                                rule đã chạy · LLM {c.model_status}
                              </p>
                              <p>
                                Rule:{" "}
                                {c.rule_snapshots
                                  .map((r) => `${r.id} v${r.version}`)
                                  .join(", ") || "Chưa có rule thực thi"}
                              </p>
                              <p>
                                Phiên bản:{" "}
                                {c.snapshot.versions
                                  .map((v) => v.id)
                                  .join(", ")}
                              </p>
                              {c.findings.map((f) => (
                                <button
                                  className="button secondary"
                                  key={f.id}
                                  onClick={() =>
                                    inspect({
                                      type: "finding",
                                      value: f,
                                      check: c,
                                    })
                                  }
                                >
                                  {f.rule_id} · Xem phát hiện
                                </button>
                              ))}
                              <details>
                                <summary>Snapshot gốc (JSON)</summary>
                                <pre>{JSON.stringify(c, null, 2)}</pre>
                              </details>
                            </details>
                          ))}
                          {history.decisions.length ? (
                            history.decisions.map((d) => (
                              <article className="review-card" key={d.id}>
                                <Badge neutral>{d.task_status}</Badge>
                                <h3>
                                  {d.request.action} · {d.request.finding_id}
                                </h3>
                                <p>{d.request.note}</p>
                                <small>
                                  {d.request.actor} ·{" "}
                                  {d.request.owner || "Chưa giao người xử lý"} ·{" "}
                                  {date(d.created_at)}
                                </small>
                              </article>
                            ))
                          ) : (
                            <p className="empty-state">
                              Chưa có quyết định của reviewer được lưu.
                            </p>
                          )}
                        </>
                      )}
                    </Page>
                  )}
                </>
              )}
            </main>
            {!isResearchWorkspace && (
              <aside
                className={`evidence ${panel ? "open" : ""}`}
                aria-label="Tri thức và bằng chứng"
              >
                {evidencePanel}
              </aside>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

createRoot(document.getElementById("root")).render(<App />);
