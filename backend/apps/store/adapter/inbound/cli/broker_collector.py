"""부동산중개업 수집기 (Driving Adapter, CLI).

- 원천: 브이월드 NED getEBOfficeInfo (data.go.kr 15123990 LINK 실체) — 현행 스냅샷 전량,
  매 실행 멱등 재수집. 원천이 폐업분을 제공하지 않아 폐업은 스냅샷 소실 기반 추정
- 수집 단위 = industry_source_code의 스냅샷 원천(source_system) × 자치구(district_code=ldCode)
- 실행: python -m apps.store.adapter.inbound.cli.broker_collector [--district 강남구]
"""

import argparse
import sys
import traceback
from collections.abc import Callable
from datetime import date

from sqlalchemy import select

from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.master.adapter.outbound.orms.industry_source_code_orm import IndustrySourceCodeOrm
from apps.store.adapter.outbound.gateways.molit_broker_gateway import MolitBrokerGateway
from apps.store.adapter.outbound.repositories.store_repository import (
    SqlAlchemyStoreRepository,
)
from apps.store.app.ports.output.broker_snapshot_port import BrokerGatewayPort
from apps.store.app.use_cases.broker_snapshot_interactor import BrokerSnapshotInteractor
from core.matrix.grid_oracle_database_manager import session_scope

# source_system → 게이트웨이 팩토리 (§5 Factory/레지스트리 — 신규 스냅샷 원천은 분기 없이 등록으로 확장)
_GATEWAY_FACTORIES: dict[str, Callable[[], BrokerGatewayPort]] = {
    "molit_broker": MolitBrokerGateway,
}


def _build_targets(district_name: str | None) -> list[tuple[str, str, str]]:
    """레지스트리에 등록된 스냅샷 원천 × 자치구 → (industry_id, source_system, district_code)."""
    with session_scope() as session:
        sources = session.execute(
            select(
                IndustrySourceCodeOrm.industry_id, IndustrySourceCodeOrm.source_system
            ).where(IndustrySourceCodeOrm.source_system.in_(_GATEWAY_FACTORIES))
        ).all()

        district_stmt = select(DistrictOrm.district_code).order_by(DistrictOrm.district_code)
        if district_name:
            district_stmt = district_stmt.where(DistrictOrm.name == district_name)
        districts = session.execute(district_stmt).scalars().all()

    return [
        (industry_id, source_system, district_code)
        for industry_id, source_system in sources
        for district_code in districts
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--district", help="자치구명 (예: 강남구) — 생략 시 25개 전체")
    args = parser.parse_args()

    observed_on = date.today()
    repository = SqlAlchemyStoreRepository()
    gateways: dict[str, BrokerGatewayPort] = {}
    interactors: dict[str, BrokerSnapshotInteractor] = {}

    processed_total = closed_total = failed = 0
    for industry_id, source_system, district_code in _build_targets(args.district):
        gateway = gateways.setdefault(source_system, _GATEWAY_FACTORIES[source_system]())
        interactor = interactors.setdefault(
            source_system, BrokerSnapshotInteractor(repository=repository, gateway=gateway)
        )
        try:
            processed, closed = interactor.ingest(industry_id, district_code, observed_on)
            processed_total += processed
            closed_total += closed
            print(
                f"broker collector: {industry_id} × {district_code}"
                f" — {processed}건 업서트, 폐업(추정) {closed}건",
                flush=True,
            )
        except Exception:
            failed += 1
            print(f"broker collector: {industry_id} × {district_code} — 실패", flush=True)
            traceback.print_exc()

    calls = sum(getattr(g, "call_count", 0) for g in gateways.values())
    print(
        f"broker collector: 총 {processed_total}건 업서트, 폐업(추정) {closed_total}건"
        f" (API {calls}회 호출)",
        flush=True,
    )
    if failed:
        print(f"broker collector: {failed}개 대상 실패", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
