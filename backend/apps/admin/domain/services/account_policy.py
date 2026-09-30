"""관리자 계정 규칙 — 계정명·비밀번호 형식과 '운영 관리자가 한 명도 안 남는 변경' 금지."""

import re
from collections.abc import Iterable

from apps.admin.domain.entities.admin_user_entity import AdminRole, AdminUser

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256
_USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")


def username_problem(username: str) -> str | None:
    if _USERNAME.fullmatch(username):
        return None
    return "계정명은 영문 소문자·숫자로 시작하는 3~32자(소문자·숫자·. _ -)여야 합니다."


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"비밀번호는 {MAX_PASSWORD_LENGTH}자 이하여야 합니다."
    return None


def leaves_no_active_operator(users: Iterable[AdminUser], target: str, role: AdminRole, active: bool) -> bool:
    """target의 역할·활성 상태를 바꾼 뒤 활성 운영 관리자가 0명이 되면 True — 관제실이 잠긴다."""
    others = any(u.username != target and u.is_active and u.role is AdminRole.OPERATOR for u in users)
    return not others and not (active and role is AdminRole.OPERATOR)
