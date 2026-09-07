from apps.master.app.dtos.region_dto import RegionDto
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.app.ports.output.region_port import (
    RegionBoundaryReaderPort,
    RegionRepositoryPort,
)

_COORD_PRECISION = 5  # 소수 5자리 ≈ 1.1m — 지도 표시용 (원본 파일은 원 정밀도 유지)


def _round_coords(node: float | list) -> float | list:
    if isinstance(node, list):
        return [_round_coords(child) for child in node]
    return round(node, _COORD_PRECISION)


class RegionInteractor(RegionUseCase):
    def __init__(
        self,
        repository: RegionRepositoryPort,
        boundary_reader: RegionBoundaryReaderPort,
    ) -> None:
        self._repository = repository
        self._boundary_reader = boundary_reader

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
