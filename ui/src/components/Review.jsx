import React from "react";
import { Icon, Page, Badge } from "./shared.jsx";
import { resultLabel } from "../api.js";
import { useT, N_ } from "../i18n.jsx";
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
  const t = useT();
  return (
    <Page
      eyebrow={t("TỪ HỒ SƠ ĐẾN PHÁT HIỆN CÓ CĂN CỨ")}
      title={t("Rà soát hồ sơ")}
      action={
        <button
          className="button"
          disabled={!!busy || offline}
          onClick={() =>
            act(N_("Đang đối chiếu hồ sơ qua API…"), async () => {
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
          {t("Chạy kiểm tra")}
        </button>
      }
    >
      <div className="review-desk">
        <div className="review-desk-copy">
          <p className="page-description">
            {t("Xác nhận hồ sơ trước khi kiểm tra. Người duyệt quyết định.")}
          </p>
          {!features.layer0_ready && (
            <button
              className="button secondary"
              disabled={!!busy}
              onClick={showPreview}
            >
              {t("Xem finding minh hoạ (fixture)")}
            </button>
          )}
        </div>
        <img
          className="review-desk-lex"
          src="/assets/lex-hero-480.webp"
          alt=""
          width="168"
          height="168"
        />
      </div>
      <section className="result-section" aria-live="polite">
        <h2>{t("Kết quả · {label}", { label: resultLabel(result, t) })}</h2>
        {result ? (
          <>
            <div className="action-row">
              <Badge neutral>
                {result.mode === "fixture"
                  ? t("Fixture · Xem trước")
                  : t("Kết quả API")}
              </Badge>
              <Badge neutral>
                {t("{count} rule đã chạy", {
                  count: result.rules_checked.length,
                })}
              </Badge>
              <Badge>
                {t("{count} rule chưa kiểm", {
                  count: result.skipped_rule_ids.length,
                })}
              </Badge>
            </div>
            <p>
              {result.mode === "fixture"
                ? t("Dữ liệu xem trước, chưa phải kết quả kiểm tra pháp lý.")
                : result.summary}
            </p>
            {result.skipped_rule_ids.length > 0 && (
              <p>
                {t("Chưa kiểm: {ids}", {
                  ids: result.skipped_rule_ids.join(", "),
                })}
              </p>
            )}
            {result.findings.map((f) => (
              <button
                className="review-card finding-button"
                data-status={f.status}
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
                <h3 lang="vi">
                  {f.rule_id} · {f.message}
                </h3>
                <p>
                  {f.record_version_id} · {f.clause_version_id}
                </p>
                <span>{t("Xem bằng chứng & quyết định ↗")}</span>
              </button>
            ))}
          </>
        ) : (
          <p>{t("Chạy kiểm tra để xem kết quả.")}</p>
        )}
      </section>
      <section className="form-panel">
        <h2>{t("01 · Hồ sơ hoạt động")}</h2>
        <div className="form-grid">
          <label>
            {t("Nhóm sản phẩm")}
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
              <option value="tpbvsk">{t("Thực phẩm bảo vệ sức khỏe")}</option>
              <option value="other">{t("Nhóm khác")}</option>
              <option value="unknown">{t("Chưa rõ")}</option>
            </select>
          </label>
          <label>
            {t("Hoạt động")}
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
              <option value="advertising">{t("Quảng cáo")}</option>
              <option value="label_only">{t("Chỉ có nhãn")}</option>
              <option value="unknown">{t("Chưa rõ")}</option>
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
          {t("Đã xác nhận bối cảnh công ty mẫu")}
        </label>
        <p className="footnote">
          {t(
            "Vai trò: nhà phân phối trong nước · Ngày rà soát {date} · LLM tắt",
            { date: draft.review_date },
          )}
        </p>
      </section>
      <section className="form-panel">
        <h2>{t("02 · Nội dung cần đối chiếu")}</h2>
        {draft.target_version_ids.map((id) => (
          <React.Fragment key={id}>
            <label className="text-field" key={id}>
              {id}
              <textarea
                lang="vi"
                value={draft.versions.find((v) => v.id === id).text}
                onChange={(e) => updateText(id, e.target.value)}
                rows="5"
              />
            </label>
            <label className="text-field">
              {t("Công dụng đã ghi · {id}", { id })}
              <textarea
                lang="vi"
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
              {t("Lưu phiên bản mới · {id}", { id })}
            </button>
          </React.Fragment>
        ))}
        <p className="footnote">
          {features.layer0_ready
            ? t("Lưu thành phiên bản mới; bản gốc và quyết định cũ được giữ.")
            : t("Fixture chỉ nhận bộ mẫu gốc; thay đổi chưa được lưu.")}
        </p>
        <button
          className="back-link"
          onClick={() => {
            setDraft(structuredClone(bundle.request));
            setResult(null);
            setSelected(null);
          }}
        >
          {t("Khôi phục bộ mẫu gốc")}
        </button>
      </section>
    </Page>
  );
}
