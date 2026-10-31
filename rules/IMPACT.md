# Record-change impact

`enqueue(event: ChangeEvent, checks: tuple[CheckResult, ...]) -> tuple[RecheckItem, ...]`
returns deterministic queue items with `event_id`, `previous_check_id` and the
original `target_version_id`, matching Khanh's `intake.service.change/recheck`
integration. The caller authorizes inputs and persists/deduplicates queue items.

Every previously checked target is considered, including clean checks. Reference
paths are followed transitively with cycle protection. Missing paths use a
conservative same-company, same-product fallback. P-02 is excluded when P-01's
dossier changes, even if an erroneous cross-product reference exists. Already
refreshed selected contexts are not queued again. IDs are hashes of event/check/
target, independent of input ordering. Conflicting immutable IDs/scope fail closed.

`apply_event(snapshot: CheckRequest, event: ChangeEvent) -> CheckRequest` appends
the supplied version, updates the explicitly selected source/target, and keeps all
old versions, old reference IDs, review date and original text unchanged. Reapplying
an identical event is idempotent. Unknown record metadata, ID collisions, invalid
increments and dangling new references are rejected; no missing evidence is invented.

The event carries no company/product metadata. A prior snapshot without the changed
record's metadata cannot be scoped or reconstructed by these pure signatures; the
caller must supply a complete authorized snapshot before rechecking it. No outside
product/company is inferred from an ID string.

Acceptance: `python -m pytest rules/tests/test_impact.py -q` (14 synthetic tests).
The two-target test verifies the fresh input differences without claiming the
bootstrap engine executed a legal rule. A separate read-only development smoke
with Tuấn Anh's unmerged engine source and a clearly synthetic basis produced one
finding for RV-02 and zero for RV-03; that branch was not merged. Integration into
the main runtime still requires the human-reviewed engine/API PRs.

No model calls, file writes or catalog activation occur in these functions.
