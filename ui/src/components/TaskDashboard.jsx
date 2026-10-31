import React, { useState } from "react";
import { Badge } from "./shared.jsx";
import { taskRows, ownerSummaries, ownerLabels, taskLabels } from "../tasks.js";
import { useT } from "../i18n.jsx";

export default function TaskDashboard({ history, inspect }) {
  const t = useT();
  const [owner, setOwner] = useState("all");
  const [status, setStatus] = useState("all");
  const rows = taskRows(history);
  const shown = rows.filter(
    (row) =>
      (owner === "all" || row.owner === owner) &&
      (status === "all" || row.status === status),
  );
  return (
    <section className="task-dashboard" aria-label={t("Dashboard việc khắc phục")}>
      <h2>{t("Việc khắc phục")}</h2>
      <p className="page-description">
        {t("Trạng thái theo quyết định mới nhất; đã đọc không tự đóng việc.")}
      </p>
      <div className="metrics">
        {["open", "assigned", "closed"].map((key) => (
          <div className="metric" key={key}>
            <strong>{rows.filter((row) => row.status === key).length}</strong>
            <small>{t(taskLabels[key])}</small>
          </div>
        ))}
      </div>
      <div className="table-scroll">
        <table>
          <caption>{t("Phân bổ theo người phụ trách trong demo")}</caption>
          <thead>
            <tr>
              <th>{t("Người phụ trách")}</th>
              <th>{t("Việc mở")}</th>
              <th>{t("Đang xử lý")}</th>
              <th>{t("Đã đóng")}</th>
              <th>{t("Đã bác bỏ")}</th>
            </tr>
          </thead>
          <tbody>
            {ownerSummaries(rows).map((row) => (
              <tr key={row.owner}>
                <th>{t(ownerLabels[row.owner])}</th>
                <td>{row.open}</td>
                <td>{row.assigned}</td>
                <td>{row.closed}</td>
                <td>{row.dismissed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="task-filters">
        <label>
          {t("Lọc người phụ trách")}
          <select value={owner} onChange={(e) => setOwner(e.target.value)}>
            <option value="all">{t("Tất cả")}</option>
            {Object.entries(ownerLabels).map(([key, name]) => (
              <option key={key} value={key}>
                {t(name)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("Lọc trạng thái việc")}
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="all">{t("Tất cả")}</option>
            {Object.entries(taskLabels).map(([key, name]) => (
              <option key={key} value={key}>
                {t(name)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{t("Phát hiện / phiên bản")}</th>
              <th>{t("Người phụ trách")}</th>
              <th>{t("Trạng thái")}</th>
              <th>{t("Hạn xử lý")}</th>
              <th>{t("Xem căn cứ")}</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((row) => (
              <tr key={row.finding.id} data-finding-id={row.finding.id}>
                <td>
                  {row.finding.rule_id}
                  <br />
                  <code>{row.finding.record_version_id}</code>
                </td>
                <td>{t(ownerLabels[row.owner])}</td>
                <td>
                  <Badge neutral>{t(taskLabels[row.status])}</Badge>
                </td>
                <td>
                  {row.decision?.request.internal_due_on ? (
                    <>{t("Hạn nội bộ: {date}", { date: row.decision.request.internal_due_on })}</>
                  ) : (
                    t("Chưa đặt hạn nội bộ")
                  )}
                  {row.decision?.request.legal_due_on && (
                    <>
                      <br />
                      {t("Hạn theo luật: {date}", {
                        date: row.decision.request.legal_due_on,
                      })}
                      <br />
                      {t("Nguồn:")}{" "}
                      <code>
                        {row.decision.request.legal_clause_version_id}
                      </code>
                    </>
                  )}
                </td>
                <td>
                  <button
                    className="button secondary"
                    onClick={() =>
                      inspect({
                        type: "finding",
                        value: row.finding,
                        check: row.check,
                      })
                    }
                  >
                    {t("Xem phát hiện")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!shown.length && (
        <p className="empty-state">{t("Chưa có việc phù hợp với bộ lọc.")}</p>
      )}
    </section>
  );
}
