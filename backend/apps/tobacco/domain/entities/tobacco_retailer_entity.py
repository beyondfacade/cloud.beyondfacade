from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class TobaccoRetailer:
    """담배소매인 지정 1건 — 편의점 출점 가능성 분석의 결정 변수 (brainstorming §3.5).

    원천은 지방행정 인허가 「기타_담배소매업」 서울 아카이브 CSV
    (data/raw/tobacco_retail/, 2026-08-25 확보 — 실컬럼 기반, 95,402행 실측).
    지정일자·폐업/취소일자·상세영업상태가 있어 지정·폐지 시계열 분석 대상.
    """

    retailer_id: str  # 관리번호 (서울 전체에서 유일 — 95,402행 중복 0 실측)
    name: str  # 사업장명
    district_code: str  # 개방자치단체코드 → district.opn_authority_code 매핑
    status_code: str  # 상세영업상태코드 (0 정상영업 ~ 6 영업정지)
    status_name: str  # 상세영업상태명 (정상영업/폐업처리/직권취소/지정취소 …)
    designated_date: date | None  # 지정일자 (실측 채움 76.0%)
    permit_date: date | None  # 인허가일자
    close_date: date | None  # 폐업일자
    cancel_date: date | None  # 인허가취소일자 — 지정취소·직권취소의 폐지 시점
    lat: float | None  # EPSG:5174 → WGS84 변환값 (store BC 전례)
    lng: float | None
    road_address: str | None  # 도로명주소 (채움 85.9%) — 표시용
    jibun_address: str | None  # 지번주소 (채움 96.9%) — 좌표 결측분 지오코딩 대기열용
    source_updated_at: datetime  # 데이터갱신시점
    region_code: str | None = None  # 행정동 — 경계 공간조인 후 채움 (store 전례)
