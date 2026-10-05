"""리포트 6개 절을 facts만으로 쓰는 순수 모듈 (stdlib만 import).

설계서 docs/superpowers/specs/2026-10-05-report-code-first-design.md §4 — 결론과 수치는 코드가 사실에서 쓰고,
LLM은 맨 위 해석(answer) 한 단락만 쓴다. 원칙:
① 숫자에는 범위(무엇의·어디의·언제의)를 붙인다 — 줄마다 동·업종 이름이나 "서울"을 적는다.
② 자료가 없으면 "자료 부족 — 이유"를 쓰고 추정으로 메우지 않는다.
③ 신뢰 태그는 코드가 붙인다 — 정형 값 [확인된 사실], 뉴스 [참고 신호].
④ 화면 차트와 같은 규칙을 쓴다 — 시간대 문장은 프론트 `hour-gap-sentence.ts`와 같은 규칙.
"""

from apps.agent.domain.services.report_guards import FUNDING_DISCLAIMER

FACT = "[확인된 사실]"
SIGNAL = "[참고 신호]"

# 절 이름 → 제목. 방출·저장 순서다(section_stream.SECTION_ORDER는 answer 다음에 이 순서).
SECTION_TITLES = {
    "verdict": "판정",
    "reasons": "왜 안 되나",
    "analogs": "유사 사례",
    "conditions": "그래도 한다면",
    "alternatives": "대안 동네·업종",
    "funding": "대안 업종 지원사업",
}

# 판정 코드 → 라벨. 프론트 `shared/verdict.ts` LABELS와 같은 어휘다.
_VERDICT_LABELS = {"red": "비추천", "orange": "조건부", "clear": "경고 없음", "insufficient": "판정 보류"}
# 신호 키 → 이름. 프론트 `shared/verdict.ts` SIGNAL_LABELS와 같은 어휘다.
_SIGNAL_LABELS = {
    "net_outflow": "순유출",
    "survival_cliff": "생존 절벽",
    "early_closure": "조기 폐업",
    "saturation": "포화",
    "shrinking": "상권 축소",
    "closure_rate": "폐업률",
    "tobacco_gap": "담배권 빈자리",
    "trade_per_office": "사무소당 거래",
}
# 시간대 6구간 표기. 프론트 `neighborhood-charts.ts` HOUR_BAND_LABELS와 같다.
HOUR_BAND_LABELS = {
    "00_06": "새벽(00~06시)",
    "06_11": "아침(06~11시)",
    "11_14": "점심(11~14시)",
    "14_17": "오후(14~17시)",
    "17_21": "저녁(17~21시)",
    "21_24": "밤(21~24시)",
}
_MAX_PER_AXIS = 3  # 대안 두 축 각 최대 3개
_DISASTER_YEARS = range(2020, 2023)
_DISASTER_NOTE = "2020~2022년 폐업률은 재난지원금·손실보상으로 폐업이 늦춰져 왜곡됐을 수 있습니다."
_BUDGET_LINE = f"{FACT} 입력한 예산으로 총 준비자금·조달 필요액·손익분기 매출을 계산하려면 자금 계획 화면을 이용하세요."
# 충격 목록이 이 업종 것인지(True) 전 업종 공통으로 되돌린 것인지(False) — report_facts._shocks가 정한다
_SHOCK_SCOPES = {True: "{industry}에 영향을 준 충격", False: "{industry} 전용 기록은 없어 전 업종 공통 충격"}


def missing(reason: str | None) -> str:
    return f"자료 부족 — {reason or '이유 미상'}"


def _missing_reason(value: object) -> str | None:
    """수집 실패·판정 불가 자리(`{"available": False, "reason": ...}`)면 그 이유, 아니면 None.

    목록 자리(지표 이력·충격·공고)도 실패하면 이 dict가 온다 — 모양을 보고 가른다.
    """
    if isinstance(value, dict) and value.get("available") is False:
        return value.get("reason") or "이유 미상"
    return None


def _names(facts: dict) -> tuple[str, str]:
    region = facts.get("region") or {}
    return region.get("name") or "이 동", region.get("industry_name") or "이 업종"


def _quarter(year_quarter: str | None) -> str:
    """'20262' → '2026년 2분기'."""
    return f"{year_quarter[:4]}년 {year_quarter[4:]}분기" if year_quarter else "최신 분기"


# ── 판정 ─────────────────────────────────────────────────────


def _verdict(facts: dict) -> str:
    region, industry = _names(facts)
    verdict = facts.get("verdict") or {}
    if not verdict.get("available"):
        return f"{FACT} {region} {industry} 판정: {missing(verdict.get('reason'))}"
    judged = [s for s in verdict.get("signals") or [] if not s.get("advisory")]
    short = sum(s.get("level") == "unavailable" for s in judged)
    label = _VERDICT_LABELS.get(verdict.get("verdict_code"), verdict.get("verdict_code"))
    tail = f", {short}개는 자료 부족으로 계산하지 못함" if short else ""
    return (
        f"{FACT} {region} {industry} 판정: **{label}** — 경고 신호 {len(judged)}개 중 "
        f"{verdict.get('on_count', 0)}개 켜짐(강한 신호 {verdict.get('strong_count', 0)}개){tail}. "
        f"산출 {str(verdict.get('computed_at') or '')[:10]}."
    )


# ── 왜 안 되나 ───────────────────────────────────────────────

# 참고 신호(advisory) 여부 → 줄 모양 (if/elif 대신 테이블 디스패치). 꺼진 신호는 쓰지 않는다.
# 켜진 신호와 표본 부족 신호는 같은 모양이다 — 표본 부족은 evidence가 "표본 부족 — …"으로 이유를 말한다.
_SIGNAL_LINES = {
    False: lambda name, evidence, where: f"- {FACT} {name}({where}): {evidence}",
    True: lambda name, evidence, where: f"- {FACT} 참고 — {name}: {evidence}",
}


def _signals(verdict: dict, region: str, industry: str) -> str:
    if not verdict.get("available"):
        return f"{FACT} 경고 신호({region} {industry}): {missing(verdict.get('reason'))}"
    where = f"{region} {industry}"
    lines = [
        _SIGNAL_LINES[bool(s.get("advisory"))](_SIGNAL_LABELS.get(s.get("key"), s.get("key")), s.get("evidence"), where)
        for s in verdict.get("signals") or []
        if s.get("level") != "off"
    ]
    return "\n".join(lines) or f"{FACT} {where}: 켜진 경고 신호 없음."


def _current_year(facts: dict) -> str | None:
    """사실 묶음의 기준 연도 — 분기 자료('20262')의 연도. 이 해의 폐업률은 아직 진행 중인 부분 연도다."""
    for key in ("commerce_change", "profile"):
        year_quarter = (facts.get(key) or {}).get("year_quarter")
        if year_quarter:
            return year_quarter[:4]
    return None


def _closure_trend(history: object, region: str, industry: str, current_year: str | None) -> str:
    reason = _missing_reason(history)
    rows = [r for r in history or [] if r.get("closure_rate") is not None] if reason is None else []
    if not rows:
        return f"{FACT} {region} {industry} 연간 폐업률: {missing(reason or '연도별 폐업률 없음')}"
    first, last = rows[0], rows[-1]
    partial = "(올해 현재까지)" if str(last["year"]) == current_year else ""
    line = (
        f"{FACT} {region} {industry} 연간 폐업률: {first['year']}년 {first['closure_rate'] * 100:.1f}% → "
        f"{last['year']}년{partial} {last['closure_rate'] * 100:.1f}%(점포 {first['store_count']}곳 → {last['store_count']}곳)."
    )
    return line + (f" {_DISASTER_NOTE}" if any(r["year"] in _DISASTER_YEARS for r in rows) else "")


def _shocks(shocks: object, industry: str) -> str:
    reason = _missing_reason(shocks)
    if reason is not None or not shocks:
        return f"{FACT} 외부 충격({industry}): {missing(reason or '기록 없음')}"
    scope = _SHOCK_SCOPES[bool(shocks[0].get("industry_specific"))].format(industry=industry)
    names = ", ".join(f"{s['name'].split(' — ')[0]}({str(s.get('start_date'))[:4]}년)" for s in shocks)
    return f"{FACT} 외부 충격({scope}): {names}."


def _reasons(facts: dict) -> str:
    region, industry = _names(facts)
    return "\n\n".join(
        [
            _signals(facts.get("verdict") or {}, region, industry),
            _closure_trend(facts.get("metrics_history"), region, industry, _current_year(facts)),
            _shocks(facts.get("shocks"), industry),
        ]
    )


# ── 유사 사례 ────────────────────────────────────────────────


def _category_paragraph(analogs: dict, category: str) -> str:
    """한 유형 = 한 문단 — 사례·종합 고정 문장([확인된 사실]) 뒤에 그 유형의 최근 조치 소식([참고 신호]).

    소식이 없으면(기사 0건·확인 못 함) 줄을 생략한다 — "없다"고 쓰지 않는다(설계서 §4).
    """
    events = [*(analogs.get("current_events") or []), *(analogs.get("analogs") or [])]
    outlook = next((o for o in analogs.get("outlooks") or [] if o.get("category") == category), {})
    sentences = [
        *(s for e in events if e.get("category") == category for s in (e.get("summary_sentence"), e.get("overlap_sentence")) if s),
        *(s for s in (outlook.get("condition_sentence"), outlook.get("recommended_sentence")) if s),
    ]
    news = [r["sentence"] for r in analogs.get("recent_news") or [] if r.get("category") == category and r.get("article_count")]
    parts = [*([f"{FACT} " + " ".join(sentences)] if sentences else []), *([f"{SIGNAL} " + " ".join(news)] if news else [])]
    return " ".join(parts)


def _show_industry_name(text: str, industry_id: str, industry: str) -> str:
    """문장 속 업종 id를 업종 이름으로 — 고정 문장에 박혀 온 주제 조사 '는'은 받침에 맞춰 '은'으로 고친다."""
    topic = "은" if (ord(industry[-1]) - 0xAC00) % 28 else "는"
    return text.replace(f"{industry_id}는", f"{industry}{topic}").replace(industry_id, industry)


def _analogs(facts: dict) -> str:
    _, industry = _names(facts)
    analogs = facts.get("analogs") or {}
    reason = _missing_reason(analogs)
    if reason is not None:
        return f"{FACT} 유사 사례(서울 전체 {industry}): {missing(reason)}"
    # 질문 속 상황 유형을 먼저, 운영자가 등록한 진행 중 유형을 뒤에
    categories = sorted(analogs.get("categories") or [], key=lambda c: c.get("reason") != "question")
    # 고정 문장에 업종 id가 그대로 박혀 오는 경우가 있다 — 사용자에게는 업종 이름을 보인다
    industry_id = (facts.get("region") or {}).get("industry_id")
    paragraphs = [
        _show_industry_name(p, industry_id, industry) if industry_id else p
        for p in (_category_paragraph(analogs, c.get("category")) for c in categories)
        if p
    ]
    return "\n\n".join(paragraphs) or f"{FACT} 서울 전체 {industry}: 비교할 과거 사례가 없습니다."


# ── 그래도 한다면 ────────────────────────────────────────────


def hour_gap_sentence(bands: list[dict]) -> str | None:
    """어긋남 문장 — 프론트 `hourGapSentence`와 같은 규칙. gap 부호가 아니라 두 최대 구간의 위치로 말한다.

    동점은 앞 구간(원천 순서) — `max`는 첫 최대를 고른다.
    """
    if not bands:
        return None
    people = max(bands, key=lambda b: b["footfall_intensity"])["hour_band"]
    money = max(bands, key=lambda b: b["sales_intensity"])["hour_band"]
    if people == money:
        return f"사람과 돈이 {HOUR_BAND_LABELS.get(people, people)}에 같이 몰립니다."
    return f"사람은 {HOUR_BAND_LABELS.get(people, people)}에 가장 많고, 돈은 {HOUR_BAND_LABELS.get(money, money)}에 돕니다."


def _hours(hour_gap: dict, region: str, industry: str) -> str:
    if not hour_gap.get("available"):
        # 이유 뒤 ": 동코드 × 업종 id" 같은 내부 코드는 사용자에게 보이지 않는다
        reason = (hour_gap.get("reason") or "").split(":")[0].strip()
        return f"{FACT} 시간대({region} {industry}): {missing(reason)}"
    sentence = hour_gap_sentence(hour_gap.get("bands") or []) or missing("시간대 구간 없음")
    return f"{FACT} 시간대({region} 유동인구·{industry} 매출, {_quarter(hour_gap.get('year_quarter'))}): {sentence}"


def _profile(profile: dict, region: str) -> str:
    reason = _missing_reason(profile)
    if reason is not None:
        return f"{FACT} 동네 유형({region}): {missing(reason)}"
    # 흐름 이름이 가장 많은 때와 같으면 같은 말을 두 번 하지 않는다
    label = profile.get("time_label_name")
    flow = "" if label == profile.get("peak_block_name") else f"{label} — "
    return (
        f"{FACT} 동네 유형({region}, {_quarter(profile.get('year_quarter'))}): {profile.get('type_name')} — "
        f"{profile.get('type_reason')} 사람 흐름: {flow}가장 많은 때 "
        f"{profile.get('peak_block_name')}, 가장 적은 때 {profile.get('trough_block_name')}."
    )


def _staying(change: dict, region: str) -> str:
    reason = _missing_reason(change)
    if reason is not None:
        return f"{FACT} 상권 영업 기간({region}): {missing(reason)}"
    seoul = change.get("seoul") or {}
    return (
        f"{FACT} 상권 영업 기간({region} 상권 전체·업종 무관, {_quarter(change.get('year_quarter'))}): "
        f"영업 중 점포 평균 {change['operating_months']:.0f}개월, 폐업 점포 평균 {change['closed_months']:.0f}개월 — "
        f"서울 동 상권 전체 기준값은 {seoul['operating_months']:.0f}개월·{seoul['closed_months']:.0f}개월입니다. "
        f"상권변화지표: {change.get('change_name')}."
    )


def _conditions(facts: dict) -> str:
    region, industry = _names(facts)
    lines = [
        _hours(facts.get("hour_gap") or {}, region, industry),
        _profile(facts.get("profile") or {}, region),
        _staying(facts.get("commerce_change") or {}, region),
        *([_BUDGET_LINE] if facts.get("budget") is not None else []),
    ]
    return "\n\n".join(lines)


# ── 대안 ─────────────────────────────────────────────────────


def _axis(items: list[dict] | None, name_key: str) -> list[str]:
    """한 축의 목록 — 순서 그대로 최대 3개, 등급 라벨 그대로. 비어 있으면 '대안 없음' 한 줄."""
    if not items:
        return ["- 대안 없음"]
    return [
        f"- {item.get(name_key)} ({_VERDICT_LABELS.get(item.get('verdict_code'), item.get('verdict_code'))})"
        for item in items[:_MAX_PER_AXIS]
    ]


def _alternatives(facts: dict) -> str:
    region, industry = _names(facts)
    alternatives = facts.get("alternatives") or {}
    if not alternatives.get("available"):
        return f"{FACT} 대안({region} {industry}): {missing(alternatives.get('reason'))}"
    return "\n".join(
        [
            f"{FACT} 같은 동네({region})의 다른 업종",
            *_axis(alternatives.get("industries"), "industry_name"),
            "",
            f"{FACT} 같은 업종({industry})의 다른 동네",
            *_axis(alternatives.get("regions"), "region_name"),
        ]
    )


# ── 지원사업 ─────────────────────────────────────────────────


def _due(candidate: dict) -> str:
    """마감일이 있으면 마감, 없으면 접수 기간 원문("예산 소진시까지"·"상시 접수")."""
    if candidate.get("deadline"):
        return f"마감 {candidate['deadline']}"
    period = candidate.get("apply_period") or "기간 미상"
    return period if period.startswith("상시") else f"접수 {period}"


def _funding(facts: dict) -> str:
    region, industry = _names(facts)
    candidates = facts.get("funding_candidates")
    reason = _missing_reason(candidates)
    if reason is not None:
        return f"{FACT} 지원사업 후보({region} {industry}): {missing(reason)}\n\n{FUNDING_DISCLAIMER}"
    if not candidates:
        return f"{FACT} {region} {industry} 조건에 맞는 공고 후보가 없습니다.\n\n{FUNDING_DISCLAIMER}"
    # 공고 제목은 원문 그대로 「」에 담는다 — 링크·공고 번호는 화면 카드가 보여 준다
    lines = [f"- 「{c.get('title')}」 — {c.get('org')}, {_due(c)}" for c in candidates]
    head = (
        f"{FACT} {region} {industry} 조건으로 찾은 공고 후보입니다 — 자격 확정이 아니라 해당 가능성이며, "
        "지원 대상은 공고 원문에서 확인해야 합니다."
    )
    return "\n\n".join([head, "\n".join(lines), FUNDING_DISCLAIMER])


# 절 이름 → 작성 함수 (dict 디스패치)
_WRITERS = {
    "verdict": _verdict,
    "reasons": _reasons,
    "analogs": _analogs,
    "conditions": _conditions,
    "alternatives": _alternatives,
    "funding": _funding,
}


def build_sections(facts: dict) -> dict[str, str]:
    """facts → {절 이름: 마크다운}. `SECTION_TITLES` 순서, 절마다 `### 제목` 머리 + 본문."""
    return {name: f"### {title}\n\n{_WRITERS[name](facts)}" for name, title in SECTION_TITLES.items()}
