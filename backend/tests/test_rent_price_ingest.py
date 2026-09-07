"""rent_price 적재 검증 — 실제 DB 병합 업서트 (임대료·공실률이 같은 행에 합쳐진다)."""

from sqlalchemy import delete, select

from apps.rent.adapter.inbound.cli.load_rent_price import upsert_observations
from apps.rent.adapter.outbound.orms.rent_price_orm import RentPriceOrm
from apps.rent.domain.entities.rent_price_entity import RentObservation
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_CLS = "990001"  # 실데이터와 충돌하지 않는 시험용 상권 ID


def _observation(metric: str, value: float, period: str = "2022Q1") -> RentObservation:
    units = {"rent": "천원/㎡", "vacancy": "%"}
    return RentObservation(
        id=f"medium_large:{_TEST_CLS}:{period}",
        building_type="medium_large",
        cls_id=_TEST_CLS,
        region_name="시험상권",
        region_path="서울>시험>시험상권",
        region_level=3,
        period=period,
        metric=metric,
        value=value,
        unit=units[metric],
        statbl_id="TEST_TBL",
    )


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(RentPriceOrm).where(RentPriceOrm.cls_id == _TEST_CLS)
        )


def test_upsert_merges_rent_and_vacancy_into_one_row():
    _cleanup()
    assert upsert_observations([_observation("rent", 38.9)]) == 1
    assert upsert_observations([_observation("vacancy", 10.5)]) == 1
    with session_scope() as session:
        row = session.execute(
            select(RentPriceOrm).where(
                RentPriceOrm.id == f"medium_large:{_TEST_CLS}:2022Q1"
            )
        ).scalar_one()
        # 임대료·공실률 두 소스가 같은 PK 행에 병합 — 서로를 지우지 않는다
        assert row.rent_per_m2 == 38.9
        assert row.vacancy_rate == 10.5
        assert row.rent_statbl_id == "TEST_TBL"
        assert row.vacancy_statbl_id == "TEST_TBL"
        assert row.district_code is None  # 상권 단위 원천 — 자치구 미확정(의도된 미연결)
    _cleanup()


def test_upsert_is_idempotent_and_updates_value():
    _cleanup()
    upsert_observations([_observation("rent", 38.9)])
    upsert_observations([_observation("rent", 40.1)])  # 표본 개편 정정 — 최신값
    with session_scope() as session:
        stored = session.execute(
            select(RentPriceOrm.rent_per_m2).where(
                RentPriceOrm.id == f"medium_large:{_TEST_CLS}:2022Q1"
            )
        ).scalar_one()
    assert stored == 40.1
    _cleanup()
