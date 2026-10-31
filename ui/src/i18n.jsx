import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import EN from "./i18n/en.js";

// Vietnamese source strings are the keys (gettext style): Vietnamese renders
// them as written, English looks them up and falls back to the source text.
// Placeholders such as {count} are filled from the values object.

export const LANGUAGES = [
  ["vi", "Tiếng Việt"],
  ["en", "English"],
];
const STORAGE_KEY = "lexcheck.language";

/** Marks a module-level string for translation without translating it. */
export const N_ = (text) => text;

/** `lang` for typed or API text: "vi" only when it has Vietnamese letters. */
export const languageOf = (text) =>
  /[\p{M}đĐ]/u.test(String(text ?? "").normalize("NFD")) ? "vi" : undefined;

export function translate(language, text, values) {
  if (typeof text !== "string") return text;
  const template = language === "en" ? (EN[text] ?? text) : text;
  if (!values) return template;
  return template.replace(/\{(\w+)\}/g, (match, name) =>
    name in values ? String(values[name]) : match,
  );
}

export function readLanguage() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "en" ? "en" : "vi";
  } catch {
    return "vi";
  }
}

function saveLanguage(language) {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Storage can be unavailable (private mode); the choice then lasts until reload.
  }
}

const LanguageContext = createContext({
  language: "vi",
  setLanguage: () => {},
  t: (text, values) => translate("vi", text, values),
});

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(readLanguage);
  useEffect(() => {
    document.documentElement.lang = language;
    document.title = translate(language, "LexCheck · Rà soát hồ sơ doanh nghiệp");
  }, [language]);
  const value = useMemo(
    () => ({
      language,
      setLanguage(next) {
        const chosen = next === "en" ? "en" : "vi";
        setLanguageState(chosen);
        saveLanguage(chosen);
      },
      t: (text, values) => translate(language, text, values),
    }),
    [language],
  );
  return (
    <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
export const useT = () => useContext(LanguageContext).t;
