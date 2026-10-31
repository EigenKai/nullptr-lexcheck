import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { taskRows, ownerSummaries } from "./tasks.js";
import TaskDashboard from "./components/TaskDashboard.jsx";

const history = {
  checks: [
    {
      id: "CHK-test",
      mode: "live",
      findings: [1, 2, 3].map((n) => ({
        id: `F-${n}`,
        rule_id: "R-02",
        record_version_id: `RV-${n}`,
      })),
    },
  ],
  decisions: [
    {
      request: {
        finding_id: "F-1",
        owner: "marketing",
        action: "assign",
        internal_due_on: "2026-11-01",
      },
      task_status: "assigned",
      created_at: "2026-10-31T08:00:00Z",
    },
    {
      request: {
        finding_id: "F-1",
        owner: "marketing",
        action: "acknowledge",
        internal_due_on: "2026-11-01",
      },
      task_status: "assigned",
      created_at: "2026-10-31T08:01:00Z",
    },
    {
      request: { finding_id: "F-2", owner: "legal", action: "close" },
      task_status: "closed",
      created_at: "2026-10-31T08:02:00Z",
    },
  ],
};

it("counts the latest actual task state, keeping acknowledgement assigned", () => {
  const rows = taskRows(history);
  expect(rows).toHaveLength(3);
  expect(rows.find((row) => row.finding.id === "F-1").status).toBe("assigned");
  const owners = ownerSummaries(rows);
  expect(owners.find((row) => row.owner === "marketing").assigned).toBe(1);
  expect(owners.find((row) => row.owner === "legal").closed).toBe(1);
  expect(owners.find((row) => row.owner === "unassigned").open).toBe(1);
});

it("renders deadlines separately and excludes fixture results", () => {
  expect(
    taskRows({
      ...history,
      checks: history.checks.map((c) => ({ ...c, mode: "fixture" })),
    }),
  ).toEqual([]);
  const markup = renderToStaticMarkup(<TaskDashboard history={history} />);
  expect(markup).toContain("Hạn nội bộ");
  expect(markup).toContain("2026-11-01");
  expect(markup).toContain("Đang xử lý");
});

it("counts a repeated finding once and opens its latest immutable check", () => {
  const first = { ...history.checks[0], created_at: "2026-10-31T08:00:00Z" };
  const repeated = {
    ...first,
    id: "CHK-latest",
    created_at: "2026-10-31T08:03:00Z",
  };
  const rows = taskRows({ ...history, checks: [repeated, first] });
  expect(rows).toHaveLength(3);
  expect(rows.find((row) => row.finding.id === "F-1").check.id).toBe(
    "CHK-latest",
  );
  expect(
    ownerSummaries(rows).find((row) => row.owner === "marketing").assigned,
  ).toBe(1);
});
