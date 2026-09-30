"""Composition Root (DIP) — admin BC Port에 Adapter를 주입한다."""

from functools import cache

from apps.admin.adapter.outbound.google.google_identity_adapter import GoogleIdentityAdapter
from apps.admin.adapter.outbound.repositories.access_event_repository import SqlAlchemyAccessEventRepository
from apps.admin.adapter.outbound.repositories.admin_audit_repository import SqlAlchemyAdminAuditRepository
from apps.admin.adapter.outbound.repositories.admin_session_repository import SqlAlchemyAdminSessionRepository
from apps.admin.adapter.outbound.repositories.admin_user_repository import SqlAlchemyAdminUserRepository
from apps.admin.adapter.outbound.repositories.ip_block_repository import SqlAlchemyIpBlockRepository
from apps.admin.adapter.outbound.repositories.security_setting_repository import SqlAlchemySecuritySettingRepository
from apps.admin.app.ports.input.access_event_use_case import AccessEventUseCase
from apps.admin.app.ports.input.admin_audit_use_case import AdminAuditUseCase
from apps.admin.app.ports.input.admin_session_use_case import AdminSessionUseCase
from apps.admin.app.ports.input.admin_user_use_case import AdminUserUseCase
from apps.admin.app.ports.input.housekeeping_use_case import HousekeepingUseCase
from apps.admin.app.ports.input.ip_block_use_case import IpBlockUseCase
from apps.admin.app.ports.input.security_setting_use_case import SecuritySettingUseCase
from apps.admin.app.use_cases.access_event_interactor import AccessEventInteractor
from apps.admin.app.use_cases.admin_audit_interactor import AdminAuditInteractor
from apps.admin.app.use_cases.admin_session_interactor import AdminSessionInteractor
from apps.admin.app.use_cases.admin_user_interactor import AdminUserInteractor
from apps.admin.app.use_cases.housekeeping_interactor import HousekeepingInteractor
from apps.admin.app.use_cases.ip_block_interactor import IpBlockInteractor
from apps.admin.app.use_cases.security_setting_interactor import SecuritySettingInteractor
from core.matrix.grid_keymaker_secret_manager import get_settings


@cache
def _google_identity() -> GoogleIdentityAdapter:
    settings = get_settings()
    return GoogleIdentityAdapter(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
    )


def get_admin_session_use_case() -> AdminSessionUseCase:
    return AdminSessionInteractor(
        users=SqlAlchemyAdminUserRepository(),
        sessions=SqlAlchemyAdminSessionRepository(),
        events=SqlAlchemyAccessEventRepository(),
        audit=SqlAlchemyAdminAuditRepository(),
        google=_google_identity(),
    )


def get_admin_user_use_case() -> AdminUserUseCase:
    return AdminUserInteractor(
        users=SqlAlchemyAdminUserRepository(),
        sessions=SqlAlchemyAdminSessionRepository(),
        audit=SqlAlchemyAdminAuditRepository(),
    )


def get_access_event_use_case() -> AccessEventUseCase:
    return AccessEventInteractor(events=SqlAlchemyAccessEventRepository(), ip_blocks=SqlAlchemyIpBlockRepository())


def get_ip_block_use_case() -> IpBlockUseCase:
    return IpBlockInteractor(
        ip_blocks=SqlAlchemyIpBlockRepository(),
        users=SqlAlchemyAdminUserRepository(),
        audit=SqlAlchemyAdminAuditRepository(),
        events=SqlAlchemyAccessEventRepository(),
        settings=SqlAlchemySecuritySettingRepository(),
    )


def get_security_setting_use_case() -> SecuritySettingUseCase:
    return SecuritySettingInteractor(
        settings=SqlAlchemySecuritySettingRepository(),
        users=SqlAlchemyAdminUserRepository(),
        audit=SqlAlchemyAdminAuditRepository(),
    )


def get_admin_audit_use_case() -> AdminAuditUseCase:
    return AdminAuditInteractor(audit=SqlAlchemyAdminAuditRepository())


def get_housekeeping_use_case() -> HousekeepingUseCase:
    return HousekeepingInteractor(
        events=SqlAlchemyAccessEventRepository(),
        audit=SqlAlchemyAdminAuditRepository(),
        sessions=SqlAlchemyAdminSessionRepository(),
        ip_blocks=SqlAlchemyIpBlockRepository(),
    )
