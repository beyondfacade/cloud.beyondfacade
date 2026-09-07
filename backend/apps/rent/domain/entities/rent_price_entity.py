from dataclasses import dataclass


@dataclass(frozen=True)
class RentObservation:
    """R-ONE 임대동향 관측 1점 — rent_price 한 행의 한 지표(임대료 또는 공실률).

    원천이 지표별 통계표로 분리되어 있어(임대료/공실률 각각) 관측 단위로 받고,
    적재 시 같은 PK 행에 병합한다 (docs/erd.md rent_price).
    지역 단위는 자치구가 아니라 R-ONE 상권/권역/시도 — 원천 지역명을 보존한다.
    """

    id: str  # "{building_type}:{cls_id}:{period}" — rent_price PK
    building_type: str  # "medium_large" 중대형 상가 / "small" 소규모 상가
    cls_id: str  # R-ONE 지역 분류 ID (CLS_ID)
    region_name: str  # CLS_NM 원문 (예: "테헤란로")
    region_path: str  # CLS_FULLNM 원문 (예: "서울>강남>테헤란로")
    region_level: int  # 1 시도 / 2 권역 / 3 상권 — region_path 깊이
    period: str  # "YYYYQn" (원천 WRTTIME_IDTFR_ID "202201" → "2022Q1")
    metric: str  # "rent" 임대료 / "vacancy" 공실률
    value: float
    unit: str  # "천원/㎡" / "%"
    statbl_id: str  # 값이 나온 R-ONE 통계표 ID — 표본 개편(기준연도) 추적
