import React, { useEffect, useState } from "react";
import { researchClient } from "./research.js";
import "./research.css";

const categories = {
  rental_contracts: "Hợp đồng thuê",
  electricity_water: "Điện & nước",
  rental_billing: "Thông báo thu tiền",
  fire_safety: "PCCC",
  residence_registration: "Tạm trú",
  deposit_settlement: "Thanh lý / tiền cọc",
};
const topicNames = {
  contracts_deposits: "Hợp đồng & tiền cọc",
  electricity_water: "Điện & nước",
  residence_registration: "Tạm trú",
  business_tax_billing: "Kinh doanh, thuế & thu tiền",
};
const states = {
  ready: "Sẵn sàng",
  researching: "Đang nghiên cứu",
  review_needed: "Chờ duyệt nguồn & rule",
  failed: "Lượt nghiên cứu chưa hoàn thành",
};
const views = {
  overview: "Tổng quan nghiên cứu",
  knowledge: "Rule & graph 3 lớp",
  sources: "Nguồn pháp lý",
  company: "Hồ sơ doanh nghiệp",
  gaps: "Thông tin cần bổ sung",
};

export function RentalWorkspace({
  id,
  view,
  onNavigate,
  onCreated,
  onUpdated,
}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("Nhà trọ — ví dụ Excel");
  const [selected, setSelected] = useState(null);
  const [refresh, setRefresh] = useState(0);
  const isNew = id === "new";

  useEffect(() => {
    setData(null);
    setSelected(null);
    setError("");
    if (isNew) return;
    let active = true;
    const controller = new AbortController();
    let timer;
    async function load() {
      try {
        const value = await researchClient.detail(id, controller.signal);
        if (!active) return;
        if (
          value.workspace.id !== id ||
          (value.result && value.result.graph.company_id !== id)
        ) {
          throw new Error("Kết quả không thuộc workspace đang chọn.");
        }
        setData(value);
        setName(value.workspace.name);
        setError("");
        if (value.workspace.state === "researching")
          timer = setTimeout(load, 2200);
        else onUpdated();
      } catch (e) {
        if (active && e.name !== "AbortError") setError(e.message);
      }
    }
    load();
    return () => {
      active = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [id, isNew, refresh, onUpdated]);

  async function act(callback) {
    setError("");
    setBusy(true);
    try {
      await callback();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  if (isNew)
    return (
      <div className="content-page research-page">
        <div className="page-eyebrow">WORKSPACE MỚI · NHÀ TRỌ</div>
        <h1 className="page-title">Bắt đầu từ hồ sơ doanh nghiệp.</h1>
        <p>
          Excel giữ riêng trên máy. Model dùng cấu trúc hồ sơ để tìm nguồn chính
          thức và đề xuất rule.
        </p>
        <form
          className="research-form"
          onSubmit={(event) => {
            event.preventDefault();
            const file = event.currentTarget.elements.workbook.files[0];
            if (!file) return;
            act(async () => {
              const workspace = await researchClient.create(name, file);
              onCreated(workspace);
            });
          }}
        >
          <label>
            Tên workspace
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={150}
              required
            />
          </label>
          <label>
            Workbook quản lý nhà trọ
            <input name="workbook" type="file" accept=".xlsx" required />
          </label>
          <p className="research-note">
            Không gửi ô dữ liệu người thuê, công thức hay tên sheet gốc lên
            model. Tên workspace là nhãn hiển thị, chưa xác nhận tên pháp lý.
          </p>
          <button className="button primary" disabled={busy}>
            {busy ? "Đang đọc cấu trúc Excel…" : "Tạo workspace & tìm luật"}
          </button>
          {error && (
            <p className="research-error" role="alert">
              {error}
            </p>
          )}
        </form>
      </div>
    );

  const scopedData = data?.workspace.id === id ? data : null;
  const w = scopedData?.workspace,
    r = scopedData?.result;
  const rules = r?.proposals || [];
  const nodes = Object.values(r?.graph.nodes || {});
  const sources = nodes.filter((n) => n.kind === "LegalDoc");
  const proposal = rules.find((rule) => rule.id === selected) || rules[0];
  async function download(source) {
    await act(async () => {
      const blob = await researchClient.source(id, source.sha256);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download =
        "official-source" + (blob.type === "application/pdf" ? ".pdf" : ".txt");
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    });
  }

  return (
    <div className="content-page research-page">
      <div className="page-eyebrow">NHÀ TRỌ · KẾT QUẢ THẬT ĐÃ LƯU CỤC BỘ</div>
      <div className="page-title-row">
        <h1 className="page-title">{views[view] || views.overview}</h1>
        {w && (
          <button
            className="button primary"
            disabled={busy || w.state === "researching"}
            onClick={() =>
              act(async () => {
                await researchClient.start(id);
                setRefresh((value) => value + 1);
                onUpdated();
              })
            }
          >
            {w.state === "researching"
              ? "Đang tìm & đọc luật…"
              : "Tìm luật & sinh rule"}
          </button>
        )}
      </div>
      <div className="research-disclaimer">
        <b>Rule đề xuất · chưa xác minh · 0 rule thực thi.</b>
        <span>
          {" "}
          Chưa đủ thông tin để kết luận pháp lý. Cần duyệt nguồn, ngày hiệu lực
          và điều kiện áp dụng trước khi có pack nhà trọ chạy audit.
        </span>
      </div>
      {error && (
        <p className="research-error" role="alert">
          {error}
        </p>
      )}
      {!w ? (
        <p role="status">
          {error
            ? "Chưa tải được workspace. Đổi workspace hoặc tải lại trang để thử lại."
            : "Đang tải kết quả từ API…"}
        </p>
      ) : (
        <>
          {(view === "overview" || !Object.hasOwn(views, view)) && (
            <>
              <div className="research-state">
                <span className="badge warn">{states[w.state]}</span>
                <span>{w.name}</span>
              </div>
              <div className="research-metrics">
                {[
                  [w.manifest.sheets.length, "sheet trong workbook"],
                  [sources.length, "nguồn đã tải"],
                  [rules.length, "rule đề xuất"],
                  [0, "rule thực thi"],
                ].map(([n, label]) => (
                  <div key={label}>
                    <strong>{n}</strong>
                    <span>{label}</span>
                  </div>
                ))}
              </div>
              <h2>Tri thức được lưu theo 3 lớp</h2>
              <div className="research-layers">
                {[
                  [
                    1,
                    "Văn bản & điều khoản",
                    "PDF gốc, hash, nguyên văn, phiên bản và quan hệ pháp lý",
                    "sources",
                  ],
                  [
                    2,
                    "Rule & khái niệm",
                    "Nghĩa vụ đề xuất, điều kiện áp dụng và chứng cứ cần xem",
                    "knowledge",
                  ],
                  [
                    3,
                    "Doanh nghiệp & hồ sơ",
                    "Workspace riêng, workbook và snapshot cấu trúc từng sheet",
                    "company",
                  ],
                ].map(([layer, title, description, destination]) => (
                  <button key={layer} onClick={() => onNavigate(destination)}>
                    <small>
                      LỚP 0{layer} ·{" "}
                      {nodes.filter((n) => n.layer === layer).length} NODE
                    </small>
                    <b>{title}</b>
                    <span>{description}</span>
                  </button>
                ))}
              </div>
              <div className="research-section">
                <div className="section-head">
                  <h2>Đã tìm thấy gì?</h2>
                  <button
                    className="button"
                    onClick={() => onNavigate("knowledge")}
                  >
                    Xem rule & nguồn
                  </button>
                </div>
                {rules.length ? (
                  rules.map((rule) => (
                    <p className="research-rule-summary" key={rule.id}>
                      {rule.title}
                      <span className="badge warn">Chờ duyệt</span>
                    </p>
                  ))
                ) : (
                  <p>
                    Chưa có đề xuất từ nguồn đọc được. Bắt đầu nghiên cứu để tạo
                    kết quả thật.
                  </p>
                )}
              </div>
              {r && (
                <p className="research-note">
                  Lượt đã lưu: {r.elapsed_seconds}s · {r.sources_attempted}{" "}
                  nguồn thử · dừng: {r.stop_reason}. Độ phủ các nhóm dự kiến
                  không chứng minh đã tìm đủ luật.
                </p>
              )}
              <details
                className="research-section"
                open={w.state === "researching"}
              >
                <summary>Tiến độ & nguồn đã xử lý</summary>
                <ol className="research-progress" aria-live="polite">
                  {w.progress.map((event, i) => (
                    <li key={i}>
                      <small>
                        {new Date(event.at).toLocaleTimeString("vi-VN")}
                      </small>{" "}
                      {event.message}
                    </li>
                  ))}
                </ol>
              </details>
            </>
          )}
          {view === "knowledge" && (
            <>
              <p>
                Chọn một rule để xem nguyên văn, vị trí trên trang và đường dẫn
                về nguồn. Tất cả đang chờ người duyệt.
              </p>
              <div className="research-rule-grid">
                <div className="research-rule-list">
                  {rules.map((rule) => (
                    <button
                      key={rule.id}
                      aria-pressed={proposal?.id === rule.id}
                      onClick={() => setSelected(rule.id)}
                    >
                      <small>
                        {rule.article} · Trang {rule.page}
                      </small>
                      <b>{rule.title}</b>
                      <span className="badge warn">LLM đề xuất</span>
                    </button>
                  ))}
                  {!rules.length && (
                    <p>
                      Chưa có rule đề xuất. Xem tiến độ hoặc thông tin còn
                      thiếu.
                    </p>
                  )}
                </div>
                {proposal && (
                  <article className="research-rule-detail">
                    <h2>{proposal.title}</h2>
                    <p>{proposal.requirement}</p>
                    <h3>Nguyên văn từ trang đã đọc</h3>
                    <blockquote>{proposal.quote}</blockquote>
                    <dl>
                      <dt>Điều / trang</dt>
                      <dd>
                        {proposal.article} · trang {proposal.page}
                      </dd>
                      <dt>Điều kiện áp dụng</dt>
                      <dd>{proposal.applicability}</dd>
                      <dt>Ngày hiệu lực đề xuất</dt>
                      <dd>
                        {proposal.valid_from || "Chưa xác định"} →{" "}
                        {proposal.valid_to || "Chưa xác định ngày kết thúc"}
                        <small>Chưa xác minh hiệu lực hiện hành</small>
                      </dd>
                      <dt>Chứng cứ cần xem</dt>
                      <dd>
                        {proposal.evidence_needed.join(" · ") ||
                          "Cần người duyệt xác định"}
                      </dd>
                      <dt>Thông tin chưa biết</dt>
                      <dd>
                        {proposal.missing_facts.join(" · ") ||
                          "Xem điều kiện áp dụng"}
                      </dd>
                      <dt>Ngoại lệ</dt>
                      <dd>
                        {proposal.exceptions.join(" · ") ||
                          "Chưa xác định đầy đủ"}
                      </dd>
                      <dt>Vị trí quote</dt>
                      <dd>
                        [{proposal.quote_start}, {proposal.quote_end}) · Unicode
                        code points
                      </dd>
                    </dl>
                    <a
                      href={proposal.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Mở nguồn chính thức ↗
                    </a>
                    <code>SHA-256 {proposal.source_sha256}</code>
                    <div className="research-trace">
                      <span>Workbook</span> → <span>Rule đề xuất</span> →{" "}
                      <span>{proposal.article}</span> → <span>PDF nguồn</span>
                    </div>
                  </article>
                )}
              </div>
            </>
          )}
          {view === "sources" && (
            <>
              <p>
                Bản gốc được lưu theo SHA-256. Text OCR cần đối chiếu ảnh trang
                PDF; chưa có người duyệt xác minh.
              </p>
              {sources.map(({ payload: source }) => (
                <article className="research-source" key={source.sha256}>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {source.title}
                  </a>
                  <p>
                    <span className="badge">{source.extraction_method}</span> ·{" "}
                    {source.pages.length} trang
                  </p>
                  <code>SHA-256 {source.sha256}</code>
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() => download(source)}
                  >
                    Tải bản gốc đã lưu
                  </button>
                  <details>
                    <summary>Xem text theo trang</summary>
                    {source.pages.map((text, index) => (
                      <details key={index}>
                        <summary>
                          Trang {index + 1} · {text.length} ký tự
                        </summary>
                        <pre>
                          {text ||
                            "Trang chưa có text, cần đọc bản gốc hoặc OCR thêm."}
                        </pre>
                      </details>
                    ))}
                  </details>
                </article>
              ))}
              {!sources.length && (
                <p>Chưa tải được nguồn chính thức cho workspace này.</p>
              )}
            </>
          )}
          {view === "company" && (
            <>
              <form
                className="research-rename"
                onSubmit={(event) => {
                  event.preventDefault();
                  act(async () => {
                    await researchClient.rename(id, name);
                    setRefresh((value) => value + 1);
                    onUpdated();
                  });
                }}
              >
                <label>
                  Tên hiển thị workspace
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    maxLength={150}
                    required
                  />
                </label>
                <button className="button" disabled={busy}>
                  Lưu tên
                </button>
              </form>
              <p className="research-note">
                Tên pháp lý chưa xác nhận. Excel gốc giữ trên máy; model chỉ
                nhận các loại hồ sơ đã phân loại, không nhận ô dữ liệu người
                thuê.
              </p>
              <code>SHA-256 workbook {w.manifest.sha256}</code>
              {w.manifest.sheets.map((sheet) => (
                <div className="research-sheet" key={sheet.index}>
                  <div>
                    <b>Sheet {sheet.index}</b>
                    <p>
                      {sheet.categories
                        .map((category) => categories[category] || category)
                        .join(", ") || "Chưa phân loại"}
                    </p>
                  </div>
                  <small>
                    {sheet.row_count} hàng · {sheet.cell_count} ô
                  </small>
                </div>
              ))}
              <p className="research-note">
                Có sheet PCCC hoặc tạm trú không chứng minh thủ tục đã hoàn tất.
                Thiếu dữ liệu kết nối cũng không chứng minh thủ tục chưa diễn
                ra.
              </p>
            </>
          )}
          {view === "gaps" && (
            <>
              <h2>Cần xác nhận về doanh nghiệp</h2>
              <ul>
                {w.manifest.unknown_facts.map((fact) => (
                  <li key={fact}>{fact}</li>
                ))}
              </ul>
              <h2>Nhóm chưa có đề xuất đủ nguồn</h2>
              <ul>
                {r?.missing_topics.map((topic) => (
                  <li key={topic}>{topicNames[topic] || topic}</li>
                ))}
              </ul>
              {r && !r.missing_topics.length && (
                <p>
                  Đã có đề xuất cho từng nhóm đã lên kế hoạch; chưa chứng minh
                  đã tìm đủ luật.
                </p>
              )}
              <h2>Văn bản tham chiếu chưa đọc đủ</h2>
              <ul>
                {r?.unresolved_documents.map((doc) => (
                  <li key={doc}>{doc}</li>
                ))}
              </ul>
              <h2>Lỗi nguồn & giới hạn lượt đọc</h2>
              <div className="research-gaps">
                {r?.gaps.map((gap, index) => (
                  <p key={index}>{gap}</p>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
