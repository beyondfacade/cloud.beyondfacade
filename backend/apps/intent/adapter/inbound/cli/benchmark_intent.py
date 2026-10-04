"""의도 관문 LLM 평가 CLI — 로컬 후보와 Gemini를 같은 평가셋으로 재 관문 추출기를 고른다 (Driving Adapter).

운영 경로는 건드리지 않는다. 평가셋(data/eval/intent_evalset.jsonl)은 검수 시트로 확정하고,
모델별 추출 결과를 문항·회차 단위 jsonl로 캐시한 뒤 채점한다(intent_bench_scoring).

실행 순서 (backend/에서):
  python -m apps.intent.adapter.inbound.cli.benchmark_intent masters --out PATH
  python -m apps.intent.adapter.inbound.cli.benchmark_intent sheet
  python -m apps.intent.adapter.inbound.cli.benchmark_intent apply
  python -m apps.intent.adapter.inbound.cli.benchmark_intent run --model gemma4:12b [--repeat 3]
  python -m apps.intent.adapter.inbound.cli.benchmark_intent evaluate
"""

import argparse
import json
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from apps.intent.adapter.inbound.cli.intent_bench_scoring import parse_sheet, render_sheet, score_row, summarize
from apps.intent.adapter.outbound.gateways.master_dictionary_gateway import MasterDictionaryGateway
from apps.intent.adapter.outbound.llm.gemini_intent_llm_adapter import GeminiIntentLlmAdapter
from apps.intent.adapter.outbound.llm.ollama_intent_llm_adapter import OllamaIntentLlmAdapter
from apps.intent.app.dtos.intent_dto import LlmSuggestion
from core.matrix.grid_benchmark_manager import percentile

# apps/intent/adapter/inbound/cli/benchmark_intent.py → parents[6] == 리포지토리 루트
_REPO_ROOT = Path(__file__).resolve().parents[6]
_EVALSET = _REPO_ROOT / "data/eval/intent_evalset.jsonl"
_SHEET = _REPO_ROOT / "data/eval/intent_evalset_review.md"
_CACHE = _REPO_ROOT / "data/eval/cache/llm-benchmark/intent"
_SUMMARY = _REPO_ROOT / "data/eval/cache/llm-benchmark/intent_summary.json"

_MODELS: dict[str, Callable] = {
    "gemma4:12b": lambda m: OllamaIntentLlmAdapter(m, model="gemma4:12b", think=False, timeout_s=30),
    "gemma4:e4b": lambda m: OllamaIntentLlmAdapter(m, model="gemma4:e4b", think=False, timeout_s=30),
    "kanana1.5:8b-q4km": lambda m: OllamaIntentLlmAdapter(m, model="kanana1.5:8b-q4km", timeout_s=30),
    "qwen3.5:9b": lambda m: OllamaIntentLlmAdapter(m, model="qwen3.5:9b", think=False, timeout_s=30),
    "qwen3.5:4b": lambda m: OllamaIntentLlmAdapter(m, model="qwen3.5:4b", think=False, timeout_s=30),
    "qwen3.5:2b-q4_K_M": lambda m: OllamaIntentLlmAdapter(m, model="qwen3.5:2b-q4_K_M", think=False, timeout_s=30),
    "gemini-2.5-flash": lambda m: GeminiIntentLlmAdapter(m),
}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def _cache_path(model: str) -> Path:
    return _CACHE / f"{model.replace(':', '_').replace('/', '_')}.jsonl"


def _confirmed() -> list[dict]:
    return [r for r in _read_jsonl(_EVALSET) if r["status"] == "confirmed"]


def _cmd_masters(args: argparse.Namespace) -> None:
    master = MasterDictionaryGateway().load()
    data = {
        "regions": [{"name": r.name, "district": r.district_name} for r in master.regions],
        "industries": master.industry_names,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"masters: 동 {len(data['regions'])}개 · 업종 {len(data['industries'])}개 → {out}", flush=True)


def _cmd_sheet(args: argparse.Namespace) -> None:
    if _SHEET.exists() and not args.force:
        print(f"sheet: {_SHEET} 가 이미 있습니다 — O/X 판정이 지워지니 apply 후에 다시 만들거나 --force 를 쓰세요.", flush=True)
        return
    rows = _read_jsonl(_EVALSET)
    _SHEET.write_text(render_sheet(rows), encoding="utf-8")
    print(f"sheet: {len(rows)}문항 → {_SHEET}", flush=True)


_VERDICT_STATUS = {"O": "confirmed", "X": "rejected"}


def _cmd_apply(args: argparse.Namespace) -> None:
    marks = parse_sheet(_SHEET.read_text(encoding="utf-8"))
    rows = _read_jsonl(_EVALSET)
    for row in rows:
        mark, expected = marks.get(row["id"], (None, None))
        status = _VERDICT_STATUS.get(mark or "")
        if status is None:
            continue
        row["status"] = status
        if status == "confirmed" and expected is not None:
            row["expected"] = expected
    _write_jsonl(_EVALSET, rows)
    counts = {s: sum(r["status"] == s for r in rows) for s in ("confirmed", "rejected", "candidate")}
    print(f"apply: {counts}", flush=True)


def _cmd_run(args: argparse.Namespace) -> None:
    adapter = _MODELS[args.model](MasterDictionaryGateway())
    items = _confirmed()
    path = _cache_path(args.model)
    done = {(r["id"], r["rep"]) for r in _read_jsonl(path)}
    path.parent.mkdir(parents=True, exist_ok=True)
    if items:
        adapter.extract(items[0]["text"])  # 워밍업 — 모델 로드 시간은 지연에서 제외
    for rep in range(args.repeat):
        for item in items:
            if (item["id"], rep) in done:
                continue
            start = time.perf_counter()
            got = adapter.extract(item["text"])
            ms = (time.perf_counter() - start) * 1000
            row = {"id": item["id"], "rep": rep, "ms": ms, "got": asdict(got) if got else None}
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"run: {args.model} → {path}", flush=True)


def _cmd_evaluate(args: argparse.Namespace) -> None:
    items = _confirmed()  # 확정 평가셋 순서 — 모델 간 쌍 비교(bootstrap)를 위해 고정
    summary: dict[str, dict] = {}
    for model in _MODELS:
        records = _read_jsonl(_cache_path(model))
        if not records:
            continue
        first = {r["id"]: r for r in records if r["rep"] == 0}
        confirmed_ids = {i["id"] for i in items}
        done = sum(i["id"] in first for i in items)
        if done < len(items):
            print(f"evaluate: {model} 미완료 — 1회차 {done}/{len(items)}건, 제외", flush=True)
            continue
        ids = [i["id"] for i in items]
        scored = [
            score_row(i["expected"], LlmSuggestion(**first[i["id"]]["got"]) if first[i["id"]]["got"] else None)
            for i in items
        ]
        ms = [r["ms"] for r in records if r["id"] in confirmed_ids]
        summary[model] = {**summarize(scored), "p50_ms": percentile(ms, 50), "p95_ms": percentile(ms, 95),
                          "per_row_both": [s["both"] for s in scored], "ids": ids}
    _SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    _SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"evaluate: {len(summary)}개 모델 → {_SUMMARY}", flush=True)


_COMMANDS: dict[str, Callable] = {
    "masters": _cmd_masters, "sheet": _cmd_sheet, "apply": _cmd_apply, "run": _cmd_run, "evaluate": _cmd_evaluate,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=list(_COMMANDS))
    parser.add_argument("--model", choices=list(_MODELS))
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--out", default=None, help="masters 출력 경로")
    parser.add_argument("--force", action="store_true", help="sheet: 기존 검수 시트 덮어쓰기")
    args = parser.parse_args()
    _COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
