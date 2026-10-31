# LexCheck frontend

React frontend adapted from the user-supplied `lexcheck-ui` HTML/CSS/JavaScript prototype. Only the integrated source and required assets are included in this PR; the original prototype and proposal remain local. The app reuses its green/cream palette, sidebar, mascot and evidence panel, with Nunito Sans replacing the original sans/serif mix.

## Run on Windows

Requires Node 22.12+ and the repository's Python 3.11 environment.

```powershell
cd ui
npm ci
npm run build
cd ..
.venv/Scripts/python.exe -X utf8 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. FastAPI already mounts `ui/dist`; no backend or contract changes are needed. `-X utf8` is necessary on Windows because existing Python file readers use the system default encoding.

For development run the API as above, then `cd ui; npm run dev` in another terminal. Vite proxies `/api` and `/health` to port 8000.

## Checks

```powershell
cd ui
npm test -- --run
npm run build
npm run test:e2e
```

Start the real API on port 8000 before E2E. The suite starts Vite itself. On Windows it uses installed Microsoft Edge; on CI run `npx playwright install --with-deps chromium` first. The suite checks real fixture API reads/checks and unavailable writes, an explicitly mocked finding to exercise evidence/reviewer controls, offline fallback, and layouts at 1280×720, 768×1024 and 375×812.

From the repository root: `.venv/Scripts/python.exe -X utf8 -m pytest -q --cov` and `.venv/Scripts/python.exe -X utf8 -m eval.run`.

## API and limits

- Loads `/api/demo` and `/api/history`; sends checks, reviewer decisions, change events and recheck requests using the existing contracts.
- API errors remain visible. A 503 never becomes a successful write in local state. Zero executed rules never becomes a clean result.
- Current backend is a fixture adapter: five rules remain disabled; decisions, changes and rechecks return 503. Frontend controls are wired for these APIs, but do not implement their missing backend behavior.
- Chat is a labelled summary of staged metadata, without an AI call, persistent chat storage or backend permissions.
- `/demo.json` is a copy of the existing synthetic fixture for API outage fallback. It is labelled offline, blocks writes, and is not an evaluation result or a model cache. Synchronize it when `data/fixtures/demo.json` changes.
- Source evidence is rendered as text by React. Span highlighting requires exact original offsets/quote; Python code-point offsets are preserved. Form input is normalized to NFC.
- Local WOFF2 assets include Vietnamese glyphs. There is no runtime Google Fonts request.

## Reused assets and libraries

- Supplied `lexcheck-ui/style.css` and `assets/mascot.png`: visual foundation and mascot; provenance is the user's supplied prototype. This integration does not establish when or how that prototype was originally created.
- React / React DOM (MIT): components and rendering.
- Vite (MIT), React plugin (MIT): development server and production build.
- Nunito Sans from Fontsource (font: SIL Open Font License 1.1; package metadata: MIT): bundled Vietnamese typography.
- Vitest (MIT), Playwright (Apache-2.0): frontend and browser verification.

This task added the React integration, API handling, responsive typography adjustments and tests locally. It did not activate legal rules, produce benchmark scores, deploy a public site, or merge a PR.
