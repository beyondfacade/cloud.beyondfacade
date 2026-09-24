"""Claude 1차 판정을 검수 시트에 기입 — 순수 함수. 사람이 시트에서 뒤집을 수 있게 판정란만 채운다."""

from apps.rag.adapter.inbound.cli.judge_evalset import Judgment, annotate_sheet
from apps.rag.adapter.inbound.cli.review_evalset import parse_sheet

_SHEET = """# 헤더 — 판정: O 또는 판정: X 라고 적는다

---
## 1. funding:P1
질문: 폐업 후 세금 지원?
공고: **체납액 징수특례**
판정: 

## 2. funding:P2
질문: 방산기업 지원금?
공고: **방산 헬프데스크**
판정: 

## 3. funding:P3
질문: 청년 창업 대출?
공고: **청년 창업자금**
판정: 
"""


def test_annotate_sheet_fills_verdict_with_reason_and_suggestion_as_memo():
    out = annotate_sheet(
        _SHEET,
        {
            "funding:P1": Judgment(verdict="O", reason="폐업·재기·세금이 공고 핵심과 일치"),
            "funding:P2": Judgment(verdict="X", reason="구미·방산이 빠져 다른 공고와 구분 안 됨", better_question="구미 방산기업 경영·기술 지원 어디서 받나요?"),
        },
    )
    assert "판정: O  # claude: 폐업·재기·세금이 공고 핵심과 일치\n" in out
    assert "판정: X  # claude: 구미·방산이 빠져 다른 공고와 구분 안 됨 | 제안: 구미 방산기업 경영·기술 지원 어디서 받나요?\n" in out
    assert out.count("판정: \n") == 1  # 판정 없는 3번은 빈 채로
    assert "# 헤더 — 판정: O 또는 판정: X 라고 적는다" in out  # 헤더 설명문은 건드리지 않는다


def test_annotated_sheet_round_trips_through_parse_sheet():
    out = annotate_sheet(_SHEET, {"funding:P1": Judgment(verdict="O", reason="이유"), "funding:P3": Judgment(verdict="X", reason="이유")})
    verdicts = parse_sheet(out)
    assert verdicts["funding:P1"][0] == "O"
    assert verdicts["funding:P2"][0] is None
    assert verdicts["funding:P3"][0] == "X"
    assert verdicts["funding:P1"][1] == "폐업 후 세금 지원?"  # 질문은 그대로


def test_annotate_sheet_overwrites_previous_claude_verdict_but_keeps_human_memo_free_lines():
    once = annotate_sheet(_SHEET, {"funding:P1": Judgment(verdict="X", reason="첫 판정")})
    twice = annotate_sheet(once, {"funding:P1": Judgment(verdict="O", reason="재판정")})
    assert "판정: O  # claude: 재판정\n" in twice
    assert "첫 판정" not in twice
