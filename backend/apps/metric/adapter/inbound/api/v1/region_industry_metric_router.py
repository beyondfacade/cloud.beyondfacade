from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.metric.adapter.inbound.api.schemas.region_industry_metric_schema import (
    MetricValueResponse,
    RegionIndustryMetricResponse,
)
from apps.metric.adapter.inbound.mappers.region_industry_metric_mapper import (
    to_metric_value_response,
    to_response,
)
from apps.metric.app.ports.input.region_industry_metric_use_case import (
    RegionIndustryMetricUseCase,
)
from apps.metric.dependencies.region_industry_metric_dependencies import (
    get_region_industry_metric_use_case,
)
from apps.metric.domain.errors import IndustryNotFoundError, MetricNotFoundError

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _not_found(code: str, message: str) -> JSONResponse:
    """에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)."""
    return JSONResponse(
        status_code=404, content={"error": {"code": code, "message": message}}
    )


@router.get("/myself", response_model=RegionIndustryMetricResponse)
def myself(
    use_case: RegionIndustryMetricUseCase = Depends(get_region_industry_metric_use_case),
) -> RegionIndustryMetricResponse:
    return to_response(use_case.myself())


@router.get("", response_model=list[MetricValueResponse])
def list_metric_values(
    industry: str,
    metric: str,
    year: int,
    use_case: RegionIndustryMetricUseCase = Depends(get_region_industry_metric_use_case),
) -> list[MetricValueResponse] | JSONResponse:
    try:
        values = use_case.list_metric_values(industry, metric, year)
    except MetricNotFoundError:
        return _not_found("METRIC_NOT_FOUND", f"지원하지 않는 metric: {metric}")
    except IndustryNotFoundError:
        return _not_found("INDUSTRY_NOT_FOUND", f"지원하지 않는 industry: {industry}")
    return [to_metric_value_response(value) for value in values]
