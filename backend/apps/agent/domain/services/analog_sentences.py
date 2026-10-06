"""유사 사례 유형 종합의 고정 문장 — LLM이 틀로 조립하면 유형·사례 이름을 섞고 글자를 끊어 쓴다.

코드가 완성 문장을 만들어 `facts.analogs.outlooks[]`에 싣고, LLM은 그대로 옮긴다.
"""

SITUATIONS = {
    "pandemic": "감염병이 유행했던 시기에",
    "minimum_wage": "최저임금이 올랐던 시기에",
    "work_hours": "근로시간이 줄었던 시기에",
    "relief": "지원금이 풀렸던 시기에",
}

# 유사 사례는 서울 전체 흐름이다 — 리포트가 동 이야기라 범위를 적지 않으면 동의 수치로 읽힌다.
# 동·자치구는 쓰지 않는다: 2026-09-30 실측에서 점포 1,000곳 넘는 구도 아무 일 없던 분기의 60~90%가
# 강세·약세로 잡혔고(서울 전체 한식 34%), 서울 전체와 판정이 같은 비율은 22~41%였다.
AREA = "서울 전체"

# 사례 분기의 비교 기준 — shock BC `Quarter.baseline`(이벤트 직전 1년의 같은 분기)
_BASELINE = "사례 직전 1년 같은 분기"

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


def recommended_sentence(outlook: dict, area: str | None = None) -> str | None:
    """`area`는 업종을 센 범위("서울 전체")."""
    situation = SITUATIONS.get(outlook.get("category") or "")
    names = [i["industry_name"] for i in outlook.get("recommended") or []]
    if not situation or not names:
        return None
    ending = "이었습니다" if _has_final_consonant(names[-1]) else "였습니다"
    where = f" {area}에서" if area else ""
    return f"{situation}{where} 다른 업종보다 상대적으로 잘 버틴 업종은 {', '.join(names)}{ending}."


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


def condition_sentence(condition: dict | None, industry_name: str, name: str | None = None) -> str | None:
    if not condition:
        return None
    before, recent = condition["before"], condition["recent"]
    event = name or condition["event_name"].split(" — ")[0]
    particle = "은" if _has_final_consonant(industry_name) else "는"
    return (
        f"{event} 직전 1년 {industry_name}{particle} {_growth(before)}고, "
        f"최근 1년은 {_growth(recent)}으며, "
        f"{_closure(before['closure_rate_pct'], recent['closure_rate_pct'])}. "
        f"{_DIRECTION_SENTENCES.get(condition.get('direction'), '')}"
    ).rstrip()


def summary_sentence(event: dict, industry_name: str, name: str | None = None) -> str | None:
    """사례 이후 분기 중 내 업종 점포 증감이 사례 직전 1년 같은 분기보다 약했던·강했던 분기 수.

    비교 기준(`Quarter.baseline`)을 문장에 적는다 — "평소"만 쓰면 "다른 업종보다"로 읽혔다.
    """
    quarters = len(event.get("quarters") or [])
    if quarters == 0:
        return None
    weak, strong = event.get("target_weak_quarters", 0), event.get("target_strong_quarters", 0)
    head = f"{name or event['name'].split(' — ')[0]} 이후{' 지금까지' if event.get('current') else ''}"
    subject = f"{industry_name} 점포 증감"
    if weak == quarters or strong == quarters:
        return f"{head} {quarters}분기 내내 {subject}이 {_BASELINE}보다 {'약했' if weak else '강했'}습니다."
    if not weak and not strong:
        return f"{head} {quarters}분기 동안 {subject}은 {_BASELINE}와 비슷했습니다."
    counts = ", ".join(
        [*([f"약했던 분기는 {weak}분기"] if weak else []), *([f"강했던 분기는 {strong}분기"] if strong else [])]
    )
    streak = event.get("target_weak_streak", 0)
    tail = f"였고, 처음 {streak}분기는 연속으로 약했습니다." if streak >= 2 else "였습니다."
    return f"{head} {quarters}분기 중 {subject}이 {_BASELINE}보다 {counts}{tail}"


# 겹친 정책을 이름까지 적는 분기 수 — 나머지는 분기 수로만 줄인다
_OVERLAP_QUARTERS = 2


def overlap_sentence(quarters: list[dict]) -> str | None:
    """사례 기간에 겹친 다른 정책 — 방향·인과 없이 나란히만."""
    overlapped = [q for q in quarters if q.get("overlaps")]
    if not overlapped:
        return None
    shown = ", ".join(
        f"{q.get('label') or str(q.get('quarter')) + '분기'}에는 {'·'.join(q['overlaps'])}"
        for q in overlapped[:_OVERLAP_QUARTERS]
    )
    rest = len(overlapped) - _OVERLAP_QUARTERS
    return f"같은 기간 {shown}도 있었습니다." + (f" 그 밖에 {rest}개 분기에도 다른 정책이 겹쳤습니다." if rest > 0 else "")


def _industry_name(analogs: dict) -> str:
    events = [*(analogs.get("current_events") or []), *(analogs.get("analogs") or [])]
    series = (s for e in events for s in e.get("series") or [] if s.get("role") == "target")
    return next((s["industry_name"] for s in series), "이 업종")


def llm_view(analogs: dict) -> dict:
    """LLM에게 넘길 모양 — 요약 문장을 비워 둔(대표가 아닌) 지난 사례는 빼서 스스로 지어 쓰지 못하게 한다.

    화면 카드는 모든 사례를 그리므로 원본은 그대로 둔다.
    """
    events = analogs.get("analogs")
    if not events:
        return analogs
    return {**analogs, "analogs": [e for e in events if e.get("summary_sentence", "") is not None]}


# 이름 " — " 뒤 구분어가 이만큼(글자) 이하면 괄호로 남긴다 — "주 52시간제 시행(5~49인 사업장)"
_QUALIFIER_MAX = 12


# 질문 속 유형마다 요약 문장을 붙일 최근 사례 수 — 나머지는 LLM이 나열하지 않도록 비워 둔다
_REPRESENTATIVES = 2


def _short_name(name: str) -> str:
    """긴 설명은 떼고 짧은 구분어만 괄호로 남긴다."""
    head, _, qualifier = name.partition(" — ")
    return f"{head}({qualifier})" if qualifier and len(qualifier) <= _QUALIFIER_MAX else head


def _display_names(events: list[dict]) -> list[str]:
    """사례마다 문장용 이름(같은 순서). 줄인 이름이 겹치면 시작 연도로 가른다."""
    shorts = [_short_name(e.get("name") or "") for e in events]
    return [
        f"{str(e['start_date'])[:4]}년 {short}" if shorts.count(short) > 1 and e.get("start_date") else short
        for e, short in zip(events, shorts)
    ]


def _representatives(analogs: dict) -> set[int]:
    """요약 문장을 붙일 지난 사례(목록 순번) — 질문 속 유형마다 최근 2건. 유형 정보가 없으면 전부."""
    events = analogs.get("analogs") or []
    if "categories" not in analogs:
        return set(range(len(events)))
    asked = {c.get("category") for c in analogs["categories"] if c.get("reason") == "question"}
    chosen: set[int] = set()
    for category in asked:
        chosen.update([i for i, e in enumerate(events) if e.get("category") == category][:_REPRESENTATIVES])
    return chosen


def with_sentences(analogs: dict) -> dict:
    """사례·유형 종합마다 LLM이 그대로 옮길 완성 문장을 붙인 사본 (원본은 그대로, 없는 목록은 두고)."""
    if analogs.get("available") is False:
        return analogs
    industry_name = f"{AREA} {_industry_name(analogs)}"
    current = analogs.get("current_events") or []
    events = [*current, *(analogs.get("analogs") or [])]
    names = _display_names(events)
    by_id = {e["event_id"]: name for e, name in zip(events, names) if e.get("event_id")}
    representatives = _representatives(analogs)

    def summarize(event: dict, name: str, written: bool = True) -> dict:
        quarters = [
            {**q, "overlaps": [_short_name(o) for o in q.get("overlaps") or []]} for q in event.get("quarters") or []
        ]
        return {
            **event,
            "quarters": quarters,
            "summary_sentence": summary_sentence(event, industry_name, name) if written else None,
            "overlap_sentence": overlap_sentence(quarters) if written else None,
        }

    def compare(outlook: dict) -> str | None:
        condition = outlook.get("condition")
        return condition_sentence(condition, industry_name, condition and by_id.get(condition.get("event_id")))

    enriched = {
        "current_events": [summarize(e, n) for e, n in zip(current, names)],
        "analogs": [
            summarize(e, n, i in representatives)
            for i, (e, n) in enumerate(zip(events[len(current):], names[len(current):]))
        ],
        "outlooks": [
            {
                **o,
                "recommended_sentence": recommended_sentence(o, AREA),
                "condition_sentence": compare(o),
            }
            for o in analogs.get("outlooks") or []
        ],
    }
    return {**analogs, **{key: items for key, items in enriched.items() if key in analogs}}
