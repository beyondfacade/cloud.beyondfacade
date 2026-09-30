"""Driving Port — 보안 동작 스위치 (자동 방어 켜기·끄기)."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.dtos.security_setting_dto import AutoDefenseDto


class SecuritySettingUseCase(ABC):
    @abstractmethod
    def myself(self) -> AutoDefenseDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def auto_defense(self) -> AutoDefenseDto:
        """현재 상태와 자동 차단 규칙."""

    @abstractmethod
    def set_auto_defense(self, enabled: bool, actor: AdminPrincipalDto, actor_ip: str | None) -> AutoDefenseDto:
        """켜고 끈 일은 감사 로그에 남는다."""
