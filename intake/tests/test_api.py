"""Live API acceptance using the committed, human-reviewed engine and catalog."""

from copy import deepcopy

from intake.fixtures import load_demo
from intake.tests.test_runtime import login


def post_ok(api, path, payload, status=200):
    response = api.post(path, json=payload)
    assert response.status_code == status, response.text
    return response.json()


def run_dossier_flow(api):
    session = login(api)
    api.headers["Authorization"] = "Bearer " + session["token"]
    bundle = load_demo()
    original = post_ok(api, "/api/check", bundle.request.model_dump(mode="json"))
    assert original["mode"] == "live"
    assert {"R-01", "R-02", "R-03"} <= set(original["rules_checked"])
    assert len(original["rules_checked"]) == len(original["rule_snapshots"])
    assert original["status"] == "no_issue_found" and original["findings"] == []
    event = bundle.event.model_dump(mode="json")
    changed = post_ok(api, "/api/changes", event)
    assert len(changed["queue"]) == 2
    assert post_ok(api, "/api/changes", event) == changed
    revised = [
        post_ok(api, "/api/rechecks", {"item_id": item["id"], "llm_mode": "off"})
        for item in changed["queue"]
    ]
    assert sum(bool(result["findings"]) for result in revised) == 1
    finding_check = next(result for result in revised if result["findings"])
    finding = finding_check["findings"][0]
    assert finding["rule_id"] == "R-02"
    assert finding_check["validator_rejections"] == []
    assert finding_check["parent_check_id"] == original["id"]
    decision_request = {
        "check_id": finding_check["id"],
        "finding_id": finding["id"],
        "action": "confirm",
        "actor": "reviewer",
        "note": "Synthetic human review.",
    }
    confirmed = post_ok(api, "/api/decisions", decision_request, 201)
    assert confirmed["task_status"] == "open"
    assert confirmed["actor_user_id"] == "U-MANAGER"
    rejected = api.post(
        "/api/decisions",
        json={
            **decision_request,
            "action": "close",
            "closure_check_id": original["id"],
        },
    )
    assert rejected.status_code == 409
    target = next(
        v for v in finding_check["snapshot"]["versions"] if v["id"] == finding["record_version_id"]
    )
    fixed = deepcopy(target)
    fixed.update(id="RV-API-FIX-v2", version=target["version"] + 1, supersedes=target["id"])
    quote = finding["evidence"][0]["quote"]
    fixed["text"] = fixed["text"].replace(quote, "")
    fixed["uses"] = [use for use in fixed["uses"] if use != quote]
    revision = post_ok(
        api,
        "/api/changes",
        {
            "id": "EV-API-MANUAL-FIX",
            "kind": "record_changed",
            "record_id": target["record_id"],
            "previous_version_id": target["id"],
            "new_version": fixed,
            "received_at": "2026-10-31T09:00:00Z",
        },
    )
    item = next(q for q in revision["queue"] if q["previous_check_id"] == finding_check["id"])
    fresh = post_ok(api, "/api/rechecks", {"item_id": item["id"], "llm_mode": "off"})
    assert fresh["findings"] == [] and fresh["status"] == "no_issue_found"
    assert fresh["parent_check_id"] == finding_check["id"]
    closed = post_ok(
        api,
        "/api/decisions",
        {
            **decision_request,
            "action": "close",
            "closure_check_id": fresh["id"],
        },
        201,
    )
    assert closed["task_status"] == "closed"
    history = api.get("/api/history").json()
    assert next(c for c in history["checks"] if c["id"] == original["id"]) == original
    assert next(d for d in history["decisions"] if d["id"] == confirmed["id"]) == confirmed
    return original, finding_check, fresh


def test_live_pipeline_uses_rule_engine(api):
    original, finding_check, fresh = run_dossier_flow(api)
    assert original["findings"] != finding_check["findings"]
    assert fresh["findings"] != finding_check["findings"]


def test_demo_source_inventory_matches_the_actual_engine(api):
    bundle = api.get("/api/demo").json()
    assert {"R-01", "R-02", "R-03"} <= {rule["id"] for rule in bundle["rules"]}
    assert all(
        rule["enabled"] and rule["verification_status"] == "verified" for rule in bundle["rules"]
    )
    assert {rule["clause_version_id"] for rule in bundle["rules"]} == {
        clause["id"] for clause in bundle["clauses"]
    }


def test_closure_requires_reviewer_session(api):
    assert (
        api.post(
            "/api/decisions",
            json={
                "check_id": "CHK-unknown",
                "finding_id": "F-unknown",
                "action": "confirm",
                "actor": "reviewer",
                "note": "Synthetic",
            },
        ).status_code
        == 401
    )
