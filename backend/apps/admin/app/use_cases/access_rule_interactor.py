from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from apps.admin.app.dtos.access_rule_dto import AccessRuleDto, CurrentDeviceDto
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.errors import AccessRuleExists, AccessRuleNotFound, InvalidAccessRule, SelfBlock
from apps.admin.app.ports.input.access_rule_use_case import AccessRuleUseCase
from apps.admin.app.ports.output.access_rule_port import AccessRuleRepositoryPort
from apps.admin.app.ports.output.admin_audit_port import AdminAuditRepositoryPort
from apps.admin.app.ports.output.admin_user_port import AdminUserRepositoryPort
from apps.admin.app.use_cases.allow_list import is_allowed
from apps.admin.app.use_cases.audit_trail import audit_entry
from apps.admin.domain.entities.access_rule_entity import AccessRule, RulePolicy, RuleTarget
from apps.admin.domain.entities.admin_audit_entity import AuditAction
from apps.admin.domain.entities.client_entity import Client
from apps.admin.domain.services.access_rule_targets import TARGETS

_POLICY_LABEL = {RulePolicy.ALLOW: "화이트리스트", RulePolicy.DENY: "블랙리스트"}


def _parse(policy: str, target: str) -> tuple[RulePolicy, RuleTarget]:
    try:
        parsed = RulePolicy(policy), RuleTarget(target)
    except ValueError as error:
        raise InvalidAccessRule(f"알 수 없는 목록·대상입니다: {policy} · {target}") from error
    if parsed == (RulePolicy.DENY, RuleTarget.IP):
        raise InvalidAccessRule("IP 블랙리스트는 IP 차단 목록에서 추가합니다.")
    return parsed


class AccessRuleInteractor(AccessRuleUseCase):
    def __init__(
        self,
        rules: AccessRuleRepositoryPort,
        users: AdminUserRepositoryPort,
        audit: AdminAuditRepositoryPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._rules = rules
        self._users = users
        self._audit = audit
        self._clock = clock

    def myself(self) -> AccessRuleDto:
        return AccessRuleDto(
            id=0, policy="allow", target="ip", value="192.0.2.0/24", note="access_rule 배선 검증",
            created_at=datetime(2026, 9, 30, tzinfo=UTC), expires_at=None, created_by="myself",
        )

    def list_active(self) -> list[AccessRuleDto]:
        return [self._to_dto(rule) for rule in self._rules.list_active(self._clock())]

    def current_device(self, client: Client) -> CurrentDeviceDto:
        return CurrentDeviceDto(
            device_id=client.device_id,
            user_agent=client.user_agent,
            allowed=is_allowed(self._rules, client, self._clock()),
            denied=self.is_denied(client),
        )

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
        rule_policy, rule_target = _parse(policy, target)
        strategy = TARGETS[rule_target]
        try:
            normalized = strategy.normalize(value)
        except ValueError as error:
            raise InvalidAccessRule(str(error)) from error
        if rule_policy is RulePolicy.DENY and strategy.matches(normalized, actor_client):
            raise SelfBlock("지금 쓰고 있는 내 디바이스는 차단할 수 없습니다.")

        now = self._clock()
        existing = self._rules.find(rule_policy, rule_target, normalized)
        if existing is not None and existing.is_active(now):
            raise AccessRuleExists(f"이미 {_POLICY_LABEL[rule_policy]}에 있습니다: {normalized}")
        rule = self._rules.save(
            AccessRule(
                id=existing.id if existing else None,
                policy=rule_policy,
                target=rule_target,
                value=normalized,
                note=note.strip(),
                created_at=now,
                expires_at=now + timedelta(minutes=ttl_minutes) if ttl_minutes else None,
                created_by=actor.id,
            )
        )
        term = f"{ttl_minutes}분" if ttl_minutes else "무기한"
        detail = " · ".join(part for part in (_POLICY_LABEL[rule_policy], strategy.label, rule.note, term) if part)
        self._audit.add(
            audit_entry(now, actor, AuditAction.ACCESS_RULE_CREATE, normalized, detail, actor_client.ip)
        )
        return self._to_dto(rule)

    def delete(self, rule_id: int, actor: AdminPrincipalDto, actor_ip: str | None) -> None:
        rule = self._rules.delete(rule_id)
        if rule is None:
            raise AccessRuleNotFound(f"목록에 없는 항목입니다: {rule_id}")
        detail = f"{_POLICY_LABEL[rule.policy]} · {TARGETS[rule.target].label}"
        self._audit.add(audit_entry(self._clock(), actor, AuditAction.ACCESS_RULE_DELETE, rule.value, detail, actor_ip))

    def is_denied(self, client: Client) -> bool:
        if client.device_id is None:
            return False
        rule = self._rules.find(RulePolicy.DENY, RuleTarget.DEVICE, client.device_id)
        return rule is not None and rule.is_active(self._clock())

    def _to_dto(self, rule: AccessRule) -> AccessRuleDto:
        actor = self._users.get_by_id(rule.created_by) if rule.created_by else None
        return AccessRuleDto(
            id=rule.id or 0,
            policy=rule.policy.value,
            target=rule.target.value,
            value=rule.value,
            note=rule.note,
            created_at=rule.created_at,
            expires_at=rule.expires_at,
            created_by=actor.username if actor else None,
        )
