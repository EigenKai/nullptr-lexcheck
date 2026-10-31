# Optional workspace tool harness

The workspace assistant can use Hugging Face's Apache-2.0
[smolagents ToolCallingAgent](https://huggingface.co/docs/smolagents/reference/agents)
instead of the existing two-call retrieval plan. The model chooses JSON tools;
there is no CodeAgent, Python executor, shell tool or unrestricted browser.
The custom [Model adapter](https://huggingface.co/docs/smolagents/reference/models)
calls only the existing `detect.client.ModelClient` boundary. No provider SDK is
imported or called by this runner.

## Install and enable

Use an isolated environment with the repository requirements and
`rules/tooling-requirements.txt`. Direct optional dependencies are pinned:
smolagents 1.26.0, openpyxl 3.1.5 and pypdf 6.21.4. The upstream agent API is
experimental; update its pin only after running these behavioral tests.
MarkItDown and Brave MCP are not used by this implementation.

```sh
python3.11 -m venv .venv-tools
.venv-tools/bin/python -m pip install -r requirements.txt -r rules/tooling-requirements.txt
```

Set `LEXCHECK_WORKSPACE_TOOL_HARNESS_ENABLED=1` in addition to the existing
workspace research/chat flags, then restart the service. Public legal search
also requires `LEXCHECK_WORKSPACE_WEB_SEARCH_ENABLED=1`. Both new flags default
to `0`. The default chat path never imports optional harness dependencies.
Configure `OPENAI_API_KEY` and `OPENAI_MODEL` privately on the server. These
flags do not activate canonical layers, generated rules or legal findings.
Web search uses `BRAVE_SEARCH_API_KEY`, also server-side only.

## Tools and evidence

- `search_documents` searches the selected workspace's reviewed FTS index.
- `read_document` reads ingested text, Word, PDF or spreadsheet pages. PDF
  extraction uses pypdf; image-only PDFs still need the existing extraction/OCR
  workflow. Word extraction uses the existing bounded local XML reader.
- `read_excel` opens the retained XLSX with openpyxl in read-only/data-only mode.
  It reads at most 100 explicitly selected cells and emits only values matching
  the selected extraction. Full native text, including free text and worksheet
  names, is the default. The user may explicitly enable personal-field redaction.
  It does not calculate formulas. Optional citations retain worksheet, coordinates, version,
  original-byte hash and exact quote offsets.
- `summarize_excel` inspects every reviewed worksheet in one tool call and returns
  at most eight labels and eight numeric samples per sheet, within 18,000 cell-text
  characters across the workbook. It reports sampled coverage and provides exact
  contiguous citation options. It exposes the selected full extraction, including
  worksheet names, or the user's optional redacted version. It does not infer
  mixed-unit totals or require legal evidence for a content summary.
- `web_search` uses Brave's documented HTTP API through `rules/brave_search.py`.
  It returns actual provider URLs, descriptions and extra snippets. Original or
  official sources are a preference, not a government-domain restriction. There
  is no single-search quota: the model can refine a query within the normal
  overall agent-step budget. Returned public HTTPS links need not be legal sites.
  Private/local addresses, file URLs and credentials remain excluded. Search
  snippets are not a claim that full original pages were read or legal rules
  verified. The chat adapter does not alter formal rule-source verification.
  [Brave API reference](https://api-dashboard.search.brave.com/api-reference/web/search/get).
- `open_url` opens actual public HTTP(S) content and returns native text plus
  resolved HTML links, including links to downloadable documents.
- `download_file` archives actual bytes and returns a workspace-scoped opaque
  file ID, source URL, SHA-256 and retrieval time. Downloading is not reading.
- `read_file` reads that artifact with the existing native HTML/PDF/Word/Excel/text
  parser. It reports page count, parser, actual excerpts and continuation offsets;
  a sparse/scanned PDF can report that OCR or review is needed.

These tools are independent choices in the real agent registry. There is no
fixed workflow, intent router, industry-specific prompt or mandated sequence.
Public network requests validate redirects and resolve/pin public IP addresses;
private/local destinations and arbitrary local file paths remain inaccessible.
Downloads stay in the current workspace cache and do not change document
selection. References are optional; parser observations retain URL/hash/time.

The real OSS loop defaults to twelve steps, configurable through
`LEXCHECK_WORKSPACE_AGENT_MAX_STEPS` (1–40). The model can stop early.
Exhaustion and unavailable models fail explicitly;
there are no canned answers. Chat citations are optional for every answer type.
Supplied quotes pass exact-source validation; invalid optional references and
orphan markers are omitted without blocking the answer. Conversation, general
information and capability questions can be answered directly. Actual tool
registry metadata tells the model which tools are enabled and their scope; no
document citation or search is needed to explain those capabilities. The model
must remain honest about unknown facts and actions. These chat choices do not
change deterministic audit validators or activate legal rules.

Business documents start unselected. Selecting them authorizes model processing
of their native extracted contents; no free-text/operational whitelist is applied.
The chat UI does not apply automatic masking or content filters. Earlier masked
extraction snapshots remain intact; full native versions use the same original
hash. Runtime files/caches stay outside the public repository. Mechanical
extraction/size budgets still apply and are reported.

The index fingerprint includes selected text, document version/title and hashes.
The public-source tool updates its own expected snapshot only while holding the
workspace lock; unrelated source/context changes still reject the answer.
Old turns retain their original evidence. This remains the existing local,
server-token workspace pilot, not production multi-user authorization.

Turn provenance records the harness/version, selected tool trace, cache keys,
agent model calls, public-search model calls, Brave HTTP calls/events and their
model-request total. Brave HTTP calls do not count as model calls. A provider
that does not expose call events is reported with unknown search/total call
counts rather than an invented number. Hosted search operations within one
provider response are distinct from these model-request counts.

## Checks

```sh
.venv-tools/bin/python -m pytest rules/tests/test_workspace_harness.py rules/tests/test_workspace_chat.py -q
make fmt FORMAT_PATHS=rules
make lint
make test
make eval
make smoke
```

Tests use generated synthetic XLSX/DOCX/PDF documents and injected model/search
network boundaries, while running the actual smolagents loop, local parsers,
workspace ingestion and citation validator. Live synthetic integration smokes
are separate from tests and do not measure legal or retrieval accuracy.
