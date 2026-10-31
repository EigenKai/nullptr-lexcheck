# Remaining work and handoff

The user revised delivery priorities to R-04 before15:50, pure legal hooks before
16:10 and Pattern guard if time permits. Earlier15:30 deployment freeze still
leaves unfinished canonical layers off. This file records work, not completion.

After16:30:

- R-06 receipt, R-07 authority audit execution and R-08 label-copy checks need
  their own scoped implementation, verified sources and positive/close-negative
  tests. The legal activation/queue hooks alone do not implement those checks.
- Rebase coordinated UI/integration PR14 and19 only after human merge of PR13,
  preserving its Excel handling and other owners' work. Do not merge another
  person's PR or force-push. The user requested this later ordering.
- Close superseded discovery branches PR9,11,12 after16:30. Keep useful source
  history; they are not a reason to re-enable old housing screens.

Before layer3 enablement, coordinate the intake flag check for stored Pattern
reuse noted in PATTERNS.md and pass the explicit deployed smoke gate. No shared
files or other owners' directories were edited by the rules packages.

The requested10 **human-written held-out** cases must be authored by the human
evaluation owner outside this public repo, without Codex reading them. Codex did
not open/list/write the existing held-out dataset. The four Pattern guards and
R-04 regressions are developer-authored public dev data; they cannot be renamed
held-out or described as handwritten by a human. Human authoring remains a handoff
item. No new held-out scores are claimed.
