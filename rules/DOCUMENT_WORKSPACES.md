# Shared document workspaces

The user requested a correction to the first housing demo: one overview for every company, two document libraries, uploads into an existing workspace, and a clear distinction between UI statistics and model-produced business understanding.

The main React app now renders **DocumentWorkspace for every workspace whenever the existing local research feature is enabled**, including the synthetic TPBVSK fixture and the private housing example. The industry-specific RentalWorkspace component was removed. With the feature disabled, the existing reviewer UI remains unchanged.

## What works

- Create an empty workspace with a name and optional user-authored activity description. No industry or legal pack is assigned from its name.
- Add files to **Tài liệu doanh nghiệp** or **Tài liệu luật** within the currently selected workspace. Supported native text formats are PDF (optional pypdf), DOCX, XLSX, UTF-8 TXT/Markdown/CSV/JSON, with size/ZIP/page/sheet limits.
- Original files remain in ignored private cache. Each upload has its real SHA-256, collection, original filename, extraction status, receive time and version. Reuploading identical bytes in the same collection reuses the document; changed bytes with the same name append a version and keep the previous file.
- View locally extracted text or download the original through the token-protected API. Scans/unsupported native extraction report an explicit need for OCR; this package does not silently call OCR or fabricate page text.
- Business-context selection is opt-in after viewing a redacted preview. Emails, telephone/identifier patterns and recognized personal columns/labelled lines are masked. Redaction is incomplete by nature, so the user must review it. Original text is available only as a separate local preview. Neither raw uploads nor selected context are sent automatically.
- Inventory graph snapshots place company documents in layer3 and legal documents in layer1. Existing saved candidate rules remain layer2; no uploaded file becomes a rule automatically. Original graph snapshots and old profile outputs remain available. Existing housing research is explicitly marked as using developer-configured context and needing a fresh generic run.
- The synthetic TPBVSK company is imported from the existing public DemoBundle records into the same library/overview. No developer-authored sample rule is used as a generated result.

## Generic business understanding

`POST /workspace-research/api/workspaces/{id}/profile` is implemented through the existing `detect.client.ModelClient` boundary, with structured output, a neutral prompt and no industry-specific input defaults. It uses only the user description and explicitly selected **company** document excerpts, never law-library contents. Factual citations must match both the selected redacted input and original extracted page text. Exact Unicode offsets are preserved in original extracted text; a separate input offset records the redacted view. A profile has its own immutable ID, input hash, timestamp, model/cache/call provenance, unknown facts and unverified status. Changing selected inputs marks the displayed profile stale.

This analysis remains **default-off** behind `LEXCHECK_WORKSPACE_PROFILE_ENABLED=0`. The profile button says when it is disabled and shows no substitute summary. Nothing in this package configures a private key or enables a runtime flag. The existing `LEXCHECK_WORKSPACE_RESEARCH_ENABLED` flag still gates the whole private local API/UI. Production reviewer authorization is unchanged; this feature remains loopback-only with its own per-process token and Origin checks.

## What is not complete

**Generic law discovery and rule generation from these two libraries are not integrated yet.** The generic workspace API refuses to start the old housing-specific research pipeline, and the new UI exposes no misleading start button for that pipeline. Legal files can be uploaded, read and retained as source evidence; they are not yet automatically fed to a new generic extraction/execution chain. No rule is activated and no legal audit capability is claimed.

No live model, search or OCR calls were made for this rework. Model behavior is tested with injected synthetic responses; no legal accuracy is measured. The inherited housing-specific result is kept as historical data and labelled accordingly. No private workbook, document, source PDF, model output or credential is committed.

## Validation

New red-first tests cover collection and workspace isolation, actual upload endpoints, format rejection, deduplication/version immutability, redacted context opt-in, law exclusion from company analysis, generic profile provenance and absence of industry defaults. Frontend tests prove both library uploads use the same current-workspace API and do not start research automatically. The production React build retains the Nunito Sans Vietnamese assets.

Use the integrated app as described in WORKSPACES.md; no service is automatically restarted or deployment enabled by this package. Computer Use is blocked on this machine because it could not establish the current browser URL confidently; manual visual review remains pending. No browser automation workaround was attempted.
