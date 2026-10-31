"""Pure record-change impact on synthetic company/product snapshots."""

from pathlib import Path

import pytest

from contracts.models import CheckRequest, CheckResult, DemoBundle


@pytest.fixture
def demo():
    return DemoBundle.model_validate_json(
        (Path(__file__).parents[2] / "data/fixtures/demo.json").read_text(encoding="utf-8")
    )


def prior(demo, *, target_ids=None, check_id="CHK-impact", request=None):
    snapshot = request or demo.request
    if target_ids is not None:
        snapshot = CheckRequest.model_validate(
            {**snapshot.model_dump(mode="json"), "target_version_ids": target_ids}
        )
    return CheckResult.model_validate(
        {
            **demo.preview.model_dump(mode="json"),
            "id": check_id,
            "snapshot": snapshot.model_dump(mode="json"),
        }
    )


def test_requeues_clean_prior_checks(demo):
    from rules.impact import enqueue

    check = prior(demo)
    assert not check.findings
    items = enqueue(demo.event, (check,))
    assert isinstance(items, tuple)
    assert {item.target_version_id for item in items} == {"RV-02-v1", "RV-03-v1"}
    assert all(
        item.event_id == demo.event.id
        and item.previous_check_id == check.id
        and item.status == "queued"
        for item in items
    )
    assert all(item.reason == "direct_dependency" for item in items)


def test_unrelated_product_is_excluded(demo):
    from rules.impact import enqueue

    check = prior(demo, target_ids=["RV-02-v1", "RV-03-v1", "RV-05-v1"])
    assert {item.target_version_id for item in enqueue(demo.event, (check,))} == {
        "RV-02-v1",
        "RV-03-v1",
    }


def test_old_snapshot_unchanged(demo):
    from rules.impact import apply_event

    before = demo.request.model_dump_json()
    fresh = apply_event(demo.request, demo.event)
    assert demo.request.model_dump_json() == before
    assert "RV-01-v1" in {version.id for version in fresh.versions}
    assert fresh.versions[-1] == demo.event.new_version
    assert fresh.context_version_ids == ("RV-01-v2", "RV-04-v1")
    assert fresh.target_version_ids == demo.request.target_version_ids
    assert fresh.versions[1].reference_ids == demo.request.versions[1].reference_ids
    assert apply_event(fresh, demo.event) == fresh


def test_two_targets_one_new_finding(demo):
    from rules.impact import apply_event, enqueue

    # This acceptance check proves the fresh inputs for the engine owner without
    # importing an unmerged engine or claiming pending catalog rules executed.
    items = enqueue(demo.event, (prior(demo),))
    assert len(items) == 2
    differences = []
    for item in items:
        fresh = apply_event(demo.request, demo.event)
        selected = {version.id: version for version in fresh.versions}
        target = selected[item.target_version_id]
        dossier = selected["RV-01-v2"]
        differences.append(set(target.uses) - set(dossier.uses))
    assert sum(bool(extra) for extra in differences) == 1
    assert set.union(*differences) == {"Hỗ trợ giảm cholesterol."}


def test_queue_is_deterministic_and_deduplicated(demo):
    from rules.impact import enqueue

    one = prior(demo, target_ids=["RV-02-v1"], check_id="CHK-one")
    two = prior(demo, target_ids=["RV-03-v1"], check_id="CHK-two")
    assert enqueue(demo.event, (one, two, one)) == enqueue(demo.event, (two, one))
    assert len({item.id for item in enqueue(demo.event, (one, two))}) == 2


def test_incomplete_reference_paths_fall_back_to_same_product(demo):
    from rules.impact import enqueue

    data = demo.request.model_dump(mode="json")
    for version in data["versions"]:
        version["reference_ids"] = []
    check = prior(
        demo, request=CheckRequest.model_validate(data), target_ids=["RV-02-v1", "RV-05-v1"]
    )
    items = enqueue(demo.event, (check,))
    assert len(items) == 1
    assert items[0].target_version_id == "RV-02-v1"
    assert items[0].reason == "product_fallback"


def test_transitive_dependency_is_detected(demo):
    from rules.impact import enqueue

    data = demo.request.model_dump(mode="json")
    data["versions"][1]["reference_ids"] = ["RV-04-v1"]
    data["versions"][3]["reference_ids"] = ["RV-01-v1"]
    check = prior(demo, request=CheckRequest.model_validate(data), target_ids=["RV-02-v1"])
    assert enqueue(demo.event, (check,))[0].reason == "direct_dependency"


def test_changed_target_is_retargeted_without_changing_old_references(demo):
    from rules.impact import apply_event, enqueue

    data = demo.request.model_dump(mode="json")
    data["target_version_ids"] = ["RV-01-v1"]
    data["context_version_ids"] = ["RV-04-v1"]
    snapshot = CheckRequest.model_validate(data)
    item = enqueue(demo.event, (prior(demo, request=snapshot),))[0]
    assert item.target_version_id == "RV-01-v1"
    fresh = apply_event(snapshot, demo.event)
    assert fresh.target_version_ids == ("RV-01-v2",)
    assert fresh.context_version_ids == ("RV-04-v1",)


def test_conflicting_or_invalid_event_never_mutates_snapshot(demo):
    from rules.impact import apply_event

    fresh = apply_event(demo.request, demo.event)
    collision = demo.event.model_copy(
        update={"new_version": demo.event.new_version.model_copy(update={"text": "conflicting"})}
    )
    with pytest.raises(ValueError):
        apply_event(fresh, collision)
    skipped_version = demo.event.model_copy(
        update={"new_version": demo.event.new_version.model_copy(update={"version": 3})}
    )
    with pytest.raises(ValueError):
        apply_event(demo.request, skipped_version)


def test_different_company_and_unknown_source_are_not_guessed(demo):
    from rules.impact import apply_event, enqueue

    data = demo.request.model_dump(mode="json")
    data["records"] = [record for record in data["records"] if record["id"] != "REC-01"]
    data["versions"] = [version for version in data["versions"] if version["record_id"] != "REC-01"]
    for version in data["versions"]:
        version["reference_ids"] = [ref for ref in version["reference_ids"] if ref != "RV-01-v1"]
    data["context_version_ids"] = ["RV-04-v1"]
    snapshot = CheckRequest.model_validate(data)
    assert enqueue(demo.event, (prior(demo, request=snapshot),)) == ()
    with pytest.raises(ValueError):
        apply_event(snapshot, demo.event)


def test_fallback_selects_new_context_when_dossier_was_not_selected(demo):
    from rules.impact import apply_event

    data = demo.request.model_dump(mode="json")
    data["context_version_ids"] = ["RV-04-v1"]
    fresh = apply_event(CheckRequest.model_validate(data), demo.event)
    assert fresh.context_version_ids == ("RV-04-v1", "RV-01-v2")
    assert fresh.review_date == demo.request.review_date


def test_already_refreshed_context_is_not_queued_again(demo):
    from rules.impact import apply_event, enqueue

    fresh = apply_event(demo.request, demo.event)
    assert enqueue(demo.event, (prior(demo, request=fresh),)) == ()


def test_same_company_other_product_is_excluded_even_with_bad_cross_reference(demo):
    from rules.impact import enqueue

    data = demo.request.model_dump(mode="json")
    data["versions"][-1]["reference_ids"] = ["RV-01-v1"]
    check = prior(demo, request=CheckRequest.model_validate(data), target_ids=["RV-05-v1"])
    assert enqueue(demo.event, (check,)) == ()


def test_ambiguous_company_scope_is_rejected(demo):
    from rules.impact import enqueue

    data = demo.request.model_dump(mode="json")
    data["profile"]["company_id"] = "CO-OTHER"
    for record in data["records"]:
        record["company_id"] = "CO-OTHER"
    other = prior(demo, request=CheckRequest.model_validate(data), check_id="CHK-other-company")
    with pytest.raises(ValueError, match="ambiguous"):
        enqueue(demo.event, (prior(demo), other))
