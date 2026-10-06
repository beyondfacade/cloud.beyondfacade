from apps.shock.app.dtos.shock_event_dto import ShockEventDto
from apps.shock.app.dtos.shock_event_region_dto import RegionalIngestResult
from apps.shock.app.ports.input.shock_event_region_use_case import ShockEventRegionUseCase
from apps.shock.app.ports.output.shock_event_port import ShockEventRepositoryPort
from apps.shock.app.ports.output.shock_event_region_port import (
    RegionalEventSourcePort,
    RegionLocatorPort,
    ShockEventRegionRepositoryPort,
)
from apps.shock.app.use_cases.shock_event_interactor import _to_dto


class ShockEventRegionInteractor(ShockEventRegionUseCase):
    def __init__(
        self,
        events: ShockEventRepositoryPort,
        links: ShockEventRegionRepositoryPort,
        locator: RegionLocatorPort | None = None,
    ) -> None:
        self._events = events
        self._links = links
        self._locator = locator

    def ingest(self, source: RegionalEventSourcePort) -> RegionalIngestResult:
        if self._locator is None:
            raise RuntimeError("ingest에는 RegionLocatorPort 주입이 필요하다")
        result = RegionalIngestResult()
        for located in source.fetch_located_events():
            if located.lat is None or located.lng is None:
                result.no_location.append(located.event)
                continue
            region_code = self._locator.locate(located.lat, located.lng)
            if region_code is None:
                result.no_region.append(located.event)
                continue
            result.linked.append((located.event, region_code))
        result.inserted, result.updated = self._events.upsert([e for e, _ in result.linked])
        self._links.replace_links([(e.event_id, code) for e, code in result.linked])
        return result

    def list_for_region(self, region_code: str) -> list[ShockEventDto]:
        return [_to_dto(e) for e in self._links.list_by_region(region_code)]
