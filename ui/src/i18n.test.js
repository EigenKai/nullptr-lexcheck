import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import EN from "./i18n/en.js";
import { translate } from "./i18n.jsx";

const SRC = fileURLToPath(new URL(".", import.meta.url));
// First argument of t("…") and N_("…") calls: the Vietnamese catalogue keys.
const CALL =
  /(?<![\w.$])(?:t|N_)\(\s*(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)'|`((?:\\.|[^`\\])*)`)/g;

function sourceFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((item) => {
    const name = path.join(dir, item.name);
    if (item.isDirectory()) return sourceFiles(name);
    return /\.(js|jsx)$/.test(name) && !name.includes(".test.") ? [name] : [];
  });
}

function keysIn(file) {
  const text = fs.readFileSync(file, "utf8");
  return [...text.matchAll(CALL)].map(([, double, single, template]) => {
    if (double !== undefined) return JSON.parse(`"${double}"`);
    if (single !== undefined) return single.replace(/\\'/g, "'");
    return template;
  });
}

const placeholders = (text) =>
  [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe("English catalogue", () => {
  it("covers every string passed to t() or N_()", () => {
    const missing = sourceFiles(SRC).flatMap((file) =>
      keysIn(file)
        .filter((key) => !(key in EN))
        .map((key) => `${path.relative(SRC, file)}: ${key}`),
    );
    expect(missing).toEqual([]);
  });

  it("uses placeholders instead of template interpolation in keys", () => {
    const interpolated = sourceFiles(SRC).flatMap((file) =>
      keysIn(file).filter((key) => key.includes("${")),
    );
    expect(interpolated).toEqual([]);
  });

  it("keeps the same placeholders in every translation", () => {
    for (const [key, value] of Object.entries(EN))
      expect(placeholders(value), key).toEqual(placeholders(key));
  });
});

describe("translate", () => {
  it("renders Vietnamese as written and fills placeholders", () => {
    expect(translate("vi", "{count} mục cần xem xét", { count: 2 })).toBe(
      "2 mục cần xem xét",
    );
  });

  it("looks up English and falls back to the source text", () => {
    expect(translate("en", "Cài đặt")).toBe("Settings");
    expect(translate("en", "{count} mục cần xem xét", { count: 1 })).toBe(
      "To review: 1",
    );
    expect(translate("en", "Chuỗi chưa có trong danh mục")).toBe(
      "Chuỗi chưa có trong danh mục",
    );
  });
});
