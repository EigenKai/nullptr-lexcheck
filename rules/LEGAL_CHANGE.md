# Pure legal activation and impact

`validate_activation(state: LegalChangeState, review_date: date) -> tuple[Rule, ...]`
and `affected_checks(event: LegalChangeEvent, checks: tuple[CheckResult, ...]) ->
tuple[RecheckItem, ...]` use the shared contracts. They do not call a model, read
the environment, use the clock, mutate old results, or write the catalog.

Activation requires accepted interpretation, a ready/active state, a recorded
human reviewer, coherent receipt/review/source-verification timestamps, verified
source/rules, and an effective interval containing the supplied review date.
It returns enabled copies for a runtime overlay. Intake PR13's `can_activate`
separately checks the actual system date and authorizes the caller. Intake owns
the review/activation timestamps and persistence. This module grants no role.

The queue depends on actual old rule/clause snapshots, includes clean checks,
deduplicates by event/check/target, and excludes unrelated activity/clause/profile.
A legal authority change applies to affected products, not only records with old
findings. Queuing never declares an existing certificate void. Old results and
source versions are retained; the service creates a fresh result for each recheck.

## Preloaded NQ21 evidence

`load_preloaded()` returns the old clause and a pending state from
`nq21-preloaded.json`. It records the signed original's actual byte hash and the
human rule owner Dung's explicit confirmation in this session. The agent compared
ND15 page20, NQ21 pages1,10,11 and re-downloaded the original. Source verification
is separate from manager acceptance of an interpretation.

- Issued:2026-04-29.
- Authority provision effective:2026-07-01 (Article6(2)).
- Received: actual fresh download timestamp in the event.
- Reviewed: null until a real reviewer accepts through the service.
- Activated: null until the separate activation action passes its gates.

Article6 includes expiry/earlier-change and transitional provisions. Historical
applications need human review. The old snapshot quotes27(5)(a) accurately; it
does not invent wording naming a national authority. The new clause quotes2(1)(a).
The snapshot's old authority interval does not revoke old certificates.

No runtime state is activated, no canonical flags change, and the disabled R-07
bootstrap catalog is untouched. R-07 authority evaluation remains roadmap work;
these pure functions and verified source snapshots alone do not complete layer2.
The dated evidence is preloaded, not a live legal-update monitoring claim.

Acceptance: `python -m pytest rules/tests/test_legal_change.py -q`, then
`make fmt FORMAT_PATHS="rules"`, `make lint`, `make test`, `make eval`, `make smoke`.
Explicit `make smoke LAYER=2` remains a deployment gate and must not be bypassed.

Delivery evidence,2026-10-31:13 initial tests failed on the missing module;
16 final focused tests passed. Linux Python3.11: `make fmt FORMAT_PATHS=rules`,
`make lint`, `make test` (275 passed,93% total coverage), `make eval` and current
`make smoke` (1 passed) pass. Explicit layer2 smoke fails with “Requested live
smoke is not implemented yet.” Therefore layer2 remains off; this PR does not
claim full intake/deployed-layer integration or a new held-out measurement.
