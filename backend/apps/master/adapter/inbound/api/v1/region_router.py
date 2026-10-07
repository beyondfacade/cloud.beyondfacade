import gzip
import json
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from apps.master.adapter.inbound.api.schemas.region_schema import (
    RegionResponse,
    RegionSummaryResponse,
)
from apps.master.adapter.inbound.mappers.region_mapper import (
    to_response,
    to_summary_response,
)
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.dependencies.region_dependencies import get_region_use_case
from apps.master.domain.errors import RegionNotFoundError

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("/myself", response_model=RegionResponse)
def myself(
    use_case: RegionUseCase = Depends(get_region_use_case),
) -> RegionResponse:
    return to_response(use_case.myself())


@dataclass(frozen=True)
class _EncodedGeojson:
    source_id: int
    raw: bytes
    gzip: bytes


_ENCODED: _EncodedGeojson | None = None


def _encoded(geojson: dict) -> _EncodedGeojson:
    """경계 dict를 한 번만 직렬화·압축해 둔다 — 같은 dict(프로세스 캐시 Proxy가 주는 객체)면 재사용.

    부하 테스트 7차 근거: 요청마다 약 450KB JSON 생성 + gzip 레벨 9(요청당 CPU 약 30ms, API CPU가 병목).
    직렬화는 FastAPI JSONResponse와 같은 형식(ensure_ascii=False, 공백 없는 구분자)이라 본문이 바뀌지 않는다.
    """
    global _ENCODED
    if _ENCODED is None or _ENCODED.source_id != id(geojson):
        raw = json.dumps(geojson, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        _ENCODED = _EncodedGeojson(source_id=id(geojson), raw=raw, gzip=gzip.compress(raw, compresslevel=9))
    return _ENCODED


@router.get("/geojson")
def geojson(
    request: Request,
    use_case: RegionUseCase = Depends(get_region_use_case),
) -> Response:
    encoded = _encoded(use_case.geojson())
    # Content-Encoding이 붙은 응답은 GZipMiddleware가 다시 압축하지 않는다
    if "gzip" in request.headers.get("accept-encoding", ""):
        return Response(
            encoded.gzip,
            media_type="application/json",
            headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding"},
        )
    return Response(encoded.raw, media_type="application/json", headers={"Vary": "Accept-Encoding"})


@router.get("/{region_code}/summary", response_model=RegionSummaryResponse)
def summary(
    region_code: str,
    industry: str,
    use_case: RegionUseCase = Depends(get_region_use_case),
) -> RegionSummaryResponse | JSONResponse:
    try:
        dto = use_case.summary(region_code, industry)
    except RegionNotFoundError:
        # 에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "REGION_NOT_FOUND",
                    "message": f"알 수 없는 region_code: {region_code}",
                }
            },
        )
    return to_summary_response(dto)
