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

const TITLES = {
  reviews: "Rà soát hồ sơ",
  history: "Lịch sử quyết định",
  knowledge: "Kho tri thức",
  settings: "Cài đặt",
};

// A hash-only goto keeps React state, so load a blank page first, then wait
// for the screen's own title so measurements never see the loading state.
async function openApp(page, hash = "") {
  await page.goto("about:blank");
  await page.goto(`/${hash ? `#${hash}` : ""}`);
  if (hash === "chat") await expect(page.locator(".hero")).toBeVisible();
  else
    await expect(page.locator("main h1.page-title")).toHaveText(
      TITLES[hash || "reviews"],
    );
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
  ["settings", (page) => openApp(page, "settings")],
];

async function shoot(page, name) {
  if (!SHOT_DIR) return;
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  // Fixed elements drift in full-page captures of a scrolled window.
  await page.evaluate(() => window.scrollTo(0, 0));
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
    // Buttons already carry a resting box-shadow, so require a real outline.
    const ring = await target.evaluate((e) => {
      const s = getComputedStyle(e);
      return { style: s.outlineStyle, width: parseFloat(s.outlineWidth) };
    });
    expect(ring.style, JSON.stringify(ring)).not.toBe("none");
    expect(ring.width, JSON.stringify(ring)).toBeGreaterThanOrEqual(2);
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

test("10 · the status strip appears only when the API is unreachable", async ({
  page,
}) => {
  for (const [width, height] of VIEWPORTS) {
    await page.setViewportSize({ width, height });
    await openApp(page);
    await expect(page.locator(".status-strip")).toHaveCount(0);
  }
  await page.route("**/api/**", (route) => route.abort());
  for (const [width, height] of VIEWPORTS) {
    await page.setViewportSize({ width, height });
    await page.goto("about:blank");
    await page.goto("/");
    const strip = page.locator(".status-strip");
    await expect(strip).toContainText("API mất kết nối");
    const box = await strip.boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(width + 1);
  }
});

test("4 · reading sizes hold up on a projector", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await openFinding(page);
  const size = (selector) =>
    page
      .locator(selector)
      .first()
      .evaluate((e) => parseFloat(getComputedStyle(e).fontSize));
  expect(await size("body")).toBeGreaterThanOrEqual(16);
  for (const selector of [
    ".finding-button h3",
    ".evidence .record-text",
    ".clause blockquote",
  ])
    expect(await size(selector), selector).toBeGreaterThanOrEqual(20);
});

test("5 · text meets WCAG AA contrast on solid backgrounds", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  for (const [name, open] of SCREENS) {
  await open(page);
  const failures = await page.evaluate(() => {
    const parse = (value) => {
      const m = value.match(/rgba?\(([^)]+)\)/);
      if (!m) return null;
      const [r, g, b, a = 1] = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
      return { r, g, b, a };
    };
    const over = (top, below) => ({
      r: top.r * top.a + below.r * (1 - top.a),
      g: top.g * top.a + below.g * (1 - top.a),
      b: top.b * top.a + below.b * (1 - top.a),
      a: 1,
    });
    // Composite background colours from the nearest opaque ancestor upward.
    const backdrop = (el) => {
      const layers = [];
      for (let e = el; e; e = e.parentElement) {
        const c = parse(getComputedStyle(e).backgroundColor);
        if (c && c.a > 0) layers.push(c);
        if (c && c.a >= 1) break;
      }
      let base = { r: 255, g: 255, b: 255, a: 1 };
      for (const layer of layers.reverse()) base = over(layer, base);
      return base;
    };
    const opacity = (el) => {
      let o = 1;
      for (let e = el; e; e = e.parentElement)
        o *= parseFloat(getComputedStyle(e).opacity);
      return o;
    };
    const lum = ({ r, g, b }) => {
      const f = (v) => {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const ownText = (e) =>
      [...e.childNodes].some(
        (n) => n.nodeType === Node.TEXT_NODE && n.textContent.trim(),
      );
    const roots = [
      "body",
      ".status-strip",
      ".page-description",
      ".badge",
      ".button",
      "mark",
      ".footnote",
    ].flatMap((s) => [...document.querySelectorAll(s)]);
    const checked = new Set();
    const out = [];
    for (const root of roots)
      for (const el of [root, ...root.querySelectorAll("*")]) {
        if (checked.has(el) || !ownText(el) || !el.getClientRects().length)
          continue;
        checked.add(el);
        const style = getComputedStyle(el);
        const bg = backdrop(el);
        const fg = parse(style.color);
        const text = over({ ...fg, a: fg.a * opacity(el) }, bg);
        const [hi, lo] = [lum(text), lum(bg)].sort((a, b) => b - a);
        const ratio = (hi + 0.05) / (lo + 0.05);
        const px = parseFloat(style.fontSize);
        const large = px >= 24 || (px >= 18.66 && Number(style.fontWeight) >= 700);
        if (ratio < (large ? 3 : 4.5))
          out.push(
            `${el.tagName}.${el.className} "${el.textContent.trim().slice(0, 30)}" ${ratio.toFixed(2)}`,
          );
      }
    return { out, count: checked.size };
  });
  expect(failures.count, name).toBeGreaterThan(10);
  expect(failures.out, name).toEqual([]);
  }
});

test("7 · reduced motion switches animation off; motion stays short", async ({
  page,
}) => {
  // playwright.config.js emulates reducedMotion: "reduce" for every test.
  await openFinding(page);
  const motion = () =>
    page.evaluate(() =>
      [...document.querySelectorAll("*")].flatMap((e) =>
        [null, "::before", "::after"].map((pseudo) => {
          const s = getComputedStyle(e, pseudo);
          const longest = (list) =>
            Math.max(...list.split(",").map((d) => parseFloat(d) || 0));
          return {
            name: `${e.tagName}.${e.className}${pseudo || ""}`,
            loader: !!e.closest(".loading-dots"),
            animation: s.animationName !== "none" ? longest(s.animationDuration) : 0,
            transition: longest(s.transitionDuration),
            properties: s.transitionProperty,
          };
        }),
      ),
    );
  const reduced = await motion();
  expect(reduced.filter((m) => m.animation > 0 || m.transition > 0)).toEqual(
    [],
  );
  expect(
    await page
      .locator(".evidence")
      .evaluate((e) => getComputedStyle(e).transitionDuration),
  ).toBe("0s");
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const full = await motion();
  expect(
    full.filter((m) => !m.loader && (m.animation > 0.25 || m.transition > 0.25)),
  ).toEqual([]);
  const ours = full.filter((m) =>
    /\b(button|nav-item|finding-button)\b/.test(m.name) && m.transition > 0,
  );
  expect(ours.length).toBeGreaterThan(0);
  for (const m of ours)
    expect(m.properties, m.name).toMatch(/^(transform|opacity)(, (transform|opacity))*$/);
});
