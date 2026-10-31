"""Local pilot routes: explicit activation, upload, scope and real research calls."""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from rules.legal_sources import source_from_text
from rules.tests.test_workspaces import Transport, workbook


def test_pilot_default_off_and_token_required(tmp_path):
    from rules.workspace_app import create_app

    with TestClient(create_app(tmp_path, enabled=False)) as client:
        assert client.get("/").status_code == 404
    app = create_app(tmp_path, enabled=True)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/api/workspaces").status_code == 401
        assert (
            client.get("/api/workspaces", headers={"X-Workspace-Token": app.state.token}).json()
            == []
        )


def test_upload_runs_model_research_and_persists_workspace_result(tmp_path):
    from rules.workspace_app import create_app

    source = source_from_text(
        "https://vanban.chinhphu.vn/example",
        "Synthetic law",
        "Điều 1. Hợp đồng\nBên cho thuê cung cấp hợp đồng.\nLuật có hiệu lực ngày 01 tháng 01 năm 2026.",
    )
    transport = Transport()
    app = create_app(
        tmp_path,
        enabled=True,
        transport_factory=lambda: transport,
        reader_factory=lambda *args, **kwargs: lambda url: source,
    )
    headers = {"X-Workspace-Token": app.state.token, "X-Workspace-Name": "Example"}
    with TestClient(app) as client:
        response = client.post("/api/workspaces?research=true", headers=headers, content=workbook())
        assert response.status_code == 201
        workspace_id = response.json()["id"]
        app.state.jobs[workspace_id].result(timeout=5)
        result = client.get(f"/api/workspaces/{workspace_id}", headers=headers).json()
        assert result["workspace"]["state"] == "review_needed"
        assert len(result["result"]["proposals"]) == 1
        assert result["result"]["executed_rule_count"] == 0
        assert (
            client.patch(
                f"/api/workspaces/{workspace_id}", headers=headers, json={"name": "Tên ví dụ mới"}
            ).json()["name"]
            == "Tên ví dụ mới"
        )
        assert [stage for stage, _ in transport.calls] == ["plan", "search", "extract"]
        assert (
            client.get("/api/workspaces/WS-000000000000000000000000", headers=headers).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/workspaces/{workspace_id}/research", headers=headers, json={"live": False}
            ).status_code
            == 422
        )


def test_upload_rejects_foreign_origin_and_invalid_workbook(tmp_path):
    from rules.workspace_app import create_app

    app = create_app(tmp_path, enabled=True)
    headers = {"X-Workspace-Token": app.state.token, "X-Workspace-Name": "Example"}
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/workspaces",
                headers={**headers, "Origin": "https://foreign.example"},
                content=workbook(),
            ).status_code
            == 403
        )
        assert (
            client.post("/api/workspaces", headers=headers, content=b"not-xlsx").status_code == 422
        )


def test_workspace_script_references_existing_static_elements():
    html = (Path(__file__).parents[1] / "workspace.html").read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([a-z-]+)"', html.split("<script>", 1)[0]))
    references = set(re.findall(r"\$\('([a-z-]+)'\)", html.split("<script>", 1)[1]))
    assert references <= ids, "Missing elements break initialization: " + str(references - ids)
