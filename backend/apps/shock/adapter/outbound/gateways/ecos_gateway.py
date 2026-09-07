"""한국은행 ECOS 금리 Driven Adapter (docs/api.md ⑧ — 2026-08-25/09-07 실호출 검증).

StatisticSearch 월별 시계열 — 실응답 필드: TIME(YYYYMM)·DATA_VALUE·UNIT_NAME.
- 기준금리: 722Y001/0101000 (rate_type "base")
- 가중평균 대출금리(신규취급액 기준): 121Y006 기업·중소기업·시설자금
  (rate_type "loan_corp"/"loan_sme"/"loan_facility") — 계산기 §8.1③ 대출금리 축.
  COFIX 원천(은행연합회)이 robots.txt 전면 불허라 정식 API인 121Y006으로 대체.
오류는 HTTP 200 + RESULT 바디로 온다 → parse_rates가 RuntimeError로 변환.
"""

from dataclasses import dataclass
from datetime import date

import httpx

from apps.shock.domain.entities.interest_rate_entity import InterestRate
from core.matrix.grid_keymaker_secret_manager import get_settings

_START_PERIOD = "201901"  # 코로나 전 기준선(2019)부터 — brainstorming §4.3
_MAX_ROWS = 1000  # 월 1행 — 2019~현재 전량 1회 수신


@dataclass(frozen=True)
class EcosSeries:
    """ECOS 월별 시계열 1개 = rate_type × 통계표 × 항목."""

    rate_type: str  # interest_rate.rate_type — id 프리픽스 "{rate_type}:{YYYYMM}"
    stat_code: str
    item_code: str


BASE_SERIES = EcosSeries("base", "722Y001", "0101000")  # 한국은행 기준금리

# 예금은행 가중평균 대출금리(신규취급액 기준) — 상가 매입 대출 추정 근접 순
LOAN_SERIES: tuple[EcosSeries, ...] = (
    EcosSeries("loan_corp", "121Y006", "BECBLA02"),  # 기업대출 (상위 벤치마크)
    EcosSeries("loan_sme", "121Y006", "BECBLA0202"),  # 중소기업대출 (소상공인 차주 근사)
    EcosSeries("loan_facility", "121Y006", "BECBLA0204"),  # 시설자금대출 (부동산 취득 최근접)
)


def parse_rates(body: dict, series: EcosSeries = BASE_SERIES) -> list[InterestRate]:
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
                id=f"{series.rate_type}:{period}",
                rate_type=series.rate_type,
                period=period,
                rate=rate,
                unit=row.get("UNIT_NAME") or "연%",
                stat_code=row.get("STAT_CODE") or series.stat_code,
                item_code=row.get("ITEM_CODE1") or series.item_code,
            )
        )
    return rates


def _fetch_series(client: httpx.Client, series: EcosSeries) -> list[InterestRate]:
    end_period = f"{date.today():%Y%m}"
    url = (
        f"https://ecos.bok.or.kr/api/StatisticSearch/{get_settings().ecos_api_key}"
        f"/json/kr/1/{_MAX_ROWS}/{series.stat_code}/M/{_START_PERIOD}/{end_period}"
        f"/{series.item_code}"
    )
    response = client.get(url)
    response.raise_for_status()
    return parse_rates(response.json(), series)


class EcosBaseRateGateway:
    def fetch_rates(self) -> list[InterestRate]:
        with httpx.Client(timeout=60) as client:
            rates = _fetch_series(client, BASE_SERIES)
        print(f"ECOS API 호출 1건 — 기준금리 월별 {len(rates)}행 수신")
        return rates


class EcosLoanRateGateway:
    def fetch_rates(self) -> list[InterestRate]:
        rates: list[InterestRate] = []
        with httpx.Client(timeout=60) as client:
            for series in LOAN_SERIES:
                series_rates = _fetch_series(client, series)
                print(f"ECOS 121Y006 {series.rate_type}: 월별 {len(series_rates)}행 수신")
                rates.extend(series_rates)
        print(f"ECOS API 호출 {len(LOAN_SERIES)}건 — 대출금리 {len(rates)}행 수신")
        return rates
