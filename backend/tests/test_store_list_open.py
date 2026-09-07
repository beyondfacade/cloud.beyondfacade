"""store 목록 검증 — GET /stores?region=&industry= 마커 계약·404 에러 바디 (Fake 포트)."""

from collections.abc import Iterator
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from apps.store.app.dtos.store_dto import IngestTarget
from apps.store.app.ports.input.store_use_case import StoreUseCase
from apps.store.app.ports.output.store_port import (
    IndustryCatalogPort,
    StorePermitGatewayPort,
    StoreRepositoryPort,
)
from apps.store.app.use_cases.store_interactor import StoreInteractor
from apps.store.dependencies.store_dependencies import get_store_use_case
from apps.store.domain.entities.store_entity import Store
from apps.store.domain.errors import IndustryNotFoundError
from main import app


class FakeRepository(StoreRepositoryPort):
    def __init__(self, stores: list[Store]) -> None:
        self._stores = stores

    def upsert(self, stores: list[Store]) -> int:
        raise NotImplementedError

    def latest_source_updated_at(
        self, industry_id: str, district_code: str
    ) -> datetime | None:
        raise NotImplementedError

    def list_open(self, region_code: str, industry_id: str) -> list[Store]:
        return [
            s
            for s in self._stores
            if s.region_code == region_code
            and s.industry_id == industry_id
            and s.close_date is None
            and s.lat is not None
            and s.lng is not None
        ]


class FakeGateway(StorePermitGatewayPort):
    def iter_stores(
        self, target: IngestTarget, updated_since: datetime | None
    ) -> Iterator[Store]:
        yield from ()


class FakeIndustryCatalog(IndustryCatalogPort):
    def exists(self, industry_id: str) -> bool:
        return industry_id == "cafe"


def _store(store_id: str, open_date: date | None = date(2020, 1, 2)) -> Store:
    return Store(
        store_id=store_id,
        name=f"업소 {store_id}",
        industry_id="cafe",
        district_code="11680",
        open_date=open_date,
        close_date=None,
        status_code="01",
        status_name="영업",
        lat=37.5,
        lng=127.03,
        source_updated_at=datetime(2026, 9, 1),
        region_code="1168064000",
    )


def _interactor(stores: list[Store]) -> StoreInteractor:
    return StoreInteractor(
        repository=FakeRepository(stores),
        gateway=FakeGateway(),
        industry_catalog=FakeIndustryCatalog(),
    )


def test_list_open_stores_returns_dtos_for_region_and_industry():
    interactor = _interactor([_store("s1"), _store("s2", open_date=None)])
    dtos = interactor.list_open_stores("1168064000", "cafe")
    assert [d.store_id for d in dtos] == ["s1", "s2"]
    assert dtos[0].status_name == "영업"
    assert dtos[1].open_date is None


def test_list_open_stores_rejects_unknown_industry():
    with pytest.raises(IndustryNotFoundError):
        _interactor([]).list_open_stores("1168064000", "bakery")


def _client(stores: list[Store]) -> TestClient:
    fake: StoreUseCase = _interactor(stores)
    app.dependency_overrides[get_store_use_case] = lambda: fake
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_stores_endpoint_returns_marker_contract():
    client = _client([_store("s1")])
    response = client.get("/stores?region=1168064000&industry=cafe")
    assert response.status_code == 200
    assert response.json() == [
        {
            "store_id": "s1",
            "name": "업소 s1",
            "lat": 37.5,
            "lng": 127.03,
            "status_name": "영업",
            "open_date": "2020-01-02",
        }
    ]


def test_stores_endpoint_404_on_unknown_industry():
    client = _client([])
    response = client.get("/stores?region=1168064000&industry=bakery")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "INDUSTRY_NOT_FOUND"
    assert body["error"]["message"]
