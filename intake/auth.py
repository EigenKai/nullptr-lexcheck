"""Synthetic demo principals. Permissions are resolved before retrieval."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request

from contracts.models import DemoSession


def now():
    return datetime.now(UTC)


@dataclass(frozen=True)
class Principal:
    user_id: str
    group: str
    expires_at: datetime


def issue(request: Request, user_id: str):
    from intake.features import feature_flags
    from intake.router import runtime_mode

    if user_id == "U-OPS" and not feature_flags(runtime_mode() == "live").layer3:
        raise HTTPException(404, "feature_disabled")
    group = "manager" if user_id == "U-MANAGER" else "operations"
    expiry = now() + timedelta(hours=2)
    token = secrets.token_urlsafe(32)
    with request.app.state.store.lock:
        request.app.state.sessions = {
            k: v for k, v in request.app.state.sessions.items() if v.expires_at > now()
        }
        request.app.state.sessions[token] = Principal(user_id, group, expiry)
    return DemoSession(user_id=user_id, group=group, token=token, expires_at=expiry)


def principal(request: Request, *, required=False, manager=False):
    from intake.features import feature_flags
    from intake.router import runtime_mode

    header = request.headers.get("Authorization", "")
    token = header[7:] if header.startswith("Bearer ") else ""
    session = request.app.state.sessions.get(token)
    if header and (session is None or session.expires_at <= now()):
        raise HTTPException(401, "unauthenticated")
    restricted = feature_flags(runtime_mode() == "live").layer3
    if (required or manager or restricted) and session is None:
        raise HTTPException(401, "unauthenticated")
    if manager and session.group != "manager":
        raise HTTPException(403, "forbidden")
    return session


def visible_record(record, person):
    return person is None or person.group == "manager" or person.group in record.access_groups


def visible_check(check, person, store):
    # Canonical ACL plus all nested snapshot records, not just the target.
    return all(
        visible_record(r, person)
        and r.id in store.records
        and visible_record(store.records[r.id], person)
        for r in check.snapshot.records
    )


def get_check(store, check_id, person):
    check = store.checks.get(check_id)
    if check is None or not visible_check(check, person, store):
        raise HTTPException(404, "not_found")
    return check


def authorize_input(snapshot, person, store):
    if person is None or person.group == "manager":
        return
    from intake.fixtures import load_demo

    if snapshot.profile != load_demo().request.profile:
        raise HTTPException(403, "forbidden")
    for record in snapshot.records:
        original = store.records.get(record.id)
        if original is None or not visible_record(original, person):
            raise HTTPException(404, "not_found")
        if record != original:
            raise HTTPException(403, "forbidden")
    if any(store.versions.get(v.id) != v for v in snapshot.versions):
        raise HTTPException(403, "forbidden")
