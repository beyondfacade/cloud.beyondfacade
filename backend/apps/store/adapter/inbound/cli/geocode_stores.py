"""학원·부동산 좌표 결측분 SGIS 지오코딩 러너 (Driving Adapter, CLI).

선행: 수집기가 road_address/jibun_address를 채운 뒤 실행.
후속: assign_regions → build_metrics.

실행:
  python -m apps.store.adapter.inbound.cli.geocode_stores
  python -m apps.store.adapter.inbound.cli.geocode_stores --limit 100
  python -m apps.store.adapter.inbound.cli.geocode_stores --industry academy
"""

import argparse

from apps.store.adapter.outbound.gateways.sgis_geocoding_gateway import (
    SgisGeocodingGateway,
)
from apps.store.adapter.outbound.repositories.store_repository import (
    SqlAlchemyStoreRepository,
)
from apps.store.app.use_cases.geocode_stores_interactor import GeocodeStoresInteractor

_DEFAULT_INDUSTRIES = ["academy", "real_estate"]


def main() -> None:
    parser = argparse.ArgumentParser(description="SGIS 지오코딩 — store lat/lng 대기열")
    parser.add_argument(
        "--industry",
        action="append",
        dest="industries",
        help="대상 industry_id (반복 가능). 기본: academy, real_estate",
    )
    parser.add_argument("--limit", type=int, default=None, help="최대 처리 건수 (스모크용)")
    args = parser.parse_args()
    industries = args.industries or list(_DEFAULT_INDUSTRIES)

    gateway = SgisGeocodingGateway()
    try:
        # 키 없으면 대기열 조회 전에 실패 — 크론 로그에서 원인 즉시 식별
        if not gateway._consumer_key or not gateway._consumer_secret:
            raise RuntimeError(
                "SGIS_SERVICE_ID / SGIS_SECURITY_KEY 미설정 — backend/.env 확인"
            )
        result = GeocodeStoresInteractor(
            repository=SqlAlchemyStoreRepository(),
            gateway=gateway,
        ).run(industry_ids=industries, limit=args.limit)
    finally:
        gateway.close()

    print(
        f"geocode_stores: 시도 {result.attempted} / 성공 {result.geocoded}"
        f" / 미매칭 {result.unmatched} (API {gateway.call_count}회)",
        flush=True,
    )


if __name__ == "__main__":
    main()
