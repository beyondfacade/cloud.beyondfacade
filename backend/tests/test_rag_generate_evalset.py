"""평가셋 추가 생성 — 표본 선택·행 구성·판정 대상 필터 (순수 함수)."""

from datetime import datetime

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


from apps.rag.adapter.inbound.cli.generate_evalset import (  # noqa: E402
    HardItem,
    build_hard_row,
    pick_sibling,
    select_colloquial,
    select_news_event,
    select_sibling,
)


def _c(cid, title, day=1):
    return {"chunk_id": cid, "content": f"{title}\n본문", "published_at": datetime(2026, 9, day)}


def test_유사_공고는_제목_토큰이_가장_많이_겹치는_다른_공고():
    target = _c("funding:A", "서울 청년 창업 자금 지원")
    pool = [target, _c("funding:B", "서울 청년 창업 자금 융자"), _c("funding:C", "부산 수출 바우처")]
    assert pick_sibling(target, pool)["chunk_id"] == "funding:B"


def test_겹침이_0_3_미만이면_유사_공고가_없다():
    target = _c("funding:A", "서울 청년 창업 자금 지원")
    assert pick_sibling(target, [target, _c("funding:C", "부산 수출 바우처")]) is None


def test_유사_공고_선택은_짝이_있는_공고만_기존_행은_건너뛴다():
    chunks = [
        _c("funding:A", "서울 청년 창업 자금 지원"),
        _c("funding:B", "서울 청년 창업 자금 융자"),
        _c("funding:C", "부산 수출 바우처"),
    ]
    items = select_sibling(chunks, existing={"funding:A"}, limit=5)
    assert [i.chunk_id for i in items] == ["funding:B"]
    assert "서울 청년 창업 자금 지원" in items[0].prompt_input  # 짝 공고 내용이 프롬프트에 들어간다
    assert items[0].relevant_ids == ["funding:B"]


def test_구어체는_기존_행을_건너뛰고_단일_정답():
    chunks = [_c("funding:A", "a"), _c("funding:B", "b")]
    items = select_colloquial(chunks, existing={"funding:A"}, limit=5)
    assert items == [HardItem("funding:B", "b\n본문", ["funding:B"])]


def test_뉴스_사건은_같은_사건_기사를_모두_정답으로_묶고_사건당_한_번만():
    chunks = [
        _c("news:a", "망원시장 야시장 개장 상인 기대", 1),
        _c("news:b", "망원시장 야시장 개장 상인 기대감", 2),
        _c("news:c", "신촌 상권 임대료 상승", 2),
    ]
    items = select_news_event(chunks, existing=set(), limit=5)
    assert [(i.chunk_id, i.relevant_ids) for i in items] == [
        ("news:a", ["news:a", "news:b"]),
        ("news:c", ["news:c"]),
    ]


def test_뉴스_사건이_기존_정답과_겹치면_건너뛴다():
    chunks = [_c("news:a", "망원시장 야시장 개장 상인 기대", 1), _c("news:b", "망원시장 야시장 개장 상인 기대감", 2)]
    assert select_news_event(chunks, existing={"news:b"}, limit=5) == []


def test_어려운_질문_행은_subset과_종류를_단다():
    row = build_hard_row(HardItem("news:a", "…", ["news:a", "news:b"]), "망원시장 밤에 장 서?", "news_event")
    assert row == {
        "question": "망원시장 밤에 장 서?",
        "relevant_ids": ["news:a", "news:b"],
        "source_type": "news",
        "status": "candidate",
        "subset": "hard",
        "hard_kind": "news_event",
    }


def test_검수_반영은_subset과_hard_kind를_보존한다():
    from apps.rag.adapter.inbound.cli.review_evalset import apply_verdicts

    row = {"question": "q", "relevant_ids": ["news:a"], "source_type": "news", "status": "candidate",
           "subset": "hard", "hard_kind": "news_event"}
    out = apply_verdicts([row], {"news:a": ("O", "q2")})
    assert out[0]["subset"] == "hard" and out[0]["hard_kind"] == "news_event"
    assert out[0]["status"] == "confirmed" and out[0]["question"] == "q2"


def test_내보내기는_문항마다_지시문과_입력과_정답_묶음을_싣는다():
    import json

    from apps.rag.adapter.inbound.cli.generate_evalset import _HARD_SYSTEMS, export_hard_items

    out = export_hard_items([HardItem("news:a", "기사 본문", ["news:a", "news:b"])], "news_event")
    row = json.loads(out.splitlines()[0])
    assert row == {
        "chunk_id": "news:a", "hard_kind": "news_event", "relevant_ids": ["news:a", "news:b"],
        "system": _HARD_SYSTEMS["news_event"], "prompt_input": "기사 본문",
    }


def test_답안_가져오기는_어려운_질문_행을_만들고_기존_정답과_따옴표를_정리한다():
    import json

    from apps.rag.adapter.inbound.cli.generate_evalset import rows_from_answers

    text = "\n".join([
        json.dumps({"chunk_id": "funding:A", "hard_kind": "colloquial", "relevant_ids": ["funding:A"],
                    "question": ' "가게 인테리어 비용 빌려주는 데 있어?" '}, ensure_ascii=False),
        json.dumps({"chunk_id": "funding:B", "hard_kind": "colloquial", "relevant_ids": ["funding:B"],
                    "question": "이미 있는 공고"}, ensure_ascii=False),
        "",
    ])
    rows = rows_from_answers(text, existing={"funding:B"})
    assert rows == [{
        "question": "가게 인테리어 비용 빌려주는 데 있어?",
        "relevant_ids": ["funding:A"],
        "source_type": "funding",
        "status": "candidate",
        "subset": "hard",
        "hard_kind": "colloquial",
    }]
