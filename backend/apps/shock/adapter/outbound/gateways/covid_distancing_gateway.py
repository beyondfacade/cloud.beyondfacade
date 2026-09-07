"""보건복지부 코로나19 사회적 거리두기 현황 API Driven Adapter (data.go.kr 15098772).

docs/api.md §3-2: 커버리지 2020-12-08 ~ 2021-10-31 (일별 328건, 결측 없음 — 2026-09-07 실호출 검증).
일별 시도 단계(stdDay×seoLvl)를 동일 단계 연속 구간으로 압축해 서울 shock_event 행을 만든다.
2020-12-08 이전 1차 거리두기는 시드 파일(shock_events_seed.json)이 보충한다.
"""

from datetime import date

import httpx

from apps.shock.app.ports.output.shock_event_port import ShockEventSourcePort
from apps.shock.domain.entities.shock_event_entity import IndustryImpact, ShockEvent
from apps.shock.domain.value_objects.shock_layer import Severity, ShockLayer
from core.matrix.grid_keymaker_secret_manager import get_settings

_ENDPOINT = "https://apis.data.go.kr/1352000/ODMS_COVID_12/callCovid12Api"
_NUM_ROWS = 400  # 전체 328건 — 1회 호출 전량 수신 (이력 데이터, 페이징 불필요)
_DATASET_URL = "https://www.data.go.kr/data/15098772/openapi.do"
_SOURCE = "보건복지부 코로나19 사회적 거리두기 현황 API (data.go.kr 15098772)"

# 단계 하한 → (여가업종, 카페) severity — brainstorming §5.2: 노래방·PC방·헬스장 ≫ 카페
_SEVERITY_BANDS = [
    (2.5, (Severity.CRITICAL, Severity.HIGH)),  # 집합금지·매장 취식 금지 수준
    (2.0, (Severity.HIGH, Severity.MEDIUM)),
    (0.0, (Severity.MEDIUM, Severity.LOW)),
]
_LEISURE_INDUSTRIES = ("karaoke", "pc_bang", "gym", "billiard")


def _impacts_for_level(level: float) -> list[IndustryImpact]:
    leisure, cafe = next(band for floor, band in _SEVERITY_BANDS if level >= floor)
    return [IndustryImpact(industry_id, leisure) for industry_id in _LEISURE_INDUSTRIES] + [
        IndustryImpact("cafe", cafe)
    ]


def _to_event(level: float, start: date, end: date) -> ShockEvent:
    return ShockEvent(
        event_id=f"covid-distancing-seoul-{start:%Y%m%d}",  # 결정적 ID — 재적재 멱등
        layer=ShockLayer.POLICY,
        name=f"코로나19 사회적 거리두기 서울 {level:g}단계",
        start_date=start,
        end_date=end,
        scope="서울",
        source=_SOURCE,
        source_url=_DATASET_URL,
        description="일별 시도 단계 시계열(stdDay×seoLvl)을 동일 단계 연속 구간으로 압축",
        industry_impacts=_impacts_for_level(level),
    )


def compress_to_events(items: list[dict]) -> list[ShockEvent]:
    """일별 실응답 → 서울(seoLvl) 동일 단계 연속 구간의 shock_event 목록 (날짜순)."""
    days = sorted(
        (date.fromisoformat(item["stdDay"]), float(item["seoLvl"])) for item in items
    )
    intervals: list[list] = []  # [level, start, end]
    for day, level in days:
        if intervals and intervals[-1][0] == level and (day - intervals[-1][2]).days == 1:
            intervals[-1][2] = day
        else:
            intervals.append([level, day, day])
    return [_to_event(level, start, end) for level, start, end in intervals]


class CovidDistancingGateway(ShockEventSourcePort):
    def fetch_events(self) -> list[ShockEvent]:
        response = httpx.get(
            _ENDPOINT,
            params={
                "serviceKey": get_settings().data_go_kr_api_key,
                "pageNo": 1,
                "numOfRows": _NUM_ROWS,
                "apiType": "JSON",
            },
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
        items = body.get("items", [])
        print(f"거리두기 API 호출 1건 — 일별 {len(items)}행 수신 (totalCount {body.get('totalCount')})")
        return compress_to_events(items)
