import React from "react";
import { Icon, Page, Badge, recordNames, ruleNames, date } from "./shared.jsx";
import { resultLabel, evidenceParts } from "../api.js";
import Evaluation from "./Evaluation.jsx";
import Patterns from "./Patterns.jsx";
import TaskDashboard from "./TaskDashboard.jsx";
import { languageOf, useT } from "../i18n.jsx";

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
  const t = useT();
  return (
    <Page
      eyebrow={t("KẾT QUẢ CŨ & QUYẾT ĐỊNH")}
      title={t("Lịch sử quyết định")}
    >
      <p className="page-description">
        {t("Mỗi lượt kiểm tra lưu snapshot, phiên bản nguồn và quyết định.")}
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
        <p>{t("Chưa lấy được lịch sử từ API.")}</p>
      ) : (
        <>
          {features.task_dashboard && (
            <TaskDashboard history={history} inspect={inspect} />
          )}
          <div className="metrics">
            <div className="metric">
              <strong>{history.checks.length}</strong>
              <small>{t("Lượt kiểm tra")}</small>
            </div>
            <div className="metric">
              <strong>{history.decisions.length}</strong>
              <small>{t("Quyết định")}</small>
            </div>
            <div className="metric">
              <strong>{history.events.length}</strong>
              <small>{t("Sự kiện")}</small>
            </div>
          </div>
          {history.checks.map((c) => (
            <details className="review-card" key={c.id}>
              <summary>
                {c.id} · {resultLabel(c, t)} <Badge neutral>{c.mode}</Badge>
              </summary>
              <p>
                {date(c.created_at, t)} ·{" "}
                {t("{count} rule đã chạy", { count: c.rules_checked.length })} ·
                LLM {c.model_status}
              </p>
              <p>
                {t("Rule: {list}", {
                  list:
                    c.rule_snapshots
                      .map((r) => `${r.id} v${r.version}`)
                      .join(", ") || t("Chưa có rule thực thi"),
                })}
              </p>
              <p>
                {t("Phiên bản: {list}", {
                  list: c.snapshot.versions.map((v) => v.id).join(", "),
                })}
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
                  {f.rule_id} · {t("Xem phát hiện")}
                </button>
              ))}
              <details>
                <summary>{t("Snapshot gốc (JSON)")}</summary>
                <pre lang="vi">{JSON.stringify(c, null, 2)}</pre>
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
                <p lang={languageOf(d.request.note)}>{d.request.note}</p>
                {features.remediation && (
                  <>
                    {d.request.internal_due_on && (
                      <p>
                        {t("Hạn nội bộ: {date}", {
                          date: d.request.internal_due_on,
                        })}
                      </p>
                    )}
                    {d.request.legal_due_on && (
                      <p>
                        {t("Hạn theo luật: {date} (nguồn: {source})", {
                          date: d.request.legal_due_on,
                          source: d.request.legal_clause_version_id,
                        })}
                      </p>
                    )}
                    {d.request.closure_conditions && (
                      <p>
                        {t("Điều kiện đóng việc:")}{" "}
                        <span lang={languageOf(d.request.closure_conditions)}>
                          {d.request.closure_conditions}
                        </span>
                      </p>
                    )}
                    {d.request.action === "acknowledge" && (
                      <p>{t("Đã đọc · trạng thái việc không đổi")}</p>
                    )}
                  </>
                )}
                <small>
                  {d.request.actor} · {d.request.owner || t("Chưa giao")} ·{" "}
                  {date(d.created_at, t)}
                </small>
              </article>
            ))
          ) : (
            <p className="empty-state">
              {t("Chưa có quyết định nào được lưu.")}
            </p>
          )}
        </>
      )}
    </Page>
  );
}
