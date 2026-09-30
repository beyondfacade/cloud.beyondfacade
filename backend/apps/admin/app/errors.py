"""admin BC 애플리케이션 오류 — HTTP 상태 매핑은 inbound 어댑터(error_handlers)가 한다."""


class AdminError(Exception):
    code = "ADMIN_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidCredentials(AdminError):
    code = "INVALID_CREDENTIALS"


class LoginThrottled(AdminError):
    code = "TOO_MANY_ATTEMPTS"


class Unauthenticated(AdminError):
    code = "UNAUTHENTICATED"


class ForbiddenRole(AdminError):
    code = "FORBIDDEN_ROLE"


class InvalidIp(AdminError):
    code = "INVALID_IP"


class SelfBlock(AdminError):
    code = "SELF_BLOCK"


class IpBlockNotFound(AdminError):
    code = "IP_BLOCK_NOT_FOUND"
