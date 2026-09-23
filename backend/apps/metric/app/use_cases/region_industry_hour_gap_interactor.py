"""시간대 어긋남 배치 — 유동인구와 매출을 같은 6구간 강도로 놓고 뺀다 (설계서 §4-2).

이 프로젝트에서 새로 가능해진 것이다. 두 원천이 같은 시간 구간을 쓰기 때문에 같은 동·같은
구간으로 나란히 놓을 수 있다. 양쪽 모두 시간당 보정을 거친 뒤에 뺀다 — 원값끼리 빼면 긴 구간이
무조건 이겨 부호가 통째로 뒤집힌다.
"""

from apps.metric.app.dtos.region_industry_hour_gap_dto import RegionIndustryHourGapDto
from apps.metric.app.ports.input.region_industry_hour_gap_use_case import (
    RegionIndustryHourGapUseCase,
)
from apps.metric.app.ports.output.region_industry_hour_gap_port import (
    RegionFootfallHourPort,
    RegionIndustryHourGapRepositoryPort,
    RegionIndustryHourSalesPort,
)
from apps.metric.domain.entities.region_industry_hour_gap_entity import (
    RegionIndustryHourGap,
)
from apps.metric.domain.value_objects.hour_band import HOUR_BANDS, band_intensities


class RegionIndustryHourGapInteractor(RegionIndustryHourGapUseCase):
    def __init__(
        self,
        repository: RegionIndustryHourGapRepositoryPort,
        footfall: RegionFootfallHourPort,
        sales: RegionIndustryHourSalesPort,
    ) -> None:
        self._repository = repository
        self._footfall = footfall
        self._sales = sales

    def myself(self) -> RegionIndustryHourGapDto:
        return RegionIndustryHourGapDto(
            region_code="myself",
            industry_id="cafe",
            year_quarter="20251",
            hour_band="06_11",
            footfall_intensity=1.0,
            sales_intensity=1.0,
            gap=0.0,
        )

    def build(self, quarters: list[str]) -> int:
        footfall_intensity = {
            (row.region_code, row.year_quarter): intensity
            for row in self._footfall.hour_values(quarters)
            if (intensity := band_intensities(row.values))
        }
        gaps: list[RegionIndustryHourGap] = []
        for row in self._sales.hour_sales(quarters):
            footfall = footfall_intensity.get((row.region_code, row.year_quarter))
            sales = band_intensities(row.values)
            # 유동인구가 없는 동(원천에만 있는 옛 행정동)과 매출이 0인 조합은 행을 만들지 않는다
            if not footfall or not sales:
                continue
            gaps.extend(
                RegionIndustryHourGap(
                    region_code=row.region_code,
                    industry_id=row.industry_id,
                    year_quarter=row.year_quarter,
                    hour_band=band,
                    footfall_intensity=footfall[band],
                    sales_intensity=sales[band],
                    gap=sales[band] - footfall[band],
                )
                for band in HOUR_BANDS
            )
        return self._repository.upsert(gaps)

    def list_bands(
        self, region_code: str, industry_id: str, year_quarter: str
    ) -> list[RegionIndustryHourGapDto]:
        return [
            RegionIndustryHourGapDto(
                region_code=entity.region_code,
                industry_id=entity.industry_id,
                year_quarter=entity.year_quarter,
                hour_band=entity.hour_band,
                footfall_intensity=entity.footfall_intensity,
                sales_intensity=entity.sales_intensity,
                gap=entity.gap,
            )
            for entity in self._repository.list_bands(region_code, industry_id, year_quarter)
        ]
