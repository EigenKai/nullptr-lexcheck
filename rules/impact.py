"""Pure, deterministic impact queues and immutable record-change snapshots.

No store, clock, model or rule catalog is consulted. The caller authorizes the
event/checks, persists queue items, and performs the actual fresh evaluation.
"""

import hashlib
import json

from contracts.models import ChangeEvent, CheckRequest, CheckResult, RecheckItem

_CONTEXT_KINDS = {
    "dossier",
    "scientific_evidence",
    "ad_confirmation",
    "registration_receipt",
    "label",
    "evidence_index",
}


def _identity(event_id, check_id, target_id):
    raw = json.dumps([event_id, check_id, target_id], separators=(",", ":")).encode()
    return "RQ-" + hashlib.sha256(raw).hexdigest()[:32]


def _depends_on(target_id, previous_id, versions):
    pending, seen = [target_id], set()
    while pending:
        current = pending.pop()
        if current == previous_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        version = versions.get(current)
        if version:
            pending.extend(version.reference_ids)
    return False


def _validate_change(snapshot, event):
    event = ChangeEvent.model_validate(event.model_dump(mode="json"))
    records = {record.id: record for record in snapshot.records}
    versions = {version.id: version for version in snapshot.versions}
    if event.record_id not in records:
        raise ValueError("Changed record metadata is missing from this snapshot.")
    previous = versions.get(event.previous_version_id)
    if previous and (
        previous.record_id != event.record_id or event.new_version.version != previous.version + 1
    ):
        raise ValueError("Event predecessor or version increment does not match the snapshot.")
    existing = versions.get(event.new_version.id)
    if existing and existing != event.new_version:
        raise ValueError("New version ID conflicts with immutable snapshot content.")
    if any(
        version.record_id == event.record_id
        and version.version == event.new_version.version
        and version.id != event.new_version.id
        for version in snapshot.versions
    ):
        raise ValueError("Record version number already has another immutable ID.")
    return event, records, versions


def enqueue(event: ChangeEvent, checks: tuple[CheckResult, ...]) -> tuple[RecheckItem, ...]:
    """Queue every affected target, including clean checks; never cross products.

    A missing reference path falls back to the changed record's same product.
    Its record metadata must be in the check snapshot: ChangeEvent deliberately
    carries no company/product fields, so absent scope is not guessed.
    """
    unique = {}
    for check in checks:
        if check.id in unique and unique[check.id] != check:
            raise ValueError("Check ID has conflicting immutable snapshots.")
        unique[check.id] = check
    scopes = {
        (record.company_id, record.product_id)
        for check in unique.values()
        for record in check.snapshot.records
        if record.id == event.record_id
    }
    if len(scopes) > 1:
        raise ValueError("Changed record ID has ambiguous company/product scope.")
    items = []
    for check in unique.values():
        snapshot = check.snapshot
        if not any(record.id == event.record_id for record in snapshot.records):
            continue
        current_event, records, versions = _validate_change(snapshot, event)
        source = records[event.record_id]
        if snapshot.profile.company_id != source.company_id:
            continue
        for target_id in snapshot.target_version_ids:
            target = records[versions[target_id].record_id]
            if target.company_id != source.company_id or target.product_id != source.product_id:
                continue
            if target.id == source.id and target_id != event.previous_version_id:
                continue
            if (
                target.id != source.id
                and current_event.new_version.id in snapshot.context_version_ids
            ):
                continue
            direct = _depends_on(target_id, event.previous_version_id, versions)
            items.append(
                RecheckItem(
                    id=_identity(event.id, check.id, target_id),
                    event_id=event.id,
                    previous_check_id=check.id,
                    target_version_id=target_id,
                    reason="direct_dependency" if direct else "product_fallback",
                    status="queued",
                )
            )
    return tuple(sorted(items, key=lambda item: (item.previous_check_id, item.target_version_id)))


def apply_event(snapshot: CheckRequest, event: ChangeEvent) -> CheckRequest:
    """Append supplied content and explicitly select it for the fresh recheck.

    Old versions and their reference_ids stay byte-for-byte unchanged. Choosing
    this event is the selection action; no received-date/latest-version heuristic
    chooses a source. The caller retains the prior CheckResult as parent/history.
    """
    event, records, versions = _validate_change(snapshot, event)
    targets = tuple(
        event.new_version.id if target == event.previous_version_id else target
        for target in snapshot.target_version_ids
    )
    contexts = []
    for version_id in snapshot.context_version_ids:
        selected = (
            event.new_version.id
            if versions[version_id].record_id == event.record_id
            else version_id
        )
        if selected not in targets and selected not in contexts:
            contexts.append(selected)
    source = records[event.record_id]
    same_product_target = any(
        records[versions[target].record_id].product_id == source.product_id
        and versions[target].record_id != source.id
        for target in snapshot.target_version_ids
    )
    if (
        source.kind in _CONTEXT_KINDS
        and same_product_target
        and event.new_version.id not in targets
        and event.new_version.id not in contexts
    ):
        contexts.append(event.new_version.id)
    new_versions = snapshot.versions
    if event.new_version.id not in versions:
        new_versions += (event.new_version,)
    return CheckRequest.model_validate(
        {
            **snapshot.model_dump(mode="json"),
            "versions": [version.model_dump(mode="json") for version in new_versions],
            "target_version_ids": targets,
            "context_version_ids": tuple(contexts),
        }
    )
