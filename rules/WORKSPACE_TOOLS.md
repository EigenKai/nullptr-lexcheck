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

## Tools and evidence

- `search_documents` searches the selected workspace's reviewed FTS index.
- `read_document` reads ingested text, Word, PDF or spreadsheet pages. PDF
  extraction uses pypdf; image-only PDFs still need the existing extraction/OCR
  workflow. Word extraction uses the existing bounded local XML reader.
- `read_excel` opens the retained XLSX with openpyxl in read-only/data-only mode.
  It reads at most 100 explicitly selected cells and emits only values matching
  the reviewed redacted extraction. It does not calculate formulas or reveal
  unknown/private cells. Citations retain worksheet, coordinates, version,
  original-byte hash and exact quote offsets.
- `summarize_excel` inspects every reviewed worksheet in one tool call and returns
  at most eight labels and eight numeric samples per sheet, within 18,000 cell-text
  characters across the workbook. It reports sampled coverage and provides exact
  contiguous citation options. It does not expose worksheet names, private cells,
  infer mixed-unit totals, or require legal evidence for a content summary.
- `web_search` calls the existing `detect.client.DiscoveryTransport`, which
  requires actual hosted web-search observations and filters official domains.
  One search request may fetch at most two official HTTPS sources, each at most
  2 MB with a 12-second retrieval timeout. Originals are archived privately;
  successfully extracted text becomes an unverified legal-library document.
  Failed or unread leads cannot support a legal answer. No OCR is invoked by
  this tool. Search queries must contain public legal topics only.

The real OSS loop allows four model steps by default, with a hard maximum of
six in its internal API. Exhaustion and unavailable models fail explicitly;
there are no canned answers. Every saved factual answer passes the shared
exact-quote validator. Legal text cannot prove business facts. Relevant legal
text, current applicability and business evidence are required for a supported
comparison; otherwise the assistant must state what is missing. An unrelated
fire-safety document cannot establish electricity pricing law.

The index fingerprint includes selected text, document version/title and hashes.
The public-source tool updates its own expected snapshot only while holding the
workspace lock; unrelated source/context changes still reject the answer.
Old turns retain their original evidence. This remains the existing local,
server-token workspace pilot, not production multi-user authorization.

Turn provenance records the harness/version, selected tool trace, cache keys,
agent model calls, public-search model calls/events and their total. A provider
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
