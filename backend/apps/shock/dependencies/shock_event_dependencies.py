"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.shock.adapter.outbound.repositories.shock_event_repository import (
    SqlAlchemyShockEventRepository,
)
from apps.shock.app.ports.input.shock_event_use_case import ShockEventUseCase
from apps.shock.app.use_cases.shock_event_interactor import ShockEventInteractor


def get_shock_event_use_case() -> ShockEventUseCase:
    # 조회 전용 배선 — ingest는 CLI가 소스 어댑터를 골라 주입한다
    return ShockEventInteractor(repository=SqlAlchemyShockEventRepository())
