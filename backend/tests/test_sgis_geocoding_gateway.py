"""SgisGeocodingGateway 단위 검증 — 픽스처 기반 (실호출 없음)."""

import pytest

from apps.store.adapter.outbound.gateways.sgis_geocoding_gateway import (
    SgisGeocodingGateway,
)


class _FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class _FakeClient:
    def __init__(self, routes: dict[str, list[dict]]) -> None:
        self._routes = {k: list(v) for k, v in routes.items()}
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict | None = None):
        self.calls.append((url, params or {}))
        key = "auth" if "authentication" in url else "geocode"
        queue = self._routes[key]
        if not queue:
            raise AssertionError(f"unexpected call: {url}")
        return _FakeResponse(queue.pop(0))


def _gateway(monkeypatch, routes: dict[str, list[dict]]) -> SgisGeocodingGateway:
    monkeypatch.setenv("SGIS_SERVICE_ID", "test-id")
    monkeypatch.setenv("SGIS_SECURITY_KEY", "test-secret")
    # settings 캐시 무효화
    from core.matrix import grid_keymaker_secret_manager as secrets

    secrets.get_settings.cache_clear()
    client = _FakeClient(routes)
    return SgisGeocodingGateway(client=client)


def test_geocode_converts_utm_k_to_wgs84(monkeypatch):
    # 서울시청 근처 UTM-K 대략값 → WGS84 변환 후 서울 범위
    gateway = _gateway(
        monkeypatch,
        {
            "auth": [
                {
                    "errCd": "0",
                    "result": {"accessToken": "tok", "accessTimeout": "9999999999"},
                }
            ],
            "geocode": [
                {
                    "errCd": "0",
                    "result": {
                        "resultdata": [
                            {"x": "953932.9", "y": "1952052.7", "matching": "0"}
                        ]
                    },
                }
            ],
        },
    )
    coords = gateway.geocode("서울특별시 중구 세종대로 110")
    assert coords is not None
    lat, lng = coords
    assert 37.4 < lat < 37.7
    assert 126.8 < lng < 127.2
    assert gateway.call_count == 1


def test_geocode_no_result_returns_none(monkeypatch):
    gateway = _gateway(
        monkeypatch,
        {
            "auth": [
                {
                    "errCd": "0",
                    "result": {"accessToken": "tok", "accessTimeout": "9999999999"},
                }
            ],
            "geocode": [{"errCd": "-100", "errMsg": "검색결과없음"}],
        },
    )
    assert gateway.geocode("존재하지않는주소 xyz") is None


def test_geocode_requires_credentials(monkeypatch):
    monkeypatch.setenv("SGIS_SERVICE_ID", "")
    monkeypatch.setenv("SGIS_SECURITY_KEY", "")
    from core.matrix import grid_keymaker_secret_manager as secrets

    secrets.get_settings.cache_clear()
    gateway = SgisGeocodingGateway(client=_FakeClient({"auth": [], "geocode": []}))
    with pytest.raises(RuntimeError, match="SGIS_SERVICE_ID"):
        gateway.geocode("서울특별시 강남구 테헤란로 1")


def test_주소_형식_불량은_예외가_아니라_건너뛴다(monkeypatch):
    """errCd -200은 "검색할 주소를 확인해주세요" — 이 주소로는 못 찾는다는 뜻이다.

    재시도 목록에 두면 호출만 두 번 쓰고 결국 RuntimeError가 되는데, 인터랙터는 geocode()를
    try로 감싸지 않아 주소 하나가 잘못되면 배치 전체가 죽는다 (2026-09-24 실호출로 확인).
    """
    gateway = _gateway(
        monkeypatch,
        {
            "auth": [
                {"errCd": "0", "result": {"accessToken": "tok", "accessTimeout": "9999999999"}}
            ],
            "geocode": [{"errCd": -200, "errMsg": "검색할 주소를 확인해주세요"}],
        },
    )

    assert gateway.geocode("존재하지않는주소 999-999") is None
    assert gateway.call_count == 1  # 재시도로 호출을 낭비하지 않는다
