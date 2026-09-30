"""Driving Port — 관리자 계정 관리 (CLI 전용)."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto


class AdminUserUseCase(ABC):
    @abstractmethod
    def upsert(self, username: str, password: str, role: str) -> AdminPrincipalDto:
        """없으면 만들고, 있으면 비밀번호·역할을 바꾸고 다시 활성화한다."""
