"""판정 리포지토리 — 업서트 멱등·signals JSON 왕복·업종별 목록 (실 DB, beyondfacade_test)."""

from datetime import datetime, timezone

from sqlalchemy import delete, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.verdict.adapter.outbound.orms.region_industry_verdict_orm import RegionIndustryVerdictOrm
from apps.verdict.adapter.outbound.repositories.region_industry_verdict_repository import (
    SqlAlchemyRegionIndustryVerdictRepository,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import (
    RegionIndustryVerdict,
    SignalResult,
)
from core.matrix.grid_oracle_database_manager import session_scope

_INDUSTRY = "korean_food"


def _two_region_codes() -> list[str]:
    with session_scope() as session:
        return session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(2)).scalars().all()


def _verdict(region_code: str, code: str, industry_id: str = _INDUSTRY) -> RegionIndustryVerdict:
    signals = tuple(
        SignalResult(key=k, level="on" if k == "net_outflow" else "off", value=0.1, percentile=80.0,
                     evidence=f"{k} 근거 — 한글 포함", source="store")
        for k in ("net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking")
    )
    return RegionIndustryVerdict(region_code, industry_id, code, 0, 1, signals, datetime(2026, 9, 28, 4, 30, tzinfo=timezone.utc))


def _cleanup(region_codes: list[str]) -> None:
    with session_scope() as session:
        session.execute(delete(RegionIndustryVerdictOrm).where(RegionIndustryVerdictOrm.region_code.in_(region_codes)))


def test_업서트는_멱등이고_signals가_JSON으로_왕복된다():
    codes = _two_region_codes()
    repo = SqlAlchemyRegionIndustryVerdictRepository()
    try:
        assert repo.upsert([_verdict(codes[0], "orange"), _verdict(codes[1], "clear")]) == 2
        assert repo.upsert([_verdict(codes[0], "red")]) == 1  # 같은 키 → 덮어씀
        found = repo.find(codes[0], _INDUSTRY)
        assert found.verdict_code == "red"
        assert [s.key for s in found.signals][0] == "net_outflow"
        assert found.signals[0].evidence == "net_outflow 근거 — 한글 포함"
        assert found.signals[0].level == "on"
        assert repo.find("0000000000", _INDUSTRY) is None
        listed = repo.list_by_industry(_INDUSTRY)
        assert [v.region_code for v in listed if v.region_code in codes] == sorted(codes)
    finally:
        _cleanup(codes)


def test_판정_대상_외_업종_행만_지운다():
    codes = _two_region_codes()
    repo = SqlAlchemyRegionIndustryVerdictRepository()
    try:
        repo.upsert([_verdict(codes[0], "clear"), _verdict(codes[1], "clear", industry_id="convenience_store")])
        assert repo.delete_other_industries([_INDUSTRY]) == 1
        assert repo.find(codes[1], "convenience_store") is None
        assert repo.find(codes[0], _INDUSTRY) is not None
    finally:
        _cleanup(codes)
