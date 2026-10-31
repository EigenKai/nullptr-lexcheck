"""API owner initializes per-application state and authorization here."""

from fastapi import FastAPI, Header


def configure_app(app: FastAPI) -> None:
    app.state.bootstrap = True


def authorization_header(authorization: str | None = Header(default=None)) -> str | None:
    return authorization
