from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ChildcareCenterStat:
    """원천 기준일 시점의 정원·현원·대기 현황 — 시점마다 변하므로 시설과 분리해 이력으로 쌓는다.

    정원 대비 현원 = 가동률, 대기아동 = 수요 초과 직접 관측 (brainstorming §3.5 어린이집).
    """

    base_date: date  # datastdrdt 원천 기준일
    capacity: int  # crcapat 정원
    child_count: int  # crchcnt 현원 (= CHILD_CNT_TOT, 종로 58건 전수 일치 실측)
    waiting_count: int | None  # EW_CNT_TOT 입소대기 — 공란 None 보존("0" 표기 실측 0건이라 0 추정 금지)
    class_count: int  # CLASS_CNT_TOT 반 수
    staff_count: int  # chcrtescnt 보육교직원 수 (= EM_CNT_TOT, 전수 일치 실측)


@dataclass(frozen=True)
class ChildcareRegionSummary:
    """행정동의 운영 중 어린이집 최신 현황 합계 — 사이드패널 카드 단위."""

    region_code: str
    base_date: date | None  # 합산된 현황 중 최신 기준일 — 시설 없으면 None
    center_count: int
    capacity: int
    child_count: int
    occupancy_rate: float | None  # 현원/정원 — 정원 0이면 None
    waiting_count: int | None  # 입소대기 합 — 전 시설 공란이면 None (중복 신청 포함 건수)

    @classmethod
    def of(cls, region_code: str, stats: list[ChildcareCenterStat]) -> "ChildcareRegionSummary":
        capacity = sum(s.capacity for s in stats)
        child_count = sum(s.child_count for s in stats)
        waitings = [s.waiting_count for s in stats if s.waiting_count is not None]
        return cls(
            region_code=region_code,
            base_date=max((s.base_date for s in stats), default=None),
            center_count=len(stats),
            capacity=capacity,
            child_count=child_count,
            occupancy_rate=round(child_count / capacity, 4) if capacity else None,
            waiting_count=sum(waitings) if waitings else None,
        )
