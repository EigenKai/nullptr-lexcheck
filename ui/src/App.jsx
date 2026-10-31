import React, {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { request as apiRequest, loadWorkspace, resultLabel } from "./api.js";
import { Icon, Page, Badge, tabs } from "./components/shared.jsx";
import Review from "./components/Review.jsx";
import Evidence from "./components/Evidence.jsx";
import History from "./components/History.jsx";
import Chat from "./components/Chat.jsx";
import Sources from "./components/Sources.jsx";
import Updates from "./components/Updates.jsx";
import Settings from "./components/Settings.jsx";
import { N_, useLanguage } from "./i18n.jsx";
import { researchClient } from "./research.js";

const DocumentWorkspace = lazy(() =>
  import("./DocumentWorkspace.jsx").then((module) => ({
    default: module.DocumentWorkspace,
  })),
);
const WorkspaceChat = lazy(() =>
  import("./WorkspaceChat.jsx").then((module) => ({
    default: module.WorkspaceChat,
  })),
);
const WorkspaceConversations = lazy(() =>
  import("./WorkspaceChat.jsx").then((module) => ({
    default: module.WorkspaceConversations,
  })),
);
const researchTabs = [
  ["chat", N_("Trợ lý Lex")],
  ["overview", N_("Tổng quan")],
  ["business", N_("Tài liệu doanh nghiệp")],
  ["legal", N_("Tài liệu luật")],
  ["knowledge", N_("Kho tri thức")],
  ["settings", N_("Thông tin workspace")],
];
export default function App() {
  const { t } = useLanguage();
  const [researchReady, setResearchReady] = useState(false);
  const [researchWorkspaces, setResearchWorkspaces] = useState([]);
  const [workspaceId, setWorkspaceId] = useState(
    () =>
      window.location.hash.match(/^#workspace\/(WS-[a-f0-9]{24}|new)$/)?.[1] ||
      "demo",
  );
  const [conversationId, setConversationId] = useState(null);
  const [chatRefresh, setChatRefresh] = useState(0);
  const [newConversationNonce, setNewConversationNonce] = useState(0);
  const [chatBusy, setChatBusy] = useState(false);
  const researchActive = researchReady && workspaceId !== "demo";
  const currentTabs = researchActive ? researchTabs : tabs;
  const currentWorkspace = researchWorkspaces.find(
    (workspace) => workspace.id === workspaceId,
  );
  const refreshResearch = useCallback(async () => {
    try {
      setResearchWorkspaces(await researchClient.list());
    } catch (error) {
      setError(error.message);
    }
  }, []);
  const refreshConversations = useCallback(
    () => setChatRefresh((value) => value + 1),
    [],
  );
  const chooseWorkspace = (id) => {
    setWorkspaceId(id);
    setConversationId(null);
    setNewConversationNonce((value) => value + 1);
    setView(id === "demo" ? "reviews" : id === "new" ? "overview" : "chat");
    setMobile(false);
    setPanel(false);
    setError("");
    window.history.replaceState(
      null,
      "",
      id === "demo" ? "#reviews" : `#workspace/${id}`,
    );
  };
  useEffect(() => {
    let active = true;
    researchClient.connect().then(async (connected) => {
      if (!active || !connected) return;
      try {
        const workspaces = await researchClient.list();
        if (active) {
          setResearchWorkspaces(workspaces);
          setResearchReady(true);
        }
      } catch {
        /* Keep the reviewer UI unchanged when the optional API is unavailable. */
      }
    });
    return () => {
      active = false;
    };
  }, []);
  const [view, setView] = useState("reviews");
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
  const [features, setFeatures] = useState({
    layer0_ready: false,
    layer1: false,
    layer2: false,
    layer3: false,
  });
  const [session, setSession] = useState(null);
  const sessionRef = useRef(null);
  const generation = useRef(0);
  const [closureCheckId, setClosureCheckId] = useState("");
  const [evaluation, setEvaluation] = useState(null);
  const request = (path, options = {}) => {
    const epoch = generation.current;
    return apiRequest(path, {
      ...options,
      headers: {
        ...options.headers,
        ...(sessionRef.current
          ? { Authorization: `Bearer ${sessionRef.current.token}` }
          : {}),
      },
    }).then((data) => {
      if (epoch !== generation.current)
        throw new Error(N_("Tài khoản đã thay đổi. Bỏ kết quả của phiên cũ."));
      return data;
    });
  };
  async function refreshHistory() {
    try {
      const log = await request("/history");
      setHistory(log);
      return log;
    } catch (e) {
      setError(e.message);
      return null;
    }
  }
  const go = (next) => {
    if (!researchActive) window.location.hash = next;
    setView(next);
    setMobile(false);
    setPanel(false);
    setError("");
    setNotice("");
  };
  async function load(user = sessionRef.current?.user_id || "U-MANAGER") {
    const epoch = generation.current;
    setBusy(N_("Đang tải hồ sơ và lịch sử từ API…"));
    setError("");
    try {
      let flags;
      try {
        flags = await apiRequest("/features");
      } catch {
        flags = {
          layer0_ready: false,
          layer1: false,
          layer2: false,
          layer3: false,
        };
      }
      if (!sessionRef.current || sessionRef.current.user_id !== user) {
        try {
          const next = await apiRequest("/session", {
            method: "POST",
            body: JSON.stringify({ user_id: user }),
          });
          if (epoch !== generation.current) return;
          sessionRef.current = next;
          setSession(next);
        } catch (e) {
          if (flags.layer0_ready) throw e;
        }
      }
      let loaded;
      if (user === "U-OPS") {
        const [records, log] = await Promise.all([
          request("/records"),
          request("/history"),
        ]);
        const latest = records.versions.filter(
          (v) => !records.versions.some((n) => n.supersedes === v.id),
        );
        const targets = latest
          .filter(
            (v) =>
              records.records.find((r) => r.id === v.record_id)?.kind ===
              "marketing",
          )
          .map((v) => v.id);
        const snapshot = {
          profile: {
            company_id: "CO-DEMO",
            product_group: "tpbvsk",
            activity: "advertising",
            role: "domestic_distributor",
            confirmed: true,
            synthetic: true,
          },
          records: records.records,
          versions: records.versions,
          target_version_ids: targets,
          context_version_ids: latest
            .filter((v) => !targets.includes(v.id))
            .map((v) => v.id),
          review_date: new Date().toISOString().slice(0, 10),
          llm_mode: "off",
        };
        loaded = {
          bundle: {
            label: "synthetic/staged",
            request: snapshot,
            rules: [],
            clauses: [],
          },
          history: log,
          offline: false,
          historyError: "",
        };
      } else {
        loaded = await loadWorkspace(
          fetch,
          sessionRef.current
            ? { Authorization: `Bearer ${sessionRef.current.token}` }
            : {},
        );
      }
      if (epoch !== generation.current) return;
      setBundle(loaded.bundle);
      setDraft(structuredClone(loaded.bundle.request));
      setHistory(loaded.history);
      setOffline(loaded.offline);
      setError(loaded.historyError);
      setFeatures(
        loaded.offline
          ? { layer0_ready: false, layer1: false, layer2: false, layer3: false }
          : flags,
      );
    } catch (e) {
      if (epoch === generation.current) setError(e.message);
    } finally {
      if (epoch === generation.current) setBusy("");
    }
  }
  function switchUser(user) {
    if (researchActive) chooseWorkspace("demo");
    generation.current += 1;
    sessionRef.current = null;
    setSession(null);
    setBundle(null);
    setDraft(null);
    setHistory(null);
    setResult(null);
    setSelected(null);
    setMessages([]);
    setPrompt("");
    setQuery("");
    setNote("");
    setClosureCheckId("");
    setEvaluation(null);
    setPanel(false);
    setError("");
    setNotice("");
    setView("reviews");
    window.location.hash = "reviews";
    load(user);
  }
  useEffect(() => {
    load();
  }, []);
  useEffect(() => {
    const navigate = () => {
      const next = window.location.hash.slice(1);
      if (next === "main") return;
      if (researchActive && next.startsWith("workspace/")) {
        setView(workspaceId === "new" ? "overview" : "chat");
        return;
      }
      const allowed =
        next === "preferences" ||
        (researchActive ? researchTabs : tabs).some(([key]) => key === next);
      setView(allowed ? next : researchActive ? "chat" : "reviews");
    };
    navigate();
    window.addEventListener("hashchange", navigate);
    return () => window.removeEventListener("hashchange", navigate);
  }, [researchActive, workspaceId]);
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
    const epoch = generation.current;
    setBusy(label);
    setError("");
    setNotice("");
    try {
      await callback();
    } catch (e) {
      if (epoch === generation.current) setError(e.message);
    } finally {
      if (epoch === generation.current) setBusy("");
    }
  }
  function inspect(item) {
    setSelected(item);
    setPanel(true);
  }
  async function showPreview() {
    await act(N_("Đang mở finding minh hoạ…"), async () => {
      const response = await fetch("/finding-preview.json");
      if (!response.ok) throw new Error(N_("Không tải được finding minh hoạ."));
      const preview = await response.json();
      setResult(preview);
      setSelected({
        type: "finding",
        value: preview.findings[0],
        check: preview,
      });
      setPanel(true);
      setNotice(
        N_("Finding minh hoạ từ fixture: chưa chạy engine, không lưu quyết định."),
      );
    });
  }
  async function ask(text) {
    if (!text.trim()) return;
    if (!features.layer1 || offline) {
      setError(N_("Chưa kết nối chatbot. Câu hỏi chưa được gửi."));
      return;
    }
    if (!check) {
      setError(N_("Chọn một kết quả kiểm tra trước khi hỏi."));
      return;
    }
    const question = text.trim();
    const epoch = generation.current;
    await act(N_("Đang tra cứu căn cứ trong kết quả đã chọn…"), async () => {
      const answer = await request("/chat", {
        method: "POST",
        body: JSON.stringify({ check_id: check.id, question }),
      });
      if (epoch === generation.current) {
        setMessages((prev) => [...prev, { question, ...answer }]);
        setPrompt("");
      }
    });
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
      versions: prev.versions.map((v) => (v.id === id ? { ...v, text } : v)),
    }));
    setResult(null);
    setSelected(null);
  }
  async function decide(action, taskFields = {}) {
    const decisionNote =
      action === "acknowledge"
        ? note.trim() || "Đã đọc phát hiện; chưa đóng việc."
        : note.trim();
    if (!decisionNote) {
      setError(N_("Nhập ghi chú trước khi lưu quyết định."));
      return;
    }
    await act(N_("Đang lưu quyết định của reviewer…"), async () => {
      await request("/decisions", {
        method: "POST",
        body: JSON.stringify({
          check_id: check.id,
          finding_id: current.id,
          action,
          actor: "reviewer",
          note: decisionNote,
          ...(action === "assign" ? { owner } : {}),
          ...(action === "close" ? { closure_check_id: closureCheckId } : {}),
          ...taskFields,
        }),
      });
      await refreshHistory();
      setNotice(N_("Đã lưu quyết định vào lịch sử API."));
      setNote("");
    });
  }
  async function revise(id) {
    const original = versions.find((v) => v.id === id);
    const edited = draft.versions.find((v) => v.id === id);
    if (
      !original ||
      (edited.text === original.text &&
        JSON.stringify(edited.uses) === JSON.stringify(original.uses))
    ) {
      setError(N_("Chỉnh nội dung hoặc công dụng trước khi tạo phiên bản mới."));
      return;
    }
    await act(N_("Đang tạo phiên bản mới và hàng đợi rà lại…"), async () => {
      const timestamp = new Date().toISOString();
      const event = {
        id: `EV-${crypto.randomUUID()}`,
        kind: "record_changed",
        record_id: original.record_id,
        previous_version_id: original.id,
        new_version: {
          ...edited,
          id: `RV-${crypto.randomUUID()}`,
          version: original.version + 1,
          supersedes: original.id,
          received_at: timestamp,
        },
        received_at: timestamp,
      };
      await request("/changes", {
        method: "POST",
        body: JSON.stringify(event),
      });
      await refreshHistory();
      go("updates");
      setNotice(N_("Đã tạo phiên bản mới. Chạy lại mục tương ứng trong hàng đợi."));
    });
  }
  const context = {
    bundle,
    draft,
    setDraft,
    result,
    setResult,
    history,
    setHistory,
    offline,
    busy,
    error,
    notice,
    setNotice,
    selected,
    setSelected,
    panel,
    setPanel,
    query,
    setQuery,
    messages,
    setMessages,
    prompt,
    setPrompt,
    oldNew,
    setOldNew,
    note,
    setNote,
    owner,
    setOwner,
    go,
    act,
    inspect,
    ask,
    versions,
    current,
    check,
    clause,
    updateText,
    decide,
    request,
    features,
    session,
    closureCheckId,
    setClosureCheckId,
    revise,
    refreshHistory,
    evaluation,
    setEvaluation,
    showPreview,
  };
  const evidencePanel = <Evidence {...context} />;
  const viewLabel =
    view === "preferences"
      ? N_("Cài đặt")
      : currentTabs.find(([key]) => key === view)?.[1] || "Workspace";
  // The strip only reports a problem: the API is unreachable, or the engine
  // behind it is not ready. A healthy connection needs no banner.
  const degraded = offline || (bundle && !features.layer0_ready);
  return (
    <>
      <a className="skip" href="#main">
        {t("Đến nội dung chính")}
      </a>
      <div className={`app${researchActive ? " research-feature" : ""}`}>
        {mobile && (
          <button
            className="nav-scrim"
            aria-label={t("Đóng menu")}
            onClick={() => setMobile(false)}
          />
        )}
        <aside className={`sidebar ${mobile ? "open" : ""}`}>
          <a
            className="brand"
            href="#"
            onClick={(e) => {
              e.preventDefault();
              go("reviews");
            }}
          >
            <img
              className="brand-mark"
              src="/assets/lex-mark-96.png"
              alt="Lex"
              width="44"
              height="44"
            />
            lexcheck
            <span className="brand-dot">.</span>
          </a>
          {researchReady && (
            <div className="workspace">
              <span className="workspace-logo">N</span>
              <label className="workspace-select">
                <select
                  aria-label={t("Chọn workspace")}
                  value={workspaceId}
                  onChange={(event) => chooseWorkspace(event.target.value)}
                  disabled={chatBusy}
                >
                  <option value="demo">NULLPTR Demo · TPBVSK</option>
                  {researchWorkspaces.map((workspace) => (
                    <option key={workspace.id} value={workspace.id}>
                      {workspace.name}
                    </option>
                  ))}
                  <option value="new">{t("+ Tạo workspace")}</option>
                </select>
                <small>
                  {researchActive
                    ? t("Tài liệu và hội thoại riêng")
                    : t("Rà soát hồ sơ mẫu")}
                </small>
              </label>
            </div>
          )}
          <button
            className="new-chat"
            disabled={researchActive && chatBusy}
            onClick={() => {
              setMessages([]);
              setPrompt("");
              if (researchActive) {
                setConversationId(null);
                setNewConversationNonce((value) => value + 1);
              }
              go("chat");
            }}
          >
            <Icon name="plus" />
            {t("Cuộc trò chuyện mới")}
          </button>
          <div className="nav-caption">{t("KHÔNG GIAN LÀM VIỆC")}</div>
          <nav aria-label={t("Điều hướng chính")}>
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
                {t(label)}
              </button>
            ))}
          </nav>
          {researchActive && workspaceId !== "new" && (
            <Suspense fallback={null}>
              <WorkspaceConversations
                workspaceId={workspaceId}
                selectedId={conversationId}
                refresh={chatRefresh}
                disabled={chatBusy}
                onSelect={(id) => {
                  setConversationId(id);
                  go("chat");
                }}
              />
            </Suspense>
          )}
          <div className="sidebar-bottom">
            <button
              className={`nav-item settings-link ${view === "preferences" ? "active" : ""}`}
              aria-current={view === "preferences" ? "page" : undefined}
              onClick={() => go("preferences")}
            >
              <Icon name="settings" />
              {t("Cài đặt")}
            </button>
            <div className="profile">
              <span className="avatar">
                {session?.group === "operations" ? "O" : "M"}
              </span>
              <span>
                <b>{t("Reviewer mẫu")}</b>
                <small>{t("Chế độ trải nghiệm")}</small>
              </span>
            </div>
            {features.layer3 && (
              <label>
                {t("Đổi tài khoản mẫu")}
                <select
                  aria-label={t("Tài khoản mẫu")}
                  value={session?.user_id || "U-MANAGER"}
                  disabled={!!busy}
                  onChange={(e) => switchUser(e.target.value)}
                >
                  <option value="U-MANAGER">{t("Quản lý")}</option>
                  <option value="U-OPS">{t("Kế toán + vận hành")}</option>
                </select>
              </label>
            )}
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <div className="breadcrumb">
              <button
                className="icon-button mobile-menu"
                onClick={() => setMobile(!mobile)}
                aria-label={t("Mở menu")}
                aria-expanded={mobile}
              >
                <Icon name="menu" />
              </button>
              <span className="muted">{t("Không gian làm việc")}</span>
              <span className="slash">/</span>
              <b>{t(viewLabel)}</b>
            </div>
            <div className="top-actions">
              <button
                className="button secondary"
                onClick={() =>
                  researchActive
                    ? refreshResearch().catch((error) => setError(error.message))
                    : load()
                }
                disabled={!!busy || chatBusy}
              >
                {t("Tải lại")}
              </button>
              <span className="demo-pill">
                {offline ? t("Bản mẫu ngoại tuyến") : t("Dữ liệu tổng hợp")}
              </span>
              <button
                className="icon-button"
                onClick={() => setPanel(!panel)}
                aria-label={t("Mở bằng chứng và tri thức")}
              >
                <Icon name="panel" />
              </button>
            </div>
          </header>
          {degraded && !researchActive && (
            <div className="status-strip">
              <span>
                {offline
                  ? t("API mất kết nối · Chỉ xem bản mẫu đi kèm")
                  : t("Engine chưa sẵn sàng · đang dùng fixture")}
              </span>
            </div>
          )}
          {busy && (
            <div className="feedback" role="status">
              {t(busy)}
            </div>
          )}
          {error && (
            <div className="feedback error" role="alert">
              {t(error)}
            </div>
          )}
          {notice && (
            <div className="feedback" role="status">
              {t(notice)}
            </div>
          )}
          <div
            className={`body-layout${researchActive ? " research-body" : ""}`}
          >
            <main id="main" tabIndex="-1">
              {view === "preferences" ? (
                <Settings
                  offline={offline}
                  features={features}
                  busy={busy}
                  reload={() => load()}
                />
              ) : researchActive ? (
                <Suspense fallback={<p role="status">{t("Đang tải workspace…")}</p>}>
                  {view === "chat" && currentWorkspace ? (
                    <WorkspaceChat
                      key={`${workspaceId}:${newConversationNonce}`}
                      workspace={currentWorkspace}
                      conversationId={conversationId}
                      newConversationNonce={newConversationNonce}
                      onConversationSelected={(id) => {
                        setConversationId(id);
                        refreshConversations();
                      }}
                      onTurnSaved={refreshConversations}
                      onBusyChange={setChatBusy}
                      onNavigate={go}
                      onDocumentsChanged={refreshResearch}
                    />
                  ) : (
                    <DocumentWorkspace
                      key={workspaceId}
                      id={workspaceId}
                      view={view}
                      onNavigate={go}
                      onUpdated={refreshResearch}
                      onCreated={(workspace) => {
                        setResearchWorkspaces((previous) => [
                          ...previous,
                          workspace,
                        ]);
                        chooseWorkspace(workspace.id);
                      }}
                    />
                  )}
                </Suspense>
              ) : !bundle ? (
                <Page title={t("Kết nối hồ sơ")}>
                  <p>{busy ? t(busy) : t("Chưa có dữ liệu.")}</p>
                  {!busy && (
                    <button className="button secondary" onClick={() => load()}>
                      {t("Tải lại")}
                    </button>
                  )}
                </Page>
              ) : (
                <>
                  {view === "chat" && <Chat {...context} />}
                  {view === "knowledge" && <Sources {...context} />}
                  {view === "reviews" && <Review {...context} />}
                  {view === "updates" && <Updates {...context} />}
                  {view === "history" && <History {...context} />}
                </>
              )}
            </main>
            {!researchActive && (
              <aside
                className={`evidence ${panel ? "open" : ""}`}
                aria-label={t("Tri thức và bằng chứng")}
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
