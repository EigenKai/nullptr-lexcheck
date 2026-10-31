# R-05 through R-08: disabled implementation package

The evaluator implements four additional deterministic checks. All four catalog
entries remain disabled. Canonical layer 2 and layer 3 remain off. No model,
source discovery, sample pack or candidate feedback can enable these entries.

| Rule | Narrow behavior | Current gate |
|---|---|---|
| R-05 | Exact dictionary phrases about medicinal effects request human review. Negated warnings are excluded. Quotes retain raw Unicode offsets. | Article 8(9) of the Advertising Law, consolidated in 88/VBHN-VPQH, PDF page 6, is transcribed but not human verified. It is a general misleading-advertising provision; the dictionary is a review heuristic, not proof of a violation. |
| R-06 | For `ad_registration`, request a receipt when no selected, connected, same-product `registration_receipt` record is available. | NQ21 Annex I, 1(b), PDF page 12 needs human verification and interpretation review. Shared validator support is also missing. |
| R-07 | For `ad_registration`, review the issuing authority of a selected confirmation dated on or after 1 July 2026. Unknown authority/date requires evidence; ambiguous sources stay uncertain. | Reuses Dung's already verified NQ21 source snapshot. Interpretation remains pending, review and activation dates remain null. |
| R-08 | For `ad_registration`, request a label when no selected, connected, same-product `label` record is available. | NQ21 Annex I, 1(c), PDF page 12 needs human verification and interpretation review. Shared validator support is also missing. |

R-06 and R-08 only check connected document presence. They do not verify the
complete alternative declaration packages, signature, validity or label image.
No missing connected record proves that a procedure never happened outside this
workspace. Scientific evidence and clinical plausibility are not adjudicated by
the R-05 keyword dictionary. Implied medicinal claims remain outside this check.

Original bootstrap clause entries are preserved. New candidate clauses use
`CV-05-v2`, `CV-06-v2`, `CV-07-v2` and `CV-08-v2`; pending candidates retain
`in_force: unknown` and null human reviewer fields. The original source PDFs and
private files are not committed. Source hashes were computed from downloaded
official files. The old and new R-07 authority clauses remain in the preloaded
event; the event's issue, effective, received, review and activation dates remain
separate. Older confirmations are never automatically declared void.

## Validator handoff to Tuan Anh

No `detect/` file is changed in this package. The current validator rejects
`missing_field` evidence with field `registration_receipt` or `label_copy` as
`evidence_mismatch`. R-06 and R-08 must remain disabled until a separately
reviewed validator PR supports those fields.

The validator should decide presence from selected context versions whose
record identity is linked by the target's immutable `reference_ids`, with the
same `product_id` and the required kind. Selecting a newer authoritative version
of that same linked record should count; selecting an unrelated product, an
unlinked record or an unselected version should not. Neither field should be
implemented as `bool(reference_ids)` or a text-keyword heuristic.

Required integration acceptance after that handoff: take the synthetic positive
cases in `test_r06_r08_positive_cases`, call `validate_findings` with the returned
rule/clause snapshots, and assert zero rejections and exact finding preservation.
Repeat the close negative cases, including an explicit document revision.
R-05 and R-07 span findings already have zero-rejection integration tests.

## Acceptance

`python -m pytest rules/tests/test_additional_rules.py -q` exercises at least two
positive and two close negative cases per rule, exact raw offsets, immutable
input snapshots, same-product selection, explicit revisions, advertising versus
registration scope, shared-validator support and distinct finding IDs for two
targets sharing one authority source. All cases are synthetic development cases;
none is a human held-out case or a legal accuracy measurement.

Before enabling any entry, obtain the missing human source and interpretation
review, land the required validator support, pass all lower layers on main, then
pass the explicit layer-2 and deployed smoke gates. This PR does not fulfill
those activation gates.

## Build evidence

| Time (+07) | Member | Evidence | Result |
|---|---|---|---|
| 2026-10-31 16:28 | Dung / Codex | Red-first synthetic behavior tests, source-only Python 3.11 Linux check | 29 new-rule tests; 75 focused acceptance tests; 408 full tests, 93% coverage; actual `make fmt FORMAT_PATHS=rules`, `make test`, `make lint`, `make eval` and default `make smoke` passed. Dev eval ran 14 cases under the four existing enabled rules; this is not an evaluation of disabled R-05..08. |
| 2026-10-31 16:28 | Dung / Codex | Explicit `make smoke LAYER=1`, `LAYER=2`, `LAYER=3` | Each found no matching smoke test and exited with pytest status 5. None of those gates is claimed green; layer flags and all four new catalog entries stay off. R-05/06/08 human verification and R-06/08 validator support remain unfinished. |
