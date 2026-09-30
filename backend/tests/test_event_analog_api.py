"""유사 사례 유스케이스·캐시 프록시·라우터·시드 유형·저장소 왕복 (흐름 원천은 Fake, 이벤트 저장은 실제 DB)."""

from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete

from apps.news.app.ports.output.news_article_port import NewsSearchGatewayPort
from apps.news.domain.entities.news_article_entity import NewsArticle
from apps.shock.adapter.outbound.gateways.caching_recent_news_gateway import (
    CachingRecentNewsGateway,
)
from apps.shock.adapter.outbound.gateways.caching_store_flow_gateway import (
    CachingStoreFlowGateway,
)
from apps.shock.adapter.outbound.gateways.recent_news_gateway import RecentNewsGateway
from apps.shock.adapter.outbound.gateways.shock_seed_gateway import ShockSeedGateway
from apps.shock.adapter.outbound.orms.shock_event_industry_orm import ShockEventIndustryOrm
from apps.shock.adapter.outbound.orms.shock_event_orm import ShockEventOrm
from apps.shock.adapter.outbound.repositories.shock_event_repository import (
    SqlAlchemyShockEventRepository,
)
from apps.shock.app.ports.output.event_analog_port import RecentNewsPort, StoreFlowPort
from apps.shock.app.ports.output.shock_event_port import ShockEventRepositoryPort
from apps.shock.app.use_cases.event_analog_interactor import EventAnalogInteractor
from apps.shock.app.use_cases.shock_event_interactor import ShockEventInteractor
from apps.shock.domain.entities.shock_event_entity import ShockEvent
from apps.shock.domain.services.industry_flows import IndustryFlows
from apps.shock.domain.value_objects.event_category import EventCategory
from apps.shock.domain.value_objects.news_headline import NewsHeadline
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

TODAY = date(2026, 9, 30)
_TEST_PREFIX = "test-analog-"


def _event(event_id: str, start: date, category: str | None, end: date | None = None) -> ShockEvent:
    return ShockEvent(
        event_id=event_id,
        layer="policy",
        name=f"{event_id} 이름",
        start_date=start,
        end_date=end,
        scope="전국",
        source="테스트 출처",
        category=category,
    )


def _flows(industry_id: str, name: str, opens: int, closes: int, closes_2020: int | None = None) -> IndustryFlows:
    openings = {date(2012, 12, 1): 1000}
    closings: dict[date, int] = {}
    for year in range(2013, 2027):
        for month in range(1, 13):
            openings[date(year, month, 1)] = opens
            closings[date(year, month, 1)] = closes_2020 if year == 2020 and closes_2020 else closes
    return IndustryFlows(industry_id, name, openings, closings)


class FakeEvents(ShockEventRepositoryPort):
    def __init__(self, events: list[ShockEvent]) -> None:
        self._events = events
        self.saved: list[ShockEvent] = []

    def upsert(self, events: list[ShockEvent]) -> tuple[int, int]:
        self.saved.extend(events)
        return len(events), 0

    def list_events(self, industry_id: str | None, limit: int) -> list[ShockEvent]:
        return self._events[:limit]

    def list_categorized(self) -> list[ShockEvent]:
        return [e for e in self._events if e.category is not None]


class FakeFlows(StoreFlowPort):
    def __init__(self) -> None:
        self.calls = 0

    def monthly_flows(self) -> list[IndustryFlows]:
        self.calls += 1
        return [_flows("cafe", "카페", 10, 8, closes_2020=30), _flows("pc_bang", "PC방", 3, 1)]


class FakeNews(RecentNewsPort):
    def __init__(self, by_keyword: dict[str, list[NewsHeadline]] | None = None, fail: bool = False) -> None:
        self._by_keyword = by_keyword or {}
        self._fail = fail
        self.queries: list[str] = []

    def latest(self, keyword: str) -> list[NewsHeadline]:
        self.queries.append(keyword)
        if self._fail:
            raise RuntimeError("뉴스 검색 실패")
        return self._by_keyword.get(keyword, [])


_EVENTS = [
    _event("covid", date(2020, 1, 20), "pandemic", date(2022, 4, 17)),
    _event("mers", date(2015, 5, 20), "pandemic", date(2015, 12, 23)),
    _event("w2025", date(2025, 1, 1), "minimum_wage", date(2025, 12, 31)),
    _event("w2026", date(2026, 1, 1), "minimum_wage", date(2026, 12, 31)),
    _event("distancing-phase", date(2020, 3, 22), None, date(2020, 5, 5)),
    _event("relief", date(2020, 5, 4), "relief", date(2020, 8, 31)),
]


def _interactor(events=_EVENTS, news: RecentNewsPort | None = None) -> EventAnalogInteractor:
    return EventAnalogInteractor(events=FakeEvents(events), flows=FakeFlows(), today=lambda: TODAY, news=news)


# ── 유스케이스 ──────────────────────────────────────────────────────────


def test_질문의_유형과_진행_중_이벤트_유형의_지난_사례를_함께_돌려준다():
    report = _interactor().analogs("cafe", "새 바이러스가 도는데 카페 창업 괜찮을까")
    assert [c.category for c in report.categories] == ["pandemic", "minimum_wage"]
    assert [c.reason for c in report.categories] == ["question", "current"]
    assert [e.event_id for e in report.current_events] == ["w2026"]
    assert [e.event_id for e in report.analogs] == ["covid", "mers", "w2025"]
    assert report.as_of == "2026-08"


def _covid():
    return next(e for e in _interactor().analogs("cafe", "코로나 같은 상황").analogs if e.event_id == "covid")


def test_사례마다_3년_12분기의_라벨과_기간을_담는다():
    covid = _covid()
    assert covid.category_label == "감염병·방역"
    assert covid.duration_months == 27
    assert len(covid.quarters) == 12
    first, fourth, last = covid.quarters[0], covid.quarters[3], covid.quarters[11]
    assert (first.quarter, first.label, first.start_month, first.end_month) == (1, "1년 차 1분기", "2020-01", "2020-03")
    assert (fourth.label, fourth.start_month, fourth.end_month) == ("1년 차 4분기", "2020-10", "2020-12")
    assert (last.label, last.start_month, last.end_month) == ("3년 차 4분기", "2022-10", "2022-12")


def test_분기에_시작한_다른_유형_이벤트를_함께_적는다():
    covid = _covid()
    assert covid.quarters[1].overlaps == ["relief 이름"]  # 2020-04~06에 지원금
    assert covid.quarters[0].overlaps == []  # 유형 없는 거리두기 국면은 적지 않는다


def test_내_업종과_추천_업종의_분기별_흐름과_약세_분기_수를_담는다():
    covid = _covid()
    assert [(s.industry_id, s.role) for s in covid.series] == [("cafe", "target"), ("pc_bang", "recommended")]
    cafe = covid.series[0]
    assert (cafe.industry_name, len(cafe.values)) == ("카페", 12)
    # 2020년 한 해 폐업 급증 → 1년 차 네 분기는 약세, 2·3년 차는 평소와 비슷
    assert all(v <= -0.3 for v in cafe.values[:4])
    assert (covid.target_weak_quarters, covid.target_strong_quarters) == (4, 0)
    assert covid.target_weak_streak == 4  # 1분기부터 연속 약세


def test_최저임금_사례는_그_해_4분기만_본다():
    w2025 = next(e for e in _interactor().analogs("cafe", None).analogs if e.event_id == "w2025")
    assert w2025.years == 1
    assert [(q.label, q.start_month, q.end_month) for q in w2025.quarters] == [
        ("1년 차 1분기", "2025-01", "2025-03"), ("1년 차 2분기", "2025-04", "2025-06"),
        ("1년 차 3분기", "2025-07", "2025-09"), ("1년 차 4분기", "2025-10", "2025-12"),
    ]
    assert all(len(s.values) == 4 for s in w2025.series)
    assert _covid().years == 3


def test_진행_중_이벤트는_끝난_분기까지만_본다():
    current = _interactor().analogs("cafe", None).current_events[0]
    assert [q.label for q in current.quarters] == ["1년 차 1분기", "1년 차 2분기"]


def test_유형마다_지난_사례의_결론을_싣는다():
    report = _interactor().analogs("cafe", "코로나")
    outlooks = {o.category: o for o in report.outlooks}
    assert list(outlooks) == ["pandemic", "minimum_wage"]
    pandemic = outlooks["pandemic"]
    assert (pandemic.label, pandemic.analog_count, pandemic.typical_duration_months) == ("감염병·방역", 2, 17)
    assert pandemic.target_trend in {"weak", "strong", "mixed", "unknown"}
    assert all(r.industry_id != "cafe" for r in pandemic.recommended)


def test_해석_주의사항을_함께_싣는다():
    caveats = " ".join(_interactor().analogs("cafe", "코로나").caveats)
    assert "12월" in caveats  # 연말 폐업 몰림
    assert "지원금" in caveats  # 2020~2022 폐업 지연
    assert "서울 전체" in caveats


def test_유형_단서도_진행_중_이벤트도_없으면_비어_있다():
    report = _interactor(events=_EVENTS[:2]).analogs("cafe", "역삼동 카페 어때")
    assert report.categories == []
    assert report.analogs == []
    assert report.current_events == []
    assert [h.category for h in report.hints] == ["pandemic", "minimum_wage", "work_hours", "relief"]


def test_비교하지_않은_유형은_질문에_넣을_예시_단어로_안내한다():
    report = _interactor().analogs("cafe", "새 바이러스가 도는데 카페 창업 괜찮을까")
    assert [(h.category, h.label, h.keyword) for h in report.hints] == [
        ("work_hours", "근로시간", "52시간"),
        ("relief", "지원금·보상", "지원금"),
    ]
    assert [h.category for h in _interactor().analogs("cafe", None).hints] == ["pandemic", "work_hours", "relief"]


def test_진행_중_이벤트가_없는_질문_속_유형은_최근_30일_조치_기사를_확인한다():
    news = FakeNews({"집합금지": [
        NewsHeadline("집합금지 명령 발동", datetime(2026, 9, 25, 10), "u1"),
        NewsHeadline("집합금지 해제", datetime(2026, 8, 1), "old"),
    ]})
    [recent] = _interactor(news=news).analogs("cafe", "코로나 같은 상황이면").recent_news
    assert (recent.category, recent.label, recent.days, recent.checked) == ("pandemic", "감염병·방역", 30, True)
    assert recent.keywords == ["집합금지", "영업제한", "거리두기 격상"]
    assert recent.article_count == 1
    assert [(h.title, h.published_at, h.url) for h in recent.headlines] == [("집합금지 명령 발동", "2026-09-25", "u1")]
    assert news.queries == ["집합금지", "영업제한", "거리두기 격상"]  # 진행 중인 최저임금은 찾지 않는다


def test_조치_기사가_없으면_없다고_싣고_검색이_실패하면_확인하지_못했다고_싣는다():
    quiet = _interactor(news=FakeNews()).analogs("cafe", "코로나").recent_news[0]
    assert quiet.checked is True
    assert (quiet.article_count, quiet.headlines) == (0, [])
    down = _interactor(news=FakeNews(fail=True)).analogs("cafe", "코로나").recent_news[0]
    assert down.checked is False


def test_질문_속_유형이_없으면_뉴스를_찾지_않는다():
    news = FakeNews()
    assert _interactor(news=news).analogs("cafe", None).recent_news == []
    assert news.queries == []


def test_흐름이_없는_업종은_대상_변동폭이_없다():
    report = _interactor().analogs("academy", "코로나")
    assert all(v is None for e in report.analogs for v in e.series[0].values)
    assert all(e.target_weak_quarters == 0 for e in report.analogs)


def test_이벤트를_유형과_함께_등록한다():
    events = FakeEvents([])
    interactor = ShockEventInteractor(repository=events)
    interactor.register(_event("new-virus", date(2026, 9, 1), "pandemic"))
    assert [e.category for e in events.saved] == ["pandemic"]


# ── 캐시 프록시 ─────────────────────────────────────────────────────────


def test_흐름은_유효_시간_안에는_다시_조회하지_않는다():
    inner = FakeFlows()
    clock = [datetime(2026, 9, 30, 9, 0)]
    proxy = CachingStoreFlowGateway(inner, ttl=timedelta(hours=6), now=lambda: clock[0])
    proxy.monthly_flows()
    clock[0] += timedelta(hours=5)
    proxy.monthly_flows()
    assert inner.calls == 1
    clock[0] += timedelta(hours=2)
    proxy.monthly_flows()
    assert inner.calls == 2


def test_조치_기사는_단어마다_유효_시간_안에는_다시_찾지_않는다():
    inner = FakeNews()
    clock = [datetime(2026, 9, 30, 9)]
    proxy = CachingRecentNewsGateway(inner, ttl=timedelta(hours=1), now=lambda: clock[0])
    proxy.latest("집합금지")
    proxy.latest("집합금지")
    proxy.latest("영업제한")
    assert inner.queries == ["집합금지", "영업제한"]
    clock[0] += timedelta(hours=2)
    proxy.latest("집합금지")
    assert inner.queries == ["집합금지", "영업제한", "집합금지"]


class FakeSearch(NewsSearchGatewayPort):
    def search(self, keyword: str) -> list[NewsArticle]:
        return [NewsArticle("a1", f"{keyword} 명령", "발췌", datetime(2026, 9, 25, 10), "https://news/1", keyword)]


def test_뉴스_검색_결과를_제목_날짜_링크만_남긴_헤드라인으로_옮긴다():
    assert RecentNewsGateway(FakeSearch()).latest("집합금지") == [
        NewsHeadline("집합금지 명령", datetime(2026, 9, 25, 10), "https://news/1")
    ]


# ── 라우터 ─────────────────────────────────────────────────────────────


def test_유사_사례_myself_배선():
    response = TestClient(app).get("/shocks/analogs/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["industry_id"] == "myself"
    assert body["analogs"][0]["quarters"][0]["label"]


# ── 시드 유형 ──────────────────────────────────────────────────────────


def test_시드의_유형은_모두_유효하고_대표_사례에_붙어_있다():
    by_id = {e.event_id: e for e in ShockSeedGateway().fetch_events()}
    assert all(e.category is None or e.category in EventCategory for e in by_id.values())
    assert by_id["outbreak-covid19-20200120"].category == "pandemic"
    assert by_id["outbreak-covid19-20200120"].end_date == date(2022, 4, 17)
    assert by_id["outbreak-mers-20150520"].category == "pandemic"
    assert by_id["outbreak-mers-20150520"].end_date == date(2015, 12, 23)
    assert all(by_id[f"min-wage-{y}"].category == "minimum_wage" for y in range(2019, 2027))
    # 거리두기 단계 조정은 한 사건의 세부 국면 — 따로 비교하지 않는다
    assert by_id["covid-distancing-20200322"].category is None


# ── 저장소 왕복 ────────────────────────────────────────────────────────


def _cleanup() -> None:
    with session_scope() as session:
        session.execute(
            delete(ShockEventIndustryOrm).where(ShockEventIndustryOrm.event_id.like(f"{_TEST_PREFIX}%"))
        )
        session.execute(delete(ShockEventOrm).where(ShockEventOrm.event_id.like(f"{_TEST_PREFIX}%")))


def test_유형은_저장했다가_그대로_읽히고_유형_있는_이벤트만_골라_읽는다():
    _cleanup()
    repository = SqlAlchemyShockEventRepository()
    repository.upsert(
        [
            _event(f"{_TEST_PREFIX}1", date(2020, 1, 20), "pandemic"),
            _event(f"{_TEST_PREFIX}2", date(2020, 3, 22), None),
        ]
    )
    ids = {e.event_id: e.category for e in repository.list_categorized() if e.event_id.startswith(_TEST_PREFIX)}
    assert ids == {f"{_TEST_PREFIX}1": "pandemic"}
    assert repository.upsert([_event(f"{_TEST_PREFIX}1", date(2020, 1, 20), "relief")]) == (0, 1)
    _cleanup()
