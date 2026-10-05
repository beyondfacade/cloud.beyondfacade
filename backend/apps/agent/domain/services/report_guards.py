"""리포트 출력 코드 가드 — LLM 글이 화면에 나가기 전에 코드가 지키는 선 (stdlib만 import).

v0.68.0(리포트 코드 우선 구조)부터 LLM은 맨 위 해석(answer) 한 단락만 쓴다. 6개 절은 코드가 facts로 쓰므로
가드는 해석 단락에만 건다(`guard_answer`).

- **판정 모순**: facts와 다른 등급을 단정하면 그 단락은 실패 — 다음 모델로 넘긴다(`verdict_contradiction`).
- **링크·공고 번호 제거**: URL·bizinfo 공고 번호를 지운다(`UrlStripper`·`strip_links`).
- **숫자 문장 삭제**: 숫자가 든 문장을 지운다(`drop_digit_sentences`) — 숫자는 본문이 범위와 함께 보여 준다.
- 판정 등급 동의어·대조 규칙은 벤치 채점과 같은 단일 원천이다. 지원사업 절의 예상치 고지문(`FUNDING_DISCLAIMER`)도 여기 둔다.
"""

import re
from collections import Counter
from dataclasses import dataclass

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


# 운영 가드용 등급 이름 — 벤치 동의어보다 좁다. 이 이름을 **단정**할 때만 모순으로 본다
# ("조건부로라도 권하기 어렵다"·"빨간불은 켜지지 않았다"처럼 등급 말이 나온 해석은 모순이 아니다).
GRADE_LABELS = {
    "red": ("비추천", "빨간색", "빨강", "레드", "적색", "red"),
    "orange": ("조건부", "주황색", "주황", "orange"),
    "clear": ("경고 없음", "clear"),
    "unavailable": ("판정 없음", "판정 보류", "insufficient"),
}
# 흔한 낱말이라 강조로 감쌌거나 등급 말이 바로 뒤에 올 때만 단정으로 보는 이름 ("주의가 필요합니다"는 아니다)
EMPHASIS_ONLY_LABELS = {"orange": ("주의 필요", "주의")}
# 단정의 모양 — 강조로 감쌈 / 등급 말·서술어·괄호·콜론이 바로 뒤 / "등급은·판정:" 바로 뒤 / 줄 머리에서 끊김
_QUOTE_PAIRS = (("**", "**"), ("'", "'"), ('"', '"'), ("`", "`"), ("“", "”"), ("‘", "’"))
_ASSERT_AFTER = r"(?:[ \t]*(?:등급|단계|판정|입니다|이다|이며|\(|:|\.(?!\d))|[ \t]*(?:으로|로)[ \t]*판정)"
_ASSERT_BEFORE = r"(?:등급|판정)[ \t]*(?:은|는|:)[ \t]*(?:\*\*|['\"`“‘])?[ \t]*"
_LINE_HEAD = r"(?:^|(?<=\n))[ \t]*(?:[-*+>][ \t]+)?(?:\*\*)?(?:\[[^\]\n]*\](?:\*\*)?[ \t]*)?"
_LINE_STOP = r"[ \t]*(?:[.—–-]|$)"
# "비추천 등급은 아니지만"·"조건부 판정은 아닙니다" — 같은 마디 안에서 은/는 … 아니로 부정하면 단정이 아니다
_NEGATED = re.compile(r"(?:[ \t]*(?:등급|단계|판정))?[ \t]*(?:은|는)[^.,\n]{0,15}?(?:아니|아닙|아님)")


def _word(label: str) -> str:
    return r"(?<![A-Za-z])" + r"[ \t]*".join(map(re.escape, label.split())) + r"(?![A-Za-z])"


def _emphasized(label: str) -> str:
    """강조로 감싼 이름(괄호 속 코드 꼬리 허용 — "‘주의 필요(orange)’") 또는 바로 뒤 등급 말."""
    word = _word(label)
    inner = rf"[ \t]*{word}(?:[ \t]*\([^)\n]{{0,20}}\))?(?:[ \t]*(?:등급|단계))?[ \t]*"
    quoted = "|".join(rf"{re.escape(o)}{inner}{re.escape(c)}" for o, c in _QUOTE_PAIRS)
    return rf"{quoted}|\([ \t]*{word}[ \t]*\)|{word}[ \t]*(?:등급|단계)"


def _assertion(label: str) -> str:
    word = _word(label)
    return rf"{_emphasized(label)}|{word}{_ASSERT_AFTER}|{_ASSERT_BEFORE}{word}|{_LINE_HEAD}{word}{_LINE_STOP}"


# 등급 그룹 → 단정 패턴 (테이블에서 만든다 — 이름을 더하면 패턴이 따라온다)
_GRADE_ASSERTIONS = {
    group: re.compile(
        "|".join([*map(_assertion, labels), *map(_emphasized, EMPHASIS_ONLY_LABELS.get(group, ()))]),
        re.IGNORECASE | re.MULTILINE,
    )
    for group, labels in GRADE_LABELS.items()
}


def verdict_contradiction(text: str, verdict_facts: dict | None) -> str | None:
    """판정 절이 facts와 **다른 등급을 단정한** 구절 — 없으면 None.

    대조할 판정 자료가 없거나 모르는 등급 코드면 대조하지 않는다(None).
    """
    if not verdict_facts:
        return None
    code = verdict_facts.get("verdict_code") if verdict_facts.get("available") else "unavailable"
    group = _VERDICT_GROUP.get(code, code)
    if group not in _GRADE_ASSERTIONS:
        return None
    hits = (
        hit
        for other, pattern in _GRADE_ASSERTIONS.items()
        if other != group
        for hit in pattern.finditer(text)
        if not _NEGATED.match(text, hit.end())
    )
    return next((hit.group(0).strip() for hit in hits), None)


def stated_grades(text: str) -> set[str]:
    """글에 나온 등급 그룹(관대한 동의어 기준) — 벤치 일관성 지표가 대안 절 줄마다 쓴다."""
    squashed = _squash(text)
    return {group for group, words in _SQUASHED_SYNONYMS.items() if any(w in squashed for w in words)}


def contradicts_verdict(text: str, verdict_facts: dict | None) -> bool:
    return verdict_contradiction(text, verdict_facts) is not None


# ── 링크·공고 번호 제거 ──────────────────────────────────────────

# URL은 ASCII 문자로만 이어진다고 본다 — 붙어 오는 한글 조사("…/x에서")와 괄호는 URL이 아니다.
_URL_CHAR = r"[A-Za-z0-9\-._~:/?#@!$&'*+,;=%]"
_URL_END = r"[A-Za-z0-9\-_~/#@$&*+=%]"  # 문장 끝 마침표·쉼표는 URL에 넣지 않는다
_URL_BODY = rf"(?:{_URL_CHAR}*{_URL_END})?"
_JUNK_CHAR = r"[^\s()\[\]<>`가-힣]"  # "https/www…"처럼 스킴이 깨진 흔적
_LINK_CORE = (
    rf"https?://{_URL_BODY}|www\.{_URL_BODY}|PBLN_\d+|pblancId=[A-Za-z0-9_]*"
    rf"|(?<![A-Za-z])(?:https?|www)(?=[:/.…]){_JUNK_CHAR}*"
)
_CORE = re.compile(_LINK_CORE)
# 링크 바로 앞의 이름표("**원문 링크:**"·"링크:"·"[원문 링크]") — 링크를 지우면 홀로 남으므로 함께 지운다.
_LINK_NAMES = r"(?:원문[ \t]*링크|공고[ \t]*링크|신청[ \t]*링크|링크|원문|URL|출처|바로가기|홈페이지)"
_LABEL = rf"(?:\*\*)?(?:\[{_LINK_NAMES}\]|{_LINK_NAMES}(?:\*\*)?[ \t]*:)(?:\*\*)?[ \t]*"
_LINK = rf"(?:{_LABEL})?(?:{_LINK_CORE})"
# 지운 뒤 남는 흔적 — 이름표만 남은 마크다운 링크, 빈 괄호·대괄호·백틱 쌍
_DEAD_MD_LINK = rf"\[[ \t]*(?:{_LINK_NAMES})?[ \t]*\]\([ \t]*\)"
_EMPTY_PAIR = r"\([ \t]*\)|\[[ \t]*\]|(?<!`)`[ \t]*`(?!`)"
_KEEP_MD_LABEL = re.compile(r"\[([^\]\n]+)\]\([ \t]*\)")
_EMPTY_ITEM = re.compile(r"(?m)^[ \t]*(?:[-*+]|\d+[.)])[ \t]*(?:\n|$)")  # 내용이 다 지워진 목록 항목

_LINK_STARTS = ("https://", "http://", "www.", "PBLN_", "pblancId=")
# 꼬리가 아직 끝나지 않은 링크 — 다음 조각에서 더 이어질 수 있다.
_OPEN_LINK = re.compile(
    rf"(?:(?:https?://|www\.|PBLN_|pblancId=){_URL_CHAR}*|(?<![A-Za-z])(?:https?|www)[:/.…]{_JUNK_CHAR}*)$"
)
# 여는 괄호·백틱·굵은 표시 + 아직 덜 온 이름표 앞부분("(원문", "**원문 링") — 낱말 둘까지만 붙든다.
_OPENER_WORD = r"(?:[(`]|\*{1,2})(?:[가-힣A-Za-z]{1,6}(?:[ \t]+[가-힣A-Za-z]{0,6})?)?"
# 링크 앞에 올 수 있는 것의 연속 — 여는 괄호·백틱, 이름표, 닫혔거나 아직 열린 "[글자](" — 링크와 함께
# 지우거나 다듬어야 하므로 붙든다(먼저 내보내면 통째로 처리할 때와 결과가 달라진다).
_BEFORE_LINK = re.compile(
    rf"[ \t]*(?:(?:{_OPENER_WORD}|\[[^\]\n]{{0,80}}(?:\]\(?)?|{_LABEL})[ \t]*)*$"
)
# 아직 짧은 목록 항목·굵은 글씨·대괄호 줄 — 뒤에 링크가 오면 줄째 지워야 하므로 줄 머리부터 붙든다.
_BARE_ITEM = re.compile(r"[ \t]*(?:[-*+]|\d+[.)])?[ \t]*")
_LISTISH_LINE = re.compile(r"[ \t]*(?:(?:[-*+]|\d+[.)])(?:[ \t][^\n]{0,30})?|(?:\*\*|\[)[^\n]{0,30})")


def _drop(pattern: str, text: str) -> str:
    """흔적 지우기 — 줄 머리면 뒤 공백까지, 줄 중간이면 앞 공백까지 함께 지운다.

    앞 공백을 `[ \t]*`로 잡으면 긴 공백 줄에서 자리마다 되짚어 제곱 시간이 든다 — 앞 조각을 잘라 낸다.
    """
    text = re.sub(rf"(?m)^[ \t]*(?:{pattern})[ \t]*", "", text)
    parts, last = [], 0
    for match in re.finditer(pattern, text):
        parts.append(text[last : match.start()].rstrip(" \t"))
        last = match.end()
    return "".join(parts) + text[last:]


def strip_links(text: str, at_line_start: bool = True) -> str:
    """URL·공고 번호(와 이름표)를 지우고, 남은 빈 괄호·백틱·빈 목록 항목을 정리한다."""
    sentinel = "\n" if at_line_start else "\x00"  # 조각 머리가 실제 줄 머리인지 정규식에 알린다
    text = _drop(_LINK, sentinel + text)
    while True:
        cleaned = _drop(_EMPTY_PAIR, _KEEP_MD_LABEL.sub(r"\1", _drop(_DEAD_MD_LINK, text)))
        if cleaned == text:
            break
        text = cleaned
    return _EMPTY_ITEM.sub("", text)[1:]


_HOLD_WINDOW = 400  # 붙들기 판단은 꼬리 이만큼에서만 — 긴 줄·긴 공백을 조각마다 다시 훑지 않는다


def _before_link(text: str, edge: int) -> int:
    return _BEFORE_LINK.search(text, max(0, edge - _HOLD_WINDOW), edge).start()


def _hold_from(text: str) -> int:
    """붙들기 시작할 위치 — 끝나지 않은 링크·링크 시작의 앞부분과 그 앞 괄호·이름표, 짧은 목록 줄."""
    window = max(0, len(text) - _HOLD_WINDOW)
    open_link = _OPEN_LINK.search(text, window)
    edge = open_link.start() if open_link else len(text) - _partial_start_length(text)
    edge = _before_link(text, edge)
    line_start = text.rfind("\n", 0, edge) + 1
    if edge - line_start > _HOLD_WINDOW:
        return edge  # 이만큼 긴 줄은 짧은 목록 줄도, 링크만 남은 항목 줄도 아니다
    line = text[line_start:edge]
    if _LISTISH_LINE.fullmatch(line) or (_CORE.search(line) and _BARE_ITEM.fullmatch(strip_links(line))):
        return line_start  # 짧은 목록 줄, 또는 링크를 지우면 표지만 남는 줄 — 줄바꿈과 함께 지워야 한다
    # 여는 괄호 뒤가 (링크를 지우고 나면) 비어 있으면 닫는 괄호가 오기 전까지 붙든다 — "([링크](…)" + ")"
    openers = (i for i in range(line_start, edge) if text[i] in "([`")
    empty = next((i for i in openers if not strip_links(text[i + 1 : edge], False).strip()), None)
    return edge if empty is None else _before_link(text, empty)


def _partial_start_length(text: str) -> int:
    """꼬리가 링크 시작(`https://`·`www.`·`PBLN_`…)의 앞부분이면 그 길이, 아니면 0."""
    return max(
        (n for start in _LINK_STARTS for n in range(1, len(start)) if text.endswith(start[:n])),
        default=0,
    )


class UrlStripper:
    """조각 스트림에서 링크를 지우는 필터. 남은 꼬리는 `flush()`로 비운다. 지운 링크 수를 센다."""

    def __init__(self, events: Counter | None = None) -> None:
        self._tail = ""
        self._line_start = True
        self.events = Counter() if events is None else events

    def feed(self, chunk: str) -> str:
        text = self._tail + chunk
        edge = _hold_from(text)
        self._tail = text[edge:]
        return self._release(text[:edge])

    def flush(self) -> str:
        text, self._tail = self._tail, ""
        return self._release(text)

    def _release(self, text: str) -> str:
        if not text:
            return ""
        self.events["links_stripped"] += len(_CORE.findall(text))
        cleaned = strip_links(text, self._line_start)
        self._line_start = text.endswith("\n")
        return cleaned


# ── 예상치 고지문 ────────────────────────────────────────────────

FUNDING_DISCLAIMER = "[확인된 사실] 금리·한도는 예상치이며, 신청 자격·한도는 공고 원문에서 확인해야 합니다."


# ── 해석(answer) 단락 가드 (설계서 2026-10-05-report-code-first §5) ────────

# 문장 끝 — 마침표·물음표·느낌표 뒤 공백. 한글 문장은 "~다."·"~요."로 끝나고, 소수점("3.5")은 뒤에 공백이 없어 갈리지 않는다.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_DIGIT = re.compile(r"\d")


def drop_digit_sentences(text: str) -> tuple[str, int]:
    """숫자가 든 문장을 통째로 지운다 — (남은 단락, 지운 문장 수). 숫자는 본문 6개 절이 범위와 함께 보여 준다."""
    sentences = [s for s in _SENTENCE_END.split(text.strip()) if s]
    kept = [s for s in sentences if not _DIGIT.search(s)]
    return " ".join(kept), len(sentences) - len(kept)


@dataclass(frozen=True)
class GuardedAnswer:
    """가드를 거친 해석 단락과 개입 기록 — 벤치가 그대로 남긴다."""

    text: str
    removed_sentences: int
    links_stripped: int
    contradiction: str | None

    @property
    def ok(self) -> bool:
        """화면에 낼 수 있는가 — 판정과 모순이 없고, 가드 뒤에도 글이 남았다."""
        return self.contradiction is None and bool(self.text)


def guard_answer(raw: str, verdict_facts: dict | None) -> GuardedAnswer:
    """해석 단락 통째 가드 — 링크·공고 번호 제거 → 판정 모순 검사 → 숫자 문장 삭제.

    모순은 단락 전체의 실패다(다음 모델로 넘긴다). 스트리밍하지 않으므로 끝까지 모은 글에 한 번 건다.
    """
    links = UrlStripper()
    text = links.feed(raw) + links.flush()
    contradiction = verdict_contradiction(text, verdict_facts)
    kept, removed = drop_digit_sentences(text)
    return GuardedAnswer(kept, removed, links.events["links_stripped"], contradiction)
