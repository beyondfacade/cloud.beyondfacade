"""ECOS 게이트웨이 파싱 검증 — StatisticSearch 실응답(2026-09-07 표본) 픽스처, 네트워크 미사용."""

import pytest

from apps.shock.adapter.outbound.gateways.ecos_gateway import parse_rates

# 실응답 표본 축약 — 파싱에 쓰는 필드는 실제 키·형식 그대로
_RESPONSE = {
    "StatisticSearch": {
        "list_total_count": 2,
        "row": [
            {
                "STAT_CODE": "722Y001",
                "STAT_NAME": "1.3.1. 한국은행 기준금리 및 여수신금리",
                "ITEM_CODE1": "0101000",
                "ITEM_NAME1": "한국은행 기준금리",
                "UNIT_NAME": "연%",
                "TIME": "201901",
                "DATA_VALUE": "1.75",
            },
            {
                "STAT_CODE": "722Y001",
                "STAT_NAME": "1.3.1. 한국은행 기준금리 및 여수신금리",
                "ITEM_CODE1": "0101000",
                "ITEM_NAME1": "한국은행 기준금리",
                "UNIT_NAME": "연%",
                "TIME": "202608",
                "DATA_VALUE": "2.75",
            },
        ],
    }
}


def test_parse_rates_maps_real_response_fields():
    rates = parse_rates(_RESPONSE)
    assert len(rates) == 2
    first = rates[0]
    assert first.id == "base:201901"  # 결정적 ID — 재적재 멱등
    assert first.rate_type == "base"
    assert first.period == "201901"
    assert first.rate == 1.75
    assert first.unit == "연%"
    assert first.stat_code == "722Y001"
    assert first.item_code == "0101000"
    assert rates[1].rate == 2.75


def test_parse_rates_raises_on_ecos_error_body():
    # ECOS는 오류를 200 + RESULT 바디로 반환한다
    error = {"RESULT": {"CODE": "INFO-100", "MESSAGE": "인증키가 유효하지 않습니다."}}
    with pytest.raises(RuntimeError, match="INFO-100"):
        parse_rates(error)


def test_parse_rates_skips_non_numeric_values():
    broken = {
        "StatisticSearch": {
            "row": [
                {"TIME": "202001", "DATA_VALUE": "-", "STAT_CODE": "722Y001",
                 "ITEM_CODE1": "0101000", "UNIT_NAME": "연%"},
            ]
        }
    }
    assert parse_rates(broken) == []
