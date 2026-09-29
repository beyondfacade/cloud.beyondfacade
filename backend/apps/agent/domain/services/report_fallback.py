"""판정·대안 절을 facts 값만으로 쓰는 순수 포매터 (stdlib만 import).

LLM이 두 절을 빼먹어도 판정은 화면에 나가야 한다 — 판정은 규칙이 내리고 문장만 LLM이 쓴다
(설계서 §2-4). 나머지 절은 근거 해석이라 LLM이 없으면 쓸 말이 없지만, 이 둘은 facts를 그대로
옮기는 절이라 코드가 쓸 수 있다.
"""

_MAX_PER_AXIS = 3  # 두 축 각 최대 3개 (설계서 §3 alternatives 계약)

# 판정 코드 → 사람이 읽는 라벨. 프론트 `shared/verdict.ts`의 LABELS와 같은 어휘다.
_VERDICT_LABELS = {
    "red": "비추천",
    "orange": "조건부",
    "clear": "경고 없음",
    "insufficient": "판정 보류",
}

_FIRED_LEVELS = ("on", "strong")


def verdict_markdown(verdict: dict | None) -> str | None:
    """facts.verdict → 판정 절. 사실 자체가 없으면 None(일반 폴백 문구로 넘긴다)."""
    if not verdict:
        return None
    if not verdict.get("available"):
        return f"### 판정\n\n판정 없음 — {verdict.get('reason') or '이유 없음'}"
    signals = verdict.get("signals") or []
    fired = [s for s in signals if s.get("level") in _FIRED_LEVELS and not s.get("advisory")]
    advisory = [s for s in signals if s.get("level") in _FIRED_LEVELS and s.get("advisory")]
    label = _VERDICT_LABELS.get(verdict.get("verdict_code"), verdict.get("verdict_code"))
    lines = [
        "### 판정",
        "",
        f"**{label}** — 켜진 신호 {verdict.get('on_count', 0)}개"
        f"(강한 경고 {verdict.get('strong_count', 0)}개).",
    ]
    lines.extend(f"- {s.get('evidence')}" for s in fired)
    if not fired:
        lines.append("켜진 신호 없음.")
    lines.extend(f"참고: {s.get('evidence')}" for s in advisory)
    lines.append(f"산출일 {verdict.get('computed_at')}")
    return "\n".join(lines)


def alternatives_markdown(alternatives: dict | None) -> str | None:
    """facts.alternatives → 대안 절. 사실 자체가 없으면 None."""
    if not alternatives:
        return None
    if not alternatives.get("available"):
        return f"### 대안 동네·업종\n\n대안 없음 — {alternatives.get('reason') or '이유 없음'}"
    return "\n".join(
        [
            "### 대안 동네·업종",
            "",
            "**같은 동네의 다른 업종**",
            *_axis(alternatives.get("industries"), "industry_name"),
            "",
            "**같은 업종의 다른 동네**",
            *_axis(alternatives.get("regions"), "region_name"),
        ]
    )


def _axis(items: list[dict] | None, name_key: str) -> list[str]:
    """한 축의 목록 줄 — 순서 그대로 최대 3개. 비어 있으면 '대안 없음' 한 줄."""
    if not items:
        return ["대안 없음"]
    return [
        f"- {item.get(name_key)} ({_VERDICT_LABELS.get(item.get('verdict_code'), item.get('verdict_code'))})"
        for item in items[:_MAX_PER_AXIS]
    ]
