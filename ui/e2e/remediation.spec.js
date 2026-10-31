import { test, expect } from "@playwright/test";

test("task timing separates legal sources and acknowledgement preserves assigned state", async ({
  page,
  request,
}) => {
  const flags = await (await request.get("/api/features")).json();
  if (!flags.remediation) {
    await page.goto("/");
    await expect(page.locator(".task-timing")).toHaveCount(0);
    return;
  }
  const session = await (
    await request.post("/api/session", { data: { user_id: "U-MANAGER" } })
  ).json();
  const headers = { Authorization: `Bearer ${session.token}` };
  const demo = await (await request.get("/api/demo", { headers })).json();
  const snapshot = structuredClone(demo.request);
  const target = structuredClone(
    snapshot.versions.find((v) => v.id === "RV-02-v1"),
  );
  target.id = `RV-REMEDIATION-${Date.now()}`;
  target.version += 1;
  target.supersedes = "RV-02-v1";
  target.uses = ["Hỗ trợ giấc ngủ."];
  target.text =
    "Hỗ trợ giấc ngủ.\nThực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.";
  snapshot.versions.push(target);
  snapshot.target_version_ids = [target.id];
  const checkedResponse = await request.post("/api/check", {
    headers,
    data: snapshot,
  });
  expect(checkedResponse.ok()).toBeTruthy();
  const checked = await checkedResponse.json();
  expect(checked.findings[0].rule_id).toBe("R-02");
  await page.goto("/#history");
  const card = page
    .locator("details.review-card")
    .filter({ has: page.locator("summary", { hasText: checked.id }) });
  await card.locator("summary").first().click();
  await card
    .getByRole("button", { name: /Xem phát hiện/ })
    .first()
    .click();
  await page.getByLabel("Ghi chú xử lý").fill("Synthetic task planning.");
  await page.getByLabel("Hạn nội bộ", { exact: true }).fill("2026-11-01");
  await page
    .getByLabel("Điều kiện đóng việc", { exact: true })
    .fill("Reviewer confirms correction and fresh recheck.");
  const assignedResponse = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/decisions") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Giao xử lý có hạn", exact: true })
    .click();
  const assigned = await (await assignedResponse).json();
  expect(assigned.request.internal_due_on).toBe("2026-11-01");
  expect(assigned.request.legal_due_on).toBeNull();
  const ackResponse = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/decisions") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Đánh dấu đã đọc", exact: true })
    .click();
  const acknowledged = await (await ackResponse).json();
  expect(acknowledged.task_status).toBe("assigned");
  expect(acknowledged.request.internal_due_on).toBe("2026-11-01");
  await expect(
    page.getByRole("button", {
      name: "Đóng việc sau kiểm tra lại",
      exact: true,
    }),
  ).toBeDisabled();
  await page.screenshot({
    path: "test-results/local-remediation.png",
    fullPage: true,
  });
});
