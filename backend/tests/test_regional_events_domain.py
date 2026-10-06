"""④지역 이벤트 도메인 매핑 — 날짜 파싱·2019년 이후 필터·결정적 슬러그·이름 (순수 함수)."""

from datetime import date

from apps.shock.domain.services.regional_events import (
    apartment_event,
    large_store_events,
    parse_ymd,
    redevelopment_events,
)
from apps.shock.domain.value_objects.shock_layer import ShockLayer


def test_parse_ymd_accepts_three_source_formats_and_rejects_blank():
    assert parse_ymd("2024-11-22") == date(2024, 11, 22)  # 정비사업·대규모점포
    assert parse_ymd("2019-05-09 00:00:00.0") == date(2019, 5, 9)  # 아파트 사용승인일
    assert parse_ymd("20240131") == date(2024, 1, 31)
    assert parse_ymd("          ") is None
    assert parse_ymd("-") is None
    assert parse_ymd(None) is None


def test_redevelopment_creates_migration_and_construction_events_since_2019():
    events = redevelopment_events(
        code="2001",
        district="중구",
        zone_name="세운6-3-3",
        biz_type="도시정비형 재개발",
        migration_start=date(2020, 12, 1),
        migration_end=date(2021, 5, 25),
        construction_start=date(2018, 7, 2),  # 2019년 이전 — 제외
    )
    assert len(events) == 1
    event = events[0]
    assert event.event_id == "regional-redev-migration-2001"
    assert event.name == "중구 세운6-3-3 도시정비형 재개발 이주 시작"
    assert (event.start_date, event.end_date) == (date(2020, 12, 1), date(2021, 5, 25))
    assert event.layer == ShockLayer.REGIONAL
    assert event.scope == "행정동"
    assert event.category is None  # 유사 사례 비교 대상 밖
    assert event.source == "서울 열린데이터광장 OA-22856 서울특별시 도시정비사업 통계"
    assert event.source_url == "https://data.seoul.go.kr/dataList/OA-22856/S/1/datasetView.do"


def test_redevelopment_drops_end_date_earlier_than_start():
    [migration, construction] = redevelopment_events(
        code="7",
        district="용산구",
        zone_name="한남3구역",
        biz_type="주택정비형 재개발",
        migration_start=date(2022, 3, 1),
        migration_end=date(2021, 1, 1),
        construction_start=date(2024, 6, 1),
    )
    assert migration.end_date is None
    assert construction.event_id == "regional-redev-construction-7"
    assert construction.name == "용산구 한남3구역 주택정비형 재개발 착공"


def test_large_store_excludes_ssm_and_creates_open_and_close_events():
    assert large_store_events("1", "GS THE FRESH 송파석촌역점", "준대규모점포", "구분없음",
                              date(2026, 8, 18), None) == []
    events = large_store_events(
        "300", "롯데쇼핑(주) 아울렛 가산점", "대규모점포", "쇼핑센터",
        date(2015, 12, 29), date(2025, 9, 30),
    )
    assert [(e.event_id, e.name, e.start_date) for e in events] == [
        ("regional-store-close-300", "롯데쇼핑(주) 아울렛 가산점 폐업", date(2025, 9, 30))
    ]
    assert events[0].description == "쇼핑센터"
    assert events[0].source == "서울 열린데이터광장 OA-16096 서울시 대규모점포 인허가 정보"


def test_apartment_movein_needs_1000_households_since_2019():
    event = apartment_event("A10025638", "래미안길음센터피스", 2352, date(2019, 11, 29))
    assert event.event_id == "regional-apt-movein-A10025638"
    assert event.name == "래미안길음센터피스 입주(2,352세대)"
    assert event.source == "서울 열린데이터광장 OA-15818 서울시 공동주택 아파트 정보"
    assert apartment_event("A1", "작은단지", 999, date(2020, 1, 1)) is None
    assert apartment_event("A2", "세대수 결측", None, date(2020, 1, 1)) is None
    assert apartment_event("A3", "옛 단지", 3000, date(2018, 12, 31)) is None
