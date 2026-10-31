import React from "react";
import { Icon, Page, Badge, recordNames, ruleNames, date } from "./shared.jsx";
import { resultLabel, evidenceParts } from "../api.js";
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
  return (
    <>
      <div className="panel-heading">
        <Icon name="network" />
        {selected ? "CHI TIẾT & BẰNG CHỨNG" : "TRI THỨC ĐƯỢC KẾT NỐI"}
        <button
          className="icon-button close-panel"
          onClick={() => setPanel(false)}
          aria-label="Đóng bảng bằng chứng"
        >
          ×
        </button>
      </div>
      {selected && (
        <button className="back-link" onClick={() => setSelected(null)}>
          ← Tổng quan tri thức
        </button>
      )}
      {!selected && (
        <>
          <div className="panel-intro">
            <h2>
              Mỗi phát hiện,
              <br />
              đều có điểm tựa.
            </h2>
            <p>Hồ sơ, điều khoản và quyết định cùng giữ đường truy lại.</p>
          </div>
          <div className="trace-map">
            <div>
              Điều khoản <small>Phiên bản & ngày hiệu lực</small>
            </div>
            <span>↓ DERIVED_FROM</span>
            <div>
              Rule <small>Trạng thái kiểm chứng</small>
            </div>
            <span>↓ EVIDENCE</span>
            <div>
              Hồ sơ doanh nghiệp{" "}
              <small>Bản gốc → phát hiện → người quyết định</small>
            </div>
          </div>
          <div className="panel-callout">
            <b>Phạm vi hiện tại</b>
            <p>
              Pack thực phẩm bảo vệ sức khỏe. Dữ liệu công ty được dựng cho
              demo. Quyết định được kiểm tra bằng phiên demo do server cấp.
            </p>
          </div>
          <p className="footnote">
            {bundle?.rules.filter((r) => r.enabled).length || 0} rule đã bật ·
            LLM tắt
          </p>
        </>
      )}
      {selected?.type === "record" && (
        <>
          <h2>{recordNames[selected.value.kind]}</h2>
          <code>{selected.value.id}</code>
          {versions
            .filter((v) => v.record_id === selected.value.id)
            .map((v) => (
              <section key={v.id}>
                <h3>
                  {v.id} · v{v.version}
                </h3>
                <p className="record-text">{v.text}</p>
                <p className="footnote">Nhận: {date(v.received_at)}</p>
                <p>Tham chiếu: {v.reference_ids.join(", ") || "Chưa có"}</p>
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
              ? "Fixture · Minh hoạ, chưa chạy engine"
              : current.source === "llm"
                ? "Suggestion · Người duyệt quyết định"
                : "Rule · Kiểm tra bằng code"}
          </Badge>
          <p>{current.message}</p>
          <p>
            Mức độ: {current.severity} · Trạng thái: {current.status}
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
                    Không tìm thấy trường <code>{ev.field}</code> trong các hồ
                    sơ đã kết nối.
                  </p>
                ) : (
                  <>
                    <p className="record-text">
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
                      {ev.kind === "span"
                        ? `Vị trí ${ev.start}–${ev.end}`
                        : ev.kind === "cell"
                          ? `${ev.sheet} · ${ev.cell}`
                          : `Trang ${ev.page}`}
                    </small>
                    {!parts && ev.kind === "span" && (
                      <p>Chưa xác nhận vị trí trích dẫn.</p>
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
              ? "Nguồn đã kiểm chứng"
              : "Nguồn chờ kiểm chứng"}
          </Badge>
          <h3>
            {clause.document} · {clause.article}
          </h3>
          <code>{clause.id}</code>
          <p>
            Từ {clause.valid_from} đến{" "}
            {clause.valid_to || "chưa ghi ngày kết thúc"} · {clause.in_force}
          </p>
          <blockquote>{current?.clause_quote || clause.text}</blockquote>
          <a
            href={
              /^https?:\/\//.test(clause.source_url)
                ? clause.source_url
                : undefined
            }
            target="_blank"
            rel="noreferrer"
          >
            Mở văn bản nguồn ↗
          </a>
          <p className="footnote">{clause.status_note}</p>
        </section>
      )}
      {current && (
        <section className="decision-form">
          <h3>Quyết định của reviewer</h3>
          <label htmlFor="decisionNote">Ghi chú xử lý</label>
          <textarea
            id="decisionNote"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <label htmlFor="owner">Người phụ trách</label>
          <select
            id="owner"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
          >
            <option value="marketing">Marketing</option>
            <option value="legal">Pháp chế</option>
            <option value="document_control">Quản lý hồ sơ</option>
          </select>
          <div className="action-row">
            {[
              ["confirm", "Xác nhận phát hiện"],
              ["reject", "Bác bỏ"],
              ["assign", "Giao xử lý"],
            ]
              .filter(([a]) => a !== "assign" || features.layer1)
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
          <label htmlFor="closure-check">
            Kết quả kiểm tra lại dùng để đóng việc
          </label>
          <select
            id="closure-check"
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
            Đóng việc sau kiểm tra lại
          </button>
          <p className="footnote">
            Đóng việc cần một lượt kiểm tra lại mới. Đọc phát hiện không tự đóng
            việc.
          </p>
        </section>
      )}
    </>
  );
}
