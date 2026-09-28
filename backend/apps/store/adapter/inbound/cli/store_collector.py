"""인허가 점포 수집기 (Driving Adapter, CLI).

- 수집 단위 = 인허가 슬러그(industry_source_code의 mois_permit 매핑) × 자치구(district.opn_authority_code).
  슬러그 하나에 업종이 여럿이면(일반음식점) 타깃은 슬러그당 1개, 건별 업종은 분류기가 정한다
- 증분: DB의 (슬러그의 업종 집합 × 자치구) 최근 갱신시점 커서 — 첫 실행은 전체 초기적재
- 실행: python -m apps.store.adapter.inbound.cli.store_collector [--district 강남구] [--industry karaoke|general_restaurants]
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
from apps.store.domain.services.permit_industry_classifier import (
    PERMIT_STORE_PREFIXES,
    permit_classifier_for,
)
from core.matrix.grid_oracle_database_manager import session_scope


def _build_targets(district_name: str | None, industry_or_slug: str | None) -> list[IngestTarget]:
    with session_scope() as session:
        rows = session.execute(
            select(IndustrySourceCodeOrm.industry_id, IndustrySourceCodeOrm.code)
            .where(IndustrySourceCodeOrm.source_system == "mois_permit")
            .order_by(IndustrySourceCodeOrm.id)
        ).all()
        if industry_or_slug:
            rows = [r for r in rows if industry_or_slug in (r.industry_id, r.code)]
        # 슬러그당 앵커 업종 1개 — 같은 슬러그에 업종이 여러 행 등록돼도 데이터셋은 한 번만 받는다
        anchor_by_slug: dict[str, str] = {}
        for industry_id, slug in rows:
            anchor_by_slug.setdefault(slug, industry_id)

        district_stmt = select(DistrictOrm).where(DistrictOrm.opn_authority_code.is_not(None))
        if district_name:
            district_stmt = district_stmt.where(DistrictOrm.name == district_name)
        districts = session.execute(district_stmt).scalars().all()

        return [
            IngestTarget(
                industry_id=anchor,
                slug=slug,
                district_code=d.district_code,
                authority_code=d.opn_authority_code,
                industry_ids=tuple(sorted(permit_classifier_for(slug, anchor).industry_ids)),
                store_prefix=PERMIT_STORE_PREFIXES.get(slug),
            )
            for slug, anchor in anchor_by_slug.items()
            for d in districts
        ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--district", help="자치구명 (예: 강남구) — 생략 시 25개 전체")
    parser.add_argument("--industry", help="industry_id 또는 인허가 슬러그 (예: karaoke, general_restaurants) — 생략 시 전체")
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
