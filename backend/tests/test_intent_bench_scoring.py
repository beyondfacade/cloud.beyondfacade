"""관문 채점 — 정답·null·지어내기·스키마 실패, 검수 시트 왕복."""

from apps.intent.adapter.inbound.cli.intent_bench_scoring import parse_sheet, render_sheet, score_row, summarize
from apps.intent.app.dtos.intent_dto import LlmSuggestion

E = {"region_name": "서교동", "industry_id": "cafe", "budget_krw": None}


def test_다_맞으면_both_1_지어내기_없음():
    r = score_row(E, LlmSuggestion("서교동", "cafe", None))
    assert (r["schema_ok"], r["both"], r["budget"], r["fabricated"], r["null_slots"]) == (True, 1.0, 1.0, False, 1)


def test_정답이_null인_칸에_값을_내면_지어내기():
    r = score_row(E, LlmSuggestion("서교동", "cafe", 50_000_000))
    assert r["fabricated"] is True and r["both"] == 1.0 and r["budget"] == 0.0


def test_실패는_스키마_불통과():
    r = score_row(E, None)
    assert r["schema_ok"] is False and r["both"] == 0.0 and r["fabricated"] is False


def test_요약의_지어내기_분모는_null_칸이_있는_행():
    rows = [score_row(E, LlmSuggestion("서교동", "cafe", 1)), score_row({"region_name": "a", "industry_id": "b", "budget_krw": 1}, LlmSuggestion("a", "b", 1))]
    s = summarize(rows)
    assert s["fabrication_rate"] == 1.0 and s["both"] == 1.0 and s["n"] == 2


def test_검수_시트_왕복과_정답_수정():
    rows = [{"id": "i01", "text": "홍대 카페", "kind": "landmark", "expected": E, "status": "candidate"}]
    sheet = render_sheet(rows).replace("판정: ", "판정: O").replace("industry=cafe", "industry=bakery")
    mark, expected = parse_sheet(sheet)["i01"]
    assert mark == "O" and expected == {"region_name": "서교동", "industry_id": "bakery", "budget_krw": None}
