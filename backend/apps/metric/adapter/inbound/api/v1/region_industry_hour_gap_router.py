from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.metric.adapter.inbound.api.schemas.region_industry_hour_gap_schema import (
    RegionIndustryHourGapResponse,
)
from apps.metric.adapter.inbound.mappers.region_industry_hour_gap_mapper import to_response
from apps.metric.app.ports.input.region_industry_hour_gap_use_case import (
    RegionIndustryHourGapUseCase,
)
from apps.metric.dependencies.region_profile_dependencies import (
    get_region_industry_hour_gap_use_case,
)

router = APIRouter(prefix="/hour-gaps", tags=["hour-gaps"])


def _not_found(code: str, message: str) -> JSONResponse:
    """에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)."""
    return JSONResponse(
        status_code=404, content={"error": {"code": code, "message": message}}
    )


@router.get("/myself", response_model=RegionIndustryHourGapResponse)
def myself(
    use_case: RegionIndustryHourGapUseCase = Depends(get_region_industry_hour_gap_use_case),
) -> RegionIndustryHourGapResponse:
    """§12 배선 검증 — 유스케이스의 하드코딩 한 구간을 응답 모양으로 감싸 왕복시킨다."""
    return to_response([use_case.myself()])


@router.get("", response_model=RegionIndustryHourGapResponse)
def find(
    region: str,
    industry: str,
    year_quarter: str | None = None,
    use_case: RegionIndustryHourGapUseCase = Depends(get_region_industry_hour_gap_use_case),
) -> RegionIndustryHourGapResponse | JSONResponse:
    """분기를 생략하면 그 동×업종의 최신 분기. 동×업종의 6구간이라 단계구분도가 아니라 패널 차트다."""
    bands = (
        use_case.list_bands(region, industry, year_quarter)
        if year_quarter
        else use_case.list_latest_bands(region, industry)
    )
    if not bands:
        return _not_found(
            "HOUR_GAP_NOT_FOUND",
            f"시간대 어긋남 자료가 없습니다: {region} × {industry}"
            + (f" ({year_quarter})" if year_quarter else ""),
        )
    return to_response(bands)
