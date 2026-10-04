"""임베딩 벤치마크 순수 로직 — 절단·전수 검색·접기·지표·bootstrap. DB·네트워크 없음."""

from datetime import datetime

import numpy as np
import pytest

from apps.rag.adapter.inbound.cli.benchmark_core import (
    CorpusRow,
    aggregate,
    decide,
    ndcg_at_k,
    paired_bootstrap_ci,
    percentile,
    pick_winner,
    rank_chunk_ids,
    render_report,
    resident_models,
    score_rows,
    top1,
    top_scored,
    truncate_normalize,
)


def test_절단_후_각_행의_노름이_1이다():
    m = np.array([[3.0, 4.0, 12.0], [1.0, 0.0, 5.0]])
    out = truncate_normalize(m, 2)
    assert out.shape == (2, 2)
    assert np.allclose(np.linalg.norm(out, axis=1), 1.0)
    assert np.allclose(out[0], [0.6, 0.8])


def test_절단_차원이_원래보다_크면_에러():
    with pytest.raises(ValueError):
        truncate_normalize(np.ones((1, 3)), 4)


def test_전수_검색은_후보_안에서만_점수순_동점은_인덱스순():
    docs = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [0.6, 0.8]])
    q = np.array([1.0, 0.0])
    got = top_scored(docs, q, np.array([1, 2, 3, 0]), k=3)
    assert [i for i, _ in got] == [0, 2, 3]  # 0과 2 동점 → 인덱스 오름차순


def _row(cid, title, day):
    return CorpusRow(cid, cid.split(":")[0], f"{title}\n본문", datetime(2026, 9, day))


def test_뉴스는_같은_사건을_접어_다른_사건이_순위에_오른다():
    corpus = [
        _row("news:a", "망원시장 야시장 개장 상인 기대", 1),
        _row("news:b", "망원시장 야시장 개장 상인 기대감", 1),
        _row("news:c", "신촌 상권 임대료 상승", 2),
    ]
    docs = np.array([[1.0, 0.0], [0.99, 0.14], [0.6, 0.8]])
    docs = docs / np.linalg.norm(docs, axis=1, keepdims=True)
    ranked = rank_chunk_ids(docs, np.array([1.0, 0.0]), corpus, np.array([0, 1, 2]), depth=2)
    assert ranked == ["news:a", "news:c"]


def test_공고는_접지_않는다():
    corpus = [_row("funding:a", "청년 창업 자금", 1), _row("funding:b", "청년 창업 자금", 1)]
    docs = np.array([[1.0, 0.0], [0.99, 0.14]])
    ranked = rank_chunk_ids(docs, np.array([1.0, 0.0]), corpus, np.array([0, 1]), depth=2)
    assert ranked == ["funding:a", "funding:b"]


def test_top1은_첫_순위만_본다():
    assert top1({"x"}, ["x", "y"]) == 1.0
    assert top1({"y"}, ["x", "y"]) == 0.0


def test_ndcg는_첫_적중_순위가_낮을수록_작고_정답이_없으면_0():
    assert ndcg_at_k({"a"}, ["a", "b"], k=10) == 1.0
    assert ndcg_at_k({"b"}, ["a", "b"], k=10) == pytest.approx(1 / np.log2(3))
    assert ndcg_at_k({"z"}, ["a", "b"], k=10) == 0.0
    assert ndcg_at_k(set(), ["a"], k=10) == 0.0


def test_ndcg는_동치_정답_여럿을_찾으면_더_높다():
    one = ndcg_at_k({"a", "b"}, ["a", "x"], k=10)
    two = ndcg_at_k({"a", "b"}, ["a", "b"], k=10)
    assert two == 1.0 and one < two


def test_bootstrap은_시드가_같으면_같은_구간():
    a, b = [1.0, 0.5, 1.0, 0.0] * 10, [0.5, 0.5, 1.0, 0.0] * 10
    assert paired_bootstrap_ci(a, b) == paired_bootstrap_ci(a, b)


def test_bootstrap_같은_점수면_차이와_구간이_0():
    diff, lo, hi = paired_bootstrap_ci([1.0, 0.5, 0.0], [1.0, 0.5, 0.0])
    assert (diff, lo, hi) == (0.0, 0.0, 0.0)


def test_bootstrap_일관되게_높으면_하한이_0보다_크다():
    diff, lo, _ = paired_bootstrap_ci([1.0] * 50, [0.5] * 50)
    assert diff == 0.5 and lo > 0


def test_bootstrap_길이가_다르면_에러():
    with pytest.raises(ValueError):
        paired_bootstrap_ci([1.0], [1.0, 0.0])


def test_백분위():
    assert percentile([10.0, 20.0, 30.0, 40.0, 50.0], 50) == 30.0


def test_상주_모델_이름을_모은다():
    ps = {"models": [{"name": "gemma4:12b", "size_vram": 1}, {"name": "bge-m3:latest", "size_vram": 1}]}
    assert resident_models(ps) == {"gemma4:12b", "bge-m3:latest"}
    assert resident_models({}) == set()


def test_행_점수는_원천_안에서만_찾고_메타를_싣는다():
    corpus = [
        CorpusRow("funding:a", "funding", "청년 창업\n.", None),
        CorpusRow("news:x", "news", "다른 사건\n.", datetime(2026, 9, 1)),
        CorpusRow("funding:b", "funding", "수출 바우처\n.", None),
    ]
    docs = np.array([[0.6, 0.8], [1.0, 0.0], [0.0, 1.0]])
    rows = [{"question": "q", "relevant_ids": ["funding:a"], "source_type": "funding", "status": "confirmed",
             "subset": "hard", "hard_kind": "colloquial"}]
    out = score_rows(docs, {"q": np.array([1.0, 0.0])}, corpus, rows, dim=2)
    assert out[0]["top1"] == 1.0 and out[0]["mrr"] == 1.0  # news:x가 더 가깝지만 원천이 달라 제외
    assert (out[0]["subset"], out[0]["hard_kind"]) == ("hard", "colloquial")


def test_subset이_없는_기존_행은_base로_센다():
    scored = [
        {"source_type": "funding", "subset": "base", "hard_kind": None, "top1": 1.0, "hit5": 1.0, "mrr": 1.0, "ndcg10": 1.0},
        {"source_type": "news", "subset": "hard", "hard_kind": "news_event", "top1": 0.0, "hit5": 1.0, "mrr": 0.5, "ndcg10": 0.5},
    ]
    agg = aggregate(scored)
    assert agg["all"]["mrr"] == 0.75 and agg["all"]["n"] == 2
    assert agg["subset:base"]["mrr"] == 1.0
    assert agg["hard:news_event"]["top1"] == 0.0
    assert "hard:None" not in agg


def test_동률이면_낮은_차원이_이긴다():
    mrr = {"g@1024": [1.0, 0.5] * 20, "g@2560": [1.0, 0.5] * 20}
    winner, tied = pick_winner(mrr, {"g@1024": 1024, "g@2560": 2560}, {}, ["g@2560", "g@1024"])
    assert winner == "g@1024" and tied == ["g@1024", "g@2560"]


def test_유의하게_높으면_차원이_커도_이긴다():
    mrr = {"g@1024": [0.5] * 40, "g@2560": [1.0] * 40}
    winner, tied = pick_winner(mrr, {"g@1024": 1024, "g@2560": 2560}, {}, ["g@1024", "g@2560"])
    assert winner == "g@2560" and tied == ["g@2560"]


def _decide(local_mrr, lat):
    mrr = {"qwen3@1536": [0.5] * 40, "bge-m3@1024": local_mrr, "gemini-2@1536": [0.9] * 40}
    dims = {"qwen3@1536": 1536, "bge-m3@1024": 1024, "gemini-2@1536": 1536}
    groups = {"qwen3@1536": "local", "bge-m3@1024": "local", "gemini-2@1536": "api"}
    return decide(mrr, dims, groups, lat, baseline="qwen3@1536")


_OK = {"coexist": True, "p95_ms": 100.0}


def test_로컬_1위가_기준선보다_유의하게_나으면_교체():
    out = _decide([1.0] * 40, {"qwen3": _OK, "bge-m3": _OK})
    assert out["local"]["choice"] == "bge-m3@1024" and out["local"]["replace"] is True
    assert out["api"]["choice"] == "gemini-2@1536"


def test_로컬_1위가_유의하지_않으면_기준선_유지():
    out = _decide([0.5] * 40, {"qwen3": _OK, "bge-m3": _OK})
    assert out["local"]["choice"] == "qwen3@1536" and out["local"]["replace"] is False


def test_게이트를_못_넘은_로컬_조합은_후보에서_빠진다():
    out = _decide([1.0] * 40, {"qwen3": _OK, "bge-m3": {"coexist": True, "p95_ms": 900.0}})
    assert out["local"]["choice"] == "qwen3@1536"
    assert out["local"]["gate_failed"] == ["bge-m3@1024"]


def test_보고서에_9조합_표와_판정이_들어간다():
    results = {
        "date": "2026-10-04", "corpus": {"chunks": 3, "sha256": "abc"}, "rows": 2,
        "configs": {"qwen3@1536": {"group": "local", "dim": 1536, "agg": {
            "all": {"n": 2, "top1": 1.0, "hit5": 1.0, "mrr": 1.0, "ndcg10": 1.0},
            "subset:hard": {"n": 1, "top1": 1.0, "hit5": 1.0, "mrr": 1.0, "ndcg10": 1.0}},
            "latency": {"p50_ms": 30.0, "p95_ms": 50.0, "coexist": True, "vram_used_mib": 9000}, "tokens": 0}},
        "decision": {"local": {"choice": "qwen3@1536", "replace": False, "winner": "qwen3@1536", "tied": ["qwen3@1536"],
                               "gate_failed": [], "vs_baseline": [0.0, 0.0, 0.0]},
                     "api": {"choice": None, "winner": None, "tied": [], "gate_failed": []}},
    }
    md = render_report(results)
    assert "| qwen3@1536 | local | 1536 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 30 | 50 | O |" in md
    assert "로컬: **qwen3@1536** (현행 유지)" in md
