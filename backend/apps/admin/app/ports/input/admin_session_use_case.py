"""Driving Port — 관리자 로그인 세션."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto, LoginResultDto


class AdminSessionUseCase(ABC):
    @abstractmethod
    def myself(self) -> AdminPrincipalDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def login(self, username: str, password: str, ip: str | None) -> LoginResultDto:
        """성공 시 세션 발급. 실패는 InvalidCredentials, 같은 IP 실패 누적은 LoginThrottled."""

    @abstractmethod
    def logout(self, token: str) -> None: ...

    @abstractmethod
    def authenticate(self, token: str) -> AdminPrincipalDto | None:
        """쿠키 토큰 → 관리자. 만료·비활성·없는 세션이면 None."""
