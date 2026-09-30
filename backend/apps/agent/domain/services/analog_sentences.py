"""유사 사례 유형 종합의 고정 문장 — LLM이 틀로 조립하면 유형·사례 이름을 섞고 글자를 끊어 쓴다.

코드가 완성 문장을 만들어 `facts.analogs.outlooks[]`에 싣고, LLM은 그대로 옮긴다.
"""

SITUATIONS = {
    "pandemic": "감염병이 유행했던 시기에",
    "minimum_wage": "최저임금이 올랐던 시기에",
    "work_hours": "근로시간이 줄었던 시기에",
    "relief": "지원금이 풀렸던 시기에",
}

# 전 업종과의 차이가 이 안(%p)이면 "비슷하게", 폐업률 차이가 이 안(%p)이면 "비슷했습니다"
_SAME_BAND = 0.5

_DIRECTION_SENTENCES = {
    "weaker": "비슷한 충격이 오면 그때보다 약할 수 있습니다.",
    "stronger": "그때보다 버틸 여력이 있을 수 있습니다.",
    "similar": "업종 상태는 그때와 비슷합니다.",
}


def _has_final_consonant(word: str) -> bool:
    """마지막 글자가 한글이고 받침이 있는지 — finance·intent BC와 같은 규칙(BC별 사본)."""
    last = word[-1:] or " "
    return "가" <= last <= "힣" and (ord(last) - 0xAC00) % 28 != 0


def recommended_sentence(outlook: dict) -> str | None:
    situation = SITUATIONS.get(outlook.get("category") or "")
    names = [i["industry_name"] for i in outlook.get("recommended") or []]
    if not situation or not names:
        return None
    ending = "이었습니다" if _has_final_consonant(names[-1]) else "였습니다"
    return f"{situation} 다른 업종보다 상대적으로 잘 버틴 업종은 {', '.join(names)}{ending}."


def _growth(period: dict) -> str:
    """전 업종 대비 — 늘었는지 줄었는지와, 전 업종보다 더·덜 그랬는지."""
    verb = "늘었" if period["growth_pct"] > 0 else "줄었"
    excess = period["excess_pct"]
    if abs(excess) < _SAME_BAND:
        return f"전 업종과 비슷하게 {verb}"
    more = (excess > 0) == (period["growth_pct"] > 0)
    return f"전 업종보다 {abs(excess):.1f}%p {'더' if more else '덜'} {verb}"


def _closure(before: float, recent: float) -> str:
    change = "비슷했" if abs(recent - before) < _SAME_BAND else "높아졌" if recent > before else "낮아졌"
    return f"폐업률은 {before:.1f}%에서 {recent:.1f}%로 {change}습니다"


def condition_sentence(condition: dict | None, industry_name: str) -> str | None:
    if not condition:
        return None
    before, recent = condition["before"], condition["recent"]
    event = condition["event_name"].split(" — ")[0]
    particle = "은" if _has_final_consonant(industry_name) else "는"
    return (
        f"{event} 직전 1년 {industry_name}{particle} {_growth(before)}고, "
        f"최근 1년은 {_growth(recent)}으며, "
        f"{_closure(before['closure_rate_pct'], recent['closure_rate_pct'])}. "
        f"{_DIRECTION_SENTENCES.get(condition.get('direction'), '')}"
    ).rstrip()


def _industry_name(analogs: dict) -> str:
    events = [*(analogs.get("current_events") or []), *(analogs.get("analogs") or [])]
    series = (s for e in events for s in e.get("series") or [] if s.get("role") == "target")
    return next((s["industry_name"] for s in series), "이 업종")


def with_sentences(analogs: dict) -> dict:
    """유형 종합마다 `recommended_sentence`·`condition_sentence`를 붙인 사본 (원본은 그대로)."""
    if not analogs.get("outlooks"):
        return analogs
    industry_name = _industry_name(analogs)
    outlooks = [
        {
            **outlook,
            "recommended_sentence": recommended_sentence(outlook),
            "condition_sentence": condition_sentence(outlook.get("condition"), industry_name),
        }
        for outlook in analogs["outlooks"]
    ]
    return {**analogs, "outlooks": outlooks}
