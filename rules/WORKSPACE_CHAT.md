# Indexed workspace conversations

An optional model-selected OSS tool loop, native Excel reading and bounded
official-source web search are described in [WORKSPACE_TOOLS.md](WORKSPACE_TOOLS.md).
Both additional flags default off; the original path below remains the default.

This local pilot restores the preview's assistant screen beside the separate
business and legal document libraries. The same screen and retrieval code serve
every workspace; there are no industry-specific answers or sample fallbacks.

## Run

Build `ui/` with `npm ci` and `npm run build`. Configure `OPENAI_API_KEY` and
`OPENAI_MODEL` in private `.env`, then start the existing app with
`LEXCHECK_WORKSPACE_RESEARCH_ENABLED=1` and
`LEXCHECK_WORKSPACE_CHAT_ENABLED=1`. Both flags default to `0`. Restart after
configuration changes. This does not enable canonical layer flags or change
the deterministic rule catalog.

Choose a workspace, upload business/legal documents, inspect the redacted
business extraction, and select documents for model context. Open **Trợ lý Lex**.
New conversations and recent conversations are saved per workspace. Sending a
message needs the server-issued local workspace token; loopback/Origin checks
still apply. This is a private single-session pilot, not production multi-user
authorization.

## Retrieval and evidence

`WorkspaceIndex` maintains a persistent SQLite FTS5 index per workspace. Only
selected business text, legal documents, the user's workspace description and
derived inventory metadata are searchable. Business model text uses full selected
native content by default, with personal-field redaction as an explicit option.
Filenames and legal text never establish company activity.

The existing `detect.client.ModelClient` first returns a structured retrieval
plan. The host runs actual `search_documents` and `read_document` tools against
the local index. A second structured model call produces an answer from at most
nine retrieved passages. This is bounded host orchestration, not a native SDK
function-call loop, external web research, or automatic legal-rule activation.
The prompt and cache input include the conversation, workspace and index version.

Chat citations are optional. Each displayed quote must occur exactly in the
retrieved passage and original extracted page. Invalid optional quotes are omitted
without blocking the answer. Saved references retain document ID, version, raw
source hash, page and Unicode code-point offsets. Conversation, capability and
general questions can be answered directly. Sources changed/revoked during
generation still cause rejection. Model failures never produce a sample answer.

Conversation manifests reference separate immutable turn files. Previous answers
whose cited sources were deselected/changed are excluded from subsequent model
history. Changing a document does not rewrite old conversation evidence. Local
viewers can still inspect their earlier turns. Legal-source currency and
applicability remain unverified; pending chat interpretation cannot alter audits.

## Checks

```text
python -m pytest rules/tests/test_workspace_chat.py rules/tests/test_workspace_chat_api.py -q
make fmt FORMAT_PATHS="rules"
make lint
make test
make eval
make smoke
cd ui
npm test -- --run
npm run build
```

Tests inject model responses and use synthetic documents only. A separate live
smoke used the configured model on synthetic company text; it is integration
evidence, not a measured legal or retrieval accuracy score. Browser visual review
remains pending because Computer Use stopped on an unknown browser URL.

## Existing Excel documents and earlier extraction versions

New v3 extractions preserve native cell text and worksheet names without a
recognized-label whitelist. The default model mode is full selected content;
`Che thông tin cá nhân` is optional and creates a new extraction version. Original
bytes and earlier text remain intact. Only selected workspace documents enter
model input. The v2 behavior below describes earlier retained snapshots.

Chat lists existing business filenames, IDs, versions and model selection states.
Open the redacted extraction directly there and select it for chat; an existing
unselected file does not need another upload. The model receives that inventory
with selected/unselected states, not only counts.

Older XLSX extractions can be refreshed locally from retained original bytes.
Refresh creates a new document/extraction version with the same original hash;
earlier text snapshots remain readable. It deselects the refreshed old version,
and the new version needs selection after review. Other documents/workspaces are
not automatically selected.

The v2 local XLSX projection reads all worksheets within extraction budgets,
retains cell coordinates, masks recognized personal columns even when their
headers occur after row ten, and withholds unknown free text and long numeric
identifiers. Only recognized operational labels and associated numeric cells
enter this conservative projection. This is a privacy filter, not LLM company
classification or proof of legal activity. Unknown text, formulas without cached
values, and unsupported units may require reading the local original. Review the
projection before selection; it is deliberately incomplete.

Excel citations carry generic worksheet/page labels and original cell references
alongside exact original quote offsets, version and original-byte hash. Internal
chunk identifiers become numbered citations in answer prose. Business tariff
data does not establish whether a price is permitted by law; an unrelated legal
PDF cannot supply missing electricity-law evidence.

Index cache identity and eligible prior-answer evidence include extraction version
and citation title as well as source-byte hash. A same-byte extraction update
cannot silently reuse old citation metadata. Repeated spreadsheet values need an
unambiguous original cell quote; include the coordinate and value. Old stored
turns retain their original evidence and are not rewritten.
