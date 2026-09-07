"""SemasConvenienceGateway 파싱·페이징 단위 검증 — 픽스처 기반 (실호출 없음)."""

import pytest

from apps.convenience.adapter.outbound.gateways.semas_convenience_gateway import (
    SemasConvenienceGateway,
)
from apps.convenience.domain.entities.convenience_store_entity import extract_brand

_REGION_CODE = "1168064000"  # 역삼1동 — adongCd(8자리) = region_code 앞 8자리 (실확인)

# 2026-09-07 실응답(역삼1동, stdrYm 202606) 축약 픽스처
_ITEM = {
    "bizesId": "MA010120220800827453",
    "bizesNm": "씨유역삼미래점",
    "brchNm": "",
    "indsSclsCd": "G20405",
    "indsSclsNm": "편의점",
    "ksicCd": "G47122",
    "adongCd": "11680640",
    "adongNm": "역삼1동",
    "lnoAdr": "서울특별시 강남구 역삼동 672-5",
    "rdnmAdr": "서울특별시 강남구 테헤란로33길 32",
    "lon": 127.038836978017,
    "lat": 37.5038668282641,
}


def _page(items: list[dict], total: int, result_code: str = "00") -> dict:
    return {
        "header": {"resultCode": result_code, "resultMsg": "NORMAL SERVICE", "stdrYm": "202606"},
        "body": {"items": items, "totalCount": total, "numOfRows": len(items)},
    }


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


def _gateway_with_pages(
    monkeypatch, pages: list[dict]
) -> tuple[SemasConvenienceGateway, list[dict]]:
    calls: list[dict] = []

    def fake_get(client, url, params):
        calls.append(params)
        return _FakeResponse(pages[len(calls) - 1])

    monkeypatch.setattr(SemasConvenienceGateway, "_get_with_retry", staticmethod(fake_get))
    monkeypatch.setenv("DATA_GO_KR_API_KEY", "test-key")
    return SemasConvenienceGateway(), calls


def test_extract_brand_keyword_dispatch():
    # 실응답 상호 변형 실측 사본 (역삼1동 149건)
    assert extract_brand("지에스25역삼미래점", None) == "GS25"
    assert extract_brand("GS25역삼상록점", None) == "GS25"
    assert extract_brand("씨유역삼비엘점", None) == "CU"
    assert extract_brand("CU역삼시티점", None) == "CU"
    assert extract_brand("세븐일레븐역삼보브점", None) == "세븐일레븐"
    assert extract_brand("코리아세븐역삼", "타워점") == "세븐일레븐"
    assert extract_brand("세븐역삼우일점", "코리아") == "세븐일레븐"
    assert extract_brand("이마트24", "강남역점") == "이마트24"
    assert extract_brand("미니스톱역삼점", None) == "미니스톱"
    # 전량 적재 후 기타 7.9% 표본에서 발견된 변형 (2026-09-07 실측)
    assert extract_brand("지에스신사초롱점", None) == "GS25"  # '25' 없는 지에스 상호
    assert extract_brand("비지에프휴먼넷역삼센타점", None) == "CU"  # BGF리테일 = CU 운영사
    assert extract_brand("비지에프리테일이화여대ECC점", None) == "CU"
    assert extract_brand("스토리웨이편의점", None) is None  # 미확인 브랜드는 None 보존
    assert extract_brand("오렌지마트", None) is None


def test_to_entity_maps_real_fields(monkeypatch):
    gateway, calls = _gateway_with_pages(monkeypatch, [_page([_ITEM], total=1)])
    (store,) = list(gateway.iter_stores(_REGION_CODE))

    assert store.store_id == "MA010120220800827453"
    assert store.name == "씨유역삼미래점"
    assert store.branch_name is None  # 공란 지점명은 None
    assert store.brand == "CU"
    assert store.region_code == _REGION_CODE  # 요청 행정동 10자리 그대로 (프리픽스 유일 실측)
    assert store.lat == pytest.approx(37.5038668, abs=1e-6)
    assert store.lng == pytest.approx(127.0388370, abs=1e-6)
    assert store.road_address == "서울특별시 강남구 테헤란로33길 32"
    assert store.jibun_address == "서울특별시 강남구 역삼동 672-5"
    assert store.source_stdr_ym == "202606"
    # 호출 파라미터 — adongCd 8자리 + 편의점 소분류 고정 필터
    assert calls[0]["key"] == "11680640"
    assert calls[0]["indsSclsCd"] == "G20405"


def test_missing_coords_preserved_as_none(monkeypatch):
    item = {**_ITEM, "lon": "", "lat": None}
    gateway, _ = _gateway_with_pages(monkeypatch, [_page([item], total=1)])
    (store,) = list(gateway.iter_stores(_REGION_CODE))
    assert store.lat is None and store.lng is None


def test_paging_iterates_until_total(monkeypatch):
    page1 = _page([{**_ITEM, "bizesId": f"MA{n:04d}"} for n in range(3)], total=5)
    page2 = _page([{**_ITEM, "bizesId": f"MA{n:04d}"} for n in range(3, 5)], total=5)
    gateway, calls = _gateway_with_pages(monkeypatch, [page1, page2])
    monkeypatch.setattr(
        "apps.convenience.adapter.outbound.gateways.semas_convenience_gateway._PAGE_SIZE", 3
    )

    stores = list(gateway.iter_stores(_REGION_CODE))
    assert len(stores) == 5
    assert [c["pageNo"] for c in calls] == [1, 2]
    assert gateway.call_count == 2


def test_empty_dong_yields_nothing(monkeypatch):
    gateway, _ = _gateway_with_pages(monkeypatch, [_page([], total=0)])
    assert list(gateway.iter_stores(_REGION_CODE)) == []


def test_error_result_code_raises(monkeypatch):
    gateway, _ = _gateway_with_pages(monkeypatch, [_page([], total=0, result_code="30")])
    with pytest.raises(RuntimeError, match="semas convenience API"):
        list(gateway.iter_stores(_REGION_CODE))
