"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.admin.adapter.inbound.api.schemas.admin_audit_schema import AuditPageResponse
from apps.admin.app.dtos.admin_audit_dto import AuditPageDto


def to_page_response(dto: AuditPageDto) -> AuditPageResponse:
    return AuditPageResponse.model_validate(asdict(dto))
