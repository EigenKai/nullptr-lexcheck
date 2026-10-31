import React from "react";
import { Icon, Page, Badge, recordNames, ruleNames, date } from "./shared.jsx";
import { resultLabel, evidenceParts } from "../api.js";
export default function Review({
  bundle,
  draft,
  setDraft,
  result,
  setResult,
  offline,
  busy,
  setSelected,
  panel,
  act,
  inspect,
  versions,
  check,
  updateText,
  request,
  features,
  session,
  revise,
  refreshHistory,
  showPreview,
}) {
  return (
    <Page
      eyebrow="TỪ HỒ SƠ ĐẾN PHÁT HIỆN CÓ CĂN CỨ"
      title="Rà soát hồ sơ"
      action={
        <button
          className="button"
          disabled={!!busy || offline}
          onClick={() =>
            act("Đang đối chiếu hồ sơ qua API…", async () => {
              const r = await request("/check", {
                method: "POST",
                body: JSON.stringify(draft),
              });
              setResult(r);
              setSelected(null);
              await refreshHistory();
            })
          }
        >
          <Icon name="check" />
          Chạy kiểm tra
        </button>
      }
    >
      <p className="page-description">
        Xác nhận bối cảnh và nội dung trước khi đối chiếu. Người duyệt quyết
        định từng phát hiện.
      </p>
      {!features.layer0_ready && (
        <button
          className="button secondary"
          disabled={!!busy}
          onClick={showPreview}
        >
          Xem finding minh hoạ (fixture)
        </button>
      )}
      <section className="result-section" aria-live="polite">
        <h2>Kết quả · {resultLabel(result)}</h2>
        {result ? (
          <>
            <div className="action-row">
              <Badge neutral>
                {result.mode === "fixture"
                  ? "Fixture · Xem trước"
                  : "Kết quả API"}
              </Badge>
              <Badge neutral>{result.rules_checked.length} rule đã chạy</Badge>
              <Badge>{result.skipped_rule_ids.length} rule chưa kiểm</Badge>
            </div>
            <p>
              {result.mode === "fixture"
                ? "Các rule đang chờ chủ sở hữu kiểm chứng nguồn. Đây là dữ liệu xem trước, chưa phải kết quả kiểm tra pháp lý."
                : result.summary}
            </p>
            {result.skipped_rule_ids.length > 0 && (
              <p>Chưa kiểm: {result.skipped_rule_ids.join(", ")}</p>
            )}
            {result.findings.map((f) => (
              <button
                className="review-card finding-button"
                key={f.id}
                onClick={() =>
                  inspect({
                    type: "finding",
                    value: f,
                    check: result,
                  })
                }
              >
                <Badge neutral={f.status === "needs_evidence"}>
                  {f.source === "llm" ? "Suggestion" : "Rule"} · {f.status}
                </Badge>
                <h3>
                  {f.rule_id} · {f.message}
                </h3>
                <p>
                  {f.record_version_id} · {f.clause_version_id}
                </p>
                <span>Xem bằng chứng & quyết định ↗</span>
              </button>
            ))}
          </>
        ) : (
          <p>
            Chạy kiểm tra để nhận kết quả từ API. Không có phát hiện hiển thị
            trước khi kiểm tra.
          </p>
        )}
      </section>
      <section className="form-panel">
        <h2>01 · Hồ sơ hoạt động</h2>
        <div className="form-grid">
          <label>
            Nhóm sản phẩm
            <select
              value={draft.profile.product_group}
              onChange={(e) => {
                setDraft({
                  ...draft,
                  profile: {
                    ...draft.profile,
                    product_group: e.target.value,
                  },
                });
                setResult(null);
              }}
            >
              <option value="tpbvsk">Thực phẩm bảo vệ sức khỏe</option>
              <option value="other">Nhóm khác</option>
              <option value="unknown">Chưa rõ</option>
            </select>
          </label>
          <label>
            Hoạt động
            <select
              value={draft.profile.activity}
              onChange={(e) => {
                setDraft({
                  ...draft,
                  profile: {
                    ...draft.profile,
                    activity: e.target.value,
                  },
                });
                setResult(null);
              }}
            >
              <option value="advertising">Quảng cáo</option>
              <option value="label_only">Chỉ có nhãn</option>
              <option value="unknown">Chưa rõ</option>
            </select>
          </label>
        </div>
        <label className="check-label">
          <input
            type="checkbox"
            checked={draft.profile.confirmed}
            onChange={(e) => {
              setDraft({
                ...draft,
                profile: {
                  ...draft.profile,
                  confirmed: e.target.checked,
                },
              });
              setResult(null);
            }}
          />
          Đã xác nhận bối cảnh công ty mẫu
        </label>
        <p className="footnote">
          Vai trò: nhà phân phối trong nước · Ngày rà soát {draft.review_date} ·
          LLM tắt
        </p>
      </section>
      <section className="form-panel">
        <h2>02 · Nội dung cần đối chiếu</h2>
        {draft.target_version_ids.map((id) => (
          <React.Fragment key={id}>
            <label className="text-field" key={id}>
              {id}
              <textarea
                value={draft.versions.find((v) => v.id === id).text}
                onChange={(e) => updateText(id, e.target.value)}
                rows="5"
              />
            </label>
            <label className="text-field">
              Công dụng đã ghi trong nội dung · {id}
              <textarea
                value={draft.versions.find((v) => v.id === id).uses.join("\n")}
                onChange={(e) => {
                  setDraft((prev) => ({
                    ...prev,
                    versions: prev.versions.map((v) =>
                      v.id === id
                        ? {
                            ...v,
                            uses: e.target.value.split("\n").filter(Boolean),
                          }
                        : v,
                    ),
                  }));
                  setResult(null);
                }}
                rows="2"
              />
            </label>
            <button
              className="button secondary"
              disabled={
                !!busy ||
                offline ||
                !features.layer0_ready ||
                session?.group !== "manager"
              }
              onClick={() => revise(id)}
            >
              Lưu phiên bản mới · {id}
            </button>
          </React.Fragment>
        ))}
        <p className="footnote">
          {features.layer0_ready
            ? "Khi chỉnh nội dung, lưu thành phiên bản mới trước; bản gốc và các quyết định cũ được giữ lại."
            : "API fixture chỉ nhận bộ mẫu gốc. Engine thật chưa sẵn sàng; thay đổi chưa được lưu."}
        </p>
        <button
          className="back-link"
          onClick={() => {
            setDraft(structuredClone(bundle.request));
            setResult(null);
            setSelected(null);
          }}
        >
          Khôi phục bộ mẫu gốc
        </button>
      </section>
    </Page>
  );
}
