"""ChildcarePortalGateway XML 파싱 단위 검증 — 픽스처 기반 (실호출 없음)."""

from datetime import date

import pytest

from apps.childcare.adapter.outbound.gateways.childcare_portal_gateway import (
    ChildcarePortalGateway,
)

_DISTRICT_CODE = "11110"  # 종로구 — arcode = district_code (5자리)

# 2026-09-17 운영키 실응답(종로구 58건) 1건 축약 사본 — 수집 대상 외 필드는 일부만 남김
_ITEM = """<item><sidoname>서울특별시</sidoname><sigunname>종로구</sigunname>
<stcode>11110000029</stcode><crname>가회어린이집</crname><crtypename>국공립</crtypename>
<crstatusname>정상</crstatusname><zipcode>03056</zipcode>
<craddr>서울특별시 종로구 북촌로12길 12-2 가회어린이집 (가회동)</craddr>
<crtelno>02-3673-2085</crtelno><chcrtescnt>10</chcrtescnt><crcapat>39</crcapat>
<crchcnt>25</crchcnt><la>37.58180502</la><lo>126.9858807</lo><crcnfmdt>1995-06-23</crcnfmdt>
<crpausebegindt></crpausebegindt><crpauseenddt></crpauseenddt><crabldt></crabldt>
<datastdrdt>2026-09-17</datastdrdt><crspec>야간연장형</crspec>
<CLASS_CNT_TOT>7</CLASS_CNT_TOT><CHILD_CNT_TOT>25</CHILD_CNT_TOT><EW_CNT_TOT>20</EW_CNT_TOT></item>"""


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


def _gateway_with_body(monkeypatch, body: str) -> tuple[ChildcarePortalGateway, list[dict]]:
    calls: list[dict] = []

    def fake_get(client, url, params):
        calls.append(params)
        return _FakeResponse(body)

    monkeypatch.setattr(ChildcarePortalGateway, "_get_with_retry", staticmethod(fake_get))
    monkeypatch.setenv("CHILDCARE_API_KEY", "test-key")
    return ChildcarePortalGateway(), calls


def test_to_entity_maps_real_fields(monkeypatch):
    gateway, calls = _gateway_with_body(monkeypatch, f"<response>{_ITEM}</response>")
    (center,) = gateway.fetch_centers(_DISTRICT_CODE)

    assert center.center_id == "11110000029"
    assert center.name == "가회어린이집"
    assert center.type_name == "국공립"
    assert center.status_name == "정상"
    assert center.district_code == _DISTRICT_CODE
    assert center.address == "서울특별시 종로구 북촌로12길 12-2 가회어린이집 (가회동)"
    assert center.zipcode == "03056"
    assert center.tel == "02-3673-2085"
    assert center.lat == pytest.approx(37.58180502)
    assert center.lng == pytest.approx(126.9858807)
    assert center.approved_on == date(1995, 6, 23)
    assert (center.paused_from, center.paused_until, center.abolished_on) == (None, None, None)

    stat = center.stat
    assert stat.base_date == date(2026, 9, 17)
    assert (stat.capacity, stat.child_count, stat.waiting_count) == (39, 25, 20)
    assert (stat.class_count, stat.staff_count) == (7, 10)

    assert calls[0]["arcode"] == _DISTRICT_CODE
    assert gateway.call_count == 1


def test_blank_waiting_and_coords_preserved_as_none(monkeypatch):
    # 실응답에서 EW_CNT_TOT 공란이 흔하다(종로 26/58·강남 40/162, "0"은 한 번도 없음) — 0으로 추정하지 않는다
    item = (
        _ITEM.replace("<EW_CNT_TOT>20</EW_CNT_TOT>", "<EW_CNT_TOT></EW_CNT_TOT>")
        .replace("<la>37.58180502</la>", "<la></la>")
        .replace("<lo>126.9858807</lo>", "<lo></lo>")
    )
    gateway, _ = _gateway_with_body(monkeypatch, f"<response>{item}</response>")
    (center,) = gateway.fetch_centers(_DISTRICT_CODE)
    assert center.stat.waiting_count is None
    assert center.lat is None and center.lng is None


def test_blank_status_preserved_as_none(monkeypatch):
    # 2026-09-17 전량 수집에서 상태 공란 3건 실측(동작·구로·마포, 모두 현원 0) — 원천 그대로 None
    item = _ITEM.replace("<crstatusname>정상</crstatusname>", "<crstatusname></crstatusname>")
    gateway, _ = _gateway_with_body(monkeypatch, f"<response>{item}</response>")
    (center,) = gateway.fetch_centers(_DISTRICT_CODE)
    assert center.status_name is None


def test_error_body_raises(monkeypatch):
    # 인증 실패도 HTTP 200 + errcode 본문으로 온다 (2026-09-17 실확인)
    body = "<response><errmsg>인증키가 유효하지 않습니다.</errmsg><errcode>INFO-100</errcode></response>"
    gateway, _ = _gateway_with_body(monkeypatch, body)
    with pytest.raises(RuntimeError, match="INFO-100"):
        gateway.fetch_centers(_DISTRICT_CODE)

