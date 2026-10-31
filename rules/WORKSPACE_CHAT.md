# Indexed workspace conversations

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
derived inventory metadata are searchable. Business model text uses the reviewed
redacted extraction. Filenames and legal text never establish company activity.

The existing `detect.client.ModelClient` first returns a structured retrieval
plan. The host runs actual `search_documents` and `read_document` tools against
the local index. A second structured model call produces an answer from at most
nine retrieved passages. This is bounded host orchestration, not a native SDK
function-call loop, external web research, or automatic legal-rule activation.
The prompt and cache input include the conversation, workspace and index version.

Each cited quote must occur exactly in the retrieved passage and original
extracted page. Saved evidence retains document ID, version, raw source hash,
page and Unicode code-point offsets. A company-information answer requires a
business source. Sources changed/revoked during generation cause rejection.
Model failures and unsupported quotes never produce a substitute sample answer.

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
