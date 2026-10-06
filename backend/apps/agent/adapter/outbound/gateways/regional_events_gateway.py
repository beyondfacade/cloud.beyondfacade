"""Driven Adapter — shock BC 지역 사건 조회 (cross-BC 접근은 이 파일 안에서만)."""

from apps.agent.app.ports.output.agent_port import RegionalEventsPort
from apps.shock.dependencies.shock_event_region_dependencies import get_shock_event_region_use_case


class RegionalEventsGateway(RegionalEventsPort):
    def for_region(self, region_code: str) -> list[dict]:
        return [
            {
                "start_date": e.start_date.isoformat(),
                "end_date": e.end_date.isoformat() if e.end_date else None,
                "name": e.name,
                "source": e.source,
                "source_url": e.source_url,
            }
            for e in get_shock_event_region_use_case().list_for_region(region_code)
        ]
