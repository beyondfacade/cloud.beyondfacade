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


class InvalidAccessRule(AdminError):
    code = "INVALID_ACCESS_RULE"


class AccessRuleExists(AdminError):
    code = "ACCESS_RULE_EXISTS"


class AccessRuleNotFound(AdminError):
    code = "ACCESS_RULE_NOT_FOUND"


class AdminUserNotFound(AdminError):
    code = "ADMIN_USER_NOT_FOUND"


class UsernameTaken(AdminError):
    code = "USERNAME_TAKEN"


class InvalidUsername(AdminError, ValueError):
    code = "INVALID_USERNAME"


class WeakPassword(AdminError, ValueError):
    code = "WEAK_PASSWORD"


class WrongPassword(AdminError):
    """현재 비밀번호 확인 실패 — 401이 아니다(프론트가 세션 만료로 오인해 로그인으로 보내지 않게)."""

    code = "WRONG_PASSWORD"


class SelfChange(AdminError):
    code = "SELF_CHANGE"


class LastOperator(AdminError):
    code = "LAST_OPERATOR"


class InvalidEmail(AdminError, ValueError):
    code = "INVALID_EMAIL"


class EmailTaken(AdminError):
    """구글 로그인이 비밀번호 계정과 이메일이 겹쳐도 자동으로 잇지 않는다 — 가입 이메일은 확인되지 않은 값이라서."""

    code = "EMAIL_TAKEN"


class GoogleNotConfigured(AdminError):
    code = "GOOGLE_NOT_CONFIGURED"


class OAuthStateMismatch(AdminError):
    code = "OAUTH_STATE_MISMATCH"


class GoogleLoginFailed(AdminError):
    code = "GOOGLE_LOGIN_FAILED"


class GoogleEmailUnverified(AdminError):
    code = "GOOGLE_EMAIL_UNVERIFIED"
