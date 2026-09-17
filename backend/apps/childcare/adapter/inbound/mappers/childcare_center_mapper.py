"""Inbound Boundary Gate — dto → schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.childcare.adapter.inbound.api.schemas.childcare_center_schema import (
    ChildcareCenterMarkerResponse,
)
from apps.childcare.app.dtos.childcare_center_dto import ChildcareCenterDto


def to_marker_response(dto: ChildcareCenterDto) -> ChildcareCenterMarkerResponse:
    return ChildcareCenterMarkerResponse(**asdict(dto))
