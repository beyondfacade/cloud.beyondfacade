# 임베딩 모델 평가 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 9개 임베딩 조합(bge-m3·qwen3·gemini-001·gemini-2 × 차원)을 같은 코퍼스·같은 평가셋으로 재고, 로컬용·API용 각 1종을 판정 규칙대로 고른다.

**Architecture:** 운영 DB는 건드리지 않는다. `rag_chunk`를 jsonl 스냅샷으로 고정 → 모델별로 최대 차원 벡터를 `.npy`로 1회 캐시 → 차원별로 앞부분 절단·재정규화 → numpy 전수 코사인 검색(운영과 같은 `source_type` 필터·뉴스 같은 사건 접기) → 지표·bootstrap·판정 → `report.md`. 평가셋에는 Claude가 만든 어려운 질문 약 60건을 기존 생성·판정·검수 CLI 흐름으로 더한다.

**Tech Stack:** Python 3.14, numpy 2.5, sentence-transformers 5.6(fp16 qwen), httpx(Ollama), google-genai(Gemini), anthropic(질문 생성·판정), pytest.

**Spec:** `docs/superpowers/specs/2026-10-04-embedding-benchmark-design.md`

## Global Constraints

- 9개 조합 고정: `bge-m3@1024`, `qwen3@1536`, `qwen3@2560`, `gemini-001@1024/1536/2560`, `gemini-2@1024/1536/2560`. 추가 후보 금지.
- 기준선 = `qwen3@1536` (색인 fp16 / 질의 Ollama Q4 + `QUERY_PROMPT`).
- 운영 동작 무변경: 어댑터 새 인자의 기본값은 현재 값(1536, `gemini-embedding-001`). `rag_dependencies.py` 레지스트리는 수정 금지.
- 주 지표 = 전체 문항 MRR(순위 깊이 10). 동률 = paired bootstrap(n=10000, seed=0) 95% 구간이 0 포함. 동률이면 낮은 차원 → 짧은 p95.
- 로컬 하드 게이트: `gemma4:12b`와 동시 상주 + 질의 p95 ≤ 500ms. 로컬 1위가 기준선보다 유의하게 낫지 않으면 기준선 유지.
- 어려운 질문 표본 선정에 어떤 임베딩 모델도 쓰지 않는다(제목 토큰 Jaccard·보도일 같은 메타데이터만).
- `if/elif` 타입 분기 대신 dict 디스패치·Strategy (CLAUDE.md §5). 테스트 제목은 한국어 서술문 가능, 기존 파일 스타일을 따른다.
- `data/`는 `.gitignore`의 `/data/` 대상 — 커밋할 평가 파일은 `git add -f`. 캐시(`data/eval/cache/`)는 커밋하지 않는다.
- 버전: 백엔드 `v0.64.0` (main 최신 v0.63.0). `backend/docs/backend_ver_log.md`에 Task마다 항목을 덧붙인다.

## 실행 환경 (모든 Task 공통)

워크트리 `/home/kimchungsik/projects/cloud.beyondfacade/.worktrees/embedding-benchmark`에는 `.venv`·`.env`가 없다. 메인 체크아웃의 것을 쓴다.

```bash
cd /home/kimchungsik/projects/cloud.beyondfacade/.worktrees/embedding-benchmark/backend
export PY=/home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python
# sys.prefix RuntimeWarning 2줄은 무해하다(다른 경로의 venv 실행).
```

## File Structure

| 파일 | 책임 | 구분 |
|---|---|---|
| `backend/apps/rag/adapter/inbound/cli/benchmark_core.py` | 순수 로직: 코퍼스 행·절단 정규화·전수 검색·순위(접기)·지표·bootstrap·백분위·판정·보고서 렌더 | 신규 |
| `backend/apps/rag/adapter/inbound/cli/benchmark_embeddings.py` | CLI: `snapshot`·`embed`·`latency`·`evaluate`, 모델 레지스트리, 파일·DB·Ollama 입출력 | 신규 |
| `backend/apps/rag/adapter/outbound/embeddings/ollama_bge_m3_adapter.py` | bge-m3 `EmbeddingPort` | 신규 |
| `backend/apps/rag/adapter/outbound/embeddings/ollama_qwen3_adapter.py` | `dim` 인자 | 수정 |
| `backend/apps/rag/adapter/outbound/embeddings/fp16_qwen3_adapter.py` | `dim` 인자 | 수정 |
| `backend/apps/rag/adapter/outbound/embeddings/gemini_embedding_adapter.py` | `model`·`dim` 인자, 모델별 입력 형식 Strategy, `retry_count` | 수정 |
| `backend/apps/rag/adapter/inbound/cli/generate_evalset.py` | `--hard-kind` 3종(선택기·프롬프트·행) | 수정 |
| `backend/apps/rag/adapter/inbound/cli/judge_evalset.py` | 다중 정답 행에 사건 단위 판정 안내 | 수정 |
| `backend/tests/test_rag_benchmark_core.py` | benchmark_core 단위 테스트 | 신규 |
| `backend/tests/test_rag_benchmark_cli.py` | CLI 순수 헬퍼 테스트 | 신규 |
| `backend/tests/test_rag_embedding_adapters.py` | 어댑터 테스트 추가 | 수정 |
| `backend/tests/test_rag_generate_evalset.py` | 어려운 질문 테스트 추가 | 수정 |
| `backend/tests/test_rag_judge_evalset.py` | 판정 메시지 테스트 추가 | 수정 |

---

### Task 1: 벤치마크 순수 로직 — 절단·검색·지표·bootstrap

**Files:**
- Create: `backend/apps/rag/adapter/inbound/cli/benchmark_core.py`
- Create: `backend/tests/test_rag_benchmark_core.py`
- Modify: `backend/docs/backend_ver_log.md` (맨 위에 v0.64.0 항목 신설)

**Interfaces:**
- Consumes: `apps.rag.adapter.inbound.cli.evaluate_rag.hit_at_k(relevant: set[str], ranked: list[str], k: int = 5) -> float`, `mrr(relevant, ranked) -> float`; `apps.rag.domain.services.same_event_collapser.collapse_same_event(hits: list[RagHit]) -> list[RagHit]`; `apps.rag.domain.entities.rag_chunk_entity.RagHit`.
- Produces:
  - `@dataclass(frozen=True) CorpusRow(chunk_id: str, source_type: str, content: str, published_at: datetime | None)`
  - `truncate_normalize(matrix: np.ndarray, dim: int) -> np.ndarray` (float32, 행 노름 1)
  - `top_scored(doc_matrix: np.ndarray, query_vec: np.ndarray, candidates: np.ndarray, k: int) -> list[tuple[int, float]]`
  - `COLLAPSERS: dict[str, Collapser]` (= `{"news": collapse_same_event}`)
  - `rank_chunk_ids(doc_matrix, query_vec, corpus: list[CorpusRow], candidates: np.ndarray, depth: int) -> list[str]`
  - `top1(relevant, ranked) -> float`, `ndcg_at_k(relevant: set[str], ranked: list[str], k: int = 10) -> float`
  - `paired_bootstrap_ci(a: list[float], b: list[float], n: int = 10_000, seed: int = 0) -> tuple[float, float, float]` (평균 차이, 하한, 상한)
  - `percentile(samples: list[float], q: float) -> float`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_rag_benchmark_core.py`:

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `$PY -m pytest tests/test_rag_benchmark_core.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.rag.adapter.inbound.cli.benchmark_core'`

- [ ] **Step 3: 구현**

`backend/apps/rag/adapter/inbound/cli/benchmark_core.py`:

```python
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
```

주의: `rank_chunk_ids`의 `fetch` 계산에 `in COLLAPSERS` 조건식이 있다. 이는 데이터 크기 계산이며 타입 분기가 아니다(운영 `RagSearchInteractor.search`와 같은 구조).

- [ ] **Step 4: 통과 확인**

Run: `$PY -m pytest tests/test_rag_benchmark_core.py tests/test_rag_eval_harness.py -q`
Expected: 전부 PASS

- [ ] **Step 5: 버전 로그 항목 신설**

`backend/docs/backend_ver_log.md`의 `# Backend Version Log` 바로 아래(기존 `## [v0.63.0]` 위)에 넣는다:

```markdown
## [v0.64.0] - 2026-10-04

### Added
- **임베딩 모델 평가 하네스** (spec `docs/superpowers/specs/2026-10-04-embedding-benchmark-design.md`) — 9개 조합(bge-m3@1024, qwen3@1536·2560, gemini-001·gemini-2@1024·1536·2560)을 같은 코퍼스·평가셋으로 비교해 로컬용·API용 각 1종을 고른다. 운영 DB·검색 경로는 바꾸지 않는다.
  - `benchmark_core.py` — MRL 절단·재정규화, 운영 규칙(원천 필터·뉴스 사건 접기) 그대로의 numpy 전수 검색, top-1·nDCG@10·paired bootstrap(n=10000, seed 0).
```

- [ ] **Step 6: 커밋**

```bash
git add backend/apps/rag/adapter/inbound/cli/benchmark_core.py backend/tests/test_rag_benchmark_core.py backend/docs/backend_ver_log.md
git commit -m "backend v0.64.0: 임베딩 벤치마크 순수 로직 (절단·전수 검색·지표·bootstrap)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 임베딩 어댑터 — `dim`·`model` 인자, Gemini 입력 형식 Strategy, bge-m3

**Files:**
- Modify: `backend/apps/rag/adapter/outbound/embeddings/ollama_qwen3_adapter.py`
- Modify: `backend/apps/rag/adapter/outbound/embeddings/fp16_qwen3_adapter.py`
- Modify: `backend/apps/rag/adapter/outbound/embeddings/gemini_embedding_adapter.py`
- Create: `backend/apps/rag/adapter/outbound/embeddings/ollama_bge_m3_adapter.py`
- Modify: `backend/tests/test_rag_embedding_adapters.py` (테스트 추가)
- Modify: `backend/docs/backend_ver_log.md` (v0.64.0 Added에 줄 추가)

**Interfaces:**
- Produces:
  - `OllamaQwen3EmbeddingAdapter(base_url="http://127.0.0.1:11434", transport=None, dim: int = 1536)`
  - `Fp16Qwen3EmbeddingAdapter(dim: int = 1536)`
  - `GeminiEmbeddingAdapter(api_key: str | None = None, model: str = "gemini-embedding-001", dim: int = 1536)` — `.model_name`은 `model`, `.retry_count: int`(429 재시도 누적)
  - `OllamaBgeM3EmbeddingAdapter(base_url="http://127.0.0.1:11434", transport=None)` — `MODEL_NAME="bge-m3"`, `PROVIDER="ollama"`, `OLLAMA_MODEL="bge-m3"`

실측 근거(2026-10-04):
- gemini-embedding-2는 `task_type` 미지원. 질의는 `"task: search result | query: {text}"`, 문서는 `"title: {title} | text: {text}"` 프리픽스로 지시한다(ai.google.dev embeddings 문서).
- 두 Gemini 모델 모두 `contents`에 문자열 2개를 넣으면 임베딩 2개가 나오고, 3072차원 노름은 1.0이다.
- Ollama bge-m3는 F16, 1024차원이며 정규화된 벡터를 돌려준다(노름 0.9999999).

- [ ] **Step 1: 실패하는 테스트 추가**

`backend/tests/test_rag_embedding_adapters.py` 끝에 추가:

```python
def test_ollama_qwen3_dim_인자가_요청_dimensions로_간다():
    captured = []
    OllamaQwen3EmbeddingAdapter(transport=_transport(captured), dim=2560).embed_documents(["문서"])
    assert captured[0]["dimensions"] == 2560


def test_gemini_기본값은_운영과_같다_001과_1536(monkeypatch):
    from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter

    adapter = GeminiEmbeddingAdapter(api_key="test-key")
    calls = []
    monkeypatch.setattr(
        adapter._client.models, "embed_content",
        lambda model, contents, config: calls.append((model, contents, config)) or _FakeEmbedResult(len(contents)),
    )
    adapter.embed_query("카페 지원")
    model, contents, config = calls[0]
    assert model == "gemini-embedding-001"
    assert contents == ["카페 지원"]
    assert config.task_type == "RETRIEVAL_QUERY"
    assert config.output_dimensionality == 1536


def test_gemini_2는_task_type_대신_프롬프트_프리픽스를_붙인다(monkeypatch):
    from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter

    adapter = GeminiEmbeddingAdapter(api_key="test-key", model="gemini-embedding-2", dim=3072)
    calls = []
    monkeypatch.setattr(
        adapter._client.models, "embed_content",
        lambda model, contents, config: calls.append((model, contents, config)) or _FakeEmbedResult(len(contents)),
    )
    adapter.embed_query("카페 지원")
    adapter.embed_documents(["청년 창업 자금\n서울시 지원"])
    assert adapter.model_name == "gemini-embedding-2"
    assert calls[0][1] == ["task: search result | query: 카페 지원"]
    assert calls[1][1] == ["title: 청년 창업 자금 | text: 청년 창업 자금\n서울시 지원"]
    assert calls[0][2].task_type is None
    assert calls[0][2].output_dimensionality == 3072


def test_gemini_429_재시도_횟수를_센다(monkeypatch):
    from google.genai import errors

    from apps.rag.adapter.outbound.embeddings import gemini_embedding_adapter as mod

    adapter = mod.GeminiEmbeddingAdapter(api_key="test-key")
    state = {"n": 0}

    def flaky(model, contents, config):
        state["n"] += 1
        if state["n"] == 1:
            raise errors.ClientError(429, {"error": {"message": "rate", "status": "RESOURCE_EXHAUSTED"}})
        return _FakeEmbedResult(len(contents))

    monkeypatch.setattr(adapter._client.models, "embed_content", flaky)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    adapter.embed_query("q")
    assert adapter.retry_count == 1


def test_bge_m3는_프리픽스_없이_bge_m3_모델로_요청한다():
    from apps.rag.adapter.outbound.embeddings.ollama_bge_m3_adapter import OllamaBgeM3EmbeddingAdapter

    captured = []

    def handler(request):
        body = json.loads(request.content)
        captured.append(body)
        return httpx.Response(200, json={"embeddings": [[1.0] + [0.0] * 1023 for _ in body["input"]]})

    adapter = OllamaBgeM3EmbeddingAdapter(transport=httpx.MockTransport(handler))
    q = adapter.embed_query("카페 지원")
    docs = adapter.embed_documents([f"문서{i}" for i in range(120)])
    assert captured[0] == {"model": "bge-m3", "input": ["카페 지원"]}
    assert [len(c["input"]) for c in captured[1:]] == [50, 50, 20]
    assert len(q) == 1024 and len(docs) == 120
    assert adapter.model_name == "bge-m3" and adapter.provider == "ollama"
```

- [ ] **Step 2: 실패 확인**

Run: `$PY -m pytest tests/test_rag_embedding_adapters.py -q`
Expected: 새 테스트 5개 FAIL (`unexpected keyword argument 'dim'`·`'model'`, `retry_count` 없음, `ollama_bge_m3_adapter` 모듈 없음). 기존 테스트는 PASS.

- [ ] **Step 3: Ollama qwen3에 `dim`**

`ollama_qwen3_adapter.py`의 `__init__` 시그니처와 본문 첫 줄, 요청 바디를 바꾼다:

```python
    def __init__(self, base_url: str = "http://127.0.0.1:11434", transport=None, dim: int = DIMENSIONS):
        """
        Ollama 임베딩 어댑터 초기화.

        Args:
            base_url: Ollama 서버 URL (기본값: http://127.0.0.1:11434)
            transport: httpx.Transport (테스트용 MockTransport 주입 가능)
            dim: 출력 차원 (기본 1536 = 운영 스키마). 벤치마크는 2560으로 받아 잘라 쓴다.
        """
        self.base_url = base_url
        self._dim = dim
```

`_embed_batch`의 요청 바디에서 `"dimensions": self.DIMENSIONS,` → `"dimensions": self._dim,`

- [ ] **Step 4: fp16 qwen3에 `dim`**

`fp16_qwen3_adapter.py`:

```python
    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self._model = None
        self._dim = dim
```

`_load`의 `truncate_dim=EMBEDDING_DIM,` → `truncate_dim=self._dim,`

- [ ] **Step 5: Gemini에 `model`·`dim`·입력 형식 Strategy·`retry_count`**

`gemini_embedding_adapter.py` — import에 `from abc import ABC, abstractmethod` 추가. `EMBEDDING_DIM` 정의 아래에 Strategy를 둔다:

```python
class _TaskFormat(ABC):
    """모델별 검색 작업 지시 방식 — 001은 task_type 파라미터, 2는 프롬프트 프리픽스(task_type 미지원)."""

    @abstractmethod
    def contents(self, texts: list[str], task_type: str) -> list[str]: ...

    @abstractmethod
    def config(self, task_type: str, dim: int) -> types.EmbedContentConfig: ...


class _TaskTypeParam(_TaskFormat):
    def contents(self, texts: list[str], task_type: str) -> list[str]:
        return texts

    def config(self, task_type: str, dim: int) -> types.EmbedContentConfig:
        return types.EmbedContentConfig(task_type=task_type, output_dimensionality=dim)


def _document_prefix(text: str) -> str:
    return f"title: {text.split(chr(10), 1)[0]} | text: {text}"


class _PromptPrefix(_TaskFormat):
    # ai.google.dev embeddings 문서(2026-10-04 확인)의 비대칭 검색 형식
    _PREFIX = {
        "RETRIEVAL_QUERY": lambda text: f"task: search result | query: {text}",
        "RETRIEVAL_DOCUMENT": _document_prefix,
    }

    def contents(self, texts: list[str], task_type: str) -> list[str]:
        return [self._PREFIX[task_type](t) for t in texts]

    def config(self, task_type: str, dim: int) -> types.EmbedContentConfig:
        return types.EmbedContentConfig(output_dimensionality=dim)


_TASK_FORMATS: dict[str, _TaskFormat] = {
    "gemini-embedding-001": _TaskTypeParam(),
    "gemini-embedding-2": _PromptPrefix(),
}
```

클래스 본문을 바꾼다(`MODEL_NAME`·`PROVIDER` 클래스 속성은 유지):

```python
    def __init__(self, api_key: str | None = None, model: str = MODEL_NAME, dim: int = EMBEDDING_DIM) -> None:
        self._client = genai.Client(api_key=api_key or get_settings().gemini_api_key)
        self._model = model
        self._dim = dim
        self._format = _TASK_FORMATS[model]
        self.retry_count = 0

    @property
    def model_name(self) -> str:
        """모델명."""
        return self._model
```

`_embed_batch_with_retry`의 호출부를:

```python
                return self._client.models.embed_content(
                    model=self.model_name,
                    contents=self._format.contents(batch, task_type),
                    config=self._format.config(task_type, self._dim),
                )
```

로 바꾸고, `time.sleep(delay)` 바로 다음 줄에 `self.retry_count += 1`을 넣는다.

주의: 클래스 본문 안에서 `model: str = MODEL_NAME` 기본값은 클래스 속성 `MODEL_NAME`을 참조한다(정의 순서상 `MODEL_NAME`이 위에 있어야 한다 — 이미 그렇다).

- [ ] **Step 6: bge-m3 어댑터 신설**

`backend/apps/rag/adapter/outbound/embeddings/ollama_bge_m3_adapter.py`:

```python
"""Ollama bge-m3 임베딩 어댑터 — EmbeddingPort 구현 (1024차원 고정, instruction 없음).

Ollama가 정규화된 벡터를 돌려준다(2026-10-04 실측 노름 1.0, F16) — 여기서 다시 정규화하지 않는다.
"""

import httpx

from apps.rag.app.ports.output.rag_port import EmbeddingPort


class OllamaBgeM3EmbeddingAdapter(EmbeddingPort):
    MODEL_NAME = "bge-m3"
    PROVIDER = "ollama"
    OLLAMA_MODEL = "bge-m3"
    BATCH_SIZE = 50

    def __init__(self, base_url: str = "http://127.0.0.1:11434", transport=None):
        # 콜드스타트(모델 로드) 대비 — ollama_qwen3_adapter와 같은 120초
        self.client = httpx.Client(base_url=base_url, transport=transport, timeout=120.0)

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def provider(self) -> str:
        return self.PROVIDER

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.BATCH_SIZE):
            response = self.client.post(
                "/api/embed", json={"model": self.OLLAMA_MODEL, "input": texts[start : start + self.BATCH_SIZE]}
            )
            response.raise_for_status()
            vectors.extend(response.json()["embeddings"])
        return vectors
```

- [ ] **Step 7: 통과 확인 + RAG 회귀**

Run: `$PY -m pytest tests/test_rag_embedding_adapters.py tests/test_rag_interactor.py tests/test_ops_api.py -q`
Expected: 전부 PASS

- [ ] **Step 8: 버전 로그 줄 추가**

v0.64.0 `### Added` 목록 끝에:

```markdown
  - 어댑터: `OllamaBgeM3EmbeddingAdapter` 신설. qwen3(Ollama·fp16)에 `dim`, Gemini에 `model`·`dim` 인자(기본값은 운영 그대로 1536·`gemini-embedding-001`). gemini-embedding-2는 `task_type`을 받지 않아 질의·문서 프롬프트 프리픽스로 지시한다(모델별 Strategy). Gemini 429 재시도 횟수 `retry_count`.
```

- [ ] **Step 9: 커밋**

```bash
git add backend/apps/rag/adapter/outbound/embeddings/ backend/tests/test_rag_embedding_adapters.py backend/docs/backend_ver_log.md
git commit -m "backend v0.64.0: 임베딩 어댑터 dim·model 인자, gemini-embedding-2 프리픽스, bge-m3 어댑터

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 어려운 질문 생성 — `--hard-kind` 3종과 판정 안내

**Files:**
- Modify: `backend/apps/rag/adapter/inbound/cli/generate_evalset.py`
- Modify: `backend/apps/rag/adapter/inbound/cli/judge_evalset.py`
- Modify: `backend/tests/test_rag_generate_evalset.py` (테스트 추가)
- Modify: `backend/tests/test_rag_judge_evalset.py` (테스트 추가)
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: `same_event(a: RagHit, b: RagHit) -> bool` (`apps.rag.domain.services.same_event_collapser`), 기존 `select_new_chunks`, `ClaudeGenerator`.
- Produces (generate_evalset):
  - `@dataclass(frozen=True) HardItem(chunk_id: str, prompt_input: str, relevant_ids: list[str])`
  - `pick_sibling(chunk: dict, pool: list[dict]) -> dict | None` — 제목 토큰 Jaccard 최대(≥0.3), 동점은 chunk_id 오름차순
  - `select_colloquial(chunks, existing: set[str], limit) -> list[HardItem]`
  - `select_sibling(chunks, existing, limit) -> list[HardItem]`
  - `select_news_event(chunks, existing, limit) -> list[HardItem]`
  - `build_hard_row(item: HardItem, question: str, kind: str) -> dict` — 키 `question, relevant_ids, source_type, status="candidate", subset="hard", hard_kind`
  - chunk dict 형태: `{"chunk_id": str, "content": str, "published_at": datetime | None}`
- Produces (judge_evalset): `build_user_message(item: _Item) -> str`, `_Item`에 필드 `answers: int = 1`

- [ ] **Step 1: 실패하는 테스트 추가**

`backend/tests/test_rag_generate_evalset.py` 끝에 추가(맨 위 import에 `from datetime import datetime` 추가):

```python
from apps.rag.adapter.inbound.cli.generate_evalset import (
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
```

`backend/tests/test_rag_judge_evalset.py` 끝에 추가:

```python
def test_정답이_여럿인_행은_사건_단위로_판정하라고_알린다():
    from apps.rag.adapter.inbound.cli.judge_evalset import _Item, build_user_message
    from apps.rag.adapter.inbound.cli.review_evalset import ProgramCard

    card = ProgramCard("a", "야시장 개장", "한겨레", None, "상권", "2026-09-01", "요약", "http://u")
    multi = build_user_message(_Item("news:a", "망원시장 밤에 장 서?", card, answers=3))
    single = build_user_message(_Item("news:a", "망원시장 밤에 장 서?", card))
    assert "같은 사건 기사 3건" in multi
    assert "같은 사건 기사" not in single
```

- [ ] **Step 2: 실패 확인**

Run: `$PY -m pytest tests/test_rag_generate_evalset.py tests/test_rag_judge_evalset.py -q`
Expected: FAIL — `ImportError: cannot import name 'HardItem'`, `build_user_message`

- [ ] **Step 3: generate_evalset 구현**

`generate_evalset.py` 수정.

(a) import 추가:

```python
import re
from dataclasses import dataclass

from apps.rag.domain.entities.rag_chunk_entity import RagHit
from apps.rag.domain.services.same_event_collapser import same_event
```

(b) `_CLAUDE_SYSTEM` 아래에 어려운 질문 프롬프트 3종을 추가한다. 공통 기준 문단은 `_CLAUDE_SYSTEM`과 같다.

```python
_HARD_COMMON = """질문은 이 기준을 만족해야 한다: **질문에 담긴 정보만으로 이 문서가 다른 유사 문서보다 우선적으로 정답이 되어야 한다.**
- 문서에 없는 사실을 지어내지 않는다.
- 출력은 질문 문장 하나뿐이다. 따옴표·설명·번호를 붙이지 않는다."""

# 어려운 질문 3종 (spec §3) — 검색 모델의 변별력을 재기 위해 표면 단어 겹침을 일부러 줄인다
_HARD_SYSTEMS = {
    "colloquial": f"""당신은 정책자금 검색(RAG) 평가셋의 어려운 질문을 만드는 사람이다.
가게를 차리려는 사람이 친구에게 묻듯 구어체로 묻는 한국어 질문을 딱 1개 만든다(15~45자).
- 공고 제목·본문의 핵심 단어(사업명·지원방식 명칭·기관명)를 그대로 쓰지 않고 일상어로 바꿔 말한다.
- 그래도 지역·대상 조건·지원 내용은 의미로 담아 이 공고를 가리켜야 한다.
{_HARD_COMMON}""",
    "sibling": f"""당신은 정책자금 검색(RAG) 평가셋의 어려운 질문을 만드는 사람이다.
[정답 문서]와 헷갈리기 쉬운 [유사 문서]가 주어진다. [정답 문서]만 가리키는 한국어 질문을 딱 1개 만든다(20~50자).
- 두 문서를 가르는 조건(대상·지원방식·금액 성격·지역·기간)을 질문에 담는다. [유사 문서]에도 맞는 질문은 실패다.
- 제목을 그대로 베끼지 않는다.
{_HARD_COMMON}""",
    "news_event": f"""당신은 지역 상권 뉴스 검색(RAG) 평가셋의 어려운 질문을 만드는 사람이다.
이 기사가 다룬 사건을 찾는 한국어 질문을 딱 1개 만든다(15~45자).
- 헤드라인의 단어를 그대로 쓰지 않고 사건의 내용(무엇이·어디서·어떻게 됐는지)으로 묻는다.
- 같은 사건을 다룬 다른 언론사 기사도 정답으로 치므로 언론사·기자는 묻지 않는다.
{_HARD_COMMON}""",
}
_HARD_SOURCE = {"colloquial": "funding", "sibling": "funding", "news_event": "news"}
```

(c) `ClaudeGenerator.__init__`에 `system` 인자:

```python
    def __init__(self, model: str, system: str = _CLAUDE_SYSTEM) -> None:
        ...  # 기존 본문 유지
        self._system = system
```

`generate`의 `system=_CLAUDE_SYSTEM,` → `system=self._system,`

(d) `build_row` 아래에 순수 함수:

```python
_TOKEN = re.compile(r"[가-힣A-Za-z0-9]+")
_SIBLING_MIN_JACCARD = 0.3  # same_event_collapser의 제목 Jaccard 기준과 같은 값


@dataclass(frozen=True)
class HardItem:
    chunk_id: str
    prompt_input: str
    relevant_ids: list[str]


def _title_tokens(content: str) -> set[str]:
    return {t for t in _TOKEN.findall(content.split("\n", 1)[0]) if len(t) >= 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def pick_sibling(chunk: dict, pool: list[dict]) -> dict | None:
    """제목 토큰이 가장 많이 겹치는 다른 공고(임베딩 모델 무관 — spec §3 모델 중립 선정)."""
    target = _title_tokens(chunk["content"])
    scored = [
        (_jaccard(target, _title_tokens(c["content"])), c["chunk_id"], c)
        for c in pool
        if c["chunk_id"] != chunk["chunk_id"]
    ]
    scored = [s for s in scored if s[0] >= _SIBLING_MIN_JACCARD]
    if not scored:
        return None
    return min(scored, key=lambda s: (-s[0], s[1]))[2]


def select_colloquial(chunks: list[dict], existing: set[str], limit: int) -> list[HardItem]:
    return [HardItem(c["chunk_id"], c["content"], [c["chunk_id"]]) for c in select_new_chunks(chunks, existing, limit)]


def select_sibling(chunks: list[dict], existing: set[str], limit: int) -> list[HardItem]:
    items: list[HardItem] = []
    for chunk in select_new_chunks(chunks, existing, len(chunks)):
        sibling = pick_sibling(chunk, chunks)
        if sibling is None:
            continue
        prompt = f"[정답 문서]\n{chunk['content']}\n\n[유사 문서]\n{sibling['content']}"
        items.append(HardItem(chunk["chunk_id"], prompt, [chunk["chunk_id"]]))
        if len(items) == limit:
            break
    return items


def _hit(chunk: dict) -> RagHit:
    return RagHit(
        chunk_id=chunk["chunk_id"], source_type="news", source_id=chunk["chunk_id"].split(":", 1)[1],
        content=chunk["content"], score=0.0, url=None, org=None, published_at=chunk["published_at"],
    )


def select_news_event(chunks: list[dict], existing: set[str], limit: int) -> list[HardItem]:
    """같은 사건 기사(same_event: 제목 Jaccard ≥ 0.3·보도일 ±3일)를 정답 묶음으로. 기존 정답과 겹치는 사건은 건너뛴다."""
    seen = set(existing)
    items: list[HardItem] = []
    for chunk in chunks:
        if chunk["chunk_id"] in seen:
            continue
        target = _hit(chunk)
        cluster = [chunk["chunk_id"]] + sorted(
            c["chunk_id"] for c in chunks if c["chunk_id"] != chunk["chunk_id"] and same_event(target, _hit(c))
        )
        if seen & set(cluster):
            continue
        seen |= set(cluster)
        items.append(HardItem(chunk["chunk_id"], chunk["content"], cluster))
        if len(items) == limit:
            break
    return items


_HARD_SELECTORS = {"colloquial": select_colloquial, "sibling": select_sibling, "news_event": select_news_event}


def build_hard_row(item: HardItem, question: str, kind: str) -> dict:
    return {
        "question": question,
        "relevant_ids": item.relevant_ids,
        "source_type": item.chunk_id.split(":", 1)[0],
        "status": "candidate",
        "subset": "hard",
        "hard_kind": kind,
    }
```

(e) `_fetch_chunks`의 select에 `RagChunkOrm.published_at`를 추가하고, 반환 dict에 `"published_at": row.published_at`를 넣는다.

(f) 기존 정답 전체를 모으는 함수를 `_existing_ids` 아래에 둔다:

```python
def _all_relevant_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        cid
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for cid in json.loads(line)["relevant_ids"]
    }
```

(g) `main()` — 인자 `parser.add_argument("--hard-kind", default=None, choices=list(_HARD_SYSTEMS), help="어려운 질문 종류 (claude 전용)")` 추가. `output_path.parent.mkdir(...)` 다음에 분기를 둔다:

```python
    if args.hard_kind:
        _run_hard(args, output_path)
        return
```

그리고 `main` 위에 둔다:

```python
def _run_hard(args, output_path: Path) -> None:
    kind = args.hard_kind
    source_type = _HARD_SOURCE[kind]
    items = _HARD_SELECTORS[kind](_fetch_chunks(source_type), _all_relevant_ids(output_path), args.limit)
    generator = ClaudeGenerator(args.model or "claude-opus-5", system=_HARD_SYSTEMS[kind])
    with output_path.open("a", encoding="utf-8") as f:
        for i, item in enumerate(items, start=1):
            question = generator.generate(source_type, item.prompt_input)
            f.write(json.dumps(build_hard_row(item, question, kind), ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i}/{len(items)}] {kind} {item.chunk_id} (정답 {len(item.relevant_ids)}건) -> {question}", flush=True)
    print(f"generate_evalset: hard/{kind} {len(items)}건 추가 → {output_path}", flush=True)
```

모듈 docstring의 실행 예시 아래에 한 줄 추가:
`어려운 질문(spec 2026-10-04 §3): --hard-kind colloquial|sibling|news_event --limit 20 (claude 전용, subset=hard)`

- [ ] **Step 4: judge_evalset 구현**

`judge_evalset.py`:

```python
_MULTI_NOTE = "\n\n[참고] 이 행은 같은 사건 기사 {n}건을 모두 정답으로 친다. 다른 언론사 기사가 여럿인 것은 X 사유가 아니다 — 사건 단위로 판정한다."


@dataclass(frozen=True)
class _Item:
    chunk_id: str
    question: str
    card: ProgramCard
    answers: int = 1


def build_user_message(item: _Item) -> str:
    c = item.card
    body = _USER.format(
        question=item.question, title=c.title, org=c.org, target=c.target or "-",
        field=c.field or "-", period=c.period, summary=(c.summary or "(요약 없음)").replace("\n", " "),
    )
    return body + (_MULTI_NOTE.format(n=item.answers) if item.answers > 1 else "")
```

`_judge`의 `messages=[{"role": "user", "content": _USER.format(...)}]`를 `messages=[{"role": "user", "content": build_user_message(item)}]`로 바꾼다. `main()`의 `items = [...]`를:

```python
    items = [
        _Item(r["relevant_ids"][0], r["question"], cards[r["relevant_ids"][0].split(":", 1)[1]], len(r["relevant_ids"]))
        for r in rows
    ]
```

로 바꾼다.

- [ ] **Step 5: 통과 확인 + 평가셋 CLI 회귀**

Run: `$PY -m pytest tests/test_rag_generate_evalset.py tests/test_rag_judge_evalset.py tests/test_rag_review_evalset.py tests/test_rag_eval_harness.py -q`
Expected: 전부 PASS

- [ ] **Step 6: 버전 로그 줄 추가**

```markdown
  - 어려운 질문: `generate_evalset --hard-kind colloquial|sibling|news_event` — 구어체(핵심어 회피)·유사 공고 구별(제목 토큰 Jaccard ≥ 0.3 짝)·뉴스 사건(같은 사건 기사 묶음 정답). 표본 선정에 임베딩 모델을 쓰지 않는다. 행에 `subset: "hard"`, `hard_kind`. `judge_evalset`은 정답이 여럿인 행에 사건 단위 판정 안내를 붙인다.
```

- [ ] **Step 7: 커밋**

```bash
git add backend/apps/rag/adapter/inbound/cli/generate_evalset.py backend/apps/rag/adapter/inbound/cli/judge_evalset.py backend/tests/test_rag_generate_evalset.py backend/tests/test_rag_judge_evalset.py backend/docs/backend_ver_log.md
git commit -m "backend v0.64.0: 어려운 평가 질문 3종 생성(구어체·유사 공고·뉴스 사건)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 벤치마크 CLI — `snapshot`·`embed` (모델 레지스트리·벡터 캐시)

**Files:**
- Create: `backend/apps/rag/adapter/inbound/cli/benchmark_embeddings.py`
- Create: `backend/tests/test_rag_benchmark_cli.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 1 `CorpusRow`; Task 2 어댑터 생성자.
- Produces (benchmark_embeddings):
  - `@dataclass(frozen=True) ModelSpec(name: str, group: str, max_dim: int, doc_embedder: Callable[[], EmbeddingPort], query_embedder: Callable[[], EmbeddingPort], ollama_model: str | None, token_counter: Callable[[list[str]], int])`
  - `MODELS: dict[str, ModelSpec]` 키 `bge-m3`, `qwen3`, `gemini-001`, `gemini-2`
  - `CONFIGS: list[tuple[str, int]]` (9개), `BASELINE = ("qwen3", 1536)`, `config_key(model: str, dim: int) -> str` (예: `"qwen3@1536"`)
  - `corpus_to_jsonl(rows: list[CorpusRow]) -> str`, `corpus_from_jsonl(text: str) -> list[CorpusRow]`
  - `pending_shards(total: int, shard: int, done: set[int]) -> list[int]` (샤드 시작 인덱스)
  - `missing_queries(cached: list[str], wanted: list[str]) -> list[str]`
  - `confirmed_rows(rows: list[dict]) -> list[dict]`
  - 캐시 경로: `data/eval/cache/embedding-benchmark/corpus.jsonl`, `corpus.sha256`, `{model}/docs_{start:06d}.npy`, `{model}/tokens.json`, `{model}/queries.json`, `{model}/queries.npy`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_rag_benchmark_cli.py`:

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `$PY -m pytest tests/test_rag_benchmark_cli.py -q`
Expected: FAIL — `ModuleNotFoundError: ... benchmark_embeddings`

- [ ] **Step 3: 구현 (snapshot·embed)**

`backend/apps/rag/adapter/inbound/cli/benchmark_embeddings.py`:

```python
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
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from apps.rag.adapter.inbound.cli.benchmark_core import CorpusRow
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


def load_doc_matrix(model: str) -> np.ndarray:
    shards = sorted((_CACHE / model).glob("docs_*.npy"))
    return np.concatenate([np.load(p) for p in shards], axis=0)


def load_query_vectors(model: str) -> dict[str, np.ndarray]:
    texts = json.loads((_CACHE / model / "queries.json").read_text(encoding="utf-8"))
    matrix = np.load(_CACHE / model / "queries.npy")
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

    done = {int(p.stem.split("_")[1]) for p in out.glob("docs_*.npy")}
    tokens_path = out / "tokens.json"
    tokens: dict[str, int] = json.loads(tokens_path.read_text()) if tokens_path.exists() else {}
    todo = pending_shards(len(corpus), _SHARD, done)
    embedder = spec.doc_embedder() if todo else None
    for start in todo:
        texts = [r.content for r in corpus[start : start + _SHARD]]
        np.save(out / f"docs_{start:06d}.npy", np.asarray(embedder.embed_documents(texts), dtype=np.float32))
        tokens[str(start)] = spec.token_counter(texts)
        tokens_path.write_text(json.dumps(tokens), encoding="utf-8")
        print(f"embed {spec.name} docs {start}~{start + len(texts) - 1} / {len(corpus)}", flush=True)

    q_texts_path, q_vecs_path = out / "queries.json", out / "queries.npy"
    cached = json.loads(q_texts_path.read_text(encoding="utf-8")) if q_texts_path.exists() else []
    new = missing_queries(cached, [r["question"] for r in confirmed_rows(_load_evalset())])
    if new:
        q_embedder = spec.query_embedder()
        vecs = np.asarray([q_embedder.embed_query(q) for q in new], dtype=np.float32)
        old = np.load(q_vecs_path) if q_vecs_path.exists() else np.zeros((0, vecs.shape[1]), dtype=np.float32)
        np.save(q_vecs_path, np.concatenate([old, vecs], axis=0))
        q_texts_path.write_text(json.dumps(cached + new, ensure_ascii=False), encoding="utf-8")
    print(f"embed {spec.name}: 문서 샤드 {len(todo)}개 새로, 질의 {len(new)}건 새로 (총 토큰 {sum(tokens.values())})", flush=True)


_COMMANDS: dict[str, Callable] = {"snapshot": _cmd_snapshot, "embed": _cmd_embed}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=list(_COMMANDS))
    parser.add_argument("--model", choices=list(MODELS))
    args = parser.parse_args()
    _COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**

Run: `$PY -m pytest tests/test_rag_benchmark_cli.py tests/test_rag_benchmark_core.py -q`
Expected: 전부 PASS

- [ ] **Step 5: 스모크 — snapshot만 실제 실행**

```bash
ln -sf /home/kimchungsik/projects/cloud.beyondfacade/backend/.env .env   # backend/.env (gitignore 대상)
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings snapshot
```

Expected: `snapshot: 8891청크 sha256=…` (청크 수는 그날 색인 상태에 따라 다를 수 있다. 0이면 DB 연결 문제 — 중단하고 보고)

- [ ] **Step 6: 버전 로그 줄 추가**

```markdown
  - `benchmark_embeddings` CLI: `snapshot`(rag_chunk 전량 jsonl + sha256, 만료 공고 포함), `embed --model`(문서 512개 샤드 단위로 이어서 캐시, confirmed 질의 캐시, Gemini는 `count_tokens`로 토큰 실측). 캐시는 `data/eval/cache/embedding-benchmark/`(커밋 안 함).
```

- [ ] **Step 7: 커밋**

```bash
git add backend/apps/rag/adapter/inbound/cli/benchmark_embeddings.py backend/tests/test_rag_benchmark_cli.py backend/docs/backend_ver_log.md
git commit -m "backend v0.64.0: 벤치마크 CLI snapshot·embed (모델 레지스트리·벡터 캐시)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `latency` — 질의 지연·동시 상주·429

**Files:**
- Modify: `backend/apps/rag/adapter/inbound/cli/benchmark_embeddings.py`
- Modify: `backend/apps/rag/adapter/inbound/cli/benchmark_core.py` (`resident_models` 추가)
- Modify: `backend/tests/test_rag_benchmark_core.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 1 `percentile`; Task 4 `MODELS`, `confirmed_rows`, `_load_evalset`, `_CACHE`.
- Produces:
  - `resident_models(ps_json: dict) -> set[str]` (Ollama `/api/ps` 응답의 `models[].name`)
  - 파일 `data/eval/cache/embedding-benchmark/{model}/latency.json`:
    `{"model": str, "n": int, "p50_ms": float, "p95_ms": float, "coexist": bool | None, "vram_used_mib": int | None, "retry_429": int | None, "effective_p50_ms": float | None}`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_rag_benchmark_core.py` 끝에 추가(import 목록에 `resident_models` 추가):

```python
def test_상주_모델_이름을_모은다():
    ps = {"models": [{"name": "gemma4:12b", "size_vram": 1}, {"name": "bge-m3:latest", "size_vram": 1}]}
    assert resident_models(ps) == {"gemma4:12b", "bge-m3:latest"}
    assert resident_models({}) == set()
```

- [ ] **Step 2: 실패 확인**

Run: `$PY -m pytest tests/test_rag_benchmark_core.py -q`
Expected: FAIL — `ImportError: cannot import name 'resident_models'`

- [ ] **Step 3: 구현**

`benchmark_core.py` 끝에:

```python
def resident_models(ps_json: dict) -> set[str]:
    """Ollama /api/ps 응답 → 지금 메모리에 올라 있는 모델 이름."""
    return {m["name"] for m in ps_json.get("models", [])}
```

`benchmark_embeddings.py` — import에 `import subprocess`, `import time`, `import httpx`, 그리고 benchmark_core에서 `percentile, resident_models` 추가. `_cmd_embed` 아래에:

```python
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
    (_CACHE / spec.name / "latency.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"latency {spec.name}: p50 {p50:.0f}ms p95 {result['p95_ms']:.0f}ms 동시상주={coexist} VRAM={vram}MiB", flush=True)
```

`_COMMANDS`에 `"latency": _cmd_latency` 추가. `main()`에 `parser.add_argument("--rpm", type=float, default=None, help="API 분당 한도 — effective 지연 = max(p50, 60000/RPM)")` 추가.

- [ ] **Step 4: 통과 확인**

Run: `$PY -m pytest tests/test_rag_benchmark_core.py tests/test_rag_benchmark_cli.py -q`
Expected: 전부 PASS

- [ ] **Step 5: 스모크 — bge-m3 지연 실제 측정**

Run: `$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings latency --model bge-m3`
Expected: `latency bge-m3: p50 …ms p95 …ms 동시상주=True VRAM=…MiB`. `동시상주=False`면 `ollama ps` 출력과 함께 보고하고 멈춘다(게이트 판단 자료).

- [ ] **Step 6: 버전 로그 줄 추가**

```markdown
  - `latency --model`: confirmed 질문 × 3회 질의 지연 p50/p95(워밍업 제외). 로컬은 `gemma4:12b`를 먼저 올리고 측정 전후 `/api/ps`로 동시 상주·nvidia-smi 사용량 확인, API는 429 재시도 횟수와 `--rpm` 기준 effective 지연.
```

- [ ] **Step 7: 커밋**

```bash
git add backend/apps/rag/adapter/inbound/cli/ backend/tests/test_rag_benchmark_core.py backend/docs/backend_ver_log.md
git commit -m "backend v0.64.0: 벤치마크 latency (질의 지연·동시 상주·429)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: `evaluate` — 조합별 지표·판정·보고서

**Files:**
- Modify: `backend/apps/rag/adapter/inbound/cli/benchmark_core.py` (`score_rows`, `aggregate`, `pick_winner`, `decide`, `render_report`)
- Modify: `backend/apps/rag/adapter/inbound/cli/benchmark_embeddings.py` (`_cmd_evaluate`)
- Modify: `backend/tests/test_rag_benchmark_core.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 1 함수, Task 4 `load_corpus`·`load_doc_matrix`·`load_query_vectors`·`CONFIGS`·`BASELINE`·`MODELS`, Task 5 `latency.json`.
- Produces (benchmark_core):
  - `score_rows(doc_matrix: np.ndarray, query_vecs: dict[str, np.ndarray], corpus: list[CorpusRow], rows: list[dict], dim: int) -> list[dict]` — 행마다 `{"question","source_type","subset","hard_kind","top1","hit5","mrr","ndcg10"}`
  - `aggregate(scored: list[dict]) -> dict[str, dict[str, float]]` — 키 `all`, `subset:base`, `subset:hard`, `source:funding`, `source:news`, `hard:colloquial`… (있는 것만), 값 `{"n","top1","hit5","mrr","ndcg10"}`
  - `pick_winner(mrr: dict[str, list[float]], dims: dict[str, int], p95: dict[str, float | None], eligible: list[str]) -> tuple[str, list[str]]`
  - `decide(mrr: dict[str, list[float]], dims: dict[str, int], groups: dict[str, str], latency: dict[str, dict], baseline: str, p95_limit_ms: float = 500.0) -> dict`
  - `render_report(results: dict) -> str`

판정 규칙(spec §6)을 그대로 옮긴다:
- 그룹(local/api)마다 eligible 조합 중 평균 MRR 1위 → 1위와의 bootstrap 하한 ≤ 0인 조합이 동률 → 동률 중 (차원, p95, 이름) 최소가 승자.
- local eligible = `coexist is True` 그리고 `p95_ms ≤ 500`. api eligible = 전부.
- local 최종: 승자가 기준선이 아니고 `paired_bootstrap_ci(승자, 기준선)` 하한 > 0이면 교체, 아니면 기준선 유지.

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_rag_benchmark_core.py` 끝에 추가(import에 `aggregate, decide, pick_winner, render_report, score_rows` 추가):

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `$PY -m pytest tests/test_rag_benchmark_core.py -q`
Expected: FAIL — `ImportError: cannot import name 'aggregate'`

- [ ] **Step 3: benchmark_core 구현**

`benchmark_core.py` import에 `from statistics import mean`, `from apps.rag.adapter.inbound.cli.evaluate_rag import hit_at_k, mrr`(기존 줄 확장) 추가. 끝에:

```python
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
```

`render_report`에서 `{True: "O", False: "X"}.get(...)`는 표시 매핑이다.

- [ ] **Step 4: `_cmd_evaluate` 구현**

`benchmark_embeddings.py` — import에 benchmark_core의 `aggregate, decide, render_report, score_rows` 추가. `_cmd_latency` 아래에:

```python
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
            "tokens": sum(json.loads(tokens_path.read_text()).values()) if tokens_path.exists() else 0,
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
```

`_COMMANDS`에 `"evaluate": _cmd_evaluate` 추가.

- [ ] **Step 5: 통과 확인 + 백엔드 전체 회귀**

Run: `$PY -m pytest tests/ -q -x`
Expected: 전부 PASS (main 기준 1072건 + 이번 추가분)

- [ ] **Step 6: 버전 로그 줄 추가**

```markdown
  - `evaluate`: 9조합 지표(전체·base/hard·원천·hard 종류별) → 판정(그룹별 MRR 1위, bootstrap 동률이면 낮은 차원·짧은 p95, 로컬은 동시 상주·p95 ≤ 500ms 게이트와 기준선 qwen3@1536 대비 유의할 때만 교체) → `data/eval/results/embedding-benchmark-YYYY-MM-DD/`(`results.json`·`report.md`).
```

- [ ] **Step 7: 커밋**

```bash
git add backend/apps/rag/adapter/inbound/cli/ backend/tests/test_rag_benchmark_core.py backend/docs/backend_ver_log.md
git commit -m "backend v0.64.0: 벤치마크 evaluate (지표 집계·판정 규칙·보고서)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 어려운 질문 생성·1차 판정 → 사용자 검수 (사람 게이트)

**Files:**
- Modify (데이터): `data/eval/rag_evalset.jsonl`, `data/eval/rag_evalset_review.md`

코드 변경이 없다. 실행만 한다. Claude API 비용이 든다(생성 60건 + 판정 60건, effort low).

- [ ] **Step 1: 생성**

```bash
$PY -m apps.rag.adapter.inbound.cli.generate_evalset --provider claude --hard-kind colloquial --limit 20
$PY -m apps.rag.adapter.inbound.cli.generate_evalset --provider claude --hard-kind sibling --limit 20
$PY -m apps.rag.adapter.inbound.cli.generate_evalset --provider claude --hard-kind news_event --limit 20
```

Expected: 종류마다 `hard/{kind} 20건 추가`. 20건이 안 되면(짝 공고·사건 부족) 건수를 그대로 보고하고 진행한다.

- [ ] **Step 2: 검수 시트 추가 + Claude 1차 판정**

```bash
$PY -m apps.rag.adapter.inbound.cli.review_evalset sheet
$PY -m apps.rag.adapter.inbound.cli.judge_evalset
```

Expected: `검수 시트에 60건 추가 (기존 200건 유지)`, `claude 판정 60건 → O n / X m`

- [ ] **Step 3: 커밋 (candidate 상태)**

```bash
git add -f data/eval/rag_evalset.jsonl data/eval/rag_evalset_review.md
git commit -m "data: 어려운 평가 질문 60건 생성·Claude 1차 판정 (candidate, 사람 검수 대기)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: 멈추고 사용자에게 검수 요청**

사용자에게 알린다: `data/eval/rag_evalset_review.md`의 201번 이후 항목에서 판정란(Claude 1차 판정이 미리 채워짐)을 확인·수정해 달라고. 끝나면 사용자가 알려 준다. **사용자 응답 전에는 Task 8로 넘어가지 않는다.**

- [ ] **Step 5: 검수 반영 (사용자 완료 후)**

```bash
$PY -m apps.rag.adapter.inbound.cli.review_evalset apply
git add -f data/eval/rag_evalset.jsonl data/eval/rag_evalset_review.md
git commit -m "data: 어려운 평가 질문 검수 반영

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `반영 완료: confirmed …` — confirmed 수는 180 + 어려운 질문 O 판정 수.

---

### Task 8: 벤치마크 실행·보고서·문서

**Files:**
- Create (데이터): `data/eval/results/embedding-benchmark-YYYY-MM-DD/{results.json,report.md,corpus.jsonl.sha256}`
- Modify: `docs/STATUS.md`, `backend/docs/backend_ver_log.md`, `docs/superpowers/specs/2026-10-04-embedding-benchmark-design.md` (§9 해소 표시)

- [ ] **Step 1: 스냅샷을 다시 고정 (검수 후 기준)**

```bash
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings snapshot
```

Task 4 스모크 이후 색인 크론이 돌았을 수 있다. 이전 캐시가 있으면 지운다: `rm -rf ../data/eval/cache/embedding-benchmark/{bge-m3,qwen3,gemini-001,gemini-2}` (이 디렉터리만. 지우기 전에 `ls`로 확인).

- [ ] **Step 2: 모델별 임베딩 (각각 따로, 백그라운드 가능)**

```bash
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings embed --model bge-m3
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings embed --model qwen3
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings embed --model gemini-001
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings embed --model gemini-2
```

qwen3 문서 임베딩은 fp16 모델(~8GB VRAM)을 쓴다. 다른 GPU 작업과 겹치지 않게 한다. 중간에 끊기면 같은 명령을 다시 실행하면 이어진다. Gemini 429로 재시도 예산이 소진돼 예외가 나도 다시 실행하면 된다.

Expected: 각 `embed …: 문서 샤드 18개 새로, 질의 N건 새로`. N = confirmed 수.

- [ ] **Step 3: 지연·상주 측정**

```bash
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings latency --model bge-m3
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings latency --model qwen3
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings latency --model gemini-001
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings latency --model gemini-2
```

qwen3 지연 측정 전에 fp16 프로세스가 끝났는지 확인한다(`nvidia-smi`).

- [ ] **Step 4: 평가·판정**

```bash
$PY -m apps.rag.adapter.inbound.cli.benchmark_embeddings evaluate
cat ../data/eval/results/embedding-benchmark-*/report.md
```

Expected: 9행 표 + `로컬: **…**`, `API: **…**`. 기준선 `qwen3@1536`의 base subset Hit@5가 1.000 근처면 하네스가 운영 평가(`evaluate_rag --provider fp16`)와 맞는다는 뜻이다. 크게 다르면(±0.03 초과) 멈추고 원인을 보고한다.

- [ ] **Step 5: 보고서 보강 (손으로)**

`report.md` 끝에 `## 비용` 절을 덧붙인다. Gemini 두 모델의 색인 토큰(`results.json`의 `configs[*].tokens`)과 그날 공식 가격표로 계산한 1회 색인 비용을 적는다. 가격은 https://ai.google.dev/gemini-api/docs/pricing 에서 확인하고, 확인한 날짜와 URL을 같이 적는다. 429 재시도 횟수(`latency.retry_429`)도 적는다.

- [ ] **Step 6: 문서 갱신**

- `docs/STATUS.md` §4-4(평가셋) 아래에 "임베딩 모델 평가(10/4~)" 항목을 둔다. 평가셋 구성(confirmed 수, hard 수), 로컬·API 선정 결과, 보고서 경로를 각 1줄로 적는다.
- spec §9의 1~3번 각각 끝에 해소 결과를 덧붙인다.
  - 1번: `→ 해소(10/4): task_type 미지원, 프롬프트 프리픽스(Task 2)`
  - 2번: `→ F16(10/4 ollama show)`
  - 3번: `→ 재시도 n회(latency.json)`
- `backend_ver_log.md` v0.64.0에 `### Changed`(또는 Added 끝)로 결과 한 줄을 적는다: `- 평가 결과: 로컬 …(교체/현행 유지), API … — data/eval/results/embedding-benchmark-YYYY-MM-DD/report.md`

- [ ] **Step 7: 커밋**

```bash
git add -f data/eval/results/embedding-benchmark-*/
git add docs/STATUS.md docs/superpowers/specs/2026-10-04-embedding-benchmark-design.md backend/docs/backend_ver_log.md
git commit -m "backend v0.64.0: 임베딩 모델 평가 결과 — 로컬·API 각 1종 선정

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 8: 사용자에게 보고**

report.md의 표와 판정을 그대로 보여 준다. 운영 반영(스키마·재색인)은 spec §10에 따라 범위 밖이므로, 별도 스펙이 필요한지 묻는다. 푸시는 하지 않는다(사용자가 직접 실행).
