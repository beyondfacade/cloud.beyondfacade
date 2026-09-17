"""어린이집 스냅샷 수집기 (Driving Adapter, CLI).

- 원천: 어린이집정보공개포털 cpmsapi030 — 폐지 제외 시설 전량 + 기준일 현황, 매 실행 멱등 재수집.
  폐지 시설은 응답에서 빠지므로 소실은 last_seen_on 정지로만 남는다 (판정 없음)
- 수집 단위 = 자치구(district) 25회/스냅샷 (일 1,000회 한도의 2.5%) — 순차 호출
- 적재 후 region_code 미기입·좌표 보유 시설만 행정동 공간조인 (store RegionIndex 재사용 — tobacco 전례).
  판정 행정동이 등록 자치구 밖이면 좌표 오류로 보고 기입하지 않는다 (동작구 시설 좌표가 중구 실측)
- 실행: python -m apps.childcare.adapter.inbound.cli.childcare_collector [--district 종로구]
"""

import argparse
import sys
import traceback
from datetime import date
from pathlib import Path

from sqlalchemy import select, update

from apps.childcare.adapter.outbound.gateways.childcare_portal_gateway import (
    ChildcarePortalGateway,
)
from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.childcare.adapter.outbound.repositories.childcare_center_repository import (
    SqlAlchemyChildcareCenterRepository,
)
from apps.childcare.app.use_cases.childcare_center_interactor import (
    ChildcareSnapshotInteractor,
)
from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.store.adapter.inbound.cli.assign_regions import RegionIndex
from core.matrix.grid_oracle_database_manager import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[6]


def _target_districts(district_name: str | None) -> list[tuple[str, str]]:
    with session_scope() as session:
        statement = select(DistrictOrm.district_code, DistrictOrm.name).order_by(
            DistrictOrm.district_code
        )
        if district_name:
            statement = statement.where(DistrictOrm.name == district_name)
        return [tuple(row) for row in session.execute(statement).all()]


def region_updates(
    centers: list[tuple[str, str]], codes: list[str | None]
) -> list[dict[str, str]]:
    """(center_id, district_code)별 판정 행정동 중 등록 자치구 안(region_code 앞 5자리 일치)만 채택."""
    return [
        {"center_id": center_id, "region_code": code}
        for (center_id, district_code), code in zip(centers, codes)
        if code is not None and code.startswith(district_code)
    ]


def assign_regions() -> None:
    """좌표 보유·region 미기입 시설만 행정동 공간조인 — store assign_regions와 동일 판정."""
    with session_scope() as session:
        refs = session.execute(
            select(RegionOrm.region_code, RegionOrm.geometry_ref).where(
                RegionOrm.geometry_ref.is_not(None)
            )
        ).all()
        rows = session.execute(
            select(
                ChildcareCenterOrm.center_id,
                ChildcareCenterOrm.district_code,
                ChildcareCenterOrm.lng,
                ChildcareCenterOrm.lat,
            ).where(
                ChildcareCenterOrm.lat.is_not(None),
                ChildcareCenterOrm.lng.is_not(None),
                ChildcareCenterOrm.region_code.is_(None),
            )
        ).all()
        print(f"childcare collector: 공간조인 대상 {len(rows)}건", flush=True)
        if not rows:
            return
        index = RegionIndex.from_refs(_REPO_ROOT, [tuple(r) for r in refs])
        codes = index.locate_many([r.lng for r in rows], [r.lat for r in rows])
        updates = region_updates([(r.center_id, r.district_code) for r in rows], codes)
        if updates:
            session.execute(update(ChildcareCenterOrm), updates)
        print(
            f"childcare collector: region 기입 {len(updates)}건 / 미판정 {len(rows) - len(updates)}건",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--district", help="자치구명 (예: 종로구) — 생략 시 25개 전체")
    args = parser.parse_args()

    observed_on = date.today()
    gateway = ChildcarePortalGateway()
    interactor = ChildcareSnapshotInteractor(
        repository=SqlAlchemyChildcareCenterRepository(), gateway=gateway
    )

    processed_total = failed = 0
    for district_code, name in _target_districts(args.district):
        try:
            processed = interactor.ingest(district_code, observed_on)
            processed_total += processed
            print(f"childcare collector: {name}({district_code}) — {processed}건 업서트", flush=True)
        except Exception:
            failed += 1
            print(f"childcare collector: {name}({district_code}) — 실패", flush=True)
            traceback.print_exc()

    print(
        f"childcare collector: 총 {processed_total}건 업서트 (API {gateway.call_count}회 호출)",
        flush=True,
    )
    assign_regions()
    if failed:
        print(f"childcare collector: {failed}개 자치구 실패", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
