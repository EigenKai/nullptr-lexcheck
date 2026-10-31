import React, { useState } from "react";
import { resultLabel } from "../api.js";
import { useT } from "../i18n.jsx";

export default function TaskTiming({
  current,
  check,
  history,
  owner,
  decide,
  busy,
  offline,
  session,
  closureCheckId,
  setClosureCheckId,
}) {
  const t = useT();
  const prior = [...(history?.decisions || [])]
    .reverse()
    .find((d) => d.request.finding_id === current.id);
  const plan = prior?.request || {};
  const [internalDue, setInternalDue] = useState(plan.internal_due_on || "");
  const [legalDue, setLegalDue] = useState(plan.legal_due_on || "");
  const [legalClause, setLegalClause] = useState(
    plan.legal_clause_version_id || "",
  );
  const [legalQuote, setLegalQuote] = useState(plan.legal_deadline_quote || "");
  const [conditions, setConditions] = useState(plan.closure_conditions || "");
  const [conditionsMet, setConditionsMet] = useState(false);
  const writable =
    !busy &&
    !offline &&
    session?.group === "manager" &&
    check.mode === "live" &&
    !["closed", "dismissed"].includes(prior?.task_status);
  return (
    <section className="task-timing">
      <h3>{t("Kế hoạch khắc phục")}</h3>
      <label>
        {t("Hạn nội bộ")}
        <input
          type="date"
          value={internalDue}
          onChange={(e) => setInternalDue(e.target.value)}
        />
      </label>
      <label>
        {t("Hạn theo luật (reviewer nhập)")}
        <input
          type="date"
          value={legalDue}
          onChange={(e) => setLegalDue(e.target.value)}
        />
      </label>
      <p className="footnote">
        {t("Hạn nội bộ không phải hạn theo luật. Chỉ nhập hạn luật sau khi đối chiếu nguồn.")}
      </p>
      <label>
        {t("Nguồn hạn theo luật")}
        <select
          value={legalClause}
          onChange={(e) => setLegalClause(e.target.value)}
        >
          <option value="">{t("Chưa chọn nguồn")}</option>
          {check.clause_snapshots
            .filter((c) => c.verification_status === "verified")
            .map((c) => (
              <option key={c.id} value={c.id} lang="vi">
                {c.id} · {c.article}
              </option>
            ))}
        </select>
      </label>
      <label>
        {t("Câu trích căn cứ hạn theo luật")}
        <textarea
          value={legalQuote}
          lang="vi"
          onChange={(e) => setLegalQuote(e.target.value)}
        />
      </label>
      <label>
        {t("Điều kiện đóng việc")}
        <textarea
          value={conditions}
          lang="vi"
          onChange={(e) => setConditions(e.target.value)}
        />
      </label>
      <div className="action-row">
        <button
          className="button secondary"
          disabled={!writable || !internalDue || !conditions.trim()}
          onClick={() =>
            decide("assign", {
              owner,
              internal_due_on: internalDue,
              legal_due_on: legalDue || null,
              legal_clause_version_id: legalClause || null,
              legal_deadline_quote: legalQuote || null,
              closure_conditions: conditions.trim(),
            })
          }
        >
          {t("Giao xử lý có hạn")}
        </button>
        <button
          className="button secondary"
          disabled={!writable}
          onClick={() => decide("acknowledge")}
        >
          {t("Đánh dấu đã đọc")}
        </button>
      </div>
      {plan.internal_due_on && (
        <p>
          {t("Hạn nội bộ đã lưu: {date}", { date: plan.internal_due_on })}
        </p>
      )}
      {plan.legal_due_on && (
        <p>
          {t("Hạn theo luật: {date} (nguồn: {source})", {
            date: plan.legal_due_on,
            source: plan.legal_clause_version_id,
          })}
        </p>
      )}
      <h3>{t("Đóng việc")}</h3>
      {plan.closure_conditions && (
        <>
          <p lang="vi">{plan.closure_conditions}</p>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={conditionsMet}
              onChange={(e) => setConditionsMet(e.target.checked)}
            />
            {t("Tôi đã kiểm tra điều kiện đóng việc")}
          </label>
        </>
      )}
      <label>
        {t("Kết quả kiểm tra lại dùng để đóng việc")}
        <select
          value={closureCheckId}
          onChange={(e) => setClosureCheckId(e.target.value)}
        >
          <option value="">{t("Chọn lượt kiểm tra mới")}</option>
          {(history?.checks || [])
            .filter((c) => c.parent_check_id === check.id)
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.id} · {resultLabel(c, t)}
              </option>
            ))}
        </select>
      </label>
      <button
        className="button secondary"
        disabled={
          !writable ||
          !closureCheckId ||
          (!!plan.closure_conditions && !conditionsMet)
        }
        onClick={() =>
          decide("close", { closure_conditions_met: conditionsMet })
        }
      >
        {t("Đóng việc sau kiểm tra lại")}
      </button>
      <p className="footnote">
        {t("Đánh dấu đã đọc không đóng việc. Đóng việc cần đối chiếu nguồn, điều kiện và lần kiểm tra mới.")}
      </p>
    </section>
  );
}
