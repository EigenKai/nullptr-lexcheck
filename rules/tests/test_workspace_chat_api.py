"""Workspace token, chat flag, persistence and injected-model API flow."""

from fastapi.testclient import TestClient

from rules.tests.test_workspace_chat import Client
from rules.workspaces import WorkspaceStore


def test_chat_routes_use_real_conversations_and_workspace_scope(tmp_path, monkeypatch):
    from rules.workspace_app import create_app

    monkeypatch.setenv("LEXCHECK_WORKSPACE_CHAT_ENABLED", "1")
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic")
    doc = store.add_document(workspace["id"], "business", "company.txt", "sửa chữa xe đạp".encode())
    store.document_context(workspace["id"], doc["id"], True)
    app = create_app(tmp_path, enabled=True, chat_client_factory=lambda workspace_id: Client())
    with TestClient(app) as client:
        assert client.get("/session").json()["chat_enabled"] is True
        headers = {"X-Workspace-Token": app.state.token}
        base = f"/api/workspaces/{workspace['id']}/conversations"
        assert client.post(base, json={}).status_code == 401
        thread = client.post(base, headers=headers, json={}).json()
        reply = client.post(
            base + f"/{thread['id']}/messages",
            headers=headers,
            json={"question": "Doanh nghiệp làm gì?"},
        )
        assert reply.status_code == 200
        assert reply.json()["citations"][0]["document_id"] == doc["id"]
        assert client.get(base, headers=headers).json()[0]["turn_count"] == 1
        assert (
            client.get(base + f"/{thread['id']}", headers=headers).json()["turns"][0]["question"]
            == "Doanh nghiệp làm gì?"
        )
        other = store.create_blank("Other")
        assert (
            client.get(
                f"/api/workspaces/{other['id']}/conversations/{thread['id']}", headers=headers
            ).status_code
            == 404
        )


def test_disabled_chat_never_calls_model(tmp_path, monkeypatch):
    from rules.workspace_app import create_app

    monkeypatch.delenv("LEXCHECK_WORKSPACE_CHAT_ENABLED", raising=False)
    store = WorkspaceStore(tmp_path)
    workspace = store.create_blank("Synthetic")

    def forbidden(workspace_id):
        raise AssertionError("Model must not be called")

    app = create_app(tmp_path, enabled=True, chat_client_factory=forbidden)
    with TestClient(app) as client:
        headers = {"X-Workspace-Token": app.state.token}
        assert client.get("/session").json()["chat_enabled"] is False
        base = f"/api/workspaces/{workspace['id']}/conversations"
        thread = client.post(base, headers=headers, json={}).json()
        assert (
            client.post(
                base + f"/{thread['id']}/messages", headers=headers, json={"question": "Hello"}
            ).status_code
            == 503
        )
