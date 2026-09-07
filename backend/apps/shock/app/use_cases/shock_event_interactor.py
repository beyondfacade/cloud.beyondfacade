from datetime import date

from apps.shock.app.dtos.shock_event_dto import IndustryImpactDto, ShockEventDto
from apps.shock.app.ports.input.shock_event_use_case import ShockEventUseCase
from apps.shock.app.ports.output.shock_event_port import (
    ShockEventRepositoryPort,
    ShockEventSourcePort,
)
from apps.shock.domain.entities.shock_event_entity import ShockEvent
from apps.shock.domain.value_objects.shock_layer import ShockLayer


def _to_dto(entity: ShockEvent) -> ShockEventDto:
    return ShockEventDto(
        event_id=entity.event_id,
        layer=entity.layer,
        name=entity.name,
        start_date=entity.start_date,
        scope=entity.scope,
        source=entity.source,
        end_date=entity.end_date,
        source_url=entity.source_url,
        description=entity.description,
        industry_impacts=[
            IndustryImpactDto(industry_id=i.industry_id, severity=i.severity)
            for i in entity.industry_impacts
        ],
    )


class ShockEventInteractor(ShockEventUseCase):
    def __init__(
        self,
        repository: ShockEventRepositoryPort,
        source: ShockEventSourcePort | None = None,
    ) -> None:
        self._repository = repository
        self._source = source

    def myself(self) -> ShockEventDto:
        return ShockEventDto(
            event_id="myself",
            layer=ShockLayer.POLICY,
            name="shock BC 배선 검증",
            start_date=date(2026, 9, 7),
            scope="전국",
            source="beyondfacade",
        )

    def ingest(self) -> tuple[int, int]:
        if self._source is None:
            raise RuntimeError("ingest에는 ShockEventSourcePort 주입이 필요하다")
        return self._repository.upsert(self._source.fetch_events())

    def list_events(self, industry_id: str | None, limit: int) -> list[ShockEventDto]:
        return [_to_dto(e) for e in self._repository.list_events(industry_id, limit)]
