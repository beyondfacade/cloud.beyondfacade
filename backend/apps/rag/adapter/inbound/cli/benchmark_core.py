"""임베딩 벤치마크 순수 로직 — 절단·정규화·전수 검색·지표·bootstrap (numpy만, DB·네트워크 없음).

운영 검색(RagSearchInteractor)과 같은 규칙으로 순위를 낸다: source_type 안에서만 찾고, 뉴스는 같은 사건을 접는다.
HNSW 대신 전수 코사인이라 근사 오차가 없다 — 임베딩 품질만 비교한다(spec §2-3).
"""

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import mean

import numpy as np

from apps.rag.adapter.inbound.cli.evaluate_rag import hit_at_k, mrr
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


def resident_models(ps_json: dict) -> set[str]:
    """Ollama /api/ps 응답 → 지금 메모리에 올라 있는 모델 이름."""
    return {m["name"] for m in ps_json.get("models", [])}


_DEPTH = 10  # MRR·nDCG 모두 상위 10 기준 (기존 evaluate_rag의 MRR은 상위 5 — 보고서에 명시)
_METRICS = ("top1", "hit5", "mrr", "ndcg10")


def score_rows(
    doc_matrix: np.ndarray, query_vecs: dict[str, np.ndarray], corpus: list[CorpusRow], rows: list[dict], dim: int
) -> list[dict]:
    docs = truncate_normalize(doc_matrix, dim)
    by_source: dict[str, list[int]] = {}
    for i, row in enumerate(corpus):
        by_source.setdefault(row.source_type, []).append(i)
    candidates = {k: np.asarray(v) for k, v in by_source.items()}
    out = []
    for row in rows:
        q = truncate_normalize(query_vecs[row["question"]][None, :], dim)[0]
        ranked = rank_chunk_ids(docs, q, corpus, candidates[row["source_type"]], _DEPTH)
        relevant = set(row["relevant_ids"])
        out.append({
            "question": row["question"], "source_type": row["source_type"],
            "subset": row.get("subset", "base"), "hard_kind": row.get("hard_kind"),
            "top1": top1(relevant, ranked), "hit5": hit_at_k(relevant, ranked, 5),
            "mrr": mrr(relevant, ranked), "ndcg10": ndcg_at_k(relevant, ranked, _DEPTH),
        })
    return out


def aggregate(scored: list[dict]) -> dict[str, dict[str, float]]:
    groups: dict[str, list[dict]] = {"all": scored}
    for s in scored:
        groups.setdefault(f"subset:{s['subset']}", []).append(s)
        groups.setdefault(f"source:{s['source_type']}", []).append(s)
        if s["hard_kind"]:
            groups.setdefault(f"hard:{s['hard_kind']}", []).append(s)
    return {
        key: {"n": len(items), **{m: mean(i[m] for i in items) for m in _METRICS}}
        for key, items in groups.items()
    }


def pick_winner(
    mrr_by: dict[str, list[float]], dims: dict[str, int], p95: dict[str, float | None], eligible: list[str]
) -> tuple[str, list[str]]:
    """평균 MRR 1위와 bootstrap 동률인 조합 중 (낮은 차원, 짧은 p95, 이름) 최소."""
    best = max(eligible, key=lambda c: (mean(mrr_by[c]), -dims[c]))
    tied = sorted(c for c in eligible if c == best or paired_bootstrap_ci(mrr_by[best], mrr_by[c])[1] <= 0)
    winner = min(tied, key=lambda c: (dims[c], p95.get(c) or float("inf"), c))
    return winner, tied


def _model_of(config: str) -> str:
    return config.split("@", 1)[0]


def _local_gate(latency: dict, p95_limit_ms: float) -> bool:
    return latency.get("coexist") is True and latency.get("p95_ms", float("inf")) <= p95_limit_ms


def decide(
    mrr_by: dict[str, list[float]], dims: dict[str, int], groups: dict[str, str],
    latency: dict[str, dict], baseline: str, p95_limit_ms: float = 500.0,
) -> dict:
    p95 = {c: latency.get(_model_of(c), {}).get("p95_ms") for c in mrr_by}
    out: dict[str, dict] = {}

    local = [c for c in mrr_by if groups[c] == "local"]
    passed = [c for c in local if _local_gate(latency.get(_model_of(c), {}), p95_limit_ms)]
    eligible = passed or [baseline]  # 전부 게이트 탈락이면 현행 유지
    winner, tied = pick_winner(mrr_by, dims, p95, eligible)
    vs = paired_bootstrap_ci(mrr_by[winner], mrr_by[baseline])
    replace = winner != baseline and vs[1] > 0
    out["local"] = {
        "winner": winner, "tied": tied, "choice": winner if replace else baseline, "replace": replace,
        "vs_baseline": list(vs), "gate_failed": sorted(set(local) - set(passed)),
    }

    api = [c for c in mrr_by if groups[c] == "api"]
    api_winner, api_tied = pick_winner(mrr_by, dims, p95, api) if api else (None, [])
    out["api"] = {"winner": api_winner, "tied": api_tied, "choice": api_winner, "gate_failed": []}
    return out


def _fmt(v: float | None, spec: str) -> str:
    return "-" if v is None else format(v, spec)


def render_report(results: dict) -> str:
    lines = [
        f"# 임베딩 모델 평가 결과 ({results['date']})",
        "",
        f"- 코퍼스 {results['corpus']['chunks']}청크 (sha256 `{results['corpus']['sha256'][:12]}`, 만료 공고 포함)",
        f"- 평가 문항 {results['rows']}건 (confirmed). MRR·nDCG는 상위 10 기준 — 기존 evaluate_rag(상위 5)와 다르다.",
        "",
        "| 조합 | 그룹 | 차원 | top-1 | Hit@5 | MRR | nDCG@10 | MRR(hard) | p50 ms | p95 ms | 동시상주 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key, c in results["configs"].items():
        a, h, lat = c["agg"]["all"], c["agg"].get("subset:hard", {}), c.get("latency") or {}
        coexist = {True: "O", False: "X"}.get(lat.get("coexist"), "-")
        lines.append(
            f"| {key} | {c['group']} | {c['dim']} | {a['top1']:.3f} | {a['hit5']:.3f} | {a['mrr']:.3f} | "
            f"{a['ndcg10']:.3f} | {_fmt(h.get('mrr'), '.3f')} | {_fmt(lat.get('p50_ms'), '.0f')} | "
            f"{_fmt(lat.get('p95_ms'), '.0f')} | {coexist} |"
        )
    local, api = results["decision"]["local"], results["decision"]["api"]
    verdict = "교체" if local["replace"] else "현행 유지"
    lines += [
        "",
        "## 판정",
        "",
        f"- 로컬: **{local['choice']}** ({verdict}) — 1위 {local['winner']}, 동률 {', '.join(local['tied'])}, "
        f"기준선 대비 MRR 차 {local['vs_baseline'][0]:+.3f} [{local['vs_baseline'][1]:+.3f}, {local['vs_baseline'][2]:+.3f}]"
        + (f", 게이트 탈락 {', '.join(local['gate_failed'])}" if local["gate_failed"] else ""),
        f"- API: **{api['choice']}** — 동률 {', '.join(api['tied'])}",
        "",
        "## 한계",
        "",
        "- 기존 confirmed 180건은 qwen 운영 시절에 검수돼 qwen 쪽으로 기울었을 수 있다.",
        "- 만료 공고를 코퍼스에 남겼다(운영 검색은 뺀다). 모든 조합에 같은 방해 문서로 작용한다.",
        "- 지연은 모델 단위로 쟀다(같은 모델의 차원별 지연은 같다고 본다).",
    ]
    return "\n".join(lines) + "\n"
