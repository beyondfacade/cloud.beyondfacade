"""GET /regions/geojson — 미리 직렬화·압축한 본문을 재사용한다 (부하 테스트 7차: 요청마다 JSON 생성 + gzip 레벨 9).

경계는 프로세스당 1번 읽어 캐시하는데(`CachingRegionUseCaseProxy`), 직렬화·압축은 요청마다 다시 하고 있었다.
"""

import gzip
import json

from fastapi.testclient import TestClient

from apps.master.adapter.inbound.api.v1 import region_router
from apps.master.dependencies.region_dependencies import get_region_use_case
from main import app

_GEOJSON = {
    "type": "FeatureCollection",
    "features": [{"type": "Feature", "properties": {"region_code": "1111051500", "name": "청운효자동"}, "geometry": None}]
    * 40,  # 압축 대상(1KB 이상)이 되게
}


class _FakeRegionUseCase:
    def geojson(self) -> dict:
        return _GEOJSON


def _client() -> TestClient:
    app.dependency_overrides[get_region_use_case] = _FakeRegionUseCase
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_region_use_case, None)


def test_gzip을_받는_클라이언트에는_미리_압축한_본문을_그대로_준다():
    response = _client().get("/regions/geojson", headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert "Accept-Encoding" in response.headers["vary"]
    assert response.json() == _GEOJSON  # TestClient가 풀어서 준다


def test_gzip을_못_받는_클라이언트에는_압축하지_않은_JSON을_준다():
    response = _client().get("/regions/geojson", headers={"Accept-Encoding": "identity"})

    assert response.status_code == 200
    assert "content-encoding" not in response.headers
    assert json.loads(response.content) == _GEOJSON


def test_같은_경계_dict면_직렬화_압축을_다시_하지_않는다():
    first = region_router._encoded(_GEOJSON)
    second = region_router._encoded(_GEOJSON)

    assert first is second
    assert json.loads(gzip.decompress(first.gzip)) == _GEOJSON
