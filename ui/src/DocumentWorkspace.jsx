import React, { useEffect, useState } from "react";
import { researchClient } from "./research.js";
import "./research.css";

const titles = {
  overview: "Tổng quan workspace",
  business: "Tài liệu doanh nghiệp",
  legal: "Tài liệu luật",
  knowledge: "Kho tri thức",
  settings: "Thông tin workspace",
};
const formats = ".pdf,.txt,.md,.docx,.xlsx,.csv,.json,.html";
const kinds = { business: "doanh nghiệp", legal: "luật" };

export function DocumentWorkspace({
  id,
  view,
  onNavigate,
  onCreated,
  onUpdated,
}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [preview, setPreview] = useState(null);
  const [rawPreview, setRawPreview] = useState(false);
  const [ruleId, setRuleId] = useState(null);
  const isNew = id === "new";

  useEffect(() => {
    setData(null);
    setPreview(null);
    setError("");
    if (isNew) return;
    const controller = new AbortController();
    let active = true;
    researchClient
      .detail(id, controller.signal)
      .then((value) => {
        if (!active) return;
        if (
          value.workspace.id !== id ||
          (value.result && value.result.graph.company_id !== id)
        )
          throw Error("Kết quả không thuộc workspace đang chọn.");
        setData(value);
        setName(value.workspace.name);
        setDescription(value.workspace.description || "");
      })
      .catch((e) => {
        if (active && e.name !== "AbortError") setError(e.message);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [id, isNew, refresh]);

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
  const reload = () => {
    setRefresh((value) => value + 1);
    onUpdated();
  };
  const workspace = data?.workspace.id === id ? data.workspace : null;
  const result = workspace ? data.result : null;
  const documents = workspace?.documents || [];
  const business = documents.filter((doc) => doc.collection === "business");
  const legal = documents.filter((doc) => doc.collection === "legal");
  const profile = workspace?.profile;
  const rules = result?.proposals || [];
  const selectedRule = rules.find((rule) => rule.id === ruleId) || rules[0];

  async function download(doc) {
    await act(async () => {
      const blob = await researchClient.original(id, doc.id);
      const url = URL.createObjectURL(blob),
        link = document.createElement("a");
      link.href = url;
      link.download = doc.name;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    });
  }

  if (isNew)
    return (
      <div className="content-page research-page">
        <div className="page-eyebrow">WORKSPACE MỚI</div>
        <h1 className="page-title">Tạo không gian hồ sơ doanh nghiệp.</h1>
        <p>
          Cùng một luồng cho mọi doanh nghiệp: nạp hồ sơ doanh nghiệp, nạp văn
          bản luật, rồi phân tích từ dữ liệu đã chọn.
        </p>
        <form
          className="research-form"
          onSubmit={(event) => {
            event.preventDefault();
            act(async () =>
              onCreated(
                await researchClient.createWorkspace(name, description),
              ),
            );
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
            Mô tả hoạt động do bạn cung cấp
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={2000}
              rows={4}
              placeholder="Có thể để trống và bổ sung tài liệu sau."
            />
          </label>
          <p className="research-note">
            Không chọn sẵn ngành hay bộ luật. Nội dung mô tả này có thể được
            dùng làm ngữ cảnh khi bạn chủ động yêu cầu phân tích.
          </p>
          <button className="button primary" disabled={busy}>
            {busy ? "Đang tạo…" : "Tạo workspace"}
          </button>
          {error && (
            <p className="research-error" role="alert">
              {error}
            </p>
          )}
        </form>
      </div>
    );

  function collection(kind) {
    const docs = kind === "business" ? business : legal;
    return (
      <>
        <div className="document-intake">
          <div>
            <h2>Thêm tài liệu {kinds[kind]}</h2>
            <p>
              {kind === "business"
                ? "Hồ sơ, hợp đồng, thông tin sản phẩm, workbook và chứng từ của doanh nghiệp."
                : "Văn bản pháp luật hoặc nguồn pháp lý bạn muốn đưa vào kho. Tải lên chưa xác nhận hiệu lực hay nội dung."}
            </p>
          </div>
          <label className="button primary document-file-button">
            {busy ? "Đang nhập…" : `+ Thêm tài liệu ${kinds[kind]}`}
            <input
              aria-label={`Thêm tài liệu ${kinds[kind]}`}
              type="file"
              accept={formats}
              multiple
              disabled={busy}
              onChange={(event) => {
                const files = [...event.target.files];
                event.target.value = "";
                act(async () => {
                  for (const file of files)
                    await researchClient.uploadDocument(id, kind, file);
                  reload();
                });
              }}
            />
          </label>
        </div>
        <p className="research-note">
          PDF, DOCX, XLSX, TXT, Markdown, CSV hoặc JSON · tối đa 15 MB/tài liệu.
          Bản gốc và bản trích giữ cục bộ, không tự gửi model.
        </p>
        {docs.length ? (
          <div className="document-table">
            {docs.map((doc) => (
              <article className="document-row" key={doc.id}>
                <div className="document-row-main">
                  <b>{doc.name}</b>
                  <small>
                    Phiên bản {doc.version} · {doc.page_count ?? "?"}{" "}
                    trang/sheet ·{" "}
                    {doc.status === "needs_ocr"
                      ? "Cần OCR/đọc bản gốc"
                      : doc.status === "needs_extraction"
                        ? "Chưa trích được text"
                        : "Đã trích text cục bộ"}
                    {doc.origin === "synthetic_fixture"
                      ? " · Dữ liệu mẫu tổng hợp"
                      : ""}
                  </small>
                  <code>SHA-256 {doc.sha256}</code>
                </div>
                <div className="document-row-actions">
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() =>
                      act(async () => {
                        setPreview(await researchClient.document(id, doc.id));
                        setRawPreview(false);
                      })
                    }
                  >
                    Xem bản trích
                  </button>
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() => download(doc)}
                  >
                    Tải bản gốc
                  </button>
                </div>
                {kind === "business" && (
                  <span className="document-context-status">
                    {doc.context_enabled
                      ? "Đã chọn làm ngữ cảnh model"
                      : "Chưa gửi model"}
                  </span>
                )}
                {kind === "legal" && (
                  <span className="badge warn">Nguồn chưa xác minh</span>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div className="document-empty">
            Chưa có tài liệu {kinds[kind]}. Dùng nút phía trên để thêm vào
            workspace này.
          </div>
        )}
        {preview?.collection === kind && (
          <section className="document-preview">
            <div className="section-head">
              <h2>{preview.name}</h2>
              <button className="button" onClick={() => setPreview(null)}>
                Đóng bản trích
              </button>
            </div>
            <p className="research-note">
              Phương thức: {preview.method}. Đây là bản trích máy, chưa xác minh
              so với bản gốc.
            </p>
            {kind === "business" && (
              <>
                {preview.method === "xlsx-cell-text-limited" && <button className="button" disabled={busy} onClick={() => act(async () => {
                  setPreview(await researchClient.refreshExtraction(id, preview.id));
                  const detail = await researchClient.detail(id);
                  setData(detail);
                  onUpdated();
                })}>Cập nhật bản trích XLSX an toàn</button>}
                <p className="document-privacy">
                  Bản dùng cho model đã che các mẫu email, số điện thoại, mã
                  định danh và một số cột cá nhân nhận diện được. Bạn cần xem
                  lại vì có thể còn tên, địa chỉ hoặc dữ liệu nhạy cảm khác.
                </p>
                <label className="document-checkbox">
                  <input
                    type="checkbox"
                    checked={rawPreview}
                    onChange={(event) => setRawPreview(event.target.checked)}
                  />
                  Xem bản trích gốc cục bộ
                </label>
              </>
            )}
            {(kind === "business" && !rawPreview
              ? preview.model_pages
              : preview.pages
            ).map((text, index) => (
              <details key={index} open={index === 0}>
                <summary>Trang/sheet {index + 1}</summary>
                <pre>
                  {text || "Chưa có text. Cần OCR hoặc đối chiếu bản gốc."}
                </pre>
              </details>
            ))}
            {preview.warnings.length > 0 && (
              <p className="research-note">
                Giới hạn: {preview.warnings.join(" · ")}
              </p>
            )}
            {kind === "business" && (
              <label className="document-checkbox">
                <input
                  type="checkbox"
                  checked={preview.context_enabled}
                  disabled={
                    busy || preview.method === "xlsx-cell-text-limited" || !preview.model_pages.some((text) => text.trim())
                  }
                  onChange={(event) => {
                    const enabled = event.target.checked;
                    act(async () => {
                      const value = await researchClient.context(
                        id,
                        preview.id,
                        enabled,
                      );
                      setPreview(value);
                      const detail = await researchClient.detail(id);
                      setData(detail);
                      onUpdated();
                    });
                  }}
                />
                Tôi đã xem bản trích đã che và chọn dùng nội dung đó làm ngữ
                cảnh phân tích.
              </label>
            )}
          </section>
        )}
      </>
    );
  }

  return (
    <div className="content-page research-page">
      <div className="page-eyebrow">
        WORKSPACE ·{" "}
        {workspace?.synthetic ? "DỮ LIỆU MẪU TỔNG HỢP" : "HỒ SƠ RIÊNG CỤC BỘ"}
      </div>
      <div className="page-title-row">
        <h1 className="page-title">{titles[view] || titles.overview}</h1>
        <button className="button" disabled={busy} onClick={reload}>
          Tải lại
        </button>
      </div>
      {error && (
        <p className="research-error" role="alert">
          {error}
        </p>
      )}
      {!workspace ? (
        <p role="status">
          {error
            ? "Chưa tải được workspace. Tải lại để thử."
            : "Đang tải dữ liệu workspace từ API…"}
        </p>
      ) : (
        <>
          {(view === "overview" || !Object.hasOwn(titles, view)) && (
            <>
              <p className="research-note">
                Các số dưới đây được tính từ kho tài liệu/API, không phải nội
                dung LLM tự viết.
              </p>
              <div className="research-metrics">
                {[
                  [business.length, "tài liệu doanh nghiệp"],
                  [legal.length, "tài liệu luật"],
                  [rules.length, "rule đề xuất đã lưu"],
                  [result?.executed_rule_count || 0, "rule thực thi"],
                ].map(([n, label]) => (
                  <div key={label}>
                    <strong>{n}</strong>
                    <span>{label}</span>
                  </div>
                ))}
              </div>
              <div className="document-collection-grid">
                {[
                  [
                    "business",
                    "Tài liệu doanh nghiệp",
                    "Thông tin và chứng từ mô tả hoạt động thực tế.",
                  ],
                  [
                    "legal",
                    "Tài liệu luật",
                    "Văn bản nguồn để trích điều khoản và đề xuất rule.",
                  ],
                ].map(([kind, title, text]) => (
                  <button key={kind} onClick={() => onNavigate(kind)}>
                    <small>KHO {kind === "business" ? "01" : "02"}</small>
                    <h2>{title}</h2>
                    <p>{text}</p>
                    <b>+ Thêm / quản lý tài liệu →</b>
                  </button>
                ))}
              </div>
              <section className="research-section">
                <div className="section-head">
                  <h2>Thông tin doanh nghiệp do LLM đề xuất</h2>
                  <button
                    className="button"
                    disabled={busy || !researchClient.profileEnabled()}
                    onClick={() =>
                      act(async () => {
                        await researchClient.profile(id);
                        reload();
                      })
                    }
                  >
                    {busy ? "Đang phân tích…" : "Phân tích từ tài liệu đã chọn"}
                  </button>
                </div>
                {!researchClient.profileEnabled() && (
                  <p className="research-note">
                    Phân tích bằng model đang tắt trong cấu hình. Tài liệu vẫn
                    được nạp và đọc cục bộ; không có câu trả lời mẫu thay thế.
                  </p>
                )}
                {profile ? (
                  <>
                    {workspace.profile_stale && (
                      <p className="document-legacy">
                        Ngữ cảnh đã chọn hoặc mô tả doanh nghiệp đã đổi. Phân
                        tích này giữ căn cứ cũ, cần chạy lại để cập nhật.
                      </p>
                    )}
                    <span className="badge">
                      LLM API · {profile.provenance.model} ·{" "}
                      {profile.provenance.status}
                    </span>
                    <p>{profile.summary}</p>
                    <dl className="profile-facts">
                      <dt>Ngành đề xuất</dt>
                      <dd>{profile.sector || "Chưa xác định"}</dd>
                      <dt>Hoạt động đề xuất</dt>
                      <dd>
                        {profile.activities.join(" · ") || "Chưa xác định"}
                      </dd>
                      <dt>Địa bàn</dt>
                      <dd>{profile.jurisdiction || "Chưa xác định"}</dd>
                    </dl>
                    <details>
                      <summary>Căn cứ đã dùng cho phân tích</summary>
                      {profile.facts.map((fact, index) => (
                        <blockquote key={index}>
                          {fact.quote}
                          <small>
                            {fact.document_id} · trang {fact.page} · [
                            {fact.start}, {fact.end})
                          </small>
                        </blockquote>
                      ))}
                    </details>
                    <p className="research-note">
                      Đây là gợi ý chưa được người dùng xác nhận. Input hash:{" "}
                      {profile.input_sha256}
                    </p>
                  </>
                ) : (
                  <div className="document-empty">
                    Chưa có kết quả LLM. Thêm tài liệu doanh nghiệp, xem bản
                    trích và chọn ngữ cảnh trước khi phân tích. Không tự gán
                    ngành theo tên workspace.
                  </div>
                )}
              </section>
              <section className="research-section">
                <h2>Graph tri thức 3 lớp</h2>
                <div className="research-layers">
                  {[
                    [1, "Văn bản & điều khoản", "legal"],
                    [2, "Rule & khái niệm", "knowledge"],
                    [3, "Doanh nghiệp & hồ sơ", "business"],
                  ].map(([layer, title, destination]) => (
                    <button key={layer} onClick={() => onNavigate(destination)}>
                      <small>LỚP 0{layer}</small>
                      <b>{title}</b>
                      <span>
                        {data?.inventory_graph
                          ? Object.values(data.inventory_graph.nodes).filter(
                              (node) => node.layer === layer,
                            ).length
                          : 0}{" "}
                        node từ kho tài liệu và kết quả đã lưu
                      </span>
                    </button>
                  ))}
                </div>
              </section>
              {workspace.legacy_research_context && (
                <p className="document-legacy">
                  Lượt nghiên cứu cũ dùng ngữ cảnh nhà trọ cấu hình sẵn bởi
                  developer. Các rule đó chưa được tạo lại từ hồ sơ hiện tại và
                  không được coi là kết quả phân tích doanh nghiệp tổng quát.
                </p>
              )}
            </>
          )}
          {(view === "business" || view === "legal") && collection(view)}
          {view === "knowledge" && (
            <>
              <p className="research-disclaimer">
                Rule đề xuất chưa xác minh; {result?.executed_rule_count || 0}{" "}
                rule thực thi. Việc nạp tài liệu không tự kích hoạt rule hoặc
                kết luận pháp lý.
              </p>
              {workspace.legacy_research_context && (
                <p className="document-legacy">
                  Kết quả cũ dùng ngữ cảnh developer cấu hình sẵn; cần phân tích
                  lại từ các tài liệu đã chọn. Không tự sửa lịch sử cũ.
                </p>
              )}
              <div className="research-rule-grid">
                <div className="research-rule-list">
                  {rules.map((rule) => (
                    <button
                      key={rule.id}
                      aria-pressed={selectedRule?.id === rule.id}
                      onClick={() => setRuleId(rule.id)}
                    >
                      <small>
                        {rule.article} · Trang {rule.page}
                      </small>
                      <b>{rule.title}</b>
                      <span className="badge warn">
                        LLM đề xuất · chờ duyệt
                      </span>
                    </button>
                  ))}
                  {!rules.length && (
                    <div className="document-empty">
                      Chưa có rule đề xuất. Tài liệu luật và hồ sơ doanh nghiệp
                      đang được lưu riêng; luồng sinh rule tổng quát chưa được
                      bật.
                    </div>
                  )}
                </div>
                {selectedRule && (
                  <article className="research-rule-detail">
                    <h2>{selectedRule.title}</h2>
                    <p>{selectedRule.requirement}</p>
                    <blockquote>{selectedRule.quote}</blockquote>
                    <dl>
                      <dt>Điều / trang</dt>
                      <dd>
                        {selectedRule.article} · {selectedRule.page}
                      </dd>
                      <dt>Điều kiện áp dụng</dt>
                      <dd>{selectedRule.applicability}</dd>
                      <dt>Ngày hiệu lực đề xuất</dt>
                      <dd>{selectedRule.valid_from || "Chưa xác định"}</dd>
                      <dt>Cần thêm thông tin</dt>
                      <dd>{selectedRule.missing_facts.join(" · ")}</dd>
                    </dl>
                    {selectedRule.source_url && (
                      <a
                        href={selectedRule.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Mở nguồn chính thức ↗
                      </a>
                    )}
                    <code>SHA-256 {selectedRule.source_sha256}</code>
                  </article>
                )}
              </div>
              {result && (
                <details>
                  <summary>Giới hạn của lượt nghiên cứu đã lưu</summary>
                  <p>
                    Dừng: {result.stop_reason}. Độ phủ nhóm dự kiến không chứng
                    minh đã tìm đủ luật.
                  </p>
                  {result.missing_topics.map((topic) => (
                    <p key={topic}>
                      {result.topics.find((item) => item.id === topic)
                        ?.question || topic}
                    </p>
                  ))}
                  {result.gaps.map((gap, i) => (
                    <p className="research-note" key={i}>
                      {gap}
                    </p>
                  ))}
                </details>
              )}
            </>
          )}
          {view === "settings" && (
            <form
              className="research-form"
              onSubmit={(event) => {
                event.preventDefault();
                act(async () => {
                  await researchClient.updateWorkspace(id, name, description);
                  reload();
                });
              }}
            >
              <label>
                Tên hiển thị
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={150}
                  required
                />
              </label>
              <label>
                Mô tả hoạt động do người dùng cung cấp
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  maxLength={2000}
                  rows={5}
                />
              </label>
              <button className="button primary" disabled={busy}>
                Lưu thông tin
              </button>
              <p className="research-note">
                Thông tin nhập tay được ghi là do người dùng cung cấp, không gắn
                nhãn LLM. Không nhập dữ liệu cá nhân không cần thiết vào phần mô
                tả gửi model.
              </p>
            </form>
          )}
        </>
      )}
    </div>
  );
}
