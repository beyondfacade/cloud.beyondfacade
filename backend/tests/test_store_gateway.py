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


def test_to_entity_classifies_general_restaurant_by_business_type():
    """일반음식점은 건별 업종을 업태로 정하고 store_id 접두는 슬러그 기반이다."""
    from apps.store.adapter.outbound.gateways.mois_permit_gateway import MoisPermitGateway
    from apps.store.app.dtos.store_dto import IngestTarget

    target = IngestTarget(
        industry_id="restaurant_other", slug="general_restaurants", district_code="11680",
        authority_code="3220000", industry_ids=("korean_food", "restaurant_other"), store_prefix="restaurant",
    )
    item = {
        "MNG_NO": "3220000-101-2026-00981", "BPLC_NM": " 논현식당 ", "BZSTAT_SE_NM": "한식",
        "LCPMT_YMD": "2026-09-23", "CLSBIZ_YMD": "", "DTL_SALS_STTS_CD": "01", "DTL_SALS_STTS_NM": "영업",
        "CRD_INFO_X": "204514.126", "CRD_INFO_Y": "444551.989", "DAT_UPDT_PNT": "2026-09-24 22:17:51",
    }
    store = MoisPermitGateway()._to_entity(item, target)
    assert store.industry_id == "korean_food"
    assert store.store_id == "restaurant:3220000:3220000-101-2026-00981"
    assert store.name == "논현식당"

    item["BPLC_NM"] = "삼원가든(한시적)"
    assert MoisPermitGateway()._to_entity(item, target).industry_id == "restaurant_other"


def test_to_entity_keeps_fixed_industry_for_legacy_slugs():
    from apps.store.adapter.outbound.gateways.mois_permit_gateway import MoisPermitGateway
    from apps.store.app.dtos.store_dto import IngestTarget

    target = IngestTarget(industry_id="karaoke", slug="karaoke_rooms", district_code="11110", authority_code="3000000")
    item = {"MNG_NO": "X-1", "BPLC_NM": "행복노래방", "BZSTAT_SE_NM": "한식", "DAT_UPDT_PNT": "2026-09-24 00:00:00"}
    store = MoisPermitGateway()._to_entity(item, target)
    assert store.industry_id == "karaoke"
    assert store.store_id == "karaoke:3000000:X-1"
