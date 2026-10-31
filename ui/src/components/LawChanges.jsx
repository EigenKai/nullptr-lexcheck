import React, { useState } from "react";
import { Badge } from "./shared.jsx";
import { useT, N_ } from "../i18n.jsx";

export default function LawChanges({
  history,
  request,
  act,
  refreshHistory,
  session,
  busy,
}) {
  const t = useT();
  const [note, setNote] = useState("");
  const [reviewDate, setReviewDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const manager = session?.group === "manager";
  const send = (path, body) =>
    act(N_("Đang ghi nhận…"), async () => {
      await request(path, { method: "POST", body: JSON.stringify(body) });
      await refreshHistory();
    });
  return (
    <section className="form-panel">
      <h2>{t("Thay đổi pháp luật")}</h2>
      <p>{t("Nguồn mới cần kiểm chứng và người có quyền diễn giải.")}</p>
      <button
        className="button secondary"
        disabled={!manager || !!busy}
        onClick={() =>
          act(N_("Đang nạp thay đổi luật…"), async () => {
            const response = await fetch("/legal-event.json");
            if (!response.ok)
              throw new Error(N_("Không đọc được sự kiện preloaded."));
            await request("/legal-changes", {
              method: "POST",
              body: JSON.stringify(await response.json()),
            });
            await refreshHistory();
          })
        }
      >
        {t("Nạp thay đổi luật preloaded")}
      </button>
      <label>
        {t("Ghi chú diễn giải")}
        <textarea value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <label>
        {t("Ngày rà soát")}
        <input
          type="date"
          value={reviewDate}
          onChange={(e) => setReviewDate(e.target.value)}
        />
      </label>
      {(history?.legal_changes || []).map((state) => (
        <article className="review-card" key={state.event.id}>
          <Badge neutral>preloaded · {state.status}</Badge>
          <h3>
            {state.event.previous_clause_version_id} →{" "}
            {state.event.new_clause.id}
          </h3>
          <p>
            {t("Ban hành {issued} · Hiệu lực {effective} · Nhận {received}", {
              issued: state.event.issued_on,
              effective: state.event.effective_on,
              received: state.event.received_at,
            })}
          </p>
          <div className="diff-grid">
            <section>
              <h3>{t("Căn cứ trước")}</h3>
              <p>
                {t("Phiên bản {version}; xem snapshot trong lịch sử.", {
                  version: state.event.previous_clause_version_id,
                })}
              </p>
            </section>
            <section>
              <h3>{t("Điều khoản mới")}</h3>
              <blockquote lang="vi">{state.event.new_clause.text}</blockquote>
              <p>{state.event.new_clause.verification_status}</p>
            </section>
          </div>
          <p>
            {t("Diễn giải")}: <span lang="vi">{state.interpretation}</span> ·{" "}
            {t("Người duyệt")}: {state.reviewed_by || t("Chưa có")} ·{" "}
            {t("Kích hoạt")}: {state.activated_at || t("Chưa có")}
          </p>
          <div className="action-row">
            <button
              className="button secondary"
              disabled={
                !manager || !!busy || !note.trim() || state.status !== "pending"
              }
              onClick={() =>
                send(`/legal-changes/${state.event.id}/review`, {
                  action: "accept",
                  note,
                })
              }
            >
              {t("Ghi nhận diễn giải")}
            </button>
            <button
              className="button secondary"
              disabled={
                !manager || !!busy || !note.trim() || state.status !== "pending"
              }
              onClick={() =>
                send(`/legal-changes/${state.event.id}/review`, {
                  action: "reject",
                  note,
                })
              }
            >
              {t("Bác bỏ diễn giải")}
            </button>
            <button
              className="button secondary"
              disabled={!manager || !!busy || state.status !== "ready"}
              onClick={() =>
                send(`/legal-changes/${state.event.id}/activate`, {
                  review_date: reviewDate,
                })
              }
            >
              {t("Kích hoạt theo ngày")}
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}
