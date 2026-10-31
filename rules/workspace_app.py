"""Local-only, default-off workspace research pilot; does not mount into shared API."""

import argparse
import hashlib
import json
import os
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import unquote, urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import Field

from contracts.models import Contract
from rules.discovery import Budget
from rules.discovery_cli import load_local_env
from rules.workspace_research import research
from rules.workspace_sources import WorkspaceSourceReader
from rules.workspaces import WorkspaceStore


class ResearchStart(Contract):
    live: bool
    max_seconds: float = Field(default=300, ge=1, le=600)
    max_sources: int = Field(default=5, ge=1, le=10)
    max_rounds: int = Field(default=4, ge=1, le=8)


class WorkspaceRename(Contract):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class WorkspaceCreate(Contract):
    name: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=2000)


class DocumentContext(Contract):
    enabled: bool


class ProfileStart(Contract):
    live: bool


def create_app(
    root=Path("cache/workspaces"),
    *,
    enabled=None,
    transport_factory=None,
    reader_factory=WorkspaceSourceReader,
    profile_client_factory=None,
):
    enabled = (
        os.environ.get("LEXCHECK_WORKSPACE_RESEARCH_ENABLED", "0") == "1"
        if enabled is None
        else enabled
    )
    store = WorkspaceStore(root)
    for workspace in store.list():
        if workspace["state"] == "researching":
            store.progress(
                workspace["id"],
                "interrupted",
                "Lượt trước bị gián đoạn; có thể bắt đầu lại. Snapshot đã lưu vẫn được giữ.",
            )
            store.update(workspace["id"], state="failed")
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="legal-research")
    job_lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(app):
        yield
        executor.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(
        title="LexCheck · Workspace research pilot",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.token = secrets.token_urlsafe(32)
    app.state.store, app.state.jobs = store, {}

    @app.middleware("http")
    async def local_guard(request, call_next):
        if not enabled:
            return JSONResponse({"code": "feature_disabled"}, status_code=404)
        if request.url.hostname not in ("127.0.0.1", "localhost", "::1", "testserver"):
            return JSONResponse({"code": "local_only"}, status_code=403)
        if request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
            return JSONResponse({"code": "local_only"}, status_code=403)
        origin = request.headers.get("origin")
        if origin and (
            urlparse(origin).scheme not in ("http", "https")
            or urlparse(origin).netloc != request.url.netloc
        ):
            return JSONResponse({"code": "foreign_origin"}, status_code=403)
        route_path = request.url.path.removeprefix(request.scope.get("root_path", ""))
        if route_path.startswith("/api/") and not secrets.compare_digest(
            request.headers.get("X-Workspace-Token", ""), app.state.token
        ):
            return JSONResponse({"code": "session_required"}, status_code=401)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.exception_handler(ValueError)
    async def invalid_request(request, exc):
        return JSONResponse(
            {
                "code": "invalid_request",
                "message": "Không đọc được yêu cầu hoặc tài liệu; kiểm tra định dạng và giới hạn file.",
            },
            status_code=422,
        )

    @app.exception_handler(FileNotFoundError)
    async def missing(request, exc):
        return JSONResponse({"code": "not_found"}, status_code=404)

    def start(workspace_id, options):
        if not options.live:
            raise HTTPException(422, "Live research must be explicitly requested.")
        workspace = store.get(workspace_id)
        if workspace.get("domain") == "unclassified":
            raise HTTPException(
                503, "Generic legal discovery is pending integration; no model was called."
            )
        with job_lock:
            if any(not future.done() for future in app.state.jobs.values()):
                raise HTTPException(
                    409, "Một workspace đang được nghiên cứu; chờ lượt hiện tại kết thúc."
                )
            store.update(workspace_id, state="researching", progress=[])

            def run():
                emit = lambda stage, message: store.progress(workspace_id, stage, message)
                try:
                    if transport_factory:
                        transport = transport_factory()
                    else:
                        from detect.client import DiscoveryTransport

                        load_local_env()
                        transport = DiscoveryTransport(
                            cache_dir=store.folder(workspace_id) / "model-cache"
                        )
                    budget = Budget(
                        max_seconds=options.max_seconds,
                        max_sources=options.max_sources,
                        max_rounds=options.max_rounds,
                    )
                    reader = reader_factory(
                        workspace_id,
                        store.folder(workspace_id) / "sources",
                        transport,
                        deadline=time.monotonic() + budget.max_seconds,
                        progress=emit,
                    )
                    result = research(
                        workspace, transport, fetcher=reader, budget=budget, progress=emit
                    )
                    store.finish(workspace_id, result)
                except Exception as exc:  # noqa: BLE001 - job boundary must persist failure without leaking input/provider payloads
                    emit(
                        "error",
                        "Không hoàn thành nghiên cứu: "
                        + type(exc).__name__
                        + ". Không có dữ liệu mẫu thay thế.",
                    )
                    store.update(workspace_id, state="failed")

            future = executor.submit(run)
            app.state.jobs[workspace_id] = future
        return store.get(workspace_id)

    app.state.start_research = start

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return (
            Path(__file__)
            .with_name("workspace.html")
            .read_text(encoding="utf-8")
            .replace("__SESSION_TOKEN__", json.dumps(app.state.token))
            .replace("__API_ROOT__", json.dumps(request.scope.get("root_path", "")))
        )

    @app.get("/session")
    def local_session():
        return {
            "token": app.state.token,
            "mode": "private_local_research",
            "profile_enabled": os.getenv("LEXCHECK_WORKSPACE_PROFILE_ENABLED", "0") == "1",
        }

    @app.get("/api/workspaces")
    def list_workspaces():
        return [store.migrate_documents(workspace["id"]) for workspace in store.list()]

    @app.post("/api/workspaces/demo")
    def ensure_demo_workspace():
        existing = next(
            (
                workspace
                for workspace in store.list()
                if workspace.get("reference_key") == "fixture:CO-DEMO"
            ),
            None,
        )
        if existing:
            return existing
        from intake.fixtures import load_demo

        bundle = load_demo()
        workspace = store.create_blank(
            "NULLPTR Demo", reference_key="fixture:CO-DEMO", synthetic=True
        )
        records = {record.id: record for record in bundle.request.records}
        for version in bundle.request.versions:
            record = records[version.record_id]
            name = record.title[:140] + f" ({version.id}).txt"
            store.add_document(
                workspace["id"], "business", name, version.text.encode(), origin="synthetic_fixture"
            )
        return store.get(workspace["id"])

    @app.post("/api/workspaces", status_code=201)
    async def upload(request: Request, research: bool = False):
        if request.headers.get("Content-Type", "").split(";", 1)[0] == "application/json":
            data = WorkspaceCreate.model_validate(await request.json())
            return store.create_blank(data.name, description=data.description)
        if research and any(not future.done() for future in app.state.jobs.values()):
            raise HTTPException(
                409, "Một workspace đang được nghiên cứu; chờ lượt hiện tại kết thúc."
            )
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 15_000_000:
                raise HTTPException(413, "Workbook exceeds 15 MB.")
        name = unquote(request.headers.get("X-Workspace-Name", "Nhà trọ — ví dụ Excel"))
        workspace = store.create(name, bytes(raw))
        if research:
            start(workspace["id"], ResearchStart(live=True))
        return store.get(workspace["id"])

    @app.get("/api/workspaces/{workspace_id}")
    def workspace_detail(workspace_id: str):
        workspace = store.migrate_documents(workspace_id)
        if workspace.get("profile"):
            fingerprint = hashlib.sha256(
                json.dumps(
                    store.model_context(workspace_id), sort_keys=True, ensure_ascii=False
                ).encode()
            ).hexdigest()
            workspace["profile_stale"] = workspace["profile"]["input_sha256"] != fingerprint
        return {
            "workspace": workspace,
            "result": store.result(workspace_id),
            "inventory_graph": store.inventory_graph(workspace_id),
        }

    @app.patch("/api/workspaces/{workspace_id}")
    def rename_workspace(workspace_id: str, change: WorkspaceRename):
        fields = {"name": change.name}
        if change.description is not None:
            fields["description"] = change.description
        return store.update(workspace_id, **fields)

    @app.get("/api/workspaces/{workspace_id}/documents")
    def document_list(workspace_id: str):
        store.migrate_documents(workspace_id)
        return store.documents(workspace_id)

    @app.post("/api/workspaces/{workspace_id}/documents/{collection}", status_code=201)
    async def document_upload(workspace_id: str, collection: str, request: Request):
        store.migrate_documents(workspace_id)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 15_000_000:
                raise HTTPException(413, "Document exceeds 15 MB.")
        name = unquote(request.headers.get("X-File-Name", "document.txt"))
        return store.add_document(workspace_id, collection, name, bytes(raw))

    @app.get("/api/workspaces/{workspace_id}/documents/{document_id}")
    def document_detail(workspace_id: str, document_id: str):
        return store.document(workspace_id, document_id)

    @app.get("/api/workspaces/{workspace_id}/documents/{document_id}/raw")
    def document_raw(workspace_id: str, document_id: str):
        document = store.document(workspace_id, document_id)
        path = (
            store.folder(workspace_id)
            / "documents"
            / document_id
            / ("original" + document["suffix"])
        )
        return FileResponse(path, filename=document["name"], media_type="application/octet-stream")

    @app.patch("/api/workspaces/{workspace_id}/documents/{document_id}/context")
    def document_model_context(workspace_id: str, document_id: str, selection: DocumentContext):
        return store.document_context(workspace_id, document_id, selection.enabled)

    @app.post("/api/workspaces/{workspace_id}/profile")
    def profile(workspace_id: str, options: ProfileStart):
        if not options.live or os.getenv("LEXCHECK_WORKSPACE_PROFILE_ENABLED", "0") != "1":
            raise HTTPException(503, "Generic profile analysis is disabled.")
        from rules.workspace_profile import infer_profile

        if profile_client_factory:
            client = profile_client_factory(workspace_id)
        else:
            from detect.client import ModelClient

            load_local_env()
            client = ModelClient(
                cache_dir=store.folder(workspace_id) / "profile-cache",
                user_id="local-session",
                group="manager",
                acl_hash=workspace_id,
            )
        try:
            return infer_profile(store, workspace_id, client)
        except RuntimeError as exc:
            raise HTTPException(
                503, "Business analysis unavailable; no sample was substituted."
            ) from exc

    @app.post("/api/workspaces/{workspace_id}/research", status_code=202)
    def begin_research(workspace_id: str, options: ResearchStart):
        return start(workspace_id, options)

    @app.get("/api/workspaces/{workspace_id}/sources/{sha256}")
    def download_source(workspace_id: str, sha256: str):
        import re

        if not re.fullmatch(r"[a-f0-9]{64}", sha256):
            raise HTTPException(404)
        result = store.result(workspace_id)
        if not result or not any(
            n["kind"] == "LegalDoc" and n["payload"]["sha256"] == sha256
            for n in result["graph"]["nodes"].values()
        ):
            raise HTTPException(404)
        for suffix, media_type in ((".pdf", "application/pdf"), (".html", "text/plain")):
            path = store.folder(workspace_id) / "sources" / (sha256 + suffix)
            if path.is_file():
                return FileResponse(
                    path, media_type=media_type, filename="official-source" + suffix
                )
        raise HTTPException(404)

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--enable", action="store_true", help="Explicitly enable this local research pilot."
    )
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--import-workbook", type=Path)
    parser.add_argument("--name", default="Nhà trọ — ví dụ Excel")
    parser.add_argument("--research", action="store_true")
    args = parser.parse_args()
    if not args.enable:
        parser.error(
            "Pass --enable for the local-only pilot; production layer flags remain unchanged."
        )
    app = create_app(enabled=True)
    if args.import_workbook:
        from rules.discovery_cli import _path

        workspace = app.state.store.create(args.name, _path(str(args.import_workbook)).read_bytes())
        print(
            json.dumps(
                {
                    "workspace_id": workspace["id"],
                    "name": workspace["name"],
                    "sheet_count": len(workspace["manifest"]["sheets"]),
                },
                ensure_ascii=False,
            )
        )
        if args.research:
            app.state.start_research(workspace["id"], ResearchStart(live=True))
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
