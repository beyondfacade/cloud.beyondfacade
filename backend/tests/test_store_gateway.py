"""MoisPermitGateway 파싱 단위 검증 — 원천 불량 데이터 방어."""

from datetime import date, datetime

from apps.store.adapter.outbound.gateways.mois_permit_gateway import (
    _parse_date,
    _parse_datetime,
    _to_wgs84,
)


def test_parse_date_normal_and_empty():
    assert _parse_date("2026-08-25") == date(2026, 8, 25)
    assert _parse_date("") is None
    assert _parse_date(None) is None


def test_parse_date_clamps_invalid_day():
    # 원천 실데이터에 존재 (2026-08-25 초기적재 크래시 원인): 2006-02-29
    assert _parse_date("2006-02-29") == date(2006, 2, 28)
    assert _parse_date("2021-04-31") == date(2021, 4, 30)


def test_parse_date_garbage_returns_none():
    assert _parse_date("0000-00-00") is None
    assert _parse_date("날짜아님") is None


def test_parse_datetime_clamps_invalid_day():
    assert _parse_datetime("2026-08-25 12:00:00") == datetime(2026, 8, 25, 12, 0)
    assert _parse_datetime("2006-02-29 10:30:00") == datetime(2006, 2, 28, 10, 30)


def test_to_wgs84_rejects_out_of_range():
    assert _to_wgs84(None, None) == (None, None)
    lat, lng = _to_wgs84("204514.126", "444551.989")  # 강남 실좌표
    assert 37.4 < lat < 37.6 and 126.9 < lng < 127.2
