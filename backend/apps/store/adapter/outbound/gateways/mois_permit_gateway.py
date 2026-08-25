"""행안부 지방행정 인허가 API Driven Adapter.

- 엔드포인트: apis.data.go.kr/1741000/{업종슬러그}/info (docs/api.md §5.1, 2026-08-25 실호출 검증)
- 좌표: EPSG:5174 평면직각 → WGS84 변환 (브이월드 실좌표와 3m 이내 교차검증)
- 증분: cond[DAT_UPDT_PNT::GTE] (원천 갱신시점 커서)
"""

import calendar
import time
from collections.abc import Iterator
from datetime import date, datetime

import httpx
from pyproj import Transformer

from apps.store.app.dtos.store_dto import IngestTarget
from apps.store.app.ports.output.store_port import StorePermitGatewayPort
from apps.store.domain.entities.store_entity import Store
from core.matrix.grid_keymaker_secret_manager import get_settings

_BASE_URL = "https://apis.data.go.kr/1741000"
_PAGE_SIZE = 100  # API 최대값
_TRANSFORMER = Transformer.from_crs(5174, 4326, always_xy=True)

# 변환 결과 검증 범위 (서울 근방) — 벗어나면 좌표 오류로 보고 버림
_LAT_RANGE = (37.0, 38.2)
_LNG_RANGE = (126.3, 127.6)


def _clamp_ymd(text: str) -> tuple[int, int, int] | None:
    """원천에 실존하는 불량 날짜(예: 2006-02-29) 방어 — 일(day)을 월말로 클램프."""
    try:
        year, month, day = (int(p) for p in text.split("-"))
        if not (1 <= month <= 12) or year < 1 or day < 1:
            return None
        return year, month, min(day, calendar.monthrange(year, month)[1])
    except ValueError:
        return None


def _parse_date(value: str | None) -> date | None:
    if not value or not value.strip():
        return None
    ymd = _clamp_ymd(value.strip()[:10])
    return date(*ymd) if ymd else None


def _parse_datetime(value: str) -> datetime:
    text = value.strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        ymd = _clamp_ymd(text[:10])
        if ymd is None:
            raise
        return datetime.fromisoformat(f"{ymd[0]:04d}-{ymd[1]:02d}-{ymd[2]:02d}{text[10:]}")


def _to_wgs84(x_raw: str | None, y_raw: str | None) -> tuple[float | None, float | None]:
    if not x_raw or not y_raw or not x_raw.strip() or not y_raw.strip():
        return None, None
    lng, lat = _TRANSFORMER.transform(float(x_raw), float(y_raw))
    if _LAT_RANGE[0] < lat < _LAT_RANGE[1] and _LNG_RANGE[0] < lng < _LNG_RANGE[1]:
        return round(lat, 7), round(lng, 7)
    return None, None


class MoisPermitGateway(StorePermitGatewayPort):
    def iter_stores(
        self, target: IngestTarget, updated_since: datetime | None
    ) -> Iterator[Store]:
        params: dict[str, str | int] = {
            "serviceKey": get_settings().data_go_kr_api_key,
            "numOfRows": _PAGE_SIZE,
            "returnType": "json",
            "cond[OPN_ATMY_GRP_CD::EQ]": target.authority_code,
        }
        if updated_since is not None:
            params["cond[DAT_UPDT_PNT::GTE]"] = updated_since.strftime("%Y%m%d%H%M%S")

        page = 1
        with httpx.Client(timeout=httpx.Timeout(60, connect=10)) as client:
            while True:
                response = self._get_with_retry(
                    client, f"{_BASE_URL}/{target.slug}/info", {**params, "pageNo": page}
                )
                body = response.json()["response"]["body"]
                items = (body.get("items") or {}).get("item") or []
                for item in items:
                    yield self._to_entity(item, target)
                if page * _PAGE_SIZE >= int(body.get("totalCount") or 0):
                    return
                page += 1

    @staticmethod
    def _get_with_retry(
        client: httpx.Client, url: str, params: dict, attempts: int = 3
    ) -> httpx.Response:
        """타임아웃·5xx는 지수 백오프 재시도, 4xx는 즉시 전파."""
        for attempt in range(attempts):
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as error:
                if error.response.status_code < 500 or attempt == attempts - 1:
                    raise
            except httpx.TimeoutException:
                if attempt == attempts - 1:
                    raise
            time.sleep(2**attempt)
        raise RuntimeError("unreachable")

    @staticmethod
    def _to_entity(item: dict, target: IngestTarget) -> Store:
        lat, lng = _to_wgs84(item.get("CRD_INFO_X"), item.get("CRD_INFO_Y"))
        # MNG_NO는 자치구 간 중복됨 (2026-08-25 실측: 강남·송파 표본 400 중 284 동일) — 조합키 필수
        return Store(
            store_id=f"{target.industry_id}:{target.authority_code}:{item['MNG_NO']}",
            name=(item.get("BPLC_NM") or "").strip(),
            industry_id=target.industry_id,
            district_code=target.district_code,
            open_date=_parse_date(item.get("LCPMT_YMD")),
            close_date=_parse_date(item.get("CLSBIZ_YMD")),
            status_code=(item.get("DTL_SALS_STTS_CD") or "").strip(),
            status_name=(item.get("DTL_SALS_STTS_NM") or "").strip(),
            lat=lat,
            lng=lng,
            source_updated_at=_parse_datetime(item["DAT_UPDT_PNT"]),
        )
