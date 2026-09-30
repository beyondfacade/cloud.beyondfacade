from datetime import datetime

from sqlalchemy import or_, select

from apps.admin.adapter.outbound.orm_mappers.access_rule_orm_mapper import apply_to_orm, to_entity, to_orm
from apps.admin.adapter.outbound.orms.access_rule_orm import AccessRuleOrm
from apps.admin.app.ports.output.access_rule_port import AccessRuleRepositoryPort
from apps.admin.domain.entities.access_rule_entity import AccessRule, RulePolicy, RuleTarget
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyAccessRuleRepository(AccessRuleRepositoryPort):
    def list_active(self, now: datetime, policy: RulePolicy | None = None) -> list[AccessRule]:
        query = select(AccessRuleOrm).where(or_(AccessRuleOrm.expires_at.is_(None), AccessRuleOrm.expires_at > now))
        if policy is not None:
            query = query.where(AccessRuleOrm.policy == policy.value)
        with session_scope() as session:
            rows = session.execute(query.order_by(AccessRuleOrm.created_at.desc(), AccessRuleOrm.id.desc())).scalars()
            return [to_entity(orm) for orm in rows]

    def find(self, policy: RulePolicy, target: RuleTarget, value: str) -> AccessRule | None:
        with session_scope() as session:
            orm = session.execute(
                select(AccessRuleOrm).where(
                    AccessRuleOrm.policy == policy.value,
                    AccessRuleOrm.target == target.value,
                    AccessRuleOrm.value == value,
                )
            ).scalar_one_or_none()
            return to_entity(orm) if orm else None

    def save(self, rule: AccessRule) -> AccessRule:
        with session_scope() as session:
            orm = session.get(AccessRuleOrm, rule.id) if rule.id is not None else None
            if orm is None:
                orm = to_orm(rule)
                session.add(orm)
            else:
                apply_to_orm(rule, orm)
            session.flush()
            return to_entity(orm)

    def delete(self, rule_id: int) -> AccessRule | None:
        with session_scope() as session:
            orm = session.get(AccessRuleOrm, rule_id)
            if orm is None:
                return None
            rule = to_entity(orm)
            session.delete(orm)
            return rule
