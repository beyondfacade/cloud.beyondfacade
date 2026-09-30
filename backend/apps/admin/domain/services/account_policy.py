"""회원 계정 규칙 — 계정명·이메일·비밀번호 형식과 '관리자가 한 명도 안 남는 변경' 금지."""

import re
from collections.abc import Iterable, Iterator
from itertools import count

from apps.admin.domain.entities.admin_user_entity import AdminRole, AdminUser

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256
MAX_EMAIL_LENGTH = 254
_USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_NOT_USERNAME_CHARS = re.compile(r"[^a-z0-9._-]+")
_USERNAME_BASE_LENGTH = 28  # 겹칠 때 붙는 번호 자리를 남긴다


def username_problem(username: str) -> str | None:
    if _USERNAME.fullmatch(username):
        return None
    return "계정명은 영문 소문자·숫자로 시작하는 3~32자(소문자·숫자·. _ -)여야 합니다."


def normalize_email(email: str) -> str:
    return email.strip().lower()


def email_problem(email: str) -> str | None:
    if len(email) <= MAX_EMAIL_LENGTH and _EMAIL.fullmatch(email):
        return None
    return "이메일 형식이 올바르지 않습니다."


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"비밀번호는 {MAX_PASSWORD_LENGTH}자 이하여야 합니다."
    return None


def username_candidates(email: str) -> Iterator[str]:
    """구글 가입 계정명 후보 — 이메일 앞부분을 계정명 규칙에 맞게 다듬고, 겹치면 2, 3, …을 붙인다."""
    local = email.split("@", 1)[0].lower()
    base = _NOT_USERNAME_CHARS.sub(".", local).strip("._-")[:_USERNAME_BASE_LENGTH].strip("._-")
    if not base:
        base = "user"
    elif len(base) < 3:
        base = f"{base}.user"
    yield base
    for n in count(2):
        yield f"{base}{n}"


def leaves_no_active_operator(users: Iterable[AdminUser], target: str, role: AdminRole, active: bool) -> bool:
    """target의 등급·활성 상태를 바꾼 뒤 활성 관리자가 0명이 되면 True — 관제실 쓰기가 잠긴다."""
    others = any(u.username != target and u.is_active and u.role is AdminRole.OPERATOR for u in users)
    return not others and not (active and role is AdminRole.OPERATOR)
