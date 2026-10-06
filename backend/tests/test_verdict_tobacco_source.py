"""담배소매인 편의점 원천 — 창 집계 순수 함수(인허가 SQL과 같은 규칙) + DB 게이트웨이(승계·기준일·빈자리·점포수·진입 결과).
업종 특화 신호 설계서 §5·§6."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.tobacco.adapter.outbound.orms.tobacco_retailer_orm import TobaccoRetailerOrm
from apps.verdict.adapter.outbound.gateways.tobacco_convenience_gateway import (
    TobaccoConvenienceSignalData,
    stats_from_episodes,
)
from apps.verdict.app.dtos.region_industry_verdict_dto import (
    EntrantOutcome,
    JudgedIndustry,
    LatestStoreCount,
    RegionContext,
    StoreSignalStat,
)
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    EntrantOutcomePort,
    IndustryCatalogPort,
    IndustrySignalDataPort,
    RegionCatalogPort,
    RegionContextPort,
    RegionIndustryVerdictRepositoryPort,
    StoreSignalStatsPort,
)
from apps.verdict.app.use_cases.industry_source import IndustrySource
from apps.verdict.app.use_cases.region_industry_verdict_interactor import RegionIndustryVerdictInteractor
from apps.verdict.domain.services.convenience_history import Episode
from apps.verdict.domain.services.profiles import TobaccoProxyProfile
from core.matrix.grid_oracle_database_manager import session_scope

_TODAY = date(2099, 6, 30)
_PREFIX = "test-tbcsrc-"


def _e(open_days: int, close_days: int | None = None) -> Episode:
    d = lambda n: _TODAY - timedelta(days=n)  # noqa: E731
    return Episode("r1", d(open_days), None if close_days is None else d(close_days))


def test_창_집계는_인허가_SQL과_같은_규칙이다():
    # test_verdict_gateways.py::test_store_집계_12개월_코호트_중위개월과 같은 8행·같은 기대값
    episodes = [_e(800), _e(800, 100), _e(100), _e(1195), _e(1195, 795), _e(1195, 95), _e(2000, 200), _e(100, 200)]
    (stat,) = stats_from_episodes(episodes, _TODAY, "convenience_store")
    assert stat.industry_id == "convenience_store"
    assert (stat.start_store_count, stat.opened_12m, stat.closed_12m) == (5, 2, 4)
    assert (stat.cohort_size, stat.cohort_survived) == (3, 2)
    assert stat.closed_3y_count == 4
    assert stat.closed_3y_median_months == pytest.approx(900 / 30.4375, rel=1e-3)


def _region() -> str:
    with session_scope() as session:
        return session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)).scalar_one()


def _second_region() -> str:
    """유령 행 테스트에서 _latest(원천 최신 날짜) 계산용 정상 레코드를 격리해 넣을 두 번째 동."""
    with session_scope() as session:
        return session.execute(
            select(RegionOrm.region_code).order_by(RegionOrm.region_code).offset(1).limit(1)
        ).scalar_one()


def _retailer(n, region, name, open_, close=None, jibun=None, lat=None, lng=None):
    return TobaccoRetailerOrm(
        retailer_id=f"{_PREFIX}{n}", name=name, district_code=region[:5], region_code=region,
        status_code="0" if close is None else "2", status_name="시험", designated_date=open_, permit_date=open_,
        close_date=close, cancel_date=None, lat=lat, lng=lng, road_address=None, jibun_address=jibun,
        source_updated_at=datetime(2099, 1, 1),
    )


def _store(n, region, lat, lng):
    return StoreOrm(
        store_id=f"{_PREFIX}{n}", name=f"빈자리시험{n}", industry_id="cafe", district_code=region[:5],
        region_code=region, subcategory_id=None, open_date=date(2090, 1, 1), close_date=None, status_code="01",
        status_name="영업", lat=lat, lng=lng, road_address=None, jibun_address=None,
        source_updated_at=datetime(2099, 1, 1),
    )


def test_담배소매인_원천은_편의점만_승계를_접어_원천_최신일_기준으로_센다():
    region = _region()
    addr = "서울특별시 시험구 시험동 1"
    retailers = [
        _retailer(1, region, "GS25 시험1점", date(2097, 1, 1), date(2098, 12, 1), jibun=addr),
        _retailer(2, region, "CU 시험1점", date(2098, 12, 20), jibun=addr),  # 19일 뒤 같은 지번 → 승계
        _retailer(3, region, "세븐일레븐 시험2점", date(2098, 10, 1), jibun="서울특별시 시험구 시험동 2"),
        _retailer(4, region, "행복슈퍼", date(2090, 1, 1), jibun="서울특별시 시험구 시험동 3", lat=37.5, lng=127.0),  # 편의점 아님
        _retailer(5, region, "이마트24 시험4점", date(2095, 1, 1), date(2099, 3, 1), jibun="서울특별시 시험구 시험동 4"),
        _retailer(6, region, "미니스톱 시험6점", date(2098, 4, 15), jibun="서울특별시 시험구 시험동 6"),
    ]
    stores = [_store(1, region, 37.5001, 127.0), _store(2, region, 37.51, 127.0)]  # 11m · 1.1km
    try:
        with session_scope() as session:
            session.add_all(retailers + stores)
        data = TobaccoConvenienceSignalData()
        # 원천 최신 날짜 2099-03-01(5번 폐업) < 요청일 → 기준일 2099-03-01, 12개월 창 (2098-03-01, 2099-03-01]
        stat = next(s for s in data.signal_stats(_TODAY) if s.region_code == region)
        assert stat.start_store_count == 2  # 승계 에피소드(1+2) · 5번
        assert stat.opened_12m == 2  # 3번 · 6번(기준일 고정이라 창 안). 2번은 승계라 개업이 아니다
        assert stat.closed_12m == 1  # 5번. 1번 폐업은 승계라 폐업이 아니다
        assert (stat.gap_candidates, stat.gap_blocked) == (2, 1)  # 상가 1은 행복슈퍼 11m 안
        assert {c.region_code: c.store_count for c in data.store_counts(None, None)}[region] == 3  # 승계·3번·6번
        assert {c.region_code: c.store_count for c in data.store_counts(2098, None)}[region] == 4  # 2098-12-31엔 5번도
        outcome = next(o for o in data.entrant_outcomes(date(2098, 1, 1), 365, 1095) if o.region_code == region)
        assert (outcome.opened, outcome.closed_within) == (2, 0)  # 3번·6번. 승계(2번)는 진입이 아니다
    finally:
        with session_scope() as session:
            session.execute(delete(TobaccoRetailerOrm).where(TobaccoRetailerOrm.retailer_id.like(f"{_PREFIX}%")))
            session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_PREFIX}%")))


# --- Ruling P7: 폐업 계열인데 종료일 없는 유령 행 드롭 ---


def _ghost(n, region, name, status_code, *, jibun=None, lat=None, lng=None) -> TobaccoRetailerOrm:
    """폐업처리·직권취소·임시소매기간만료·지정취소인데 폐업일·취소일이 둘 다 없는 유령 행 (원천 결측)."""
    return TobaccoRetailerOrm(
        retailer_id=f"{_PREFIX}{n}", name=name, district_code=region[:5], region_code=region,
        status_code=status_code, status_name="시험", designated_date=date(2080, 1, 1), permit_date=date(2080, 1, 1),
        close_date=None, cancel_date=None, lat=lat, lng=lng, road_address=None, jibun_address=jibun,
        source_updated_at=datetime(2099, 1, 1),
    )


def test_폐업_계열인데_종료일_없는_유령_행은_적재에서_빠진다():
    region, anchor_region = _region(), _second_region()
    ghosts = [
        _ghost(11, region, "GS25 유령1점", "2", jibun="서울특별시 시험구 유령동 1"),  # 폐업처리 — 폐업일 없음
        _ghost(12, region, "미니스톱 유령2점", "3", jibun="서울특별시 시험구 유령동 2"),  # 직권취소 — 취소일 없음
        _ghost(13, region, "CU 유령3점", "4", jibun="서울특별시 시험구 유령동 3"),  # 임시소매기간만료
        _ghost(14, region, "세븐일레븐 유령4점", "5", jibun="서울특별시 시험구 유령동 4"),  # 지정취소 — 취소일 없음
        _ghost(15, region, "유령소매인", "3", lat=37.6, lng=127.1),  # 브랜드 아님 — 빈자리 가짜 막힘 대상
    ]
    # 유령 행은 전부 걸러지므로 _latest(원천 최신 날짜) 계산에 쓸 정상 레코드를 다른 동에 하나 둔다
    anchor = _retailer(16, anchor_region, "GS25 기준점", date(2099, 1, 1))
    ghost_gap_store = _store(15, region, 37.6001, 127.1)  # 11m 안 — 유령소매인이 안 빠지면 막힌 걸로 잡힌다
    try:
        with session_scope() as session:
            session.add_all(ghosts + [anchor, ghost_gap_store])
        data = TobaccoConvenienceSignalData()
        counts = {c.region_code: c.store_count for c in data.store_counts(None, None)}
        assert counts.get(region, 0) == 0  # 유령 편의점 4곳 전부 영업중으로 안 잡힌다
        stat = next(s for s in data.signal_stats(_TODAY) if s.region_code == region)
        assert (stat.start_store_count, stat.opened_12m, stat.closed_12m) == (0, 0, 0)
        assert (stat.gap_candidates, stat.gap_blocked) == (1, 0)  # 유령 소매인이 상가를 막지 않는다
    finally:
        with session_scope() as session:
            session.execute(delete(TobaccoRetailerOrm).where(TobaccoRetailerOrm.retailer_id.like(f"{_PREFIX}%")))
            session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_PREFIX}%")))


# --- Task 6 리뷰: proxy basis도 전체(None) 백테스트 합산에 풀링되는지 (aggregate=제외·permit=포함은 test_verdict_sources.py에 있음) ---


class _FakeRepository(RegionIndustryVerdictRepositoryPort):
    def upsert(self, verdicts):
        raise AssertionError("백테스트는 저장하지 않는다")

    def list_by_industry(self, industry_id):
        return []

    def list_by_region(self, region_code):
        return []

    def find(self, region_code, industry_id):
        return None

    def delete_other_industries(self, keep_industry_ids):
        raise AssertionError


class _FakeStoreStats(StoreSignalStatsPort):
    def signal_stats(self, today):
        return [StoreSignalStat("r01", "korean_food", 100, 10, 5, 40, 20, 30, 24.0)]


class _FakeContext(RegionContextPort):
    def latest_contexts(self, quarter_max=None):
        return [RegionContext("r01", 10_000)]

    def latest_store_counts(self, year_max=None):
        return [LatestStoreCount("r01", "korean_food", 90)]


class _FakeCatalog(IndustryCatalogPort):
    def judged_industries(self):
        return [JudgedIndustry("korean_food", "한식"), JudgedIndustry("convenience_store", "편의점")]

    def named_industries(self, industry_ids):
        names = {"korean_food": "한식", "convenience_store": "편의점"}
        return [JudgedIndustry(i, names[i]) for i in industry_ids]


class _FakeRegions(RegionCatalogPort):
    def regions(self):
        return []


class _FakeOutcomes(EntrantOutcomePort):
    def entrant_outcomes(self, as_of, entry_days, horizon_days):
        return [EntrantOutcome("r01", "korean_food", opened=10, closed_within=3)]


class _FakeConvenienceData(IndustrySignalDataPort):
    def signal_stats(self, today):
        return [StoreSignalStat("r01", "convenience_store", 90, 8, 6, 0, 0, 0, None, gap_candidates=10, gap_blocked=5)]

    def store_counts(self, year_max, quarter_max):
        return [LatestStoreCount("r01", "convenience_store", 80)]

    def entrant_outcomes(self, as_of, entry_days, horizon_days):
        return [EntrantOutcome("r01", "convenience_store", opened=20, closed_within=9)]


def test_프록시_원천도_전체_백테스트_합산에_풀링된다():
    interactor = RegionIndustryVerdictInteractor(
        repository=_FakeRepository(), store_stats=_FakeStoreStats(), region_context=_FakeContext(),
        industry_catalog=_FakeCatalog(), region_catalog=_FakeRegions(), entrant_outcomes=_FakeOutcomes(),
        sources={"convenience_store": IndustrySource(TobaccoProxyProfile(), _FakeConvenienceData())},
    )
    report = interactor.backtest(date(2026, 9, 29))
    assert any(b.industry_id is None for b in report.buckets)  # aggregate와 달리 전체(None) 버킷이 있다
    # 한식(개업10, permit) + 편의점(개업20, proxy) 둘 다 전체(None) 버킷에 풀링된다
    assert sum(b.opened for b in report.buckets if b.industry_id is None) == 30
