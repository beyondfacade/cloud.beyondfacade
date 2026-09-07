"""R-ONE 임대동향 적재 러너 (Driving Adapter, CLI — 주 1회 크론 실행 대상).

임대료·공실률 통계표 20개(2019~최신, 중대형·소규모 상가) 전량 수신 →
rent_price 병합 업서트(같은 PK 행에 지표별 컬럼 갱신 — 멱등). load_interest_rate 관행.

실행: python -m apps.rent.adapter.inbound.cli.load_rent_price
"""

from collections import Counter

from sqlalchemy.dialects.postgresql import insert

from apps.rent.adapter.outbound.gateways.rone_gateway import RoneRentGateway
from apps.rent.adapter.outbound.orms.rent_price_orm import RentPriceOrm
from apps.rent.domain.entities.rent_price_entity import RentObservation
from core.matrix.grid_oracle_database_manager import session_scope

# 지표 → (값 컬럼, 출처 통계표 컬럼) — 새 지표는 여기 등록으로 확장 (분기 없이)
_METRIC_COLUMNS: dict[str, tuple[str, str]] = {
    "rent": ("rent_per_m2", "rent_statbl_id"),
    "vacancy": ("vacancy_rate", "vacancy_statbl_id"),
}


def _row_values(observation: RentObservation) -> dict:
    value_column, statbl_column = _METRIC_COLUMNS[observation.metric]
    return {
        "id": observation.id,
        "building_type": observation.building_type,
        "cls_id": observation.cls_id,
        "region_name": observation.region_name,
        "region_path": observation.region_path,
        "region_level": observation.region_level,
        "district_code": None,  # 상권 단위 원천 — 자치구 매핑 후속
        "period": observation.period,
        value_column: observation.value,
        statbl_column: observation.statbl_id,
    }


def upsert_observations(observations: list[RentObservation]) -> int:
    """PK(id) 충돌 시 해당 지표 컬럼만 갱신 — 다른 지표·후속 매핑을 지우지 않는다. 멱등."""
    count = 0
    with session_scope() as session:
        for metric, group in _group_by_metric(observations).items():
            value_column, statbl_column = _METRIC_COLUMNS[metric]
            statement = insert(RentPriceOrm).values([_row_values(o) for o in group])
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        value_column: getattr(statement.excluded, value_column),
                        statbl_column: getattr(statement.excluded, statbl_column),
                    },
                )
            )
            count += len(group)
    return count


def _group_by_metric(
    observations: list[RentObservation],
) -> dict[str, list[RentObservation]]:
    groups: dict[str, list[RentObservation]] = {}
    for observation in observations:
        groups.setdefault(observation.metric, []).append(observation)
    return groups


def main() -> None:
    observations = RoneRentGateway().fetch_observations()
    # 같은 지표의 같은 PK가 빈티지 경계에서 겹치면 뒤(새 표본)가 이긴다 — 배치 내 중복 제거
    deduped: dict[tuple[str, str], RentObservation] = {
        (o.metric, o.id): o for o in observations
    }
    unique = list(deduped.values())
    count = upsert_observations(unique)
    by_metric = Counter(o.metric for o in unique)
    periods = sorted({o.period for o in unique})
    print(
        f"rent price loader: {count}행 업서트"
        f" (임대료 {by_metric['rent']} / 공실률 {by_metric['vacancy']})"
        f" — 분기 {periods[0]}~{periods[-1]}"
    )


if __name__ == "__main__":
    main()
