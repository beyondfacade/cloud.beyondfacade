"""GeocodeStoresInteractor 단위 검증 — Fake 게이트웨이·저장소."""

from datetime import datetime

from apps.store.app.use_cases.geocode_stores_interactor import GeocodeStoresInteractor
from apps.store.domain.entities.store_entity import Store


def _store(
    store_id: str,
    *,
    road: str | None = None,
    jibun: str | None = None,
    lat: float | None = None,
) -> Store:
    return Store(
        store_id=store_id,
        name=store_id,
        industry_id="academy",
        district_code="11680",
        open_date=None,
        close_date=None,
        status_code="open",
        status_name="개원",
        lat=lat,
        lng=None,
        source_updated_at=datetime(2026, 9, 1),
        road_address=road,
        jibun_address=jibun,
    )


class _FakeRepo:
    def __init__(self, pending: list[Store]) -> None:
        self.pending = pending
        self.updates: list[tuple[str, float, float]] = []

    def list_pending(self, industry_ids, limit=None):
        rows = self.pending
        if limit is not None:
            rows = rows[:limit]
        return rows

    def update_coordinates(self, updates):
        self.updates.extend(updates)
        return len(updates)


class _FakeGateway:
    def __init__(self, mapping: dict[str, tuple[float, float] | None]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def geocode(self, address: str):
        self.calls.append(address)
        return self.mapping.get(address)


def test_geocode_prefers_road_then_jibun_fallback():
    repo = _FakeRepo(
        [
            _store("a1", road="도로명A", jibun="지번A"),
            _store("a2", road="도로명B", jibun="지번B"),
            _store("a3", road=None, jibun="지번C"),
        ]
    )
    gateway = _FakeGateway(
        {
            "도로명A": (37.5, 127.0),
            "도로명B": None,
            "지번B": (37.51, 127.01),
            "지번C": (37.52, 127.02),
        }
    )
    result = GeocodeStoresInteractor(repo, gateway).run(["academy"])
    assert result.attempted == 3
    assert result.geocoded == 3
    assert result.unmatched == 0
    assert repo.updates == [
        ("a1", 37.5, 127.0),
        ("a2", 37.51, 127.01),
        ("a3", 37.52, 127.02),
    ]
    assert gateway.calls == ["도로명A", "도로명B", "지번B", "지번C"]


def test_geocode_counts_unmatched():
    repo = _FakeRepo([_store("x", road="없는주소")])
    gateway = _FakeGateway({"없는주소": None})
    result = GeocodeStoresInteractor(repo, gateway).run(["academy"])
    assert (result.attempted, result.geocoded, result.unmatched) == (1, 0, 1)
    assert repo.updates == []
