"""Driving Port — 디바이스·IP 화이트리스트/블랙리스트."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.access_rule_dto import AccessRuleDto, CurrentDeviceDto
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.domain.entities.client_entity import Client


class AccessRuleUseCase(ABC):
    @abstractmethod
    def myself(self) -> AccessRuleDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def list_active(self) -> list[AccessRuleDto]: ...

    @abstractmethod
    def current_device(self, client: Client) -> CurrentDeviceDto: ...

    @abstractmethod
    def create(
        self,
        policy: str,
        target: str,
        value: str,
        note: str,
        ttl_minutes: int | None,
        actor: AdminPrincipalDto,
        actor_client: Client,
    ) -> AccessRuleDto:
        """값 형식이 틀리거나 IP 블랙리스트면 InvalidAccessRule, 이미 있으면 AccessRuleExists,
        지금 쓰는 내 디바이스를 막으려 하면 SelfBlock."""

    @abstractmethod
    def delete(self, rule_id: int, actor: AdminPrincipalDto, actor_ip: str | None) -> None:
        """없는 id면 AccessRuleNotFound."""

    @abstractmethod
    def is_denied(self, client: Client) -> bool:
        """디바이스 블랙리스트에 걸리는지 — 보안 미들웨어가 매 관리자 요청마다 묻는다."""
