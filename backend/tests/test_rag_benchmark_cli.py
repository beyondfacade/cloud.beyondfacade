"""벤치마크 CLI 순수 헬퍼 — 레지스트리·코퍼스 직렬화·샤드 이어하기·질의 캐시. DB·네트워크 없음."""

import json
from argparse import Namespace
from datetime import datetime

import numpy as np
import pytest

from apps.rag.adapter.inbound.cli import benchmark_embeddings as be
from apps.rag.adapter.inbound.cli.benchmark_core import CorpusRow
from apps.rag.adapter.inbound.cli.benchmark_embeddings import (
    BASELINE,
    CONFIGS,
    MODELS,
    ModelSpec,
    config_key,
    confirmed_rows,
    corpus_from_jsonl,
    corpus_to_jsonl,
    missing_queries,
    pending_shards,
)


def test_조합은_스펙의_9개이고_기준선은_qwen3_1536():
    assert [config_key(m, d) for m, d in CONFIGS] == [
        "bge-m3@1024", "qwen3@1536", "qwen3@2560",
        "gemini-001@1024", "gemini-001@1536", "gemini-001@2560",
        "gemini-2@1024", "gemini-2@1536", "gemini-2@2560",
    ]
    assert BASELINE == ("qwen3", 1536)


def test_조합_차원은_모델_최대_차원을_넘지_않고_그룹은_로컬_API():
    assert all(d <= MODELS[m].max_dim for m, d in CONFIGS)
    assert {m: MODELS[m].group for m in MODELS} == {
        "bge-m3": "local", "qwen3": "local", "gemini-001": "api", "gemini-2": "api",
    }


def test_코퍼스_직렬화_왕복():
    rows = [CorpusRow("news:a", "news", "제목\n본문", datetime(2026, 9, 1, 9, 30)), CorpusRow("funding:b", "funding", "x", None)]
    assert corpus_from_jsonl(corpus_to_jsonl(rows)) == rows


def test_샤드는_끝난_것을_건너뛰고_마지막은_짧아도_포함():
    assert pending_shards(1100, 512, done={0}) == [512, 1024]


def test_질의_캐시는_없는_질문만_순서대로_중복_없이():
    assert missing_queries(["a", "b"], ["b", "c", "a", "c", "d"]) == ["c", "d"]


def test_평가_대상은_confirmed만():
    rows = [{"status": "confirmed", "question": "a"}, {"status": "rejected", "question": "b"}, {"status": "candidate", "question": "c"}]
    assert [r["question"] for r in confirmed_rows(rows)] == ["a"]


# ── 캐시 무결성 (임시 디렉터리 + 가짜 어댑터) ──────────────────────────────


class _FakeEmbedder:
    def embed_documents(self, texts):
        return [[1.0, 0.0]] * len(texts)

    def embed_query(self, text):
        return [0.0, 1.0]


def _setup(monkeypatch, tmp_path, counter=lambda texts: 0, sha="aaa"):
    monkeypatch.setattr(be, "_CACHE", tmp_path)
    monkeypatch.setattr(be, "_EVALSET", tmp_path / "evalset.jsonl")
    (tmp_path / "corpus.jsonl").write_text(corpus_to_jsonl([CorpusRow("a", "news", "x", None), CorpusRow("b", "news", "y", None)]), encoding="utf-8")
    (tmp_path / "corpus.sha256").write_text(sha + "\n", encoding="utf-8")
    rows = [{"status": "confirmed", "question": q} for q in ("q1", "q2")]
    (tmp_path / "evalset.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    spec = ModelSpec("fake", "local", 2, _FakeEmbedder, _FakeEmbedder, None, counter)
    monkeypatch.setitem(MODELS, "fake", spec)
    return Namespace(model="fake")


def test_코퍼스_sha가_다르면_embed가_중단된다(monkeypatch, tmp_path):
    args = _setup(monkeypatch, tmp_path)
    be._cmd_embed(args)
    (tmp_path / "corpus.sha256").write_text("bbb\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="코퍼스"):
        be._cmd_embed(args)
    with pytest.raises(RuntimeError, match="코퍼스"):
        be.load_doc_matrix("fake")


def test_질의_텍스트와_벡터_수가_다르면_로드가_실패한다(monkeypatch, tmp_path):
    args = _setup(monkeypatch, tmp_path)
    be._cmd_embed(args)
    np.save(tmp_path / "fake" / "queries.npy", np.zeros((3, 2), dtype=np.float32))
    with pytest.raises(ValueError, match="질의"):
        be.load_query_vectors("fake")


def test_토큰_계산이_실패하면_샤드_파일이_남지_않는다(monkeypatch, tmp_path):
    def boom(texts):
        raise RuntimeError("count_tokens 실패")

    args = _setup(monkeypatch, tmp_path, counter=boom)
    with pytest.raises(RuntimeError, match="count_tokens"):
        be._cmd_embed(args)
    assert list((tmp_path / "fake").glob("docs_*.npy")) == []


def test_질의_추가는_벡터가_더_많은_부분_저장_상태에서도_정렬을_유지한다(monkeypatch, tmp_path):
    args = _setup(monkeypatch, tmp_path)
    out = tmp_path / "fake"
    out.mkdir()
    (out / "queries.json").write_text(json.dumps(["q1"]), encoding="utf-8")
    np.save(out / "queries.npy", np.ones((2, 2), dtype=np.float32))  # 텍스트보다 벡터가 1개 많다
    be._cmd_embed(args)
    vectors = be.load_query_vectors("fake")
    assert list(vectors) == ["q1", "q2"]
    assert vectors["q1"].tolist() == [1.0, 1.0] and vectors["q2"].tolist() == [0.0, 1.0]
