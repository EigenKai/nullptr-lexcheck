import React from "react";
import { Icon, Badge, recordNames, date } from "./shared.jsx";
import { resultLabel, evidenceParts } from "../api.js";
import { useT } from "../i18n.jsx";
import TaskTiming from "./TaskTiming.jsx";
export default function Evidence({
  bundle,
  history,
  offline,
  busy,
  selected,
  setSelected,
  panel,
  setPanel,
  note,
  setNote,
  owner,
  setOwner,
  versions,
  current,
  check,
  clause,
  decide,
  features,
  session,
  closureCheckId,
  setClosureCheckId,
}) {
  const t = useT();
  // bundle.rules is the static demo fixture, where every rule is disabled, so
  // count the rules the check on screen ran (its stored snapshots) instead.
  const enabledRules =
    check?.mode === "live" && check.model_status === "off"
      ? (check.rule_snapshots || []).filter((r) => r.enabled).length
      : 0;
  return (
    <>
      <div className="panel-heading">
        <Icon name="network" />
        {selected ? t("CHI TIẾT & BẰNG CHỨNG") : t("TRI THỨC ĐƯỢC KẾT NỐI")}
        <button
          className="icon-button close-panel"
          onClick={() => setPanel(false)}
          aria-label={t("Đóng bảng bằng chứng")}
        >
          ×
        </button>
      </div>
      {selected && (
        <button className="back-link" onClick={() => setSelected(null)}>
          {t("← Tổng quan tri thức")}
        </button>
      )}
      {!selected && (
        <>
          <div className="panel-intro">
            <p>{t("Mỗi phát hiện truy được về điều khoản và hồ sơ.")}</p>
          </div>
          <div className="trace-map">
            <div>
              {t("Điều khoản")} <small>{t("Phiên bản & ngày hiệu lực")}</small>
            </div>
            <span>↓ DERIVED_FROM</span>
            <div>
              Rule <small>{t("Trạng thái kiểm chứng")}</small>
            </div>
            <span>↓ EVIDENCE</span>
            <div>
              {t("Hồ sơ doanh nghiệp")}{" "}
              <small>{t("Bản gốc → phát hiện → người quyết định")}</small>
            </div>
          </div>
          <div className="panel-callout">
            <b>{t("Phạm vi hiện tại")}</b>
            <p>{t("Thực phẩm bảo vệ sức khỏe · dữ liệu mẫu.")}</p>
          </div>
          {enabledRules > 0 && (
            <p className="footnote">
              {t("{count} rule đã bật · LLM tắt", { count: enabledRules })}
            </p>
          )}
        </>
      )}
      {selected?.type === "record" && (
        <>
          <h2>{t(recordNames[selected.value.kind])}</h2>
          <code>{selected.value.id}</code>
          {versions
            .filter((v) => v.record_id === selected.value.id)
            .map((v) => (
              <section key={v.id}>
                <h3>
                  {v.id} · v{v.version}
                </h3>
                <p className="record-text" lang="vi">
                  {v.text}
                </p>
                <p className="footnote">
                  {t("Nhận: {date}", { date: date(v.received_at, t) })}
                </p>
                <p>
                  {t("Tham chiếu: {ids}", {
                    ids: v.reference_ids.join(", ") || t("Chưa có"),
                  })}
                </p>
              </section>
            ))}
        </>
      )}
      {current && (
        <>
          <h2>
            {current.rule_id} · v{current.rule_version}
          </h2>
          <Badge neutral={current.status === "needs_evidence"}>
            {check?.mode === "fixture"
              ? t("Fixture · Minh hoạ, chưa chạy engine")
              : current.source === "llm"
                ? t("Suggestion · Người duyệt quyết định")
                : t("Rule · Kiểm tra bằng code")}
          </Badge>
          <p lang="vi">{current.message}</p>
          <p>
            {t("Mức độ: {severity} · Trạng thái: {status}", {
              severity: current.severity,
              status: current.status,
            })}
          </p>
          <p>
            Applicability: {current.applicability || check?.applicability} ·{" "}
            {check?.applicability_reason}
          </p>
          {current.evidence.map((ev, i) => {
            const source = check?.snapshot.versions.find(
              (v) => v.id === ev.record_version_id,
            );
            const parts = source ? evidenceParts(source.text, ev) : null;
            return (
              <section className="evidence-step" key={i}>
                <b>{ev.record_version_id}</b>
                {ev.kind === "missing_field" ? (
                  <p>
                    {t("Hồ sơ đã kết nối thiếu trường:")} <code>{ev.field}</code>
                  </p>
                ) : (
                  <>
                    <p className="record-text" lang="vi">
                      {parts ? (
                        <>
                          {parts[0]}
                          <mark>{parts[1]}</mark>
                          {parts[2]}
                        </>
                      ) : (
                        ev.quote
                      )}
                    </p>
                    <small>
                      {ev.kind === "span" ? (
                        t("Vị trí {start}–{end}", {
                          start: ev.start,
                          end: ev.end,
                        })
                      ) : ev.kind === "cell" ? (
                        <span lang="vi">
                          {ev.sheet} · {ev.cell}
                        </span>
                      ) : (
                        t("Trang {page}", { page: ev.page })
                      )}
                    </small>
                    {!parts && ev.kind === "span" && (
                      <p>{t("Chưa xác nhận vị trí trích dẫn.")}</p>
                    )}
                  </>
                )}
              </section>
            );
          })}
        </>
      )}
      {clause && (
        <section className="clause">
          <Badge neutral>
            {clause.verification_status === "verified"
              ? t("Nguồn đã kiểm chứng")
              : t("Nguồn chờ kiểm chứng")}
          </Badge>
          <h3 lang="vi">
            {clause.document} · {clause.article}
          </h3>
          <code>{clause.id}</code>
          <p>
            {t("Từ {from} đến {to} · {status}", {
              from: clause.valid_from,
              to: clause.valid_to || t("chưa ghi ngày kết thúc"),
              status: clause.in_force,
            })}
          </p>
          <blockquote lang="vi">
            {current?.clause_quote || clause.text}
          </blockquote>
          <a
            href={
              /^https?:\/\//.test(clause.source_url)
                ? clause.source_url
                : undefined
            }
            target="_blank"
            rel="noreferrer"
          >
            {t("Mở văn bản nguồn ↗")}
          </a>
          <p className="footnote">{clause.status_note}</p>
        </section>
      )}
      {current && (
        <section className="decision-form">
          <h3>{t("Quyết định của reviewer")}</h3>
          <label htmlFor="decisionNote">{t("Ghi chú xử lý")}</label>
          <textarea
            id="decisionNote"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <label htmlFor="owner">{t("Người phụ trách")}</label>
          <select
            id="owner"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
          >
            <option value="marketing">Marketing</option>
            <option value="legal">{t("Pháp chế")}</option>
            <option value="document_control">{t("Quản lý hồ sơ")}</option>
          </select>
          <div className="action-row">
            {[
              ["confirm", t("Xác nhận phát hiện")],
              ["reject", t("Bác bỏ")],
              ["assign", t("Giao xử lý")],
            ]
              .filter(
                ([a]) =>
                  a !== "assign" || (features.layer1 && !features.remediation),
              )
              .map(([a, label]) => (
                <button
                  className="button secondary"
                  disabled={
                    !!busy ||
                    offline ||
                    !session ||
                    session.group !== "manager" ||
                    check?.mode !== "live"
                  }
                  key={a}
                  onClick={() => decide(a)}
                >
                  {label}
                </button>
              ))}
          </div>
          {features.remediation ? (
            <TaskTiming
              key={current.id}
              current={current}
              check={check}
              history={history}
              owner={owner}
              decide={decide}
              busy={busy}
              offline={offline}
              session={session}
              closureCheckId={closureCheckId}
              setClosureCheckId={setClosureCheckId}
            />
          ) : (
            <>
              <label htmlFor="closure-check">
                {t("Lượt kiểm tra lại để đóng việc")}
              </label>
              <select
                id="closure-check"
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
              <button
                className="button secondary"
                disabled={
                  !!busy ||
                  offline ||
                  !closureCheckId ||
                  session?.group !== "manager" ||
                  check?.mode !== "live"
                }
                onClick={() => decide("close")}
              >
                {t("Đóng việc sau kiểm tra lại")}
              </button>
              <p className="footnote">
                {t("Cần một lượt kiểm tra lại mới để đóng việc.")}
              </p>
            </>
          )}
        </section>
      )}
    </>
  );
}
