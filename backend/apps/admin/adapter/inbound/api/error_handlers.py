from fastapi import Request
from fastapi.responses import JSONResponse

from apps.admin.app.errors import (
    AdminError,
    ForbiddenRole,
    InvalidCredentials,
    InvalidIp,
    IpBlockNotFound,
    LoginThrottled,
    SelfBlock,
    Unauthenticated,
)

_STATUS: dict[type[AdminError], int] = {
    InvalidCredentials: 401,
    Unauthenticated: 401,
    ForbiddenRole: 403,
    IpBlockNotFound: 404,
    InvalidIp: 400,
    SelfBlock: 400,
    LoginThrottled: 429,
}


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


async def admin_error_handler(request: Request, error: AdminError) -> JSONResponse:
    return JSONResponse(status_code=_STATUS.get(type(error), 400), content=error_body(error.code, error.message))
