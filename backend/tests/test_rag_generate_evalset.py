"""평가셋 추가 생성 — 표본 선택·행 구성·판정 대상 필터 (순수 함수)."""

from apps.rag.adapter.inbound.cli.generate_evalset import build_row, select_new_chunks
from apps.rag.adapter.inbound.cli.judge_evalset import pending_rows
from apps.rag.adapter.inbound.cli.review_evalset import ProgramCard, parse_sheet, render_sheet


def test_select_new_chunks_skips_ids_already_in_evalset_and_keeps_order():
    chunks = [{"chunk_id": f"funding:P{i}", "content": ""} for i in (1, 2, 3, 4, 5)]
    picked = select_new_chunks(chunks, existing_ids={"funding:P2", "funding:P4"}, limit=2)
    assert [c["chunk_id"] for c in picked] == ["funding:P1", "funding:P3"]


def test_build_row_is_candidate_with_source_type_from_chunk_id():
    row = build_row({"chunk_id": "news:abc", "content": "…"}, "강북구 주민참여예산 투표 뉴스 있어?")
    assert row == {
        "question": "강북구 주민참여예산 투표 뉴스 있어?",
        "relevant_ids": ["news:abc"],
        "source_type": "news",
        "status": "candidate",
    }


def test_pending_rows_are_only_candidates():
    rows = [
        {"relevant_ids": ["funding:P1"], "status": "confirmed"},
        {"relevant_ids": ["funding:P2"], "status": "candidate"},
        {"relevant_ids": ["funding:P3"], "status": "rejected"},
    ]
    assert [r["relevant_ids"][0] for r in pending_rows(rows)] == ["funding:P2"]


def test_render_sheet_can_start_numbering_after_existing_items():
    rows = [{"question": "q", "relevant_ids": ["funding:P9"], "source_type": "funding", "status": "candidate"}]
    cards = {"P9": ProgramCard("P9", "제목", "기관", None, None, "상시", None, "http://u/9")}
    sheet = render_sheet(rows, cards, start=51, header=False)
    assert sheet.startswith("## 51. funding:P9\n")
    assert "# RAG 평가셋 검수 시트" not in sheet
    assert parse_sheet(sheet)["funding:P9"] == (None, "q")
