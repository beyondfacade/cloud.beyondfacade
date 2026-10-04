"""임베딩 모델 평가 CLI — 9개 조합을 같은 코퍼스·평가셋으로 재고 로컬용·API용 각 1종을 고른다 (Driving Adapter).

spec: docs/superpowers/specs/2026-10-04-embedding-benchmark-design.md
운영 DB·검색 경로는 건드리지 않는다. 코퍼스를 jsonl로 고정하고 모델별 최대 차원 벡터를 .npy로 1회 캐시한 뒤,
차원별로 잘라 numpy 전수 검색한다(benchmark_core).

실행 순서 (backend/에서):
  python -m apps.rag.adapter.inbound.cli.benchmark_embeddings snapshot
  python -m apps.rag.adapter.inbound.cli.benchmark_embeddings embed --model bge-m3|qwen3|gemini-001|gemini-2
  python -m apps.rag.adapter.inbound.cli.benchmark_embeddings latency --model ...
  python -m apps.rag.adapter.inbound.cli.benchmark_embeddings evaluate
"""

import argparse
import hashlib
import json
import os
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np

from apps.rag.adapter.inbound.cli.benchmark_core import (
    CorpusRow,
    aggregate,
    decide,
    percentile,
    render_report,
    resident_models,
    score_rows,
)
from apps.rag.adapter.outbound.embeddings.fp16_qwen3_adapter import Fp16Qwen3EmbeddingAdapter
from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter
from apps.rag.adapter.outbound.embeddings.ollama_bge_m3_adapter import OllamaBgeM3EmbeddingAdapter
from apps.rag.adapter.outbound.embeddings.ollama_qwen3_adapter import OllamaQwen3EmbeddingAdapter
from apps.rag.app.ports.output.rag_port import EmbeddingPort

# apps/rag/adapter/inbound/cli/benchmark_embeddings.py → parents[6] == 리포지토리 루트
_REPO_ROOT = Path(__file__).resolve().parents[6]
_CACHE = _REPO_ROOT / "data/eval/cache/embedding-benchmark"
_EVALSET = _REPO_ROOT / "data/eval/rag_evalset.jsonl"
_SHARD = 512


def _gemini_tokens(model: str) -> Callable[[list[str]], int]:
    def count(texts: list[str]) -> int:
        from google import genai

        from core.matrix.grid_keymaker_secret_manager import get_settings

        client = genai.Client(api_key=get_settings().gemini_api_key)
        return client.models.count_tokens(model=model, contents=texts).total_tokens

    return count


def _no_tokens(texts: list[str]) -> int:
    return 0  # 로컬 모델은 API 과금 대상이 아니다


@dataclass(frozen=True)
class ModelSpec:
    name: str
    group: str  # "local" | "api"
    max_dim: int
    doc_embedder: Callable[[], EmbeddingPort]
    query_embedder: Callable[[], EmbeddingPort]
    ollama_model: str | None  # 동시 상주 확인 대상 (API는 None)
    token_counter: Callable[[list[str]], int]


# 레지스트리 — 모델 이름 → 색인·질의 어댑터 (spec §2 표). qwen3는 운영 혼용 구도(색인 fp16 / 질의 Q4) 그대로.
MODELS: dict[str, ModelSpec] = {
    "bge-m3": ModelSpec("bge-m3", "local", 1024, OllamaBgeM3EmbeddingAdapter, OllamaBgeM3EmbeddingAdapter,
                        "bge-m3", _no_tokens),
    "qwen3": ModelSpec("qwen3", "local", 2560, lambda: Fp16Qwen3EmbeddingAdapter(dim=2560),
                       lambda: OllamaQwen3EmbeddingAdapter(dim=2560), "qwen3-embedding:4b", _no_tokens),
    "gemini-001": ModelSpec("gemini-001", "api", 3072,
                            lambda: GeminiEmbeddingAdapter(model="gemini-embedding-001", dim=3072),
                            lambda: GeminiEmbeddingAdapter(model="gemini-embedding-001", dim=3072),
                            None, _gemini_tokens("gemini-embedding-001")),
    "gemini-2": ModelSpec("gemini-2", "api", 3072,
                          lambda: GeminiEmbeddingAdapter(model="gemini-embedding-2", dim=3072),
                          lambda: GeminiEmbeddingAdapter(model="gemini-embedding-2", dim=3072),
                          None, _gemini_tokens("gemini-embedding-2")),
}

CONFIGS: list[tuple[str, int]] = [
    ("bge-m3", 1024), ("qwen3", 1536), ("qwen3", 2560),
    ("gemini-001", 1024), ("gemini-001", 1536), ("gemini-001", 2560),
    ("gemini-2", 1024), ("gemini-2", 1536), ("gemini-2", 2560),
]
BASELINE = ("qwen3", 1536)


def config_key(model: str, dim: int) -> str:
    return f"{model}@{dim}"


# ── 순수 헬퍼 ────────────────────────────────────────────────────────────


def corpus_to_jsonl(rows: list[CorpusRow]) -> str:
    return "".join(
        json.dumps(
            {"chunk_id": r.chunk_id, "source_type": r.source_type, "content": r.content,
             "published_at": r.published_at.isoformat() if r.published_at else None},
            ensure_ascii=False,
        ) + "\n"
        for r in rows
    )


def corpus_from_jsonl(text: str) -> list[CorpusRow]:
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        published = datetime.fromisoformat(d["published_at"]) if d["published_at"] else None
        rows.append(CorpusRow(d["chunk_id"], d["source_type"], d["content"], published))
    return rows


def pending_shards(total: int, shard: int, done: set[int]) -> list[int]:
    return [start for start in range(0, total, shard) if start not in done]


def missing_queries(cached: list[str], wanted: list[str]) -> list[str]:
    have = set(cached)
    out: list[str] = []
    for q in wanted:
        if q not in have:
            have.add(q)
            out.append(q)
    return out


def confirmed_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["status"] == "confirmed"]


# ── 파일·DB (어댑터 경계) ────────────────────────────────────────────────


def _load_evalset() -> list[dict]:
    return [json.loads(line) for line in _EVALSET.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_corpus() -> list[CorpusRow]:
    return corpus_from_jsonl((_CACHE / "corpus.jsonl").read_text(encoding="utf-8"))


def _atomic_write(path: Path, write: Callable) -> None:
    """임시 파일에 쓴 뒤 교체한다 — 중간에 죽어도 최종 이름에는 온전한 파일만 남는다."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        write(f)
    os.replace(tmp, path)


def _save_npy(path: Path, array: np.ndarray) -> None:
    _atomic_write(path, lambda f: np.save(f, array))


def _save_text(path: Path, text: str) -> None:
    _atomic_write(path, lambda f: f.write(text.encode("utf-8")))


def _check_corpus_sha(model: str, record: bool) -> None:
    """모델 캐시가 현재 코퍼스 스냅샷으로 만든 것인지 확인한다. record면 처음 만들 때 sha를 남긴다."""
    current = (_CACHE / "corpus.sha256").read_text(encoding="utf-8").strip()
    path = _CACHE / model / "corpus.sha256"
    if path.exists():
        if path.read_text(encoding="utf-8").strip() != current:
            raise RuntimeError(
                f"{model} 캐시가 현재 코퍼스와 다릅니다(snapshot 재실행?). "
                f"{_CACHE / model} 를 지우고 다시 embed 하세요."
            )
    elif record:
        _save_text(path, current + "\n")


def load_doc_matrix(model: str) -> np.ndarray:
    _check_corpus_sha(model, record=False)
    shards = sorted((_CACHE / model).glob("docs_*.npy"))
    return np.concatenate([np.load(p) for p in shards], axis=0)


def load_query_vectors(model: str) -> dict[str, np.ndarray]:
    texts = json.loads((_CACHE / model / "queries.json").read_text(encoding="utf-8"))
    matrix = np.load(_CACHE / model / "queries.npy")
    if len(texts) != len(matrix):
        raise ValueError(f"{model} 질의 캐시가 어긋났습니다: 텍스트 {len(texts)}개, 벡터 {len(matrix)}개")
    return dict(zip(texts, matrix))


def _cmd_snapshot(args) -> None:
    """rag_chunk 전량(만료 공고 포함 — spec §4)을 chunk_id 순서로 고정한다."""
    from sqlalchemy import select

    from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm
    from core.matrix.grid_oracle_database_manager import session_scope

    stmt = select(
        RagChunkOrm.chunk_id, RagChunkOrm.source_type, RagChunkOrm.content, RagChunkOrm.published_at
    ).order_by(RagChunkOrm.chunk_id)
    with session_scope() as session:
        rows = [CorpusRow(r.chunk_id, r.source_type, r.content, r.published_at) for r in session.execute(stmt).all()]
    text = corpus_to_jsonl(rows)
    _CACHE.mkdir(parents=True, exist_ok=True)
    (_CACHE / "corpus.jsonl").write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (_CACHE / "corpus.sha256").write_text(digest + "\n", encoding="utf-8")
    print(f"snapshot: {len(rows)}청크 sha256={digest[:12]} → {_CACHE}", flush=True)


def _cmd_embed(args) -> None:
    """문서는 샤드 단위로 이어서, 질의는 confirmed 문항 중 캐시에 없는 것만 임베딩한다."""
    spec = MODELS[args.model]
    out = _CACHE / spec.name
    out.mkdir(parents=True, exist_ok=True)
    corpus = load_corpus()
    _check_corpus_sha(spec.name, record=True)

    done = {int(p.stem.split("_")[1]) for p in out.glob("docs_*.npy")}
    tokens_path = out / "tokens.json"
    tokens: dict[str, int] = json.loads(tokens_path.read_text()) if tokens_path.exists() else {}
    todo = pending_shards(len(corpus), _SHARD, done)
    embedder = spec.doc_embedder() if todo else None
    for start in todo:
        texts = [r.content for r in corpus[start : start + _SHARD]]
        vectors = np.asarray(embedder.embed_documents(texts), dtype=np.float32)
        tokens[str(start)] = spec.token_counter(texts)  # 샤드 저장 전에 센다 — 실패하면 샤드도 안 남는다
        _save_text(tokens_path, json.dumps(tokens))
        _save_npy(out / f"docs_{start:06d}.npy", vectors)
        print(f"embed {spec.name} docs {start}~{start + len(texts) - 1} / {len(corpus)}", flush=True)

    q_texts_path, q_vecs_path = out / "queries.json", out / "queries.npy"
    cached = json.loads(q_texts_path.read_text(encoding="utf-8")) if q_texts_path.exists() else []
    new = missing_queries(cached, [r["question"] for r in confirmed_rows(_load_evalset())])
    if new:
        q_embedder = spec.query_embedder()
        vecs = np.asarray([q_embedder.embed_query(q) for q in new], dtype=np.float32)
        old = np.load(q_vecs_path)[: len(cached)] if q_vecs_path.exists() else np.zeros((0, vecs.shape[1]), dtype=np.float32)
        _save_npy(q_vecs_path, np.concatenate([old, vecs], axis=0))
        _save_text(q_texts_path, json.dumps(cached + new, ensure_ascii=False))
    print(f"embed {spec.name}: 문서 샤드 {len(todo)}개 새로, 질의 {len(new)}건 새로 (총 토큰 {sum(tokens.values())})", flush=True)


_OLLAMA = "http://127.0.0.1:11434"
_LLM_RESIDENT = "gemma4:12b"  # 분석 폴백 LLM — 운영에서 임베더와 같이 GPU에 올라간다
_LATENCY_REPEATS = 3


def _ollama_load_pair(ollama_model: str) -> None:
    """LLM과 임베더를 둘 다 올린다(keep_alive 10분)."""
    with httpx.Client(base_url=_OLLAMA, timeout=300.0) as client:
        client.post("/api/generate", json={"model": _LLM_RESIDENT, "prompt": "", "keep_alive": "10m"}).raise_for_status()
        client.post("/api/embed", json={"model": ollama_model, "input": ["상주 확인"], "keep_alive": "10m"}).raise_for_status()


def _ollama_resident(ollama_model: str) -> tuple[bool, int]:
    """지금 둘 다 상주하는지(읽기만 — 다시 올리지 않는다) + nvidia-smi 사용 메모리(MiB)."""
    with httpx.Client(base_url=_OLLAMA, timeout=30.0) as client:
        names = resident_models(client.get("/api/ps").json())
    used = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True,
    ).stdout.split()[0]
    llm_up = any(n.startswith(_LLM_RESIDENT) for n in names)
    emb_up = any(n.split(":")[0] == ollama_model.split(":")[0] for n in names)
    return llm_up and emb_up, int(used)


def _cmd_latency(args) -> None:
    """질의 임베딩 지연 p50/p95 (confirmed 질문 × 3회, 네트워크 포함). 로컬은 gemma4 동시 상주를 먼저 만든다."""
    spec = MODELS[args.model]
    questions = [r["question"] for r in confirmed_rows(_load_evalset())]
    embedder = spec.query_embedder()
    embedder.embed_query("워밍업")  # 콜드스타트(모델 로드)는 지연에서 뺀다
    coexist, vram = (None, None)
    if spec.ollama_model:
        _ollama_load_pair(spec.ollama_model)
        coexist, vram = _ollama_resident(spec.ollama_model)
    samples: list[float] = []
    for _ in range(_LATENCY_REPEATS):
        for q in questions:
            started = time.perf_counter()
            embedder.embed_query(q)
            samples.append((time.perf_counter() - started) * 1000)
    if spec.ollama_model:  # 측정 중에 LLM이 밀려났는지 다시 본다 (읽기만)
        coexist = coexist and _ollama_resident(spec.ollama_model)[0]
    p50 = percentile(samples, 50)
    result = {
        "model": spec.name, "n": len(samples), "p50_ms": p50, "p95_ms": percentile(samples, 95),
        "coexist": coexist, "vram_used_mib": vram,
        "retry_429": getattr(embedder, "retry_count", None),
        "effective_p50_ms": max(p50, 60000 / args.rpm) if args.rpm else None,
    }
    (_CACHE / spec.name).mkdir(parents=True, exist_ok=True)
    _save_text(_CACHE / spec.name / "latency.json", json.dumps(result, ensure_ascii=False, indent=2))
    print(f"latency {spec.name}: p50 {p50:.0f}ms p95 {result['p95_ms']:.0f}ms 동시상주={coexist} VRAM={vram}MiB", flush=True)


def _load_latency(model: str) -> dict:
    path = _CACHE / model / "latency.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _cmd_evaluate(args) -> None:
    corpus = load_corpus()
    rows = confirmed_rows(_load_evalset())
    configs: dict[str, dict] = {}
    mrr_by: dict[str, list[float]] = {}
    for model, dim in CONFIGS:
        key = config_key(model, dim)
        scored = score_rows(load_doc_matrix(model), load_query_vectors(model), corpus, rows, dim)
        mrr_by[key] = [s["mrr"] for s in scored]
        tokens_path = _CACHE / model / "tokens.json"
        configs[key] = {
            "group": MODELS[model].group, "dim": dim, "agg": aggregate(scored), "latency": _load_latency(model),
            "tokens": sum(json.loads(tokens_path.read_text(encoding="utf-8")).values()) if tokens_path.exists() else 0,
        }
        print(f"evaluate {key}: MRR {configs[key]['agg']['all']['mrr']:.3f}", flush=True)

    latency = {m: _load_latency(m) for m in MODELS}
    decision = decide(
        mrr_by, {k: c["dim"] for k, c in configs.items()}, {k: c["group"] for k, c in configs.items()},
        latency, baseline=config_key(*BASELINE),
    )
    date = datetime.now().strftime("%Y-%m-%d")
    results = {
        "date": date,
        "corpus": {"chunks": len(corpus), "sha256": (_CACHE / "corpus.sha256").read_text().strip()},
        "rows": len(rows), "configs": configs, "decision": decision, "per_row_mrr": mrr_by,
    }
    out = _REPO_ROOT / f"data/eval/results/embedding-benchmark-{date}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "report.md").write_text(render_report(results), encoding="utf-8")
    (out / "corpus.jsonl.sha256").write_text(results["corpus"]["sha256"] + "\n", encoding="utf-8")
    print(f"evaluate: 로컬 {decision['local']['choice']} / API {decision['api']['choice']} → {out}", flush=True)


_COMMANDS: dict[str, Callable] = {
    "snapshot": _cmd_snapshot, "embed": _cmd_embed, "latency": _cmd_latency, "evaluate": _cmd_evaluate,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=list(_COMMANDS))
    parser.add_argument("--model", choices=list(MODELS))
    parser.add_argument("--rpm", type=float, default=None, help="API 분당 한도 — effective 지연 = max(p50, 60000/RPM)")
    args = parser.parse_args()
    _COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
