"""서울 상권분석서비스 동네 맥락 7종 적재 러너 (Driving Adapter, CLI).

- 원천: 서울 열린데이터광장 공개분 로컬 CSV (`data/raw/seoul_commerce/`, CP949 — API 호출 0회).
  7종 모두 ZIP 배포가 없어 포털 시트 탭의 전체 CSV 내려받기로 확보했다 (설계서 §2)
  · footfall_adstrd/  OA-22178 길단위인구   9,350행 → 22행 전개
  · worker_adstrd/    OA-22184 직장인구     9,108행 → 21행 전개 (**414개 동뿐**)
  · resident_adstrd/  OA-22183 상주인구     9,350행 → 인구 21행 + 가구 3행
  · apartment_adstrd/ OA-22163 아파트       9,331행 → 스톡 13행 + 평균 1행
  · facility_adstrd/  OA-22169 집객시설     9,350행 → 20행 전개
  · spending_adstrd/  OA-22166 소비         9,350행 → 11행 전개
  · change_adstrd/    OA-15575 상권변화지표 9,350행 → 동별 1행 + 서울 평균 22행(중복 제거)
- 시점 범위 20211~20262 **22분기**. commerce(20분기)보다 넓다 — 자르지 않고 전량 적재한다
- region 해석: region 427행을 앞 8자리 키 맵으로 1회 로드. 원천에만 있는 옛 행정동
  (11230536 용신동 · 11680740 일원2동 · 11740520 상일동)은 region_code NULL로 적재한다
- 멱등: 각 테이블 PK 기준 INSERT … ON CONFLICT DO UPDATE
- 원천이 정적 아카이브라 크론 비대상 — 갱신은 파일 재확보 후 재실행 (멱등)

실행: python -m apps.neighborhood.adapter.inbound.cli.load_neighborhood
      [--kind footfall|worker|resident|apartment|facility|spending|change|all]
"""

import argparse
from collections.abc import Callable
from pathlib import Path

from apps.neighborhood.adapter.outbound.gateways.region_catalog_gateway import RegionCatalogGateway
from apps.neighborhood.adapter.outbound.gateways.seoul_neighborhood_csv_gateway import (
    SeoulApartmentHouseholdCsvGateway,
    SeoulCommerceChangeBaselineCsvGateway,
    SeoulCommerceChangeCsvGateway,
    SeoulFacilityCsvGateway,
    SeoulFootfallCsvGateway,
    SeoulHousingAverageCsvGateway,
    SeoulResidentHouseholdCsvGateway,
    SeoulResidentPopulationCsvGateway,
    SeoulSpendingCsvGateway,
    SeoulWorkerPopulationCsvGateway,
)
from apps.neighborhood.adapter.outbound.repositories.region_commerce_change_repository import (
    SqlAlchemyRegionCommerceChangeRepository,
)
from apps.neighborhood.adapter.outbound.repositories.region_facility_quarter_repository import (
    SqlAlchemyRegionFacilityQuarterRepository,
)
from apps.neighborhood.adapter.outbound.repositories.region_footfall_quarter_repository import (
    SqlAlchemyRegionFootfallQuarterRepository,
)
from apps.neighborhood.adapter.outbound.repositories.region_household_quarter_repository import (
    SqlAlchemyRegionHouseholdQuarterRepository,
)
from apps.neighborhood.adapter.outbound.repositories.region_housing_average_quarter_repository import (
    SqlAlchemyRegionHousingAverageQuarterRepository,
)
from apps.neighborhood.adapter.outbound.repositories.region_population_quarter_repository import (
    SqlAlchemyRegionPopulationQuarterRepository,
)
from apps.neighborhood.adapter.outbound.repositories.region_spending_quarter_repository import (
    SqlAlchemyRegionSpendingQuarterRepository,
)
from apps.neighborhood.adapter.outbound.repositories.seoul_commerce_change_baseline_repository import (
    SqlAlchemySeoulCommerceChangeBaselineRepository,
)
from apps.neighborhood.app.dtos.neighborhood_ingest_result_dto import NeighborhoodIngestResultDto
from apps.neighborhood.app.use_cases.region_commerce_change_interactor import (
    RegionCommerceChangeIngestInteractor,
)
from apps.neighborhood.app.use_cases.region_facility_quarter_interactor import (
    RegionFacilityQuarterIngestInteractor,
)
from apps.neighborhood.app.use_cases.region_footfall_quarter_interactor import (
    RegionFootfallQuarterIngestInteractor,
)
from apps.neighborhood.app.use_cases.region_household_quarter_interactor import (
    RegionHouseholdQuarterIngestInteractor,
)
from apps.neighborhood.app.use_cases.region_housing_average_quarter_interactor import (
    RegionHousingAverageQuarterIngestInteractor,
)
from apps.neighborhood.app.use_cases.region_population_quarter_interactor import (
    RegionPopulationQuarterIngestInteractor,
)
from apps.neighborhood.app.use_cases.region_spending_quarter_interactor import (
    RegionSpendingQuarterIngestInteractor,
)
from apps.neighborhood.app.use_cases.seoul_commerce_change_baseline_interactor import (
    SeoulCommerceChangeBaselineIngestInteractor,
)

_RAW_DIR = Path(__file__).resolve().parents[6] / "data" / "raw" / "seoul_commerce"

# kind → 원천 디렉토리. kind 하나가 테이블 둘에 들어가는 경우가 있어(상주·아파트·상권변화)
# 디렉토리와 테이블은 1:1이 아니다
_SOURCE_DIRS = {
    "footfall": "footfall_adstrd",
    "worker": "worker_adstrd",
    "resident": "resident_adstrd",
    "apartment": "apartment_adstrd",
    "facility": "facility_adstrd",
    "spending": "spending_adstrd",
    "change": "change_adstrd",
}

# 적재 결과를 테이블별로 찍기 위한 라벨 + DTO 쌍
_TableResults = list[tuple[str, NeighborhoodIngestResultDto]]


def source_paths(kind: str, raw_dir: Path = _RAW_DIR) -> list[Path]:
    directory = raw_dir / _SOURCE_DIRS[kind]
    paths = sorted(directory.glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"동네 맥락 CSV 없음: {directory}/*.csv")
    return paths


def _ingest_footfall(paths: list[Path]) -> _TableResults:
    interactor = RegionFootfallQuarterIngestInteractor(
        repository=SqlAlchemyRegionFootfallQuarterRepository(),
        gateway=SeoulFootfallCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    return [("region_footfall_quarter", interactor.ingest(paths))]


def _ingest_worker(paths: list[Path]) -> _TableResults:
    interactor = RegionPopulationQuarterIngestInteractor(
        repository=SqlAlchemyRegionPopulationQuarterRepository(),
        gateway=SeoulWorkerPopulationCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    return [("region_population_quarter(worker)", interactor.ingest(paths))]


def _ingest_resident(paths: list[Path]) -> _TableResults:
    """상주인구 CSV 하나가 인구 21행과 가구 3행 두 테이블로 갈린다 (설계서 §3-3)."""
    population = RegionPopulationQuarterIngestInteractor(
        repository=SqlAlchemyRegionPopulationQuarterRepository(),
        gateway=SeoulResidentPopulationCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    household = RegionHouseholdQuarterIngestInteractor(
        repository=SqlAlchemyRegionHouseholdQuarterRepository(),
        gateway=SeoulResidentHouseholdCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    return [
        ("region_population_quarter(resident)", population.ingest(paths)),
        ("region_household_quarter(household)", household.ingest(paths)),
    ]


def _ingest_apartment(paths: list[Path]) -> _TableResults:
    """아파트 CSV 하나가 세대·단지 수(긴 형태)와 평균 면적·시가(별도 테이블)로 갈린다."""
    household = RegionHouseholdQuarterIngestInteractor(
        repository=SqlAlchemyRegionHouseholdQuarterRepository(),
        gateway=SeoulApartmentHouseholdCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    average = RegionHousingAverageQuarterIngestInteractor(
        repository=SqlAlchemyRegionHousingAverageQuarterRepository(),
        gateway=SeoulHousingAverageCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    return [
        ("region_household_quarter(apartment)", household.ingest(paths)),
        ("region_housing_average_quarter", average.ingest(paths)),
    ]


def _ingest_facility(paths: list[Path]) -> _TableResults:
    interactor = RegionFacilityQuarterIngestInteractor(
        repository=SqlAlchemyRegionFacilityQuarterRepository(),
        gateway=SeoulFacilityCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    return [("region_facility_quarter", interactor.ingest(paths))]


def _ingest_spending(paths: list[Path]) -> _TableResults:
    interactor = RegionSpendingQuarterIngestInteractor(
        repository=SqlAlchemyRegionSpendingQuarterRepository(),
        gateway=SeoulSpendingCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    return [("region_spending_quarter", interactor.ingest(paths))]


def _ingest_change(paths: list[Path]) -> _TableResults:
    """**서울 평균(baseline)이 먼저다.** 동별 행의 year_quarter가 이를 FK로 참조한다(§3-5)."""
    baseline = SeoulCommerceChangeBaselineIngestInteractor(
        repository=SqlAlchemySeoulCommerceChangeBaselineRepository(),
        gateway=SeoulCommerceChangeBaselineCsvGateway(),
    )
    change = RegionCommerceChangeIngestInteractor(
        repository=SqlAlchemyRegionCommerceChangeRepository(),
        gateway=SeoulCommerceChangeCsvGateway(),
        region_catalog=RegionCatalogGateway(),
    )
    return [
        ("seoul_commerce_change_baseline", baseline.ingest(paths)),
        ("region_commerce_change", change.ingest(paths)),
    ]


# dict 순서 = --kind all 실행 순서
_INGESTORS: dict[str, Callable[[list[Path]], _TableResults]] = {
    "footfall": _ingest_footfall,
    "worker": _ingest_worker,
    "resident": _ingest_resident,
    "apartment": _ingest_apartment,
    "facility": _ingest_facility,
    "spending": _ingest_spending,
    "change": _ingest_change,
}


def load(kind: str, raw_dir: Path = _RAW_DIR) -> _TableResults:
    paths = source_paths(kind, raw_dir)
    print(f"neighborhood loader: {kind} — 파일 {len(paths)}개", flush=True)
    results = _INGESTORS[kind](paths)
    for label, result in results:
        print(
            f"neighborhood loader: {label} {result.processed}행 업서트"
            f" — region 기입 {result.region_resolved}건 / 미매칭 {result.region_unresolved}건",
            flush=True,
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=[*_INGESTORS, "all"], default="all")
    args = parser.parse_args()
    for kind in _INGESTORS if args.kind == "all" else [args.kind]:
        load(kind)


if __name__ == "__main__":
    main()
