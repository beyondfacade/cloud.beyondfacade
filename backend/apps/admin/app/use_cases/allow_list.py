from datetime import datetime

from apps.admin.app.ports.output.access_rule_port import AccessRuleRepositoryPort
from apps.admin.domain.entities.access_rule_entity import RulePolicy
from apps.admin.domain.entities.client_entity import Client
from apps.admin.domain.services.access_rule_targets import matching_rule


def is_allowed(rules: AccessRuleRepositoryPort, client: Client, now: datetime) -> bool:
    """IP(대역) 또는 디바이스가 화이트리스트에 있는지 — 자동 차단·로그인 제한 예외 판정."""
    return matching_rule(rules.list_active(now, RulePolicy.ALLOW), client, now) is not None
