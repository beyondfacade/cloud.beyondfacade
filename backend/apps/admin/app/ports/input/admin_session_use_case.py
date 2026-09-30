"""Driving Port — 회원 로그인 세션 (비밀번호·공개 가입·구글)."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto, GoogleLoginStartDto, LoginResultDto
from apps.admin.domain.entities.client_entity import Client


class AdminSessionUseCase(ABC):
    @abstractmethod
    def myself(self) -> AdminPrincipalDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def login(self, login_id: str, password: str, client: Client) -> LoginResultDto:
        """login_id는 계정명 또는 이메일. 실패는 InvalidCredentials, 같은 IP 실패 누적은 LoginThrottled
        (화이트리스트 IP·디바이스는 제한하지 않는다)."""

    @abstractmethod
    def signup(self, username: str, email: str, password: str, client: Client) -> LoginResultDto:
        """일반(viewer) 계정을 만들고 바로 로그인. InvalidUsername·InvalidEmail·WeakPassword·UsernameTaken·EmailTaken,
        같은 IP 가입 누적은 LoginThrottled."""

    @abstractmethod
    def google_enabled(self) -> bool: ...

    @abstractmethod
    def begin_google_login(self) -> GoogleLoginStartDto:
        """구글 동의 화면 주소와 콜백에서 대조할 state·PKCE verifier. 설정이 없으면 GoogleNotConfigured."""

    @abstractmethod
    def finish_google_login(
        self, code: str, state: str, expected_state: str | None, code_verifier: str, client: Client
    ) -> LoginResultDto:
        """state 불일치는 OAuthStateMismatch, 교환 실패는 GoogleLoginFailed, 미확인 이메일은 GoogleEmailUnverified.
        처음 보는 구글 계정은 일반으로 가입시키고, 이메일이 다른 계정과 겹치면 EmailTaken."""

    @abstractmethod
    def logout(self, token: str) -> None: ...

    @abstractmethod
    def authenticate(self, token: str) -> AdminPrincipalDto | None:
        """쿠키 토큰 → 회원. 만료·비활성·없는 세션이면 None."""

    @abstractmethod
    def change_password(
        self, principal: AdminPrincipalDto, token: str, current_password: str, new_password: str, ip: str | None
    ) -> None:
        """현재 비밀번호가 틀리면 WrongPassword, 규칙 위반은 WeakPassword. 성공하면 지금 세션만 남기고 끊는다.
        비밀번호가 없는 구글 전용 계정은 현재 비밀번호 없이 처음 설정한다."""

    @abstractmethod
    def change_username(self, principal: AdminPrincipalDto, username: str, ip: str | None) -> AdminPrincipalDto:
        """내 계정명을 바꾼다 — 세션은 유지. InvalidUsername·UsernameTaken, 지금과 같으면 그대로 돌려준다."""
