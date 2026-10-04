"""리포트 벤치 CLI 순수 부분 — 고정 facts, 게이트, 보고서."""

from apps.agent.adapter.inbound.cli.benchmark_report import (
    REPORT_MODELS,
    FrozenFacts,
    collect_run,
    score_run,
)
from apps.agent.adapter.inbound.cli.report_bench_scoring import (
    intent_gates,
    mask_model_names,
    render_llm_report,
    report_gates,
)
from apps.agent.domain.entities.agent_event_entity import AgentEvent


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


def test_승자가_없으면_보고서가_그렇게_말한다():
    results = {"date": "2026-10-04", "report": {"rows": [], "winner": None, "tied": []},
               "intent": {"rows": [], "winner": None, "tied": []}, "residency": None}
    md = render_llm_report(results)
    assert "리포트: **없음**" in md and "동시 상주: 미측정" in md


def test_판정자_묶음의_모델_이름을_가린다():
    text = "Gemma4:12b와 qwen3.5:4b, 카카오의 kanana1.5, 구글 Gemini-2.5-flash, LG AI, LG. algorithm 은 그대로."
    masked = mask_model_names(text)
    for name in ("emma", "wen", "kanana", "카카오", "구글", "emini", "LG"):
        assert name not in masked
    assert "algorithm" in masked and masked.count("[모델]") >= 6


def _events():
    return [
        AgentEvent("agent_status", {"agent": "facts", "status": "running"}),
        AgentEvent("facts", {"verdict": {}}),
        AgentEvent("tool_call", {"agent": "funding", "tool": "x", "summary": "s"}),
        AgentEvent("report_delta", {"section": "verdict", "markdown": "### 판정\n비추천"}),
        AgentEvent("report_delta", {"section": "verdict", "markdown": " 입니다."}),
        AgentEvent("report_done", {"report_id": "r", "citations": []}),
    ]


def test_이벤트에서_지연과_절을_모은다():
    ticks = iter([10.0, 10.5, 12.0])  # facts 수신 · 첫 delta · done (초)
    got = collect_run(_events(), clock=lambda: next(ticks))
    assert got["first_ms"] == 500 and got["total_ms"] == 2000
    assert got["sections"] == {"verdict": "### 판정\n비추천 입니다."}
    assert got["tool_calls"] == [{"agent": "funding", "tool": "x", "summary": "s"}]


def test_한_회차_채점_완주_판정_숫자():
    facts = {"verdict": {"available": True, "verdict_code": "red"}}
    ok = {"sections": {"verdict": "비추천입니다. 폐업률 12.3%"}, "error": None}
    got = score_run(ok, facts)
    assert got["complete"] is False  # 6절 중 1절만
    assert got["verdict_ok"] is True
    assert got["unmatched"] == ["12.3%"]
    assert score_run({"sections": {}, "error": "boom"}, facts)["verdict_ok"] is False
