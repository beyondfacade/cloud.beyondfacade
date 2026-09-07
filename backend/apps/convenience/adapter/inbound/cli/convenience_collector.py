"""편의점 스냅샷 수집기 (Driving Adapter, CLI).

- 원천: 소진공 상가정보 sdsc2 storeListInDong(indsSclsCd=G20405) — 현행 스냅샷 전량,
  매 실행 멱등 재수집. 개폐업 시계열 불가(api.md §2-3)이므로 소실은 last_seen_on
  정지로만 남는다 (판정 없음 — tobacco_retailer가 개폐업 이력 담당)
- 수집 단위 = 행정동(region) 427회/스냅샷 (일 한도 10,000회의 4.3%) — 순차 호출
- 실행: python -m apps.convenience.adapter.inbound.cli.convenience_collector [--region 역삼1동]
"""

import argparse
import sys
import traceback
from datetime import date

from sqlalchemy import select

from apps.convenience.adapter.outbound.gateways.semas_convenience_gateway import (
    SemasConvenienceGateway,
)
from apps.convenience.adapter.outbound.repositories.convenience_store_repository import (
    SqlAlchemyConvenienceStoreRepository,
)
from apps.convenience.app.use_cases.convenience_store_interactor import (
    ConvenienceSnapshotInteractor,
)
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope


def _target_regions(region_name: str | None) -> list[tuple[str, str]]:
    with session_scope() as session:
        statement = select(RegionOrm.region_code, RegionOrm.name).order_by(
            RegionOrm.region_code
        )
        if region_name:
            statement = statement.where(RegionOrm.name == region_name)
        return [tuple(row) for row in session.execute(statement).all()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", help="행정동명 (예: 역삼1동) — 생략 시 427개 전체")
    args = parser.parse_args()

    observed_on = date.today()
    gateway = SemasConvenienceGateway()
    interactor = ConvenienceSnapshotInteractor(
        repository=SqlAlchemyConvenienceStoreRepository(), gateway=gateway
    )

    processed_total = failed = 0
    for region_code, name in _target_regions(args.region):
        try:
            processed = interactor.ingest(region_code, observed_on)
            processed_total += processed
            print(f"convenience collector: {name}({region_code}) — {processed}건 업서트", flush=True)
        except Exception:
            failed += 1
            print(f"convenience collector: {name}({region_code}) — 실패", flush=True)
            traceback.print_exc()

    print(
        f"convenience collector: 총 {processed_total}건 업서트 (API {gateway.call_count}회 호출)",
        flush=True,
    )
    if failed:
        print(f"convenience collector: {failed}개 행정동 실패", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
