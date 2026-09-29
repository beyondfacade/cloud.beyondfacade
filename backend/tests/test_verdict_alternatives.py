"""대안 두 축 — 순위 규칙(도메인)과 인터랙터 조합(Fake 포트) (설계서 §12)."""

from datetime import date, datetime, timezone

import pytest

from apps.verdict.app.dtos.region_industry_verdict_dto import JudgedIndustry, RegionInfo
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    IndustryCatalogPort,
    EntrantOutcomePort,
    RegionCatalogPort,
    RegionContextPort,
    RegionIndustryVerdictRepositoryPort,
    StoreSignalStatsPort,
)
from apps.verdict.app.use_cases.region_industry_verdict_interactor import RegionIndustryVerdictInteractor
from apps.verdict.domain.entities.region_industry_verdict_entity import RegionIndustryVerdict
from apps.verdict.domain.errors import IndustryNotFoundError
from apps.verdict.domain.services.alternatives import rank_alternatives

_AT = datetime(2026, 9, 29, tzinfo=timezone.utc)


def _v(region: str, industry: str, code: str, strong: int = 0, on: int = 0) -> RegionIndustryVerdict:
    return RegionIndustryVerdict(region, industry, code, strong, on, (), _AT)


# --- 도메인 순위 규칙 ---

def test_후보는_clear_orange만이고_기준보다_신호가_적은_순으로_3개까지():
    base = _v("r1", "cafe", "red", strong=2, on=3)
    candidates = [
        _v("r1", "pub", "orange", 1, 2),
        _v("r1", "snack", "clear"),
        _v("r1", "gym", "insufficient"),
        _v("r1", "karaoke", "red", 2, 2),
        _v("r1", "hair_salon", "orange", 0, 1),
        _v("r1", "korean_food", "clear"),
        _v("r1", "billiard", "orange", 1, 1),
    ]
    ranked = rank_alternatives(base, candidates, key=lambda v: v.industry_id)
    assert [v.industry_id for v in ranked] == ["korean_food", "snack", "hair_salon"]  # clear(id순) → orange(0,1)


def test_기준이_clear면_대안이_없고_보류면_clear_orange_전부가_대안():
    clear_base = _v("r1", "cafe", "clear")
    boryu_base = _v("r1", "cafe", "insufficient")
    candidates = [_v("r1", "pub", "orange", 0, 1), _v("r1", "snack", "clear"), _v("r1", "gym", "red", 2, 2)]
    assert rank_alternatives(clear_base, candidates, key=lambda v: v.industry_id) == []
    assert [v.industry_id for v in rank_alternatives(boryu_base, candidates, key=lambda v: v.industry_id)] == ["snack", "pub"]


def test_같은_orange라도_신호_수가_더_적어야_대안이다():
    base = _v("r1", "cafe", "orange", strong=1, on=1)
    candidates = [_v("r1", "pub", "orange", 1, 1), _v("r1", "snack", "orange", 0, 1), _v("r1", "gym", "orange", 1, 2)]
    assert [v.industry_id for v in rank_alternatives(base, candidates, key=lambda v: v.industry_id)] == ["snack"]


# --- 인터랙터 ---

class FakeRepository(RegionIndustryVerdictRepositoryPort):
    def __init__(self, rows):
        self.rows = {(v.region_code, v.industry_id): v for v in rows}

    def upsert(self, verdicts):
        return 0

    def list_by_industry(self, industry_id):
        return sorted((v for v in self.rows.values() if v.industry_id == industry_id), key=lambda v: v.region_code)

    def list_by_region(self, region_code):
        return sorted((v for v in self.rows.values() if v.region_code == region_code), key=lambda v: v.industry_id)

    def find(self, region_code, industry_id):
        return self.rows.get((region_code, industry_id))

    def delete_other_industries(self, keep_industry_ids):
        return 0


class FakeCatalog(IndustryCatalogPort):
    def judged_industries(self):
        return [JudgedIndustry("cafe", "카페"), JudgedIndustry("pub", "호프주점"), JudgedIndustry("snack", "분식")]


class FakeOutcomes(EntrantOutcomePort):
    def entrant_outcomes(self, as_of, entry_days, horizon_days):
        return []


class FakeRegions(RegionCatalogPort):
    def regions(self):
        return [
            RegionInfo("r1", "역삼1동", "office"),
            RegionInfo("r2", "삼성1동", "office"),
            RegionInfo("r3", "대치2동", "office"),
            RegionInfo("r4", "신촌동", "campus"),
            RegionInfo("r5", "논현1동", None),
        ]


class _Unused(StoreSignalStatsPort, RegionContextPort):
    def signal_stats(self, today):
        raise AssertionError

    def latest_contexts(self, quarter_max=None):
        raise AssertionError

    def latest_store_counts(self, year_max=None):
        raise AssertionError


def _interactor(rows):
    return RegionIndustryVerdictInteractor(
        repository=FakeRepository(rows), store_stats=_Unused(), region_context=_Unused(),
        industry_catalog=FakeCatalog(), region_catalog=FakeRegions(), entrant_outcomes=FakeOutcomes(),
    )


def test_동네_고정은_같은_동_다른_업종_업종_고정은_같은_유형_다른_동():
    rows = [
        _v("r1", "cafe", "red", 2, 3),
        _v("r1", "pub", "orange", 0, 1), _v("r1", "snack", "clear"),
        _v("r2", "cafe", "clear"), _v("r3", "cafe", "orange", 1, 1),
        _v("r4", "cafe", "clear"),  # 유형이 다르다 → 제외
        _v("r5", "cafe", "clear"),  # 유형 없음 → 제외
    ]
    dto = _interactor(rows).alternatives("r1", "cafe")
    assert dto.neighborhood_type == "office"
    assert [(a.industry_id, a.industry_name, a.verdict_code) for a in dto.industries] == [("snack", "분식", "clear"), ("pub", "호프주점", "orange")]
    assert [(a.region_code, a.region_name, a.verdict_code) for a in dto.regions] == [("r2", "삼성1동", "clear"), ("r3", "대치2동", "orange")]


def test_유형이_없는_동은_업종_고정_축이_비고_기준_판정이_없으면_None():
    rows = [_v("r5", "cafe", "red", 2, 2), _v("r5", "snack", "clear"), _v("r2", "cafe", "clear")]
    dto = _interactor(rows).alternatives("r5", "cafe")
    assert dto.neighborhood_type is None and dto.regions == ()
    assert [a.industry_id for a in dto.industries] == ["snack"]
    assert _interactor(rows).alternatives("r9", "cafe") is None
    with pytest.raises(IndustryNotFoundError):
        _interactor(rows).alternatives("r5", "academy")
