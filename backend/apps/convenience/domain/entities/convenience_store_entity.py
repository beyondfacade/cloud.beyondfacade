from dataclasses import dataclass

# 브랜드 키워드 사전 (§5 dict 디스패치 — if/elif 대신 순서 있는 매핑, 느슨한 키워드는 뒤로).
# 역삼1동 149건 + 전량 9,395건 기타 표본 실측 변형: 지에스25/GS25/지에스('25' 생략 상호),
# 씨유/CU/비지에프(BGF리테일 = CU 운영사), 세븐일레븐/코리아세븐/세븐(+지점 '코리아'),
# 이마트24, 미니스톱. 미확인(예: 스토리웨이·씨스페이스)은 None 보존 — 원본 상호가 진실.
_BRAND_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("GS25", ("GS25", "지에스")),
    ("CU", ("씨유", "CU", "비지에프")),
    ("이마트24", ("이마트24",)),
    ("미니스톱", ("미니스톱",)),
    ("세븐일레븐", ("세븐일레븐", "코리아세븐", "세븐")),
)


def extract_brand(name: str, branch_name: str | None) -> str | None:
    """상호+지점명에서 편의점 브랜드 추출 — 키워드 미매칭은 None (기타 브랜드)."""
    text = f"{name} {branch_name or ''}".upper()
    for brand, keywords in _BRAND_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return brand
    return None


@dataclass(frozen=True)
class ConvenienceStore:
    """편의점 현행 스냅샷 1건 — 현재 분포·경쟁밀도 축 (brainstorming §3.5).

    원천은 소진공 상가정보 sdsc2 storeListInDong(indsSclsCd=G20405 체인화 편의점).
    상가정보는 개폐업 시계열 불가(api.md §2-3 — 상가업소번호 재생성 이력)이므로
    이 스냅샷은 store/region_industry_metric에 넣지 않는다 — 개폐업 이력은
    tobacco_retailer(지정·취소일자)가 담당. 소실 추정은 first/last_seen 관측 필드로.
    """

    store_id: str  # bizesId (상가업소번호 — 역삼1동 149건 중복 0 실측)
    name: str  # bizesNm 상호명
    branch_name: str | None  # brchNm 지점명 (공란 다수)
    brand: str | None  # 상호 기반 추출 (GS25/CU/세븐일레븐/이마트24/미니스톱) — 미확인 None
    region_code: str  # 요청 행정동 10자리 — adongCd 8자리 = region_code 앞 8자리 (유일 실측)
    lat: float | None  # WGS84 (원천 제공 — 표본 149건 채움 100%)
    lng: float | None
    road_address: str | None  # rdnmAdr
    jibun_address: str | None  # lnoAdr
    source_stdr_ym: str  # 원천 기준연월 (header stdrYm — 소실 분석 시 빈티지 구분용)
