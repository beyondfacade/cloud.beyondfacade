from abc import ABC, abstractmethod
from datetime import datetime

from apps.admin.domain.entities.access_rule_entity import AccessRule, RulePolicy, RuleTarget


class AccessRuleRepositoryPort(ABC):
    @abstractmethod
    def list_active(self, now: datetime, policy: RulePolicy | None = None) -> list[AccessRule]:
        """최신순. policy를 주면 그 목록만."""

    @abstractmethod
    def find(self, policy: RulePolicy, target: RuleTarget, value: str) -> AccessRule | None:
        """만료된 항목도 돌려준다 — 같은 값을 다시 넣을 때 그 행을 고쳐 쓴다."""

    @abstractmethod
    def save(self, rule: AccessRule) -> AccessRule:
        """id가 없으면 새로 넣고, 있으면 그 행을 갱신한다."""

    @abstractmethod
    def delete(self, rule_id: int) -> AccessRule | None:
        """지운 항목을 돌려준다. 없던 id면 None."""
