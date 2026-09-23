"""시간대 어긋남 배치 검증 — 보정 후 뺄셈·부호·결측 건너뛰기·멱등 (Fake 포트, 설계서 §4-2)."""

import pytest

from apps.metric.app.dtos.region_industry_hour_gap_dto import (
    RegionHourValues,
    RegionIndustryHourSales,
)
from apps.metric.app.ports.output.region_industry_hour_gap_port import (
    RegionFootfallHourPort,
    RegionIndustryHourGapRepositoryPort,
    RegionIndustryHourSalesPort,
)
from apps.metric.app.use_cases.region_industry_hour_gap_interactor import (
    RegionIndustryHourGapInteractor,
)
from apps.metric.domain.entities.region_industry_hour_gap_entity import (
    RegionIndustryHourGap,
)

_UNIFORM = {"00_06": 6, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 4, "21_24": 3}


class FakeRepository(RegionIndustryHourGapRepositoryPort):
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str, str, str], RegionIndustryHourGap] = {}

    def upsert(self, gaps: list[RegionIndustryHourGap]) -> int:
        for gap in gaps:
            self.rows[(gap.region_code, gap.industry_id, gap.year_quarter, gap.hour_band)] = gap
        return len(gaps)

    def list_bands(self, region_code, industry_id, year_quarter):
        return [
            gap
            for key, gap in sorted(self.rows.items())
            if key[:3] == (region_code, industry_id, year_quarter)
        ]

    def latest_quarter(self, region_code, industry_id):
        quarters = [k[2] for k in self.rows if k[:2] == (region_code, industry_id)]
        return max(quarters) if quarters else None


class FakeFootfall(RegionFootfallHourPort):
    def __init__(self, rows: list[RegionHourValues]) -> None:
        self._rows = rows
        self.requested: list[str] | None = None

    def hour_values(self, quarters: list[str]) -> list[RegionHourValues]:
        self.requested = quarters
        return [r for r in self._rows if r.year_quarter in quarters]


class FakeSales(RegionIndustryHourSalesPort):
    def __init__(self, rows: list[RegionIndustryHourSales]) -> None:
        self._rows = rows

    def hour_sales(self, quarters: list[str]) -> list[RegionIndustryHourSales]:
        return [r for r in self._rows if r.year_quarter in quarters]


def _build(footfall, sales, quarters=("20251",)):
    repository = FakeRepository()
    gateway = FakeFootfall(footfall)
    processed = RegionIndustryHourGapInteractor(
        repository=repository, footfall=gateway, sales=FakeSales(sales)
    ).build(list(quarters))
    return repository, gateway, processed


def test_한_조합이_6구간_행을_만든다():
    repository, _, processed = _build(
        [RegionHourValues("11110", "20251", dict(_UNIFORM))],
        [RegionIndustryHourSales("11110", "cafe", "20251", dict(_UNIFORM))],
    )

    assert processed == 6
    assert len(repository.list_bands("11110", "cafe", "20251")) == 6


def test_유동과_매출이_같은_모양이면_어긋남이_0이다():
    repository, _, _ = _build(
        [RegionHourValues("11110", "20251", dict(_UNIFORM))],
        # 크기만 다르고 시간 분포가 같다 — 강도로 보면 동일하다
        [RegionIndustryHourSales("11110", "cafe", "20251", {k: v * 1000 for k, v in _UNIFORM.items()})],
    )

    assert all(
        gap.gap == pytest.approx(0.0)
        for gap in repository.list_bands("11110", "cafe", "20251")
    )


def test_출근길_매출이_앞서면_06_11_어긋남이_양수다():
    # 업무 밀집형 동의 카페 모양 — 사람은 고르게 있는데 돈은 아침에 돈다 (설계서 §6-6 부호 검증)
    repository, _, _ = _build(
        [RegionHourValues("11110", "20251", dict(_UNIFORM))],
        [
            RegionIndustryHourSales(
                "11110",
                "cafe",
                "20251",
                {"00_06": 1, "06_11": 60, "11_14": 10, "14_17": 10, "17_21": 8, "21_24": 1},
            )
        ],
    )

    bands = {gap.hour_band: gap for gap in repository.list_bands("11110", "cafe", "20251")}
    assert bands["06_11"].gap > 0
    assert bands["00_06"].gap < 0


def test_원값으로_빼면_뒤집히는_경우를_보정이_막는다():
    # 00_06 원값이 매출에서 가장 크지만 6시간짜리라 시간당으로는 가장 약하다
    sales = {"00_06": 20, "06_11": 18, "11_14": 15, "14_17": 15, "17_21": 18, "21_24": 14}
    repository, _, _ = _build(
        [RegionHourValues("11110", "20251", dict(_UNIFORM))],
        [RegionIndustryHourSales("11110", "cafe", "20251", sales)],
    )

    bands = {gap.hour_band: gap for gap in repository.list_bands("11110", "cafe", "20251")}
    assert max(sales, key=lambda k: sales[k]) == "00_06"
    assert bands["00_06"].gap < 0  # 보정 없이 뺐다면 양수로 나왔을 자리다


def test_유동인구가_없는_동은_행을_만들지_않는다():
    repository, _, processed = _build(
        [], [RegionIndustryHourSales("11110", "cafe", "20251", dict(_UNIFORM))]
    )

    assert processed == 0 and repository.rows == {}


def test_매출이_전부_0이면_행을_만들지_않는다():
    repository, _, processed = _build(
        [RegionHourValues("11110", "20251", dict(_UNIFORM))],
        [RegionIndustryHourSales("11110", "cafe", "20251", dict.fromkeys(_UNIFORM, 0))],
    )

    assert processed == 0


def test_요청한_분기만_읽는다():
    _, gateway, _ = _build([], [], quarters=("20251", "20252"))

    assert gateway.requested == ["20251", "20252"]


def test_재실행해도_행_수가_늘지_않는다():
    footfall = [RegionHourValues("11110", "20251", dict(_UNIFORM))]
    sales = [RegionIndustryHourSales("11110", "cafe", "20251", dict(_UNIFORM))]
    repository = FakeRepository()
    interactor = RegionIndustryHourGapInteractor(
        repository=repository, footfall=FakeFootfall(footfall), sales=FakeSales(sales)
    )

    interactor.build(["20251"])
    interactor.build(["20251"])

    assert len(repository.rows) == 6


def test_최신_분기_6구간은_분기를_몰라도_꺼낼_수_있다():
    footfall = [RegionHourValues("11110", q, dict(_UNIFORM)) for q in ("20251", "20252")]
    sales = [RegionIndustryHourSales("11110", "cafe", q, dict(_UNIFORM)) for q in ("20251", "20252")]
    repository = FakeRepository()
    interactor = RegionIndustryHourGapInteractor(
        repository=repository, footfall=FakeFootfall(footfall), sales=FakeSales(sales)
    )
    interactor.build(["20251", "20252"])

    bands = interactor.list_latest_bands("11110", "cafe")

    assert len(bands) == 6 and {b.year_quarter for b in bands} == {"20252"}
    assert interactor.list_latest_bands("11110", "karaoke") == []
