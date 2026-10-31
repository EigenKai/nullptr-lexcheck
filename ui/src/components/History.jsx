import React from "react";
import { Icon, Page, Badge, recordNames, ruleNames, date } from "./shared.jsx";
import { resultLabel, evidenceParts } from "../api.js";
import Evaluation from "./Evaluation.jsx";
import Patterns from "./Patterns.jsx";
import TaskDashboard from "./TaskDashboard.jsx";
export default function History({
  history,
  busy,
  note,
  owner,
  act,
  inspect,
  versions,
  check,
  request,
  features,
  session,
  refreshHistory,
}) {
  return (
    <Page
      eyebrow="KẾT QUẢ CŨ & QUYẾT ĐỊNH ĐƯỢC GIỮ LẠI"
      title="Lịch sử quyết định"
    >
      <p className="page-description">
        Mỗi lượt kiểm tra giữ snapshot đầu vào, phiên bản nguồn và quyết định
        của người duyệt.
      </p>
      {features.layer1 && session?.group === "manager" && (
        <Evaluation request={request} act={act} />
      )}
      {features.layer3 && (
        <Patterns
          history={history}
          request={request}
          act={act}
          refreshHistory={refreshHistory}
          session={session}
          busy={busy}
        />
      )}
      {!history ? (
        <p>Chưa lấy được lịch sử từ API.</p>
      ) : (
        <>
          {features.task_dashboard && (
            <TaskDashboard history={history} inspect={inspect} />
          )}
          <div className="metrics">
            <div className="metric">
              <strong>{history.checks.length}</strong>
              <small>Lượt kiểm tra</small>
            </div>
            <div className="metric">
              <strong>{history.decisions.length}</strong>
              <small>Quyết định</small>
            </div>
            <div className="metric">
              <strong>{history.events.length}</strong>
              <small>Sự kiện</small>
            </div>
          </div>
          {history.checks.map((c) => (
            <details className="review-card" key={c.id}>
              <summary>
                {c.id} · {resultLabel(c)} <Badge neutral>{c.mode}</Badge>
              </summary>
              <p>
                {date(c.created_at)} · {c.rules_checked.length} rule đã chạy ·
                LLM {c.model_status}
              </p>
              <p>
                Rule:{" "}
                {c.rule_snapshots
                  .map((r) => `${r.id} v${r.version}`)
                  .join(", ") || "Chưa có rule thực thi"}
              </p>
              <p>
                Phiên bản: {c.snapshot.versions.map((v) => v.id).join(", ")}
              </p>
              {c.findings.map((f) => (
                <button
                  className="button secondary"
                  key={f.id}
                  onClick={() =>
                    inspect({
                      type: "finding",
                      value: f,
                      check: c,
                    })
                  }
                >
                  {f.rule_id} · Xem phát hiện
                </button>
              ))}
              <details>
                <summary>Snapshot gốc (JSON)</summary>
                <pre>{JSON.stringify(c, null, 2)}</pre>
              </details>
            </details>
          ))}
          {history.decisions.length ? (
            history.decisions.map((d) => (
              <article className="review-card" key={d.id}>
                <Badge neutral>{d.task_status}</Badge>
                <h3>
                  {d.request.action} · {d.request.finding_id}
                </h3>
                <p>{d.request.note}</p>
                {features.remediation && (
                  <>
                    {d.request.internal_due_on && (
                      <p>Hạn nội bộ: {d.request.internal_due_on}</p>
                    )}
                    {d.request.legal_due_on && (
                      <p>
                        Hạn theo luật: {d.request.legal_due_on} (nguồn:{" "}
                        {d.request.legal_clause_version_id})
                      </p>
                    )}
                    {d.request.closure_conditions && (
                      <p>Điều kiện đóng việc: {d.request.closure_conditions}</p>
                    )}
                    {d.request.action === "acknowledge" && (
                      <p>Đã đọc · trạng thái việc được giữ nguyên</p>
                    )}
                  </>
                )}
                <small>
                  {d.request.actor} ·{" "}
                  {d.request.owner || "Chưa giao người xử lý"} ·{" "}
                  {date(d.created_at)}
                </small>
              </article>
            ))
          ) : (
            <p className="empty-state">
              Chưa có quyết định của reviewer được lưu.
            </p>
          )}
        </>
      )}
    </Page>
  );
}
