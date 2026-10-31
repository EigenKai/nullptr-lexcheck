import { test, expect } from "@playwright/test";
import fs from "node:fs";
const demo = JSON.parse(
  fs.readFileSync(
    new URL("../../data/fixtures/demo.json", import.meta.url),
    "utf8",
  ),
);

test("history HTTP failure preserves the API dossier without static fallback", async ({
  page,
}) => {
  let fallback = 0;
  await page.route("**/demo.json", (route) => {
    fallback += 1;
    return route.continue();
  });
  await page.route("**/api/history", (route) =>
    route.fulfill({
      status: 503,
      json: { code: "not_ready", message: "Pending" },
    }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Rà soát hồ sơ", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("chưa sẵn sàng");
  await expect(page.locator(".status-strip")).toContainText("API kết nối");
  expect(fallback).toBe(0);
});

test("UI-only account switch clears the previous user snapshot and ignores private demo route", async ({
  page,
}) => {
  // Explicit browser-state test doubles, not evidence of live layer-3 integration.
  const manager = structuredClone(demo);
  manager.request.versions[0].text = "MANAGER-ONLY-SENTINEL";
  await page.route("**/api/features", (route) =>
    route.fulfill({
      json: { layer0_ready: true, layer1: true, layer2: true, layer3: true },
    }),
  );
  await page.route("**/api/session", (route) => {
    const user = route.request().postDataJSON().user_id;
    return route.fulfill({
      json: {
        user_id: user,
        group: user === "U-MANAGER" ? "manager" : "operations",
        token:
          user === "U-MANAGER"
            ? "unit-manager-token-long-enough"
            : "unit-ops-token-long-enough",
        expires_at: "2026-10-31T18:00:00Z",
      },
    });
  });
  let opsDemoReads = 0;
  await page.route("**/api/demo", (route) => {
    if (route.request().headers().authorization?.includes("unit-ops"))
      opsDemoReads++;
    return route.fulfill({ json: manager });
  });
  await page.route("**/api/history", (route) =>
    route.fulfill({
      json: {
        checks: [],
        decisions: [],
        events: [],
        queue: [],
        legal_changes: [],
        patterns: [],
        mode: "live",
      },
    }),
  );
  await page.route("**/api/records", (route) =>
    route.fulfill({
      json: {
        records: demo.request.records.filter((r) => r.id === "REC-03"),
        versions: demo.request.versions
          .filter((v) => v.record_id === "REC-03")
          .map((v) => ({ ...v, reference_ids: [] })),
      },
    }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Kho tri thức", exact: true }).click();
  await page.getByRole("button", { name: /Hồ sơ công bố REC-01/ }).click();
  await expect(page.locator(".evidence")).toContainText(
    "MANAGER-ONLY-SENTINEL",
  );
  await page.getByLabel("Tài khoản mẫu").selectOption("U-OPS");
  await expect(page.getByLabel("Tài khoản mẫu")).toHaveValue("U-OPS");
  await expect(page.locator("body")).not.toContainText("MANAGER-ONLY-SENTINEL");
  await expect(page.locator(".evidence")).not.toContainText("REC-01");
  expect(opsDemoReads).toBe(0);
});

test("record a real live review, dossier recheck finding and decision", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Rà soát hồ sơ", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Chạy kiểm tra", exact: true })
    .click();
  await expect(page.locator(".result-section")).toContainText(
    /\d+ rule đã chạy/,
  );
  await page.screenshot({
    path: "test-results/local-review.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Cập nhật nguồn", exact: true })
    .click();
  await page.getByRole("button", { name: "Gửi sự kiện mẫu tới API" }).click();
  const queueCard = page.locator(".review-card").filter({
    has: page.getByRole("heading", { name: "RV-02-v1", exact: true }),
  });
  await queueCard
    .getByRole("button", { name: "Kiểm tra lại", exact: true })
    .first()
    .click();
  await page.locator(".finding-button").first().click();
  await expect(page.locator(".evidence")).toContainText("R-02");
  await expect(page.locator(".evidence mark")).toBeVisible();
  await page
    .getByLabel("Ghi chú xử lý")
    .fill("Synthetic browser review; evidence needs human review.");
  await page
    .getByRole("button", { name: "Xác nhận phát hiện", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Đã lưu quyết định");
  await page.screenshot({
    path: "test-results/local-evidence-live.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Kho tri thức", exact: true }).click();
  await page.screenshot({
    path: "test-results/local-sources.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Cập nhật nguồn", exact: true })
    .click();
  await page.getByRole("button", { name: "Xem bản cũ / mới" }).click();
  await page.screenshot({
    path: "test-results/local-change.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
