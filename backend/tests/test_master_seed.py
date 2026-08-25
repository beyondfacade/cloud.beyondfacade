"""마스터 계층 시드 검증 — 서울 자치구 25 / 행정동 427 / 업종 10종 + 소스코드 매핑."""

from sqlalchemy import func, select

from apps.master.adapter.inbound.cli.seed_master import seed_all
from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.master.adapter.outbound.orms.industry_source_code_orm import IndustrySourceCodeOrm
from apps.master.adapter.outbound.orms.industry_subcategory_orm import IndustrySubcategoryOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope


def _count(session, orm) -> int:
    return session.execute(select(func.count()).select_from(orm)).scalar()


def test_seed_all_is_idempotent_and_counts_match():
    seed_all()
    seed_all()  # 두 번 실행해도 중복 없이 동일해야 한다

    with session_scope() as session:
        assert _count(session, DistrictOrm) == 25
        assert _count(session, RegionOrm) == 427
        assert _count(session, IndustryOrm) == 10
        assert _count(session, IndustrySourceCodeOrm) >= 9
        assert _count(session, IndustrySubcategoryOrm) >= 8


def test_region_fk_points_to_valid_district():
    with session_scope() as session:
        orphan = session.execute(
            select(func.count())
            .select_from(RegionOrm)
            .outerjoin(DistrictOrm, RegionOrm.district_code == DistrictOrm.district_code)
            .where(DistrictOrm.district_code.is_(None))
        ).scalar()
    assert orphan == 0


def test_industry_demand_types_are_four_kinds():
    with session_scope() as session:
        kinds = set(session.execute(select(IndustryOrm.demand_type).distinct()).scalars())
    assert kinds == {"daily", "leisure", "macro", "demographic"}
