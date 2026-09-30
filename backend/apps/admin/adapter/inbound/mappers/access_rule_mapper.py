"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.admin.adapter.inbound.api.schemas.access_rule_schema import AccessRuleResponse, CurrentDeviceResponse
from apps.admin.app.dtos.access_rule_dto import AccessRuleDto, CurrentDeviceDto


def to_response(dto: AccessRuleDto) -> AccessRuleResponse:
    return AccessRuleResponse(**asdict(dto))


def to_device_response(dto: CurrentDeviceDto) -> CurrentDeviceResponse:
    return CurrentDeviceResponse(**asdict(dto))
