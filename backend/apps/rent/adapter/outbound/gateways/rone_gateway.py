"""부동산원 R-ONE 임대동향 Driven Adapter (docs/api.md ⑫ — 2026-09-07 실호출 검증).

SttsApiTblData.do — 실응답 필드: WRTTIME_IDTFR_ID(YYYYQQ)·CLS_ID·CLS_NM·CLS_FULLNM·
DTA_VAL·UI_NM. 지역 단위는 상권/권역/시도(CLS_FULLNM "서울>강남>테헤란로") — 자치구 아님.
통계표가 표본 기준연도(빈티지)별로 분리 제공되어 2019~최신을 여러 표로 이어 붙인다.
오류는 HTTP 200 + RESULT 바디로 온다(ECOS 전례) → parse_page가 RuntimeError로 변환.
"""

from dataclasses import dataclass

import httpx

from apps.rent.domain.entities.rent_price_entity import RentObservation
from core.matrix.grid_keymaker_secret_manager import get_settings

_BASE_URL = "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"
_PAGE_SIZE = 1000  # 1회 최대 수신 실측 허용치
_SEOUL = "서울"


@dataclass(frozen=True)
class RoneTable:
    """R-ONE 통계표 1개 = 지표×상가유형×표본 빈티지."""

    metric: str  # "rent" 임대료 / "vacancy" 공실률
    building_type: str  # "medium_large" / "small"
    statbl_id: str
    vintage: str  # 표본 기준연도 라벨 (로그·문서용)


# 2026-09-07 SttsApiTbl.do 전수 조회로 확정한 통계표 매핑 (docs/api.md ⑫).
# 시리즈별 옛 빈티지 → 새 빈티지 순서 — 경계 분기 중복 시 새 표본이 덮어쓴다.
_TABLES: tuple[RoneTable, ...] = (
    # 임대료 (천원/㎡) — 중대형 상가
    RoneTable("rent", "medium_large", "A_2024_00266", "2019년"),
    RoneTable("rent", "medium_large", "A_2024_00270", "2020년"),
    RoneTable("rent", "medium_large", "A_2024_00274", "2021년"),
    RoneTable("rent", "medium_large", "A_2024_00278", "2022년~"),
    RoneTable("rent", "medium_large", "T244363134858603", "2024년3분기~"),
    # 임대료 — 소규모 상가
    RoneTable("rent", "small", "A_2024_00267", "2019년"),
    RoneTable("rent", "small", "A_2024_00271", "2020년"),
    RoneTable("rent", "small", "A_2024_00275", "2021년"),
    RoneTable("rent", "small", "A_2024_00279", "2022년~"),
    RoneTable("rent", "small", "T248223134698125", "2024년3분기~"),
    # 공실률 (%) — 중대형 상가
    RoneTable("vacancy", "medium_large", "A_2024_00245", "2019년"),
    RoneTable("vacancy", "medium_large", "A_2024_00248", "2020년"),
    RoneTable("vacancy", "medium_large", "A_2024_00251", "2021년"),
    RoneTable("vacancy", "medium_large", "A_2024_00254", "2022년~"),
    RoneTable("vacancy", "medium_large", "T249633134845544", "2024년3분기~"),
    # 공실률 — 소규모 상가
    RoneTable("vacancy", "small", "A_2024_00246", "2019년"),
    RoneTable("vacancy", "small", "A_2024_00249", "2020년"),
    RoneTable("vacancy", "small", "A_2024_00252", "2021년"),
    RoneTable("vacancy", "small", "A_2024_00255", "2022년~"),
    RoneTable("vacancy", "small", "T241833134686576", "2024년3분기~"),
)


def parse_page(body: dict) -> tuple[int, list[dict]]:
    """실응답 JSON → (전체 행 수, 이 페이지 행). RESULT 오류 바디는 예외로 변환한다."""
    result = body.get("RESULT")
    if result is not None:
        raise RuntimeError(f"R-ONE 오류 {result.get('CODE')}: {result.get('MESSAGE')}")
    sections = body.get("SttsApiTblData", [])
    total = 0
    rows: list[dict] = []
    for section in sections:
        for head in section.get("head", []):
            head_result = head.get("RESULT")
            if head_result is not None and head_result.get("CODE") != "INFO-000":
                raise RuntimeError(
                    f"R-ONE 오류 {head_result.get('CODE')}: {head_result.get('MESSAGE')}"
                )
            total = head.get("list_total_count", total)
        rows.extend(section.get("row", []))
    return total, rows


def _to_period(wrttime: str) -> str:
    """원천 WRTTIME_IDTFR_ID "202201"(=2022년 1분기) → "2022Q1"."""
    return f"{wrttime[:4]}Q{int(wrttime[4:])}"


def to_observations(rows: list[dict], table: RoneTable) -> list[RentObservation]:
    """서울(시도·권역·상권) 행만 관측 엔티티로 변환 — 전국·타 시도 제외."""
    observations = []
    for row in rows:
        path = row.get("CLS_FULLNM") or ""
        if path != _SEOUL and not path.startswith(f"{_SEOUL}>"):
            continue
        try:
            value = float(row["DTA_VAL"])
        except (KeyError, TypeError, ValueError):
            continue  # 결측 방어
        cls_id = str(row["CLS_ID"])
        period = _to_period(str(row["WRTTIME_IDTFR_ID"]))
        observations.append(
            RentObservation(
                id=f"{table.building_type}:{cls_id}:{period}",
                building_type=table.building_type,
                cls_id=cls_id,
                region_name=row.get("CLS_NM") or "",
                region_path=path,
                region_level=path.count(">") + 1,
                period=period,
                metric=table.metric,
                value=value,
                unit=row.get("UI_NM") or "",
                statbl_id=table.statbl_id,
            )
        )
    return observations


class RoneRentGateway:
    def fetch_observations(self) -> list[RentObservation]:
        """통계표 20개 순차 페이징 전량 수신 — 호출 수를 로그로 남긴다."""
        key = get_settings().rone_api_key
        calls = 0
        observations: list[RentObservation] = []
        with httpx.Client(timeout=60) as client:
            for table in _TABLES:
                fetched = 0
                page = 1
                table_observations: list[RentObservation] = []
                while True:
                    response = client.get(
                        _BASE_URL,
                        params={
                            "KEY": key,
                            "Type": "json",
                            "pIndex": page,
                            "pSize": _PAGE_SIZE,
                            "STATBL_ID": table.statbl_id,
                            "DTACYCLE_CD": "QY",
                        },
                    )
                    response.raise_for_status()
                    calls += 1
                    total, rows = parse_page(response.json())
                    fetched += len(rows)
                    table_observations.extend(to_observations(rows, table))
                    if fetched >= total or not rows:
                        break
                    page += 1
                observations.extend(table_observations)
                print(
                    f"R-ONE {table.metric}/{table.building_type}/{table.vintage}"
                    f" ({table.statbl_id}): 서울 {len(table_observations)}행"
                )
        print(f"R-ONE API 호출 {calls}건 — 서울 관측 {len(observations)}행 수신")
        return observations
