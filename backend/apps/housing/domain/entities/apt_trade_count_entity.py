from dataclasses import dataclass


@dataclass(frozen=True)
class AptTradeCount:
    """아파트 매매 신고 건수 — 자치구×법정동×월 (국토부 RTMSDataSvcAptTrade, 업종 특화 신호 설계서 §11).
    법정동은 원천 umdNm 원문. 행정동 배분은 verdict BC가 한다(store 지번주소 분포, 근사)."""

    district_code: str  # 시군구 5자리 = LAWD_CD
    legal_dong: str  # 법정동명 (umdNm)
    deal_ym: str  # "YYYYMM"
    trade_count: int
