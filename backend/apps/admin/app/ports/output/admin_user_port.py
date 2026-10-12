from abc import ABC, abstractmethod
from datetime import datetime

from apps.admin.domain.entities.admin_user_entity import AdminUser


class AdminUserRepositoryPort(ABC):
    @abstractmethod
    def get_by_username(self, username: str) -> AdminUser | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> AdminUser | None:
        """email은 소문자로 맞춘 값으로 넘긴다."""

    @abstractmethod
    def get_by_google_sub(self, google_sub: str) -> AdminUser | None: ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> AdminUser | None: ...

    @abstractmethod
    def save(self, user: AdminUser) -> AdminUser:
        """username 기준 생성 또는 비밀번호·역할·활성 갱신 — id가 채워진 엔티티 반환."""

    @abstractmethod
    def touch_login(self, user_id: int, at: datetime) -> None: ...

    @abstractmethod
    def list_all(self) -> list[AdminUser]:
        """계정명순 — 관리자 계정은 수십 개를 넘지 않아 전부 읽는다."""

    @abstractmethod
    def save_avatar(self, user_id: int, media_type: str, content: bytes) -> int:
        """사진을 갈아 끼우고 avatar_version을 1 올린다 — 새 버전 반환."""

    @abstractmethod
    def get_avatar(self, user_id: int) -> tuple[str, bytes] | None:
        """(media_type, content) — 없으면 None."""
