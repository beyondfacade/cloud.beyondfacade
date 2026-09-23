from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.metric.adapter.inbound.api.schemas.region_profile_schema import (
    ProfileMetricValueResponse,
    ProfileTypeResponse,
    RegionProfileResponse,
)
from apps.metric.adapter.inbound.mappers.region_profile_mapper import (
    to_metric_value_response,
    to_response,
    to_type_response,
)
from apps.metric.app.ports.input.region_profile_use_case import RegionProfileUseCase
from apps.metric.dependencies.region_profile_dependencies import (
    get_region_profile_use_case,
)
from apps.metric.domain.errors import MetricNotFoundError

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _not_found(code: str, message: str) -> JSONResponse:
    """에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)."""
    return JSONResponse(
        status_code=404, content={"error": {"code": code, "message": message}}
    )


# `/{region_code}`보다 먼저 선언해야 'myself'가 행정동 코드로 잡히지 않는다
@router.get("/myself", response_model=RegionProfileResponse)
def myself(
    use_case: RegionProfileUseCase = Depends(get_region_profile_use_case),
) -> RegionProfileResponse:
    return to_response(use_case.myself())


# `/{region_code}`보다 먼저 선언해야 'types'가 행정동 코드로 잡히지 않는다 (`/myself`와 같은 이유)
@router.get("/types", response_model=list[ProfileTypeResponse])
def list_types(
    year_quarter: str | None = None,
    use_case: RegionProfileUseCase = Depends(get_region_profile_use_case),
) -> list[ProfileTypeResponse]:
    """유형 단계구분도용 — 범주 계약. 숫자 계약(`GET /profiles?metric=`)과 경로를 나눈다.

    한 응답에 value/category를 섞어 한쪽을 null로 두지 않는다 (`map-metric-contract` §5).
    """
    return [to_type_response(dto) for dto in use_case.list_types(year_quarter)]


@router.get("", response_model=list[ProfileMetricValueResponse])
def list_metric_values(
    metric: str,
    year_quarter: str | None = None,
    use_case: RegionProfileUseCase = Depends(get_region_profile_use_case),
) -> list[ProfileMetricValueResponse] | JSONResponse:
    """단계구분도용 — 분기를 생략하면 가장 최근 분기. 업종 축이 없는 동 단위 지표다."""
    try:
        values = use_case.list_metric_values(metric, year_quarter)
    except MetricNotFoundError:
        return _not_found("METRIC_NOT_FOUND", f"지원하지 않는 metric: {metric}")
    return [to_metric_value_response(value) for value in values]


@router.get("/{region_code}", response_model=RegionProfileResponse)
def find(
    region_code: str,
    year_quarter: str | None = None,
    use_case: RegionProfileUseCase = Depends(get_region_profile_use_case),
) -> RegionProfileResponse | JSONResponse:
    """분기를 생략하면 그 동의 가장 최근 분기를 준다 — 화면은 어느 분기가 최신인지 모른다."""
    dto = (
        use_case.find(region_code, year_quarter)
        if year_quarter
        else use_case.find_latest(region_code)
    )
    if dto is None:
        return _not_found(
            "REGION_PROFILE_NOT_FOUND",
            f"동네 프로필이 없습니다: {region_code}"
            + (f" ({year_quarter})" if year_quarter else ""),
        )
    return to_response(dto)
