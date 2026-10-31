import { test, expect } from "@playwright/test";
import fs from "node:fs";

// Settings page and the English interface. Source material (legal clauses,
// record text, quotes) stays Vietnamese and is marked with lang="vi".
const demo = JSON.parse(
  fs.readFileSync(
    new URL("../../data/fixtures/demo.json", import.meta.url),
    "utf8",
  ),
);

// Letters that occur in Vietnamese but never in English text.
const VIETNAMESE =
  "[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]";

// A synthetic finding, as in review.spec.js; engine messages are English.
function findingResult() {
  const result = structuredClone(demo.preview);
  const text = result.snapshot.versions.find((v) => v.id === "RV-02-v1").text;
  result.findings = [
    {
      id: "F-UI",
      rule_id: "R-02",
      rule_version: 1,
      clause_version_id: "CV-02-v1",
      record_version_id: "RV-02-v1",
      status: "suggestion",
      source: "llm",
      severity: "medium",
      message: "Synthetic finding for the interface test",
      clause_quote: demo.clauses[1].text,
      evidence: [
        {
          kind: "span",
          record_version_id: "RV-02-v1",
          start: 0,
          end: 16,
          quote: text.slice(0, 16),
        },
      ],
    },
  ];
  return result;
}

async function open(page, hash) {
  await page.goto("about:blank");
  await page.goto(`/#${hash}`);
  if (hash === "chat") await expect(page.locator(".hero")).toBeVisible();
  else await expect(page.locator("main h1.page-title")).toBeVisible();
  await expect(page.locator("main h1.page-title, .hero").first()).not.toHaveText(
    /Kết nối hồ sơ|Connecting records/,
  );
}

// Visible Vietnamese text (and labels users meet) outside [lang="vi"].
function vietnameseOutsideSource(page) {
  return page.evaluate((letters) => {
    const pattern = new RegExp(letters, "i");
    const leaks = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const parent = node.parentElement;
      if (!parent || !pattern.test(node.textContent)) continue;
      if (parent.closest('[lang="vi"]')) continue;
      const option = parent.closest("option");
      if (!option && !parent.getClientRects().length) continue;
      leaks.push(node.textContent.trim().slice(0, 90));
    }
    for (const el of document.querySelectorAll("[aria-label],[placeholder],[title]")) {
      if (el.closest('[lang="vi"]')) continue;
      for (const name of ["aria-label", "placeholder", "title"]) {
        const value = el.getAttribute(name);
        if (value && pattern.test(value)) leaks.push(`${name}: ${value}`);
      }
    }
    return leaks;
  }, VIETNAMESE);
}

test("settings switches the interface language and remembers it", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Rà soát hồ sơ", exact: true }),
  ).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "vi");
  await page.getByRole("button", { name: "Cài đặt", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Cài đặt", exact: true }),
  ).toBeVisible();

  await page.getByRole("radio", { name: "English" }).check();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(
    page.getByRole("heading", { name: "Settings", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Record review", exact: true }),
  ).toBeVisible();
  await expect(page).toHaveTitle("LexCheck · Company record review");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("radio", { name: "English" })).toBeChecked();

  await page.getByRole("radio", { name: "Tiếng Việt" }).check();
  await expect(
    page.getByRole("heading", { name: "Cài đặt", exact: true }),
  ).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "vi");
});

test("the healthy shell shows no workspace card and no status strip", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Rà soát hồ sơ", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("NULLPTR Demo")).toHaveCount(0);
  await expect(page.locator(".workspace")).toHaveCount(0);
  await expect(page.locator(".status-strip")).toHaveCount(0);
});

test("English mode leaves only source material in Vietnamese", async ({
  page,
}) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() =>
    window.localStorage.setItem("lexcheck.language", "en"),
  );
  await page.route("**/api/check", (route) =>
    route.fulfill({ json: findingResult() }),
  );
  const leaks = {};
  for (const hash of ["chat", "knowledge", "updates", "history", "settings"]) {
    await open(page, hash);
    leaks[hash] = await vietnameseOutsideSource(page);
  }
  await open(page, "reviews");
  leaks.reviews = await vietnameseOutsideSource(page);
  await page.locator(".page-title-row .button").first().click();
  await page.locator(".finding-button").first().click();
  await expect(page.locator(".evidence mark").first()).toBeVisible();
  leaks.finding = await vietnameseOutsideSource(page);
  for (const [screen, found] of Object.entries(leaks))
    expect(found, `${screen} has untranslated text`).toEqual([]);
});
