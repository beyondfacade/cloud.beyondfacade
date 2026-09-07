from apps.master.app.dtos.region_dto import (
    RegionDto,
    RegionSummaryDto,
    SummaryCardDto,
)
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.app.ports.output.region_port import (
    RegionBoundaryReaderPort,
    RegionMetricSummaryPort,
    RegionRepositoryPort,
)
from apps.master.domain.errors import RegionNotFoundError

_COORD_PRECISION = 5  # 소수 5자리 ≈ 1.1m — 지도 표시용 (원본 파일은 원 정밀도 유지)
_NO_DATA = "데이터 없음"


def _round_coords(node: float | list) -> float | list:
    if isinstance(node, list):
        return [_round_coords(child) for child in node]
    return round(node, _COORD_PRECISION)


def _percent(rate: float | None) -> str:
    return _NO_DATA if rate is None else f"{rate * 100:.1f}%"


def _signed_percent(rate: float | None) -> str:
    if rate is None:
        return _NO_DATA
    return f"{'+' if rate >= 0 else ''}{rate * 100:.1f}%"  # 음수 부호는 포맷이 붙인다


class RegionInteractor(RegionUseCase):
    def __init__(
        self,
        repository: RegionRepositoryPort,
        boundary_reader: RegionBoundaryReaderPort,
        # geojson 전용 구성(기존 테스트)이 지표 포트 없이 구성하도록 기본 None
        metric_summary: RegionMetricSummaryPort | None = None,
    ) -> None:
        self._repository = repository
        self._boundary_reader = boundary_reader
        self._metric_summary = metric_summary

    def myself(self) -> RegionDto:
        return RegionDto(region_code="myself", name="region BC 배선 검증")

    def geojson(self) -> dict:
        features = []
        for region in self._repository.list_regions():
            if region.geometry_ref is None:
                continue
            source = self._boundary_reader.read_feature(region.geometry_ref)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": source["geometry"]["type"],
                        "coordinates": _round_coords(source["geometry"]["coordinates"]),
                    },
                    # name은 파일 properties(adm_nm/emd_kor_nm 혼재)가 아니라 DB에서
                    "properties": {"region_code": region.region_code, "name": region.name},
                }
            )
        return {"type": "FeatureCollection", "features": features}

    def summary(self, region_code: str, industry_id: str) -> RegionSummaryDto:
        region = self._repository.find(region_code)
        if region is None:
            raise RegionNotFoundError(region_code)
        snapshot = self._metric_summary.fetch(region_code, industry_id)
        if snapshot is None:
            cards = [
                SummaryCardDto(label=label, value=_NO_DATA, grade="fact")
                for label in ("점포수", "폐업률", "성장률")
            ]
        else:
            cards = [
                SummaryCardDto(label="점포수", value=f"{snapshot.store_count}개", grade="fact"),
                SummaryCardDto(label="폐업률", value=_percent(snapshot.closure_rate), grade="fact"),
                SummaryCardDto(label="성장률", value=_signed_percent(snapshot.growth_rate), grade="fact"),
            ]
        return RegionSummaryDto(
            region_code=region.region_code,
            name=region.name,
            industry_id=industry_id,
            cards=cards,
        )
