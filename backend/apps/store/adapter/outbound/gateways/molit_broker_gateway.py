"""국토교통부 부동산중개업(브이월드 NED EDOffices) Driven Adapter.

- 엔드포인트: api.vworld.kr/ned/data/getEBOfficeInfo (2026-09-07 실호출 검증)
  — data.go.kr 15123990은 이 서비스로의 LINK형 (data.go.kr 쿼터 미사용)
- 인증: VWORLD_API_KEY + domain(인증키 등록 서비스URL) — VworldBoundaryGateway 전례
- ldCode = district_code(시군구 5자리) 그대로 사용. 상태 무필터 조회가 영업중·휴업·업무정지
  전 상태 포함 (강남 2,990 = 영업중 2,972 + 휴업 16 + 업무정지 2 실측)
- 원천에 좌표·폐업일 없음: lat/lng NULL 적재(SGIS 지오코딩 후속 대상, 학원과 동일 대기열),
  폐업은 스냅샷 소실 추정 (BrokerSnapshotInteractor 책임)
"""

import calendar
import time
from collections.abc import Iterator
from datetime import date, datetime

import httpx

from apps.store.app.ports.output.broker_snapshot_port import BrokerGatewayPort
from apps.store.domain.entities.store_entity import Store
from core.matrix.grid_keymaker_secret_manager import get_settings

_BASE_URL = "https://api.vworld.kr/ned/data/getEBOfficeInfo"
_PAGE_SIZE = 1000  # 실호출 검증 최대값 (1,000행 정상 수신)

# sttusSeCode → 정규화 코드 (§5 dict 디스패치) — 미지 코드는 원문 보존
_STATUS_CODES = {"1": "open", "2": "suspended"}


def _parse_date(value: str | None) -> date | None:
    """YYYY-MM-DD 방어 파싱 — 불량 일(day)은 월말로 클램프 (MOIS 게이트웨이 전례)."""
    text = (value or "").strip()[:10]
    try:
        year, month, day = (int(p) for p in text.split("-"))
    except ValueError:
        return None
    if not (1 <= month <= 12) or year < 1 or day < 1:
        return None
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _to_source_updated_at(value: str | None) -> datetime:
    """lastUpdtDt(일 단위) → 커서용 datetime — 결측 시 관측일로 폴백 (학원 게이트웨이 전례)."""
    parsed = _parse_date(value) or date.today()
    return datetime(parsed.year, parsed.month, parsed.day)


class MolitBrokerGateway(BrokerGatewayPort):
    def __init__(self) -> None:
        settings = get_settings()
        self._key = settings.vworld_api_key
        self._domain = settings.vworld_service_domain
        self.call_count = 0  # 호출량 규율 — CLI가 로그로 보고

    def iter_offices(self, industry_id: str, district_code: str) -> Iterator[Store]:
        params: dict[str, str | int] = {
            "key": self._key,
            "domain": self._domain,
            "ldCode": district_code,
            "format": "json",
            "numOfRows": _PAGE_SIZE,
        }
        page = 1
        with httpx.Client(timeout=httpx.Timeout(60, connect=10)) as client:
            while True:
                response = self._get_with_retry(client, _BASE_URL, {**params, "pageNo": page})
                self.call_count += 1
                body = response.json().get("EDOffices")
                # 인증 실패·파라미터 오류는 {"response": {...}} 래퍼 또는 resultCode로 옴
                if body is None or (body.get("resultCode") or "").strip():
                    raise RuntimeError(f"molit broker API 오류: {response.text[:300]}")
                for item in body.get("field") or []:
                    yield self._to_store(item, industry_id, district_code)
                if page * _PAGE_SIZE >= int(body.get("totalCount") or 0):
                    return
                page += 1

    @staticmethod
    def _get_with_retry(
        client: httpx.Client, url: str, params: dict, attempts: int = 3
    ) -> httpx.Response:
        """타임아웃·5xx는 지수 백오프 재시도, 4xx는 즉시 전파 (MOIS 게이트웨이 전례)."""
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
    def _to_store(item: dict, industry_id: str, district_code: str) -> Store:
        # jurirno(등록번호)는 자치구 내 유일 — ldCode 조합으로 전역 유일키 구성
        status_code = (item.get("sttusSeCode") or "").strip()
        return Store(
            store_id=f"{industry_id}:{district_code}:{item['jurirno']}",
            name=(item.get("bsnmCmpnm") or "").strip(),
            industry_id=industry_id,
            district_code=district_code,
            open_date=_parse_date(item.get("registDe")),
            close_date=None,  # 원천에 폐업일 없음 — 스냅샷 소실 추정(인터랙터)
            status_code=_STATUS_CODES.get(status_code, status_code),
            status_name=(item.get("sttusSeCodeNm") or "").strip(),
            lat=None,  # 원천에 좌표 없음 — SGIS 지오코딩 후속 대상
            lng=None,
            source_updated_at=_to_source_updated_at(item.get("lastUpdtDt")),
        )
