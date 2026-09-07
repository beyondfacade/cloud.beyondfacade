"""정책 충격 시드 적재 러너 (Driving Adapter, CLI).

시드 파일(gateways/seed/shock_events_seed.json — 각 행 출처 명시)을 읽어
shock_event 업서트(멱등) + 업종 영향 연결. 거리두기 API 미커버 구간·최저임금·
주 52시간제·재난지원금(왜곡 주의 포함)을 담는다 — brainstorming §5.2.

실행: python -m apps.shock.adapter.inbound.cli.seed_shock_events
"""

from apps.shock.adapter.outbound.gateways.shock_seed_gateway import ShockSeedGateway
from apps.shock.adapter.outbound.repositories.shock_event_repository import (
    SqlAlchemyShockEventRepository,
)
from apps.shock.app.use_cases.shock_event_interactor import ShockEventInteractor


def main() -> None:
    interactor = ShockEventInteractor(
        repository=SqlAlchemyShockEventRepository(),
        source=ShockSeedGateway(),
    )
    inserted, updated = interactor.ingest()
    print(f"shock seed: 신규 {inserted}건 / 갱신 {updated}건")


if __name__ == "__main__":
    main()
