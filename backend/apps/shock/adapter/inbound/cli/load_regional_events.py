"""④지역 이벤트 적재 러너 (Driving Adapter, CLI — 주 1회 크론 실행 대상).

서울 열린데이터광장 3개 원천 → shock_event(layer=regional, category NULL) + shock_event_region:
- OA-22856 도시정비사업: 이주 시작(~이주 종료)·착공 — 주소를 SGIS로 지오코딩
- OA-16096 대규모점포: 개설(인허가)·폐업 — 준대규모점포(SSM) 제외
- OA-15818 아파트: 1,000세대 이상 사용승인(입주)
2019-01-01 이후만. event_id가 결정적이라 재실행 멱등. 위치를 못 정한 이벤트는 저장하지 않고 센다.

실행: python -m apps.shock.adapter.inbound.cli.load_regional_events
"""

from collections import Counter

from apps.shock.adapter.outbound.gateways.region_locator_gateway import RegionIndexLocator
from apps.shock.adapter.outbound.gateways.seoul_regional_event_gateway import (
    ApartmentGateway,
    LargeStoreGateway,
    RedevelopmentGateway,
)
from apps.shock.adapter.outbound.repositories.shock_event_region_repository import (
    SqlAlchemyShockEventRegionRepository,
)
from apps.shock.adapter.outbound.repositories.shock_event_repository import (
    SqlAlchemyShockEventRepository,
)
from apps.shock.app.use_cases.shock_event_region_interactor import (
    ShockEventRegionInteractor,
)
from apps.store.adapter.outbound.gateways.sgis_geocoding_gateway import (
    SgisGeocodingGateway,
)


def _kind(event_id: str) -> str:
    """'regional-redev-migration-2493' → 'redev-migration' (보고용 유형)."""
    return event_id.removeprefix("regional-").rsplit("-", 1)[0]


def main() -> None:
    geocoder = SgisGeocodingGateway()
    interactor = ShockEventRegionInteractor(
        events=SqlAlchemyShockEventRepository(),
        links=SqlAlchemyShockEventRegionRepository(),
        locator=RegionIndexLocator(),
    )
    try:
        for source in (RedevelopmentGateway(geocoder), LargeStoreGateway(), ApartmentGateway()):
            result = interactor.ingest(source)
            kinds = Counter(_kind(event.event_id) for event, _ in result.linked)
            print(
                f"{source.service}: 원천 {source.row_count}행 (API {source.call_count}회)"
                f" → 연결 {len(result.linked)}건 {dict(kinds)}"
                f" / 신규 {result.inserted} 갱신 {result.updated}"
                f" / 건너뜀: 위치 없음 {len(result.no_location)} · 행정동 밖 {len(result.no_region)}",
                flush=True,
            )
            for event in result.no_location + result.no_region:
                print(f"  건너뜀 — {event.event_id} {event.name}")
    finally:
        geocoder.close()
    print(f"SGIS 지오코딩 {geocoder.call_count}회")


if __name__ == "__main__":
    main()
