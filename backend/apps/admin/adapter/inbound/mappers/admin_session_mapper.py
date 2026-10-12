"""Inbound Boundary Gate — dto ↔ schema 변환."""

from apps.admin.adapter.inbound.api.schemas.admin_session_schema import AdminMeResponse
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto


def to_me_response(dto: AdminPrincipalDto) -> AdminMeResponse:
    return AdminMeResponse(
        id=dto.id,
        username=dto.username,
        role=dto.role,
        can_operate=dto.can_operate,
        specialty=dto.specialty,
        avatar_version=dto.avatar_version,
    )
