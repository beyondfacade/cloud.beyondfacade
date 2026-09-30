"""Outbound Boundary Gate — entity ↔ ORM 변환."""

from apps.admin.adapter.outbound.orms.access_rule_orm import AccessRuleOrm
from apps.admin.domain.entities.access_rule_entity import AccessRule, RulePolicy, RuleTarget

_FIELDS = ("value", "note", "created_at", "expires_at", "created_by")


def to_orm(entity: AccessRule) -> AccessRuleOrm:
    return AccessRuleOrm(
        policy=entity.policy.value, target=entity.target.value, **{name: getattr(entity, name) for name in _FIELDS}
    )


def to_entity(orm: AccessRuleOrm) -> AccessRule:
    return AccessRule(
        id=orm.id,
        policy=RulePolicy(orm.policy),
        target=RuleTarget(orm.target),
        **{name: getattr(orm, name) for name in _FIELDS},
    )


def apply_to_orm(entity: AccessRule, orm: AccessRuleOrm) -> None:
    orm.policy, orm.target = entity.policy.value, entity.target.value
    for name in _FIELDS:
        setattr(orm, name, getattr(entity, name))
