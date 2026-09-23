"""서울 상권분석서비스 행정동 계열 적재 러너 (Driving Adapter, CLI).

- 원천: 서울 열린데이터광장 공개분 로컬 CSV (data/raw/seoul_commerce/, CP949 — API 호출 0회)
  · sales_adstrd/  OA-22175 추정매출-행정동  343,167행 / 63업종 / 2021Q1~2025Q4
  · store_adstrd/  OA-22172 점포-행정동      704,470행 / 100업종 / 2021Q1~2025Q4
- kind `sales_breakdown`은 같은 sales_adstrd CSV를 다시 읽어 요일·시간대·성별·연령대 분해
  47컬럼을 1NF long으로 편다 (원본 1행 → 구간 23행 = 약 789만 행, 설계서 §4-1)
- region 해석: region 427행을 앞 8자리 키 맵으로 1회 로드. 원천에만 있는 옛 행정동
  (11230536 용신동 · 11680740 일원2동 · 11740520 상일동)은 region_code NULL로 적재한다
- 멱등: PK(adstrd_code, service_industry_code, year_quarter[, dim_type, dim_key])
  INSERT … ON CONFLICT DO UPDATE
- 원천이 정적 아카이브라 크론 비대상 — 갱신은 파일 재확보 후 재실행 (멱등)

실행: python -m apps.commerce.adapter.inbound.cli.load_commerce [--kind sales|store|sales_breakdown|all]
      sales_breakdown은 부모 sales 행이 먼저 있어야 한다 (복합 FK) — all은 이 순서로 돈다
"""

import argparse
from pathlib import Path

from apps.commerce.adapter.outbound.gateways.region_catalog_gateway import RegionCatalogGateway
from apps.commerce.adapter.outbound.gateways.seoul_commerce_csv_gateway import (
    SeoulCommerceSalesBreakdownCsvGateway,
    SeoulCommerceSalesCsvGateway,
    SeoulCommerceStoreCsvGateway,
)
from apps.commerce.adapter.outbound.repositories.region_commerce_sales_breakdown_repository import (
    SqlAlchemyRegionCommerceSalesBreakdownRepository,
)
from apps.commerce.adapter.outbound.repositories.region_commerce_sales_repository import (
    SqlAlchemyRegionCommerceSalesRepository,
)
from apps.commerce.adapter.outbound.repositories.region_commerce_store_repository import (
    SqlAlchemyRegionCommerceStoreRepository,
)
from apps.commerce.app.dtos.region_commerce_sales_dto import CommerceIngestResultDto
from apps.commerce.app.use_cases.region_commerce_sales_breakdown_interactor import (
    RegionCommerceSalesBreakdownIngestInteractor,
)
from apps.commerce.app.use_cases.region_commerce_sales_interactor import (
    RegionCommerceSalesIngestInteractor,
)
from apps.commerce.app.use_cases.region_commerce_store_interactor import (
    RegionCommerceStoreIngestInteractor,
)

_RAW_DIR = Path(__file__).resolve().parents[6] / "data" / "raw" / "seoul_commerce"


def source_paths(kind: str, raw_dir: Path = _RAW_DIR) -> list[Path]:
    directory = _SOURCE_DIRS[kind]
    paths = sorted((raw_dir / f"{directory}_adstrd").glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"상권분석 CSV 없음: {raw_dir / f'{directory}_adstrd'}/*.csv")
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


def _ingest_sales_breakdown(paths: list[Path]) -> CommerceIngestResultDto:
    interactor = RegionCommerceSalesBreakdownIngestInteractor(
        repository=SqlAlchemyRegionCommerceSalesBreakdownRepository(),
        gateway=SeoulCommerceSalesBreakdownCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    return interactor.ingest(paths)


# 분해는 매출과 같은 CSV를 읽는다 — kind와 디렉토리가 1:1이 아니라 분리한다
_SOURCE_DIRS = {"sales": "sales", "store": "store", "sales_breakdown": "sales"}
# dict 순서 = --kind all 실행 순서. 분해는 부모 sales 행이 있어야 복합 FK를 통과한다
_INGESTORS = {
    "sales": _ingest_sales,
    "store": _ingest_store,
    "sales_breakdown": _ingest_sales_breakdown,
}


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
    parser.add_argument(
        "--kind", choices=[*_INGESTORS, "all"], default="all"
    )
    args = parser.parse_args()
    for kind in _INGESTORS if args.kind == "all" else [args.kind]:
        load(kind)


if __name__ == "__main__":
    main()
