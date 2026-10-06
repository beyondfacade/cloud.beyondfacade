"""④지역 이벤트 매핑 — 서울 열린데이터광장 3개 원천의 행을 shock_event로 옮기는 순수 함수.

- 2019-01-01 이후 날짜만 이벤트로 만든다 (상권 분석 기간과 같은 출발점)
- event_id는 원천 고유번호로 만든 결정적 슬러그 — 재적재 멱등
- category는 비워 둔다 — 유사 사례(analog) 비교는 category 붙은 국가 단위 이벤트만 본다
- source는 공공누리 출처표시를 겸한다 (데이터셋 번호·이름)
"""

from datetime import date

from apps.shock.domain.entities.shock_event_entity import ShockEvent
from apps.shock.domain.value_objects.shock_layer import ShockLayer

SINCE = date(2019, 1, 1)
_SCOPE = "행정동"
_LARGE_STORE_KIND = "대규모점포"  # 준대규모점포(SSM)는 동네 슈퍼 규모라 지역 충격으로 보지 않는다
_MOVE_IN_MIN_HOUSEHOLDS = 1000

_REDEV = ("OA-22856", "서울특별시 도시정비사업 통계")
_LARGE_STORE = ("OA-16096", "서울시 대규모점포 인허가 정보")
_APARTMENT = ("OA-15818", "서울시 공동주택 아파트 정보")


def parse_ymd(text: str | None) -> date | None:
    """'2024-11-22'·'2019-05-09 00:00:00.0'·'20240131' → date. 공란·'-'·불량은 None."""
    digits = (text or "").strip()[:10].replace("-", "")
    if len(digits) != 8 or not digits.isdigit():
        return None
    try:
        return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError:
        return None


def _event(
    dataset: tuple[str, str],
    event_id: str,
    name: str,
    start: date,
    end: date | None = None,
    description: str | None = None,
) -> ShockEvent:
    dataset_id, dataset_name = dataset
    return ShockEvent(
        event_id=event_id,
        layer=ShockLayer.REGIONAL,
        name=name,
        start_date=start,
        end_date=end if end is not None and end >= start else None,
        scope=_SCOPE,
        source=f"서울 열린데이터광장 {dataset_id} {dataset_name}",
        source_url=f"https://data.seoul.go.kr/dataList/{dataset_id}/S/1/datasetView.do",
        description=description,
    )


def _recent(day: date | None) -> bool:
    return day is not None and day >= SINCE


def redevelopment_events(
    code: str,
    district: str,
    zone_name: str,
    biz_type: str,
    migration_start: date | None,
    migration_end: date | None,
    construction_start: date | None,
) -> list[ShockEvent]:
    """정비구역 1곳 → 이주 시작(종료일=이주 종료)·착공 이벤트."""
    zone = f"{district} {zone_name} {biz_type}"
    events = []
    if _recent(migration_start):
        events.append(
            _event(_REDEV, f"regional-redev-migration-{code}", f"{zone} 이주 시작",
                   migration_start, migration_end)
        )
    if _recent(construction_start):
        events.append(
            _event(_REDEV, f"regional-redev-construction-{code}", f"{zone} 착공",
                   construction_start)
        )
    return events


def large_store_events(
    mgt_no: str,
    name: str,
    store_kind: str,
    business_type: str,
    permit_date: date | None,
    close_date: date | None,
) -> list[ShockEvent]:
    """대규모점포 1곳 → 개설(인허가)·폐업 이벤트. 준대규모점포·구분 공란은 제외."""
    if store_kind != _LARGE_STORE_KIND:
        return []
    description = business_type or None  # 업태(백화점·대형마트·쇼핑센터 등)
    events = []
    if _recent(permit_date):
        events.append(
            _event(_LARGE_STORE, f"regional-store-open-{mgt_no}", f"{name} 개설(인허가)",
                   permit_date, description=description)
        )
    if _recent(close_date):
        events.append(
            _event(_LARGE_STORE, f"regional-store-close-{mgt_no}", f"{name} 폐업",
                   close_date, description=description)
        )
    return events


def apartment_event(
    apt_code: str, name: str, households: int | None, approval_date: date | None
) -> ShockEvent | None:
    """사용승인 1,000세대 이상 단지 → 대규모 입주 이벤트 (세대수 결측·0은 제외)."""
    if not households or households < _MOVE_IN_MIN_HOUSEHOLDS or not _recent(approval_date):
        return None
    return _event(_APARTMENT, f"regional-apt-movein-{apt_code}",
                  f"{name} 입주({households:,}세대)", approval_date)
