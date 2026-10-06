"""상권 변화 상세 조회 검증 — 최신 분기 기본값·서울 평균 동봉 (Fake 포트)."""

from apps.neighborhood.app.ports.output.region_commerce_change_query_port import (
    RegionCommerceChangeQueryPort,
)
from apps.neighborhood.app.ports.output.seoul_commerce_change_baseline_query_port import (
    SeoulCommerceChangeBaselineQueryPort,
)
from apps.neighborhood.domain.entities.seoul_commerce_change_baseline_entity import (
    SeoulCommerceChangeBaseline,
)
from apps.neighborhood.app.use_cases.region_commerce_change_query_interactor import (
    RegionCommerceChangeQueryInteractor,
)
from apps.neighborhood.domain.entities.region_commerce_change_entity import (
    RegionCommerceChange,
)


def _row(region_code: str, year_quarter: str, operating_months: float | None) -> RegionCommerceChange:
    return RegionCommerceChange(
        adstrd_code=region_code[:8],
        year_quarter=year_quarter,
        change_code="LL",
        change_name="다이나믹",
        operating_months=operating_months,
        closed_months=48.0,
        region_code=region_code,
    )


class FakeQueryPort(RegionCommerceChangeQueryPort):
    def __init__(self, rows: list[RegionCommerceChange]) -> None:
        self.rows = rows

    def find(self, region_code: str, year_quarter: str) -> RegionCommerceChange | None:
        return next(
            (r for r in self.rows if r.region_code == region_code and r.year_quarter == year_quarter),
            None,
        )

    def find_latest(self, region_code: str) -> RegionCommerceChange | None:
        candidates = [r for r in self.rows if r.region_code == region_code]
        return max(candidates, key=lambda r: r.year_quarter) if candidates else None


class FakeBaselinePort(SeoulCommerceChangeBaselineQueryPort):
    def __init__(self, rows: dict[str, tuple[float, float]]) -> None:
        self.rows = rows

    def find(self, year_quarter: str) -> SeoulCommerceChangeBaseline | None:
        pair = self.rows.get(year_quarter)
        return None if pair is None else SeoulCommerceChangeBaseline(year_quarter, *pair)


_BASELINE = FakeBaselinePort({"20262": (117.0, 52.0)})  # 20253은 baseline 없음


_ROWS = [
    _row("1168064000", "20262", 110.0),
    _row("1168064000", "20253", 104.0),
]


def _interactor() -> RegionCommerceChangeQueryInteractor:
    return RegionCommerceChangeQueryInteractor(FakeQueryPort(list(_ROWS)), _BASELINE)


def test_상세는_분기를_생략하면_그_동의_최신_분기를_주고_서울_평균을_동봉한다():
    dto = _interactor().find_with_baseline("1168064000", None)

    assert dto.year_quarter == "20262"
    assert (dto.operating_months, dto.closed_months) == (110.0, 48.0)
    assert (dto.seoul.operating_months, dto.seoul.closed_months) == (117.0, 52.0)


def test_baseline_행이_없는_분기면_seoul은_None이다():
    dto = _interactor().find_with_baseline("1168064000", "20253")

    assert dto.year_quarter == "20253" and dto.operating_months == 104.0
    assert dto.seoul is None


def test_없는_동은_None이다():
    assert _interactor().find_with_baseline("9999999999", None) is None
