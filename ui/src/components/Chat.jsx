import React from "react";
import { Icon, Badge, recordNames } from "./shared.jsx";
import { languageOf, useT } from "../i18n.jsx";

export default function Chat({
  bundle,
  features = {},
  offline,
  busy,
  messages,
  prompt,
  setPrompt,
  go,
  inspect,
  ask,
  versions,
  check,
}) {
  const t = useT();
  const canAsk = !!features.layer1 && !!check && !offline && !busy;
  const chatNote = !features.layer1
    ? t("Chế độ xem trước; chưa gửi câu hỏi hoặc gọi model.")
    : offline
      ? t("API mất kết nối; chưa gửi câu hỏi.")
      : check
        ? t("Chỉ hỏi trên snapshot {id}; trả lời không tự đóng việc.", {
            id: check.id,
          })
        : t("Chọn một kết quả ở Rà soát hồ sơ trước khi hỏi.");
  return (
    <div className="chat-page">
      {(!features.layer1 || offline) && (
        <div className="chat-availability" role="status">
          <b>{t("Chưa kết nối chatbot")}</b>
          <p>{chatNote}</p>
        </div>
      )}
      {!messages.length ? (
        <>
          <section className="hero">
            <div className="hero-copy">
              <h1>
                {t("Chào bạn,")}
                <br />
                {t("mình kiểm tra")}
                <br />
                <em>{t("điều gì hôm nay?")}</em>
              </h1>
            </div>
            <div className="mascot-wrap">
              <img
                className="mascot"
                src="/assets/lex-hero-480.webp"
                alt={t("Lex cầm kính lúp và bảng kiểm")}
                width="240"
                height="240"
              />
            </div>
          </section>
          <div className="context-line">
            <Icon name="network" />
            <b>{t("{count} phiên bản hồ sơ", { count: versions.length })}</b>
            <span>·</span>
            <button onClick={() => go("knowledge")}>
              {t("Xem kho tri thức ↗")}
            </button>
          </div>
          <div className="suggestion-label">{t("BẮT ĐẦU NHANH")}</div>
          <div className="suggestions">
            {[
              [
                "check",
                t("Rà soát nội dung"),
                t("Đối chiếu hồ sơ công bố"),
                () => go("reviews"),
              ],
              [
                "library",
                t("Hỏi từ kho tri thức"),
                t("Tìm hồ sơ và nguồn đang có"),
                () => ask(t("Có hồ sơ nào trong kho?")),
                !canAsk,
              ],
              [
                "refresh",
                t("Có gì vừa thay đổi?"),
                t("So sánh công dụng v1 / v2"),
                () => go("updates"),
              ],
              [
                "clock",
                t("Tiếp tục việc còn dở"),
                t("Xem quyết định đã ghi nhận"),
                () => go("history"),
              ],
            ].map(([icon, title, subtitle, fn, disabled]) => (
              <button
                className="suggestion"
                key={icon}
                onClick={fn}
                disabled={disabled}
              >
                <span>
                  <Icon name={icon} />
                </span>
                <div>
                  <b>{title}</b>
                  <small>{subtitle}</small>
                </div>
                <span className="arrow">↗</span>
              </button>
            ))}
          </div>
          <div className="section-head">
            <h2>{t("Tài liệu đang làm việc")}</h2>
            <button onClick={() => go("knowledge")}>{t("Xem tất cả ↗")}</button>
          </div>
          <div className="file-list">
            {bundle.request.records.slice(0, 2).map((r) => (
              <button
                className="file-row"
                key={r.id}
                onClick={() => inspect({ type: "record", value: r })}
              >
                <span className="file-icon">
                  <Icon name="file" />
                </span>
                <span className="file-info">
                  <b>{t(recordNames[r.kind])}</b>
                  <small>
                    {r.id} · {r.product_id}
                  </small>
                </span>
                <Badge neutral>{t("Mẫu")}</Badge>
              </button>
            ))}
          </div>
        </>
      ) : (
        <>
          <h1 className="chat-title">{t("Hỏi từ kho tri thức")}</h1>
          <div className="messages" aria-live="polite">
            {messages.map((m, i) => (
              <React.Fragment key={i}>
                <div className="message user" lang={languageOf(m.question)}>
                  {m.question}
                </div>
                <div className="message assistant">
                  <div className="assistant-heading">
                    <img
                      src="/assets/lex-avatar-64.png"
                      alt=""
                      width="30"
                      height="30"
                    />
                    Lex{" "}
                    <Badge neutral>
                      {m.model_status} ·{" "}
                      {m.status === "needs_evidence"
                        ? t("Cần thêm chứng cứ")
                        : t("Có trích dẫn")}
                    </Badge>
                  </div>
                  <p lang={languageOf(m.answer)}>{m.answer}</p>
                  {(m.citations || []).map((citation, index) => (
                    <blockquote key={index}>
                      <code>{citation.clause_version_id}</code>
                      <p lang="vi">{citation.quote}</p>
                    </blockquote>
                  ))}
                  <button
                    className="button secondary"
                    onClick={() => go("knowledge")}
                  >
                    {t("Xem hồ sơ nguồn ↗")}
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
            {t("Nhập câu hỏi cho Lex")}
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={
              features.layer1
                ? t("Hỏi về hồ sơ, công dụng hoặc việc cần xử lý…")
                : t("Chưa thể gửi câu hỏi")
            }
            rows="2"
            maxLength="1000"
            disabled={!canAsk}
            aria-describedby="chat-note"
          />
          <div className="composer-bottom">
            <span className="composer-context">
              <Icon name="network" />
              {t("Kho tri thức CO-DEMO")}
            </span>
            <button
              className="send"
              type="submit"
              aria-label={t("Gửi câu hỏi")}
              disabled={!canAsk || !prompt.trim()}
            >
              ↑
            </button>
          </div>
        </form>
        <p className="composer-note" id="chat-note">
          {chatNote}
        </p>
      </div>
    </div>
  );
}
