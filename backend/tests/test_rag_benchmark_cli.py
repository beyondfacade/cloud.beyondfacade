"""벤치마크 CLI 순수 헬퍼 — 레지스트리·코퍼스 직렬화·샤드 이어하기·질의 캐시. DB·네트워크 없음."""

from datetime import datetime

from apps.rag.adapter.inbound.cli.benchmark_core import CorpusRow
from apps.rag.adapter.inbound.cli.benchmark_embeddings import (
    BASELINE,
    CONFIGS,
    MODELS,
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
