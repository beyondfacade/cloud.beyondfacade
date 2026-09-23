"""서울 상권분석서비스 행정동 계열 적재 러너 (Driving Adapter, CLI).

- 원천: 서울 열린데이터광장 공개분 로컬 CSV (data/raw/seoul_commerce/, CP949 — API 호출 0회)
  · sales_adstrd/  OA-22175 추정매출-행정동  343,167행 / 63업종 / 2021Q1~2025Q4
  · store_adstrd/  OA-22172 점포-행정동      704,470행 / 100업종 / 2021Q1~2025Q4
- region 해석: region 427행을 앞 8자리 키 맵으로 1회 로드. 원천에만 있는 옛 행정동
  (11230536 용신동 · 11680740 일원2동 · 11740520 상일동)은 region_code NULL로 적재한다
- 멱등: PK(adstrd_code, service_industry_code, year_quarter) INSERT … ON CONFLICT DO UPDATE
- 원천이 정적 아카이브라 크론 비대상 — 갱신은 파일 재확보 후 재실행 (멱등)

실행: python -m apps.commerce.adapter.inbound.cli.load_commerce [--kind sales|store|all]
"""

import argparse
from pathlib import Path

from apps.commerce.adapter.outbound.gateways.region_catalog_gateway import RegionCatalogGateway
from apps.commerce.adapter.outbound.gateways.seoul_commerce_csv_gateway import (
    SeoulCommerceSalesCsvGateway,
    SeoulCommerceStoreCsvGateway,
)
from apps.commerce.adapter.outbound.repositories.region_commerce_sales_repository import (
    SqlAlchemyRegionCommerceSalesRepository,
)
from apps.commerce.adapter.outbound.repositories.region_commerce_store_repository import (
    SqlAlchemyRegionCommerceStoreRepository,
)
from apps.commerce.app.dtos.region_commerce_sales_dto import CommerceIngestResultDto
from apps.commerce.app.use_cases.region_commerce_sales_interactor import (
    RegionCommerceSalesIngestInteractor,
)
from apps.commerce.app.use_cases.region_commerce_store_interactor import (
    RegionCommerceStoreIngestInteractor,
)

_RAW_DIR = Path(__file__).resolve().parents[6] / "data" / "raw" / "seoul_commerce"


def source_paths(kind: str, raw_dir: Path = _RAW_DIR) -> list[Path]:
    paths = sorted((raw_dir / f"{kind}_adstrd").glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"상권분석 CSV 없음: {raw_dir / f'{kind}_adstrd'}/*.csv")
    return paths


def _ingest_sales(paths: list[Path]) -> CommerceIngestResultDto:
    interactor = RegionCommerceSalesIngestInteractor(
        repository=SqlAlchemyRegionCommerceSalesRepository(),
        gateway=SeoulCommerceSalesCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    return interactor.ingest(paths)


def _ingest_store(paths: list[Path]) -> CommerceIngestResultDto:
    interactor = RegionCommerceStoreIngestInteractor(
        repository=SqlAlchemyRegionCommerceStoreRepository(),
        gateway=SeoulCommerceStoreCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    return interactor.ingest(paths)


_INGESTORS = {"sales": _ingest_sales, "store": _ingest_store}


def load(kind: str, raw_dir: Path = _RAW_DIR) -> CommerceIngestResultDto:
    paths = source_paths(kind, raw_dir)
    print(f"commerce loader: {kind} — 파일 {len(paths)}개", flush=True)
    result = _INGESTORS[kind](paths)
    print(
        f"commerce loader: {kind} {result.processed}행 업서트"
        f" — region 기입 {result.region_resolved}건 / 미매칭 {result.region_unresolved}건",
        flush=True,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["sales", "store", "all"], default="all")
    args = parser.parse_args()
    for kind in _INGESTORS if args.kind == "all" else [args.kind]:
        load(kind)


if __name__ == "__main__":
    main()
