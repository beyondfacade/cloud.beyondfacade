"""Driven Adapter — 서울 자치구 코드·이름 (cross-BC 접근은 어댑터 레이어에서만).

읽기 방향은 `funding` → `master` 단방향. 25행 고정이라 프로세스 수명 동안 한 번만 읽는다.
"""

from functools import lru_cache

from sqlalchemy import select

from apps.funding.app.ports.output.funding_program_port import (
    DistrictNameLookupPort,
    SeoulDistrictNamesPort,
)
from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from core.matrix.grid_oracle_database_manager import session_scope


@lru_cache(maxsize=1)
def _load_districts() -> dict[str, str]:
    with session_scope() as session:
        rows = session.execute(select(DistrictOrm.district_code, DistrictOrm.name)).all()
    return {code: name for code, name in rows}


class SeoulDistrictNamesGateway(SeoulDistrictNamesPort, DistrictNameLookupPort):
    def names(self) -> frozenset[str]:
        return frozenset(_load_districts().values())

    def name_of(self, district_code: str) -> str | None:
        return _load_districts().get(district_code)
