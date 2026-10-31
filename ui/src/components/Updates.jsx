import React from "react";
import { Icon, Page, Badge, recordNames, ruleNames, date } from "./shared.jsx";
import { resultLabel, evidenceParts } from "../api.js";
import { useT, N_ } from "../i18n.jsx";
import LawChanges from "./LawChanges.jsx";
export default function Updates({
  bundle,
  setDraft,
  setResult,
  setNotice,
  history,
  offline,
  busy,
  oldNew,
  setOldNew,
  go,
  act,
  versions,
  request,
  features,
  session,
  refreshHistory,
}) {
  const t = useT();
  return (
    <Page eyebrow={t("THAY ĐỔI · KIỂM TRA LẠI")} title={t("Cập nhật nguồn")}>
      <p className="page-description">
        {t("Xem thay đổi và hồ sơ cần kiểm tra lại.")}
      </p>
      <div className="source-card">
        <Icon name="refresh" />
        <span>
          <b>{t("Nguồn pháp luật chính thức")}</b>
          <small>{t("Chưa có lần kiểm tra thành công")}</small>
        </span>
        <Badge>{t("Chưa kết nối")}</Badge>
      </div>
      {bundle.event && (
        <article className="review-card">
          <Badge neutral>{t("Sự kiện dựng sẵn · Chưa áp dụng")}</Badge>
          <h2>{t("Hồ sơ công bố có phiên bản mới")}</h2>
          <p>
            {bundle.event.previous_version_id} → {bundle.event.new_version.id}
          </p>
          <button
            className="button secondary"
            onClick={() => setOldNew(!oldNew)}
            aria-expanded={oldNew}
          >
            {t("Xem bản cũ / mới")}
          </button>
          {oldNew && (
            <div className="diff-grid">
              <section>
                <h3>{t("Bản cũ · v1")}</h3>
                <p className="record-text" lang="vi">
                  {
                    versions.find(
                      (v) => v.id === bundle.event.previous_version_id,
                    )?.text
                  }
                </p>
              </section>
              <section>
                <h3>{t("Bản mới · v2")}</h3>
                <p className="record-text" lang="vi">
                  {bundle.event.new_version.text}
                </p>
              </section>
            </div>
          )}
          <p className="footnote">
            {t("Bỏ công dụng:")} <span lang="vi">Hỗ trợ giảm cholesterol.</span>
          </p>
          <p className="footnote">
            {t("API quyết định phạm vi ảnh hưởng, không phải UI.")}
          </p>
          <button
            className="button"
            disabled={!!busy || offline}
            onClick={() =>
              act(N_("Đang gửi sự kiện…"), async () => {
                await request("/changes", {
                  method: "POST",
                  body: JSON.stringify(bundle.event),
                });
                await refreshHistory();
                setNotice(N_("API đã ghi nhận thay đổi."));
              })
            }
          >
            {t("Gửi sự kiện mẫu tới API")}
          </button>
        </article>
      )}
      <h2>{t("Hàng đợi kiểm tra lại")}</h2>
      {features.layer2 && (
        <LawChanges
          history={history}
          request={request}
          act={act}
          refreshHistory={refreshHistory}
          session={session}
          busy={busy}
        />
      )}
      {history?.queue.length ? (
        history.queue.map((q) => (
          <article className="review-card" key={q.id}>
            <Badge neutral>{q.status}</Badge>
            <h3>{q.target_version_id}</h3>
            <p>
              <span lang="vi">{q.reason}</span> · {t("Kết quả gốc")}{" "}
              {q.previous_check_id}
            </p>
            <button
              className="button secondary"
              disabled={
                !!busy ||
                offline ||
                q.status !== "queued" ||
                session?.group !== "manager"
              }
              onClick={() =>
                act(N_("Đang kiểm tra lại…"), async () => {
                  const r = await request("/rechecks", {
                    method: "POST",
                    body: JSON.stringify({
                      item_id: q.id,
                      llm_mode: "off",
                    }),
                  });
                  setResult(r);
                  setDraft(structuredClone(r.snapshot));
                  await refreshHistory();
                  go("reviews");
                })
              }
            >
              {t("Kiểm tra lại")}
            </button>
          </article>
        ))
      ) : (
        <p className="empty-state">
          {offline
            ? t("Không lấy được hàng đợi: API mất kết nối.")
            : t("Chưa có hồ sơ trong hàng đợi.")}
        </p>
      )}
    </Page>
  );
}
