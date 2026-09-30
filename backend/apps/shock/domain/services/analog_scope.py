"""유사 사례 계산 범위 — 내 업종 흐름을 동네 가까이서 보되, 표본이 모자라면 서울 전체로 돌아간다.

동 단위는 쓰지 않는다. 2026-09-30 실측에서 보라매동 한식(124곳)은 분기 값이 2~3%p씩 흔들려 약세·강세
기준(±0.3%p)을 거의 매번 넘었고, 2025년 최저임금 사례는 서울 전체(4분기 연속 약세)와 반대로 나왔다.
자치구도 점포가 적으면 같은 문제가 있어(관악구 당구장 88곳, 표준편차 6.8%p) 내 업종 점포가
`DISTRICT_MIN_STOCK` 이상인 구에서만 구로 계산한다 — 한식은 25개 구 전부, 카페 20개, 미용실 19개 구가 넘는다.

비교 업종(거듭 강세·약세)은 늘 서울 전체다. 구 안에서 줄 세우면 점포 수백 곳짜리 업종의 큰 흔들림이 1등과
꼴찌를 차지한다.
"""

from dataclasses import dataclass, replace
from datetime import date

from apps.shock.domain.services.event_analog import EventImpact
from apps.shock.domain.services.industry_flows import IndustryFlows

DISTRICT_MIN_STOCK = 1000

SCOPE_DISTRICT = "district"
SCOPE_SEOUL = "seoul"
SEOUL_NAME = "서울 전체"


@dataclass(frozen=True)
class AnalogScope:
    level: str  # district | seoul — 내 업종 흐름을 센 범위
    name: str  # "관악구" | "서울 전체"
    target_stock: int  # 그 범위의 내 업종 현재 점포 수
    min_stock: int = DISTRICT_MIN_STOCK
    comparison_name: str = SEOUL_NAME  # 비교 업종을 센 범위


def _stock(flows: list[IndustryFlows], industry_id: str, month: date) -> int | None:
    flow = next((f for f in flows if f.industry_id == industry_id), None)
    return None if flow is None else flow.stock_at(month)


def choose_scope(
    seoul_flows: list[IndustryFlows],
    district_flows: list[IndustryFlows],
    industry_id: str,
    district_name: str | None,
    month: date,
) -> AnalogScope:
    local = _stock(district_flows, industry_id, month)
    if district_name and local is not None and local >= DISTRICT_MIN_STOCK:
        return AnalogScope(SCOPE_DISTRICT, district_name, local)
    return AnalogScope(SCOPE_SEOUL, SEOUL_NAME, _stock(seoul_flows, industry_id, month) or 0)


def with_local_target(impact: EventImpact, local: EventImpact, industry_id: str) -> EventImpact:
    """서울 전체로 계산한 사례에 내 업종 값만 구 값으로 바꿔 끼운다 — 비교 업종 순위는 그대로 둔다."""
    quarters = [
        replace(seoul, target=near.target, excess={**seoul.excess, industry_id: near.excess.get(industry_id)})
        for seoul, near in zip(impact.quarters, local.quarters)
    ]
    return replace(impact, quarters=quarters)
