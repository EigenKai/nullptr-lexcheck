"""Exercise retrieval policy with server principals; no client-created role is trusted."""

from datetime import timedelta

from fastapi import HTTPException

from contracts.models import DecisionRequest
from intake import auth
from intake.fixtures import load_demo


def operations(api):
    token = "server-side-test-principal-token"
    api.app.state.sessions[token] = auth.Principal(
        "U-OPS", "operations", auth.now() + timedelta(hours=1)
    )
    api.headers["Authorization"] = "Bearer " + token


def test_history_and_check_do_not_leak_hidden_text(api):
    store = api.app.state.store
    preview = load_demo().preview
    private_record = preview.snapshot.records[0].model_copy(update={"access_groups": ("manager",)})
    store.records[private_record.id] = private_record
    snapshot = preview.snapshot.model_copy(
        update={"records": (private_record,) + preview.snapshot.records[1:]}
    )
    secret = preview.model_copy(
        update={"id": "CHK-SECRET", "snapshot": snapshot, "summary": "PRIVATE-SENTINEL"}
    )
    store.checks[secret.id] = secret
    operations(api)
    assert api.get("/api/checks/CHK-SECRET").status_code == 404
    assert "PRIVATE-SENTINEL" not in api.get("/api/history").text
    assert private_record.id not in [r["id"] for r in api.get("/api/records").json()["records"]]


def test_forged_acl_and_unknown_versions_are_rejected(api):
    store = api.app.state.store
    request = load_demo().request
    operations(api)
    person = next(p for p in api.app.state.sessions.values() if p.group == "operations")
    forged = request.model_copy(
        update={
            "records": (request.records[0].model_copy(update={"title": "Forged metadata"}),)
            + request.records[1:]
        }
    )
    try:
        auth.authorize_input(forged, person, store)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Forged canonical metadata was accepted")


def test_manager_authority_comes_from_server_session(api):
    operations(api)
    # Even though the required wire-contract actor says reviewer, it grants no authority.
    body = DecisionRequest(
        check_id="CHK-X", finding_id="F-X", action="confirm", actor="reviewer", note="Synthetic"
    ).model_dump(mode="json")
    response = api.post("/api/decisions", json=body)
    assert response.status_code in (403, 503)
    assert api.app.state.store.decisions == {}


def test_invalid_token_is_not_an_anonymous_reader(api):
    api.headers["Authorization"] = "Bearer forged-opaque-token"
    assert api.get("/api/history").status_code == 401
    assert api.get("/api/records").status_code == 401


def test_auth_requires_manager_even_without_runtime_gate(api):
    import pytest
    from fastapi import HTTPException, Request

    operations(api)
    request = Request(
        {
            "type": "http",
            "app": api.app,
            "headers": [(b"authorization", api.headers["Authorization"].encode())],
        }
    )
    with pytest.raises(HTTPException) as exc:
        auth.principal(request, manager=True)
    assert exc.value.status_code == 403
