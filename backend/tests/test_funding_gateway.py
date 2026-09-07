"""bizinfo 게이트웨이 파싱 검증 — 실응답(2026-09-07 표본) 기반 픽스처, 네트워크 미사용."""

from datetime import date, datetime

from apps.funding.adapter.outbound.gateways.bizinfo_gateway import (
    clean_summary,
    parse_period,
    to_entity,
)

# 실응답 표본 축약 — 파싱에 쓰는 필드는 실제 키·형식 그대로
_ITEM = {
    "pblancId": "PBLN_000000000126191",
    "pblancNm": "[제주] 2026년 고용정착 및 인재육성 지원사업 추가모집 공고 ",
    "pblancUrl": "https://www.bizinfo.go.kr/sii/siia/selectSIIA200Detail.do?pblancId=PBLN_000000000126191",
    "jrsdInsttNm": "고용노동부",
    "excInsttNm": "제주콘텐츠진흥원",
    "pldirSportRealmLclasCodeNm": "인력",
    "pldirSportRealmMlsfcCodeNm": "고용환경개선",
    "trgetNm": "중소기업",
    "hashtags": "인력,제주,고용정착,2026",
    "reqstBeginEndDe": "2026-09-03 ~ 2026-09-17",
    "bsnsSumryCn": "<p>신규 정규직 채용을 지원하고,&nbsp;장려금 지원</p><p><br></p>",
    "creatPnttm": "2026-09-04 15:03:04",
    "updtPnttm": "2026-09-04 15:51:29",
}


def test_to_entity_maps_real_response_fields():
    entity = to_entity(_ITEM)
    assert entity.program_id == "PBLN_000000000126191"
    assert entity.source == "bizinfo"
    assert entity.title == "[제주] 2026년 고용정착 및 인재육성 지원사업 추가모집 공고"
    assert entity.org == "고용노동부"
    assert entity.exec_org == "제주콘텐츠진흥원"
    assert entity.field_category == "인력"
    assert entity.target_text == "중소기업"  # 원문 그대로 보존 (LLM 추출 원천)
    assert entity.hashtags == "인력,제주,고용정착,2026"
    assert entity.url.endswith("PBLN_000000000126191")
    assert entity.apply_begin == date(2026, 9, 3)
    assert entity.deadline == date(2026, 9, 17)
    assert entity.summary == "신규 정규직 채용을 지원하고, 장려금 지원"  # 태그·엔티티 제거
    assert entity.posted_at == datetime(2026, 9, 4, 15, 3, 4)
    assert entity.source_updated_at == datetime(2026, 9, 4, 15, 51, 29)
    assert entity.is_expired is False


def test_to_entity_drops_item_without_id_or_url():
    assert to_entity({**_ITEM, "pblancId": ""}) is None
    assert to_entity({k: v for k, v in _ITEM.items() if k != "pblancUrl"}) is None


def test_parse_period_defensive_variants():
    assert parse_period("2026-02-10 ~ 2026-11-13") == (date(2026, 2, 10), date(2026, 11, 13))
    assert parse_period("2026-09-03 ~") == (date(2026, 9, 3), None)  # 마감 미상
    assert parse_period("상시") == (None, None)
    assert parse_period("예산 소진시까지") == (None, None)
    assert parse_period("") == (None, None)
    assert parse_period(None) == (None, None)
    assert parse_period("2026-13-99 ~ 2026-11-13") == (date(2026, 11, 13), None)  # 비정상 날짜 방어


def test_clean_summary_truncates_and_handles_empty():
    assert clean_summary(None) is None
    assert clean_summary("<p><br></p>") is None
    assert len(clean_summary("<p>" + "가" * 2000 + "</p>")) == 1000  # 발췌 상한
