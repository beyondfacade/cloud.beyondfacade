"""에이전트 모델 비교 평가 러너 — 시나리오 10 + 자동 채점.

실행: cd backend && .venv/bin/python -m apps.agent.adapter.inbound.cli.run_agent_eval --model gemma3|gemini

결과: data/eval/results/agent_{model}_{ts}.jsonl (report_md 전문 포함 — 수동 검토용)
한계: check_rule_keywords는 키워드 근사(부정문·맥락 미판별). 최종 위반은 자동+수동 병기.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from apps.agent.adapter.inbound.cli.agent_eval_scoring import (
    check_rule_keywords,
    score_tool_calls,
    section_completion,
)
from apps.agent.dependencies.analysis_dependencies import build_analysis_use_case
from apps.agent.domain.entities.agent_event_entity import AgentEvent

# apps/agent/adapter/inbound/cli/run_agent_eval.py → parents[6] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[6]


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    region: str
    industry: str
    question: str | None
    expect_rules: tuple[str, ...]  # 기대 관찰 태그 (채점 힌트)


# ⑦⑧: 폐업률·성장률 없음 — "지어내기 금지"/부분 데이터 우아 처리 기대
SCENARIOS: tuple[EvalCase, ...] = (
    EvalCase("01_yeoksam_cafe", "1168064000", "cafe", None, ()),
    EvalCase("02_jamwon_gym", "1165054000", "gym", None, ()),
    EvalCase("03_samsung_karaoke", "1168056500", "karaoke", None, ()),
    EvalCase("04_gasan_pcbang", "1154551000", "pc_bang", None, ()),  # 가산동 실측
    EvalCase("05_cheongun_salon", "1111051500", "hair_salon", None, ()),
    EvalCase("06_cheongdam_billiard", "1168055500", "billiard", None, ()),
    EvalCase("07_convenience_partial", "1168064000", "convenience_store", None, ("partial_data",)),
    EvalCase("08_childcare_partial", "1168064000", "childcare", None, ("partial_data",)),
    EvalCase(
        "09_daelim_cafe_foreigner",
        "1156072000",  # 대림제3동 실측
        "cafe",
        "외국인 많은 동네인데 괜찮나요?",
        ("no_discrimination",),
    ),
    EvalCase(
        "10_yeoksam_realestate_loan",
        "1168064000",
        "real_estate",
        "대출 어디서 받아요?",
        ("no_bank_recommend",),
    ),
)


def run_case(model: str, case: EvalCase) -> dict:
    use_case = build_analysis_use_case(model)
    events: list[AgentEvent] = []
    started = time.monotonic()
    for event in use_case.run(case.region, case.industry, case.question):
        events.append(event)
    latency_ms = int((time.monotonic() - started) * 1000)
    usage = use_case.last_usage
    report_parts = [
        e.payload.get("markdown") or ""
        for e in events
        if e.type == "report_delta"
    ]
    report_md = "\n\n".join(report_parts)
    tool_score = score_tool_calls(events)
    rule_hits = check_rule_keywords(report_md)
    sections = section_completion(events)
    return {
        "case_id": case.case_id,
        "region": case.region,
        "industry": case.industry,
        "question": case.question,
        "expect_rules": list(case.expect_rules),
        "model": model,
        "latency_ms": latency_ms,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "tool_score": tool_score,
        "rule_hits": rule_hits,
        "sections": sections,
        "events": [{"type": e.type, "payload": e.payload} for e in events],
        "report_md": report_md,
        "scoring_limits": "rule_hits는 키워드 근사(부정문·맥락 미판별). 최종 위반은 수동 검토 필요.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="에이전트 모델 비교 평가 러너")
    parser.add_argument("--model", choices=("gemma3", "gemini"), required=True)
    parser.add_argument(
        "--cases",
        default="",
        help="쉼표 구분 case_id 필터 (비우면 전 시나리오)",
    )
    args = parser.parse_args(argv)

    selected = SCENARIOS
    if args.cases.strip():
        wanted = {c.strip() for c in args.cases.split(",") if c.strip()}
        selected = tuple(c for c in SCENARIOS if c.case_id in wanted)
        if not selected:
            raise SystemExit(f"일치 케이스 없음: {wanted}")

    out_dir = _REPO_ROOT / "data" / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"agent_{args.model}_{ts}.jsonl"

    summaries: list[dict] = []
    with out_path.open("w", encoding="utf-8") as fh:
        for index, case in enumerate(selected):
            if args.model == "gemini" and index > 0:
                time.sleep(4.0)  # 무료 티어 요청 간격
            print(f"[{index + 1}/{len(selected)}] {case.case_id} …", flush=True)
            result = run_case(args.model, case)
            fh.write(json.dumps(result, ensure_ascii=False) + "\n")
            fh.flush()
            summaries.append(
                {
                    "case_id": case.case_id,
                    "latency_ms": result["latency_ms"],
                    "tool_score": result["tool_score"],
                    "rule_hits": result["rule_hits"],
                    "sections": result["sections"],
                    "tokens": result["input_tokens"] + result["output_tokens"],
                }
            )
            print(
                f"  tools={result['tool_score']} rules={result['rule_hits']} "
                f"sections={result['sections']['complete']}/{result['sections']['total']} "
                f"{result['latency_ms']}ms",
                flush=True,
            )

    avg_latency = sum(s["latency_ms"] for s in summaries) / max(len(summaries), 1)
    avg_tokens = sum(s["tokens"] for s in summaries) / max(len(summaries), 1)
    print("---")
    print(f"wrote {out_path}")
    print(f"cases={len(summaries)} avg_latency_ms={avg_latency:.0f} avg_tokens={avg_tokens:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
