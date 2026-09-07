"""tobacco_retailer 적재 검증 — CSV 파싱(순수) + 실제 DB 멱등 업서트 (rent 전례)."""

import pytest
from sqlalchemy import delete, select, update

from apps.tobacco.adapter.inbound.cli.load_tobacco_retailer import (
    parse_retailer,
    upsert_retailers,
)
from apps.tobacco.adapter.outbound.orms.tobacco_retailer_orm import TobaccoRetailerOrm
from apps.tobacco.domain.entities.tobacco_retailer_entity import TobaccoRetailer
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope

_DISTRICTS = {"3000000": "11110"}  # 종로구 (개방자치단체코드 → district_code)
_TEST_ID = "TEST-TOBACCO-0001"  # 실데이터 관리번호(숫자 19자리)와 충돌하지 않는 시험용 키


def _row(**overrides: str) -> dict[str, str]:
    """실CSV(기타_담배소매업_서울특별시.csv, 2026-08-25) 1행 실측 사본."""
    row = {
        "개방자치단체코드": "3000000",
        "관리번호": "2006300010105600013",
        "인허가일자": "2006-08-11",
        "인허가취소일자": "2011-11-10",
        "영업상태명": "취소/말소/만료/정지/중지",
        "폐업일자": "",
        "사업장명": "홍익마트",
        "도로명주소": "서울특별시 종로구 통일로 254 (무악동)",
        "상세영업상태명": "지정취소",
        "상세영업상태코드": "5",
        "영업상태코드": "04",
        "좌표정보(X)": "196193.491497926    ",
        "좌표정보(Y)": "452516.646583755    ",
        "지번주소": "서울특별시 종로구 무악동 37번지 1호",
        "지정일자": "2006-08-11",
        "데이터갱신시점": "2025-12-15 16:15:28",
    }
    row.update(overrides)
    return row


def test_parse_retailer_maps_real_row():
    retailer = parse_retailer(_row(), _DISTRICTS)
    assert isinstance(retailer, TobaccoRetailer)
    assert retailer.retailer_id == "2006300010105600013"
    assert retailer.name == "홍익마트"
    assert retailer.district_code == "11110"
    assert retailer.status_code == "5"
    assert retailer.status_name == "지정취소"
    assert retailer.close_date is None
    assert retailer.road_address == "서울특별시 종로구 통일로 254 (무악동)"
    assert retailer.jibun_address == "서울특별시 종로구 무악동 37번지 1호"
    assert str(retailer.designated_date) == "2006-08-11"
    assert str(retailer.permit_date) == "2006-08-11"
    assert str(retailer.cancel_date) == "2011-11-10"
    assert str(retailer.source_updated_at) == "2025-12-15 16:15:28"
    # EPSG:5174 → WGS84 (무악동 실좌표 — 브이월드 교차검증 전례와 동일 변환)
    assert retailer.lat == pytest.approx(37.5749346, abs=1e-6)
    assert retailer.lng == pytest.approx(126.9576974, abs=1e-6)


def test_parse_retailer_drops_out_of_seoul_coords():
    # 실CSV에 실존하는 이상 좌표(Y=171131 → 위도 35.0, 서울 밖) — 좌표만 버리고 행은 유지
    retailer = parse_retailer(
        _row(**{"좌표정보(X)": "153874.180653307", "좌표정보(Y)": "171131.881015428"}),
        _DISTRICTS,
    )
    assert retailer is not None
    assert retailer.lat is None and retailer.lng is None


def test_parse_retailer_blank_coords_and_dates():
    retailer = parse_retailer(
        _row(**{"좌표정보(X)": "", "좌표정보(Y)": "", "지정일자": "", "인허가취소일자": ""}),
        _DISTRICTS,
    )
    assert retailer.lat is None and retailer.lng is None
    assert retailer.designated_date is None and retailer.cancel_date is None


def test_parse_retailer_clamps_invalid_day():
    # 원천 실존 불량 날짜 유형(예: 2006-02-29) — store BC 전례와 동일하게 월말로 클램프
    retailer = parse_retailer(_row(**{"지정일자": "2006-02-29"}), _DISTRICTS)
    assert str(retailer.designated_date) == "2006-02-28"


def test_parse_retailer_unknown_authority_returns_none():
    assert parse_retailer(_row(**{"개방자치단체코드": "9999999"}), _DISTRICTS) is None


def _entity(status_code: str = "0", status_name: str = "정상영업") -> TobaccoRetailer:
    return parse_retailer(
        _row(
            **{
                "관리번호": _TEST_ID,
                "상세영업상태코드": status_code,
                "상세영업상태명": status_name,
            }
        ),
        _DISTRICTS,
    )


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(TobaccoRetailerOrm).where(TobaccoRetailerOrm.retailer_id == _TEST_ID)
        )


def test_upsert_is_idempotent_and_preserves_region_code():
    _cleanup()
    assert upsert_retailers([_entity()]) == 1
    # 공간조인 결과를 흉내(실존 region 코드) — 재적재가 region_code를 지우면 안 된다
    with session_scope() as session:
        region_code = session.execute(select(RegionOrm.region_code).limit(1)).scalar_one()
        session.execute(
            update(TobaccoRetailerOrm)
            .where(TobaccoRetailerOrm.retailer_id == _TEST_ID)
            .values(region_code=region_code)
        )
    assert upsert_retailers([_entity(status_code="2", status_name="폐업처리")]) == 1
    with session_scope() as session:
        row = session.execute(
            select(TobaccoRetailerOrm).where(TobaccoRetailerOrm.retailer_id == _TEST_ID)
        ).scalar_one()
        assert row.status_code == "2"  # 재적재 시 상태는 최신값으로 갱신
        assert row.status_name == "폐업처리"
        assert row.name == "홍익마트"
        assert row.region_code == region_code  # 공간조인 기입값 보존 (멱등 재적재)
    _cleanup()
