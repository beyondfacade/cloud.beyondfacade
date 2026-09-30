"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.admin.adapter.inbound.api.schemas.admin_user_schema import (
    AdminSessionInfoResponse,
    AdminSessionListResponse,
    AdminUserListResponse,
    AdminUserResponse,
)
from apps.admin.app.dtos.admin_user_dto import AdminSessionInfoDto, AdminUserDto


def to_user_response(dto: AdminUserDto) -> AdminUserResponse:
    return AdminUserResponse.model_validate(asdict(dto))


def to_user_list_response(dtos: list[AdminUserDto]) -> AdminUserListResponse:
    return AdminUserListResponse(items=[to_user_response(dto) for dto in dtos])


def to_session_list_response(dtos: list[AdminSessionInfoDto]) -> AdminSessionListResponse:
    return AdminSessionListResponse(items=[AdminSessionInfoResponse.model_validate(asdict(dto)) for dto in dtos])
