"""한국은행 ECOS 기준금리 Driven Adapter (docs/api.md ⑧ — 2026-08-25 실호출 검증).

StatisticSearch 722Y001(월)/0101000 — 실응답 필드: TIME(YYYYMM)·DATA_VALUE·UNIT_NAME.
오류는 HTTP 200 + RESULT 바디로 온다 → parse_rates가 RuntimeError로 변환.
"""

from datetime import date

import httpx

from apps.shock.domain.entities.interest_rate_entity import InterestRate
from core.matrix.grid_keymaker_secret_manager import get_settings

_STAT_CODE = "722Y001"  # 한국은행 기준금리 및 여수신금리
_ITEM_CODE = "0101000"  # 한국은행 기준금리
_RATE_TYPE = "base"
_START_PERIOD = "201901"  # 코로나 전 기준선(2019)부터 — brainstorming §4.3
_MAX_ROWS = 1000  # 월 1행 — 2019~현재 전량 1회 수신


def parse_rates(body: dict) -> list[InterestRate]:
    """실응답 JSON → 시계열 엔티티. RESULT 바디(오류)는 예외로 변환한다."""
    result = body.get("RESULT")
    if result is not None:
        raise RuntimeError(f"ECOS 오류 {result.get('CODE')}: {result.get('MESSAGE')}")
    rates = []
    for row in body.get("StatisticSearch", {}).get("row", []):
        try:
            rate = float(row["DATA_VALUE"])
        except (KeyError, ValueError):
            continue  # 결측 표기("-" 등) 방어
        period = row["TIME"]
        rates.append(
            InterestRate(
                id=f"{_RATE_TYPE}:{period}",
                rate_type=_RATE_TYPE,
                period=period,
                rate=rate,
                unit=row.get("UNIT_NAME") or "연%",
                stat_code=row.get("STAT_CODE") or _STAT_CODE,
                item_code=row.get("ITEM_CODE1") or _ITEM_CODE,
            )
        )
    return rates


class EcosBaseRateGateway:
    def fetch_rates(self) -> list[InterestRate]:
        end_period = f"{date.today():%Y%m}"
        url = (
            f"https://ecos.bok.or.kr/api/StatisticSearch/{get_settings().ecos_api_key}"
            f"/json/kr/1/{_MAX_ROWS}/{_STAT_CODE}/M/{_START_PERIOD}/{end_period}/{_ITEM_CODE}"
        )
        response = httpx.get(url, timeout=60)
        response.raise_for_status()
        rates = parse_rates(response.json())
        print(f"ECOS API 호출 1건 — 기준금리 월별 {len(rates)}행 수신")
        return rates
