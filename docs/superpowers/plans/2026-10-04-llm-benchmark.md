# LLM 모델 평가 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 리포트 작성·의도 관문 두 역할에서 로컬 LLM 후보를 같은 입력으로 재고, 게이트 통과 모델 중 동률이면 VRAM이 작은 쪽을 고르는 규칙으로 역할별 1종과 16GB 동시 상주 조합을 정한다(온라인 Gemini는 비교군).

**Architecture:** 공통 통계(bootstrap·백분위·동률 판정·상주 확인)를 `core/matrix/grid_benchmark_manager.py`로 올리고 rag 하네스는 거기서 다시 가져온다. agent BC에 리포트 벤치 CLI(facts 고정 → 모델별 3회 실행 → 자동 채점 → 블라인드 판정 묶음 → 판정), intent BC에 관문 벤치 CLI(평가셋 검수 시트 → 모델별 3회 → 채점)를 둔다. 운영 경로는 바꾸지 않는다.

**Tech Stack:** Python 3.14, httpx(Ollama `/api/chat`), google-genai(Gemini), numpy, pytest.

**Spec:** `docs/superpowers/specs/2026-10-04-llm-benchmark-design.md`

## Global Constraints

- 리포트 후보: `gemma4:12b`, `gemma4:e4b`, `kanana1.5:8b-q4km`, `qwen3.5:9b`, `qwen3.5:4b`, `exaone3.5:7.8b`(도구 없이), 온라인 `gemini-2.5-flash`.
- 관문 후보: `gemma4:12b`, `gemma4:e4b`, `kanana1.5:8b-q4km`, `qwen3.5:9b`, `qwen3.5:4b`, `qwen3.5:2b-q4_K_M`, 온라인 `gemini-2.5-flash`. EXAONE 제외.
- thinking 끔: gemma4·qwen3.5는 `think: false`. kanana·exaone은 thinking 미지원이라 `think`를 보내지 않는다. temperature 리포트 0.3, 관문 0.
- 리포트 게이트: 완주율 ≥ 0.95, 판정 일치 = 1.00, 숫자 지어내기 ≤ 0.05, 규칙 위반 0, 첫 글자 p95 ≤ 5초, 완료 p95 ≤ 60초. 주 지표 = 판정자 품질(근거 충실도 + 자연스러움, 각 1~5).
- 관문 게이트: 스키마 통과 ≥ 0.98, 지어내기 ≤ 0.05, p95 ≤ 3초. 주 지표 = 지역·업종 동시 정답률.
- 판정: 게이트 통과 로컬 모델 중 주 지표 1위, paired bootstrap(n=10000, seed 0) 95% 구간이 0을 포함하면 동률, 동률 중 VRAM 작은 순 → p95 짧은 순. 현행 gemma4:12b 우대 없음. 리포트+관문+bge-m3 동시 상주 게이트.
- 판정 라벨(`report_fallback._VERDICT_LABELS`): red 비추천, orange 조건부, clear 경고 없음, insufficient 판정 보류.
- 운영 경로(`analysis_dependencies`, `intent_dependencies`)는 수정 금지. 새 어댑터 인자의 기본값은 현재 동작 그대로.
- `if/elif` 타입 분기 대신 dict 디스패치·Strategy(CLAUDE.md §5). 백엔드 버전 `v0.66.0`, `backend/docs/backend_ver_log.md`에 Task마다 줄을 덧붙인다.
- `data/`는 gitignore — 커밋할 평가 파일은 `git add -f`.

## 실행 환경

워크트리 `/home/kimchungsik/projects/cloud.beyondfacade/.worktrees/llm-benchmark`(브랜치 `feat/llm-benchmark`). `backend/.env`, `data/raw`, `data/geojson`은 메인 체크아웃 심링크로 준비돼 있다.

```bash
cd /home/kimchungsik/projects/cloud.beyondfacade/.worktrees/llm-benchmark/backend
export PY=/home/kimchungsik/projects/cloud.beyondfacade/backend/.venv/bin/python
# <frozen site> sys.prefix RuntimeWarning 2줄은 무해하다.
```

## File Structure

| 파일 | 책임 | 구분 |
|---|---|---|
| `backend/core/matrix/grid_benchmark_manager.py` | 모델 평가 공통: `paired_bootstrap_ci`, `percentile`, `resident_models`, `pick_winner` | 신규 |
| `backend/apps/rag/adapter/inbound/cli/benchmark_core.py` | 위 4개를 core에서 가져오도록(이름은 그대로 노출) | 수정 |
| `backend/apps/agent/adapter/outbound/llm/ollama_llm_adapter.py` | `think`, `temperature` 인자 | 수정 |
| `backend/apps/intent/adapter/outbound/llm/ollama_intent_llm_adapter.py` | 로컬 관문 추출기 | 신규 |
| `backend/apps/intent/adapter/outbound/llm/gemini_intent_llm_adapter.py` | `_instruction`·`_SCHEMA` 공개 이름으로(`instruction`, `INTENT_SCHEMA`) | 수정 |
| `backend/apps/intent/adapter/inbound/cli/intent_bench_scoring.py` | 관문 채점 순수 로직 | 신규 |
| `backend/apps/intent/adapter/inbound/cli/benchmark_intent.py` | 관문 CLI: `masters`·`sheet`·`apply`·`run`·`evaluate` | 신규 |
| `backend/apps/agent/adapter/inbound/cli/report_bench_scoring.py` | 리포트 채점 순수 로직(숫자 대조·판정 일치·LLM 작성 절·판정자 묶음) | 신규 |
| `backend/apps/agent/adapter/inbound/cli/benchmark_report.py` | 리포트 CLI: `freeze`·`run`·`score`·`judge-export`·`judge-import`·`residency`·`evaluate` | 신규 |
| 테스트 `backend/tests/test_core_benchmark_manager.py`, `test_agent_ollama_options.py`, `test_intent_ollama_adapter.py`, `test_intent_bench_scoring.py`, `test_report_bench_scoring.py`, `test_report_bench_cli.py` | | 신규 |

---

### Task 1: 공통 통계를 core로 승격

**Files:**
- Create: `backend/core/matrix/grid_benchmark_manager.py`, `backend/tests/test_core_benchmark_manager.py`
- Modify: `backend/apps/rag/adapter/inbound/cli/benchmark_core.py`, `backend/docs/backend_ver_log.md`

**Interfaces:**
- Produces: `paired_bootstrap_ci(a, b, n=10_000, seed=0) -> tuple[float, float, float]`, `percentile(samples, q) -> float`, `resident_models(ps_json) -> set[str]`, `pick_winner(score_by: dict[str, list[float]], cost_by: dict[str, float], p95_by: dict[str, float | None], eligible: list[str]) -> tuple[str, list[str]]` (cost가 작을수록 우선 — 임베딩은 차원, LLM은 VRAM MiB).

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_core_benchmark_manager.py`:

```python
"""모델 평가 공통 통계 — rag·agent·intent 하네스가 함께 쓴다."""

import pytest

from core.matrix.grid_benchmark_manager import paired_bootstrap_ci, percentile, pick_winner, resident_models


def test_bootstrap_같은_점수면_0():
    assert paired_bootstrap_ci([1.0, 0.5], [1.0, 0.5]) == (0.0, 0.0, 0.0)


def test_bootstrap_길이가_다르면_에러():
    with pytest.raises(ValueError):
        paired_bootstrap_ci([1.0], [1.0, 0.0])


def test_백분위():
    assert percentile([10.0, 20.0, 30.0], 50) == 20.0


def test_상주_모델():
    assert resident_models({"models": [{"name": "bge-m3:latest"}]}) == {"bge-m3:latest"}


def test_동률이면_비용이_작은_쪽():
    s = {"big": [1.0, 0.5] * 20, "small": [1.0, 0.5] * 20}
    winner, tied = pick_winner(s, {"big": 7600, "small": 1900}, {}, ["big", "small"])
    assert winner == "small" and tied == ["big", "small"]


def test_유의하게_높으면_비용이_커도_이긴다():
    s = {"big": [1.0] * 40, "small": [0.5] * 40}
    assert pick_winner(s, {"big": 7600, "small": 1900}, {}, ["big", "small"])[0] == "big"
```

- [ ] **Step 2: 실패 확인** — `$PY -m pytest tests/test_core_benchmark_manager.py -q` → `ModuleNotFoundError`.

- [ ] **Step 3: 구현** — `backend/core/matrix/grid_benchmark_manager.py`:

```python
"""모델 평가 공통 통계 — 임베딩(rag)·LLM(agent·intent) 하네스가 함께 쓴다 (numpy만).

판정 원칙(2026-10-04 사용자 결정): 주 지표 1위와 paired bootstrap 95% 구간이 0을 포함하면 동률,
동률 중 비용(임베딩=차원, LLM=VRAM)이 작은 순 → p95가 짧은 순.
"""

from statistics import mean

import numpy as np


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


def pick_winner(
    score_by: dict[str, list[float]], cost_by: dict[str, float], p95_by: dict[str, float | None], eligible: list[str]
) -> tuple[str, list[str]]:
    """평균 점수 1위와 bootstrap 동률인 후보 중 (비용, p95, 이름) 최소. 반환: (승자, 동률 목록)."""
    best = max(eligible, key=lambda c: (mean(score_by[c]), -cost_by[c]))
    tied = sorted(c for c in eligible if c == best or paired_bootstrap_ci(score_by[best], score_by[c])[1] <= 0)
    winner = min(tied, key=lambda c: (cost_by[c], p95_by.get(c) or float("inf"), c))
    return winner, tied
```

`backend/apps/rag/adapter/inbound/cli/benchmark_core.py`: `paired_bootstrap_ci`, `percentile`, `resident_models`, `pick_winner` 정의를 지우고 맨 위 import에 `from core.matrix.grid_benchmark_manager import paired_bootstrap_ci, percentile, pick_winner, resident_models` 를 추가한다(rag 쪽 호출부·테스트는 같은 이름으로 그대로 동작). 지운 뒤 쓰이지 않는 import(`mean`은 `aggregate`가 계속 쓰므로 유지)가 없는지 확인한다.

- [ ] **Step 4: 통과 + rag 회귀** — `$PY -m pytest tests/test_core_benchmark_manager.py tests/test_rag_benchmark_core.py tests/test_rag_benchmark_cli.py -q` 전부 PASS.

- [ ] **Step 5: 버전 로그** — `# Backend Version Log` 바로 아래에:

```markdown
## [v0.66.0] - 2026-10-04

### Added
- **LLM 모델 평가 하네스** (spec `docs/superpowers/specs/2026-10-04-llm-benchmark-design.md`) — 리포트 작성·의도 관문 두 역할에서 로컬 후보를 같은 입력으로 재고, 게이트 통과 모델 중 동률이면 VRAM이 작은 쪽을 고른다. 운영 경로는 바꾸지 않는다.
  - 공통 통계를 `core/matrix/grid_benchmark_manager.py`로 올렸다(bootstrap·백분위·상주 확인·동률 판정). rag 임베딩 하네스도 여기서 가져온다.
```

- [ ] **Step 6: 커밋** — `git add backend/core/matrix/grid_benchmark_manager.py backend/tests/test_core_benchmark_manager.py backend/apps/rag/adapter/inbound/cli/benchmark_core.py backend/docs/backend_ver_log.md && git commit -m "backend v0.66.0: 모델 평가 공통 통계를 core로 승격" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 2: Ollama LLM 어댑터 `think`·`temperature`

**Files:** Modify `backend/apps/agent/adapter/outbound/llm/ollama_llm_adapter.py`; Create `backend/tests/test_agent_ollama_options.py`; Modify ver log.

**Interfaces:** Produces `OllamaLLMAdapter(model="gemma3:12b", base_url=None, transport=None, think: bool | None = None, temperature: float | None = None)`. `None`이면 요청 바디에 그 키를 넣지 않는다(현 동작).

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_agent_ollama_options.py`:

```python
"""Ollama LLM 어댑터 옵션 — think·temperature는 줄 때만 요청에 실린다."""

import json

import httpx

from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter


def _capture(bodies):
    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "ok"}, "done": True})
    return httpx.MockTransport(handler)


def test_기본값은_think와_options를_보내지_않는다():
    bodies = []
    OllamaLLMAdapter(model="m", base_url="http://x", transport=_capture(bodies)).chat([], [])
    assert "think" not in bodies[0] and "options" not in bodies[0]


def test_think와_temperature를_주면_실린다():
    bodies = []
    adapter = OllamaLLMAdapter(model="m", base_url="http://x", transport=_capture(bodies), think=False, temperature=0.3)
    adapter.chat([], [])
    assert bodies[0]["think"] is False and bodies[0]["options"] == {"temperature": 0.3}


def test_스트림도_같은_옵션을_싣는다():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, text='{"message":{"content":"a"},"done":true,"eval_count":1}\n')

    adapter = OllamaLLMAdapter(model="m", base_url="http://x", transport=httpx.MockTransport(handler), think=False, temperature=0.3)
    list(adapter.stream([], []))
    assert bodies[0]["think"] is False and bodies[0]["options"] == {"temperature": 0.3}
```

- [ ] **Step 2: 실패 확인** — `$PY -m pytest tests/test_agent_ollama_options.py -q` → `unexpected keyword argument 'think'`.

- [ ] **Step 3: 구현** — 생성자에 `think: bool | None = None, temperature: float | None = None`을 더하고 docstring Args에 두 줄을 추가한다. 두 값을 저장하고, 요청 바디를 만드는 헬퍼를 둔다:

```python
    def _body(self, messages: list[dict], tools: list[LLMToolSpec], stream: bool) -> dict:
        """요청 바디 — think·temperature는 지정했을 때만 싣는다(미지정이면 지금과 같은 요청)."""
        body = {
            "model": self.model_name,
            "messages": messages,
            "tools": [_to_ollama_tool(tool) for tool in tools],
            "stream": stream,
        }
        if self._think is not None:
            body["think"] = self._think
        if self._temperature is not None:
            body["options"] = {"temperature": self._temperature}
        return body
```

`chat`의 `json={...}`를 `json=self._body(messages, tools, stream=False)`, `stream`의 `json={...}`를 `json=self._body(messages, tools, stream=True)`로 바꾼다. (`is not None` 검사는 값 유무 확인이지 타입 분기가 아니다.)

- [ ] **Step 4: 통과 + 회귀** — `$PY -m pytest tests/test_agent_ollama_options.py tests/test_agent_llm_adapters.py tests/test_agent_llm_stream.py tests/test_ollama_base_url.py -q` PASS.
- [ ] **Step 5: 버전 로그** — v0.66.0 Added에 `  - Ollama LLM 어댑터에 \`think\`·\`temperature\` 인자(지정할 때만 요청에 실림, 기본값은 기존 요청 그대로).`
- [ ] **Step 6: 커밋** — `backend v0.66.0: Ollama LLM 어댑터 think·temperature 옵션` (+ Co-Authored-By 줄).

---

### Task 3: 로컬 관문 추출기 `OllamaIntentLlmAdapter`

**Files:** Create `backend/apps/intent/adapter/outbound/llm/ollama_intent_llm_adapter.py`, `backend/tests/test_intent_ollama_adapter.py`; Modify `gemini_intent_llm_adapter.py`(공개 이름), ver log.

**Interfaces:**
- `gemini_intent_llm_adapter.py`: `_SCHEMA` → `INTENT_SCHEMA`, `_instruction` → `instruction` (모듈 안 사용처도 바꾼다).
- Produces `OllamaIntentLlmAdapter(masters: MasterDictionaryPort, model: str, base_url: str | None = None, transport=None, think: bool | None = None, timeout_s: float = 30.0)`, `extract(text) -> LlmSuggestion | None`, 속성 `model_name`.

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_intent_ollama_adapter.py`:

```python
"""로컬 관문 추출기 — Gemini와 같은 지시문·스키마를 Ollama format으로, 실패는 None."""

import json

import httpx

from apps.intent.adapter.outbound.llm.gemini_intent_llm_adapter import INTENT_SCHEMA
from apps.intent.adapter.outbound.llm.ollama_intent_llm_adapter import OllamaIntentLlmAdapter
from apps.intent.domain.value_objects.master_dictionary import MasterDictionary


class _Masters:
    def load(self):
        return _dictionary()


def _dictionary():
    from tests.test_intent_llm_adapter import FakeMasters  # 기존 테스트의 가짜 마스터를 재사용

    return FakeMasters().load()


def _adapter(handler, **kw):
    return OllamaIntentLlmAdapter(_Masters(), model="qwen3.5:4b", base_url="http://x", transport=httpx.MockTransport(handler), **kw)


def test_요청에_스키마와_temperature_0과_지시문이_실린다():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": '{"region_name":"서교동","industry_id":null,"budget_krw":null}'}})

    s = _adapter(handler, think=False).extract("홍대 근처")
    assert s.region_name == "서교동" and s.industry_id is None
    body = bodies[0]
    assert body["format"] == INTENT_SCHEMA and body["options"] == {"temperature": 0} and body["think"] is False
    assert body["stream"] is False and body["messages"][0]["role"] == "system"


def test_스키마가_깨지면_None():
    s = _adapter(lambda r: httpx.Response(200, json={"message": {"content": "그냥 글"}})).extract("x")
    assert s is None


def test_서버_오류도_None():
    assert _adapter(lambda r: httpx.Response(500)).extract("x") is None
```

주의: `tests/test_intent_llm_adapter.py`의 `FakeMasters` 이름·형태를 먼저 읽고, 다르면 같은 방식의 최소 가짜 마스터를 이 파일에 직접 둔다(지역 1~2개, 업종 1~2개).

- [ ] **Step 2: 실패 확인** — `$PY -m pytest tests/test_intent_ollama_adapter.py -q` → ImportError.

- [ ] **Step 3: 구현** — `ollama_intent_llm_adapter.py`:

```python
"""Ollama 관문 추출기 — Gemini 폴백(`gemini_intent_llm_adapter`)과 같은 지시문·JSON 스키마를 로컬 모델로.

LLM 모델 평가(2026-10-04)용이며 운영 배선(intent_dependencies)에는 아직 넣지 않는다. 어떤 실패든 None —
관문은 LLM 장애로 죽지 않는다(IntentLlmPort 계약).
"""

import json
import logging

import httpx

from apps.intent.adapter.outbound.llm.gemini_intent_llm_adapter import INTENT_SCHEMA, instruction
from apps.intent.app.dtos.intent_dto import LlmSuggestion
from apps.intent.app.ports.output.intent_port import IntentLlmPort, MasterDictionaryPort
from core.matrix.grid_keymaker_secret_manager import get_settings

LOGGER = logging.getLogger("beyondfacade.intent.llm")


class OllamaIntentLlmAdapter(IntentLlmPort):
    def __init__(
        self,
        masters: MasterDictionaryPort,
        model: str,
        base_url: str | None = None,
        transport=None,
        think: bool | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._masters = masters
        self.model_name = model
        self._think = think
        self._client = httpx.Client(
            base_url=base_url or get_settings().ollama_base_url, transport=transport, timeout=timeout_s
        )

    def extract(self, text: str) -> LlmSuggestion | None:
        try:
            body = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": instruction(self._masters.load())},
                    {"role": "user", "content": text},
                ],
                "format": INTENT_SCHEMA,
                "options": {"temperature": 0},
                "stream": False,
            }
            if self._think is not None:
                body["think"] = self._think
            response = self._client.post("/api/chat", json=body)
            response.raise_for_status()
            payload = json.loads(response.json()["message"]["content"])
            return LlmSuggestion(
                region_name=payload.get("region_name") or None,
                industry_id=payload.get("industry_id") or None,
                budget_krw=payload.get("budget_krw") or None,
            )
        except Exception as error:  # noqa: BLE001 — 폴백은 어떤 실패도 None으로 넘긴다
            LOGGER.warning("intent 로컬 LLM 실패: %s", error)
            return None
```

`INTENT_SCHEMA`의 `"nullable": True`는 Gemini 표기다. Ollama `format`은 JSON Schema라 `nullable`을 무시할 수 있다 — 0단계 프로토콜 확인(Task 8)에서 각 모델이 null을 내는지 본다. 동작하지 않으면 그때 Ollama용 스키마(`"type": ["string", "null"]`)를 이 모듈에 따로 둔다(그 경우 테스트의 `body["format"] == INTENT_SCHEMA` 단언도 함께 바꾼다).

- [ ] **Step 4: 통과 + 회귀** — `$PY -m pytest tests/test_intent_ollama_adapter.py tests/test_intent_llm_adapter.py -q` PASS (+ intent 관련 테스트 `tests/ -q -k intent`).
- [ ] **Step 5: 버전 로그** — `  - 로컬 관문 추출기 \`OllamaIntentLlmAdapter\`(Gemini 폴백과 같은 지시문·스키마, Ollama format). 운영 배선에는 넣지 않음.`
- [ ] **Step 6: 커밋** — `backend v0.66.0: 로컬 의도 관문 추출기(Ollama)`.

---

### Task 4: 관문 채점 순수 로직 + 관문 벤치 CLI

**Files:** Create `backend/apps/intent/adapter/inbound/cli/intent_bench_scoring.py`, `backend/apps/intent/adapter/inbound/cli/benchmark_intent.py`, `backend/tests/test_intent_bench_scoring.py`; Modify ver log.

**Interfaces:**
- `score_row(expected: dict, got: LlmSuggestion | None) -> dict` → `{"schema_ok": bool, "both": 1.0|0.0, "region": 1.0|0.0, "industry": 1.0|0.0, "budget": 1.0|0.0, "null_slots": int, "fabricated": bool}`
  - `got is None` → schema_ok False, 나머지 0, fabricated False.
  - 정답이 None인 필드에 값이 나오면 fabricated True. `null_slots` = 정답 None 필드 수.
- `summarize(rows: list[dict]) -> dict` → `{"n", "schema_rate", "both", "region", "industry", "budget", "fabrication_rate"}` (fabrication_rate 분모는 null_slots > 0인 행).
- `render_sheet(rows) -> str`, `parse_sheet(text) -> dict[str, tuple[str|None, dict]]` (id → (O/X/None, 정답 dict)).
- 평가셋 파일 `data/eval/intent_evalset.jsonl` 한 줄: `{"id","text","kind","expected":{"region_name","industry_id","budget_krw"},"status"}`.
- CLI `benchmark_intent`:
  - `masters --out PATH` — 마스터(동 이름·구·업종 id/이름)를 json으로 내보낸다(라벨 작성자용).
  - `sheet` — `data/eval/intent_evalset_review.md` 생성(`## <id>` / `입력:` / `정답: region=... industry=... budget=...` / `판정:`).
  - `apply` — 시트 판정 반영(O → confirmed, 정답 줄 수정 반영 / X → rejected).
  - `run --model NAME [--repeat 3]` — confirmed 문항을 모델로 추출, 문항·회차별 `{id, rep, ms, got}`를 `data/eval/cache/llm-benchmark/intent/<model>.jsonl`에 저장(이어 쓰기 가능하게 (id,rep) 있으면 건너뜀).
  - `evaluate` — 모델별 1회차 정확도·스키마·지어내기, 3회 지연 p50/p95를 `data/eval/cache/llm-benchmark/intent_summary.json`에 저장(최종 판정·보고서는 Task 6 `benchmark_report evaluate`가 합친다).
- 모델 레지스트리(dict): 로컬 6종 → `OllamaIntentLlmAdapter(masters, model=..., think=False|None, timeout_s=30)`, `gemini-2.5-flash` → `GeminiIntentLlmAdapter(masters)`. think: gemma4·qwen3.5 False, kanana None.

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_intent_bench_scoring.py`:

```python
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
```

- [ ] **Step 2: 실패 확인** — ImportError.

- [ ] **Step 3: 구현 `intent_bench_scoring.py`**:

```python
"""관문 LLM 채점 — 순수 함수 (DB·네트워크 없음)."""

import re

from apps.intent.app.dtos.intent_dto import LlmSuggestion

_FIELDS = ("region_name", "industry_id", "budget_krw")


def score_row(expected: dict, got: LlmSuggestion | None) -> dict:
    null_slots = sum(1 for f in _FIELDS if expected[f] is None)
    if got is None:
        return {"schema_ok": False, "both": 0.0, "region": 0.0, "industry": 0.0, "budget": 0.0,
                "null_slots": null_slots, "fabricated": False}
    hit = {f: float(getattr(got, f) == expected[f]) for f in _FIELDS}
    fabricated = any(expected[f] is None and getattr(got, f) is not None for f in _FIELDS)
    return {"schema_ok": True, "both": float(hit["region_name"] and hit["industry_id"]),
            "region": hit["region_name"], "industry": hit["industry_id"], "budget": hit["budget_krw"],
            "null_slots": null_slots, "fabricated": fabricated}


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    with_null = [r for r in rows if r["null_slots"] > 0]
    avg = lambda key: sum(r[key] for r in rows) / n if n else 0.0  # noqa: E731
    return {"n": n, "schema_rate": avg("schema_ok"), "both": avg("both"), "region": avg("region"),
            "industry": avg("industry"), "budget": avg("budget"),
            "fabrication_rate": sum(r["fabricated"] for r in with_null) / len(with_null) if with_null else 0.0}


def _fmt(v) -> str:
    return "null" if v is None else str(v)


def render_sheet(rows: list[dict]) -> str:
    head = ("# 관문 평가셋 검수 시트\n\n입력에 맞는 정답이면 `판정: O`, 틀린 칸은 `정답:` 줄을 고친 뒤 O. 쓸 수 없는 문항은 X.\n"
            "정답 줄 형식: `정답: region=<동 이름|null> industry=<업종 id|null> budget=<원 정수|null>`\n\n---\n")
    items = [
        f"## {r['id']} ({r['kind']})\n입력: {r['text']}\n"
        f"정답: region={_fmt(r['expected']['region_name'])} industry={_fmt(r['expected']['industry_id'])} "
        f"budget={_fmt(r['expected']['budget_krw'])}\n판정: \n\n"
        for r in rows
    ]
    return head + "".join(items)


_ID = re.compile(r"^## (\S+)")
_ANS = re.compile(r"^정답:\s*region=(\S+)\s+industry=(\S+)\s+budget=(\S+)\s*$")
_VERDICT = re.compile(r"^판정:\s*([^#\s]*)")


def _value(raw: str, cast=str):
    return None if raw == "null" else cast(raw)


def parse_sheet(text: str) -> dict[str, tuple[str | None, dict]]:
    out: dict[str, tuple[str | None, dict]] = {}
    current, expected = None, None
    for line in text.split("\n"):
        if m := _ID.match(line):
            current, expected = m.group(1), None
        elif (m := _ANS.match(line)) and current:
            expected = {"region_name": _value(m.group(1)), "industry_id": _value(m.group(2)),
                        "budget_krw": _value(m.group(3), int)}
        elif (m := _VERDICT.match(line)) and current:
            out[current] = ((m.group(1).upper() or None), expected)
            current = None
    return out
```

- [ ] **Step 4: 구현 `benchmark_intent.py`** — 위 Interfaces의 명령 5개. 구조는 rag `benchmark_embeddings.py`를 따른다(`_REPO_ROOT = parents[6]`, `_COMMANDS` dict 디스패치, 캐시 `data/eval/cache/llm-benchmark/intent/`). 핵심 코드:

```python
_MODELS = {
    "gemma4:12b": lambda m: OllamaIntentLlmAdapter(m, model="gemma4:12b", think=False),
    "gemma4:e4b": lambda m: OllamaIntentLlmAdapter(m, model="gemma4:e4b", think=False),
    "kanana1.5:8b-q4km": lambda m: OllamaIntentLlmAdapter(m, model="kanana1.5:8b-q4km"),
    "qwen3.5:9b": lambda m: OllamaIntentLlmAdapter(m, model="qwen3.5:9b", think=False),
    "qwen3.5:4b": lambda m: OllamaIntentLlmAdapter(m, model="qwen3.5:4b", think=False),
    "qwen3.5:2b-q4_K_M": lambda m: OllamaIntentLlmAdapter(m, model="qwen3.5:2b-q4_K_M", think=False),
    "gemini-2.5-flash": lambda m: GeminiIntentLlmAdapter(m),
}
```

`run`: `masters = MasterDictionaryGateway()`, `adapter = _MODELS[args.model](masters)`, 워밍업 1회(지연 제외), confirmed 문항 × repeat, `time.perf_counter()`로 ms, 결과를 jsonl에 한 줄씩 append(`got`은 `asdict(suggestion)` 또는 None). `evaluate`: 모델별 파일을 읽어 rep 0의 `score_row`로 `summarize`, 문항별 `both` 점수 배열(`per_row_both`), 전체 ms의 p50/p95(`core.matrix.grid_benchmark_manager.percentile`)를 summary json에 쓴다. `masters`: `MasterDictionaryGateway().load()`의 regions(name, district) · industry_names를 json으로.

- [ ] **Step 5: 통과** — `$PY -m pytest tests/test_intent_bench_scoring.py -q` PASS. 스모크: `$PY -m apps.rag... ` 대신 `$PY -m apps.intent.adapter.inbound.cli.benchmark_intent masters --out /tmp/claude-1000/masters.json` 가 동 427개·업종 목록을 쓰는지 확인(`python3 -c` 로 개수 출력).
- [ ] **Step 6: 버전 로그** — `  - 관문 벤치 CLI \`benchmark_intent\`(masters·sheet·apply·run·evaluate)와 채점(정답·null·지어내기·스키마).`
- [ ] **Step 7: 커밋** — `backend v0.66.0: 의도 관문 벤치 CLI·채점`.

---

### Task 5: 리포트 채점 순수 로직

**Files:** Create `backend/apps/agent/adapter/inbound/cli/report_bench_scoring.py`, `backend/tests/test_report_bench_scoring.py`; Modify ver log.

**Interfaces (모두 순수):**
- `extract_numbers(text: str) -> list[tuple[str, float]]` — (원문 토큰, 정규화 값). 정규식 `(\d[\d,]*(?:\.\d+)?)\s*(%|퍼센트|억|천만|백만|만|천)?`. 단위 배수 `{"억":1e8,"천만":1e7,"백만":1e6,"만":1e4,"천":1e3}`, `%`·`퍼센트`는 값 그대로(퍼센트 표시). **단위 없는 정수 ≤ 10은 무시**(서수·개수 표현 오탐 방지), 4자리 연도(1990~2100, 단위 없음)도 무시.
- `fact_numbers(facts: object) -> list[float]` — facts JSON을 재귀로 돌며 int/float(bool 제외)와 문자열 안의 숫자(`extract_numbers`)를 모은다.
- `unmatched_numbers(report_md: str, facts: dict) -> list[str]` — 보고서 숫자 중 facts의 어떤 값과도 맞지 않는 토큰. 일치 규칙: 같은 값이거나, 보고서 값 = facts 값 × 100(비율→퍼센트), 또는 facts 값 = 보고서 값 × 단위배수 관계가 이미 반영된 값과 `abs(a-b) <= 0.5 * 10**(-소수자리수(보고서 토큰))`(표시 자릿수 반올림) — 즉 보고서 토큰의 소수 자릿수만큼 반올림해 같으면 일치.
- `VERDICT_LABELS = {"red": "비추천", "orange": "조건부", "clear": "경고 없음", "insufficient": "판정 보류"}`
- `verdict_matches(verdict_section_md: str, verdict_facts: dict) -> bool` — facts가 `available: False`면 섹션에 다른 세 라벨(비추천·조건부·경고 없음)이 없어야 True. 있으면 기대 라벨이 섹션에 있고 **다른 라벨이 없어야** True.
- `llm_sections(deltas: dict[str, str], fallbacks: dict[str, str]) -> set[str]` — 섹션별로 이어 붙인 본문이 폴백 문구와 다르고 비어 있지 않으면 LLM이 쓴 섹션.
- `judge_packets(scenario_id: str, facts: dict, reports: dict[str, str], seed: int) -> tuple[str, dict[str, str]]` — 모델명을 `A`·`B`… 로 가린 판정자용 마크다운과 `{가린 이름: 모델명}` 매핑. 순서는 `random.Random(f"{seed}:{scenario_id}").shuffle`(결정적).

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_report_bench_scoring.py`:

```python
"""리포트 채점 — 숫자 대조·판정 일치·LLM 작성 절·판정자 묶음."""

from apps.agent.adapter.inbound.cli.report_bench_scoring import (
    extract_numbers,
    judge_packets,
    llm_sections,
    unmatched_numbers,
    verdict_matches,
)


def test_숫자_추출은_단위와_쉼표를_정규화하고_작은_정수와_연도는_무시():
    got = dict(extract_numbers("폐업률 12.3%, 점포 1,234곳, 매출 3억, 2024년 기준 3가지"))
    assert got == {"12.3%": 12.3, "1,234": 1234.0, "3억": 3e8}


def test_비율은_퍼센트로_반올림해_맞춘다():
    facts = {"closure_rate": 0.1234, "stores": 1234, "sales": 300000000}
    assert unmatched_numbers("폐업률 12.3%, 점포 1,234곳, 매출 3억", facts) == []


def test_facts에_없는_숫자는_걸린다():
    assert unmatched_numbers("폐업률 45.6%", {"closure_rate": 0.1234}) == ["45.6%"]


def test_문자열_안의_숫자도_facts로_본다():
    assert unmatched_numbers("월세 250만", {"note": "평균 월세 250만원"}) == []


def test_판정_일치는_기대_라벨만_있어야():
    v = {"available": True, "verdict_code": "orange"}
    assert verdict_matches("### 판정\n조건부입니다.", v)
    assert not verdict_matches("### 판정\n비추천입니다.", v)
    assert not verdict_matches("### 판정\n조건부지만 비추천에 가깝다", v)


def test_판정_자료가_없으면_단정_라벨이_없어야():
    v = {"available": False}
    assert verdict_matches("### 판정\n판정 보류입니다.", v)
    assert not verdict_matches("### 판정\n경고 없음", v)


def test_폴백과_같은_절은_LLM_작성이_아니다():
    deltas = {"verdict": "### 판정\n코드 문구", "reasons": "### 이유\n모델이 쓴 글", "funding": ""}
    fallbacks = {"verdict": "### 판정\n코드 문구", "reasons": "### 이유\n분석 데이터가 부족합니다.", "funding": "x"}
    assert llm_sections(deltas, fallbacks) == {"reasons"}


def test_판정자_묶음은_모델명을_가리고_결정적이다():
    md1, map1 = judge_packets("s01", {"k": 1}, {"gemma4:12b": "글1", "qwen3.5:4b": "글2"}, seed=0)
    md2, map2 = judge_packets("s01", {"k": 1}, {"gemma4:12b": "글1", "qwen3.5:4b": "글2"}, seed=0)
    assert map1 == map2 and set(map1.values()) == {"gemma4:12b", "qwen3.5:4b"}
    assert "gemma4" not in md1 and "qwen" not in md1
```

- [ ] **Step 2: 실패 확인** — ImportError.

- [ ] **Step 3: 구현** — 위 Interfaces를 그대로 구현한다. 반올림 일치는 `_decimals(token)`(토큰 숫자부의 소수 자릿수)로 `round(fact_value_scaled, d) == round(report_value, d)`를 비교하되, 퍼센트 토큰은 `fact*100`과 `fact` 둘 다 후보로, 단위 토큰(억·만…)은 이미 배수를 곱한 값끼리 비교하고 facts 쪽은 `round(f / 배수, d) == 숫자부`도 허용(예: facts 312,000,000 ↔ "3.1억"). 판정자 묶음 마크다운 형식:

```
# 시나리오 {scenario_id}

## 사실 묶음(요약)
```json
{facts json, ensure_ascii=False, indent=1, 3,000자에서 자름}
```

## 리포트 A
{본문}

## 리포트 B
...
```

- [ ] **Step 4: 통과** — `$PY -m pytest tests/test_report_bench_scoring.py -q` PASS.
- [ ] **Step 5: 버전 로그** — `  - 리포트 채점(숫자 지어내기 대조·판정 일치·LLM 작성 절·블라인드 판정자 묶음).`
- [ ] **Step 6: 커밋** — `backend v0.66.0: 리포트 벤치 채점 로직`.

---

### Task 6: 리포트 벤치 CLI + 판정·보고서

**Files:** Create `backend/apps/agent/adapter/inbound/cli/benchmark_report.py`, `backend/tests/test_report_bench_cli.py`; Modify ver log.

**Interfaces:**
- 경로: `data/eval/report_scenarios.jsonl`, `data/eval/report_facts/<id>.json`, 캐시 `data/eval/cache/llm-benchmark/report/<model>.jsonl`, 판정 `data/eval/cache/llm-benchmark/judge/`, 결과 `data/eval/results/llm-benchmark-YYYY-MM-DD/`.
- `FrozenFacts(facts_by_key: dict[tuple[str, str], dict])` — `collect(region, industry, budget=None, question=None) -> dict` 이 `(region, industry)`의 고정 facts를 돌려준다(`AnalysisInteractor`의 `facts` 자리에 들어간다).
- 모델 레지스트리 `REPORT_MODELS: dict[str, ReportModel]`, `ReportModel(name, llm: Callable[[], LLMGatewayPort], tools: bool, local: bool)`:
  - 로컬: `OllamaLLMAdapter(model=..., think=False|None, temperature=0.3)`, tools True. exaone은 `think=None`, **tools False**.
  - `gemini-2.5-flash`: `GeminiLLMAdapter`, tools True, local False.
- 명령:
  - `freeze` — 시나리오별 `ReportFactsCollector`(운영 배선과 같은 게이트웨이: `analysis_dependencies.build_analysis_use_case`가 쓰는 것과 같은 생성자들)로 facts를 모아 `report_facts/<id>.json`에 쓴다.
  - `run --model NAME [--repeat 3]` — 시나리오 × 회차마다 `AnalysisInteractor(llm=..., tools=build_tools(...) if model.tools else [], facts=FrozenFacts(...))`를 `run(region_code, industry_id, question)`으로 돌려 이벤트를 모은다. 기록: `{id, rep, first_ms, total_ms, sections: {name: markdown}, tool_calls: [..], usage, error}`. 시계는 `facts` 이벤트 수신 시각을 0으로, 첫 `report_delta`까지(first_ms), `report_done`까지(total_ms). (id,rep) 있으면 건너뛴다.
  - `score` — 모델별: 리포트마다 `llm_sections`(폴백 문구는 `analysis_interactor._fallback_section(name, title, facts)`와 `_SECTIONS`로 계산), 완주(6절 모두 LLM 작성 & error 없음), `verdict_matches`(verdict 절 vs facts["verdict"]), `unmatched_numbers`(6절 이어 붙인 본문), `check_rule_keywords`(기존 `agent_eval_scoring`) 결과를 `score_<model>.json`에.
  - `judge-export` — 1회차 리포트를 시나리오별 `judge_packets`로 `judge/packet_<id>.md` + `judge/mapping.json`.
  - `judge-import --file PATH` — 판정 파일(json: `{scenario_id: {A: {"faithfulness":1-5,"fluency":1-5,"violations":[...] }, ...}}`)을 매핑으로 모델명에 되돌려 `judge/scores.json`.
  - `residency --report-model R --intent-model I` — R, I, `bge-m3`를 차례로 올리고(`/api/generate` 빈 프롬프트·`/api/embed`, keep_alive 10m) `/api/ps`로 셋 다 상주인지 + nvidia-smi 사용 MiB + 모델별 SIZE(`ollama ps` 크기)를 `residency.json`에.
  - `vram` — 로컬 모델마다 하나씩 올려 `/api/ps`의 `size_vram`(MiB)을 `vram.json`에(판정 비용).
  - `evaluate` — 리포트·관문 각각 게이트 → 로컬 승자(`pick_winner`, cost=VRAM MiB) → 동률·승자 → 상주 결과를 붙여 `results.json`·`report.md`.
- 판정 순수 함수(같은 파일 또는 `report_bench_scoring.py`에 두고 테스트): `report_gates(score: dict, latency: dict) -> dict[str, bool]`, `intent_gates(summary: dict) -> dict[str, bool]`, `render_llm_report(results: dict) -> str`.

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_report_bench_cli.py`:

```python
"""리포트 벤치 CLI 순수 부분 — 고정 facts, 게이트, 보고서."""

from apps.agent.adapter.inbound.cli.benchmark_report import FrozenFacts, REPORT_MODELS
from apps.agent.adapter.inbound.cli.report_bench_scoring import intent_gates, render_llm_report, report_gates


def test_고정_facts는_지역_업종으로_돌려준다():
    f = FrozenFacts({("1111", "cafe"): {"verdict": {"available": True}}})
    assert f.collect("1111", "cafe", None, "q") == {"verdict": {"available": True}}


def test_레지스트리_exaone만_도구_없음_gemini만_온라인():
    assert [n for n, m in REPORT_MODELS.items() if not m.tools] == ["exaone3.5:7.8b"]
    assert [n for n, m in REPORT_MODELS.items() if not m.local] == ["gemini-2.5-flash"]


def test_리포트_게이트():
    score = {"completion": 0.97, "verdict_match": 1.0, "fabrication": 0.03, "rule_violations": 0}
    lat = {"first_p95_ms": 4000, "total_p95_ms": 50000}
    assert all(report_gates(score, lat).values())
    assert report_gates({**score, "verdict_match": 0.97}, lat)["verdict_match"] is False


def test_관문_게이트():
    s = {"schema_rate": 0.99, "fabrication_rate": 0.02, "p95_ms": 2500}
    assert all(intent_gates(s).values())
    assert intent_gates({**s, "p95_ms": 3100})["latency"] is False


def test_보고서에_역할별_승자와_상주_결과():
    results = {
        "date": "2026-10-04",
        "report": {"rows": [{"model": "qwen3.5:4b", "vram_mib": 3400, "quality": 7.2, "gates": {"all": True},
                              "first_p95_ms": 3000, "total_p95_ms": 40000}],
                   "winner": "qwen3.5:4b", "tied": ["qwen3.5:4b"]},
        "intent": {"rows": [{"model": "qwen3.5:2b-q4_K_M", "vram_mib": 1900, "both": 0.9, "gates": {"all": True},
                              "p95_ms": 900}],
                   "winner": "qwen3.5:2b-q4_K_M", "tied": ["qwen3.5:2b-q4_K_M"]},
        "residency": {"ok": True, "used_mib": 9000},
    }
    md = render_llm_report(results)
    assert "리포트: **qwen3.5:4b**" in md and "관문: **qwen3.5:2b-q4_K_M**" in md and "동시 상주: O" in md
```

- [ ] **Step 2: 실패 확인** — ImportError.

- [ ] **Step 3: 구현** — 게이트 함수(`report_bench_scoring.py`에 추가):

```python
REPORT_LIMITS = {"completion": 0.95, "verdict_match": 1.0, "fabrication": 0.05, "first_p95_ms": 5000, "total_p95_ms": 60000}
INTENT_LIMITS = {"schema_rate": 0.98, "fabrication_rate": 0.05, "p95_ms": 3000}


def report_gates(score: dict, latency: dict) -> dict[str, bool]:
    gates = {
        "completion": score["completion"] >= REPORT_LIMITS["completion"],
        "verdict_match": score["verdict_match"] >= REPORT_LIMITS["verdict_match"],
        "fabrication": score["fabrication"] <= REPORT_LIMITS["fabrication"],
        "rules": score["rule_violations"] == 0,
        "latency": latency["first_p95_ms"] <= REPORT_LIMITS["first_p95_ms"] and latency["total_p95_ms"] <= REPORT_LIMITS["total_p95_ms"],
    }
    return gates


def intent_gates(summary: dict) -> dict[str, bool]:
    return {
        "schema": summary["schema_rate"] >= INTENT_LIMITS["schema_rate"],
        "fabrication": summary["fabrication_rate"] <= INTENT_LIMITS["fabrication_rate"],
        "latency": summary["p95_ms"] <= INTENT_LIMITS["p95_ms"],
    }
```

`render_llm_report(results)`: 제목 `# LLM 모델 평가 결과 ({date})`, `## 리포트 작성` 표(모델·VRAM·품질·완주·판정 일치·지어내기·규칙·첫 글자 p95·완료 p95·게이트 O/X), `## 의도 관문` 표(모델·VRAM·동시 정답·지역·업종·예산·스키마·지어내기·p95·게이트), `## 판정` (`- 리포트: **{winner}** — 동률 {tied}`, `- 관문: **{winner}** — 동률 {tied}`, `- 동시 상주: O|X ({used_mib} MiB)`), `## 한계`(숫자 대조 오탐 가능, 판정자도 LLM, 시나리오 12건). 온라인 행은 표에 넣되 판정 대상에서 제외(`local: False`). 키가 없는 행은 `-`로. 리포트 표 끝에 `비고` 열 — `tools: False` 모델은 "도구 없음(참고 비교군, 라이선스 NC)", 온라인은 "온라인 비교군". `results["report"]["rows"][i]`에 `note` 키로 넘긴다(테스트의 최소 행처럼 `note`가 없으면 빈칸).

`benchmark_report.py`는 Interfaces대로 구현한다. `freeze`의 facts 수집기 구성은 `apps/agent/dependencies/analysis_dependencies.py`의 `build_analysis_use_case` 안 `ReportFactsCollector(...)` 생성과 **같은 인자**로 만든다(그 파일을 읽고 그대로 옮긴다 — 운영 파일은 수정하지 않는다). `run`의 도구 목록도 같은 파일의 `build_tools(region_facts, rag_search, FinanceFactsGateway(), budget)`와 같게 만든다.

- [ ] **Step 4: 통과 + 전체 회귀** — `$PY -m pytest tests/test_report_bench_cli.py tests/test_report_bench_scoring.py -q` PASS, `$PY -m pytest tests/ -q` 전부 PASS.
- [ ] **Step 5: 버전 로그** — `  - 리포트 벤치 CLI \`benchmark_report\`(freeze·run·score·judge-export·judge-import·vram·residency·evaluate): facts를 파일로 고정해 모든 모델에 같은 입력, 게이트·동률(VRAM 우선) 판정, 결과 보고서.`
- [ ] **Step 6: 커밋** — `backend v0.66.0: 리포트 벤치 CLI·판정·보고서`.

---

### Task 7: 평가 데이터 — 시나리오·facts 고정·관문 평가셋 (사람 검수 게이트)

코드 변경 없음(데이터). 

- [ ] **Step 1: 시나리오 12건** — DB에서 판정 4종을 고루 고른다:

```bash
$PY - <<'EOF'
from sqlalchemy import text
from core.matrix.grid_oracle_database_manager import session_scope
with session_scope() as s:
    for code in ("red", "orange", "clear", "insufficient"):
        rows = s.execute(text("select region_code, industry_id from region_industry_verdict where verdict_code=:c order by region_code, industry_id limit 40"), {"c": code}).all()
        print(code, rows[::10][:4])
EOF
```

(테이블·컬럼명이 다르면 `apps/verdict/adapter/outbound/orms/`에서 확인.) 판정별 2건(8건) + 데이터 일부 없음 2건(편의점·어린이집 등 스냅샷 업종) + 규칙·도구 2건(① 대출 질문 "은행 대출 받아서 차려도 될까요?" — 금융 규제·자금 도구, ② 외국인 상권 질문 "외국인이 많은 동네인데 괜찮을까요?" — 차별 표현 규칙)을 `data/eval/report_scenarios.jsonl`에 쓴다(`{"id":"s01","region_code":...,"industry_id":...,"question":... or null,"tags":["red"]}`).

- [ ] **Step 2: facts 고정** — `$PY -m apps.agent.adapter.inbound.cli.benchmark_report freeze` → 12개 파일. 각 파일의 `verdict.verdict_code`가 의도한 판정인지 확인.

- [ ] **Step 3: 관문 평가셋 초안** — `benchmark_intent masters --out <scratch>/masters.json` 후, 서브에이전트(질문 작성자)가 masters를 보고 §3-1 6유형 × 13~14건(총 약 80건)을 `data/eval/intent_evalset.jsonl`(status candidate)로 작성. 범위 밖·빠진 정보 유형은 정답 null을 정확히.
- [ ] **Step 4: 검수 시트** — `benchmark_intent sheet` → `data/eval/intent_evalset_review.md`. 다른 서브에이전트가 1차 판정(정답 줄 수정 포함)을 시트에 채운다.
- [ ] **Step 5: 커밋** — `git add -f data/eval/report_scenarios.jsonl data/eval/report_facts data/eval/intent_evalset.jsonl data/eval/intent_evalset_review.md` → `data: LLM 평가 시나리오·facts 고정·관문 평가셋(1차 판정)`.
- [ ] **Step 6: 멈추고 사용자 검수 요청** — 시트 검수 후 `benchmark_intent apply` → 커밋 `data: 관문 평가셋 검수 반영`. **사용자 응답 전 Task 8 금지.**

---

### Task 8: 실행·판정·보고서

- [ ] **Step 1: 0단계 프로토콜 호환** — 로컬 모델마다 관문 1건(`run --model X --repeat 1` 후 결과 1줄 확인: null 출력 가능 여부, 스키마 통과), 리포트 1건(`run --model X --repeat 1`을 시나리오 1개로 — `--only s01` 옵션이 없으면 결과 첫 줄만 확인)으로 `think:false`·도구·JSON format이 동작하는지 본다. 응답에 thinking 내용이 섞이면(`message.thinking` 존재) 기록한다. 문제 모델은 기록하고 진행(게이트에서 탈락).
- [ ] **Step 2: VRAM** — `benchmark_report vram`.
- [ ] **Step 3: 관문 본실험** — 7개 모델 `benchmark_intent run --model X --repeat 3` → `benchmark_intent evaluate`. GPU 모델은 하나씩 순서대로(동시 실행 금지).
- [ ] **Step 4: 리포트 본실험** — 7개 모델 `benchmark_report run --model X --repeat 3` → `benchmark_report score`. 한 모델당 12 × 3 = 36회.
- [ ] **Step 5: 블라인드 판정** — `judge-export` → 시나리오별 판정 서브에이전트(12개, 모델명 모름)가 기준(근거 충실도: facts에 있는 사실만 쓰고 해석이 맞는가 1~5 / 자연스러움: 한국어 문장·구성 1~5 / 응답 규칙 4종 위반 목록)으로 채점해 json 작성 → 합쳐 `judge-import`.
- [ ] **Step 6: 판정·상주** — `evaluate` → 승자 조합으로 `residency --report-model R --intent-model I` → `evaluate` 재실행.
- [ ] **Step 7: 보고서 보강·문서** — `report.md`에 비용 절(gemini-2.5-flash 공식 가격표, 확인일·URL, 토큰 실측), 0단계 호환 메모, 라이선스(kanana 모델 카드 확인)를 손으로 추가. `docs/STATUS.md`에 LLM 평가 항목, spec §9 해소 표시, ver log에 결과 줄.
- [ ] **Step 8: 커밋** — `git add -f data/eval/results/llm-benchmark-*/` + 문서 → `backend v0.66.0: LLM 모델 평가 결과`. 푸시 금지.
