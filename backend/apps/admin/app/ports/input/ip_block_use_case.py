"""Driving Port — 관리자 경로 IP 차단."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.dtos.ip_block_dto import IpBlockDto


class IpBlockUseCase(ABC):
    @abstractmethod
    def myself(self) -> IpBlockDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def list_active(self) -> list[IpBlockDto]: ...

    @abstractmethod
    def block(
        self, ip: str, reason: str, ttl_minutes: int | None, actor: AdminPrincipalDto, actor_ip: str | None
    ) -> IpBlockDto:
        """형식이 틀린 IP는 InvalidIp, 자기 IP 차단은 SelfBlock. 이미 차단된 IP는 사유·만료 갱신."""

    @abstractmethod
    def unblock(self, ip: str, actor: AdminPrincipalDto, actor_ip: str | None) -> None:
        """없는 IP면 IpBlockNotFound."""

    @abstractmethod
    def is_blocked(self, ip: str | None) -> bool: ...

    @abstractmethod
    def enforce_auto_defense(self, ip: str | None) -> IpBlockDto | None:
        """자동 방어가 켜져 있고 규칙 임계치에 닿았으면 그 IP를 기한부로 차단한다. 차단했으면 그 차단을 돌려준다.
        루프백·이미 차단 중인 IP는 건드리지 않는다."""
