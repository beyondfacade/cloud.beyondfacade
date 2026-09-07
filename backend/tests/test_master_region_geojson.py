"""region 경계 FeatureCollection 조립 — GET /regions/geojson.

프론트엔드 계약: FeatureCollection, 각 Feature의 properties = {region_code, name}.
name은 경계 파일 properties(adm_nm/emd_kor_nm 혼재)가 아니라 DB region.name에서 온다.
"""

from apps.master.app.use_cases.region_interactor import RegionInteractor
from apps.master.app.use_cases.region_use_case_proxy import CachingRegionUseCaseProxy
from apps.master.app.ports.output.region_port import (
    RegionBoundaryReaderPort,
    RegionRepositoryPort,
)
from apps.master.domain.entities.region_entity import Region


class FakeRepository(RegionRepositoryPort):
    def __init__(self, regions: list[Region]) -> None:
        self._regions = regions

    def list_regions(self) -> list[Region]:
        return self._regions

    def find(self, region_code: str) -> Region | None:
        return next((r for r in self._regions if r.region_code == region_code), None)


class FakeBoundaryReader(RegionBoundaryReaderPort):
    def __init__(self, features: dict[str, dict]) -> None:
        self._features = features
        self.read_count = 0

    def read_feature(self, geometry_ref: str) -> dict:
        self.read_count += 1
        return self._features[geometry_ref]


def _feature(coords: list) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "MultiPolygon", "coordinates": coords},
        "properties": {"adm_nm": "파일속이름", "source_layer": "lt_c_cademd"},
    }


def _interactor() -> tuple[RegionInteractor, FakeBoundaryReader]:
    regions = [
        Region(
            region_code="1111051500",
            district_code="11110",
            name="청운효자동",
            geometry_ref="data/geojson/regions/1111051500.json",
        ),
        Region(
            region_code="1111000000",
            district_code="11110",
            name="경계없는동",
            geometry_ref=None,
        ),
    ]
    reader = FakeBoundaryReader(
        {
            "data/geojson/regions/1111051500.json": _feature(
                [[[[126.12345678901, 37.98765432109], [126.2, 37.9], [126.1, 37.8], [126.12345678901, 37.98765432109]]]]
            )
        }
    )
    return RegionInteractor(repository=FakeRepository(regions), boundary_reader=reader), reader


def test_geojson_builds_feature_collection_with_db_properties():
    interactor, _ = _interactor()
    fc = interactor.geojson()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1  # geometry_ref 없는 동은 제외
    feature = fc["features"][0]
    assert feature["type"] == "Feature"
    assert feature["properties"] == {"region_code": "1111051500", "name": "청운효자동"}
    assert feature["geometry"]["type"] == "MultiPolygon"


def test_geojson_rounds_coordinates_to_display_precision():
    interactor, _ = _interactor()
    fc = interactor.geojson()
    first_point = fc["features"][0]["geometry"]["coordinates"][0][0][0]
    assert first_point == [126.12346, 37.98765]  # 소수 5자리 (~1.1m)


def test_caching_proxy_reads_files_only_once():
    interactor, reader = _interactor()
    proxy = CachingRegionUseCaseProxy(interactor)
    first = proxy.geojson()
    second = proxy.geojson()
    assert first is second
    assert reader.read_count == 1
