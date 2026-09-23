"""Driven Adapter — master BC의 region·district·industry를 파서 사전으로 (cross-BC는 여기서만).

427동·25구·10업종은 바뀌지 않는 마스터라 프로세스당 1회 로드해 `lru_cache`한다(대구 전례).
"""

from functools import lru_cache

from sqlalchemy import select

from apps.intent.app.ports.output.intent_port import MasterDictionaryPort
from apps.intent.domain.value_objects.master_dictionary import MasterDictionary, RegionEntry
from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope


@lru_cache(maxsize=1)
def _load() -> MasterDictionary:
    with session_scope() as session:
        districts = {
            code: name for code, name in session.execute(select(DistrictOrm.district_code, DistrictOrm.name))
        }
        regions = [
            RegionEntry(region_code=code, name=name, district_code=district, district_name=districts[district])
            for code, name, district in session.execute(
                select(RegionOrm.region_code, RegionOrm.name, RegionOrm.district_code)
            )
        ]
        industries = dict(session.execute(select(IndustryOrm.industry_id, IndustryOrm.name)).all())
    return MasterDictionary(
        regions=regions,
        districts={name: code for code, name in districts.items()},
        industry_names=industries,
    )


class MasterDictionaryGateway(MasterDictionaryPort):
    def load(self) -> MasterDictionary:
        return _load()
