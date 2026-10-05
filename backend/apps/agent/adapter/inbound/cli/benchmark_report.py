"""리포트 작성 LLM 평가 CLI — 로컬 후보와 Gemini를 같은 고정 facts로 재 모델을 고른다 (Driving Adapter).

운영 경로는 건드리지 않는다. facts를 한 번 모아 파일로 고정(freeze)하고, 모델마다 같은 facts로
AnalysisInteractor를 돌려 시나리오·회차 단위 jsonl로 캐시한 뒤(run) 채점·판정한다.

실행 순서 (backend/에서):
  python -m apps.agent.adapter.inbound.cli.benchmark_report freeze
  python -m apps.agent.adapter.inbound.cli.benchmark_report run --model qwen3.5:4b [--repeat 3]
  python -m apps.agent.adapter.inbound.cli.benchmark_report score
  python -m apps.agent.adapter.inbound.cli.benchmark_report judge-export
  python -m apps.agent.adapter.inbound.cli.benchmark_report judge-import --file PATH
  python -m apps.agent.adapter.inbound.cli.benchmark_report vram
  python -m apps.agent.adapter.inbound.cli.benchmark_report residency --report-model R --intent-model I
  python -m apps.agent.adapter.inbound.cli.benchmark_report evaluate [--out-dir NAME]

같은 날 재평가는 `--cache-tag NAME`(run·score·judge-*·evaluate 공통)으로 캐시를 `report-NAME/`·`judge-NAME/`에
나누고, `evaluate --out-dir NAME`으로 기존 결과 폴더를 덮어쓰지 않게 한다.
"""

import argparse
import json
import subprocess
import time
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from statistics import mean

import httpx

from apps.agent.adapter.inbound.cli.agent_eval_scoring import check_rule_keywords
from apps.agent.adapter.inbound.cli.report_bench_scoring import (
    intent_gates,
    classify_violation,
    judge_packets,
    llm_sections,
    mask_model_names,
    render_llm_report,
    report_gates,
    unmatched_numbers,
    verdict_matches,
    verdict_states_grade,
)
from apps.agent.adapter.outbound.gateways.event_analog_facts_gateway import EventAnalogFactsGateway
from apps.agent.adapter.outbound.gateways.finance_facts_gateway import FinanceFactsGateway
from apps.agent.adapter.outbound.gateways.funding_facts_gateway import FundingFactsGateway
from apps.agent.adapter.outbound.gateways.region_facts_gateway import RegionFactsGateway
from apps.agent.adapter.outbound.gateways.verdict_facts_gateway import VerdictFactsGateway
from apps.agent.adapter.outbound.llm.gemini_llm_adapter import GeminiLLMAdapter
from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter
from apps.agent.app.ports.output.agent_port import LLMGatewayPort
from apps.agent.app.use_cases.agent_tools import build_tools
from apps.agent.app.use_cases.analysis_interactor import (
    _SECTIONS,
    SYSTEM_PROMPT,
    AnalysisInteractor,
    _fallback_section,
    guarded_fallback_section,
)
from apps.agent.app.use_cases.report_facts import ReportFactsCollector
from apps.agent.domain.entities.agent_event_entity import AgentEvent
from apps.agent.domain.services.section_stream import concat_sections
from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case
from core.matrix.grid_benchmark_manager import paired_bootstrap_ci, percentile, pick_winner, resident_models
from core.matrix.grid_keymaker_secret_manager import get_settings

# apps/agent/adapter/inbound/cli/benchmark_report.py → parents[6] == 리포지토리 루트
_REPO_ROOT = Path(__file__).resolve().parents[6]
_SCENARIOS = _REPO_ROOT / "data/eval/report_scenarios.jsonl"
_FACTS_DIR = _REPO_ROOT / "data/eval/report_facts"
_CACHE = _REPO_ROOT / "data/eval/cache/llm-benchmark"
_RUNS = _CACHE / "report"
_JUDGE = _CACHE / "judge"
_INTENT_SUMMARY = _CACHE / "intent_summary.json"
_VRAM = _CACHE / "vram.json"
_RESIDENCY = _CACHE / "residency.json"
_RESULTS_ROOT = _REPO_ROOT / "data/eval/results"

_JUDGE_SEED = 0
_TEMPERATURE = 0.3  # 운영 리포트 호출과 같게
# 첫 턴 프롬프트 실측 최대 14,143토큰(도구 포함, 2026-10-05) + 출력·도구 턴 여유 — Ollama 기본 컨텍스트는 ~2k에서 잘린다
BENCH_NUM_CTX = 32768
_LOCAL_OPTIONS = {"num_ctx": BENCH_NUM_CTX}  # vram·residency도 같은 옵션으로 올려야 VRAM이 실사용을 반영한다
_OLLAMA_KEEP_ALIVE = "10m"
_MIB = 1024 * 1024
_BGE = "bge-m3"
_INTENT_ONLY_LOCAL = ("qwen3.5:2b-q4_K_M",)  # 관문 전용 후보 — VRAM만 잰다
_ONLINE = "gemini-2.5-flash"
# Gemini 2.5 Flash 유료 티어 단가(1M 토큰당, 출력은 생각 토큰 포함) — 바뀌면 확인일·출처와 함께 고친다
_GEMINI_PRICE = {"input": 0.30, "output": 2.50}
_GEMINI_PRICE_CHECKED = "2026-10-05"
_GEMINI_PRICE_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"


@dataclass(frozen=True)
class ReportModel:
    name: str
    llm: Callable[[], LLMGatewayPort]
    tools: bool
    local: bool


def _ollama(name: str, think: bool | None, tools: bool = True) -> ReportModel:
    return ReportModel(name, lambda: OllamaLLMAdapter(model=name, think=think, temperature=_TEMPERATURE, num_ctx=BENCH_NUM_CTX), tools, True)


REPORT_MODELS: dict[str, ReportModel] = {m.name: m for m in (
    _ollama("gemma4:12b", False),
    _ollama("gemma4:e4b", False),
    _ollama("kanana1.5:8b-q4km", None),
    _ollama("qwen3.5:9b", False),
    _ollama("qwen3.5:4b", False),
    # Ollama 템플릿에 도구 처리가 없다 — 도구 없이 돌리는 참고 비교군(라이선스 NC)
    _ollama("exaone3.5:7.8b", None, tools=False),
    ReportModel(_ONLINE, lambda: GeminiLLMAdapter(model=_ONLINE), True, False),
)}
_NOTES = {False: "온라인 비교군"}  # local 여부별 비고
_NO_TOOL_NOTE = "도구 없음(참고 비교군, 라이선스 NC)"


class FrozenFacts:
    """얼려 둔 facts — ReportFactsCollector.collect를 대신해 AnalysisInteractor의 facts 자리에 들어간다."""

    def __init__(self, facts_by_key: dict[tuple[str, str], dict]):
        self._facts = facts_by_key

    def collect(self, region: str, industry: str, budget: int | None = None, question: str | None = None) -> dict:
        return self._facts[(region, industry)]


# ── 입출력 ─────────────────────────────────────────────────

def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_json(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cache_dirs(tag: str | None) -> tuple[Path, Path]:
    """(리포트 회차 캐시, 판정 캐시) — 태그가 있으면 `report-<tag>/`·`judge-<tag>/`로 나눈다."""
    suffix = f"-{tag}" if tag else ""
    return _CACHE / f"report{suffix}", _CACHE / f"judge{suffix}"


def _safe(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


def _run_path(model: str) -> Path:
    return _RUNS / f"{_safe(model)}.jsonl"


def _score_path(model: str) -> Path:
    return _RUNS / f"score_{_safe(model)}.json"


def _scenarios() -> list[dict]:
    return _read_jsonl(_SCENARIOS)


def _facts_of(scenario_id: str) -> dict:
    return json.loads((_FACTS_DIR / f"{scenario_id}.json").read_text(encoding="utf-8"))


# ── 순수 로직 ──────────────────────────────────────────────

def collect_run(events: Iterable[AgentEvent], clock: Callable[[], float] = time.perf_counter) -> dict:
    """이벤트 스트림 → {first_ms, total_ms, sections, tool_calls}.

    시계는 facts 이벤트 수신을 0으로, 첫 report_delta까지(first_ms)·report_done까지(total_ms)를 잰다.
    """
    start: float | None = None
    first_ms = total_ms = None
    sections: dict[str, str] = {}
    tool_calls: list[dict] = []
    for event in events:
        if event.type == "facts":
            start = clock()
        elif event.type == "tool_call":
            tool_calls.append(event.payload)
        elif event.type == "report_delta":
            if first_ms is None and start is not None:
                first_ms = (clock() - start) * 1000
            section = event.payload["section"]
            sections[section] = sections.get(section, "") + event.payload["markdown"]
        elif event.type == "report_done" and start is not None:
            total_ms = (clock() - start) * 1000
    return {"first_ms": first_ms, "total_ms": total_ms, "sections": sections, "tool_calls": tool_calls}


def _report_text(sections: dict[str, str]) -> str:
    return concat_sections(sections.items(), order=[name for name, _ in _SECTIONS])


def _written_sections(sections: dict[str, str], facts: dict) -> set[str]:
    """LLM이 쓴 절 — 맨 폴백(v0.67.0 이전 캐시)과 가드를 씌운 폴백(이후) 어느 쪽과도 다른 절."""
    plain = {name: _fallback_section(name, title, facts) for name, title in _SECTIONS}
    guarded = {name: guarded_fallback_section(name, title, facts) for name, title in _SECTIONS}
    return llm_sections(sections, plain) & llm_sections(sections, guarded)


def _tool_spec_text() -> str:
    """모델에 노출되는 도구 정의(이름·설명·스키마)를 한 덩어리 글로 — 모델이 여기서 가져온 숫자는 지어낸 게 아니다."""
    specs = [t.spec for t in build_tools(None, None, None, None)]  # 정의만 읽는다 — 게이트웨이는 호출되지 않음
    return json.dumps(
        [{"name": s.name, "description": s.description, "input_schema": s.input_schema} for s in specs],
        ensure_ascii=False,
    )


def score_run(record: dict, facts: dict, question: str | None = None, tools_given: bool = True) -> dict:
    """한 회차 채점 — 완주(6절 모두 LLM 작성 & 오류 없음)·판정 일치·지어낸 숫자·규칙 키워드.

    숫자 근거는 facts뿐 아니라 사용자 질문·도구 결과(자금 계산·RAG 재검색)·시스템 프롬프트·
    모델이 받은 도구 설명이다(도구 없는 모델은 도구 설명 제외).
    판정 일치는 판정 절을 LLM이 썼을 때만 본다(폴백 문구는 facts로 쓴 것이라 모델 평가가 아니다).
    """
    sections = record["sections"]
    written = _written_sections(sections, facts)
    text = _report_text(sections)
    grounding = {
        "facts": facts, "question": question, "tool_results": record.get("tool_results", []),
        "system_prompt": SYSTEM_PROMPT, "tool_specs": _tool_spec_text() if tools_given else "",
    }
    return {
        "complete": not record.get("error") and written >= {name for name, _ in _SECTIONS},
        "verdict_ok": "verdict" in written and verdict_matches(sections["verdict"], facts.get("verdict", {})),
        "verdict_graded": "verdict" in written and verdict_states_grade(sections["verdict"]),
        "unmatched": unmatched_numbers(text, grounding),
        "rule_hits": check_rule_keywords(text),
    }


def _p95(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return percentile(clean, 95) if clean else None


# ── 명령 ───────────────────────────────────────────────────

def _collector() -> tuple[ReportFactsCollector, RegionFactsGateway, object]:
    """analysis_dependencies.build_analysis_use_case와 같은 생성자 인자."""
    region_facts = RegionFactsGateway()
    rag_search = get_rag_search_use_case()
    collector = ReportFactsCollector(
        region_facts=region_facts,
        verdict_facts=VerdictFactsGateway(),
        funding_facts=FundingFactsGateway(),
        news_search=rag_search,
        analog_facts=EventAnalogFactsGateway(),
    )
    return collector, region_facts, rag_search


def _cmd_freeze(args: argparse.Namespace) -> None:
    collector, _, _ = _collector()
    for s in _scenarios():
        path = _FACTS_DIR / f"{s['id']}.json"
        if path.exists() and not args.force:
            continue
        _write_json(path, collector.collect(s["region_code"], s["industry_id"], None, s["question"]))
        print(f"freeze: {s['id']} → {path}", flush=True)


def _ollama_post(path: str, body: dict) -> dict:
    response = httpx.post(f"{get_settings().ollama_base_url}{path}", json=body, timeout=300.0)
    response.raise_for_status()
    return response.json()


def _ollama_ps() -> list[dict]:
    response = httpx.get(f"{get_settings().ollama_base_url}/api/ps", timeout=30.0)
    response.raise_for_status()
    return response.json().get("models", [])


def _load(model: str, keep_alive: str | int = _OLLAMA_KEEP_ALIVE, options: dict | None = None) -> None:
    """빈 프롬프트로 모델을 올린다(keep_alive 0이면 내린다). 로컬 LLM은 벤치와 같은 options로 올린다."""
    body = {"model": model, "prompt": "", "keep_alive": keep_alive, "stream": False}
    if options:
        body["options"] = options
    _ollama_post("/api/generate", body)


def _unload_all() -> None:
    for m in _ollama_ps():
        _load(m["name"], 0)


def _recording(run: Callable[[dict], str], sink: list[str]) -> Callable[[dict], str]:
    """도구 실행을 감싸 결과 문자열을 sink에 남긴다."""
    def wrapped(arguments: dict) -> str:
        result = run(arguments)
        sink.append(result)
        return result
    return wrapped


def _cmd_run(args: argparse.Namespace) -> None:
    model = REPORT_MODELS[args.model]
    llm = model.llm()
    if model.local:
        _load(model.name, options=_LOCAL_OPTIONS)  # 워밍업 — 모델 로드 시간은 지연에서 제외
    path = _run_path(model.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["id"], r["rep"]) for r in _read_jsonl(path)}
    _, region_facts, rag_search = _collector()
    base_tools = build_tools(region_facts, rag_search, FinanceFactsGateway(), None) if model.tools else []
    for rep in range(args.repeat):
        for s in _scenarios():
            if (s["id"], rep) in done:
                continue
            frozen = FrozenFacts({(s["region_code"], s["industry_id"]): _facts_of(s["id"])})
            tool_results: list[str] = []  # 리포트 숫자의 근거 — 도구가 돌려준 결과를 그대로 모은다
            tools = [replace(t, run=_recording(t.run, tool_results)) for t in base_tools]
            interactor = AnalysisInteractor(llm=llm, tools=tools, facts=frozen)
            error = None
            events: list[AgentEvent] = []

            def stream():
                for event in interactor.run(s["region_code"], s["industry_id"], s["question"]):
                    events.append(event)
                    yield event

            try:
                got = collect_run(stream())
            except Exception as exc:  # 모델·전송 실패도 한 회차의 결과다 — 완주 게이트가 걸러낸다
                error = f"{type(exc).__name__}: {exc}"
                got = {**collect_run(events), "first_ms": None, "total_ms": None}  # 중단된 회차의 시간은 의미 없다
            usage = interactor.last_usage
            if not error and usage.output_tokens == 0 and not _written_sections(got["sections"], _facts_of(s["id"])):
                error = "no_llm_output"
                print(f"run: 경고 {model.name} {s['id']} rep{rep} LLM 출력 없음", flush=True)
            row = {"id": s["id"], "rep": rep, **got, "error": error, "tool_results": tool_results,
                   "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}}
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"run: {model.name} {s['id']} rep{rep} total={got['total_ms']} error={error}", flush=True)


def _cmd_score(args: argparse.Namespace) -> None:
    scenarios = _scenarios()
    facts = {s["id"]: _facts_of(s["id"]) for s in scenarios}
    questions = {s["id"]: s["question"] for s in scenarios}
    for name in REPORT_MODELS:
        records = _read_jsonl(_run_path(name))
        if not records:
            continue
        runs = [{**r, **score_run(r, facts[r["id"]], questions[r["id"]], REPORT_MODELS[name].tools)} for r in records]
        n = len(runs)
        summary = {
            "model": name, "n": n,
            "completion": sum(r["complete"] for r in runs) / n,
            "verdict_match": sum(r["verdict_ok"] for r in runs) / n,
            # 참고 — LLM이 쓴 판정 절에 등급 말이 없는 회차 수(모순은 아니지만 등급을 생략)
            "verdict_no_grade": sum("verdict" in _written_sections(r["sections"], facts[r["id"]])
                                    and not r["verdict_graded"] for r in runs),
            "fabrication": sum(bool(r["unmatched"]) for r in runs) / n,
            "rule_violations_keyword": sum(len(r["rule_hits"]) for r in runs),
            "first_p95_ms": _p95([r["first_ms"] for r in runs]),
            "total_p95_ms": _p95([r["total_ms"] for r in runs]),
            "runs": [{k: r[k] for k in ("id", "rep", "complete", "verdict_ok", "unmatched", "rule_hits",
                                        "first_ms", "total_ms", "error")} for r in runs],
        }
        _write_json(_score_path(name), summary)
        print(f"score: {name} → {_score_path(name)}", flush=True)


def _first_rep_reports() -> dict[str, dict[str, str]]:
    """{시나리오 id: {모델: 1회차 본문}} — 본문의 모델명은 가린다."""
    out: dict[str, dict[str, str]] = {}
    for name in REPORT_MODELS:
        for r in _read_jsonl(_run_path(name)):
            if r["rep"] == 0 and r["sections"]:
                out.setdefault(r["id"], {})[name] = mask_model_names(_report_text(r["sections"]))
    return out


def _cmd_judge_export(args: argparse.Namespace) -> None:
    _JUDGE.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, dict[str, str]] = {}
    for sid, reports in _first_rep_reports().items():
        packet, mapping[sid] = judge_packets(sid, _facts_of(sid), reports, _JUDGE_SEED)
        (_JUDGE / f"packet_{sid}.md").write_text(packet, encoding="utf-8")
    _write_json(_JUDGE / "mapping.json", mapping)
    print(f"judge-export: {len(mapping)}개 시나리오 → {_JUDGE}", flush=True)


def _cmd_judge_import(args: argparse.Namespace) -> None:
    mapping = _read_json(_JUDGE / "mapping.json")
    judged = json.loads(Path(args.file).read_text(encoding="utf-8"))
    scores: dict[str, dict[str, dict]] = _read_json(_JUDGE / "scores.json", {})  # 이어 넣기 — 덮어쓰지 않는다
    for sid, by_blind in judged.items():
        for blind, score in by_blind.items():
            scores.setdefault(mapping[sid][blind], {})[sid] = score
    _write_json(_JUDGE / "scores.json", scores)
    print(f"judge-import: {len(scores)}개 모델 → {_JUDGE / 'scores.json'}", flush=True)


def _gpu_used_mib() -> int | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, check=True).stdout
        return int(out.strip().splitlines()[0])
    except (OSError, subprocess.CalledProcessError, ValueError, IndexError):
        return None


def _entry(ps: list[dict], model: str) -> dict | None:
    return next((m for m in ps if m["name"] in (model, f"{model}:latest")), None)


def _cmd_vram(args: argparse.Namespace) -> None:
    models = [n for n, m in REPORT_MODELS.items() if m.local] + list(_INTENT_ONLY_LOCAL)
    vram: dict[str, float] = {}
    for model in models:
        try:
            _unload_all()
            _load(model, options=_LOCAL_OPTIONS)
            entry = _entry(_ollama_ps(), model)
        except httpx.HTTPError as exc:
            print(f"vram: {model} 로드 실패 — 건너뜀 ({exc})", flush=True)
            continue
        if entry is None:
            print(f"vram: {model} /api/ps 에 없음 — 건너뜀", flush=True)
            continue
        vram[model] = entry["size_vram"] / _MIB
        _write_json(_VRAM, vram)  # 모델마다 저장 — 중간에 끊겨도 잰 값은 남는다
        print(f"vram: {model} {vram[model]:.0f} MiB", flush=True)
    _unload_all()


def _cmd_residency(args: argparse.Namespace) -> None:
    _unload_all()
    wanted = list(dict.fromkeys([args.report_model, args.intent_model, _BGE]))  # 같은 모델이면 한 번만
    for model in wanted:
        if model == _BGE:
            _ollama_post("/api/embed", {"model": _BGE, "input": "ping", "keep_alive": _OLLAMA_KEEP_ALIVE})
        else:
            _load(model, options=_LOCAL_OPTIONS)
    ps = _ollama_ps()
    present = resident_models({"models": ps})
    sizes = {m: {"size_mib": e["size"] / _MIB, "vram_mib": e["size_vram"] / _MIB}
             for m in wanted if (e := _entry(ps, m))}
    # 셋 다 올라 있고, 각각 전부 GPU에 있어야 한다(부분 CPU 오프로드는 상주 실패)
    ok = all((m in present or f"{m}:latest" in present) and e["size_vram"] == e["size"]
             for m in wanted if (e := _entry(ps, m)) is not None) and len(sizes) == len(wanted)
    result = {"report_model": args.report_model, "intent_model": args.intent_model, "same_model": len(wanted) == 2,
              "ok": ok, "used_mib": _gpu_used_mib(), "sizes": sizes}
    _write_json(_RESIDENCY, result)
    print(f"residency: ok={ok} {result['used_mib']} MiB", flush=True)


def _exclusion(local: bool, gates: dict[str, bool], judged: int | None, total: int, vram: float | None) -> str | None:
    """판정 대상에서 빠진 이유 — 대상이면 None. judged가 None이면 판정 개수를 따지지 않는다(관문)."""
    if not local:
        return "온라인 비교군(판정 대상 아님)"
    failed = [k for k, ok in gates.items() if not ok and k != "all"]
    if failed:
        return "게이트 탈락: " + ", ".join(failed)
    if judged is not None and judged < total:
        return f"판정 미완료 {judged}/{total}"
    if vram is None:
        return "VRAM 미측정"
    return None


def build_report_block(scores: dict[str, dict], judge: dict, vram: dict, scenario_ids: list[str]) -> dict:
    """리포트 역할 판정 — 게이트 통과 & 로컬 & 판정 완료 & VRAM 측정된 모델 중 pick_winner."""
    rows, per_row, p95_by, eligible = [], {}, {}, []
    ref_quality, ref_p95, ref_violations = {}, {}, {}  # 참고 순위 — 게이트와 무관하게 로컬 전부
    for name, score in scores.items():
        model = REPORT_MODELS[name]
        mine = judge.get(name, {})
        judged = sum(sid in mine for sid in scenario_ids)
        quality = [mine[sid]["faithfulness"] + mine[sid]["fluency"] for sid in scenario_ids] \
            if judged == len(scenario_ids) else []
        judge_violations = sum(len(mine[sid].get("violations", [])) for sid in scenario_ids if sid in mine)
        merged = {**score, "rule_violations": score["rule_violations_keyword"] + judge_violations}
        latency = {k: score[k] if score[k] is not None else float("inf") for k in ("first_p95_ms", "total_p95_ms")}
        gates = report_gates(merged, latency)
        gates["all"] = all(gates.values())
        excluded = _exclusion(model.local, gates, judged, len(scenario_ids), vram.get(name))
        note = _NOTES.get(model.local, "") or ("" if model.tools else _NO_TOOL_NOTE)
        rows.append({"model": name, "vram_mib": vram.get(name), "quality": mean(quality) if quality else None,
                     "n": score.get("n"), "completion": score["completion"], "verdict_match": score["verdict_match"],
                     "verdict_no_grade": score.get("verdict_no_grade"),
                     "fabrication": score["fabrication"], "rule_violations": merged["rule_violations"],
                     "first_p95_ms": score["first_p95_ms"], "total_p95_ms": score["total_p95_ms"],
                     "gates": gates, "note": note, "local": model.local, "excluded": excluded})
        if excluded is None:
            eligible.append(name)
            per_row[name], p95_by[name] = quality, score["total_p95_ms"]
        if model.local and quality:
            ref_quality[name], ref_p95[name] = quality, score["total_p95_ms"]
        if mine:  # 위반 유형은 온라인 비교군도 함께 센다
            ref_violations[name] = dict(Counter(classify_violation(v) for sid in scenario_ids if sid in mine
                                                for v in mine[sid].get("violations", [])))
    block = _pick(rows, per_row, per_row, {m: vram[m] for m in eligible}, p95_by, eligible)
    block["reference"] = {**_reference(rows, ref_quality, ref_p95, vram, "quality"),
                          "scenario_ids": scenario_ids, "per_scenario": ref_quality, "violations": ref_violations}
    return block


def _reference(rows: list[dict], score_by: dict, p95_by: dict, vram: dict, metric: str) -> dict:
    """참고 순위 — 게이트와 무관하게 받은 로컬 모델 전부를 평균 점수로 줄 세운다.

    1위(best) 대비 문항별 paired bootstrap 구간(ci_vs_best: 평균 차, 하한, 상한)을 남기고,
    VRAM을 잰 모델끼리 pick_winner(동률이면 VRAM 작은 쪽).
    """
    by_name = {r["model"]: r for r in rows}
    order = sorted(score_by, key=lambda m: -mean(score_by[m]))
    ranking = [{"model": m, metric: mean(score_by[m]), "vram_mib": vram.get(m),
                "failed": [k for k, ok in by_name[m]["gates"].items() if not ok and k != "all"]} for m in order]
    best = order[0] if order else None
    ci = {m: list(paired_bootstrap_ci(score_by[best], score_by[m])) for m in order[1:]}
    measured = [m for m in order if m in vram]
    winner, tied = pick_winner(score_by, vram, p95_by, measured) if measured else (None, [])
    return {"ranking": ranking, "best": best, "ci_vs_best": ci, "winner": winner, "tied": tied}


def _report_block(scenario_ids: list[str]) -> dict:
    scores = {name: score for name in REPORT_MODELS if (score := _read_json(_score_path(name))) is not None}
    return build_report_block(scores, _read_json(_JUDGE / "scores.json", {}), _read_json(_VRAM, {}), scenario_ids)


def _pick(rows: list[dict], per_row: dict, score_by: dict, vram_by: dict, p95_by: dict, eligible: list[str]) -> dict:
    block = {"rows": rows, "per_row": per_row, "winner": None, "tied": []}
    if eligible:
        block["winner"], block["tied"] = pick_winner(score_by, vram_by, p95_by, eligible)
        best = max(eligible, key=lambda m: mean(score_by[m]))
        block["ci_vs_best"] = {m: paired_bootstrap_ci(score_by[best], score_by[m]) for m in eligible if m != best}
    return block


def _intent_block() -> dict:
    return build_intent_block(_read_json(_INTENT_SUMMARY, {}), _read_json(_VRAM, {}))


def build_intent_block(summary: dict[str, dict], vram: dict) -> dict:
    """관문 역할 판정 + 참고 순위(게이트와 무관하게 로컬 전부, 동시 정답 기준)."""
    rows, per_row, vram_by, p95_by, eligible = [], {}, {}, {}, []
    ref_both, ref_p95 = {}, {}
    for name, s in summary.items():
        gates = intent_gates(s)
        gates["all"] = all(gates.values())
        local = name in REPORT_MODELS and REPORT_MODELS[name].local or name in _INTENT_ONLY_LOCAL
        rows.append({"model": name, "vram_mib": vram.get(name), "both": s["both"], "region": s["region"],
                     "industry": s["industry"], "budget": s["budget"], "schema_rate": s["schema_rate"],
                     "fabrication_rate": s["fabrication_rate"], "fabrication_any_null": s.get("fabrication_any_null"),
                     "p95_ms": s["p95_ms"], "gates": gates,
                     "note": "" if local else "온라인 비교군", "local": local,
                     "excluded": _exclusion(local, gates, None, 0, vram.get(name))})
        if gates["all"] and local and name in vram:
            eligible.append(name)
            per_row[name], vram_by[name], p95_by[name] = s["per_row_both"], vram[name], s["p95_ms"]
        if local:
            ref_both[name], ref_p95[name] = s["per_row_both"], s["p95_ms"]
    block = _pick(rows, per_row, per_row, vram_by, p95_by, eligible)
    block["reference"] = {**_reference(rows, ref_both, ref_p95, vram, "both"),
                          "ids": next(iter(summary.values()))["ids"] if summary else [],
                          "per_row_both": {name: s["per_row_both"] for name, s in summary.items()}}
    return block


def gemini_cost(records: list[dict]) -> dict:
    """Gemini 리포트 캐시의 usage 평균 → 리포트 1건 토큰·비용(USD)."""
    n = len(records)
    mean_in = sum(r["usage"]["input_tokens"] for r in records) / n
    mean_out = sum(r["usage"]["output_tokens"] for r in records) / n
    usd = (mean_in * _GEMINI_PRICE["input"] + mean_out * _GEMINI_PRICE["output"]) / 1_000_000
    return {"model": _ONLINE, "n": n, "mean_input_tokens": mean_in, "mean_output_tokens": mean_out,
            "usd_per_report": usd, "price_per_1m_usd": _GEMINI_PRICE,
            "checked": _GEMINI_PRICE_CHECKED, "source": _GEMINI_PRICE_SOURCE}


def _cmd_evaluate(args: argparse.Namespace) -> None:
    ids = [s["id"] for s in _scenarios()]
    gemini_runs = _read_jsonl(_run_path(_ONLINE))
    results = {"date": date.today().isoformat(), "report": _report_block(ids), "intent": _intent_block(),
               "residency": _read_json(_RESIDENCY), "cost": gemini_cost(gemini_runs) if gemini_runs else None}
    out = _RESULTS_ROOT / (args.out_dir or f"llm-benchmark-{results['date']}")
    _write_json(out / "results.json", results)
    (out / "report.md").write_text(render_llm_report(results), encoding="utf-8")
    print(f"evaluate: 리포트 승자 {results['report']['winner']} · 관문 승자 {results['intent']['winner']} → {out}",
          flush=True)


_COMMANDS: dict[str, Callable] = {
    "freeze": _cmd_freeze, "run": _cmd_run, "score": _cmd_score, "judge-export": _cmd_judge_export,
    "judge-import": _cmd_judge_import, "vram": _cmd_vram, "residency": _cmd_residency, "evaluate": _cmd_evaluate,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=list(_COMMANDS))
    parser.add_argument("--model", choices=list(REPORT_MODELS))
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--file", default=None, help="judge-import: 판정 json 경로")
    parser.add_argument("--report-model", default=None)
    parser.add_argument("--intent-model", default=None)
    parser.add_argument("--force", action="store_true", help="freeze: 기존 facts 덮어쓰기")
    parser.add_argument("--out-dir", default=None, help="evaluate: 결과 폴더 이름(기본 llm-benchmark-YYYY-MM-DD)")
    parser.add_argument("--cache-tag", default=None, help="run·score·judge-*·evaluate: 캐시를 report-<tag>/·judge-<tag>/로 분리")
    args = parser.parse_args()
    global _RUNS, _JUDGE  # 명령 함수들이 모듈 경로를 읽는다 — 태그는 실행 시작에 한 번만 바꾼다
    _RUNS, _JUDGE = cache_dirs(args.cache_tag)
    _COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
