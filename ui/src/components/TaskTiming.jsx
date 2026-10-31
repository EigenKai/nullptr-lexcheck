import React, { useState } from "react";
import { resultLabel } from "../api.js";

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
      <h3>Kế hoạch khắc phục</h3>
      <label>
        Hạn nội bộ
        <input
          type="date"
          value={internalDue}
          onChange={(e) => setInternalDue(e.target.value)}
        />
      </label>
      <label>
        Hạn theo luật (reviewer nhập)
        <input
          type="date"
          value={legalDue}
          onChange={(e) => setLegalDue(e.target.value)}
        />
      </label>
      <p className="footnote">
        Hạn nội bộ không phải hạn theo luật. Chỉ nhập hạn theo luật sau khi đối
        chiếu nguồn; để trống nếu chưa xác định.
      </p>
      <label>
        Nguồn hạn theo luật (phiên bản điều khoản)
        <select
          value={legalClause}
          onChange={(e) => setLegalClause(e.target.value)}
        >
          <option value="">Chưa chọn nguồn</option>
          {check.clause_snapshots
            .filter((c) => c.verification_status === "verified")
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.id} · {c.article}
              </option>
            ))}
        </select>
      </label>
      <label>
        Câu trích làm căn cứ cho hạn theo luật
        <textarea
          value={legalQuote}
          onChange={(e) => setLegalQuote(e.target.value)}
        />
      </label>
      <label>
        Điều kiện đóng việc
        <textarea
          value={conditions}
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
          Giao xử lý có hạn
        </button>
        <button
          className="button secondary"
          disabled={!writable}
          onClick={() => decide("acknowledge")}
        >
          Đánh dấu đã đọc
        </button>
      </div>
      {plan.internal_due_on && <p>Hạn nội bộ đã lưu: {plan.internal_due_on}</p>}
      {plan.legal_due_on && (
        <p>
          Hạn theo luật: {plan.legal_due_on} (nguồn:{" "}
          {plan.legal_clause_version_id})
        </p>
      )}
      <h3>Đóng việc sau kiểm tra lại</h3>
      {plan.closure_conditions && (
        <>
          <p>{plan.closure_conditions}</p>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={conditionsMet}
              onChange={(e) => setConditionsMet(e.target.checked)}
            />
            Tôi đã kiểm tra các điều kiện đóng việc
          </label>
        </>
      )}
      <label>
        Kết quả kiểm tra lại dùng để đóng việc
        <select
          value={closureCheckId}
          onChange={(e) => setClosureCheckId(e.target.value)}
        >
          <option value="">Chọn lượt kiểm tra mới</option>
          {(history?.checks || [])
            .filter((c) => c.parent_check_id === check.id)
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.id} · {resultLabel(c)}
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
        Đóng việc sau kiểm tra lại
      </button>
      <p className="footnote">
        Đã đọc chỉ ghi nhận việc tiếp nhận, không đóng việc. Nguồn, điều kiện và
        kết quả kiểm tra mới phải được đối chiếu trước khi đóng việc.
      </p>
    </section>
  );
}
