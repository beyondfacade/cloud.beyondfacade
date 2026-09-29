"""아파트 매매 건수 수집 — 응답 파싱·월 범위·멱등 업서트 (업종 특화 신호 설계서 §11)."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from apps.housing.adapter.inbound.cli.load_apt_trade_counts import month_range, upsert_counts
from apps.housing.adapter.outbound.gateways.molit_apt_trade_gateway import MolitApiError, count_by_legal_dong
from apps.housing.adapter.outbound.orms.apt_trade_count_orm import AptTradeCountOrm
from apps.housing.domain.entities.apt_trade_count_entity import AptTradeCount
from core.matrix.grid_oracle_database_manager import session_scope

_OK = """<?xml version="1.0" encoding="UTF-8"?><response><header><resultCode>000</resultCode><resultMsg>OK</resultMsg></header>
<body><items><item><umdNm>역삼동</umdNm></item><item><umdNm> 역삼동 </umdNm></item><item><umdNm>대치동</umdNm></item></items>
<numOfRows>1000</numOfRows><pageNo>1</pageNo><totalCount>3</totalCount></body></response>"""

_BAD = """<OpenAPI_ServiceResponse><cmmMsgHeader><errMsg>SERVICE ERROR</errMsg>
<returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg><returnReasonCode>30</returnReasonCode></cmmMsgHeader></OpenAPI_ServiceResponse>"""


def test_응답을_법정동별_건수로_센다():
    counts, total = count_by_legal_dong(_OK)
    assert counts == {"역삼동": 2, "대치동": 1} and total == 3


def test_정상_코드가_아니면_예외다():
    with pytest.raises(MolitApiError):
        count_by_legal_dong(_BAD)


def test_월_범위는_양끝을_포함한다():
    assert month_range("202111", "202202") == ["202111", "202112", "202201", "202202"]


def test_업서트는_멱등이다():
    rows = [AptTradeCount("11680", "시험동", "209901", 5), AptTradeCount("11680", "시험동2", "209901", 1)]
    try:
        assert upsert_counts(rows, datetime(2099, 1, 1, tzinfo=timezone.utc)) == 2
        assert upsert_counts([AptTradeCount("11680", "시험동", "209901", 7)], datetime(2099, 1, 2, tzinfo=timezone.utc)) == 1
        with session_scope() as session:
            got = dict(session.execute(
                select(AptTradeCountOrm.legal_dong, AptTradeCountOrm.trade_count).where(AptTradeCountOrm.deal_ym == "209901")
            ).all())
        assert got == {"시험동": 7, "시험동2": 1}
    finally:
        with session_scope() as session:
            session.execute(delete(AptTradeCountOrm).where(AptTradeCountOrm.deal_ym == "209901"))
