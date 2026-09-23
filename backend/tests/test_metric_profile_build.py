"""동네 프로필 배치 검증 — 4분기 평활·임계 재계산·결측 처리·멱등 (Fake 포트, 설계서 §5·§8)."""

import pytest

from apps.metric.app.dtos.region_profile_dto import RegionQuarterObservation
from apps.metric.app.ports.output.region_profile_port import (
    NeighborhoodObservationPort,
    RegionProfileRepositoryPort,
)
from apps.metric.app.use_cases.region_profile_interactor import RegionProfileInteractor
from apps.metric.domain.entities.region_profile_entity import RegionProfile

_UNIFORM_HOURS = {"00_06": 6, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 4, "21_24": 3}
_FLAT_DOW = dict.fromkeys(["mon", "tue", "wed", "thu", "fri", "sat", "sun"], 100)


class FakeRepository(RegionProfileRepositoryPort):
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], RegionProfile] = {}
        self.upsert_calls = 0

    def upsert(self, profiles: list[RegionProfile]) -> int:
        self.upsert_calls += 1
        for profile in profiles:
            self.rows[(profile.region_code, profile.year_quarter)] = profile
        return len(profiles)

    def find(self, region_code: str, year_quarter: str) -> RegionProfile | None:
        return self.rows.get((region_code, year_quarter))

    def find_latest(self, region_code: str) -> RegionProfile | None:
        candidates = [p for p in self.rows.values() if p.region_code == region_code]
        return max(candidates, key=lambda p: p.year_quarter) if candidates else None


class FakeObservations(NeighborhoodObservationPort):
    def __init__(self, observations: list[RegionQuarterObservation]) -> None:
        self._observations = observations
        self.requested: list[str] | None = None

    def quarter_observations(self, quarters: list[str]) -> list[RegionQuarterObservation]:
        self.requested = quarters
        return [o for o in self._observations if o.year_quarter in quarters]


def _observation(region_code: str, year_quarter: str, **overrides) -> RegionQuarterObservation:
    base = dict(
        worker_total=2_000,
        resident_total=20_000,
        footfall_by_hour=dict(_UNIFORM_HOURS),
        footfall_by_dow=dict(_FLAT_DOW),
        footfall_20s=120.0,
        footfall_age_total=1_000.0,
        spending_total=1_000_000,
        spending_fnb=220_000,
        facility_total=90,
        university_count=0,
    )
    return RegionQuarterObservation(
        region_code=region_code, year_quarter=year_quarter, **{**base, **overrides}
    )


def _build(observations, quarters):
    repository = FakeRepository()
    gateway = FakeObservations(observations)
    processed = RegionProfileInteractor(
        repository=repository, observations=gateway
    ).build(quarters)
    return repository, gateway, processed


def test_창은_대상_분기를_포함한_직전_4분기를_요구한다():
    _, gateway, _ = _build([_observation("11110", "20214")], ["20214"])

    assert gateway.requested == ["20211", "20212", "20213", "20214"]


def test_창이_연도_경계를_넘어간다():
    _, gateway, _ = _build([_observation("11110", "20221")], ["20221"])

    assert gateway.requested == ["20212", "20213", "20214", "20221"]


def test_앞_분기가_없으면_가용한_만큼만_쓴다():
    repository, _, processed = _build([_observation("11110", "20211")], ["20211"])

    assert processed == 1
    assert repository.find("11110", "20211") is not None


def test_판정은_분기_단독이_아니라_4분기_평균으로_한다():
    # 마지막 분기만 직장비가 폭발해도 평균이 낮으면 업무 밀집형이 되지 않는다
    조용한동 = [_observation("11110", q) for q in ["20211", "20212", "20213"]]
    조용한동.append(_observation("11110", "20214", worker_total=200_000))
    비교군 = [
        _observation(f"1112{i}", q, worker_total=1_000)
        for i in range(5)
        for q in ["20211", "20212", "20213", "20214"]
    ]

    repository, _, _ = _build([*조용한동, *비교군], ["20214"])

    profile = repository.find("11110", "20214")
    assert profile is not None
    # (2천×3 + 20만) ÷ 4분기 = 51,500 → 직장비 2.575.
    # 평활 없이 20254 단독이었다면 10.0으로 찍혔을 것이다
    assert profile.worker_resident_ratio == pytest.approx(2.575)


def test_직장인구_결측_동은_비율이_None으로_남는다():
    # 비교군을 둔다 — 동 하나짜리 분포에서는 그 동이 모든 분위수의 경계라 판정이 무의미해진다
    비교군 = [_observation(f"1112{i}", "20211", spending_fnb=400_000) for i in range(9)]
    repository, _, _ = _build(
        [_observation("11110", "20211", worker_total=None), *비교군], ["20211"]
    )

    profile = repository.find("11110", "20211")
    assert profile is not None and profile.worker_resident_ratio is None
    assert profile.neighborhood_type == "residential"


def test_상주인구_하한에_걸린_동은_혼합형으로_간다():
    # 반포본동 모양 — 직장비 48.5지만 분모가 비정상이다
    이주중 = _observation("11110", "20211", resident_total=117, worker_total=5_675)
    정상 = [_observation(f"1112{i}", "20211") for i in range(99)]

    repository, _, _ = _build([이주중, *정상], ["20211"])

    profile = repository.find("11110", "20211")
    assert profile is not None
    assert profile.neighborhood_type == "mixed" and "재건축" in profile.type_reason


def test_심야지수는_시간당_보정을_거친_값이다():
    # 00_06(6h) 원값이 압도적이어도 균등 입력이면 지수는 1.0이다
    repository, _, _ = _build([_observation("11110", "20211")], ["20211"])

    profile = repository.find("11110", "20211")
    assert profile is not None and profile.night_index == pytest.approx(1.0)


def test_주말지수는_요일_일평균_비로_낸다():
    주말강세 = _observation(
        "11110",
        "20211",
        footfall_by_dow={**_FLAT_DOW, "sat": 200, "sun": 200},
    )

    repository, _, _ = _build([주말강세], ["20211"])

    profile = repository.find("11110", "20211")
    assert profile is not None and profile.weekend_index == pytest.approx(2.0)


def test_여러_분기를_한_번에_만들면_분기마다_행이_생긴다():
    observations = [
        _observation(rc, q)
        for rc in ["11110", "11120"]
        for q in ["20211", "20212", "20213", "20214"]
    ]

    repository, _, processed = _build(observations, ["20213", "20214"])

    assert processed == 4
    assert len(repository.rows) == 4


def test_재실행해도_행_수가_늘지_않고_값이_갱신된다():
    observations = [_observation("11110", "20211")]
    repository = FakeRepository()
    interactor = RegionProfileInteractor(
        repository=repository, observations=FakeObservations(observations)
    )

    interactor.build(["20211"])
    interactor.build(["20211"])

    assert repository.upsert_calls == 2
    assert len(repository.rows) == 1
