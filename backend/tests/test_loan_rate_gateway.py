"""ECOS 가중평균 대출금리(121Y006) 파싱 검증 — 실응답(2026-09-07 표본) 픽스처, 네트워크 미사용."""

from apps.shock.adapter.outbound.gateways.ecos_gateway import (
    LOAN_SERIES,
    EcosSeries,
    parse_rates,
)

_CORP_SERIES = EcosSeries("loan_corp", "121Y006", "BECBLA02")

# 실응답 표본 축약 — 파싱에 쓰는 필드는 실제 키·형식 그대로
_RESPONSE = {
    "StatisticSearch": {
        "list_total_count": 2,
        "row": [
            {
                "STAT_CODE": "121Y006",
                "STAT_NAME": "1.3.3.2.1. 예금은행 대출금리(신규취급액 기준)",
                "ITEM_CODE1": "BECBLA02",
                "ITEM_NAME1": "기업대출",
                "UNIT_NAME": "연리%",
                "TIME": "202201",
                "DATA_VALUE": "3.3",
            },
            {
                "STAT_CODE": "121Y006",
                "STAT_NAME": "1.3.3.2.1. 예금은행 대출금리(신규취급액 기준)",
                "ITEM_CODE1": "BECBLA02",
                "ITEM_NAME1": "기업대출",
                "UNIT_NAME": "연리%",
                "TIME": "202211",
                "DATA_VALUE": "5.67",
            },
        ],
    }
}


def test_parse_rates_maps_loan_series_with_id_convention():
    rates = parse_rates(_RESPONSE, _CORP_SERIES)
    assert len(rates) == 2
    first = rates[0]
    assert first.id == "loan_corp:202201"  # base:{YYYYMM} 관행과 일관된 프리픽스
    assert first.rate_type == "loan_corp"
    assert first.period == "202201"
    assert first.rate == 3.3
    assert first.unit == "연리%"
    assert first.stat_code == "121Y006"
    assert first.item_code == "BECBLA02"
    assert rates[1].rate == 5.67  # 2022 급등 사이클 표본


def test_loan_series_covers_corp_sme_facility():
    # 계산기 §8.1③ 대출금리 축 — 상가 매입 추정용 3계열 (신규취급액 기준)
    assert [(s.rate_type, s.item_code) for s in LOAN_SERIES] == [
        ("loan_corp", "BECBLA02"),
        ("loan_sme", "BECBLA0202"),
        ("loan_facility", "BECBLA0204"),
    ]
    assert all(series.stat_code == "121Y006" for series in LOAN_SERIES)
