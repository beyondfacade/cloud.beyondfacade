"""코로나 거리두기 이력 적재 러너 (Driving Adapter, CLI — 과거 이력 1회성, 크론 불요).

data.go.kr 15098772 (2020-12-08~2021-10-31 일별 328건) 1회 호출 전량 수신 →
서울(seoLvl) 동일 단계 연속 구간으로 압축 → shock_event 업서트(멱등) + 업종 영향 연결.
2020-12-08 이전 구간은 seed_shock_events가 보충한다.

실행: python -m apps.shock.adapter.inbound.cli.load_distancing
"""

from apps.shock.adapter.outbound.gateways.covid_distancing_gateway import (
    CovidDistancingGateway,
)
from apps.shock.adapter.outbound.repositories.shock_event_repository import (
    SqlAlchemyShockEventRepository,
)
from apps.shock.app.use_cases.shock_event_interactor import ShockEventInteractor


def main() -> None:
    interactor = ShockEventInteractor(
        repository=SqlAlchemyShockEventRepository(),
        source=CovidDistancingGateway(),
    )
    inserted, updated = interactor.ingest()
    print(f"distancing loader: 신규 {inserted}건 / 갱신 {updated}건")


if __name__ == "__main__":
    main()
