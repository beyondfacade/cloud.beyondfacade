"""평가셋 사람 검수 시트 — 렌더링·파싱·반영 (순수 함수, DB 없음).

시트는 VS Code에서 편집하는 markdown. 판정란에 O(적합)·X(부적합)를 적고, 질문 줄을 고치면 고친 질문이 반영된다.
비워 두면 candidate 그대로.
"""

from apps.rag.adapter.inbound.cli.review_evalset import (
    ProgramCard,
    apply_verdicts,
    parse_sheet,
    render_sheet,
)

_ROWS = [
    {"question": "폐업 후 세금 지원?", "relevant_ids": ["funding:P1"], "source_type": "funding", "status": "candidate"},
    {"question": "방산기업 지원금?", "relevant_ids": ["funding:P2"], "source_type": "funding", "status": "candidate"},
    {"question": "청년 창업 대출?", "relevant_ids": ["funding:P3"], "source_type": "funding", "status": "candidate"},
]
_CARDS = {
    "P1": ProgramCard("P1", "체납액 징수특례", "국세청", "소상공인", "기타/제도", "2020.01.01 ~ 2026.12.31", "요약1", "http://u/1"),
    "P2": ProgramCard("P2", "방산 경영기술 지원", "구미시", "중소기업", "경영/컨설팅", "2026.01.01 ~ 2026.12.31", "요약2", "http://u/2"),
    "P3": ProgramCard("P3", "청년 창업자금", "중기부", "청년", "금융/융자", "상시", None, "http://u/3"),
}


def test_render_sheet_lists_every_row_with_program_card_and_empty_verdict():
    sheet = render_sheet(_ROWS, _CARDS)
    assert sheet.count("\n판정: \n") == 3  # 빈 판정 줄이 항목마다 하나 (헤더 설명문의 "판정:"은 제외)
    assert "## 1. funding:P1" in sheet
    assert "질문: 폐업 후 세금 지원?" in sheet
    assert "체납액 징수특례" in sheet and "국세청" in sheet and "요약1" in sheet
    assert "http://u/3" in sheet  # 요약이 없는 공고도 카드가 나온다


def test_parse_sheet_reads_verdict_and_edited_question_per_id():
    sheet = render_sheet(_ROWS, _CARDS)
    edited = (
        sheet.replace("질문: 방산기업 지원금?", "질문: 구미 방산기업 경영 기술 지원은 어디서 받나요?")
        .replace("판정: \n", "판정: O\n", 1)  # 1번 O
    )
    # 2번은 질문만 고치고 O, 3번은 X
    lines = edited.split("\n")
    seen = 0
    for i, line in enumerate(lines):
        if line.startswith("판정:"):
            seen += 1
            if seen == 2:
                lines[i] = "판정: o"  # 소문자도 허용
            if seen == 3:
                lines[i] = "판정: X  # 질문이 공고와 안 맞음"
    verdicts = parse_sheet("\n".join(lines))

    assert verdicts["funding:P1"] == ("O", "폐업 후 세금 지원?")
    assert verdicts["funding:P2"] == ("O", "구미 방산기업 경영 기술 지원은 어디서 받나요?")
    assert verdicts["funding:P3"] == ("X", "청년 창업 대출?")


def test_parse_sheet_leaves_blank_verdict_as_none():
    verdicts = parse_sheet(render_sheet(_ROWS, _CARDS))
    assert all(v[0] is None for v in verdicts.values())


def test_apply_verdicts_promotes_o_rejects_x_and_keeps_blank_candidate():
    verdicts = {
        "funding:P1": ("O", "폐업 후 세금 지원?"),
        "funding:P2": ("O", "구미 방산기업 경영 기술 지원은 어디서 받나요?"),
        "funding:P3": (None, "청년 창업 대출?"),
    }
    out = apply_verdicts(_ROWS, verdicts)

    assert [r["status"] for r in out] == ["confirmed", "confirmed", "candidate"]
    assert out[1]["question"] == "구미 방산기업 경영 기술 지원은 어디서 받나요?"
    assert out[2]["question"] == "청년 창업 대출?"
    assert _ROWS[1]["question"] == "방산기업 지원금?"  # 입력은 건드리지 않는다


def test_apply_verdicts_marks_x_as_rejected():
    out = apply_verdicts(_ROWS, {"funding:P3": ("X", "청년 창업 대출?")})
    assert out[2]["status"] == "rejected"
    assert out[0]["status"] == "candidate"  # 시트에 없는 행은 그대로


def test_apply_verdicts_rejects_unknown_mark():
    import pytest

    with pytest.raises(ValueError, match="funding:P1"):
        apply_verdicts(_ROWS, {"funding:P1": ("?", "폐업 후 세금 지원?")})
