"""행정동 경계 점 판정 Driven Adapter — store BC의 검증된 RegionIndex를 읽기 전용 재사용 (tobacco 전례).

region.geometry_ref 경계 GeoJSON으로 공간 인덱스를 한 번 만들고, 점마다 포함 판정(경계 틈은 최근접 스냅).
"""

from pathlib import Path

from sqlalchemy import select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.shock.app.ports.output.shock_event_region_port import RegionLocatorPort
from apps.store.adapter.inbound.cli.assign_regions import RegionIndex
from core.matrix.grid_oracle_database_manager import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[6]


class RegionIndexLocator(RegionLocatorPort):
    def __init__(self) -> None:
        with session_scope() as session:
            refs = session.execute(
                select(RegionOrm.region_code, RegionOrm.geometry_ref).where(
                    RegionOrm.geometry_ref.is_not(None)
                )
            ).all()
        self._index = RegionIndex.from_refs(_REPO_ROOT, [tuple(r) for r in refs])

    def locate(self, lat: float, lng: float) -> str | None:
        return self._index.locate(lng, lat)
