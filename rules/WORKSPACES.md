# Private workspace research pilot

**Current shared document UI:** see [DOCUMENT_WORKSPACES.md](DOCUMENT_WORKSPACES.md).
It replaces the industry-specific screens with the same overview and separate
business/legal libraries for every workspace. The standalone XLSX/housing flow
described below is historical development documentation, not the current upload
or generic model workflow. Generic law discovery/rule generation remains pending.

This package implements the user's rental-housing example. The follow-up integration, explicitly requested by the user, adds a selector and native research screens to the existing React UI and mounts its private API in the main FastAPI app. It is a coordinated integration PR; shared contracts and the runtime TPBVSK pack are unchanged. `LEXCHECK_WORKSPACE_RESEARCH_ENABLED` defaults to `0`. No production layer flag changes.

## Run

For the integrated demo (recommended for the current user walkthrough):

```powershell
# Build existing React UI first: cd ui; npm ci; npm run build; cd ..
$env:LEXCHECK_WORKSPACE_RESEARCH_ENABLED = "1"
.venv/Scripts/python.exe -X utf8 -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

Open <http://127.0.0.1:8002> and choose the housing workspace from the selector below the LexCheck logo. Existing private workspaces are read from ignored `cache/workspaces`; `LEXCHECK_WORKSPACE_DIR` can select a separate local store. A link with `#workspace/<id>` opens a specific workspace. The main sidebar exposes overview, rule/source tracing, original PDF/text pages, workbook structure and research gaps. Switching back to TPBVSK restores the existing reviewer screens. Creating another housing workspace uploads the workbook to the local API and starts research only on the explicitly labelled button. Viewing saved results makes no model calls.

The main app mounts research under `/workspace-research` only when the flag is enabled; otherwise no research store is instantiated. Its loopback/Origin/token checks still apply after mounting. The server issues the research session through `/workspace-research/session`, distinct from the canonical reviewer session. This local-only integration is not production multi-company authorization. The research subapp's lifespan is managed by the parent app.

The standalone pilot remains available for development:

From repository root with the authorized OpenAI adapter available:

```powershell
.venv/Scripts/python.exe -X utf8 -m rules.workspace_app --enable --port 8001 --import-workbook QUAN_LY_NHA_TRO_AN_DANH.xlsx --name "Nhà trọ — ví dụ Excel" --research
```

Then open <http://127.0.0.1:8001>. Without `--import-workbook`, existing local workspaces are loaded. The UI creates workspaces from `.xlsx`, switches among them, renames their display labels, starts research, shows live progress, and displays sources/pages, rule proposals, missing facts and graph counts by layer. "Create workspace & research" starts the real model workflow automatically. A rerun creates a new immutable result file and retains earlier runs on disk; it is a fresh bounded search, not an exhaustive continuation.

Use private root `.env` entries `OPENAI_API_KEY` and `OPENAI_MODEL`. The selected model must support hosted web search, structured outputs and PDF inputs. No model name or key is guessed. SDK calls remain exclusively in `detect/client.py`. PDF input syntax was checked against [official OpenAI file-input documentation](https://developers.openai.com/api/docs/guides/file-inputs).

Native PDF text uses the optional `pypdf` package. Install it locally into the virtual environment if absent; shared dependencies remain coordinated separately. Without it, PDFs report a source gap. Tests inject transports/PDF objects and need no key, network or private workbook.

## Privacy and scope

- The original Excel stays under ignored `cache/workspaces/<id>/source.xlsx`. Do not commit or publish it. The specific user-supplied workbook is also excluded locally from Git.
- The structural projection never returns cell contents, formulas, links, tenant values or raw sheet names. It uses only standardized categories, row/cell counts, byte length and a real SHA-256 of the uploaded bytes. The model receives category signals and explicit unknown business facts, not workbook cells or tenant data. Workspace display names are labels and are not sent for research.
- The app binds to `127.0.0.1`. The local API requires a per-process token, a loopback client/host and matching Origin; there is no public CORS or raw Excel download endpoint. This is not production multi-user authorization and must not be deployed as a replacement for canonical reviewer sessions/ACLs.
- Only `.xlsx` is accepted; macro workbooks, external worksheet relations, unsafe XML and files exceeding size/sheet/cell budgets are rejected. No formula, embedded link or workbook instruction executes.
- Presence of a PCCC/residence sheet is an inventory signal. It never proves completion of a procedure; absent connected data never proves it did not occur externally. Locality, building scale, registration form, turnover and procedure history remain unknown.

## Research and stopping

The model plans up to five topics from business activity and workbook structure, searches official sources, and supplies real search-source URLs. The host validates URLs/redirects, downloads originals with byte/time/page limits and archives actual raw bytes by SHA-256. Native text is read locally first. Sparse scan pages use the configured model's PDF input in batches of at most four, preserving their original page mapping. At most eight sparse pages per run are OCRed in this pilot; opening/closing pages are prioritized. Omitted pages, illegibility and OCR failures stay explicit gaps. No transcription is described as human-verified.

Extraction uses the actual selected source pages and a housing-specific **incomplete obligation proposal** schema. Exact quote spans and article locations are checked. A proposed date also needs a matching source date quotation containing that date; missing dates stay null. Version/current-applicability checks still require human legal review. Authorities' and tenants' duties are excluded from operator proposals.

Default bounds are five source attempts, four search rounds, 24 proposals and 300 seconds, plus no-new-source stopping. Failed fetches count as attempts. A topic is covered only in the limited sense that at least one grounded proposal was obtained; unresolved referenced instruments still require research. Reaching all planned topics does not establish legal completeness. No sample rule, fabricated source or static catalog fallback is used.

## Three layers (proposal §4.1)

1. `LegalDoc` contains original URL, raw hash, pages and extraction method. `Article` leads to canonical `ClauseVersion` when a source-supported effective date exists; otherwise an incomplete `ClauseExcerpt` is retained. References and amendment/repeal/suspension relations remain labelled candidate/unresolved. Raw quote offsets are Unicode code points on the preserved page transcription.
2. `RuleProposal` derives from the exact clause/excerpt and links to a `Concept`. It includes actor, applicability/thresholds, unknown facts, exceptions and evidence needed. It is deliberately **not an alternative definition of the canonical executable `Rule`**: current canonical types are TPBVSK-specific. `runtime_contract=requires_domain_pack_review`, `enabled=false`, `verification_status=to_be_verified`, operation `model_review`; activation date stays null.
3. `Company`, `WorkbookSnapshot` and `SheetSnapshot` record the private example and immutable input hash. `POTENTIALLY_SUBJECT_TO` links the workbook to proposals with applicability pending. No finding or confirmation is invented from worksheet presence.

Every result reports **0 executed rules** and `not_enough_information`. A reviewed rental-housing pack and coordinated contract/API integration are required for later audit execution. Human rule-owner verification of original clauses, dates and applicability is still required before enabling any rule. Old confirmations and connected records are not declared void.

## Validation and known limits

Named acceptance commands:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest rules/tests/test_workspaces.py rules/tests/test_workspace_app.py rules/tests/test_workspace_sources.py rules/tests/test_workspace_ocr.py -q
.venv/Scripts/python.exe -X utf8 -m pytest -q --cov --cov-report=term-missing
.venv/Scripts/ruff.exe check .
.venv/Scripts/python.exe -X utf8 -m eval.run
.venv/Scripts/python.exe -X utf8 -m scripts.smoke --layer auto
```

These are the Windows equivalents of the repository Makefile targets (`make` is unavailable in this shell). Run `ruff format rules` and `ruff check --fix rules` before each owned commit.

The initial actual workbook has seven sheets. A real API run autonomously found and downloaded an official PDF, OCRed eight pages, and saved three pending PCCC proposals with graph nodes in all three layers. It stopped at the five-source-attempt limit; four fetch URLs failed, many scan pages were omitted, dates remain unverified and four planned topic groups lacked proposals. This demonstrates orchestration, not legal coverage/accuracy. Results, original documents and API caches remain private and are not fixtures or evaluation results.

Computer Use stopped Chrome verification because it could not determine the current Windows browser URL confidently enough to enforce its policy; direct visual review remains outstanding. The integrated API was exercised against the running main service, preserving the existing `/api/demo` and private workspace results. Linux `make test/lint/eval/smoke` pass; frontend unit tests and production build pass. Windows-only failures in the existing final-eval tests (`O_NOFOLLOW` and symlink privileges) were not worked around in another owner's code; the complete suite passes in Linux. Only synthetic test datasets were used. MiniRAG has not been installed or substituted by this package. No hosted deployment or layer activation is claimed.
