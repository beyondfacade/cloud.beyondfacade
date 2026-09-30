from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.dtos.security_setting_dto import AutoBlockRuleDto, AutoDefenseDto
from apps.admin.app.ports.input.security_setting_use_case import SecuritySettingUseCase
from apps.admin.app.ports.output.admin_audit_port import AdminAuditRepositoryPort
from apps.admin.app.ports.output.admin_user_port import AdminUserRepositoryPort
from apps.admin.app.ports.output.security_setting_port import SecuritySettingRepositoryPort
from apps.admin.app.use_cases.audit_trail import audit_entry
from apps.admin.domain.entities.admin_audit_entity import AuditAction
from apps.admin.domain.entities.security_setting_entity import AUTO_DEFENSE, SecuritySetting
from apps.admin.domain.services.auto_block_rules import AUTO_BLOCK_RULES


def _minutes(span: timedelta) -> int:
    return int(span.total_seconds() // 60)


_RULES = [
    AutoBlockRuleDto(
        rule=r.rule,
        title=r.title,
        threshold=r.threshold,
        window_minutes=_minutes(r.window),
        block_minutes=_minutes(r.block),
        repeat_block_minutes=_minutes(r.repeat_block),
    )
    for r in AUTO_BLOCK_RULES
]


class SecuritySettingInteractor(SecuritySettingUseCase):
    def __init__(
        self,
        settings: SecuritySettingRepositoryPort,
        users: AdminUserRepositoryPort,
        audit: AdminAuditRepositoryPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._settings = settings
        self._users = users
        self._audit = audit
        self._clock = clock

    def myself(self) -> AutoDefenseDto:
        return AutoDefenseDto(enabled=True, updated_at=datetime(2026, 9, 30, tzinfo=UTC), updated_by="myself")

    def auto_defense(self) -> AutoDefenseDto:
        return self._to_dto(self._settings.get(AUTO_DEFENSE))

    def set_auto_defense(self, enabled: bool, actor: AdminPrincipalDto, actor_ip: str | None) -> AutoDefenseDto:
        now = self._clock()
        saved = self._settings.save(SecuritySetting(key=AUTO_DEFENSE, enabled=enabled, updated_at=now, updated_by=actor.id))
        detail = "켬" if enabled else "끔"
        self._audit.add(audit_entry(now, actor, AuditAction.AUTO_DEFENSE_TOGGLE, AUTO_DEFENSE, detail, actor_ip))
        return self._to_dto(saved)

    def _to_dto(self, setting: SecuritySetting) -> AutoDefenseDto:
        actor = self._users.get_by_id(setting.updated_by) if setting.updated_by else None
        return AutoDefenseDto(
            enabled=setting.enabled,
            updated_at=setting.updated_at,
            updated_by=actor.username if actor else None,
            rules=_RULES,
        )
