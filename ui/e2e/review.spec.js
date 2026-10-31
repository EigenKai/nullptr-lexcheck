import { test, expect } from "@playwright/test";
import fs from "node:fs";
const demo = JSON.parse(
  fs.readFileSync(new URL("../public/demo.json", import.meta.url), "utf8"),
);

test("connected review, source versions, unavailable write, and responsive Vietnamese font", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator(".status-strip")).toContainText("API kết nối");
  await expect(page.locator(".mascot")).toBeVisible();
  await page
    .getByRole("button", { name: "Rà soát hồ sơ", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Chạy kiểm tra", exact: true })
    .click();
  await expect(page.locator(".result-section")).toContainText(
    "Chưa đủ thông tin",
  );
  await expect(page.locator(".result-section")).toContainText("0 rule đã chạy");
  await page
    .getByRole("button", { name: "Cập nhật nguồn", exact: true })
    .click();
  await page.getByRole("button", { name: "Xem bản cũ / mới" }).click();
  await expect(page.locator(".diff-grid")).toContainText(
    "Hỗ trợ giảm cholesterol.",
  );
  await page.getByRole("button", { name: "Gửi sự kiện mẫu tới API" }).click();
  await expect(page.getByRole("alert")).toContainText("chưa sẵn sàng");
  await page
    .getByRole("button", { name: "Lịch sử quyết định", exact: true })
    .click();
  await expect(page.locator("main")).toContainText("CHK-preview");
  for (const [width, height] of [
    [1280, 720],
    [768, 1024],
    [375, 812],
  ]) {
    await page.setViewportSize({ width, height });
    if (width <= 800)
      await page.getByRole("button", { name: "Mở menu", exact: true }).click();
    await page.getByRole("button", { name: "Cuộc trò chuyện mới" }).click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: `test-results/home-${width}.png`,
      fullPage: true,
    });
    const overflow = await page.evaluate(() =>
      [...document.querySelectorAll("body *")]
        .filter((e) => e.getBoundingClientRect().right > innerWidth + 1)
        .map((e) => [
          e.tagName,
          e.className,
          Math.round(e.getBoundingClientRect().right),
        ]),
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      JSON.stringify({ width, overflow }),
    ).toBeTruthy();
    expect(
      await page
        .locator(".hero h1")
        .evaluate((e) => getComputedStyle(e).fontFamily),
    ).toContain("Nunito Sans");
    await page.screenshot({
      path: `test-results/home-${width}.png`,
      fullPage: true,
    });
  }
  expect(errors).toEqual([]);
});

test("offline fallback is labelled and disables writes", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");
  await expect(page.locator(".status-strip")).toContainText("API mất kết nối");
  await page
    .getByRole("button", { name: "Rà soát hồ sơ", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Chạy kiểm tra", exact: true }),
  ).toBeDisabled();
});

test("finding traces and reviewer actions use the API contract", async ({
  page,
}) => {
  // Synthetic UI-only response exercises a path the current fixture backend cannot produce.
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
  await page.route("**/api/check", (route) => route.fulfill({ json: result }));
  await page.goto("/");
  await page
    .getByRole("button", { name: "Rà soát hồ sơ", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Chạy kiểm tra", exact: true })
    .click();
  await page.locator(".finding-button").click();
  await expect(page.locator("mark")).toHaveText("Hỗ trợ tiêu hóa.");
  await expect(page.locator(".evidence")).toContainText("Suggestion");
  await page.getByLabel("Ghi chú xử lý").fill("Cần đối chiếu hồ sơ gốc.");
  const outgoing = page.waitForRequest("**/api/decisions");
  await page.getByRole("button", { name: "Giao xử lý", exact: true }).click();
  expect((await outgoing).postDataJSON()).toMatchObject({
    check_id: result.id,
    finding_id: "F-UI",
    action: "assign",
    actor: "reviewer",
    owner: "marketing",
  });
  await expect(page.getByRole("alert")).toContainText("Chưa lưu thay đổi");
});
