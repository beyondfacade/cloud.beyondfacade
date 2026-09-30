"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.admin.adapter.inbound.api.schemas.security_setting_schema import AutoDefenseResponse
from apps.admin.app.dtos.security_setting_dto import AutoDefenseDto


def to_response(dto: AutoDefenseDto) -> AutoDefenseResponse:
    return AutoDefenseResponse(**asdict(dto))
