"""SeoulAcademyGateway 파싱 단위 검증 — OA-20528 실응답 픽스처 기반 (2026-09-07)."""

from datetime import date, datetime

from apps.store.adapter.outbound.gateways.seoul_academy_gateway import (
    SeoulAcademyGateway,
    _build_courses,
    _parse_fee_items,
    _parse_ymd,
)

_DISTRICTS = {"동대문구": "11230", "강남구": "11680"}

# 2026-09-07 실응답 1행 (동대문구 국제전자과학학원) 축약
_ITEM = {
    "ADMDST_NM": "동대문구",
    "PEI_TRNG_NM": "학원",
    "PEI_DSGN_NO": "1000000083",
    "PEI_NM": "국제전자과학학원",
    "ESTBL_YMD": "19680210",
    "REG_YMD": "19680210",
    "REG_STTS_NM": "개원",
    "PSCP_SUM": "30",
    "FLD_NM": "직업기술",
    "TRNG_CRS_LIST_NM": "전자,",
    "TRNG_CRS_NM": "전자",
    "INDV_ATNLC_AMT_CN": "",
    "LOAD_DT": "20231018",
}


def test_parse_ymd_normal_empty_and_garbage():
    assert _parse_ymd("19681227") == date(1968, 12, 27)
    assert _parse_ymd("") is None
    assert _parse_ymd(None) is None
    assert _parse_ymd("날짜아님") is None
    assert _parse_ymd("20060229") == date(2006, 2, 28)  # 불량 일 클램프 (MOIS 전례)


def test_parse_fee_items_name_amount_pairs():
    items = _parse_fee_items("고등영어:300000, 초등영어A:150000")
    assert items == [("고등영어", 300000), ("초등영어A", 150000)]


def test_parse_fee_items_non_numeric_amount_kept_as_name():
    assert _parse_fee_items("상담 후 결정") == [("상담 후 결정", None)]
    assert _parse_fee_items("") == []


def test_build_courses_prefers_fee_items_over_curriculum():
    item = {**_ITEM, "INDV_ATNLC_AMT_CN": "전자기초:100000"}
    courses = _build_courses("academy:seoul:1", item)
    assert [(c.course_name, c.tuition_fee) for c in courses] == [("전자기초", 100000)]
    assert courses[0].course_id == "academy:seoul:1:1"
    assert courses[0].target_grade is None  # LLM 추출 후속 — 원문(course_name)만 보존


def test_build_courses_falls_back_to_curriculum_list():
    courses = _build_courses("academy:seoul:1", _ITEM)
    assert [(c.course_name, c.tuition_fee) for c in courses] == [("전자", None)]


def test_to_record_maps_store_fields_and_subcategory():
    gateway = SeoulAcademyGateway(district_codes=_DISTRICTS)
    record = gateway._to_record(_ITEM)
    store = record.store
    assert store.store_id == "academy:seoul:1000000083"
    assert store.industry_id == "academy"
    assert store.district_code == "11230"
    assert store.subcategory_id == "academy_vocational"  # 직업기술 → dict 디스패치
    assert (store.status_code, store.status_name) == ("open", "개원")
    assert store.open_date == date(1968, 2, 10)
    assert (store.lat, store.lng) == (None, None)  # 원천 좌표 없음 — SGIS 지오코딩 후속
    assert store.source_updated_at == datetime(2023, 10, 18)


def test_to_record_unmapped_field_leaves_subcategory_null():
    record = SeoulAcademyGateway(district_codes=_DISTRICTS)._to_record(
        {**_ITEM, "FLD_NM": "종합(대)"}
    )
    assert record.store.subcategory_id is None


def test_to_record_empty_district_parsed_from_road_address():
    # 자치구명 공란 행 실존 (2026-09-07 전량 중 40행) — 도로명주소 두 번째 어절로 복구
    record = SeoulAcademyGateway(district_codes=_DISTRICTS)._to_record(
        {**_ITEM, "ADMDST_NM": "", "ROAD_NM_ADDR": "서울특별시 강남구 테헤란로 1"}
    )
    assert record.store.district_code == "11680"


def test_to_record_unknown_district_skipped_and_counted():
    gateway = SeoulAcademyGateway(district_codes={"강남구": "11680"})
    assert gateway._to_record(_ITEM) is None
    assert gateway.skipped_districts == {"동대문구": 1}
