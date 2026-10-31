import { test, expect } from "@playwright/test";

test("dashboard groups actual tasks and preserves dossier impact history", async ({
  page,
  request,
}) => {
  const flags = await (await request.get("/api/features")).json();
  if (!flags.task_dashboard) {
    await page.goto("/#history");
    await expect(page.getByLabel("Dashboard việc khắc phục")).toHaveCount(0);
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
  target.id = `RV-DASHBOARD-${Date.now()}`;
  target.version += 1;
  target.supersedes = "RV-02-v1";
  target.uses = ["Hỗ trợ giấc ngủ."];
  target.text =
    "Hỗ trợ giấc ngủ.\nThực phẩm này không phải là thuốc và không có tác dụng thay thế thuốc chữa bệnh.";
  snapshot.versions.push(target);
  snapshot.target_version_ids = [target.id];
  const check = await (
    await request.post("/api/check", { headers, data: snapshot })
  ).json();
  const finding = check.findings.find((f) => f.rule_id === "R-02");
  const decision = {
    check_id: check.id,
    finding_id: finding.id,
    actor: "reviewer",
    note: "Synthetic dashboard task.",
  };
  expect(
    (
      await request.post("/api/decisions", {
        headers,
        data: {
          ...decision,
          action: "assign",
          owner: "marketing",
          internal_due_on: "2026-11-01",
          closure_conditions: "Fresh review.",
        },
      })
    ).ok(),
  ).toBeTruthy();
  expect(
    (
      await request.post("/api/decisions", {
        headers,
        data: { ...decision, action: "acknowledge" },
      })
    ).ok(),
  ).toBeTruthy();
  await page.goto("/#history");
  await page.getByLabel("Lọc người phụ trách").selectOption("marketing");
  await page.getByLabel("Lọc trạng thái việc").selectOption("assigned");
  const row = page.locator(`[data-finding-id="${finding.id}"]`);
  await expect(row).toContainText("Đang xử lý");
  await expect(row).toContainText("Hạn nội bộ: 2026-11-01");
  await page.screenshot({
    path: "test-results/local-dashboard.png",
    fullPage: true,
  });
  await page.getByLabel("Lọc trạng thái việc").selectOption("closed");
  await expect(row).toHaveCount(0);
  expect(
    (await request.post("/api/changes", { headers, data: demo.event })).ok(),
  ).toBeTruthy();
  await page
    .getByRole("button", { name: "Cập nhật nguồn", exact: true })
    .click();
  await page.getByRole("button", { name: "Tải lại", exact: true }).click();
  const impact = page.locator(`[data-event-id="${demo.event.id}"]`);
  await expect(impact).toContainText(demo.event.previous_version_id);
  await expect(impact).toContainText(demo.event.new_version.id);
  await expect(impact).toContainText("Kết quả cũ giữ nguyên");
  await expect(
    page.getByText("Luật nạp trước · Chưa áp dụng", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("CV-07-v1 → CV-07-v2", { exact: true }),
  ).toBeVisible();
});
