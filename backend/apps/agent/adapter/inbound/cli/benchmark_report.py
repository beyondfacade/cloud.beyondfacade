"""리포트 작성 LLM 평가 CLI — 로컬 후보와 Gemini를 같은 고정 facts로 재 모델을 고른다 (Driving Adapter).

운영 경로는 건드리지 않는다. facts를 한 번 모아 파일로 고정(freeze)하고, 모델마다 같은 facts로
AnalysisInteractor를 돌려 시나리오·회차 단위 jsonl로 캐시한 뒤(run) 채점·판정한다.

실행 순서 (backend/에서):
  python -m apps.agent.adapter.inbound.cli.benchmark_report freeze
  python -m apps.agent.adapter.inbound.cli.benchmark_report sections-check
  python -m apps.agent.adapter.inbound.cli.benchmark_report run --model qwen3.5:4b [--repeat 3]
  python -m apps.agent.adapter.inbound.cli.benchmark_report score
  python -m apps.agent.adapter.inbound.cli.benchmark_report judge-export
  python -m apps.agent.adapter.inbound.cli.benchmark_report judge-import --file PATH
  python -m apps.agent.adapter.inbound.cli.benchmark_report judge-export --compare-tag OTHER --models a,b [--cache-tag T]
  python -m apps.agent.adapter.inbound.cli.benchmark_report judge-import --compare-tag OTHER --file PATH [--cache-tag T]
  python -m apps.agent.adapter.inbound.cli.benchmark_report judge-compare --compare-tag OTHER [--cache-tag T]
  python -m apps.agent.adapter.inbound.cli.benchmark_report vram
  python -m apps.agent.adapter.inbound.cli.benchmark_report residency --report-model R --intent-model I
  python -m apps.agent.adapter.inbound.cli.benchmark_report evaluate [--out-dir NAME]

150건 평가셋은 freeze·sections-check·run·score·judge-export에 `--scenario-set 150`을 붙인다(시나리오·facts 경로만 바뀐다).

v0.68.0(리포트 코드 우선 구조)부터 6개 절은 코드가 facts로 쓴다 — `sections-check`가 모델 호출 없이 범위 없는 숫자·
이유 빠진 자료 부족 자리를 센다. LLM은 맨 위 해석(answer) 한 단락만 쓰므로 `score`·`judge-export`는 그 단락만 본다.
같은 날 재평가는 `--cache-tag NAME`(run·score·judge-*·evaluate 공통)으로 캐시를 `report-NAME/`·`judge-NAME/`에
나누고, `evaluate --out-dir NAME`으로 기존 결과 폴더를 덮어쓰지 않게 한다.
"""

import argparse
import json
import random
import re
import subprocess
import time
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean

import httpx

from apps.agent.adapter.inbound.cli.agent_eval_scoring import check_rule_keywords
from apps.agent.adapter.inbound.cli.report_bench_scoring import (
    SCOPE_WORDS,
    answer_packets,
    intent_gates,
    classify_violation,
    judge_packets,
    mask_model_names,
    missing_data_gaps,
    render_llm_report,
    report_gates,
    unscoped_number_lines,
)
from apps.agent.adapter.outbound.gateways.event_analog_facts_gateway import EventAnalogFactsGateway
from apps.agent.adapter.outbound.gateways.funding_facts_gateway import FundingFactsGateway
from apps.agent.adapter.outbound.gateways.region_facts_gateway import RegionFactsGateway
from apps.agent.adapter.outbound.gateways.verdict_facts_gateway import VerdictFactsGateway
from apps.agent.adapter.outbound.llm.gemini_llm_adapter import GeminiLLMAdapter
from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter
from apps.agent.app.ports.output.agent_port import LLMGatewayPort
from apps.agent.app.use_cases.analysis_interactor import ANSWER_FALLBACK, AnalysisInteractor, region_names
from apps.agent.app.use_cases.report_facts import ReportFactsCollector
from apps.agent.domain.entities.agent_event_entity import AgentEvent
from apps.agent.domain.services.report_guards import blank_names, contradicts_verdict
from apps.agent.domain.services.report_sampling import REPORT_SEED, REPORT_TEMPERATURE
from apps.agent.domain.services.report_sections import build_sections, scarce_lead, scarcity
from apps.agent.domain.services.section_stream import concat_sections
from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case
from core.matrix.grid_benchmark_manager import paired_bootstrap_ci, percentile, pick_winner, resident_models
from core.matrix.grid_keymaker_secret_manager import get_settings

# apps/agent/adapter/inbound/cli/benchmark_report.py → parents[6] == 리포지토리 루트
_REPO_ROOT = Path(__file__).resolve().parents[6]
# --scenario-set → (시나리오 파일, facts 폴더). 150은 사람 판정용 평가셋(report_scenarios150이 고른다)
_SCENARIO_SETS = {
    "12": (_REPO_ROOT / "data/eval/report_scenarios.jsonl", _REPO_ROOT / "data/eval/report_facts"),
    "150": (_REPO_ROOT / "data/eval/report_scenarios_150.jsonl", _REPO_ROOT / "data/eval/report_facts_150"),
}
_SCENARIOS, _FACTS_DIR = _SCENARIO_SETS["12"]
_CACHE = _REPO_ROOT / "data/eval/cache/llm-benchmark"
_RUNS = _CACHE / "report"
_JUDGE = _CACHE / "judge"
_INTENT_SUMMARY = _CACHE / "intent_summary.json"
_VRAM = _CACHE / "vram.json"
_RESIDENCY = _CACHE / "residency.json"
_RESULTS_ROOT = _REPO_ROOT / "data/eval/results"

_JUDGE_SEED = 0
_HUMAN_SAMPLE = 20  # 사람 검수 표본(설계서 §7) — judge-export가 시드로 고정해 human_sample.json에 남긴다
_DIGITS = re.compile(r"\d+")
# 샘플링은 운영 리포트와 같은 단일 원천(report_sampling: 온도 0·seed 42). 2026-10-05 기준선 캐시는 로컬 0.3·Gemini
# 기본값으로 돌았다 — 회차 기록에 temperature·seed를 남겨 보고서가 구분한다(옛 캐시는 "미기록").
_BASELINE_SAMPLING = "미기록(기준선: 로컬 0.3·Gemini 기본값)"
_BASE_TAG = "base"  # 판정 비교 모드에서 태그 없는 캐시의 이름
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
    return ReportModel(name, lambda: OllamaLLMAdapter(model=name, think=think, temperature=REPORT_TEMPERATURE,
                                                      seed=REPORT_SEED, num_ctx=BENCH_NUM_CTX), tools, True)


REPORT_MODELS: dict[str, ReportModel] = {m.name: m for m in (
    _ollama("gemma4:12b", False),
    _ollama("gemma4:e4b", False),
    _ollama("kanana1.5:8b-q4km", None),
    _ollama("qwen3.5:9b", False),
    _ollama("qwen3.5:4b", False),
    # Ollama 템플릿에 도구 처리가 없다 — 도구 없이 돌리는 참고 비교군(라이선스 NC)
    _ollama("exaone3.5:7.8b", None, tools=False),
    ReportModel(_ONLINE, lambda: GeminiLLMAdapter(model=_ONLINE, temperature=REPORT_TEMPERATURE, seed=REPORT_SEED),
                True, False),
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
    """이벤트 스트림 → {first_ms, total_ms, sections}.

    시계는 facts 이벤트 수신을 0으로, 해석(answer) 단락까지(first_ms)·report_done까지(total_ms)를 잰다.
    6개 절은 사실 수집 직후 곧바로 나가므로 지연의 의미가 해석 기준으로 바뀌었다(v0.68.0).
    """
    start: float | None = None
    first_ms = total_ms = None
    sections: dict[str, str] = {}
    for event in events:
        if event.type == "facts":
            start = clock()
        elif event.type == "report_delta":
            section = event.payload["section"]
            if section == "answer" and first_ms is None and start is not None:
                first_ms = (clock() - start) * 1000
            sections[section] = sections.get(section, "") + event.payload["markdown"]
        elif event.type == "report_done" and start is not None:
            total_ms = (clock() - start) * 1000
    return {"first_ms": first_ms, "total_ms": total_ms, "sections": sections}


def _report_text(sections: dict[str, str]) -> str:
    return concat_sections(sections.items())


def score_run(record: dict, facts: dict) -> dict:
    """한 회차 채점 — 해석(answer) 한 단락만 본다. 6개 절은 코드라 결정적이다(sections-check·단위 테스트).

    `digits`는 가드 뒤에도 남은 숫자 토큰 수(0이어야 한다 — 분석 동·대안 동 이름 속 숫자는 세지 않는다),
    `removed_sentences`·`raw_contradiction`은 시도 기록에서 가드가 지운 문장 수와 판정 모순으로 실패한 시도가 있었는지다.
    """
    answer = record["sections"].get("answer", "")
    attempts = record.get("answer_attempts") or []
    missing = scarcity(facts)
    # 자료 부족 동네는 LLM이 실패하면 코드 첫 문장만 남는다 — 그것도 폴백이다
    fallbacks = {ANSWER_FALLBACK, *([scarce_lead(facts, missing)] if missing is not None else [])}
    return {
        "complete": not record.get("error") and bool(answer),
        "fallback": answer in fallbacks,
        "verdict_ok": not contradicts_verdict(answer, facts.get("verdict")),
        "digits": len(_DIGITS.findall(blank_names(answer, region_names(facts)))),
        "removed_sentences": sum(a.get("removed_sentences", 0) for a in attempts),
        "raw_contradiction": any(a.get("contradiction") for a in attempts),
        "rule_hits": check_rule_keywords(answer),
    }


def score_summary(model: str, runs: list[dict]) -> dict:
    """모델 요약 — evaluate 호환 키(completion·verdict_match·fabrication·…)와 해석 지표(`answer`).

    호환 키는 모두 해석 단락 기준이다: fabrication = 가드 뒤에도 숫자가 남은 해석 비율(0이어야 한다).
    """
    n = len(runs)
    return {
        "model": model, "n": n,
        "completion": sum(r["complete"] for r in runs) / n,
        "verdict_match": sum(r["verdict_ok"] for r in runs) / n,
        "fabrication": sum(r["digits"] > 0 for r in runs) / n,
        "rule_violations_keyword": sum(len(r["rule_hits"]) for r in runs),
        "first_p95_ms": _p95([r["first_ms"] for r in runs]),  # 해석 단락이 나온 시각(본문 6개 절은 즉시)
        "total_p95_ms": _p95([r["total_ms"] for r in runs]),
        "answer": {
            "fallback_rate": sum(r["fallback"] for r in runs) / n,
            "digits_after_guard": sum(r["digits"] for r in runs),
            "raw_contradiction_rate": sum(r["raw_contradiction"] for r in runs) / n,
            "removed_sentences": sum(r["removed_sentences"] for r in runs),
        },
        "sampling": sampling_label(runs),
        "runs": [{k: r[k] for k in ("id", "rep", "complete", "fallback", "verdict_ok", "digits", "removed_sentences",
                                    "raw_contradiction", "rule_hits", "first_ms", "total_ms", "error")} for r in runs],
    }


def sampling_label(runs: list[dict]) -> str:
    """회차들이 쓴 온도/seed — 기록이 없는 옛 캐시는 기준선(로컬 0.3·Gemini 기본값)이라고 밝힌다."""
    labels = sorted({f"{r['temperature']}/{r['seed']}" for r in runs if "temperature" in r})
    if any("temperature" not in r for r in runs):  # 섞인 캐시에서 미기록 회차를 숨기지 않는다
        labels.append(_BASELINE_SAMPLING)
    return ", ".join(labels)


def run_record(scenario_id: str, rep: int, got: dict, error: str | None, interactor) -> dict:
    """캐시 한 줄 — 화면 본문(`sections`, 해석 포함)과 해석 시도 기록(`answer_attempts`: 원문·지운 문장 수·모순·오류)."""
    usage = interactor.last_usage
    return {"id": scenario_id, "rep": rep, **got, "answer_attempts": interactor.last_answer_attempts,
            "error": error, "temperature": REPORT_TEMPERATURE, "seed": REPORT_SEED,
            "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}}


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


def _cmd_sections_check(args: argparse.Namespace) -> None:
    """코드 절 자동 검사(설계서 §7) — 세트 전체 facts로 6개 절을 써서 범위 없는 숫자 줄·이유 빠진 자료 부족 자리를 센다.

    모델을 부르지 않는다. 결과는 `sections_check.json`(문제 있는 시나리오만 줄 단위로)이다.
    """
    scenarios = _scenarios()
    issues: dict[str, dict] = {}
    for s in scenarios:
        facts = _facts_of(s["id"])
        sections = build_sections(facts)
        region = facts.get("region") or {}
        regions = (facts.get("alternatives") or {}).get("regions") or []
        # 동 이름에 숫자가 든다("상계3.4동") — 이름은 숫자로 세지 않는다
        names = [n for n in (region.get("name"), *(r.get("region_name") for r in regions)) if n]
        scope = [w for w in (region.get("name"), region.get("industry_name"), *SCOPE_WORDS) if w]
        found = {
            "unscoped": [line for md in sections.values() for line in unscoped_number_lines(md, scope, names)],
            "missing": missing_data_gaps(facts, sections),
        }
        if any(found.values()):
            issues[s["id"]] = found
    _write_json(_RUNS / "sections_check.json", {"scenarios": len(scenarios), "issues": issues})
    print(f"sections-check: {len(scenarios)}건 중 문제 {len(issues)}건 → {_RUNS / 'sections_check.json'}", flush=True)


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


def _cmd_run(args: argparse.Namespace) -> None:
    model = REPORT_MODELS[args.model]
    llm = model.llm()
    if model.local:
        _load(model.name, options=_LOCAL_OPTIONS)  # 워밍업 — 모델 로드 시간은 지연에서 제외
    path = _run_path(model.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["id"], r["rep"]) for r in _read_jsonl(path)}
    for rep in range(args.repeat):
        for s in _scenarios():
            if (s["id"], rep) in done:
                continue
            frozen = FrozenFacts({(s["region_code"], s["industry_id"]): _facts_of(s["id"])})
            interactor = AnalysisInteractor(llm=llm, facts=frozen)  # 모델 하나만 평가한다 — 재시도 모델 없음
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
            if not error and interactor.last_usage.output_tokens == 0:
                error = "no_llm_output"
                print(f"run: 경고 {model.name} {s['id']} rep{rep} LLM 출력 없음", flush=True)
            row = run_record(s["id"], rep, got, error, interactor)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"run: {model.name} {s['id']} rep{rep} total={got['total_ms']} error={error}", flush=True)


def _cmd_score(args: argparse.Namespace) -> None:
    facts = {s["id"]: _facts_of(s["id"]) for s in _scenarios()}
    for name in REPORT_MODELS:
        records = _read_jsonl(_run_path(name))
        if not records:
            continue
        if any("answer_attempts" not in r for r in records):
            raise SystemExit("옛 형식 캐시 — 새 구조 벤치는 --cache-tag로 돌린 run만 채점")
        runs = [{**r, **score_run(r, facts[r["id"]])} for r in records]
        _write_json(_score_path(name), score_summary(name, runs))
        print(f"score: {name} → {_score_path(name)}", flush=True)


def _first_rep_answers() -> dict[str, tuple[str, dict[str, str]]]:
    """{시나리오 id: (코드 6개 절 본문, {모델: 1회차 해석})} — 해석의 모델명은 가린다. 본문은 모델과 무관하게 같다."""
    out: dict[str, tuple[str, dict[str, str]]] = {}
    for name in REPORT_MODELS:
        for r in _read_jsonl(_run_path(name)):
            answer = r["sections"].get("answer")
            if r["rep"] == 0 and answer:
                body = concat_sections((k, v) for k, v in r["sections"].items() if k != "answer")
                out.setdefault(r["id"], (body, {}))[1][name] = mask_model_names(answer)
    return out


def compare_reports(models: list[str], runs_by_tag: dict[str, Path]) -> dict[str, dict[str, str]]:
    """{시나리오: {"모델@태그": 1회차 본문}} — 두 태그의 같은 모델 회차를 한 묶음에 섞는다(본문 모델명은 가린다)."""
    out: dict[str, dict[str, str]] = {}
    for tag, runs_dir in runs_by_tag.items():
        for model in models:
            for r in _read_jsonl(runs_dir / f"{_safe(model)}.jsonl"):
                if r["rep"] == 0 and r["sections"]:
                    out.setdefault(r["id"], {})[f"{model}@{tag}"] = mask_model_names(_report_text(r["sections"]))
    return out


def compare_judged(scores: dict[str, dict[str, dict]], tag: str, other: str) -> dict:
    """`모델@태그`별 충실도·자연스러움 평균과, 같은 모델의 두 태그 짝지은 차이(tag − other, bootstrap 구간)."""
    means = {key: {"faithfulness": mean(s["faithfulness"] for s in by_sid.values()),
                   "fluency": mean(s["fluency"] for s in by_sid.values()), "n": len(by_sid)}
             for key, by_sid in scores.items() if by_sid}
    diffs = {}
    for model in sorted({key.rsplit("@", 1)[0] for key in scores}):
        mine, theirs = scores.get(f"{model}@{tag}", {}), scores.get(f"{model}@{other}", {})
        sids = sorted(set(mine) & set(theirs))
        if sids:
            diffs[model] = {metric: paired_bootstrap_ci([mine[s][metric] for s in sids], [theirs[s][metric] for s in sids])
                            for metric in ("faithfulness", "fluency")} | {"n": len(sids)}
    return {"means": means, "diffs": diffs}


def _compare_dir(args: argparse.Namespace) -> Path:
    """비교 묶음 판정 폴더 — 현재 판정 폴더 안에 따로 둔다(평소 묶음·점수를 덮어쓰지 않게)."""
    return _JUDGE / f"compare-{args.compare_tag}"


def _cmd_judge_export(args: argparse.Namespace) -> None:
    if args.compare_tag:
        _export_compare(args)
        return
    _JUDGE.mkdir(parents=True, exist_ok=True)
    questions = {s["id"]: s["question"] for s in _scenarios()}
    mapping: dict[str, dict[str, str]] = {}
    for sid, (body, answers) in _first_rep_answers().items():
        scarce = scarcity(_facts_of(sid)) is not None
        packet, mapping[sid] = answer_packets(sid, questions.get(sid), body, answers, _JUDGE_SEED, scarce)
        (_JUDGE / f"packet_{sid}.md").write_text(packet, encoding="utf-8")
    _write_json(_JUDGE / "mapping.json", mapping)
    # 사람 검수 표본 — 같은 시드면 같은 20건
    sample = sorted(random.Random(_JUDGE_SEED).sample(sorted(mapping), min(_HUMAN_SAMPLE, len(mapping))))
    _write_json(_JUDGE / "human_sample.json", sample)
    print(f"judge-export: {len(mapping)}개 시나리오(사람 검수 {len(sample)}건) → {_JUDGE}", flush=True)


def _export_compare(args: argparse.Namespace) -> None:
    """두 태그 캐시의 같은 모델 회차를 섞은 블라인드 묶음 — mapping 값은 `모델@태그`."""
    tag = args.cache_tag or _BASE_TAG
    runs = {tag: _RUNS, args.compare_tag: cache_dirs(None if args.compare_tag == _BASE_TAG else args.compare_tag)[0]}
    out = _compare_dir(args)
    out.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, dict[str, str]] = {}
    for sid, reports in compare_reports(args.models.split(","), runs).items():
        packet, mapping[sid] = judge_packets(sid, _facts_of(sid), reports, _JUDGE_SEED)
        (out / f"packet_{sid}.md").write_text(packet, encoding="utf-8")
    _write_json(out / "mapping.json", mapping)
    print(f"judge-export(비교): {len(mapping)}개 시나리오 {tag} vs {args.compare_tag} → {out}", flush=True)


def _cmd_judge_import(args: argparse.Namespace) -> None:
    judge_dir = _compare_dir(args) if args.compare_tag else _JUDGE  # 비교 묶음이면 키가 `모델@태그`다
    mapping = _read_json(judge_dir / "mapping.json")
    judged = json.loads(Path(args.file).read_text(encoding="utf-8"))
    scores: dict[str, dict[str, dict]] = _read_json(judge_dir / "scores.json", {})  # 이어 넣기 — 덮어쓰지 않는다
    for sid, by_blind in judged.items():
        for blind, score in by_blind.items():
            scores.setdefault(mapping[sid][blind], {})[sid] = score
    _write_json(judge_dir / "scores.json", scores)
    print(f"judge-import: {len(scores)}개 모델 → {judge_dir / 'scores.json'}", flush=True)


def _argument_error(args: argparse.Namespace) -> str | None:
    """비교 모드 인자 검증 — 잘못이면 사용자에게 보일 문장, 아니면 None."""
    if args.compare_tag and not args.models and args.command == "judge-export":
        return "--compare-tag로 내보내려면 --models a,b 가 필요합니다"
    if args.compare_tag and args.compare_tag == (args.cache_tag or _BASE_TAG):
        return f"--compare-tag({args.compare_tag})가 현재 캐시 태그와 같습니다 — 다른 태그와 비교하세요"
    if args.command in ("score", "sections-check") and not args.cache_tag:
        return "새 구조 벤치는 --cache-tag가 필요합니다 — 태그 없는 report/는 옛 기준선 캐시라 쓰지 않습니다"
    return None


def _cmd_judge_compare(args: argparse.Namespace) -> None:
    tag = args.cache_tag or _BASE_TAG
    got = compare_judged(_read_json(_compare_dir(args) / "scores.json", {}), tag, args.compare_tag)
    for key, m in sorted(got["means"].items()):
        print(f"{key}: 충실도 {m['faithfulness']:.2f} · 자연스러움 {m['fluency']:.2f} (n={m['n']})")
    for model, d in got["diffs"].items():
        print(f"{model} {tag}−{args.compare_tag} (n={d['n']}): "
              + " · ".join(f"{k} {d[k][0]:+.2f} [{d[k][1]:+.2f}, {d[k][2]:+.2f}]" for k in ("faithfulness", "fluency")))


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
                     "gates": gates, "note": note, "local": model.local, "excluded": excluded,
                     "guard": score.get("guard"), "raw": score.get("raw"),
                     "sampling": score.get("sampling"), "consistency": score.get("consistency")})
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
    "freeze": _cmd_freeze, "sections-check": _cmd_sections_check, "run": _cmd_run, "score": _cmd_score, "judge-export": _cmd_judge_export,
    "judge-import": _cmd_judge_import, "judge-compare": _cmd_judge_compare, "vram": _cmd_vram, "residency": _cmd_residency, "evaluate": _cmd_evaluate,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=list(_COMMANDS))
    parser.add_argument("--model", choices=list(REPORT_MODELS))
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--file", default=None, help="judge-import: 판정 json 경로")
    parser.add_argument("--compare-tag", default=None,
                        help="judge-export·import·compare: 이 태그 캐시와 섞어 비교(태그 없는 캐시는 base)")
    parser.add_argument("--models", default=None, help="judge-export --compare-tag: 비교할 모델(쉼표 구분)")
    parser.add_argument("--report-model", default=None)
    parser.add_argument("--intent-model", default=None)
    parser.add_argument("--force", action="store_true", help="freeze: 기존 facts 덮어쓰기")
    parser.add_argument("--out-dir", default=None, help="evaluate: 결과 폴더 이름(기본 llm-benchmark-YYYY-MM-DD)")
    parser.add_argument("--cache-tag", default=None, help="run·score·judge-*·evaluate: 캐시를 report-<tag>/·judge-<tag>/로 분리")
    parser.add_argument("--scenario-set", choices=list(_SCENARIO_SETS), default="12",
                        help="시나리오 파일·facts 폴더 묶음(기본 12건, 150은 report_scenarios_150·report_facts_150)")
    args = parser.parse_args()
    if error := _argument_error(args):
        parser.error(error)
    global _RUNS, _JUDGE, _SCENARIOS, _FACTS_DIR  # 명령 함수들이 모듈 경로를 읽는다 — 실행 시작에 한 번만 바꾼다
    _RUNS, _JUDGE = cache_dirs(args.cache_tag)
    _SCENARIOS, _FACTS_DIR = _SCENARIO_SETS[args.scenario_set]
    _COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
