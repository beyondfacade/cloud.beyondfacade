"""리포트 출력 코드 가드 — LLM 본문이 화면에 나가기 전에 코드가 지키는 선 (stdlib만 import).

LLM 평가(2026-10-05)에서 리포트 실패의 상당 부분은 "화면이 이미 보여 주는 값을 글로 옮기다 틀리는"
문제였다. 판정 등급 배지와 지원사업 원문 링크는 화면이 facts로 직접 그리므로, 글에서는 코드가 막는다.

- **판정 모순 교체**: 판정 절은 절이 끝날 때 한 번에 내보낸다(프론트 리듀서가 append라 이미 흘린
  조각은 되돌릴 수 없다). facts와 다른 등급을 단정하면 facts로 쓴 판정 절로 바꾼다.
- **링크·공고 번호 제거**: 모든 절에서 URL·bizinfo 공고 번호를 지운다. 조각 경계에서 잘린 URL은
  꼬리를 붙들었다가 다음 조각과 합쳐 판단한다.
- **기본 신뢰 태그**: 사실 절의 본문이 태그로 시작하지 않으면 `[확인된 사실]`을 붙인다.
- **예상치 고지**: 지원사업 절 끝에 금리·한도 예상치 고지문을 덧붙인다(이미 있으면 그대로).
"""

import re
from collections.abc import Callable

# ── 판정 등급 동의어 (벤치 채점과 같은 단일 원천) ──────────────────

# 판정 그룹별 동의어(공백 제거·소문자 기준으로 비교). 그룹 하나가 한 등급의 표현이다.
VERDICT_SYNONYMS = {
    "red": ("비추천", "빨강", "빨간", "레드", "red", "적색"),
    "orange": ("조건부", "주황", "오렌지", "orange", "'주의' 등급", "주의 등급"),
    "clear": ("경고 없", "경고가 없", "위험 신호가 없", "위험 신호도 켜지지 않", "clear"),
    "unavailable": ("판정 없음", "판정 보류", "판정할 수 없", "판정하지 않", "판정을 내리지 않", "insufficient"),
}
_VERDICT_GROUP = {"insufficient": "unavailable"}  # verdict_code → 동의어 그룹(나머지는 코드가 곧 그룹)


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


_SQUASHED_SYNONYMS = {group: tuple(_squash(w) for w in words) for group, words in VERDICT_SYNONYMS.items()}


def verdict_matches(verdict_section_md: str, verdict_facts: dict) -> bool:
    """판정 절이 facts 판정과 모순되지 않는가 — 다른 등급의 동의어를 단정하지 않으면 통과.

    등급 말을 아예 안 쓴 절(생략)은 모순이 아니다. 판정 자료가 없으면(available False)
    unavailable 그룹이 기대 등급이며, 비추천·조건부·경고 없음 계열 말은 모두 모순이다.
    """
    text = _squash(verdict_section_md)
    code = verdict_facts.get("verdict_code") if verdict_facts.get("available") else "unavailable"
    group = _VERDICT_GROUP.get(code, code)
    if group not in _SQUASHED_SYNONYMS:
        return False
    return not any(w in text for g, words in _SQUASHED_SYNONYMS.items() if g != group for w in words)


def verdict_states_grade(verdict_section_md: str) -> bool:
    """판정 절이 어느 등급이든 등급 말(동의어)을 쓰는가 — 생략 건수를 세는 참고 지표."""
    text = _squash(verdict_section_md)
    return any(w in text for words in _SQUASHED_SYNONYMS.values() for w in words)


def contradicts_verdict(text: str, verdict_facts: dict | None) -> bool:
    """판정 절이 facts와 다른 등급을 단정하는가. 대조할 판정 자료가 없으면 모순이 아니다."""
    return bool(verdict_facts) and not verdict_matches(text, verdict_facts)


# ── 링크·공고 번호 제거 ──────────────────────────────────────────

# URL은 ASCII 문자로만 이어진다고 본다 — 붙어 오는 한글 조사("…/x에서")와 괄호는 URL이 아니다.
_URL_CHAR = r"[A-Za-z0-9\-._~:/?#@!$&'*+,;=%]"
_URL_END = r"[A-Za-z0-9\-_~/#@$&*+=%]"  # 문장 끝 마침표·쉼표는 URL에 넣지 않는다
_URL_BODY = rf"(?:{_URL_CHAR}*{_URL_END})?"
_LINK = re.compile(
    rf"[ \t]*(?:https?://{_URL_BODY}|www\.{_URL_BODY}|PBLN_\d+|pblancId=[A-Za-z0-9_]*)"
)
_LINK_STARTS = ("https://", "http://", "www.", "PBLN_", "pblancId=")
# 꼬리가 아직 끝나지 않은 링크 — 다음 조각에서 더 이어질 수 있다.
_OPEN_LINK = re.compile(rf"(?:https?://|www\.|PBLN_|pblancId=){_URL_CHAR}*$")
# 링크 앞에 붙은 여는 괄호·공백 — 링크를 지우면 빈 괄호로 남으므로 함께 붙든다.
_BEFORE_LINK = re.compile(r"[ \t]*[(\[]?$")
_EMPTY_BRACKETS = re.compile(r"[ \t]*(?:\(\s*\)|\[\s*\])")


def strip_links(text: str) -> str:
    """URL·공고 번호를 지우고, 지운 자리에 남은 빈 괄호를 정리한다."""
    return _EMPTY_BRACKETS.sub("", _LINK.sub("", text))


def _hold_from(text: str) -> int:
    """붙들기 시작할 위치 — 끝나지 않은 링크나 링크 시작의 앞부분, 그 앞 괄호·공백까지."""
    open_link = _OPEN_LINK.search(text)
    edge = open_link.start() if open_link else len(text) - _partial_start_length(text)
    return _BEFORE_LINK.search(text[:edge]).start()


def _partial_start_length(text: str) -> int:
    """꼬리가 링크 시작(`https://`·`www.`·`PBLN_`…)의 앞부분이면 그 길이, 아니면 0."""
    return max(
        (n for start in _LINK_STARTS for n in range(1, len(start)) if text.endswith(start[:n])),
        default=0,
    )


class UrlStripper:
    """조각 스트림에서 링크를 지우는 필터. 남은 꼬리는 `flush()`로 비운다."""

    def __init__(self) -> None:
        self._tail = ""

    def feed(self, chunk: str) -> str:
        text = self._tail + chunk
        edge = _hold_from(text)
        self._tail = text[edge:]
        return strip_links(text[:edge])

    def flush(self) -> str:
        text, self._tail = self._tail, ""
        return strip_links(text)


# ── 기본 신뢰 태그 ───────────────────────────────────────────────

_TRUST_TAGS = ("[확인된 사실]", "[참고 신호]")
DEFAULT_TAG = "[확인된 사실] "


def _split_heading(buffer: str) -> tuple[str, str] | None:
    """(헤딩 줄+공백, 본문). 헤딩 줄이 아직 끝나지 않았으면 None."""
    start = 0
    if buffer.startswith("#"):
        newline = buffer.find("\n")
        if newline < 0:
            return None
        start = newline + 1
    body = buffer[start:].lstrip()
    return buffer[: len(buffer) - len(body)], body


class LeadingTagGuard:
    """절 본문(헤딩 다음)이 신뢰 태그로 시작하지 않으면 `[확인된 사실]`을 붙인다.

    본문 첫 글자가 나올 때까지(태그의 앞부분이면 태그가 끝날 때까지) 붙들었다가 판단한다.
    """

    def __init__(self) -> None:
        self._buffer = ""
        self._decided = False

    def feed(self, chunk: str) -> str:
        if self._decided:
            return chunk
        self._buffer += chunk
        return self._decide(final=False)

    def flush(self) -> str:
        if self._decided:
            return ""
        return self._decide(final=True)

    def _decide(self, final: bool) -> str:
        split = _split_heading(self._buffer)
        body = split[1] if split else ""
        pending = not body or any(tag.startswith(body) and tag != body for tag in _TRUST_TAGS)
        if pending and not final:
            return ""
        text, self._buffer, self._decided = self._buffer, "", True
        if not body or body.startswith(_TRUST_TAGS):
            return text
        head, rest = split
        return head + DEFAULT_TAG + rest


def ensure_leading_tag(text: str) -> str:
    guard = LeadingTagGuard()
    return guard.feed(text) + guard.flush()


# ── 예상치 고지문 ────────────────────────────────────────────────

FUNDING_DISCLAIMER = "[확인된 사실] 금리·한도는 예상치이며, 신청 자격·한도는 공고 원문에서 확인해야 합니다."


def disclaimer_suffix(text: str) -> str:
    """지원사업 절 끝에 덧붙일 고지문 — 이미 있으면 빈 문자열."""
    return "" if FUNDING_DISCLAIMER in text else "\n\n" + FUNDING_DISCLAIMER


# ── 절별 가드 조립 ───────────────────────────────────────────────


class _PlainGuard:
    """링크만 지운다 (유사 사례·계약 밖 섹션)."""

    def __init__(self) -> None:
        self._links = UrlStripper()

    def feed(self, chunk: str) -> str:
        return self._links.feed(chunk)

    def end(self) -> str:
        """절이 (일단) 끝났다 — 붙들던 꼬리를 낸다. 같은 절이 다시 열리면 이어서 feed된다."""
        return self._links.flush()


class _TaggedGuard(_PlainGuard):
    """링크 제거 + 기본 신뢰 태그 (왜 안 되나·그래도 한다면·대안)."""

    def __init__(self) -> None:
        super().__init__()
        self._tag = LeadingTagGuard()

    def feed(self, chunk: str) -> str:
        return self._tag.feed(super().feed(chunk))

    def end(self) -> str:
        return self._tag.feed(super().end()) + self._tag.flush()


class _FundingGuard(_TaggedGuard):
    """지원사업 — 절이 끝날 때 예상치 고지문을 덧붙인다(이미 나간 본문에 있으면 생략)."""

    def __init__(self) -> None:
        super().__init__()
        self._sent = ""

    def feed(self, chunk: str) -> str:
        text = super().feed(chunk)
        self._sent += text
        return text

    def end(self) -> str:
        text = super().end()
        text += disclaimer_suffix(self._sent + text)
        self._sent += text
        return text


class _VerdictGuard(_TaggedGuard):
    """판정 — 절을 통째로 붙들었다가 끝날 때 facts와 대조한다.

    모순이면 facts로 쓴 판정 절로 바꾼다. 같은 절이 다시 열려 또 모순이면, 이미 판정을 내보냈으므로
    그 조각만 버린다(교체문을 두 번 내지 않는다).
    """

    def __init__(self, verdict_facts: dict | None, fallback: str) -> None:
        super().__init__()
        self._facts = verdict_facts
        self._fallback = fallback
        self._held = ""
        self._sent = False

    def feed(self, chunk: str) -> str:
        self._held += super().feed(chunk)
        return ""

    def end(self) -> str:
        text, self._held = self._held + super().end(), ""
        if contradicts_verdict(text, self._facts):
            text = "" if self._sent else ensure_leading_tag(self._fallback)
        self._sent = self._sent or bool(text)
        return text


class ReportGuard:
    """섹션 조각 스트림 → 가드를 거친 조각 스트림. 절 전환·`close()`가 곧 그 절의 끝이다."""

    def __init__(self, verdict_facts: dict | None, verdict_fallback: str) -> None:
        # 섹션 이름 → 가드 생성기 (if/elif 대신 테이블 디스패치). 없는 이름은 링크만 지운다.
        self._factories: dict[str, Callable[[], _PlainGuard]] = {
            "verdict": lambda: _VerdictGuard(verdict_facts, verdict_fallback),
            "reasons": _TaggedGuard,
            "conditions": _TaggedGuard,
            "alternatives": _TaggedGuard,
            "funding": _FundingGuard,
        }
        self._guards: dict[str, _PlainGuard] = {}
        self._current: str | None = None

    def feed(self, chunks: list[tuple[str, str]]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for section, chunk in chunks:
            if section != self._current:
                out.extend(self.close())
                self._current = section
            out.extend(_pair(section, self._guard(section).feed(chunk)))
        return out

    def close(self) -> list[tuple[str, str]]:
        """지금 열린 절을 끝낸다 — 붙들던 꼬리·판정·고지문을 낸다."""
        section, self._current = self._current, None
        if section is None:
            return []
        return _pair(section, self._guards[section].end())

    def _guard(self, section: str) -> _PlainGuard:
        if section not in self._guards:
            self._guards[section] = self._factories.get(section, _PlainGuard)()
        return self._guards[section]


def _pair(section: str, text: str) -> list[tuple[str, str]]:
    return [(section, text)] if text else []


def guard_section(name: str, markdown: str) -> str:
    """한 절 통째로 가드를 씌운다 — 폴백 문구용(판정 대조는 하지 않는다: 폴백이 곧 facts다)."""
    guard = ReportGuard(None, "")
    return "".join(text for _, text in [*guard.feed([(name, markdown)]), *guard.close()])
