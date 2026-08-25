"""인허가 점포 수집기 (Driving Adapter, CLI).

- 수집 단위 = 업종(industry_source_code의 mois_permit 매핑) × 자치구(district.opn_authority_code)
- 증분: DB의 (업종×자치구) 최근 갱신시점 커서 — 첫 실행은 전체 초기적재
- 실행: python -m apps.store.adapter.inbound.cli.store_collector [--district 강남구] [--industry karaoke]
"""

import argparse
import sys
import traceback

from sqlalchemy import select

from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.master.adapter.outbound.orms.industry_source_code_orm import IndustrySourceCodeOrm
from apps.store.adapter.outbound.gateways.mois_permit_gateway import MoisPermitGateway
from apps.store.adapter.outbound.repositories.store_repository import (
    SqlAlchemyStoreRepository,
)
from apps.store.app.dtos.store_dto import IngestTarget
from apps.store.app.use_cases.store_interactor import StoreInteractor
from core.matrix.grid_oracle_database_manager import session_scope


def _build_targets(district_name: str | None, industry_id: str | None) -> list[IngestTarget]:
    with session_scope() as session:
        slug_stmt = select(
            IndustrySourceCodeOrm.industry_id, IndustrySourceCodeOrm.code
        ).where(IndustrySourceCodeOrm.source_system == "mois_permit")
        if industry_id:
            slug_stmt = slug_stmt.where(IndustrySourceCodeOrm.industry_id == industry_id)
        slugs = session.execute(slug_stmt).all()

        district_stmt = select(DistrictOrm).where(DistrictOrm.opn_authority_code.is_not(None))
        if district_name:
            district_stmt = district_stmt.where(DistrictOrm.name == district_name)
        districts = session.execute(district_stmt).scalars().all()

        return [
            IngestTarget(
                industry_id=ind,
                slug=slug,
                district_code=d.district_code,
                authority_code=d.opn_authority_code,
            )
            for ind, slug in slugs
            for d in districts
        ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--district", help="자치구명 (예: 강남구) — 생략 시 25개 전체")
    parser.add_argument("--industry", help="industry_id (예: karaoke) — 생략 시 인허가 6종 전체")
    parser.add_argument("--full", action="store_true", help="증분 커서 무시, 전체 재수집 (부분 적재 복구용)")
    args = parser.parse_args()

    targets = _build_targets(args.district, args.industry)
    interactor = StoreInteractor(
        repository=SqlAlchemyStoreRepository(), gateway=MoisPermitGateway()
    )
    failed = 0
    for target in targets:
        try:
            processed = interactor.ingest([target], full=args.full)
            print(f"store collector: {target.industry_id} × {target.district_code} — {processed}건", flush=True)
        except Exception:
            failed += 1
            print(f"store collector: {target.industry_id} × {target.district_code} — 실패", flush=True)
            traceback.print_exc()
    if failed:
        print(f"store collector: {failed}개 대상 실패", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
