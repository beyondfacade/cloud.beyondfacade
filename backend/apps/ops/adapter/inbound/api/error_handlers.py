from fastapi import Request
from fastapi.responses import JSONResponse

from apps.ops.app.errors import CollectorRunning, OpsError, UnknownCollector

_STATUS: dict[type[OpsError], int] = {
    UnknownCollector: 404,
    CollectorRunning: 409,
}


async def ops_error_handler(request: Request, error: OpsError) -> JSONResponse:
    return JSONResponse(
        status_code=_STATUS.get(type(error), 400),
        content={"error": {"code": error.code, "message": error.message}},
    )
