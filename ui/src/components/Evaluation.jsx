import React, { useState } from "react";

export default function Evaluation({ request, act }) {
  const [report, setReport] = useState(null);
  return (
    <section className="form-panel">
      <h2>Đánh giá trên dữ liệu đã gán nhãn</h2>
      <button
        className="button secondary"
        onClick={() =>
          act("Đang đọc báo cáo đánh giá…", async () =>
            setReport(await request("/evaluation")),
          )
        }
      >
        Đọc báo cáo từ API
      </button>
      {report && (
        <>
          <p>
            {report.phase} · n={report.n} ·{" "}
            {report.git_sha || "Chưa ghi commit"}
          </p>
          <p>
            {report.n === 0
              ? "Chưa đo chất lượng phát hiện. Không có số so sánh."
              : report.note}
          </p>
          {report.n > 0 && (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Hệ thống</th>
                    <th>Số ca</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>Cờ sai trên ca sạch</th>
                    <th>Model calls</th>
                  </tr>
                </thead>
                <tbody>
                  {report.systems.map((s) => (
                    <tr key={s.system}>
                      <td>{s.system}</td>
                      <td>{s.evaluated_cases}</td>
                      <td>{s.precision ?? "Chưa đo"}</td>
                      <td>{s.recall ?? "Chưa đo"}</td>
                      <td>{s.false_flags_on_clean}</td>
                      <td>{s.model_calls}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
