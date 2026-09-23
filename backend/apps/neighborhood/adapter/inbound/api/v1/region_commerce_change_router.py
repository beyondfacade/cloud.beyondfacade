from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.neighborhood.adapter.inbound.api.schemas.region_commerce_change_schema import (
    ChangeMetricValueResponse,
    RegionCommerceChangeResponse,
)
from apps.neighborhood.adapter.inbound.mappers.region_commerce_change_mapper import (
    to_metric_value_response,
    to_response,
)
from apps.neighborhood.app.ports.input.region_commerce_change_query_use_case import (
    RegionCommerceChangeQueryUseCase,
)
from apps.neighborhood.dependencies.region_commerce_change_dependencies import (
    get_region_commerce_change_query_use_case,
)
from apps.neighborhood.domain.errors import MetricNotFoundError

router = APIRouter(prefix="/commerce-changes", tags=["commerce-changes"])


@router.get("/myself", response_model=RegionCommerceChangeResponse)
def myself(
    use_case: RegionCommerceChangeQueryUseCase = Depends(
        get_region_commerce_change_query_use_case
    ),
) -> RegionCommerceChangeResponse:
    return to_response(use_case.myself())


@router.get("", response_model=list[ChangeMetricValueResponse])
def list_metric_values(
    metric: str,
    year_quarter: str | None = None,
    use_case: RegionCommerceChangeQueryUseCase = Depends(
        get_region_commerce_change_query_use_case
    ),
) -> list[ChangeMetricValueResponse] | JSONResponse:
    """단계구분도용 — 분기를 생략하면 가장 최근 분기. 업종 축이 없는 동 단위 지표다."""
    try:
        values = use_case.list_metric_values(metric, year_quarter)
    except MetricNotFoundError:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "METRIC_NOT_FOUND",
                    "message": f"지원하지 않는 metric: {metric}",
                }
            },
        )
    return [to_metric_value_response(value) for value in values]
