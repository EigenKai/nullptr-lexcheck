# Reviewed Pattern guard and bounded reuse

`review(pattern: Pattern, cases: tuple[CheckRequest, ...]) -> Pattern` imports the
shared model. It requires a supplied human reviewer, at least four distinct known
development cases, two positives and two clean cases, exact company/pack/rule/
clause versions, a verified active basis, and zero false positives or misses.
Broad phrases such as `bác sĩ An` fail the safety-advice/negation guard. Report
hashes are computed from actual inputs, explicit labels, observed matches and
source hash. Missing reviewer leaves the candidate unchanged; failed guards
produce a rejected Pattern. No model invents labels or review evidence.

`rules/examples/pattern-guard.json` is the array of four CheckRequest values intake
PR13 expects. `pattern-guard-labels.json` contains explicit developer-authored
synthetic dev labels keyed by input hashes. These are public development guards,
not human-written held-out data and not a legal-accuracy measurement.

The first bounded reuse supports positive R-04 phrases only. Explicitly supplied
active Patterns annotate existing grounded deterministic findings with
`pattern_id`; results list the actual `pattern_ids_used`. They cannot add a new
finding, suppress a deterministic finding, bypass medical negation/safety advice,
change a rule's executed count or mutate an old check. Broader learned detection
is deferred. Default `patterns=()` preserves all baseline behavior. Candidate,
rejected, suspended, other-company and changed-version Patterns have no effect.

Only the trusted service may pass active Patterns. Intake owns the canonical
layer3 flag, authenticated reviewer, original confirmed decision membership,
source-record access and persistence; the pure engine grants no user permissions.
PR13's review route is gated, but its evaluate path also needs to stop passing
stored active Patterns when layer3 is off. This coordination item must be resolved
before enabling layer3. No layer flag or live Pattern is enabled by this package.

When a law version changes, old Patterns no longer match rule/clause versions;
intake persists the `suspended` state while keeping old checks unchanged. A finite
guard set never establishes universal accuracy; runtime reuse stays within
already-grounded deterministic findings for this reason.

Acceptance: `python -m pytest rules/tests/test_patterns.py -q`, including the
candidate, clean-guard, reuse and legal-version regression names in job2, followed
by `make fmt FORMAT_PATHS="rules"`, `make lint`, `make test`, `make eval` and
`make smoke`. Explicit `make smoke LAYER=3` controls later enablement.

Delivery evidence,2026-10-31:7 tests failed on the missing review implementation;
a further negation regression failed before bounded reuse was tightened. All9
Pattern tests and27 focused Pattern/R-04 tests now pass. Linux Python3.11 make
fmt/lint/test/eval/current smoke pass (286 tests,93% total coverage; smoke1).
Explicit layer3 smoke fails because live-layer smoke is not implemented on this
base. Layer3 stays off; no live human Pattern, held-out score or expanded legal
detection capability is claimed.
