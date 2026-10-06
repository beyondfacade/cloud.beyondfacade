"""서울 열린데이터광장 ④지역 이벤트 원천 Driven Adapter 3종 (2026-10-06 실호출 검증).

- 엔드포인트: openapi.seoul.go.kr:8088/{key}/json/{서비스}/{start}/{end}/ — 1회 최대 1,000건, 일 1,000회
- OA-22856 TbSeoulRedevStatus 도시정비사업: 좌표 없음 → SGIS 지오코딩(지번 → 도로명 순).
  브이월드 지오코더는 결과 DB 저장 금지 약관(docs/api.md §2-4)이라 쓰지 않는다
- OA-16096 LOCALDATA_082501 대규모점포 인허가: X/Y는 EPSG:5174 → WGS84 변환 (tobacco·store 전례)
- OA-15818 OpenAptInfo 공동주택 아파트: XCRD/YCRD가 이미 WGS84

행→이벤트 매핑(날짜·필터·슬러그·이름)은 도메인 순수 함수(regional_events)가 맡는다.
"""

from abc import abstractmethod
from collections.abc import Iterator

import httpx
from pyproj import Transformer

from apps.shock.app.dtos.shock_event_region_dto import LocatedEvent
from apps.shock.app.ports.output.shock_event_region_port import RegionalEventSourcePort
from apps.shock.domain.entities.shock_event_entity import ShockEvent
from apps.shock.domain.services.regional_events import (
    apartment_event,
    large_store_events,
    parse_ymd,
    redevelopment_events,
)
from apps.store.app.ports.output.geocoding_port import GeocodingGatewayPort
from core.matrix.grid_keymaker_secret_manager import get_settings

_BASE_URL = "http://openapi.seoul.go.kr:8088"
_PAGE_SIZE = 1000  # API 최대값
_TM_TO_WGS84 = Transformer.from_crs(5174, 4326, always_xy=True)
# 변환 결과 검증 범위 (서울 근방) — 벗어나면 좌표 오류로 보고 버림 (tobacco 전례와 동일)
_LAT_RANGE = (37.0, 38.2)
_LNG_RANGE = (126.3, 127.6)


def _float(value: object) -> float | None:
    try:
        return float(str(value).strip())
    except ValueError:
        return None


class SeoulOpenDataGateway(RegionalEventSourcePort):
    """Template Method — 페이징 수신은 공통, 행 → (이벤트, 위치) 변환만 원천마다 다르다."""

    service: str

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=httpx.Timeout(60, connect=10))
        self.call_count = 0  # 일 1,000회 한도 규율 — CLI가 로그로 보고
        self.row_count = 0

    def fetch_located_events(self) -> list[LocatedEvent]:
        return [located for row in self._rows() for located in self._locate(row)]

    @abstractmethod
    def _locate(self, row: dict) -> list[LocatedEvent]:
        """원천 1행 → 위치를 붙인 이벤트 (대상 아님이면 빈 목록)."""

    def _rows(self) -> Iterator[dict]:
        key = get_settings().seoul_open_data_api_key
        start = 1
        while True:
            response = self._client.get(
                f"{_BASE_URL}/{key}/json/{self.service}/{start}/{start + _PAGE_SIZE - 1}/"
            )
            self.call_count += 1
            if response.is_error:  # 예외 메시지에 키가 든 URL이 찍히지 않게 상태 코드만 남긴다
                raise RuntimeError(f"{self.service} HTTP {response.status_code}")
            payload = response.json().get(self.service)
            if payload is None:  # 인증 실패·요청 오류는 서비스 키 없이 RESULT만 옴
                raise RuntimeError(f"{self.service} API 오류: {response.text[:300]}")
            rows = payload.get("row") or []
            self.row_count += len(rows)
            yield from rows
            if start + _PAGE_SIZE > int(payload["list_total_count"]):
                return
            start += _PAGE_SIZE


def _at(events: list[ShockEvent], lat: float | None, lng: float | None) -> list[LocatedEvent]:
    return [LocatedEvent(event=event, lat=lat, lng=lng) for event in events]


class RedevelopmentGateway(SeoulOpenDataGateway):
    service = "TbSeoulRedevStatus"

    def __init__(self, geocoder: GeocodingGatewayPort, client: httpx.Client | None = None) -> None:
        super().__init__(client)
        self._geocoder = geocoder

    def _locate(self, row: dict) -> list[LocatedEvent]:
        events = redevelopment_events(
            code=row["CODE"].strip(),
            district=row["DISTRICT"].strip(),
            zone_name=row["ZONE_NM"].strip(),
            biz_type=row["BIZ_TYPE"].strip(),
            migration_start=parse_ymd(row.get("MIGRATION_START_YMD")),
            migration_end=parse_ymd(row.get("MIGRATION_END_YMD")),
            construction_start=parse_ymd(row.get("CONSTRUCTION_START_YMD")),
        )
        if not events:  # 대상 아닌 구역은 지오코딩 호출을 쓰지 않는다
            return []
        lat, lng = self._geocode(row) or (None, None)
        return _at(events, lat, lng)

    def _geocode(self, row: dict) -> tuple[float, float] | None:
        district = row["DISTRICT"].strip()
        for address in (row.get("JIBUN_ADDR"), row.get("ROAD_ADDR")):
            if address and address.strip():
                point = self._geocoder.geocode(f"서울특별시 {district} {address.strip()}")
                if point is not None:
                    return point
        return None


class LargeStoreGateway(SeoulOpenDataGateway):
    service = "LOCALDATA_082501"

    def _locate(self, row: dict) -> list[LocatedEvent]:
        events = large_store_events(
            mgt_no=row["MGTNO"].strip(),
            name=row["BPLCNM"].strip(),
            store_kind=(row.get("JPSENM") or "").strip(),
            business_type=(row.get("UPTAENM") or "").strip(),
            permit_date=parse_ymd(row.get("APVPERMYMD")),
            close_date=parse_ymd(row.get("DCBYMD")),
        )
        x, y = _float(row.get("X")), _float(row.get("Y"))
        if not events or x is None or y is None:
            return _at(events, None, None)
        lng, lat = _TM_TO_WGS84.transform(x, y)
        if not (_LAT_RANGE[0] < lat < _LAT_RANGE[1] and _LNG_RANGE[0] < lng < _LNG_RANGE[1]):
            return _at(events, None, None)
        return _at(events, lat, lng)


class ApartmentGateway(SeoulOpenDataGateway):
    service = "OpenAptInfo"

    def _locate(self, row: dict) -> list[LocatedEvent]:
        households = _float(row.get("TNOHSH"))
        event = apartment_event(
            apt_code=row["APT_CD"].strip(),
            name=row["APT_NM"].strip(),
            households=int(households) if households is not None else None,
            approval_date=parse_ymd(row.get("USE_APRV_YMD")),
        )
        if event is None:
            return []
        return _at([event], _float(row.get("YCRD")), _float(row.get("XCRD")))
