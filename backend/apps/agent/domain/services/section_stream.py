"""리포트 절 조각 → 저장용 마크다운 (stdlib만 import).

SSE `report_delta`는 절 이름과 마크다운 조각이다. 저장본(analysis_report.report_md)·벤치·평가 러너는 이 모듈로
절별로 이어 붙이고 계약 순서로 정렬한다.
"""

from collections.abc import Iterable

# 저장·표시 기준 섹션 순서 — 질문에 대한 직접 답(answer_lead, 코드)이 맨 위, 그 아래 해석(answer), 다음에 코드 6개 절
# (report_sections.SECTION_TITLES 순서). 해석은 6개 절보다 늦게 도착하지만 저장본은 화면처럼 맨 위다. answer 없는 옛 저장본은 그대로다.
SECTION_ORDER = ("answer_lead", "answer", "verdict", "reasons", "analogs", "conditions", "alternatives", "funding")


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
