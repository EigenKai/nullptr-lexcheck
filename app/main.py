from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from contracts.models import HealthResponse
from intake.layer_routes import router as layer_router
from intake.router import router, runtime_mode
from intake.runtime import authorization_header, configure_app


def health():
    return HealthResponse(mode=runtime_mode())


async def invalid_request(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": "invalid_request", "message": "Request does not match the contract."},
    )


async def http_error(request: Request, exc: HTTPException):
    errors = {
        401: ("unauthenticated", "Demo session required."),
        403: ("forbidden", "Action not permitted."),
        404: ("not_found", "Resource not found."),
        409: ("conflict", "Version or state conflict."),
        503: ("not_ready", "Feature implementation pending."),
    }
    code, message = errors.get(
        exc.status_code, ("invalid_request", "Request could not be processed.")
    )
    if exc.detail == "feature_disabled":
        code, message = "feature_disabled", "Feature is disabled."
    return JSONResponse(status_code=exc.status_code, content={"code": code, "message": message})


def create_app() -> FastAPI:
    application = FastAPI(
        title="LexCheck", version="0.1.0", dependencies=[Depends(authorization_header)]
    )
    configure_app(application)
    application.include_router(router)
    application.include_router(layer_router)
    application.add_api_route("/health", health, response_model=HealthResponse, methods=["GET"])
    application.add_exception_handler(RequestValidationError, invalid_request)
    application.add_exception_handler(HTTPException, http_error)
    ui_dist = Path(__file__).resolve().parents[1] / "ui/dist"
    if ui_dist.is_dir():
        application.mount("/", StaticFiles(directory=ui_dist, html=True), name="ui")
    return application


app = create_app()
