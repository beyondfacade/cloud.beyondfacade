"""region_facts_gateway — 해석 주의 생성(DB 없음) + facts 선수집이 쓰는 조회 3종(실 DB)."""

from dataclasses import dataclass

from sqlalchemy import delete, select

from apps.agent.adapter.outbound.gateways import region_facts_gateway
from apps.agent.adapter.outbound.gateways.region_facts_gateway import (
    RegionFactsGateway,
    _profile_caveats,
    _shock_event_to_dict,
    _type_median,
)
from apps.metric.adapter.outbound.orms.region_industry_metric_orm import (
    RegionIndustryMetricOrm,
)
from apps.metric.app.dtos.region_industry_hour_gap_dto import RegionIndustryHourGapDto
from apps.neighborhood.app.dtos.region_commerce_change_query_dto import (
    RegionCommerceChangeDto,
    SeoulBaselineDto,
)
from core.matrix.grid_oracle_database_manager import session_scope

_INDUSTRY = "korean_food"


class _FakeHourGapUseCase:
    """list_latest_bands만 흉내 내는 대역 — 게이트웨이가 쓰는 메서드는 그것뿐이다."""

    def __init__(self, bands: list) -> None:
        self._bands = bands

    def list_latest_bands(self, region_code: str, industry_id: str) -> list:
        return self._bands


class _FakeCommerceChangeUseCase:
    def __init__(self, dto) -> None:
        self._dto = dto

    def find_with_baseline(self, region_code: str, year_quarter: str | None):
        return self._dto


@dataclass
class FakeProfile:
    worker_resident_ratio: float | None = 1.2
    type_reason: str = "어느 축에서도 서울 상위·하위 경계를 넘지 않습니다."


def _texts(profile, facilities=()) -> str:
    return " ".join(_profile_caveats(profile, list(facilities)))


def test_직장인구_결측_동에만_0으로_읽지_말라는_주의가_붙는다():
    있음 = _texts(FakeProfile(worker_resident_ratio=None))
    없음 = _texts(FakeProfile(worker_resident_ratio=2.0))

    assert "0명으로 읽지" in 있음
    assert "0명으로 읽지" not in 없음


def test_재건축_판정_동에만_비율_불신_주의가_붙는다():
    있음 = _texts(
        FakeProfile(type_reason="상주인구가 비정상적으로 적어(재건축 등) 비율 판정을 적용하지 않았습니다.")
    )
    없음 = _texts(FakeProfile())

    assert "비율로 단정하지" in 있음
    assert "비율로 단정하지" not in 없음


def test_집객시설_1위가_버스정거장일_때만_그_주의가_붙는다():
    # 늘 붙는 문구는 읽히지 않는다 — 역삼1동처럼 약국·은행이 1위인 동에는 달지 않는다
    버스 = _texts(FakeProfile(), [{"type": "버스정거장", "count": 120}])
    약국 = _texts(FakeProfile(), [{"type": "약국", "count": 64}])

    assert "버스정거장" in 버스
    assert "버스정거장" not in 약국


def test_아파트_평균_시가_주의는_항상_붙는다():
    # 값 자체가 늘 이상치 위험을 갖는다 (원천 편차가 극단적)
    assert "참고값" in _texts(FakeProfile())


# --- 유형 중앙값 (설계서 map-stage §7 benchmarks) ---


@dataclass
class FakeRow:
    weekend_index: float | None
    night_index: float | None
    fnb_share: float | None
    worker_resident_ratio: float | None


def test_유형_중앙값은_필드마다_결측을_뺀_중앙값이다():
    rows = [
        FakeRow(0.8, 0.6, 0.10, 2.0),
        FakeRow(0.9, 0.7, 0.20, None),   # 직장인구 결측 동 — 그 필드만 빠진다
        FakeRow(1.0, 0.8, 0.30, 4.0),
    ]

    median = _type_median(rows)

    assert median == {
        "weekend_index": 0.9,
        "night_index": 0.7,
        "fnb_share": 0.2,
        "worker_resident_ratio": 3.0,
    }


def test_어느_필드가_전부_결측이면_그_필드만_None이다():
    rows = [FakeRow(0.8, 0.6, 0.1, None), FakeRow(1.0, 0.8, 0.3, None)]

    assert _type_median(rows)["worker_resident_ratio"] is None
    assert _type_median(rows)["night_index"] == 0.7


def test_빈_목록이면_None이다():
    assert _type_median([]) is None


def test_유형_중앙값이_있을_때만_비교_기준_주의가_붙는다():
    benchmarks = {"seoul": None, "type_median": {"night_index": 0.7}, "type_count": 36}

    있음 = " ".join(_profile_caveats(FakeProfile(), [], benchmarks))
    없음 = " ".join(_profile_caveats(FakeProfile(), [], {"seoul": None, "type_median": None, "type_count": 0}))

    assert "36개 동 중앙값" in 있음
    assert "중앙값" not in 없음


# --- facts 선수집이 쓰는 신규 조회 3종 (실 DB, beyondfacade_test) ---


def _first_region_code() -> str:
    from apps.master.adapter.outbound.orms.region_orm import RegionOrm
    from core.matrix.grid_oracle_database_manager import session_scope

    with session_scope() as session:
        return session.execute(
            select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)
        ).scalar_one()


def test_연도별_지표를_연도_순서대로_돌려준다():
    """추세선은 연도 순서가 곧 x축이다 — 정렬이 깨지면 꺾은선이 뒤엉킨다."""
    region_code = _first_region_code()
    with session_scope() as session:
        session.execute(
            delete(RegionIndustryMetricOrm).where(
                RegionIndustryMetricOrm.region_code == region_code,
                RegionIndustryMetricOrm.industry_id == _INDUSTRY,
            )
        )
        for year, store_count in ((2025, 120), (2023, 100), (2024, 110)):
            session.add(
                RegionIndustryMetricOrm(
                    region_code=region_code,
                    industry_id=_INDUSTRY,
                    year=year,
                    store_count=store_count,
                    open_count=5,
                    close_count=3,
                    closure_rate=0.03,
                    growth_rate=0.02,
                )
            )
    try:
        rows = RegionFactsGateway().metrics_history(region_code, _INDUSTRY)

        assert [row["year"] for row in rows] == [2023, 2024, 2025]
        assert rows[0] == {
            "year": 2023,
            "store_count": 100,
            "open_count": 5,
            "close_count": 3,
            "closure_rate": 0.03,
            "growth_rate": 0.02,
        }
    finally:
        with session_scope() as session:
            session.execute(
                delete(RegionIndustryMetricOrm).where(
                    RegionIndustryMetricOrm.region_code == region_code,
                    RegionIndustryMetricOrm.industry_id == _INDUSTRY,
                )
            )


def test_지표가_없는_동_업종은_빈_목록이다():
    assert RegionFactsGateway().metrics_history(_first_region_code(), "nonexistent") == []


def test_요약은_업종명을_함께_싣는다():
    """facts.region의 업종명이 뉴스 검색 질의와 시각 자료 제목에 쓰인다."""
    summary = RegionFactsGateway().summary(_first_region_code(), _INDUSTRY)

    assert summary["industry_name"] == "한식"
    assert summary["name"]


def test_모르는_업종이면_업종명은_None이다():
    assert RegionFactsGateway().summary(_first_region_code(), "nonexistent")["industry_name"] is None


def test_시간대_어긋남은_최신_분기_6구간을_시간_순으로_돌려준다(monkeypatch):
    bands = [
        RegionIndustryHourGapDto(
            region_code="1168064000",
            industry_id=_INDUSTRY,
            year_quarter="20252",
            hour_band=band,
            footfall_intensity=1.0,
            sales_intensity=1.2,
            gap=0.2,
        )
        for band in ("00_06", "06_11")
    ]
    monkeypatch.setattr(
        region_facts_gateway,
        "get_region_industry_hour_gap_use_case",
        lambda: _FakeHourGapUseCase(bands),
    )

    result = RegionFactsGateway().hour_gap("1168064000", _INDUSTRY)

    assert result["available"] is True
    assert result["year_quarter"] == "20252"
    assert [band["hour_band"] for band in result["bands"]] == ["00_06", "06_11"]
    assert result["bands"][0]["gap"] == 0.2


def test_시간대_어긋남_자료가_없으면_이유와_함께_비운다(monkeypatch):
    monkeypatch.setattr(
        region_facts_gateway,
        "get_region_industry_hour_gap_use_case",
        lambda: _FakeHourGapUseCase([]),
    )

    result = RegionFactsGateway().hour_gap("1168064000", _INDUSTRY)

    assert result["available"] is False
    assert result["reason"]


def test_상권_변화는_서울_평균을_함께_돌려준다(monkeypatch):
    dto = RegionCommerceChangeDto(
        region_code="1168064000",
        year_quarter="20252",
        change_code="LL",
        change_name="다이나믹",
        operating_months=110.0,
        closed_months=50.0,
        seoul=SeoulBaselineDto(operating_months=118.0, closed_months=54.0),
    )
    monkeypatch.setattr(
        region_facts_gateway,
        "get_region_commerce_change_query_use_case",
        lambda: _FakeCommerceChangeUseCase(dto),
    )

    result = RegionFactsGateway().commerce_change_detail("1168064000")

    assert result["available"] is True
    assert result["change_name"] == "다이나믹"
    assert result["seoul"] == {"operating_months": 118.0, "closed_months": 54.0}


def test_상권_변화_자료가_없으면_이유와_함께_비운다(monkeypatch):
    monkeypatch.setattr(
        region_facts_gateway,
        "get_region_commerce_change_query_use_case",
        lambda: _FakeCommerceChangeUseCase(None),
    )

    result = RegionFactsGateway().commerce_change_detail("1168064000")

    assert result["available"] is False
    assert result["reason"]


# --- facts가 프론트 계약(RegionProfile·ReportShock)으로 나가는지 (리뷰 라운드 2) ---

# 프론트 `RegionProfile`이 읽는 키 (frontend/src/shared/api/types.ts) — 하나라도 빠지면 그림이 빈다
_PROFILE_KEYS = frozenset(
    {
        "region_code",
        "year_quarter",
        "neighborhood_type",
        "time_label",
        "peak_block",
        "trough_block",
        "type_reason",
        "worker_resident_ratio",
        "weekend_index",
        "night_index",
        "footfall_20s_share",
        "fnb_share",
        "facility_total",
        "resident_total",
        "block_intensities",
    }
)


def test_동네_프로필은_프론트_계약_키를_모두_싣는다():
    """유형·시간대는 **코드**로 나간다 — 한국어 문구는 화면이 갖는다(프롬프트용 이름은 별도 키)."""
    from apps.metric.adapter.outbound.orms.region_profile_quarter_orm import (
        RegionProfileQuarterOrm,
    )

    region_code = _first_region_code()
    quarter = "20991"  # 최신 분기로 뽑히도록 실제 분기보다 뒤에 둔다
    with session_scope() as session:
        session.add(
            RegionProfileQuarterOrm(
                region_code=region_code,
                year_quarter=quarter,
                neighborhood_type="office",
                type_reason="시험",
                time_label="day",
                peak_block="day",
                trough_block="night",
                footfall_20s_share=0.21,
                block_morning=0.8,
                block_day=1.4,
                block_evening=1.1,
                block_night=0.4,
            )
        )
    try:
        profile = RegionFactsGateway().neighborhood_profile(region_code)
    finally:
        with session_scope() as session:
            session.execute(
                delete(RegionProfileQuarterOrm).where(
                    RegionProfileQuarterOrm.region_code == region_code,
                    RegionProfileQuarterOrm.year_quarter == quarter,
                )
            )

    assert _PROFILE_KEYS <= set(profile)
    assert profile["neighborhood_type"] == "office"  # 코드 그대로 — 화면이 문구를 붙인다
    assert (profile["peak_block"], profile["trough_block"]) == ("day", "night")
    assert profile["block_intensities"] == {
        "morning": 0.8,
        "day": 1.4,
        "evening": 1.1,
        "night": 0.4,
    }
    assert profile["type_name"] == "낮 인구 우위형"  # 프롬프트가 읽는 한국어 이름은 별도 키로 남는다
    assert {"time_label_name", "peak_block_name", "trough_block_name"} <= set(profile)
    assert {"benchmarks", "caveats"} <= set(profile)  # LLM 해석 재료는 그대로 남는다


def test_프로필_행이_없는_동은_이유와_함께_비운다():
    """빈 dict를 주면 프론트가 `available` 분기를 못 탄다 — 그림 자리에 '자료 없음'이 떠야 한다."""
    profile = RegionFactsGateway().neighborhood_profile("0000000000")

    assert profile["available"] is False
    assert profile["reason"]


def test_인구_행이_없는_동도_이유와_함께_비운다():
    """0으로 채운 dict는 '인구 0명'이라는 거짓말이다."""
    population = RegionFactsGateway().population("0000000000")

    assert population["available"] is False
    assert population["reason"]


def test_충격_사건은_프론트_계약_키를_싣는다():
    """`ReportShock`이 event_id·name·기간을 읽는다."""
    from datetime import date

    from apps.shock.app.dtos.shock_event_dto import IndustryImpactDto, ShockEventDto

    event = _shock_event_to_dict(
        ShockEventDto(
            event_id="E1",
            layer="policy",
            name="재난지원금",
            start_date=date(2020, 5, 13),
            scope="national",
            source="정부",
            industry_impacts=[IndustryImpactDto(industry_id="korean_food", severity="high")],
        )
    )

    assert {"event_id", "name", "start_date", "end_date", "layer", "scope", "source"} <= set(event)
    assert event["start_date"] == "2020-05-13"
    assert event["industry_impacts"] == [{"industry_id": "korean_food", "severity": "high"}]
