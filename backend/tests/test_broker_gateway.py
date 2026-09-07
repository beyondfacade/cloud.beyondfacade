"""MolitBrokerGateway 파싱·페이징 단위 검증 — 픽스처 기반 (실호출 없음)."""

from datetime import date, datetime

import pytest

from apps.store.adapter.outbound.gateways.molit_broker_gateway import (
    MolitBrokerGateway,
    _parse_date,
    _to_source_updated_at,
)

# 2026-09-07 실응답(강남구) 축약 픽스처
_ITEM = {
    "jurirno": "9250-9926",
    "brkrNm": "김수정",
    "ldCode": "11680",
    "ldCodeNm": "서울특별시 강남구",
    "registDe": "2010-01-28",
    "sttusSeCodeNm": "영업중",
    "rdnmadrcode": "11680312200600043100000",
    "mnnmadr": "서울특별시 강남구 역삼동 708-26",
    "rdnmadr": "서울특별시 강남구 선릉로 431",
    "estbsBeginDe": "2026-02-01",
    "lastUpdtDt": "2026-09-07",
    "estbsEndDe": "2027-01-31",
    "sttusSeCode": "1",
    "bsnmCmpnm": "녹색커피공인중개사사무소",
}


def _page(items: list[dict], total: int) -> dict:
    return {
        "EDOffices": {
            "field": items,
            "pageNo": "1",
            "resultCode": "",
            "totalCount": str(total),
            "numOfRows": str(len(items)),
            "resultMsg": "",
        }
    }


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


def _gateway_with_pages(monkeypatch, pages: list[dict]) -> tuple[MolitBrokerGateway, list[dict]]:
    calls: list[dict] = []

    def fake_get(client, url, params):
        calls.append(params)
        return _FakeResponse(pages[len(calls) - 1])

    monkeypatch.setattr(MolitBrokerGateway, "_get_with_retry", staticmethod(fake_get))
    return MolitBrokerGateway(), calls


def test_parse_date_normal_clamp_garbage():
    assert _parse_date("2010-01-28") == date(2010, 1, 28)
    assert _parse_date("2006-02-29") == date(2006, 2, 28)  # MOIS 원천 불량 날짜 전례 방어
    assert _parse_date("") is None
    assert _parse_date(None) is None
    assert _parse_date("날짜아님") is None


def test_source_updated_at_falls_back_to_today():
    assert _to_source_updated_at("2026-09-07") == datetime(2026, 9, 7)
    today = date.today()
    assert _to_source_updated_at("") == datetime(today.year, today.month, today.day)


def test_to_store_maps_fields(monkeypatch):
    gateway, _ = _gateway_with_pages(monkeypatch, [_page([_ITEM], total=1)])
    (store,) = list(gateway.iter_offices("real_estate", "11680"))

    assert store.store_id == "real_estate:11680:9250-9926"
    assert store.name == "녹색커피공인중개사사무소"
    assert store.industry_id == "real_estate"
    assert store.district_code == "11680"
    assert store.open_date == date(2010, 1, 28)
    assert store.close_date is None  # 원천에 폐업일 없음 — 스냅샷 소실 추정은 인터랙터 책임
    assert (store.status_code, store.status_name) == ("open", "영업중")
    assert (store.lat, store.lng) == (None, None)  # 원천에 좌표 없음 — SGIS 지오코딩 후속
    assert store.source_updated_at == datetime(2026, 9, 7)


def test_status_dict_dispatch_preserves_unknown_code(monkeypatch):
    suspended = {**_ITEM, "sttusSeCode": "2", "sttusSeCodeNm": "휴업"}
    unknown = {**_ITEM, "jurirno": "9250-0001", "sttusSeCode": "4", "sttusSeCodeNm": "업무정지"}
    gateway, _ = _gateway_with_pages(monkeypatch, [_page([suspended, unknown], total=2)])

    first, second = list(gateway.iter_offices("real_estate", "11680"))
    assert (first.status_code, first.status_name) == ("suspended", "휴업")
    assert (second.status_code, second.status_name) == ("4", "업무정지")  # 미지 코드 원문 보존


def test_paging_iterates_until_total(monkeypatch):
    page1 = _page([{**_ITEM, "jurirno": f"9250-{n:04d}"} for n in range(3)], total=5)
    page2 = _page([{**_ITEM, "jurirno": f"9250-{n:04d}"} for n in range(3, 5)], total=5)
    gateway, calls = _gateway_with_pages(monkeypatch, [page1, page2])
    # 페이지 크기를 픽스처에 맞춤 (실전 1,000은 실호출 검증값)
    monkeypatch.setattr(
        "apps.store.adapter.outbound.gateways.molit_broker_gateway._PAGE_SIZE", 3
    )

    stores = list(gateway.iter_offices("real_estate", "11680"))
    assert len(stores) == 5
    assert [c["pageNo"] for c in calls] == [1, 2]
    assert calls[0]["ldCode"] == "11680"
    assert gateway.call_count == 2


def test_error_payload_raises(monkeypatch):
    gateway, _ = _gateway_with_pages(
        monkeypatch, [{"response": {"resultCode": "INVALID_KEY", "resultMsg": "인증 실패"}}]
    )
    with pytest.raises(RuntimeError, match="molit broker API"):
        list(gateway.iter_offices("real_estate", "11680"))


def test_result_code_in_body_raises(monkeypatch):
    gateway, _ = _gateway_with_pages(
        monkeypatch,
        [{"EDOffices": {"resultCode": "INVALID_TYPE", "resultMsg": "ldCode 오류"}}],
    )
    with pytest.raises(RuntimeError, match="molit broker API"):
        list(gateway.iter_offices("real_estate", "11680"))
