"""region_facts_gateway의 해석 주의 생성 검증 — 해당하는 주의만 붙는다 (DB 없음)."""

from dataclasses import dataclass

from apps.agent.adapter.outbound.gateways.region_facts_gateway import _profile_caveats


@dataclass
class FakeProfile:
    worker_resident_ratio: float | None = 1.2
    type_reason: str = "어느 축에서도 서울 상위·하위 경계를 넘지 않습니다."


def _texts(profile, facilities=()) -> str:
    return " ".join(_profile_caveats(profile, list(facilities)))


def test_직장인구_결측_동에만_0으로_읽지_말라는_주의가_붙는다():
    있음 = _texts(FakeProfile(worker_resident_ratio=None))
    없음 = _texts(FakeProfile(worker_resident_ratio=2.0))

    assert "0명으로 읽지" in 있음
    assert "0명으로 읽지" not in 없음


def test_재건축_판정_동에만_비율_불신_주의가_붙는다():
    있음 = _texts(
        FakeProfile(type_reason="상주인구가 비정상적으로 적어(재건축 등) 비율 판정을 적용하지 않았습니다.")
    )
    없음 = _texts(FakeProfile())

    assert "비율로 단정하지" in 있음
    assert "비율로 단정하지" not in 없음


def test_집객시설_1위가_버스정거장일_때만_그_주의가_붙는다():
    # 늘 붙는 문구는 읽히지 않는다 — 역삼1동처럼 약국·은행이 1위인 동에는 달지 않는다
    버스 = _texts(FakeProfile(), [{"type": "버스정거장", "count": 120}])
    약국 = _texts(FakeProfile(), [{"type": "약국", "count": 64}])

    assert "버스정거장" in 버스
    assert "버스정거장" not in 약국


def test_아파트_평균_시가_주의는_항상_붙는다():
    # 값 자체가 늘 이상치 위험을 갖는다 (원천 편차가 극단적)
    assert "참고값" in _texts(FakeProfile())
