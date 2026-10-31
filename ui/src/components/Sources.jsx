import React from "react";
import { Icon, Page, Badge, recordNames, ruleNames, date } from "./shared.jsx";
import { resultLabel, evidenceParts } from "../api.js";
export default function Sources({
  bundle,
  query,
  setQuery,
  inspect,
  versions,
  clause,
  request,
}) {
  return (
    <Page eyebrow="BỘ NHỚ CỦA DOANH NGHIỆP" title="Kho tri thức">
      <p className="page-description">
        Hồ sơ doanh nghiệp và điều khoản pháp luật, mỗi nguồn một phiên bản rõ
        ràng.
      </p>
      <div className="metrics">
        <div className="metric">
          <strong>{bundle.request.records.length}</strong>
          <small>Hồ sơ mẫu</small>
        </div>
        <div className="metric">
          <strong>{bundle.rules.length}</strong>
          <small>Rule trong pack</small>
        </div>
        <div className="metric">
          <strong>{bundle.rules.filter((r) => r.enabled).length}</strong>
          <small>Rule đã bật</small>
        </div>
      </div>
      <label htmlFor="docSearch">Tìm hồ sơ hoặc điều khoản</label>
      <input
        className="search full"
        id="docSearch"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Tên hồ sơ, mã phiên bản…"
      />
      <h2>Hồ sơ doanh nghiệp</h2>
      <div className="document-table">
        {bundle.request.records
          .filter((r) =>
            `${r.id} ${recordNames[r.kind]} ${r.title}`
              .toLocaleLowerCase("vi")
              .includes(query.toLocaleLowerCase("vi")),
          )
          .map((r) => (
            <button
              className="doc-row doc-button"
              key={r.id}
              onClick={() => inspect({ type: "record", value: r })}
            >
              <span className="doc-row-main">
                <span className="file-icon">
                  <Icon name="file" />
                </span>
                <span>
                  <b>{recordNames[r.kind]}</b>
                  <small>
                    {r.id} · {r.product_id} · v
                    {versions.find((v) => v.record_id === r.id)?.version}
                  </small>
                </span>
              </span>
              <Badge neutral>Dữ liệu tổng hợp</Badge>
            </button>
          ))}
      </div>
      <h2>Điều khoản & rule</h2>
      {bundle.rules
        .filter(
          (r) =>
            `${r.id} ${ruleNames[r.check_type]}`
              .toLowerCase()
              .includes(query.toLowerCase()) ||
            bundle.clauses
              .find((c) => c.id === r.clause_version_id)
              ?.document.toLowerCase()
              .includes(query.toLowerCase()),
        )
        .map((r) => (
          <button
            className="source-card full doc-button"
            key={r.id}
            onClick={() =>
              inspect({
                type: "clause",
                value: bundle.clauses.find((c) => c.id === r.clause_version_id),
              })
            }
          >
            <Icon name="file" />
            <span>
              <b>
                {r.id} · {ruleNames[r.check_type]}
              </b>
              <small>
                {r.clause_version_id} · v{r.version}
              </small>
            </span>
            <Badge>{r.enabled ? "Đang bật" : "Chờ kiểm chứng"}</Badge>
          </button>
        ))}
      <p className="footnote">
        Nhập PDF, OCR, Drive và phân quyền tài liệu chưa được triển khai trên
        backend.
      </p>
    </Page>
  );
}
