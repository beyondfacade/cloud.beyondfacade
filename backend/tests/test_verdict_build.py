"""판정 배치 — Fake 포트로 업종별 상대평가·업서트·조회 검증 (설계서 §4-4)."""

from datetime import date, datetime, timezone

import pytest

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    JudgedIndustry,
    LatestStoreCount,
    RegionContext,
    StoreSignalStat,
)
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    IndustryCatalogPort,
    RegionContextPort,
    RegionIndustryVerdictRepositoryPort,
    StoreSignalStatsPort,
)
from apps.verdict.app.use_cases.region_industry_verdict_interactor import (
    RegionIndustryVerdictInteractor,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import (
    SIGNAL_KEYS,
    VERDICT_INSUFFICIENT,
    RegionIndustryVerdict,
)
from apps.verdict.domain.errors import IndustryNotFoundError


class FakeRepository(RegionIndustryVerdictRepositoryPort):
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], RegionIndustryVerdict] = {}

    def upsert(self, verdicts):
        for v in verdicts:
            self.rows[(v.region_code, v.industry_id)] = v
        return len(verdicts)

    def list_by_industry(self, industry_id):
        return sorted((v for v in self.rows.values() if v.industry_id == industry_id), key=lambda v: v.region_code)

    def find(self, region_code, industry_id):
        return self.rows.get((region_code, industry_id))

    def delete_other_industries(self, keep_industry_ids):
        keep = set(keep_industry_ids)
        doomed = [k for k in self.rows if k[1] not in keep]
        for k in doomed:
            del self.rows[k]
        return len(doomed)


class FakeStoreStats(StoreSignalStatsPort):
    def __init__(self, stats):
        self.stats = stats

    def signal_stats(self, today):
        return self.stats


class FakeContext(RegionContextPort):
    def __init__(self, contexts, counts):
        self.contexts, self.counts = contexts, counts

    def latest_contexts(self):
        return self.contexts

    def latest_store_counts(self):
        return self.counts


class FakeCatalog(IndustryCatalogPort):
    def judged_industries(self):
        return [JudgedIndustry("korean_food", "한식")]


def _stat(region: str, closed_12m: int) -> StoreSignalStat:
    return StoreSignalStat(
        region_code=region, industry_id="korean_food", start_store_count=100, opened_12m=10,
        closed_12m=closed_12m, cohort_size=40, cohort_survived=20, closed_3y_count=30, closed_3y_median_months=24.0,
    )


def _context(region: str, change_code: str | None = "HH") -> RegionContext:
    return RegionContext(
        region_code=region, resident_total=10_000, change_code=change_code,
        change_name=None if change_code is None else "정체", change_quarter="20262",
        closed_months=25.0, seoul_closed_months=27.0,
    )


def _interactor(stats, contexts, counts):
    repo = FakeRepository()
    return repo, RegionIndustryVerdictInteractor(
        repository=repo, store_stats=FakeStoreStats(stats),
        region_context=FakeContext(contexts, counts), industry_catalog=FakeCatalog(),
    )


def test_동_20개를_업종_안에서_상대평가해_상위_동만_켠다():
    regions = [f"11680{i:05d}" for i in range(20)]
    stats = [_stat(r, closed_12m=10 + i) for i, r in enumerate(regions)]  # 순유출률 0.00 ~ 0.19
    contexts = [_context(r) for r in regions]
    counts = [LatestStoreCount(r, "korean_food", 90) for r in regions]
    repo, interactor = _interactor(stats, contexts, counts)

    assert interactor.build(date(2026, 9, 28)) == 20

    worst = repo.find(regions[19], "korean_food")
    best = repo.find(regions[0], "korean_food")
    assert [s.key for s in worst.signals] == list(SIGNAL_KEYS)
    assert worst.signals[0].level == "strong"  # 19개보다 크다 → 95
    assert best.signals[0].level == "off"
    # 포화는 전 동 동일값 → 백분위 0 → off, 상권축소는 HH → off
    assert worst.signals[3].level == "off" and worst.signals[4].level == "off"
    assert worst.verdict_code == "orange"  # strong 1개


def test_집계가_없는_동은_표본_부족으로_보류된다():
    regions = ["1168000001", "1168000002", "1168000003"]
    repo, interactor = _interactor([], [_context(r, change_code=None) for r in regions], [])
    interactor.build(date(2026, 9, 28))
    v = repo.find(regions[0], "korean_food")
    assert v.verdict_code == VERDICT_INSUFFICIENT
    assert all(s.level == "unavailable" for s in v.signals)


def test_조회는_판정_대상_업종만_받는다():
    repo, interactor = _interactor([], [_context("1168000001")], [])
    interactor.build(date(2026, 9, 28))
    assert [v.value for v in interactor.list_verdict_values("korean_food")] == [VERDICT_INSUFFICIENT]
    assert interactor.find("1168000001", "korean_food").region_code == "1168000001"
    assert interactor.find("0000000000", "korean_food") is None
    with pytest.raises(IndustryNotFoundError):
        interactor.list_verdict_values("academy")
    with pytest.raises(IndustryNotFoundError):
        interactor.find("1168000001", "chicken")


def test_배치는_판정_대상에서_빠진_업종의_옛_행을_지운다():
    repo, interactor = _interactor([], [_context("1168000001")], [])
    stale = RegionIndustryVerdict("1168000001", "convenience_store", VERDICT_INSUFFICIENT, 0, 0, (), datetime(2026, 9, 28, tzinfo=timezone.utc))
    repo.upsert([stale])

    interactor.build(date(2026, 9, 28))

    assert repo.find("1168000001", "convenience_store") is None
    assert repo.find("1168000001", "korean_food") is not None


def test_myself는_하드코딩_행을_돌려준다():
    _, interactor = _interactor([], [], [])
    me = interactor.myself()
    assert me.region_code == "myself" and len(me.signals) == 5
