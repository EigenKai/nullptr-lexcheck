import { test, expect } from "@playwright/test";
import fs from "node:fs";

const demo = JSON.parse(
  fs.readFileSync(
    new URL("../../data/fixtures/demo.json", import.meta.url),
    "utf8",
  ),
);
const workspaceId = "WS-0123456789abcdef01234567";
async function reviewerApi(page) {
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/features")
      return route.fulfill({
        json: {
          layer0_ready: false,
          layer1: false,
          layer2: false,
          layer3: false,
        },
      });
    if (path === "/api/demo") return route.fulfill({ json: demo });
    if (path === "/api/history")
      return route.fulfill({
        json: { checks: [], decisions: [], events: [], queue: [] },
      });
    return route.fulfill({ status: 404, json: { code: "disabled" } });
  });
}

test("workspace API off preserves reviewer UI and never loads feature styles", async ({
  page,
}) => {
  await reviewerApi(page);
  await page.route("**/workspace-research/session", (route) =>
    route.fulfill({ status: 404, json: { code: "disabled" } }),
  );
  const featureRequests = [];
  page.on("request", (request) => {
    if (
      /WorkspaceChat|DocumentWorkspace|research\.css|workspace-chat\.css/.test(
        request.url(),
      )
    )
      featureRequests.push(request.url());
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Rà soát hồ sơ", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Chọn workspace" }),
  ).toHaveCount(0);
  await expect(page.locator(".research-feature")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Rà soát hồ sơ", exact: true }),
  ).toBeVisible();
  expect(featureRequests).toEqual([]);
});

test("enabled API exposes workspace documents while retaining reviewer navigation", async ({
  page,
}) => {
  await reviewerApi(page);
  await page.route("**/workspace-research/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/session"))
      return route.fulfill({
        json: { token: "synthetic-test-token", chat_enabled: true },
      });
    if (path.endsWith("/api/workspaces"))
      return route.fulfill({
        json: [{ id: workspaceId, name: "Synthetic workspace", documents: [] }],
      });
    if (path.endsWith("/conversations")) return route.fulfill({ json: [] });
    return route.fulfill({
      json: {
        workspace: {
          id: workspaceId,
          name: "Synthetic workspace",
          documents: [],
        },
        result: null,
        inventory_graph: { nodes: {}, edges: [] },
      },
    });
  });
  await page.goto("/");
  const selector = page.getByRole("combobox", { name: "Chọn workspace" });
  await expect(selector).toBeVisible();
  await selector.selectOption(workspaceId);
  await expect(page.locator(".research-feature")).toBeVisible();
  await page
    .getByRole("button", { name: "Tài liệu doanh nghiệp", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Tài liệu doanh nghiệp", exact: true }),
  ).toBeVisible();
  await selector.selectOption("demo");
  await expect(
    page.getByRole("heading", { name: "Rà soát hồ sơ", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".research-feature")).toHaveCount(0);
});
