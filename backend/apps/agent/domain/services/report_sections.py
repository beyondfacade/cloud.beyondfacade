"""리포트 6개 절을 facts만으로 쓰는 순수 모듈 (stdlib만 import).

설계서 docs/superpowers/specs/2026-10-05-report-code-first-design.md §4 — 결론과 수치는 코드가 사실에서 쓰고,
LLM은 맨 위 해석(answer) 한 단락만 쓴다. 원칙:
① 숫자에는 범위(무엇의·어디의·언제의)를 붙인다 — 줄마다 동·업종 이름이나 "서울"을 적는다.
② 자료가 없으면 "자료 부족 — 이유"를 쓰고 추정으로 메우지 않는다.
③ 신뢰 태그는 코드가 붙인다 — 정형 값 [확인된 사실]. 뉴스는 본문에 넣지 않는다(네이버 검색 결과는 화면 링크로만).
④ 화면 차트와 같은 규칙을 쓴다 — 시간대 문장은 프론트 `hour-gap-sentence.ts`와 같은 규칙.
"""

import logging

from apps.agent.domain.services.report_guards import FUNDING_DISCLAIMER

LOGGER = logging.getLogger(__name__)

FACT = "[확인된 사실]"

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
VERDICT_LABELS = {"red": "비추천", "orange": "조건부", "clear": "경고 없음", "insufficient": "판정 보류"}
# 신호 키 → 이름. 프론트 `shared/verdict.ts` SIGNAL_LABELS와 같은 어휘다.
SIGNAL_LABELS = {
    "net_outflow": "순유출",
    "survival_cliff": "생존 절벽",
    "early_closure": "조기 폐업",
    "saturation": "포화",
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
DISASTER_NOTE = "2020~2022년 폐업률은 재난지원금·손실보상으로 폐업이 늦춰져 왜곡됐을 수 있습니다."
_DISASTER_YEAR_NOTE = "(재난지원 시기 — 폐업이 늦춰져 왜곡됐을 수 있음)"
_BUDGET_LINE = f"{FACT} 입력한 예산으로 총 준비자금·조달 필요액·손익분기 매출을 계산하려면 자금 계획 화면을 이용하세요."
# 충격 목록이 이 업종 것인지(True) 전 업종 공통으로 되돌린 것인지(False) — report_facts._shocks가 정한다
_SHOCK_SCOPES = {True: "{industry}에 영향을 준 충격", False: "{industry} 전용 기록은 없어 전 업종 공통 충격"}


def missing(reason: str | None) -> str:
    return f"자료 부족 — {reason or '이유 미상'}"


def missing_reason(value: object) -> str | None:
    """수집 실패·판정 불가 자리(`{"available": False, "reason": ...}`)면 그 이유, 아니면 None.

    목록 자리(지표 이력·충격·공고)도 실패하면 이 dict가 온다 — 모양을 보고 가른다.
    """
    if isinstance(value, dict) and value.get("available") is False:
        return value.get("reason") or "이유 미상"
    return None


def subject_names(facts: dict) -> tuple[str, str]:
    region = facts.get("region") or {}
    return region.get("name") or "이 동", region.get("industry_name") or "이 업종"


def quarter_label(year_quarter: str | None) -> str:
    """'20262' → '2026년 2분기'."""
    return f"{year_quarter[:4]}년 {year_quarter[4:]}분기" if year_quarter else "최신 분기"


# ── 판정 ─────────────────────────────────────────────────────


def _verdict(facts: dict) -> str:
    region, industry = subject_names(facts)
    verdict = facts.get("verdict") or {}
    if not verdict.get("available"):
        return f"{FACT} {region} {industry} 판정: {missing(verdict.get('reason'))}"
    judged = [s for s in verdict.get("signals") or [] if not s.get("advisory")]
    label = VERDICT_LABELS.get(verdict.get("verdict_code"), verdict.get("verdict_code"))
    # 꺼진 신호와 계산 못 한 신호를 한 줄로 묶으면 해석이 "경고 없음은 자료가 비어서"로 읽었다 — 이름까지 나눠 쓴다
    groups = (("off", "계산했지만 기준을 넘지 않은 신호"), ("unavailable", "자료 부족으로 계산하지 못한 신호"))
    parts = [
        f"{FACT} {region} {industry} 판정: **{label}** — 경고 신호 {len(judged)}개 중 "
        f"{verdict.get('on_count', 0)}개 켜짐(강한 신호 {verdict.get('strong_count', 0)}개).",
        *(
            f"{title} {len(group)}개({'·'.join(SIGNAL_LABELS.get(s.get('key'), s.get('key')) for s in group)})."
            for level, title in groups
            if (group := [s for s in judged if s.get("level") == level])
        ),
        f"산출 {str(verdict.get('computed_at') or '')[:10]}.",
    ]
    return " ".join(parts)


# ── 왜 안 되나 ───────────────────────────────────────────────

# 참고 신호(advisory) 여부 → 줄 모양 (if/elif 대신 테이블 디스패치). 꺼진 신호는 쓰지 않는다.
# 켜진 신호와 표본 부족 신호는 같은 모양이다 — 표본 부족은 evidence가 "표본 부족 — …"으로 이유를 말한다.
_SIGNAL_LINES = {
    False: lambda name, evidence, where: f"- {FACT} {name}({where}): {evidence}",
    True: lambda name, evidence, where: f"- {FACT} 참고 — {name}: {evidence}",
}


# 이름만으로 헷갈리는 두 신호의 뜻 — 한쪽이 표본 부족이면 LLM이 다른 쪽 수치로 메웠다(12b 4건)
_SIGNAL_MEANINGS = {
    "survival_cliff": "3년 전 새로 연 점포 중 지금 남은 비율",
    "early_closure": "최근 3년 문 닫은 점포가 문 닫기 전까지 영업한 기간, 새로 연 점포의 생존율이 아님",
}


def _signals(verdict: dict, region: str, industry: str) -> str:
    if not verdict.get("available"):
        return f"{FACT} 경고 신호({region} {industry}): {missing(verdict.get('reason'))}"
    where = f"{region} {industry}"
    lines = [
        _SIGNAL_LINES[bool(s.get("advisory"))](
            SIGNAL_LABELS.get(s.get("key"), s.get("key")),
            s.get("evidence"),
            f"{where} — {_SIGNAL_MEANINGS[s.get('key')]}" if s.get("key") in _SIGNAL_MEANINGS else where,
        )
        for s in verdict.get("signals") or []
        if s.get("level") != "off"
    ]
    return "\n".join(lines) or f"{FACT} {where}: 켜진 경고 신호 없음."


def current_year(facts: dict) -> str | None:
    """사실 묶음의 기준 연도 — 분기 자료('20262')의 연도. 이 해의 폐업률은 아직 진행 중인 부분 연도다."""
    for key in ("commerce_change", "profile"):
        year_quarter = (facts.get(key) or {}).get("year_quarter")
        if year_quarter:
            return year_quarter[:4]
    return None


def _closure_trend(history: object, region: str, industry: str, current_year: str | None) -> str:
    reason = missing_reason(history)
    rows = [r for r in history or [] if r.get("closure_rate") is not None] if reason is None else []
    if not rows:
        return f"{FACT} {region} {industry} 연간 폐업률: {missing(reason or '연도별 폐업률 없음')}"
    # 점포 수·폐업률 모두 해마다 싣는다 — 첫해·끝해 두 점만 주면 LLM이 "꾸준히 증가"로 옮겼다
    years = " · ".join(_year_line(r, current_year) for r in sorted(rows, key=lambda r: r["year"]))
    return f"{FACT} {region} {industry} 점포 수·연간 폐업률(해마다): {years}."


def _year_line(row: dict, current_year: str | None) -> str:
    """한 해 점포 수·폐업률 — 재난지원 해면 단서를 바로 옆에 붙인다. 문장 끝에 두면 LLM이 다른 해 수치에도 옮겨 붙인다."""
    partial = "(올해 현재까지)" if str(row["year"]) == current_year else ""
    note = _DISASTER_YEAR_NOTE if row["year"] in _DISASTER_YEARS else ""
    return f"{row['year']}년{partial} 점포 {row['store_count']}곳·폐업률 {row['closure_rate'] * 100:.1f}%{note}"


def _shocks(shocks: object, industry: str) -> str:
    reason = missing_reason(shocks)
    if reason is not None or not shocks:
        return f"{FACT} 외부 충격({industry}): {missing(reason or '기록 없음')}"
    scope = _SHOCK_SCOPES[bool(shocks[0].get("industry_specific"))].format(industry=industry)
    names = ", ".join(f"{s['name'].split(' — ')[0]}({str(s.get('start_date'))[:4]}년)" for s in shocks)
    return f"{FACT} 외부 충격({scope}): {names}."


def _reasons(facts: dict) -> str:
    region, industry = subject_names(facts)
    return "\n\n".join(
        [
            _signals(facts.get("verdict") or {}, region, industry),
            _closure_trend(facts.get("metrics_history"), region, industry, current_year(facts)),
            _shocks(facts.get("shocks"), industry),
        ]
    )


# ── 유사 사례 ────────────────────────────────────────────────


def _category_paragraph(analogs: dict, category: str) -> str:
    """한 유형 = 한 문단 — 사례·종합 고정 문장([확인된 사실]). 최근 조치 뉴스는 네이버 검색 결과라
    본문(LLM 입력)에 넣지 않고 화면 링크로만 보여 준다(검색 API 특약 2.3).
    """
    events = [*(analogs.get("current_events") or []), *(analogs.get("analogs") or [])]
    outlook = next((o for o in analogs.get("outlooks") or [] if o.get("category") == category), {})
    sentences = [
        *(s for e in events if e.get("category") == category for s in (e.get("summary_sentence"), e.get("overlap_sentence")) if s),
        *(s for s in (outlook.get("condition_sentence"), outlook.get("recommended_sentence")) if s),
    ]
    return f"{FACT} " + " ".join(sentences) if sentences else ""


def topic_particle(word: str) -> str:
    """주제 조사 — 받침이 있으면 '은', 없으면 '는'."""
    return "은" if (ord(word[-1]) - 0xAC00) % 28 else "는"


def _show_industry_name(text: str, industry_id: str, industry: str) -> str:
    """문장 속 업종 id를 업종 이름으로 — 고정 문장에 박혀 온 주제 조사 '는'은 받침에 맞춰 '은'으로 고친다."""
    return text.replace(f"{industry_id}는", f"{industry}{topic_particle(industry)}").replace(industry_id, industry)


def _analogs(facts: dict) -> str:
    _, industry = subject_names(facts)
    analogs = facts.get("analogs") or {}
    reason = missing_reason(analogs)
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
        return f"사람(유동인구)과 매출이 모두 {HOUR_BAND_LABELS.get(people, people)}에 가장 많습니다."
    # 사람과 매출을 두 문장으로 나눈다 — 한 문장이면 LLM이 둘을 한 구간으로 합쳐 옮긴다
    return (
        f"사람(유동인구)이 가장 많은 때는 {HOUR_BAND_LABELS.get(people, people)}입니다. "
        f"매출이 가장 많은 때는 {HOUR_BAND_LABELS.get(money, money)}으로, 사람이 가장 많은 때와 다릅니다."
    )


def _hours(hour_gap: dict, region: str, industry: str) -> str:
    if not hour_gap.get("available"):
        # 이유 뒤 ": 동코드 × 업종 id" 같은 내부 코드는 사용자에게 보이지 않는다
        reason = (hour_gap.get("reason") or "").split(":")[0].strip()
        return f"{FACT} 시간대({region} {industry}): {missing(reason)}"
    sentence = hour_gap_sentence(hour_gap.get("bands") or []) or missing("시간대 구간 없음")
    return f"{FACT} 시간대({region} 유동인구·{industry} 매출, {quarter_label(hour_gap.get('year_quarter'))}): {sentence}"


def _profile(profile: dict, region: str) -> str:
    reason = missing_reason(profile)
    if reason is not None:
        return f"{FACT} 동네 유형({region}): {missing(reason)}"
    # 흐름 이름이 가장 많은 때와 같으면 같은 말을 두 번 하지 않는다
    label = profile.get("time_label_name")
    flow = "" if label == profile.get("peak_block_name") else f"{label} — "
    return (
        f"{FACT} 동네 유형({region}, {quarter_label(profile.get('year_quarter'))}): {profile.get('type_name')} — "
        f"{profile.get('type_reason')} 사람 흐름: {flow}가장 많은 때 "
        f"{profile.get('peak_block_name')}, 가장 적은 때 {profile.get('trough_block_name')}."
    )


def _staying(change: dict, region: str) -> str:
    reason = missing_reason(change)
    if reason is not None:
        return f"{FACT} 상권 영업 기간({region}): {missing(reason)}"
    seoul = change.get("seoul") or {}
    return (
        f"{FACT} 상권 영업 기간({region} 상권 전체·업종 무관, {quarter_label(change.get('year_quarter'))}): "
        f"영업 중 점포 평균 {change['operating_months']:.0f}개월, 폐업 점포 평균 {change['closed_months']:.0f}개월 — "
        f"서울 동 상권 전체 기준값은 {seoul['operating_months']:.0f}개월·{seoul['closed_months']:.0f}개월입니다. "
        f"상권변화지표: {change.get('change_name')}."
    )


def resident_line(facts: dict) -> str:
    """주민 연령 구성(주민등록)과 아파트 평균 시가(참고값) — 사람 검수 "거주민 생활수준" 메모(설계서 §6)."""
    region, _ = subject_names(facts)
    population = facts.get("population") or {}
    ages = population.get("age_distribution") or {}
    total = sum(ages.values())
    reason = missing_reason(population)
    if reason is not None or not total:
        head = f"{FACT} 주민({region}): {missing(reason or '연령별 인구 없음')}"
    else:
        old = sum(v for k, v in ages.items() if int(k) >= 60) / total
        young = sum(v for k, v in ages.items() if 20 <= int(k) < 40) / total
        period = str(population.get("period") or "")
        head = (
            f"{FACT} 주민({region}, {period[:4]}년 {int(period[4:])}월 주민등록): "
            f"60세 이상 {old * 100:.0f}%, 20~39세 {young * 100:.0f}%"
        )
    price = (facts.get("profile") or {}).get("apartment_avg_price_won")
    tail = f" · 아파트 평균 시가 약 {price / 100_000_000:.1f}억 원(동별 편차가 커 참고값입니다)" if price else ""
    return f"{head}{tail}."


def _conditions(facts: dict) -> str:
    region, industry = subject_names(facts)
    lines = [
        _hours(facts.get("hour_gap") or {}, region, industry),
        _profile(facts.get("profile") or {}, region),
        _staying(facts.get("commerce_change") or {}, region),
        resident_line(facts),
        *([_BUDGET_LINE] if facts.get("budget") is not None else []),
    ]
    return "\n\n".join(lines)


# ── 대안 ─────────────────────────────────────────────────────


def _axis(items: list[dict] | None, name_key: str) -> list[str]:
    """한 축의 목록 — 순서 그대로 최대 3개, 등급 라벨 그대로. 비어 있으면 '대안 없음' 한 줄."""
    if not items:
        return ["- 대안 없음"]
    return [
        f"- {item.get(name_key)} ({VERDICT_LABELS.get(item.get('verdict_code'), item.get('verdict_code'))})"
        for item in items[:_MAX_PER_AXIS]
    ]


def _alternatives(facts: dict) -> str:
    region, industry = subject_names(facts)
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
    region, industry = subject_names(facts)
    candidates = facts.get("funding_candidates")
    reason = missing_reason(candidates)
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


# ── 자료 부족 동네 — 해석 첫 문장은 코드가 쓴다 ─────────────

# 계산하지 못한 판정 신호 키 → 첫 문장에 쓸 짧은 항목명(숫자 없이). 없는 키는 신호 이름으로 쓴다.
_MISSING_SIGNAL_LABELS = {
    "net_outflow": "폐업·개업 흐름",
    "survival_cliff": "개업 점포 생존율",
    "early_closure": "폐업 점포 영업 기간",
    "saturation": "점포 밀도",
}
# 수집하지 못한 사실 키 → 짧은 항목명. 이 순서로 적는다(이유 원문·내부 코드는 첫 문장에 쓰지 않는다).
_MISSING_FACT_LABELS = {
    "metrics_history": "연도별 폐업률",
    "shocks": "외부 충격",
    "analogs": "유사 사례",
    "hour_gap": "시간대별 매출",
    "profile": "동네 유형",
    "commerce_change": "상권 영업 기간",
    "alternatives": "대안 동네·업종",
    "funding_candidates": "지원사업 후보",
}
# 판정 자료가 있는가 → 고정 첫 문장 (판정 보류는 부족한 자료를, 판정을 내리지 않는 업종은 그 사실을 말한다)
_SCARCE_LEADS = {
    True: lambda subject, items: (
        f"{FACT} {subject} 자료가 부족해 진입 판단을 내리기 어렵습니다 — 부족한 자료: {', '.join(items)}."
    ),
    False: lambda subject, items: (
        f"{FACT} {subject} 경고 판정을 내리는 업종이 아니어서 진입 판단을 내리지 않습니다 — 아래 사실만 참고하세요."
    ),
}


def scarcity(facts: dict) -> list[str] | None:
    """자료 부족 동네(판정을 내리지 않는 업종·판정 보류)면 부족한 자료의 짧은 항목명 목록, 아니면 None.

    목록: 계산하지 못한 판정 신호 → 수집하지 못한 사실 항목. 판정을 내리지 않는 업종이면 빌 수 있다.
    """
    verdict = facts.get("verdict") or {}
    if verdict.get("available") and verdict.get("verdict_code") != "insufficient":
        return None
    signals = [
        _MISSING_SIGNAL_LABELS.get(s.get("key"), SIGNAL_LABELS.get(s.get("key"), s.get("key")))
        for s in verdict.get("signals") or []
        if s.get("level") == "unavailable"
    ]
    items = [label for key, label in _MISSING_FACT_LABELS.items() if missing_reason(facts.get(key)) is not None]
    return list(dict.fromkeys([*signals, *items]))


def scarce_lead(facts: dict, missing_items: list[str]) -> str:
    """자료 부족 동네 해석의 고정 첫 문장 — 결론은 틀리면 안 되므로 코드가 쓴다. 숫자는 쓰지 않는다."""
    region, industry = subject_names(facts)
    available = bool((facts.get("verdict") or {}).get("available"))
    return _SCARCE_LEADS[available](f"{region} {industry}{topic_particle(industry)}", missing_items)


def alternatives_pointer(facts: dict) -> str | None:
    """대안 절에 경고 없음이 한 곳이라도 있으면 그 절을 가리키는 고정 문장, 아니면 None. 추천은 하지 않는다."""
    alternatives = facts.get("alternatives") or {}
    if not alternatives.get("available"):
        return None
    items = [*(alternatives.get("industries") or []), *(alternatives.get("regions") or [])]
    if any(item.get("verdict_code") == "clear" for item in items):
        return "대안 동네·업종 절에 경고 없음으로 나온 곳도 함께 확인해 보세요."
    return None


# 절 이름 → 작성 함수 (dict 디스패치)
_WRITERS = {
    "verdict": _verdict,
    "reasons": _reasons,
    "analogs": _analogs,
    "conditions": _conditions,
    "alternatives": _alternatives,
    "funding": _funding,
}


def _write(name: str, facts: dict) -> str:
    """절 하나 — 빈 값 등으로 작성 함수가 예외를 내면 그 절만 "자료 부족" 줄로 쓴다(리포트 전체를 끊지 않는다)."""
    try:
        return _WRITERS[name](facts)
    except Exception:
        LOGGER.exception("코드 절 작성 실패 — %s", name)  # 사용자에겐 자료 부족 줄, 원인은 로그로
        return f"{FACT} {missing('일부 값이 비어 이 절을 쓰지 못함')}"


def build_sections(facts: dict) -> dict[str, str]:
    """facts → {절 이름: 마크다운}. `SECTION_TITLES` 순서, 절마다 `### 제목` 머리 + 본문."""
    return {name: f"### {title}\n\n{_write(name, facts)}" for name, title in SECTION_TITLES.items()}
