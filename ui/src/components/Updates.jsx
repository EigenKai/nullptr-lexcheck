import React from "react";
import { Icon, Page, Badge, recordNames, ruleNames, date } from "./shared.jsx";
import { resultLabel, evidenceParts } from "../api.js";
import LawChanges from "./LawChanges.jsx";
import ChangeImpact from "./ChangeImpact.jsx";
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
  return (
    <Page
      eyebrow="THAY ĐỔI MỘT NGUỒN · KIỂM TRA LẠI PHỤ THUỘC"
      title="Cập nhật nguồn"
    >
      <p className="page-description">
        Giữ bản cũ, xem nội dung đổi và hàng đợi hồ sơ cần rà soát lại.
      </p>
      <div className="source-card">
        <Icon name="refresh" />
        <span>
          <b>Nguồn pháp luật chính thức</b>
          <small>Chưa kết nối watcher · Chưa có lần kiểm tra thành công</small>
        </span>
        <Badge>Chưa kết nối</Badge>
      </div>
      {bundle.event && (
        <article className="review-card">
          <Badge neutral>Sự kiện hồ sơ dựng sẵn · Chưa áp dụng</Badge>
          <h2>Hồ sơ công bố có phiên bản mới</h2>
          <p>
            {bundle.event.previous_version_id} → {bundle.event.new_version.id}
          </p>
          <button
            className="button secondary"
            onClick={() => setOldNew(!oldNew)}
            aria-expanded={oldNew}
          >
            Xem bản cũ / mới
          </button>
          {oldNew && (
            <div className="diff-grid">
              <section>
                <h3>Bản cũ · v1</h3>
                <p className="record-text">
                  {
                    versions.find(
                      (v) => v.id === bundle.event.previous_version_id,
                    )?.text
                  }
                </p>
              </section>
              <section>
                <h3>Bản mới · v2</h3>
                <p className="record-text">{bundle.event.new_version.text}</p>
              </section>
            </div>
          )}
          <p className="footnote">
            Công dụng được bỏ: Hỗ trợ giảm cholesterol. API quyết định phạm vi
            ảnh hưởng; UI không tự tạo hàng đợi.
          </p>
          <button
            className="button"
            disabled={!!busy || offline}
            onClick={() =>
              act("Đang gửi sự kiện và lấy hàng đợi…", async () => {
                await request("/changes", {
                  method: "POST",
                  body: JSON.stringify(bundle.event),
                });
                await refreshHistory();
                setNotice("API đã ghi nhận thay đổi.");
              })
            }
          >
            Gửi sự kiện mẫu tới API
          </button>
        </article>
      )}
      <h2>Hàng đợi kiểm tra lại</h2>
      {features.task_dashboard && <ChangeImpact history={history} />}
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
              {q.reason} · Kết quả gốc {q.previous_check_id}
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
                act("Đang kiểm tra lại hồ sơ phụ thuộc…", async () => {
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
              Kiểm tra lại
            </button>
          </article>
        ))
      ) : (
        <p className="empty-state">
          {offline
            ? "Không lấy được hàng đợi khi API mất kết nối."
            : "API chưa có hồ sơ trong hàng đợi."}
        </p>
      )}
    </Page>
  );
}
