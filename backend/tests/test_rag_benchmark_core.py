"""임베딩 벤치마크 순수 로직 — 절단·전수 검색·접기·지표·bootstrap. DB·네트워크 없음."""

from datetime import datetime

import numpy as np
import pytest

from apps.rag.adapter.inbound.cli.benchmark_core import (
    CorpusRow,
    ndcg_at_k,
    paired_bootstrap_ci,
    percentile,
    rank_chunk_ids,
    resident_models,
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
