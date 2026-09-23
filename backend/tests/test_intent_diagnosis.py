"""한 줄 진단 조립 검증 — LLM 없이 어휘 테이블로만 문장을 만든다 (설계서 §6)."""

from apps.intent.domain.services.diagnosis import (
    PeakSalesBand,
    ProfileFacts,
    compose_diagnosis,
)


def _profile(**overrides) -> ProfileFacts:
    base = dict(
        region_name="역삼1동",
        type_code="office",
        type_reason="직장인구가 상주인구의 5.9배로 서울 상위 10%이고, 주말 유동이 평일보다 적습니다.",
        time_label="day",
        year_quarter="20262",
    )
    return ProfileFacts(**{**base, **overrides})


def test_정상_동은_유형과_매출_정점_구간을_한_문장으로_잇는다():
    diagnosis = compose_diagnosis(
        _profile(), "카페", PeakSalesBand(hour_band="11_14", year_quarter="20254")
    )

    assert diagnosis.sentence == "역삼1동은 낮 인구 우위형이고, 카페는 점심(11~14시)에 돈이 돕니다."
    assert diagnosis.type_name == "낮 인구 우위형"
    assert diagnosis.peak_sales_band == "11_14"
    assert diagnosis.hour_gap_quarter == "20254"


def test_조사는_받침에_따라_은_는을_고른다():
    diagnosis = compose_diagnosis(
        _profile(region_name="연남동"), "노래방", PeakSalesBand("21_24", "20254")
    )

    assert diagnosis.sentence.startswith("연남동은 ")
    assert "노래방은 밤(21~24시)에" in diagnosis.sentence


def test_혼합형은_뚜렷한_특징이_없다고_말한다():
    diagnosis = compose_diagnosis(
        _profile(type_code="mixed", type_reason="어느 축에서도 서울 상위·하위 경계를 넘지 않습니다."),
        "카페",
        PeakSalesBand("11_14", "20254"),
    )

    assert diagnosis.sentence.startswith("역삼1동은 뚜렷한 특징이 없는 혼합형이고,")


def test_재건축_동은_유형_대신_근거_문장을_그대로_쓴다():
    # 상주인구 하한에 걸린 동에 억지로 유형을 붙이지 않는다 (분류 문서 §7-3)
    reason = "상주인구가 비정상적으로 적어(재건축 등) 비율 판정을 적용하지 않았습니다."
    diagnosis = compose_diagnosis(
        _profile(region_name="둔촌제1동", type_code="mixed", type_reason=reason),
        "카페",
        PeakSalesBand("11_14", "20254"),
    )

    assert diagnosis.sentence == f"둔촌제1동은 {reason}"
    assert diagnosis.peak_sales_band is None


def test_매출_구간이_없으면_뒤_절을_뺀다():
    diagnosis = compose_diagnosis(_profile(), "카페", None)

    assert diagnosis.sentence == "역삼1동은 낮 인구 우위형입니다."
    assert diagnosis.peak_sales_band is None and diagnosis.hour_gap_quarter is None
