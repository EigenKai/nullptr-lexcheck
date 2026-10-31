import React from "react";
import { Icon, Badge, recordNames } from "./shared.jsx";
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
  const canAsk = !!features.layer1 && !!check && !offline && !busy;
  const chatNote = !features.layer1
    ? "Khung chat đang ở chế độ xem trước. Hỏi đáp chưa được bật trên backend; chưa gửi câu hỏi hoặc gọi model."
    : offline
      ? "API mất kết nối. Câu hỏi chưa được gửi."
      : check
        ? `Chỉ hỏi trên snapshot ${check.id}. Trả lời không tự đóng công việc.`
        : "Chọn một kết quả kiểm tra trong màn Rà soát trước khi hỏi.";
  return (
    <div className="chat-page">
      <div className="eyebrow">
        <span className="status-dot" />
        KHÔNG GIAN DOANH NGHIỆP · CO-DEMO
      </div>
      {(!features.layer1 || offline) && (
        <div className="chat-availability" role="status">
          <b>Chưa kết nối chatbot</b>
          <p>{chatNote}</p>
        </div>
      )}
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
            <button onClick={() => go("knowledge")}>Xem kho tri thức ↗</button>
          </div>
          <div className="suggestion-label">BẮT ĐẦU TỪ MỘT VIỆC CỤ THỂ</div>
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
                !canAsk,
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
            ].map(([i, t, sub, fn, disabled]) => (
              <button
                className="suggestion"
                key={t}
                onClick={fn}
                disabled={disabled}
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
            <button onClick={() => go("knowledge")}>Xem tất cả ↗</button>
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
                    <Badge neutral>
                      {m.model_status} ·{" "}
                      {m.status === "needs_evidence"
                        ? "Cần thêm chứng cứ"
                        : "Có trích dẫn"}
                    </Badge>
                  </div>
                  <p>{m.answer}</p>
                  {(m.citations || []).map((citation, index) => (
                    <blockquote key={index}>
                      <code>{citation.clause_version_id}</code>
                      <p>{citation.quote}</p>
                    </blockquote>
                  ))}
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
            placeholder={
              features.layer1
                ? "Hỏi về hồ sơ, công dụng hoặc việc cần xử lý…"
                : "Chưa kết nối chatbot · chưa thể gửi câu hỏi"
            }
            rows="2"
            maxLength="1000"
            disabled={!canAsk}
            aria-describedby="chat-note"
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
