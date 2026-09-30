"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.admin.adapter.inbound.api.schemas.ip_block_schema import IpBlockResponse
from apps.admin.app.dtos.ip_block_dto import IpBlockDto


def to_response(dto: IpBlockDto) -> IpBlockResponse:
    return IpBlockResponse(**asdict(dto))
