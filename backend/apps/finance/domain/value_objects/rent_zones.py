"""구 → R-ONE 임대동향 권역 매핑 (설계서 §4-3).

R-ONE은 행정동이 아니라 상권(서울 83)·권역(4)·시도(1) 단위다. 동 단위 임대료 자료가 없으므로 구가 속한
권역의 평균으로 근사한다. 매핑은 적재된 상권 83개의 `region_path`를 구별로 대조해 정했다(2026-09-23,
`rent_price` 2026Q2):

- 강남 — 테헤란로·강남대로·도산대로·압구정·청담·신사역·논현역·학동/강남구청역(강남구) ·
  서초·교대역·양재역·양재말죽거리·남부터미널·서래마을·방배역/내방역(서초구)
- 도심 — 명동·을지로·충무로·남대문·동대문·방산시장·시청(중구) · 종로·광화문·북촌·서촌(종로구)
- 영등포신촌 — 영등포·영등포역·당산역(영등포구) · 홍대합정·홍대/합정·동교/연남·망원역·공덕역(마포구) ·
  신촌·신촌/이대(서대문구)
- 기타 — 나머지 전부. **송파(잠실·가락시장)·용산(이태원·용산역)도 R-ONE에서는 기타다.**

구 단위 근사의 한계: 혜화동(종로구)·약수역(중구)은 R-ONE이 기타로 두지만 구 단위로는 도심에 묶인다.
값은 "참고"이며 응답의 caveat가 그 사실을 말한다.
"""

ZONE_GANGNAM = "서울>강남"
ZONE_DOWNTOWN = "서울>도심"
ZONE_YEONGDEUNGPO_SINCHON = "서울>영등포신촌"
ZONE_OTHER = "서울>기타"

RENT_ZONES: tuple[str, ...] = (ZONE_GANGNAM, ZONE_DOWNTOWN, ZONE_YEONGDEUNGPO_SINCHON, ZONE_OTHER)

# district_code → 권역 region_path. 25구 전부.
RENT_ZONE_BY_DISTRICT: dict[str, str] = {
    "11110": ZONE_DOWNTOWN,  # 종로구
    "11140": ZONE_DOWNTOWN,  # 중구
    "11170": ZONE_OTHER,  # 용산구 — R-ONE 이태원·용산역은 기타
    "11200": ZONE_OTHER,  # 성동구 — 뚝섬·왕십리
    "11215": ZONE_OTHER,  # 광진구 — 건대입구·군자·구의역
    "11230": ZONE_OTHER,  # 동대문구 — 청량리·경희대·장안동
    "11260": ZONE_OTHER,  # 중랑구 — 상봉역
    "11290": ZONE_OTHER,  # 성북구 — 성신여대
    "11305": ZONE_OTHER,  # 강북구 — 수유·미아사거리
    "11320": ZONE_OTHER,  # 도봉구 — 쌍문역
    "11350": ZONE_OTHER,  # 노원구 — 상계역
    "11380": ZONE_OTHER,  # 은평구 — 연신내·불광역
    "11410": ZONE_YEONGDEUNGPO_SINCHON,  # 서대문구 — 신촌·신촌/이대
    "11440": ZONE_YEONGDEUNGPO_SINCHON,  # 마포구 — 홍대합정·동교/연남·망원역·공덕역
    "11470": ZONE_OTHER,  # 양천구 — 목동
    "11500": ZONE_OTHER,  # 강서구 — 화곡·까치산역
    "11530": ZONE_OTHER,  # 구로구 — 구로디지털단지역·오류동역
    "11545": ZONE_OTHER,  # 금천구 — 독산/시흥
    "11560": ZONE_YEONGDEUNGPO_SINCHON,  # 영등포구 — 영등포·영등포역·당산역
    "11590": ZONE_OTHER,  # 동작구 — 사당·노량진
    "11620": ZONE_OTHER,  # 관악구 — 신림역·서울대입구역·낙성대
    "11650": ZONE_GANGNAM,  # 서초구 — 서초·교대역·양재역·서래마을·방배역
    "11680": ZONE_GANGNAM,  # 강남구 — 테헤란로·강남대로·압구정·청담·신사역
    "11710": ZONE_OTHER,  # 송파구 — R-ONE 잠실·가락시장은 기타
    "11740": ZONE_OTHER,  # 강동구 — 천호
}


def rent_zone_of(district_code: str) -> str | None:
    """구 코드 → 권역. 서울 밖(미등록)이면 None."""
    return RENT_ZONE_BY_DISTRICT.get(district_code)
