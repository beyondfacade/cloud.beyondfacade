import ipaddress
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.dtos.ip_block_dto import IpBlockDto
from apps.admin.app.errors import InvalidIp, IpBlockNotFound, SelfBlock
from apps.admin.app.ports.input.ip_block_use_case import IpBlockUseCase
from apps.admin.app.ports.output.admin_user_port import AdminUserRepositoryPort
from apps.admin.app.ports.output.ip_block_port import IpBlockRepositoryPort
from apps.admin.domain.entities.ip_block_entity import IpBlock


class IpBlockInteractor(IpBlockUseCase):
    def __init__(
        self,
        ip_blocks: IpBlockRepositoryPort,
        users: AdminUserRepositoryPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._ip_blocks = ip_blocks
        self._users = users
        self._clock = clock

    def myself(self) -> IpBlockDto:
        return IpBlockDto(
            ip="192.0.2.1", reason="ip_block 배선 검증", created_at=datetime(2026, 9, 29, tzinfo=UTC),
            expires_at=None, created_by="myself",
        )

    def list_active(self) -> list[IpBlockDto]:
        return [self._to_dto(block) for block in self._ip_blocks.list_active(self._clock())]

    def block(
        self, ip: str, reason: str, ttl_minutes: int | None, actor: AdminPrincipalDto, actor_ip: str | None
    ) -> IpBlockDto:
        try:
            normalized = str(ipaddress.ip_address(ip.strip()))
        except ValueError as error:
            raise InvalidIp(f"IP 주소 형식이 아닙니다: {ip}") from error
        if normalized == actor_ip:
            raise SelfBlock("지금 접속 중인 내 IP는 차단할 수 없습니다.")
        now = self._clock()
        block = IpBlock(
            ip=normalized,
            reason=reason.strip() or "수동 차단",
            created_at=now,
            expires_at=now + timedelta(minutes=ttl_minutes) if ttl_minutes else None,
            created_by=actor.id,
        )
        self._ip_blocks.save(block)
        return self._to_dto(block)

    def unblock(self, ip: str) -> None:
        if not self._ip_blocks.delete(ip):
            raise IpBlockNotFound(f"차단 목록에 없는 IP입니다: {ip}")

    def is_blocked(self, ip: str | None) -> bool:
        if ip is None:
            return False
        block = self._ip_blocks.get(ip)
        return block is not None and block.is_active(self._clock())

    def _to_dto(self, block: IpBlock) -> IpBlockDto:
        actor = self._users.get_by_id(block.created_by) if block.created_by else None
        return IpBlockDto(
            ip=block.ip,
            reason=block.reason,
            created_at=block.created_at,
            expires_at=block.expires_at,
            created_by=actor.username if actor else None,
        )
