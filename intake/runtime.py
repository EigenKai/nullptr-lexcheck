"""API owner initializes per-application state and authorization here."""

import os
from pathlib import Path

from fastapi import FastAPI, Header

from intake.store import Store


def configure_app(app: FastAPI) -> None:
    app.state.store = Store(Path(os.getenv("LEXCHECK_STATE_FILE", "cache/demo-state.json")))
    app.state.sessions = {}


def authorization_header(authorization: str | None = Header(default=None)) -> str | None:
    return authorization
