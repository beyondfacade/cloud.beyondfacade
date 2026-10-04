"""임베딩 벤치마크 순수 로직 — 절단·정규화·전수 검색·지표·bootstrap (numpy만, DB·네트워크 없음).

운영 검색(RagSearchInteractor)과 같은 규칙으로 순위를 낸다: source_type 안에서만 찾고, 뉴스는 같은 사건을 접는다.
HNSW 대신 전수 코사인이라 근사 오차가 없다 — 임베딩 품질만 비교한다(spec §2-3).
"""

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from apps.rag.adapter.inbound.cli.evaluate_rag import hit_at_k
from apps.rag.domain.entities.rag_chunk_entity import RagHit
from apps.rag.domain.services.same_event_collapser import Collapser, collapse_same_event

# rag_interactor._COLLAPSERS·_COLLAPSE_FETCH_FACTOR와 같아야 한다 (운영 검색 재현)
COLLAPSERS: dict[str, Collapser] = {"news": collapse_same_event}
_COLLAPSE_FETCH_FACTOR = 10


@dataclass(frozen=True)
class CorpusRow:
    chunk_id: str
    source_type: str
    content: str
    published_at: datetime | None


def truncate_normalize(matrix: np.ndarray, dim: int) -> np.ndarray:
    """MRL 절단 — 앞 dim개 성분만 남기고 행마다 L2 재정규화."""
    if dim > matrix.shape[1]:
        raise ValueError(f"절단 차원 {dim}이 원래 차원 {matrix.shape[1]}보다 크다")
    cut = np.asarray(matrix[:, :dim], dtype=np.float32)
    norms = np.linalg.norm(cut, axis=1, keepdims=True)
    norms[norms < 1e-12] = 1.0
    return cut / norms


def top_scored(
    doc_matrix: np.ndarray, query_vec: np.ndarray, candidates: np.ndarray, k: int
) -> list[tuple[int, float]]:
    """candidates(문서 행 인덱스) 안에서 코사인 상위 k개. 점수 내림차순, 동점은 인덱스 오름차순(결정적)."""
    scores = doc_matrix[candidates] @ query_vec
    order = np.lexsort((candidates, -scores))
    return [(int(candidates[i]), float(scores[i])) for i in order[:k]]


def _as_hit(row: CorpusRow, score: float) -> RagHit:
    return RagHit(
        chunk_id=row.chunk_id, source_type=row.source_type, source_id=row.chunk_id.split(":", 1)[1],
        content=row.content, score=score, url=None, org=None, published_at=row.published_at,
    )


def _no_collapse(hits: list[RagHit]) -> list[RagHit]:
    return hits


def rank_chunk_ids(
    doc_matrix: np.ndarray, query_vec: np.ndarray, corpus: list[CorpusRow], candidates: np.ndarray, depth: int
) -> list[str]:
    """운영 검색 규칙의 상위 depth개 chunk_id. 접기 대상 원천은 depth의 10배를 가져와 접은 뒤 자른다."""
    source_type = corpus[int(candidates[0])].source_type if len(candidates) else ""
    collapser = COLLAPSERS.get(source_type, _no_collapse)
    fetch = depth * _COLLAPSE_FETCH_FACTOR if source_type in COLLAPSERS else depth
    hits = [_as_hit(corpus[i], s) for i, s in top_scored(doc_matrix, query_vec, candidates, fetch)]
    return [h.chunk_id for h in collapser(hits)[:depth]]


def top1(relevant: set[str], ranked: list[str]) -> float:
    return hit_at_k(relevant, ranked, 1)


def ndcg_at_k(relevant: set[str], ranked: list[str], k: int = 10) -> float:
    """이진 관련도 nDCG. 동치 정답 여럿을 모두 찾을수록 높다(보조 지표 — 주 지표는 MRR)."""
    dcg = sum(1.0 / math.log2(i + 2) for i, cid in enumerate(ranked[:k]) if cid in relevant)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal if ideal else 0.0


def paired_bootstrap_ci(
    a: list[float], b: list[float], n: int = 10_000, seed: int = 0
) -> tuple[float, float, float]:
    """문항별 점수 차이(a−b)의 평균과 95% 구간. 하한 ≤ 0 ≤ 상한이면 동률."""
    if len(a) != len(b):
        raise ValueError(f"문항 수가 다르다: {len(a)} != {len(b)}")
    x = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), size=(n, len(x)))].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(x.mean()), float(lo), float(hi)


def percentile(samples: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(samples, dtype=np.float64), q))
