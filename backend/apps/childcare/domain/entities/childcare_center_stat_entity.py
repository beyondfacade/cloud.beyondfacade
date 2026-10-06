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
