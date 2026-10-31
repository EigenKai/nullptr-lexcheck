from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from contracts.models import HealthResponse
from intake.router import router, runtime_mode

app = FastAPI(title="LexCheck", version="0.1.0")
app.include_router(router)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(mode=runtime_mode())


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": "invalid_request", "message": "Request does not match the contract."},
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    errors = {
        404: ("not_found", "Resource not found."),
        409: ("conflict", "Version or state conflict."),
        503: ("not_ready", "Feature implementation pending."),
    }
    code, message = errors.get(
        exc.status_code, ("invalid_request", "Request could not be processed.")
    )
    return JSONResponse(status_code=exc.status_code, content={"code": code, "message": message})


UI_DIST = Path(__file__).resolve().parents[1] / "ui/dist"
if UI_DIST.is_dir():
    app.mount("/", StaticFiles(directory=UI_DIST, html=True), name="ui")
