import React, { useState } from "react";
import { Badge } from "./shared.jsx";
import { taskRows, ownerSummaries, ownerLabels, taskLabels } from "../tasks.js";

export default function TaskDashboard({ history, inspect }) {
  const [owner, setOwner] = useState("all");
  const [status, setStatus] = useState("all");
  const rows = taskRows(history);
  const shown = rows.filter(
    (row) =>
      (owner === "all" || row.owner === owner) &&
      (status === "all" || row.status === status),
  );
  return (
    <section className="task-dashboard" aria-label="Dashboard việc khắc phục">
      <h2>Việc khắc phục</h2>
      <p className="page-description">
        Trạng thái lấy từ quyết định mới nhất của từng phát hiện. Đã đọc không
        tự đóng việc.
      </p>
      <div className="metrics">
        {["open", "assigned", "closed"].map((key) => (
          <div className="metric" key={key}>
            <strong>{rows.filter((row) => row.status === key).length}</strong>
            <small>{taskLabels[key]}</small>
          </div>
        ))}
      </div>
      <div className="table-scroll">
        <table>
          <caption>Phân bổ theo người phụ trách trong demo</caption>
          <thead>
            <tr>
              <th>Người phụ trách</th>
              <th>Việc mở</th>
              <th>Đang xử lý</th>
              <th>Đã đóng</th>
              <th>Đã bác bỏ</th>
            </tr>
          </thead>
          <tbody>
            {ownerSummaries(rows).map((row) => (
              <tr key={row.owner}>
                <th>{ownerLabels[row.owner]}</th>
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
          Lọc người phụ trách
          <select value={owner} onChange={(e) => setOwner(e.target.value)}>
            <option value="all">Tất cả</option>
            {Object.entries(ownerLabels).map(([key, name]) => (
              <option key={key} value={key}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Lọc trạng thái việc
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="all">Tất cả</option>
            {Object.entries(taskLabels).map(([key, name]) => (
              <option key={key} value={key}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Phát hiện / phiên bản</th>
              <th>Người phụ trách</th>
              <th>Trạng thái</th>
              <th>Hạn xử lý</th>
              <th>Xem căn cứ</th>
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
                <td>{ownerLabels[row.owner]}</td>
                <td>
                  <Badge neutral>{taskLabels[row.status]}</Badge>
                </td>
                <td>
                  {row.decision?.request.internal_due_on ? (
                    <>Hạn nội bộ: {row.decision.request.internal_due_on}</>
                  ) : (
                    "Chưa đặt hạn nội bộ"
                  )}
                  {row.decision?.request.legal_due_on && (
                    <>
                      <br />
                      Hạn theo luật: {row.decision.request.legal_due_on}
                      <br />
                      Nguồn:{" "}
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
                    Xem phát hiện
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!shown.length && (
        <p className="empty-state">Chưa có việc phù hợp với bộ lọc.</p>
      )}
    </section>
  );
}
