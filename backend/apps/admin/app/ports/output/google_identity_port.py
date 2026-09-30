"""Driven Port — 구글 OAuth(OpenID Connect) 인가 코드 흐름."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.google_identity_dto import GoogleIdentityDto


class GoogleIdentityPort(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        """클라이언트 ID·비밀이 있어야 구글 로그인을 연다."""

    @abstractmethod
    def authorization_url(self, state: str, code_challenge: str) -> str:
        """사용자를 보낼 구글 동의 화면 주소 — PKCE S256."""

    @abstractmethod
    def exchange(self, code: str, code_verifier: str) -> GoogleIdentityDto | None:
        """인가 코드 → 검증된 신원. 교환 실패·믿을 수 없는 토큰이면 None."""
