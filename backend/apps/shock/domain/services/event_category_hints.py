"""질문 문장에서 이벤트 유형 단서를 찾는다 — 등록되지 않은 가상의 상황도 유사 사례로 잇기 위해.

단서가 겹치면 여러 유형을 모두 돌려준다. 어느 유형이 질문에 맞는지는 리포트 작성 LLM이
유사 사례 값을 보고 최종 판단한다 — 여기서는 비교 재료를 넓게 모으는 역할만 한다.
"유행"처럼 감염병이 아닌 뜻(유행 메뉴)으로도 흔한 말은 단서로 쓰지 않는다.
"""

from apps.shock.domain.value_objects.event_category import EventCategory

_KEYWORDS: dict[EventCategory, tuple[str, ...]] = {
    EventCategory.PANDEMIC: (
        "바이러스", "감염병", "전염병", "코로나", "메르스", "팬데믹", "거리두기",
        "방역", "확진", "집합금지", "독감", "호흡기",
    ),
    EventCategory.MINIMUM_WAGE: ("최저임금", "최저 임금", "최저시급", "시급 인상", "인건비"),
    EventCategory.WORK_HOURS: ("52시간", "근로시간", "노동시간", "근무시간 단축"),
    EventCategory.RELIEF: ("지원금", "손실보상", "재난지원", "보조금"),
}

# 비교하지 않은 유형을 "질문에 이 단어를 넣으면 비교한다"고 안내할 때 쓰는 대표 단서
HINT_KEYWORDS: dict[EventCategory, str] = {
    EventCategory.PANDEMIC: "코로나",
    EventCategory.MINIMUM_WAGE: "최저임금",
    EventCategory.WORK_HOURS: "52시간",
    EventCategory.RELIEF: "지원금",
}


def categories_in(question: str | None) -> list[str]:
    """질문에 단서가 있는 유형 — EventCategory 선언 순서."""
    if not question:
        return []
    return [
        category.value
        for category, keywords in _KEYWORDS.items()
        if any(keyword in question for keyword in keywords)
    ]
