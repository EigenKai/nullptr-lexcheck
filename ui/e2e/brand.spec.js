import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

// Brand and readability checks for the reviewer screens shown during the demo.
const demo = JSON.parse(
  fs.readFileSync(
    new URL("../../data/fixtures/demo.json", import.meta.url),
    "utf8",
  ),
);
const SHOT_DIR = process.env.UI_SHOT_DIR;
const VIEWPORTS = [
  [1440, 900],
  [1280, 720],
  [375, 812],
];

// Same synthetic finding as review.spec.js: the fixture backend returns none.
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
      message: "Phát hiện dựng cho kiểm thử UI",
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

test.beforeEach(async ({ page }) => {
  await page.route("**/api/check", (route) =>
    route.fulfill({ json: findingResult() }),
  );
});

// A hash-only goto keeps React state, so load a blank page first.
async function openApp(page, hash = "") {
  await page.goto("about:blank");
  await page.goto(`/${hash ? `#${hash}` : ""}`);
  await expect(page.locator(".status-strip")).toContainText("API kết nối");
  await page.evaluate(() => document.fonts.ready);
}

async function openFinding(page) {
  await openApp(page, "reviews");
  await page
    .getByRole("button", { name: "Chạy kiểm tra", exact: true })
    .click();
  await page.locator(".finding-button").first().click();
  await expect(page.locator(".evidence mark")).toBeVisible();
}

const SCREENS = [
  ["review", (page) => openFinding(page)],
  ["chat", (page) => openApp(page, "chat")],
  ["history", (page) => openApp(page, "history")],
  ["knowledge", (page) => openApp(page, "knowledge")],
];

async function shoot(page, name) {
  if (!SHOT_DIR) return;
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  await page.screenshot({
    path: path.join(SHOT_DIR, `${name}.png`),
    fullPage: true,
  });
}

test("9 · no horizontal overflow on any demo screen", async ({ page }) => {
  test.setTimeout(120_000);
  for (const [width, height] of VIEWPORTS) {
    await page.setViewportSize({ width, height });
    for (const [name, open] of SCREENS) {
      await open(page);
      const overflow = await page.evaluate(() =>
        [...document.querySelectorAll("body *")]
          .filter((e) => e.getBoundingClientRect().right > innerWidth + 1)
          .slice(0, 5)
          .map((e) => `${e.tagName}.${e.className}`),
      );
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        JSON.stringify({ name, width, overflow }),
      ).toBeTruthy();
      await shoot(page, `${name}-${width}x${height}`);
    }
  }
});

test("1 · the sidebar brand mark is a small Lex image", async ({ page }) => {
  await openApp(page);
  const mark = page.locator(".sidebar img[alt*='Lex']").first();
  await expect(mark).toBeVisible();
  const { src, natural } = await mark.evaluate((img) => ({
    src: new URL(img.currentSrc || img.src).pathname,
    natural: img.naturalWidth,
  }));
  expect(natural).toBeGreaterThan(0);
  expect(src).not.toBe("/assets/mascot.png");
  const body = await (await page.request.get(src)).body();
  expect(body.length).toBeLessThanOrEqual(60 * 1024);
});

test("2 · no image on the review or chat screen exceeds 250 KB", async ({
  page,
}) => {
  const images = new Set();
  page.on("request", (request) => {
    if (request.resourceType() === "image") images.add(request.url());
  });
  await openFinding(page);
  await openApp(page, "chat");
  await expect(page.locator(".hero img")).toBeVisible();
  await page.evaluate(() =>
    Promise.all([...document.images].map((img) => img.decode().catch(() => {}))),
  );
  expect(images.size).toBeGreaterThan(0);
  // Bodies of responses from earlier pages are gone, so fetch each URL again.
  for (const url of images) {
    if (url.startsWith("data:")) continue;
    const size = (await (await page.request.get(url)).body()).length;
    expect(size, url).toBeLessThanOrEqual(250 * 1024);
  }
});

test("3 · favicon, theme colour and brand tokens come from the mascot", async ({
  page,
}) => {
  await openApp(page);
  const href = await page.locator("link[rel=icon]").getAttribute("href");
  const icon = await page.request.get(href);
  expect(icon.status()).toBe(200);
  expect(icon.headers()["content-type"]).toMatch(/^image\//);
  const tokens = await page.evaluate(() => {
    const style = getComputedStyle(document.documentElement);
    return Object.fromEntries(
      ["scale", "ink", "cream", "gold", "navy", "mint"].map((name) => [
        name,
        style.getPropertyValue(`--brand-${name}`).trim().toLowerCase(),
      ]),
    );
  });
  for (const value of Object.values(tokens)) expect(value).toMatch(/^#[0-9a-f]{6}$/);
  const theme = await page
    .locator("meta[name=theme-color]")
    .getAttribute("content");
  expect(theme.trim().toLowerCase()).toBe(tokens.scale);
});

async function tabTo(page, locator) {
  for (let i = 0; i < 60; i++) {
    await page.keyboard.press("Tab");
    if (await locator.evaluate((e) => e === document.activeElement)) return;
  }
  throw new Error("element never received keyboard focus");
}

test("6 · keyboard focus is clearly visible", async ({ page }) => {
  await openApp(page, "reviews");
  const targets = [
    page.locator("nav .nav-item", { hasText: "Kho tri thức" }),
    page.getByRole("button", { name: "Chạy kiểm tra", exact: true }),
  ];
  for (const target of targets) {
    await tabTo(page, target);
    const ring = await target.evaluate((e) => {
      const s = getComputedStyle(e);
      return {
        style: s.outlineStyle,
        width: parseFloat(s.outlineWidth),
        shadow: s.boxShadow,
      };
    });
    const outlined = ring.style !== "none" && ring.width >= 2;
    expect(outlined || ring.shadow !== "none", JSON.stringify(ring)).toBe(
      true,
    );
  }
});

test("8 · fonts carry Vietnamese glyphs", async ({ page }) => {
  await openApp(page);
  const text = "Rà soát hồ sơ ữ ặ ẫ ỡ";
  const families = [
    ["Nunito Sans Variable", text, true],
    ["Source Serif 4 Variable", text, true],
    ["JetBrains Mono Variable", "R-01", false],
  ];
  for (const [family, sample, vietnamese] of families) {
    const result = await page.evaluate(
      async ([family, sample]) => {
        await document.fonts.load(`20px "${family}"`, sample);
        const faces = [...document.fonts].filter(
          (f) => f.family.replace(/"/g, "") === family && f.status === "loaded",
        );
        return {
          check: document.fonts.check(`20px "${family}"`, sample),
          loaded: faces.length,
          vietnamese: faces.some((f) => /1EA0/i.test(f.unicodeRange)),
        };
      },
      [family, sample],
    );
    expect(result.loaded, family).toBeGreaterThan(0);
    expect(result.check, family).toBe(true);
    if (vietnamese) expect(result.vietnamese, family).toBe(true);
  }
});

test("10 · the data-mode status stays visible at every width", async ({
  page,
}) => {
  for (const [width, height] of VIEWPORTS) {
    await page.setViewportSize({ width, height });
    await openApp(page);
    const strip = page.locator(".status-strip");
    await expect(strip).toBeVisible();
    await expect(strip).toContainText(/live|fixture/);
    const box = await strip.boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(width + 1);
  }
});
