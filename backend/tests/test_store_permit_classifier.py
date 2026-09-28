"""인허가 업태 → 업종 분류기 검증 — 순수 도메인 서비스, DB 불필요."""

from apps.store.domain.services.permit_industry_classifier import (
    GENERAL_RESTAURANT_CLASSIFIER,
    RESTAURANT_OTHER,
    BusinessTypeClassifier,
    FixedIndustryClassifier,
    permit_classifier_for,
)


def test_fixed_classifier_always_returns_anchor():
    fixed = FixedIndustryClassifier("karaoke")
    assert fixed.classify("노래연습장업", "행복노래방") == "karaoke"
    assert fixed.classify(None, None) == "karaoke"
    assert fixed.industry_ids == frozenset({"karaoke"})


def test_general_restaurant_business_types_map_to_food_industries():
    c = GENERAL_RESTAURANT_CLASSIFIER
    assert c.classify("한식", "논현식당") == "korean_food"
    assert c.classify("중국식", "북경반점") == "chinese_food"
    assert c.classify("일식", "스시야") == "japanese_food"
    assert c.classify("경양식", "파스타집") == "western_food"
    assert c.classify("분식", "김밥천국") == "snack"
    assert c.classify("통닭(치킨)", "BBQ") == "chicken"
    assert c.classify("호프/통닭", "역전할머니") == "pub"


def test_unmapped_business_type_falls_back_to_other():
    c = GENERAL_RESTAURANT_CLASSIFIER
    assert c.classify("기타", "육해품") == RESTAURANT_OTHER
    assert c.classify("패스트푸드", "맘스터치") == RESTAURANT_OTHER
    assert c.classify("까페", "카페 논현") == RESTAURANT_OTHER
    assert c.classify("", "이름만") == RESTAURANT_OTHER
    assert c.classify(None, None) == RESTAURANT_OTHER


def test_temporary_marker_in_name_overrides_business_type():
    # 파일럿 '기타' 표본의 다수가 "(한시적)" 팝업 영업 — 업태가 한식이어도 판정 대상에서 뺀다
    assert GENERAL_RESTAURANT_CLASSIFIER.classify("한식", "삼원가든(한시적)") == RESTAURANT_OTHER


def test_business_type_is_normalized_for_spaces_and_unicode():
    c = BusinessTypeClassifier({"호프/통닭": "pub"}, fallback="x")
    assert c.classify(" 호프/통닭 ", "") == "pub"
    assert c.classify("호프 / 통닭", "") == "pub"
    # NFD(자소 분리)로 들어와도 같은 키
    import unicodedata

    assert c.classify(unicodedata.normalize("NFD", "호프/통닭"), "") == "pub"


def test_industry_ids_include_every_mapped_industry_and_fallback():
    ids = GENERAL_RESTAURANT_CLASSIFIER.industry_ids
    assert {"korean_food", "chinese_food", "japanese_food", "western_food", "snack", "chicken", "pub", RESTAURANT_OTHER} == ids


def test_classifier_lookup_by_slug():
    assert permit_classifier_for("general_restaurants", RESTAURANT_OTHER) is GENERAL_RESTAURANT_CLASSIFIER
    fixed = permit_classifier_for("karaoke_rooms", "karaoke")
    assert isinstance(fixed, FixedIndustryClassifier)
    assert fixed.classify("아무거나", "x") == "karaoke"
