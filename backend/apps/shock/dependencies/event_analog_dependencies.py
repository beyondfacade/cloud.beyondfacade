"""Composition Root (DIP) — 유사 사례 UseCase 배선.

흐름 캐시는 프로세스에 하나다 — 요청마다 새로 만들면 캐시가 요청과 함께 사라진다.
"""

from apps.shock.adapter.outbound.gateways.caching_store_flow_gateway import (
    CachingStoreFlowGateway,
)
from apps.shock.adapter.outbound.gateways.store_flow_gateway import StoreFlowGateway
from apps.shock.adapter.outbound.repositories.shock_event_repository import (
    SqlAlchemyShockEventRepository,
)
from apps.shock.app.ports.input.event_analog_use_case import EventAnalogUseCase
from apps.shock.app.use_cases.event_analog_interactor import EventAnalogInteractor

_FLOWS = CachingStoreFlowGateway(StoreFlowGateway())


def get_event_analog_use_case() -> EventAnalogUseCase:
    return EventAnalogInteractor(events=SqlAlchemyShockEventRepository(), flows=_FLOWS)
