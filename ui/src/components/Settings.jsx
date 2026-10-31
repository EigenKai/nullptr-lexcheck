import React from "react";
import { LANGUAGES, useLanguage } from "../i18n.jsx";
import { Page } from "./shared.jsx";

/** Display language and the data connection, moved out of the main screens. */
export default function Settings({ offline, features, busy, reload }) {
  const { t, language, setLanguage } = useLanguage();
  const connection = offline
    ? t("Mất kết nối · đang xem bản mẫu đi kèm")
    : features.layer0_ready
      ? t("Đã kết nối · live")
      : t("Đã kết nối · engine chưa sẵn sàng");
  return (
    <Page title={t("Cài đặt")}>
      <section className="settings-group" aria-labelledby="settings-language">
        <h2 id="settings-language">{t("Ngôn ngữ")}</h2>
        <div
          className="segmented"
          role="radiogroup"
          aria-labelledby="settings-language"
        >
          {LANGUAGES.map(([code, name]) => (
            <label
              key={code}
              className={`segment ${language === code ? "active" : ""}`}
            >
              <input
                type="radio"
                name="language"
                value={code}
                checked={language === code}
                onChange={() => setLanguage(code)}
              />
              <span lang={code}>{name}</span>
            </label>
          ))}
        </div>
        <p className="settings-hint">
          {t("Điều khoản và nội dung hồ sơ giữ nguyên văn gốc.")}
        </p>
      </section>
      <section className="settings-group" aria-labelledby="settings-data">
        <h2 id="settings-data">{t("Dữ liệu")}</h2>
        <dl className="settings-facts">
          <div>
            <dt>API</dt>
            <dd>{connection}</dd>
          </div>
          <div>
            <dt>{t("Nguồn")}</dt>
            <dd>{t("Dữ liệu tổng hợp (synthetic/staged)")}</dd>
          </div>
          <div>
            <dt>{t("Gói luật")}</dt>
            <dd>{t("Thực phẩm bảo vệ sức khỏe (TPBVSK)")}</dd>
          </div>
        </dl>
        <button
          className="button secondary"
          onClick={reload}
          disabled={!!busy}
        >
          {t("Tải lại dữ liệu")}
        </button>
      </section>
    </Page>
  );
}
