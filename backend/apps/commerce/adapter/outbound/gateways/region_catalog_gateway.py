"""Driven Adapter — region 마스터 8자리 키 맵 (cross-BC 접근은 어댑터 레이어에서만).

원천 `행정동_코드`는 8자리, 우리 `region.region_code`는 10자리이고 앞 8자리가 1:1이다
(427행 전수 확인, 접두 충돌 0건 — 설계서 §3-1). 427행을 한 번 읽어 맵으로 두고, 행마다
DB를 조회하지 않는다.
"""

from sqlalchemy import select

from apps.commerce.app.ports.output.region_catalog_port import RegionCatalogPort
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope


class RegionCatalogGateway(RegionCatalogPort):
    def region_code_by_adstrd(self) -> dict[str, str]:
        with session_scope() as session:
            codes = session.execute(select(RegionOrm.region_code)).scalars().all()
        return {code[:8]: code for code in codes}
