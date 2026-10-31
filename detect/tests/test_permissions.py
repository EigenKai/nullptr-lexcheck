from types import SimpleNamespace

from detect.candidates import CandidateBatch
from detect.client import ModelClient

ARGS = {"purpose": "permission-test", "payload": {}, "prompt": "test", "schema": CandidateBatch}


def make_client(directory, group="manager", **kwargs):
    return ModelClient(
        model="test",
        cache_dir=directory,
        user_id="U-test",
        group=group,
        acl_hash="acl-v1",
        transport=lambda **kw: SimpleNamespace(
            status="completed", output_parsed=CandidateBatch(candidates=())
        ),
        **kwargs,
    )


def test_cache_does_not_cross_groups(tmp_path):
    manager = make_client(tmp_path)
    cached = manager.generate(**ARGS, mode="live")
    assert manager.generate(**ARGS, mode="cache").status == "cached"
    ops = make_client(tmp_path, group="operations").generate(**ARGS, mode="cache")
    assert ops.status == "unavailable" and ops.key != cached.key


def test_pattern_changes_cache_key(tmp_path):
    first = make_client(tmp_path, pattern_version="PAT-v1").generate(**ARGS, mode="live")
    changed = make_client(tmp_path, pattern_version="PAT-v2").generate(**ARGS, mode="cache")
    assert first.key != changed.key and changed.status == "unavailable"


def test_revoked_access_rechecked_on_cache_hit(tmp_path):
    client = make_client(tmp_path)
    client.generate(**ARGS, mode="live")
    revoked = make_client(tmp_path, authorize=lambda payload: False)
    assert revoked.generate(**ARGS, mode="cache").error == "access_denied"


def test_group_cannot_read_private_snapshot(tmp_path, request_data):
    records = tuple(
        r.model_copy(update={"access_groups": ("manager",)}) for r in request_data.records
    )
    payload = {
        "request": request_data.model_copy(update={"records": records}).model_dump(mode="json")
    }
    client = make_client(tmp_path, group="operations")
    assert client.generate(**{**ARGS, "payload": payload}, mode="live").error == "access_denied"
    assert not list(tmp_path.iterdir())


def test_layer3_requires_server_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("LEXCHECK_LAYER3_ENABLED", "1")
    client = ModelClient(model="test", cache_dir=tmp_path)
    assert client.generate(**ARGS, mode="cache").error == "access_denied"


def test_acl_and_user_invalidate_cache(tmp_path):
    base = make_client(tmp_path).generate(**ARGS, mode="live")
    for scope in (
        {"user_id": "U-other", "acl_hash": "acl-v1"},
        {"user_id": "U-test", "acl_hash": "acl-v2"},
    ):
        client = ModelClient(model="test", cache_dir=tmp_path, group="manager", **scope)
        result = client.generate(**ARGS, mode="cache")
        assert result.status == "unavailable" and result.key != base.key
