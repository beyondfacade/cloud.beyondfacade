"""유형 판정 결정 목록 검증 — 규칙 순서·임계 재계산·예외 처리 (설계서 §5, 분류 문서 §4-1)."""

import pytest

from apps.metric.domain.services.typology import (
    TypologyInput,
    TypologyThresholds,
    classify,
    derive_thresholds,
)

_BASE = dict(
    worker_resident_ratio=0.2,
    weekend_index=1.02,
    night_index=1.05,
    footfall_20s_share=0.12,
    fnb_share=0.22,
    fnb_amount_per_resident=50_000.0,
    facility_total=90,
    resident_total=20_000,
    university_count=0,
)

_THRESHOLDS = TypologyThresholds(
    worker_resident_q90=1.491,
    weekend_q50=1.029,
    university_median_positive=3,
    footfall_20s_q90=0.2207,
    fnb_per_resident_q75=102_484.0,
    fnb_share_q50=0.2429,
    fnb_share_q75=0.3202,
    night_q25=0.9792,
    night_q50=1.0737,
    facility_q75=154,
    resident_floor=1_000,
)


def _input(**overrides) -> TypologyInput:
    return TypologyInput(**{**_BASE, **overrides})


def test_R1_업무_밀집형은_직장비_상위10퍼센트와_주말_감소를_함께_요구한다():
    verdict = classify(_input(worker_resident_ratio=2.714, weekend_index=0.81), _THRESHOLDS)

    assert verdict.type_code == "office"
    assert "2.7배" in verdict.reason and "상위 10%" in verdict.reason


def test_R1은_주말지수가_중앙값_이상이면_통과하지_못한다():
    verdict = classify(_input(worker_resident_ratio=2.714, weekend_index=1.20), _THRESHOLDS)

    assert verdict.type_code != "office"


def test_직장인구_결측_동은_업무_밀집형이_될_수_없다():
    verdict = classify(
        _input(worker_resident_ratio=None, weekend_index=0.5, night_index=1.2), _THRESHOLDS
    )

    assert verdict.type_code == "residential"


def test_R2_대학가형은_대학수와_20대_비중을_함께_요구한다():
    verdict = classify(_input(university_count=4, footfall_20s_share=0.299), _THRESHOLDS)

    assert verdict.type_code == "campus"
    assert "29.9%" in verdict.reason


def test_업무_밀집형이_대학가형보다_앞선다():
    # 명동·종로처럼 대학 건물과 20대가 함께 있는 도심이 대학가형으로 새지 않아야 한다
    verdict = classify(
        _input(
            worker_resident_ratio=3.0,
            weekend_index=0.8,
            university_count=4,
            footfall_20s_share=0.30,
        ),
        _THRESHOLDS,
    )

    assert verdict.type_code == "office"


def test_대학가형이_먹자형보다_앞선다():
    # 화양동·신촌동처럼 외식 결제가 큰 대학가가 먹자형으로 새지 않아야 한다
    verdict = classify(
        _input(
            university_count=4,
            footfall_20s_share=0.30,
            fnb_amount_per_resident=200_000.0,
            fnb_share=0.36,
        ),
        _THRESHOLDS,
    )

    assert verdict.type_code == "campus"


def test_R3_먹자형_A분기는_1인당_결제액과_비중을_함께_본다():
    verdict = classify(
        _input(fnb_amount_per_resident=200_000.0, fnb_share=0.30), _THRESHOLDS
    )

    assert verdict.type_code == "dining"
    assert "200,000원" in verdict.reason


def test_R3_먹자형_B분기는_비중_상위25퍼센트와_낮은_심야체류를_본다():
    verdict = classify(
        _input(fnb_amount_per_resident=10.0, fnb_share=0.36, night_index=0.90), _THRESHOLDS
    )

    assert verdict.type_code == "dining"
    assert "36.0%" in verdict.reason


def test_R4_생활_중심형은_집객시설_상위25퍼센트와_낮_우위를_본다():
    verdict = classify(_input(facility_total=192, night_index=1.02), _THRESHOLDS)

    assert verdict.type_code == "hub"
    assert "192개" in verdict.reason


def test_R5_주거형_근거문장은_직장인구_결측이면_앞절을_뺀다():
    있음 = classify(_input(worker_resident_ratio=0.07, night_index=1.13), _THRESHOLDS)
    없음 = classify(_input(worker_resident_ratio=None, night_index=1.13), _THRESHOLDS)

    assert 있음.type_code == 없음.type_code == "residential"
    assert "직장인구가 상주인구보다 적고" in 있음.reason
    assert "직장인구" not in 없음.reason


def test_R6_혼합형이_최후의_보루다():
    verdict = classify(_input(worker_resident_ratio=1.2, night_index=0.90), _THRESHOLDS)

    assert verdict.type_code == "mixed"
    assert "어느 축에서도" in verdict.reason


def test_상주인구_하한에_걸린_동은_비율_판정을_건너뛰고_혼합형이_된다():
    # 반포본동(상주 117명) — 재건축 이주로 직장÷상주가 48.5까지 치솟는다 (설계서 §3-3)
    verdict = classify(
        _input(resident_total=117, worker_resident_ratio=48.5, weekend_index=0.5),
        _THRESHOLDS,
    )

    assert verdict.type_code == "mixed"
    assert "재건축" in verdict.reason


def test_임계값은_주어진_분포에서_매번_다시_계산된다():
    inputs = [
        _input(worker_resident_ratio=r, facility_total=f, night_index=n, university_count=u)
        for r, f, n, u in [(0.1, 10, 0.9, 0), (0.5, 50, 1.0, 2), (1.0, 100, 1.1, 0), (5.0, 200, 1.3, 6)]
    ]

    thresholds = derive_thresholds(inputs)

    assert thresholds.worker_resident_q90 == pytest.approx(3.8)
    assert thresholds.facility_q75 == pytest.approx(125.0)
    # 대학 수 중앙값은 "대학이 있는 동"만 대상으로 한다
    assert thresholds.university_median_positive == pytest.approx(4.0)


def test_임계값_계산은_직장인구_결측_동을_직장비_분포에서_제외한다():
    inputs = [_input(worker_resident_ratio=None), _input(worker_resident_ratio=2.0)]

    thresholds = derive_thresholds(inputs)

    assert thresholds.worker_resident_q90 == pytest.approx(2.0)
