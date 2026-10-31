import React, { useState } from "react";
import { Badge } from "./shared.jsx";

export default function LawChanges({
  history,
  request,
  act,
  refreshHistory,
  session,
  busy,
}) {
  const [note, setNote] = useState("");
  const [reviewDate, setReviewDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const manager = session?.group === "manager";
  const send = (path, body) =>
    act("Đang ghi nhận diễn giải nguồn…", async () => {
      await request(path, { method: "POST", body: JSON.stringify(body) });
      await refreshHistory();
    });
  return (
    <section className="form-panel">
      <h2>Thay đổi pháp luật · preloaded</h2>
      <p>
        Nguồn mới phải được kiểm chứng và có diễn giải của người có quyền. Ngày
        ban hành, hiệu lực, nhận và kích hoạt được giữ riêng.
      </p>
      <button
        className="button secondary"
        disabled={!manager || !!busy}
        onClick={() =>
          act("Đang nạp sự kiện preloaded…", async () => {
            const response = await fetch("/legal-event.json");
            if (!response.ok)
              throw new Error("Không đọc được sự kiện preloaded.");
            await request("/legal-changes", {
              method: "POST",
              body: JSON.stringify(await response.json()),
            });
            await refreshHistory();
          })
        }
      >
        Nạp thay đổi luật preloaded
      </button>
      <label>
        Ghi chú diễn giải
        <textarea value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <label>
        Ngày rà soát
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
            Ban hành {state.event.issued_on} · Hiệu lực{" "}
            {state.event.effective_on} · Nhận {state.event.received_at}
          </p>
          <div className="diff-grid">
            <section>
              <h3>Căn cứ trước</h3>
              <p>
                Phiên bản {state.event.previous_clause_version_id}; xem snapshot
                trong lịch sử để giữ đúng căn cứ cũ.
              </p>
            </section>
            <section>
              <h3>Điều khoản mới</h3>
              <blockquote>{state.event.new_clause.text}</blockquote>
              <p>{state.event.new_clause.verification_status}</p>
            </section>
          </div>
          <p>
            Diễn giải: {state.interpretation} · Người duyệt:{" "}
            {state.reviewed_by || "Chưa có"} · Kích hoạt:{" "}
            {state.activated_at || "Chưa kích hoạt"}
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
              Ghi nhận diễn giải
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
              Bác bỏ diễn giải
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
              Kích hoạt theo ngày
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}
