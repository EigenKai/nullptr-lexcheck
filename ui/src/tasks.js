import { N_ } from "./i18n.jsx";

export const ownerLabels = {
  marketing: "Marketing",
  legal: N_("Pháp chế"),
  document_control: N_("Quản lý hồ sơ"),
  unassigned: N_("Chưa giao"),
};
export const taskLabels = {
  open: N_("Việc mở"),
  assigned: N_("Đang xử lý"),
  closed: N_("Đã đóng"),
  dismissed: N_("Đã bác bỏ"),
};

export function taskRows(history) {
  const latest = new Map();
  for (const decision of history?.decisions || []) {
    const id = decision.request.finding_id;
    const old = latest.get(id);
    if (!old || new Date(decision.created_at) >= new Date(old.created_at))
      latest.set(id, decision);
  }
  const tasks = new Map();
  for (const check of history?.checks || []) {
    if (check.mode !== "live") continue;
    for (const finding of check.findings) {
      const old = tasks.get(finding.id);
      if (
        !old ||
        new Date(check.created_at || 0) >= new Date(old.check.created_at || 0)
      ) {
        const decision = latest.get(finding.id);
        tasks.set(finding.id, {
          finding,
          check,
          decision,
          owner: decision?.request.owner || "unassigned",
          status: decision?.task_status || "open",
        });
      }
    }
  }
  return [...tasks.values()];
}

export function ownerSummaries(rows) {
  return Object.keys(ownerLabels).map((owner) => {
    const assigned = rows.filter((row) => row.owner === owner);
    return {
      owner,
      ...Object.fromEntries(
        Object.keys(taskLabels).map((status) => [
          status,
          assigned.filter((row) => row.status === status).length,
        ]),
      ),
    };
  });
}
