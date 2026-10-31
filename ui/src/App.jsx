import React, { useEffect, useRef, useState } from "react";
import { request as apiRequest, loadWorkspace, resultLabel } from "./api.js";
import { Icon, Page, Badge, tabs } from "./components/shared.jsx";
import Review from "./components/Review.jsx";
import Evidence from "./components/Evidence.jsx";
import History from "./components/History.jsx";
import Chat from "./components/Chat.jsx";
import Sources from "./components/Sources.jsx";
import Updates from "./components/Updates.jsx";
export default function App() {
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
        throw new Error("Tài khoản đã thay đổi. Bỏ kết quả của phiên cũ.");
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
    window.location.hash = next;
    setView(next);
    setMobile(false);
    setPanel(false);
    setError("");
    setNotice("");
  };
  async function load(user = sessionRef.current?.user_id || "U-MANAGER") {
    const epoch = generation.current;
    setBusy("Đang tải hồ sơ và lịch sử từ API…");
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
      const allowed = tabs.some(([key]) => key === next);
      setView(allowed ? next : "reviews");
    };
    navigate();
    window.addEventListener("hashchange", navigate);
    return () => window.removeEventListener("hashchange", navigate);
  }, []);
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
    await act("Đang mở finding minh hoạ…", async () => {
      const response = await fetch("/finding-preview.json");
      if (!response.ok) throw new Error("Không tải được finding minh hoạ.");
      const preview = await response.json();
      setResult(preview);
      setSelected({
        type: "finding",
        value: preview.findings[0],
        check: preview,
      });
      setPanel(true);
      setNotice(
        "Finding minh hoạ synthetic/staged từ fixture. Chưa chạy engine; không lưu quyết định hoặc gọi model.",
      );
    });
  }
  async function ask(text) {
    if (!text.trim()) return;
    if (!features.layer1 || offline) {
      setError("Chưa kết nối chatbot. Câu hỏi chưa được gửi.");
      return;
    }
    if (!check) {
      setError("Chọn một kết quả kiểm tra trước khi hỏi.");
      return;
    }
    const question = text.trim();
    const epoch = generation.current;
    await act("Đang tra cứu căn cứ trong kết quả đã chọn…", async () => {
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
          ...(action === "close" ? { closure_check_id: closureCheckId } : {}),
        }),
      });
      await refreshHistory();
      setNotice("Đã lưu quyết định vào lịch sử API.");
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
      setError("Chỉnh nội dung hoặc công dụng trước khi tạo phiên bản mới.");
      return;
    }
    await act("Đang tạo phiên bản mới và hàng đợi rà lại…", async () => {
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
      setNotice("Đã tạo phiên bản mới. Chạy lại mục tương ứng trong hàng đợi.");
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
          <div className="workspace">
            <span className="workspace-logo">N</span>
            <span>
              <b>NULLPTR Demo</b>
              <small>Doanh nghiệp TPBVSK · Dữ liệu mẫu</small>
            </span>
          </div>
          <button
            className="new-chat"
            onClick={() => {
              setMessages([]);
              setPrompt("");
              go("chat");
            }}
          >
            <Icon name="plus" />
            Cuộc trò chuyện mới
          </button>
          <div className="nav-caption">KHÔNG GIAN LÀM VIỆC</div>
          <nav aria-label="Điều hướng chính">
            {tabs.map(([key, label]) => (
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
              <span className="avatar">
                {session?.group === "operations" ? "O" : "M"}
              </span>
              <span>
                <b>Reviewer mẫu</b>
                <small>Chế độ trải nghiệm</small>
              </span>
            </div>
            {features.layer3 && (
              <label>
                Đổi tài khoản mẫu
                <select
                  aria-label="Tài khoản mẫu"
                  value={session?.user_id || "U-MANAGER"}
                  disabled={!!busy}
                  onChange={(e) => switchUser(e.target.value)}
                >
                  <option value="U-MANAGER">Quản lý</option>
                  <option value="U-OPS">Kế toán + vận hành</option>
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
                aria-label="Mở menu"
                aria-expanded={mobile}
              >
                <Icon name="menu" />
              </button>
              <span className="muted">Không gian làm việc</span>
              <span className="slash">/</span>
              <b>{tabs.find((t) => t[0] === view)[1]}</b>
            </div>
            <div className="top-actions">
              <span className="demo-pill">
                synthetic/staged ·{" "}
                {offline ? "fixture ngoại tuyến" : "Dữ liệu tổng hợp"}
              </span>
              <button
                className="icon-button"
                onClick={() => setPanel(!panel)}
                aria-label="Mở bằng chứng và tri thức"
              >
                <Icon name="panel" />
              </button>
            </div>
          </header>
          <div className="status-strip">
            <span>TPBVSK</span>
            <span>
              {offline
                ? "API mất kết nối · Chỉ xem bản mẫu đi kèm"
                : `API kết nối · ${features.layer0_ready ? "live" : "fixture — engine chưa sẵn sàng"}`}
            </span>
            <button onClick={() => load()} disabled={!!busy}>
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
          <div className="body-layout">
            <main id="main" tabIndex="-1">
              {!bundle ? (
                <Page title="Kết nối hồ sơ">
                  <p>
                    {busy || "Chưa có dữ liệu. Bấm Tải lại để thử kết nối."}
                  </p>
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
            <aside
              className={`evidence ${panel ? "open" : ""}`}
              aria-label="Tri thức và bằng chứng"
            >
              {evidencePanel}
            </aside>
          </div>
        </div>
      </div>
    </>
  );
}
