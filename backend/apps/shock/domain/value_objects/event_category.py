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
