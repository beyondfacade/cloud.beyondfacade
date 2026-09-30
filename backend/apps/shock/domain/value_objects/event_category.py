"""이벤트 유형 VO — 유사 사례 비교의 단위. 같은 유형의 지난 이벤트가 지금 이벤트의 참고 사례다.

layer(정책·거시·트렌드·지역)가 충격이 **어디서** 왔는지라면, 유형은 **무엇이** 일어났는지다.
유형이 없는 이벤트(거리두기 단계 조정처럼 한 사건의 세부 국면)는 유사 사례 비교에 쓰지 않는다.
"""

from enum import StrEnum


class EventCategory(StrEnum):
    PANDEMIC = "pandemic"  # 감염병 유행과 방역 조치
    MINIMUM_WAGE = "minimum_wage"  # 최저임금 인상
    WORK_HOURS = "work_hours"  # 근로시간 단축
    RELIEF = "relief"  # 재난지원금·손실보상


CATEGORY_LABELS: dict[str, str] = {
    EventCategory.PANDEMIC: "감염병·방역",
    EventCategory.MINIMUM_WAGE: "최저임금",
    EventCategory.WORK_HOURS: "근로시간",
    EventCategory.RELIEF: "지원금·보상",
}

# 비교 기간(년, 분기는 ×4) — 해마다 새로 정해지는 최저임금·한 번 지급하는 지원금은 그 해만 본다
# (다음 해 이벤트와 겹치지 않게). 드문 충격인 감염병과 한 번 바뀌면 이어지는 근로시간 제도는 3년.
# 이벤트 직전 4분기와 최근 4분기의 업종 상태를 견주는 유형 — 몇 년에 한 번 오는 드문 이벤트만.
# 최저임금은 해마다 올라 "직전 4분기"가 곧 작년(최근과 겹침)이고, 지원금은 짧아 상태를 바꾸지 못한다.
CONDITION_COMPARED: frozenset[str] = frozenset({EventCategory.PANDEMIC, EventCategory.WORK_HOURS})

CATEGORY_YEARS: dict[str, int] = {
    EventCategory.PANDEMIC: 3,
    EventCategory.MINIMUM_WAGE: 1,
    EventCategory.WORK_HOURS: 3,
    EventCategory.RELIEF: 1,
}
