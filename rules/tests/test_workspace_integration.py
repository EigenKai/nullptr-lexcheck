"""Shared-app integration stays off by default and preserves the existing API."""

import pytest
from fastapi.testclient import TestClient

from rules.tests.test_workspaces import workbook
from rules.workspaces import WorkspaceStore


def test_main_app_mounts_private_workspace_api_only_when_enabled(monkeypatch, tmp_path):
    from app.main import create_app

    monkeypatch.setenv("LEXCHECK_WORKSPACE_RESEARCH_ENABLED", "0")
    monkeypatch.setenv("LEXCHECK_WORKSPACE_DIR", str(tmp_path))
    with TestClient(create_app()) as client:
        assert client.get("/workspace-research/session").status_code == 404
        assert client.get("/health").status_code == 200
    monkeypatch.setenv("LEXCHECK_WORKSPACE_RESEARCH_ENABLED", "1")
    workspace = WorkspaceStore(tmp_path).create("Housing example", workbook())
    with TestClient(create_app()) as client:
        session = client.get("/workspace-research/session")
        assert session.status_code == 200
        token = session.json()["token"]
        headers = {"X-Workspace-Token": token}
        assert client.get("/workspace-research/api/workspaces").status_code == 401
        response = client.get("/workspace-research/api/workspaces", headers=headers)
        assert [w["id"] for w in response.json()] == [workspace["id"]]
        assert client.get("/api/demo").status_code == 200
        assert client.get("/health").status_code == 200
        assert client.get("/workspace-research/").status_code == 200
        assert 'const apiRoot="/workspace-research"' in client.get("/workspace-research/").text


def test_mounted_session_rejects_foreign_origin(monkeypatch, tmp_path):
    from app.main import create_app

    monkeypatch.setenv("LEXCHECK_WORKSPACE_RESEARCH_ENABLED", "1")
    monkeypatch.setenv("LEXCHECK_WORKSPACE_DIR", str(tmp_path))
    with TestClient(create_app()) as client:
        assert (
            client.get(
                "/workspace-research/session", headers={"Origin": "https://elsewhere.example"}
            ).status_code
            == 403
        )


def test_workspace_store_rejects_held_out_location_before_creating_it(tmp_path):
    forbidden = tmp_path / "test_final"
    with pytest.raises(ValueError, match="Held-out"):
        WorkspaceStore(forbidden)
    assert not forbidden.exists()
