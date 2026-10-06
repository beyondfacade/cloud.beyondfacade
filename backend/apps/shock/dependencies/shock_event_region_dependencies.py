"""Composition Root (DIP) — ④지역 이벤트 조회 UseCase에 Adapter를 주입한다."""

from apps.shock.adapter.outbound.repositories.shock_event_region_repository import (
    SqlAlchemyShockEventRegionRepository,
)
from apps.shock.adapter.outbound.repositories.shock_event_repository import (
    SqlAlchemyShockEventRepository,
)
from apps.shock.app.ports.input.shock_event_region_use_case import ShockEventRegionUseCase
from apps.shock.app.use_cases.shock_event_region_interactor import (
    ShockEventRegionInteractor,
)


def get_shock_event_region_use_case() -> ShockEventRegionUseCase:
    # 조회 전용 배선 — ingest는 CLI가 원천·위치판정 어댑터를 골라 주입한다
    return ShockEventRegionInteractor(
        events=SqlAlchemyShockEventRepository(),
        links=SqlAlchemyShockEventRegionRepository(),
    )
