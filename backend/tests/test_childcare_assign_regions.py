"""어린이집 공간조인 — 등록 자치구와 어긋난 판정 배제 검증 (순수 함수)."""

from apps.childcare.adapter.inbound.cli.childcare_collector import region_updates


def test_region_updates_reject_code_outside_registered_district():
    # 2026-09-17 실측: 동작구 등록 시설 좌표가 시청 인근(중구)을 가리킴 — 교차 구 판정은 기입하지 않는다
    centers = [("A", "11110"), ("B", "11590"), ("C", "11110")]  # (center_id, district_code)
    codes = ["1111051500", "1114055000", None]
    assert region_updates(centers, codes) == [{"center_id": "A", "region_code": "1111051500"}]
