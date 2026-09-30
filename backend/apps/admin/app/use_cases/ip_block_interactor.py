import ipaddress
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.dtos.ip_block_dto import IpBlockDto
from apps.admin.app.errors import InvalidIp, IpBlockNotFound, SelfBlock
from apps.admin.app.ports.input.ip_block_use_case import IpBlockUseCase
from apps.admin.app.ports.output.access_event_port import AccessEventRepositoryPort
from apps.admin.app.ports.output.access_rule_port import AccessRuleRepositoryPort
from apps.admin.app.ports.output.admin_audit_port import AdminAuditRepositoryPort
from apps.admin.app.ports.output.admin_user_port import AdminUserRepositoryPort
from apps.admin.app.ports.output.ip_block_port import IpBlockRepositoryPort
from apps.admin.app.ports.output.security_setting_port import SecuritySettingRepositoryPort
from apps.admin.app.use_cases.allow_list import is_allowed
from apps.admin.app.use_cases.audit_trail import audit_entry
from apps.admin.domain.entities.admin_audit_entity import AdminAudit, AuditAction
from apps.admin.domain.entities.client_entity import Client
from apps.admin.domain.entities.ip_block_entity import IpBlock
from apps.admin.domain.entities.security_setting_entity import AUTO_DEFENSE
from apps.admin.domain.services.auto_block_rules import (
    AUTO_BLOCK_ACTOR,
    AUTO_BLOCK_RULES,
    auto_block_exempt,
    is_auto_block,
)


class IpBlockInteractor(IpBlockUseCase):
    def __init__(
        self,
        ip_blocks: IpBlockRepositoryPort,
        users: AdminUserRepositoryPort,
        audit: AdminAuditRepositoryPort,
        events: AccessEventRepositoryPort,
        settings: SecuritySettingRepositoryPort,
        rules: AccessRuleRepositoryPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._ip_blocks = ip_blocks
        self._users = users
        self._audit = audit
        self._events = events
        self._settings = settings
        self._rules = rules
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
        term = f"{ttl_minutes}분" if ttl_minutes else "무기한"
        self._audit.add(
            audit_entry(now, actor, AuditAction.IP_BLOCK_CREATE, normalized, f"{block.reason} · {term}", actor_ip)
        )
        return self._to_dto(block)

    def unblock(self, ip: str, actor: AdminPrincipalDto, actor_ip: str | None) -> None:
        if not self._ip_blocks.delete(ip):
            raise IpBlockNotFound(f"차단 목록에 없는 IP입니다: {ip}")
        self._audit.add(audit_entry(self._clock(), actor, AuditAction.IP_BLOCK_DELETE, ip, ip=actor_ip))

    def is_blocked(self, client: Client) -> bool:
        if client.ip is None:
            return False
        now = self._clock()
        block = self._ip_blocks.get(client.ip)
        if block is None or not block.is_active(now):
            return False
        return not (is_auto_block(block) and is_allowed(self._rules, client, now))

    def enforce_auto_defense(self, client: Client) -> IpBlockDto | None:
        ip, now = client.ip, self._clock()
        if auto_block_exempt(ip) or not self._settings.get(AUTO_DEFENSE).enabled or is_allowed(self._rules, client, now):
            return None
        previous = self._ip_blocks.get(ip)
        if previous is not None and previous.is_active(now):
            return None
        repeat = previous is not None and is_auto_block(previous)
        for rule in AUTO_BLOCK_RULES:
            count = sum(self._events.count(kind, ip, now - rule.window) for kind in rule.kinds)
            if count < rule.threshold:
                continue
            term = rule.repeat_block if repeat else rule.block
            block = IpBlock(ip=ip, reason=rule.reason(count, repeat), created_at=now, expires_at=now + term)
            self._ip_blocks.save(block)
            minutes = int(term.total_seconds() // 60)
            self._audit.add(
                AdminAudit(
                    occurred_at=now, action=AuditAction.IP_BLOCK_AUTO, actor_username=AUTO_BLOCK_ACTOR,
                    target=ip, detail=f"{block.reason} · {minutes}분",
                )
            )
            return self._to_dto(block)
        return None

    def _to_dto(self, block: IpBlock) -> IpBlockDto:
        actor = self._users.get_by_id(block.created_by) if block.created_by else None
        return IpBlockDto(
            ip=block.ip,
            reason=block.reason,
            created_at=block.created_at,
            expires_at=block.expires_at,
            created_by=actor.username if actor else AUTO_BLOCK_ACTOR if is_auto_block(block) else None,
        )
