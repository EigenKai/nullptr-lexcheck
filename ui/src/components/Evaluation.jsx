import React, { useState } from "react";
import { useT, N_ } from "../i18n.jsx";

export default function Evaluation({ request, act }) {
  const t = useT();
  const [report, setReport] = useState(null);
  return (
    <section className="form-panel">
      <h2>{t("Đánh giá trên dữ liệu đã gán nhãn")}</h2>
      <button
        className="button secondary"
        onClick={() =>
          act(N_("Đang đọc báo cáo đánh giá…"), async () =>
            setReport(await request("/evaluation")),
          )
        }
      >
        {t("Đọc báo cáo từ API")}
      </button>
      {report && (
        <>
          <p>
            {report.phase} · n={report.n} ·{" "}
            {report.git_sha || t("Chưa ghi commit")}
          </p>
          <p>
            {report.n === 0
              ? t("Chưa đo chất lượng phát hiện.")
              : report.note}
          </p>
          {report.n > 0 && (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{t("Hệ thống")}</th>
                    <th>{t("Số ca")}</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>{t("Cờ sai trên ca sạch")}</th>
                    <th>Model calls</th>
                  </tr>
                </thead>
                <tbody>
                  {report.systems.map((s) => (
                    <tr key={s.system}>
                      <td>{s.system}</td>
                      <td>{s.evaluated_cases}</td>
                      <td>{s.precision ?? t("Chưa đo")}</td>
                      <td>{s.recall ?? t("Chưa đo")}</td>
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
