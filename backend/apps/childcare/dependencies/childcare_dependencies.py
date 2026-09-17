"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from fastapi.responses import JSONResponse

from apps.childcare.adapter.outbound.gateways.region_catalog_gateway import RegionCatalogGateway
from apps.childcare.adapter.outbound.repositories.childcare_center_repository import (
    SqlAlchemyChildcareCenterRepository,
)
from apps.childcare.adapter.outbound.repositories.childcare_center_stat_repository import (
    SqlAlchemyChildcareCenterStatRepository,
)
from apps.childcare.app.ports.input.childcare_center_stat_use_case import (
    ChildcareCenterStatUseCase,
)
from apps.childcare.app.ports.input.childcare_center_use_case import ChildcareCenterQueryUseCase
from apps.childcare.app.use_cases.childcare_center_interactor import (
    ChildcareCenterQueryInteractor,
)
from apps.childcare.app.use_cases.childcare_center_stat_interactor import (
    ChildcareCenterStatInteractor,
)


def get_childcare_center_query_use_case() -> ChildcareCenterQueryUseCase:
    return ChildcareCenterQueryInteractor(
        repository=SqlAlchemyChildcareCenterRepository(), region_catalog=RegionCatalogGateway()
    )


def get_childcare_center_stat_use_case() -> ChildcareCenterStatUseCase:
    return ChildcareCenterStatInteractor(
        repository=SqlAlchemyChildcareCenterStatRepository(),
        region_catalog=RegionCatalogGateway(),
    )


def region_not_found(region_code: str) -> JSONResponse:
    """에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약) — 라우터 2종 공용."""
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "REGION_NOT_FOUND",
                "message": f"알 수 없는 region_code: {region_code}",
            }
        },
    )
