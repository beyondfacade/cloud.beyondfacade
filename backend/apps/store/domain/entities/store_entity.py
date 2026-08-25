from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Store:
    """점포 (인허가 단위) — 개폐업 시계열의 기본 레코드."""

    store_id: str  # 인허가 관리번호(MNG_NO)
    name: str
    industry_id: str
    district_code: str
    open_date: date | None  # 인허가일자(LCPMT_YMD)
    close_date: date | None  # 폐업일자(CLSBIZ_YMD)
    status_code: str  # 상세영업상태코드(DTL_SALS_STTS_CD)
    status_name: str
    lat: float | None
    lng: float | None
    source_updated_at: datetime  # 데이터갱신시점(DAT_UPDT_PNT) — 증분 수집 커서
    region_code: str | None = None  # 행정동 — 경계 공간조인 후 채움
    subcategory_id: str | None = None
