"""토큰 스트림을 `[SECTION:name]` 마커로 가르는 순수 분할기 (stdlib만 import).

LLM은 마커를 한 덩어리로 주지 않는다 — `[SECT` / `ION:verdict]`처럼 조각 경계에 걸쳐 온다.
그래서 버퍼 꼬리가 **마커 앞부분일 수 있을 때만** 그만큼 붙들고, 나머지는 곧바로 흘린다
(붙드는 길이가 곧 스트리밍 지연이다).

두 가지 규칙을 정해 둔다.
- **서문은 버린다**: 첫 마커 앞 텍스트(머리말·도구 호출 전 잡담)는 리포트 본문이 아니다.
- **중복 마커는 이어 붙인다**: 같은 마커가 다시 오면 그 섹션을 다시 열 뿐, 이미 내보낸 조각을
  되돌리지 않는다(프론트 리듀서가 append다). 다시 열 때 빈 줄 하나를 앞에 붙여 앞 본문과
  붙어 버리지 않게 한다 — 스트림은 되돌릴 수 없으므로 "뒤엣것이 이긴다"가 성립하지 않는다.
"""

import re
from collections.abc import Iterable

# 저장·표시 기준 섹션 순서 (설계서 §5 계약 표). 인터랙터 `_SECTIONS`의 키 순서와 같다 —
# 조각은 도착 순서가 뒤섞일 수 있어도 저장본은 늘 이 순서여야 한다.
SECTION_ORDER = ("verdict", "reasons", "analogs", "conditions", "alternatives", "funding")

_MARKER = re.compile(r"\[SECTION:(\w+)\]")

# 버퍼 꼬리가 마커의 앞부분인 경우만 골라낸다 — `[`, `[SEC`, `[SECTION:verd` …
_PARTIAL_MARKER = re.compile(r"\[(?:S(?:E(?:C(?:T(?:I(?:O(?:N(?::\w*)?)?)?)?)?)?)?)?$")

# 꼬리 공백도 붙든다 — 섹션 끝 줄바꿈을 먼저 흘려보내면 털어낼 방법이 없다(뒤에 마커가 올지
# 모른다). 공백은 다음 글자가 오는 즉시 함께 나가므로 체감 지연이 없다.
_TRAILING_SPACE = re.compile(r"\s+$")


# 문단 사이 빈 줄 — 꼬리 공백은 다음 글자와 함께 나가므로 빈 줄은 늘 한 조각 안에 통째로 온다.
_PARAGRAPH_BREAK = re.compile(r"[ \t]*\n\s*\n\s*")


class SectionSplitter:
    """텍스트 조각을 먹여 `(섹션, 조각)` 목록을 받는다. 남은 꼬리는 `flush()`로 비운다.

    `single_paragraph` 섹션은 문단 사이 빈 줄을 줄바꿈 하나로 바꿔 한 문단으로 잇는다.
    """

    def __init__(self, single_paragraph: Iterable[str] = ()) -> None:
        self._single_paragraph = frozenset(single_paragraph)
        self._buffer = ""
        self._section: str | None = None
        self._section_started = False  # 현재 섹션의 첫 조각인지 (왼쪽 공백 제거용)
        self._reopened = False  # 이미 본 섹션을 다시 열었는지 (빈 줄 한 번 삽입용)
        self.sections_seen: list[str] = []

    def feed(self, text: str) -> list[tuple[str, str]]:
        self._buffer += text
        chunks: list[tuple[str, str]] = []
        while True:
            marker = _MARKER.search(self._buffer)
            if marker is None:
                break
            chunks.extend(self._take(self._buffer[: marker.start()], last=True))
            self._open(marker.group(1))
            self._buffer = self._buffer[marker.end() :]

        edge = _hold_from(_PARTIAL_MARKER, self._buffer)
        edge = _hold_from(_TRAILING_SPACE, self._buffer[:edge])  # 마커 앞 공백도 함께 붙든다
        chunks.extend(self._take(self._buffer[:edge]))
        self._buffer = self._buffer[edge:]
        return chunks

    def flush(self) -> list[tuple[str, str]]:
        """붙들고 있던 꼬리를 마지막 조각으로 낸다 — 두 번 불러도 같은 조각을 다시 내지 않는다."""
        chunks = self._take(self._buffer, last=True)
        self._buffer = ""
        return chunks

    def _open(self, section: str) -> None:
        self._reopened = section in self.sections_seen
        self._section = section
        self._section_started = False
        if not self._reopened:
            self.sections_seen.append(section)

    def _take(self, text: str, last: bool = False) -> list[tuple[str, str]]:
        """현재 섹션의 조각 1건 — 섹션 첫 조각은 왼쪽, 마지막 조각은 오른쪽 공백을 턴다."""
        if self._section is None:
            return []  # 첫 마커 앞 서문은 버린다
        if not self._section_started:
            text = text.lstrip()
        if last:
            text = text.rstrip()
        if not text:
            return []
        if not self._section_started and self._reopened:
            text = "\n\n" + text  # 다시 열린 섹션이 앞 본문에 붙지 않게 한 번만 띄운다
            self._reopened = False
        if self._section in self._single_paragraph:
            text = _PARAGRAPH_BREAK.sub("\n", text)
        self._section_started = True
        return [(self._section, text)]


def _hold_from(pattern: re.Pattern, buffer: str) -> int:
    """버퍼에서 붙들기 시작할 위치 — 걸리는 꼬리가 없으면 버퍼 끝(전부 흘린다)."""
    match = pattern.search(buffer)
    return match.start() if match else len(buffer)


def concat_sections(
    chunks: Iterable[tuple[str, str]], order: Iterable[str] = SECTION_ORDER
) -> str:
    """조각 목록 → 저장용 마크다운. 섹션 안은 그대로 잇고, 섹션끼리는 빈 줄로 나눈다.

    섹션은 `order` 순서로 정렬한다 — 도착 순서가 뒤섞여도(폴백이 뒤늦게 붙는 경우) 저장본은
    늘 계약 순서다. `order`에 없는 섹션은 뒤에 도착 순서대로 남긴다(버리지 않는다).
    """
    ranking = list(order)
    sections: dict[str, list[str]] = {}
    for section, chunk in chunks:
        sections.setdefault(section, []).append(chunk)
    names = sorted(
        sections, key=lambda name: ranking.index(name) if name in ranking else len(ranking)
    )
    return "\n\n".join("".join(sections[name]) for name in names)
