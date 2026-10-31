import React, { useEffect, useState } from "react";
import { Badge, date } from "./shared.jsx";
import { resultLabel } from "../api.js";
import { N_, useT } from "../i18n.jsx";

export default function ChangeImpact({ history }) {
  const t = useT();
  const [preloaded, setPreloaded] = useState(null);
  const [legalError, setLegalError] = useState("");
  useEffect(() => {
    let current = true;
    fetch("/legal-preview.json")
      .then((response) => {
        if (!response.ok) throw new Error("source_unavailable");
        return response.json();
      })
      .then((value) => {
        if (current) setPreloaded(value);
      })
      .catch(() => {
        if (current)
          setLegalError(
            N_("Chưa tải được nguồn luật nạp trước; chưa thể xác nhận cập nhật từ nguồn này."),
          );
      });
    return () => {
      current = false;
    };
  }, []);
  const legalStates = [...(history?.legal_changes || [])];
  if (
    preloaded?.state &&
    !legalStates.some((state) => state.event.id === preloaded.state.event.id)
  )
    legalStates.push(preloaded.state);
  const queueFor = (id) =>
    (history?.queue || []).filter((item) => item.event_id === id);
  const queueTable = (id) => (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>{t("Phiên bản cần kiểm lại")}</th>
            <th>{t("Kết quả cũ giữ nguyên")}</th>
            <th>{t("Kết quả kiểm lại")}</th>
          </tr>
        </thead>
        <tbody>
          {queueFor(id).map((item) => {
            const fresh = history.checks.find(
              (check) => check.id === item.new_check_id,
            );
            return (
              <tr key={item.id}>
                <td>
                  <code>{item.target_version_id}</code>
                  <br />
                  <Badge neutral>
                    {item.status === "queued" ? t("Chờ kiểm lại") : t("Đã kiểm lại")}
                  </Badge>
                </td>
                <td>
                  <code>{item.previous_check_id}</code>
                </td>
                <td>
                  {fresh ? (
                    <>
                      <code>{fresh.id}</code>
                      <br />
                      {resultLabel(fresh, t)}
                    </>
                  ) : (
                    t("Chưa có kết quả mới")
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
  return (
    <section aria-label={t("Tác động thay đổi nguồn")}>
      <h2>{t("Tác động thay đổi hồ sơ")}</h2>
      {[...(history?.events || [])].reverse().map((event) => (
        <article
          className="review-card"
          key={event.id}
          data-event-id={event.id}
        >
          <Badge neutral>{t("Thay đổi hồ sơ đã ghi nhận")}</Badge>
          <h3>{event.record_id}</h3>
          <p>
            <code>{event.previous_version_id}</code> →{" "}
            <code>{event.new_version.id}</code>
          </p>
          <p>{t("Nhận lúc: {date}", { date: date(event.received_at, t) })}</p>
          <p>{t("Kết quả và quyết định cũ được giữ; chỉ lượt kiểm lại tạo kết quả mới.")}</p>
          {queueTable(event.id)}
        </article>
      ))}
      {!history?.events.length && <p>{t("Chưa có thay đổi hồ sơ được ghi nhận.")}</p>}
      {legalError && <p className="footnote">{t(legalError)}</p>}
      {legalStates.map((state) => (
        <article className="review-card" key={state.event.id}>
          {!(history?.legal_changes || []).some(
            (saved) => saved.event.id === state.event.id,
          ) && <Badge neutral>{t("Luật nạp trước · Chưa áp dụng")}</Badge>}
          <Badge neutral>
            {state.status} ·{" "}
            {state.event.new_clause.verification_status === "verified"
              ? t("Nguồn đã đối chiếu")
              : t("Chờ xác minh nguồn")}
          </Badge>
          <h3>{t("Thay đổi điều khoản")}</h3>
          <p>
            {state.event.previous_clause_version_id} →{" "}
            {state.event.new_clause.id}
          </p>
          <dl>
            <dt>{t("Ban hành")}</dt>
            <dd>{state.event.issued_on}</dd>
            <dt>{t("Hiệu lực")}</dt>
            <dd>{state.event.effective_on}</dd>
            <dt>{t("Nhận")}</dt>
            <dd>{date(state.event.received_at, t)}</dd>
            <dt>{t("Duyệt")}</dt>
            <dd>
              {state.reviewed_at ? date(state.reviewed_at, t) : t("Chưa duyệt")}
            </dd>
          </dl>
          <p>
            {t("Rule liên quan:")}{" "}
            {state.event.proposed_rules.map((rule) => rule.id).join(", ")}
          </p>
          <div className="diff-grid">
            <section>
              <h4>{t("Điều khoản cũ")}</h4>
              <blockquote lang="vi">
                {(preloaded?.previous_clause?.id ===
                state.event.previous_clause_version_id
                  ? preloaded.previous_clause
                  : (history?.checks || [])
                      .flatMap((check) => check.clause_snapshots)
                      .find(
                        (clause) =>
                          clause.id === state.event.previous_clause_version_id,
                      )
                )?.text || t("Không tìm thấy bản cũ trong các nguồn đã kết nối.")}
              </blockquote>
            </section>
            <section>
              <h4>{t("Điều khoản mới")}</h4>
              <blockquote lang="vi">{state.event.new_clause.text}</blockquote>
            </section>
          </div>
          {queueTable(state.event.id)}
        </article>
      ))}
    </section>
  );
}
