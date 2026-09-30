"""Outbound Boundary Gate — entity ↔ ORM 변환."""

from apps.admin.adapter.outbound.orms.admin_user_orm import AdminUserOrm
from apps.admin.domain.entities.admin_user_entity import AdminRole, AdminUser


def to_entity(orm: AdminUserOrm) -> AdminUser:
    return AdminUser(
        id=orm.id,
        username=orm.username,
        password_hash=orm.password_hash,
        role=AdminRole(orm.role),
        is_active=orm.is_active,
        created_at=orm.created_at,
        last_login_at=orm.last_login_at,
    )


def apply_to_orm(entity: AdminUser, orm: AdminUserOrm) -> None:
    orm.username = entity.username
    orm.password_hash = entity.password_hash
    orm.role = entity.role.value
    orm.is_active = entity.is_active
