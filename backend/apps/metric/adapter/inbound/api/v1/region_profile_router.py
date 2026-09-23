from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.metric.adapter.inbound.api.schemas.region_profile_schema import (
    RegionProfileResponse,
)
from apps.metric.adapter.inbound.mappers.region_profile_mapper import to_response
from apps.metric.app.ports.input.region_profile_use_case import RegionProfileUseCase
from apps.metric.dependencies.region_profile_dependencies import (
    get_region_profile_use_case,
)

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
