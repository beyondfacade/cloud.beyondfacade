"""R-ONE 게이트웨이 파싱 검증 — SttsApiTblData 실응답(2026-09-07 표본) 픽스처, 네트워크 미사용."""

import pytest

from apps.rent.adapter.outbound.gateways.rone_gateway import (
    RoneTable,
    parse_page,
    to_observations,
)

_TABLE = RoneTable(
    metric="rent",
    building_type="medium_large",
    statbl_id="A_2024_00278",
    vintage="2022년~",
)

# 실응답 표본 축약 — 파싱에 쓰는 필드는 실제 키·형식 그대로 (임대료 2022년~ 중대형 상가)
_RESPONSE = {
    "SttsApiTblData": [
        {
            "head": [
                {"list_total_count": 2700},
                {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
            ]
        },
        {
            "row": [
                {
                    "STATBL_ID": "A_2024_00278",
                    "DTACYCLE_CD": "QY",
                    "WRTTIME_IDTFR_ID": "202201",
                    "CLS_ID": 520036,
                    "CLS_NM": "가락시장",
                    "ITM_NM": "임대료",
                    "DTA_VAL": 38.9998660091614,
                    "UI_NM": "천원/㎡",
                    "CLS_FULLNM": "서울>기타>가락시장",
                    "WRTTIME_DESC": "2022년 1분기",
                },
                {
                    "STATBL_ID": "A_2024_00278",
                    "DTACYCLE_CD": "QY",
                    "WRTTIME_IDTFR_ID": "202201",
                    "CLS_ID": 510003,
                    "CLS_NM": "도심",
                    "ITM_NM": "임대료",
                    "DTA_VAL": 99.9326232717226,
                    "UI_NM": "천원/㎡",
                    "CLS_FULLNM": "서울>도심",
                    "WRTTIME_DESC": "2022년 1분기",
                },
                {
                    "STATBL_ID": "A_2024_00278",
                    "DTACYCLE_CD": "QY",
                    "WRTTIME_IDTFR_ID": "202201",
                    "CLS_ID": 500001,
                    "CLS_NM": "전국",
                    "ITM_NM": "임대료",
                    "DTA_VAL": 25.5185076374493,
                    "UI_NM": "천원/㎡",
                    "CLS_FULLNM": "전국",
                    "WRTTIME_DESC": "2022년 1분기",
                },
                {
                    "STATBL_ID": "A_2024_00278",
                    "DTACYCLE_CD": "QY",
                    "WRTTIME_IDTFR_ID": "202201",
                    "CLS_ID": 520113,
                    "CLS_NM": "금남로/충장로",
                    "ITM_NM": "임대료",
                    "DTA_VAL": 30.3933624369483,
                    "UI_NM": "천원/㎡",
                    "CLS_FULLNM": "광주>금남로/충장로",
                    "WRTTIME_DESC": "2022년 1분기",
                },
            ]
        },
    ]
}


def test_parse_page_returns_total_and_rows():
    total, rows = parse_page(_RESPONSE)
    assert total == 2700
    assert len(rows) == 4


def test_parse_page_raises_on_error_result():
    # R-ONE도 오류를 200 + RESULT 바디로 반환한다 (ECOS 전례와 동일 방어)
    error = {"RESULT": {"CODE": "INFO-100", "MESSAGE": "인증키가 유효하지 않습니다."}}
    with pytest.raises(RuntimeError, match="INFO-100"):
        parse_page(error)


def test_to_observations_keeps_seoul_only_and_maps_fields():
    _, rows = parse_page(_RESPONSE)
    observations = to_observations(rows, _TABLE)
    # 전국·광주 행은 제외 — 서울 시도·권역·상권만
    assert len(observations) == 2
    first = observations[0]
    assert first.id == "medium_large:520036:2022Q1"  # 결정적 ID — 재적재 멱등
    assert first.building_type == "medium_large"
    assert first.cls_id == "520036"
    assert first.region_name == "가락시장"
    assert first.region_path == "서울>기타>가락시장"
    assert first.region_level == 3  # 시도>권역>상권
    assert first.period == "2022Q1"  # WRTTIME_IDTFR_ID 202201 → 분기 표기
    assert first.metric == "rent"
    assert first.value == pytest.approx(38.9998660091614)
    assert first.unit == "천원/㎡"
    assert first.statbl_id == "A_2024_00278"
    assert observations[1].region_level == 2  # "서울>도심" 권역


def test_to_observations_skips_missing_values():
    rows = [
        {
            "WRTTIME_IDTFR_ID": "202201",
            "CLS_ID": 520036,
            "CLS_NM": "가락시장",
            "DTA_VAL": None,
            "UI_NM": "천원/㎡",
            "CLS_FULLNM": "서울>기타>가락시장",
        }
    ]
    assert to_observations(rows, _TABLE) == []
