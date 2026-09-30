"""Driving Port — 관리자 계정 관리 (인사팀 화면 + CLI)."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.dtos.admin_user_dto import AdminSessionInfoDto, AdminUserDto


class AdminUserUseCase(ABC):
    @abstractmethod
    def myself(self) -> AdminUserDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def upsert(self, username: str, password: str, role: str) -> AdminPrincipalDto:
        """CLI 전용 — 없으면 만들고, 있으면 비밀번호·역할을 바꾸고 다시 활성화한다."""

    @abstractmethod
    def list_users(self, q: str, role: str | None, status: str) -> list[AdminUserDto]:
        """q는 계정명 부분 일치(대소문자 무시), status는 all | active | suspended."""

    @abstractmethod
    def create(
        self, actor: AdminPrincipalDto, username: str, role: str, password: str, ip: str | None
    ) -> AdminUserDto:
        """InvalidUsername·WeakPassword·UsernameTaken."""

    @abstractmethod
    def change_role(self, actor: AdminPrincipalDto, username: str, role: str, ip: str | None) -> AdminUserDto:
        """자기 역할은 SelfChange, 활성 운영자가 0명이 되면 LastOperator."""

    @abstractmethod
    def set_active(self, actor: AdminPrincipalDto, username: str, active: bool, ip: str | None) -> AdminUserDto:
        """정지하면 그 계정의 세션을 모두 끊는다. 자기 자신은 SelfChange."""

    @abstractmethod
    def reset_password(self, actor: AdminPrincipalDto, username: str, password: str, ip: str | None) -> None:
        """남의 비밀번호를 새로 정하고 기존 세션을 끊는다. 내 비밀번호는 현재 비밀번호 확인을 거치는 쪽으로."""

    @abstractmethod
    def sessions(
        self, actor: AdminPrincipalDto, username: str, current_token: str | None
    ) -> list[AdminSessionInfoDto]:
        """본인 또는 운영 관리자만 — 아니면 ForbiddenRole."""

    @abstractmethod
    def revoke_sessions(
        self, actor: AdminPrincipalDto, username: str, current_token: str | None, ip: str | None
    ) -> int:
        """그 계정의 세션을 끊는다 — 본인이면 지금 쓰는 세션은 남긴다."""
