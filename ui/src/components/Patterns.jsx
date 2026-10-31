import React, { useState } from "react";
import { useT, N_ } from "../i18n.jsx";

export default function Patterns({
  history,
  request,
  act,
  refreshHistory,
  session,
  busy,
}) {
  const t = useT();
  const [decision, setDecision] = useState("");
  const [phrase, setPhrase] = useState("");
  const [note, setNote] = useState("");
  const send = (path, body) =>
    act(N_("Đang kiểm tra feedback…"), async () => {
      await request(path, { method: "POST", body: JSON.stringify(body) });
      await refreshHistory();
    });
  if (session?.group !== "manager") return null;
  return (
    <section className="form-panel">
      <h2>{t("Feedback có người duyệt")}</h2>
      <p>
        {t("Candidate chưa đổi kết quả; chỉ dùng lại sau guard test và khi được duyệt.")}
      </p>
      <label>
        {t("Quyết định xác nhận")}
        <select value={decision} onChange={(e) => setDecision(e.target.value)}>
          <option value="">{t("Chọn quyết định")}</option>
          {(history?.decisions || [])
            .filter((d) => d.request.action === "confirm")
            .map((d) => (
              <option key={d.id} value={d.id}>
                {d.id} · {d.request.finding_id}
              </option>
            ))}
        </select>
      </label>
      <label>
        {t("Cụm từ trong bằng chứng")}
        <input value={phrase} onChange={(e) => setPhrase(e.target.value)} />
      </label>
      <button
        className="button secondary"
        disabled={!!busy || !decision || !phrase.trim()}
        onClick={() =>
          send("/feedback", {
            decision_id: decision,
            phrase,
            polarity: "positive",
          })
        }
      >
        {t("Tạo Pattern candidate")}
      </button>
      <label>
        {t("Ghi chú duyệt")}
        <textarea value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      {(history?.patterns || []).map((p) => (
        <article className="review-card" key={p.id}>
          <h3>
            {p.id} · {p.state}
          </h3>
          <blockquote lang="vi">{p.phrase}</blockquote>
          <p>
            {p.company_id} · {p.rule_id} v{p.rule_version} ·{" "}
            {p.clause_version_id}
          </p>
          <p>Guard report: {p.test_report_sha256 || t("Chưa có")}</p>
          <button
            className="button secondary"
            disabled={!!busy || !note.trim() || p.state !== "candidate"}
            onClick={() =>
              send(`/patterns/${p.id}/review`, { action: "accept", note })
            }
          >
            {t("Kiểm guard và duyệt")}
          </button>
          <button
            className="button secondary"
            disabled={!!busy || !note.trim() || p.state !== "candidate"}
            onClick={() =>
              send(`/patterns/${p.id}/review`, { action: "reject", note })
            }
          >
            {t("Bác bỏ candidate")}
          </button>
        </article>
      ))}
    </section>
  );
}
