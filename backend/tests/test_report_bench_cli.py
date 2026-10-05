"""리포트 벤치 CLI 순수 부분 — 고정 facts, 게이트, 보고서."""

from apps.agent.adapter.inbound.cli.benchmark_report import (
    REPORT_MODELS,
    build_intent_block,
    build_report_block,
    FrozenFacts,
    collect_run,
    gemini_cost,
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
        AgentEvent("report_delta", {"section": "verdict", "markdown": "### 판정\n비추천"}),
        AgentEvent("report_delta", {"section": "answer", "markdown": "신중히 보세요."}),
        AgentEvent("report_done", {"report_id": "r", "citations": []}),
    ]


def test_첫_글자_지연은_해석_단락이_나온_시각이다():
    ticks = iter([10.0, 10.5, 12.0])  # facts 수신 · 해석 delta · done (초) — 코드 절 delta는 시계를 읽지 않는다
    got = collect_run(_events(), clock=lambda: next(ticks))
    assert got["first_ms"] == 500 and got["total_ms"] == 2000
    assert got["sections"] == {"verdict": "### 판정\n비추천", "answer": "신중히 보세요."}


def test_해석_채점은_가드_뒤_숫자_모순_폴백과_지운_문장을_센다():
    from apps.agent.app.use_cases.analysis_interactor import ANSWER_FALLBACK

    facts = {"verdict": {"available": True, "verdict_code": "red"}}
    attempts = [{"model": "a", "removed_sentences": 2, "contradiction": "판정은 **경고 없음"},
                {"model": "b", "removed_sentences": 1, "contradiction": None}]

    ok = score_run({"sections": {"answer": "신중히 보세요. 대안을 먼저 보세요."}, "answer_attempts": attempts,
                    "error": None}, facts)
    fallback = score_run({"sections": {"answer": ANSWER_FALLBACK}, "error": None}, facts)

    assert ok == {"complete": True, "fallback": False, "verdict_ok": True, "digits": 0, "removed_sentences": 3,
                  "raw_contradiction": True, "rule_hits": []}
    assert fallback["fallback"] is True and fallback["removed_sentences"] == 0


def test_모델명을_가려도_한국어_조사는_남는다():
    assert mask_model_names("Gemma4:12b와 Qwen3.5:4b는") == "[모델]와 [모델]는"


def _score(**kw):
    base = {"completion": 1.0, "verdict_match": 1.0, "fabrication": 0.0, "rule_violations_keyword": 0,
            "first_p95_ms": 1000, "total_p95_ms": 10000}
    return {**base, **kw}


def _judge(model_scores, ids, viol=()):
    return {sid: {"faithfulness": f, "fluency": f, "violations": list(viol)} for sid, f in zip(ids, model_scores)}


def test_판정_대상_게이트_탈락과_온라인과_판정_부분은_제외():
    ids = ["a", "b"]
    scores = {"qwen3.5:4b": _score(), "qwen3.5:9b": _score(fabrication=0.5),
              "gemma4:e4b": _score(), "gemini-2.5-flash": _score()}
    judge = {"qwen3.5:4b": _judge([4, 4], ids), "qwen3.5:9b": _judge([5, 5], ids),
             "gemma4:e4b": _judge([5], ids[:1]), "gemini-2.5-flash": _judge([5, 5], ids)}
    vram = {"qwen3.5:4b": 3400, "qwen3.5:9b": 6600, "gemma4:e4b": 9600}
    block = build_report_block(scores, judge, vram, ids)
    why = {r["model"]: r["excluded"] for r in block["rows"]}
    assert block["winner"] == "qwen3.5:4b"
    assert why["qwen3.5:4b"] is None
    assert why["qwen3.5:9b"] == "게이트 탈락: fabrication"
    assert why["gemma4:e4b"] == "판정 미완료 1/2"
    assert "온라인" in why["gemini-2.5-flash"]


def test_규칙_위반은_키워드와_판정자_보고를_합친다():
    ids = ["a", "b"]
    scores = {"qwen3.5:4b": _score(rule_violations_keyword=0)}
    judge = {"qwen3.5:4b": _judge([4, 4], ids, viol=["차별 표현"])}
    block = build_report_block(scores, judge, {"qwen3.5:4b": 3400}, ids)
    row = block["rows"][0]
    assert row["rule_violations"] == 2 and row["gates"]["rules"] is False and block["winner"] is None


def test_VRAM_미측정은_제외_사유로_남는다():
    ids = ["a"]
    block = build_report_block({"qwen3.5:4b": _score()}, {"qwen3.5:4b": _judge([4], ids)}, {}, ids)
    assert block["rows"][0]["excluded"] == "VRAM 미측정"


def test_참고_순위는_게이트와_별개로_로컬_전부를_줄_세우고_위반_유형을_센다():
    ids = ["a", "b"]
    scores = {"qwen3.5:4b": _score(fabrication=0.5), "qwen3.5:9b": _score(), "gemini-2.5-flash": _score()}
    judge = {"qwen3.5:4b": _judge([5, 5], ids, viol=["금리 예상치 고지 없음"]),
             "qwen3.5:9b": _judge([3, 3], ids, viol=["표기 누락"]),
             "gemini-2.5-flash": _judge([5, 5], ids)}
    block = build_report_block(scores, judge, {"qwen3.5:4b": 3400.7, "qwen3.5:9b": 6600}, ids)
    ref = block["reference"]
    assert [r["model"] for r in ref["ranking"]] == ["qwen3.5:4b", "qwen3.5:9b"]
    assert ref["ranking"][0]["failed"] == ["fabrication", "rules"] and ref["winner"] == "qwen3.5:4b"
    assert ref["violations"]["qwen3.5:4b"] == {"금융": 2}
    results = {"date": "2026-10-04", "report": {**block, "winner": None}, "intent": {"rows": [], "winner": None},
               "residency": None}
    md = render_llm_report(results)
    assert "## 참고 순위 (게이트와 별개)" in md and "채택 결정이 아니다" in md
    assert "참고 1위(동률 시 VRAM 작은 쪽): **qwen3.5:4b**" in md and "| 3401 |" in md


def test_참고_순위는_시나리오별_품질과_1위_대비_bootstrap_구간을_남기고_위반_유형에_온라인도_넣는다():
    ids = ["a", "b"]
    scores = {"qwen3.5:4b": _score(fabrication=0.5), "qwen3.5:9b": _score(), "gemini-2.5-flash": _score()}
    judge = {"qwen3.5:4b": _judge([5, 4], ids), "qwen3.5:9b": _judge([3, 3], ids),
             "gemini-2.5-flash": _judge([5, 5], ids, viol=["표기 누락"])}
    ref = build_report_block(scores, judge, {"qwen3.5:4b": 3400, "qwen3.5:9b": 6600}, ids)["reference"]
    assert ref["scenario_ids"] == ids
    assert ref["per_scenario"] == {"qwen3.5:4b": [10, 8], "qwen3.5:9b": [6, 6]}
    assert ref["best"] == "qwen3.5:4b" and list(ref["ci_vs_best"]) == ["qwen3.5:9b"]
    assert ref["ci_vs_best"]["qwen3.5:9b"][0] == 3.0
    assert ref["violations"]["gemini-2.5-flash"] == {"신뢰 등급 표기": 2}


def test_리포트_행에_판정_등급_생략_건수():
    ids = ["a"]
    block = build_report_block({"qwen3.5:4b": _score(verdict_no_grade=3)}, {"qwen3.5:4b": _judge([4], ids)},
                               {"qwen3.5:4b": 3400}, ids)
    assert block["rows"][0]["verdict_no_grade"] == 3


def _intent(both, fab=0.0, p95=1000.0):
    return {"both": sum(both) / len(both), "region": 1.0, "industry": 1.0, "budget": 1.0, "schema_rate": 1.0,
            "fabrication_rate": fab, "fabrication_any_null": fab / 2, "p95_ms": p95, "per_row_both": both,
            "ids": [f"i{n}" for n in range(len(both))]}


def test_관문_블록은_게이트와_별개로_로컬_참고_순위와_문항별_점수를_남긴다():
    summary = {"gemma4:12b": _intent([1.0, 1.0, 0.0], fab=0.077), "gemma4:e4b": _intent([1.0, 0.0, 0.0], fab=0.2),
               "gemini-2.5-flash": _intent([1.0, 1.0, 1.0])}
    block = build_intent_block(summary, {"gemma4:12b": 8034, "gemma4:e4b": 3158})
    assert block["winner"] is None
    ref = block["reference"]
    assert ref["per_row_both"]["gemma4:12b"] == [1.0, 1.0, 0.0] and "gemini-2.5-flash" in ref["per_row_both"]
    assert [r["model"] for r in ref["ranking"]] == ["gemma4:12b", "gemma4:e4b"]
    assert ref["best"] == "gemma4:12b" and "gemma4:e4b" in ref["ci_vs_best"] and ref["winner"] in ref["tied"]
    assert {r["model"]: r["fabrication_any_null"] for r in block["rows"]}["gemma4:12b"] == 0.0385


def test_Gemini_리포트_비용은_캐시_토큰_평균에서_계산한다():
    records = [{"usage": {"input_tokens": 1_000_000, "output_tokens": 0}},
               {"usage": {"input_tokens": 0, "output_tokens": 1_000_000}}]
    cost = gemini_cost(records)
    assert cost["mean_input_tokens"] == 500_000 and cost["mean_output_tokens"] == 500_000
    assert abs(cost["usd_per_report"] - (0.15 + 1.25)) < 1e-9
    assert cost["checked"] == "2026-10-05" and cost["source"] == "https://ai.google.dev/gemini-api/docs/pricing"


def test_보고서는_판정_모순_없음_등급_생략_비용_notes_링크를_싣는다():
    row = {"model": "qwen3.5:4b", "vram_mib": 3400, "quality": 7.2, "gates": {"all": True}, "verdict_match": 1.0,
           "verdict_no_grade": 3, "n": 36}
    results = {"date": "2026-10-05", "report": {"rows": [row], "winner": None, "tied": []},
               "intent": {"rows": [{"model": "m", "gates": {"all": False}, "fabrication_any_null": 0.039}],
                          "winner": None},
               "residency": None,
               "cost": {"model": "gemini-2.5-flash", "n": 36, "mean_input_tokens": 14085.2,
                        "mean_output_tokens": 1942.4, "usd_per_report": 0.0091, "price_per_1m_usd":
                        {"input": 0.30, "output": 2.50}, "checked": "2026-10-05",
                        "source": "https://ai.google.dev/gemini-api/docs/pricing"}}
    md = render_llm_report(results)
    assert "판정 모순 없음" in md and "| 3/36 |" in md and "0.039" in md
    assert "$0.0091" in md and "[notes.md](notes.md)" in md


def test_캐시_태그가_없으면_지금_경로_있으면_분리된_경로를_쓴다():
    from apps.agent.adapter.inbound.cli.benchmark_report import _CACHE, cache_dirs

    assert cache_dirs(None) == (_CACHE / "report", _CACHE / "judge")
    assert cache_dirs("guards") == (_CACHE / "report-guards", _CACHE / "judge-guards")


def test_평가_결과_폴더는_out_dir로_바꿀_수_있다(tmp_path, monkeypatch):
    import argparse

    from apps.agent.adapter.inbound.cli import benchmark_report as br

    monkeypatch.setattr(br, "_RESULTS_ROOT", tmp_path)
    monkeypatch.setattr(br, "_RUNS", tmp_path / "runs")
    monkeypatch.setattr(br, "_scenarios", lambda: [])
    monkeypatch.setattr(br, "_report_block", lambda ids: {"winner": None})
    monkeypatch.setattr(br, "_intent_block", lambda: {"winner": None})
    monkeypatch.setattr(br, "render_llm_report", lambda results: "md")

    br._cmd_evaluate(argparse.Namespace(out_dir="llm-benchmark-2026-10-05-guards"))
    br._cmd_evaluate(argparse.Namespace(out_dir=None))

    assert (tmp_path / "llm-benchmark-2026-10-05-guards" / "report.md").exists()
    assert any(p.name.startswith("llm-benchmark-") and p.name != "llm-benchmark-2026-10-05-guards"
               for p in tmp_path.iterdir())


# --- 가드 전 원문 보존 (리뷰 1차) ---

_GUARD = {"verdict_replaced": 1, "links_stripped": 2, "tags_added": 5, "disclaimer_added": 1}


def test_보고서에_가드_개입_표와_첫_글자_지연_주의를_싣는다():
    ids = ["a"]
    score = {**_score(), "guard": _GUARD, "raw": {"completion": 0.5, "verdict_match": 0.75, "fabrication": 0.25,
                                                   "rule_violations_keyword": 1}}
    block = build_report_block({"qwen3.5:4b": score}, {"qwen3.5:4b": _judge([4], ids)}, {"qwen3.5:4b": 3400}, ids)
    results = {"date": "2026-10-06", "report": block, "intent": {"rows": [], "winner": None, "tied": []},
               "residency": None}

    md = render_llm_report(results)

    assert "## 코드 가드 개입" in md
    assert "| qwen3.5:4b | 1 | 2 | 5 | 1 | 0.75 | 0.25 |" in md
    assert "판정 절 전체를 붙드는 시간" in md


# --- 일관성 1단계: 샘플링 기록·일관성 표·판정 비교 모드 ---


def test_벤치_모델은_로컬과_gemini_모두_운영_샘플링_상수로_부른다(monkeypatch):
    from apps.agent.adapter.inbound.cli import benchmark_report as br
    from apps.agent.domain.services.report_sampling import REPORT_SEED, REPORT_TEMPERATURE

    built = {}
    monkeypatch.setattr(br, "OllamaLLMAdapter", lambda **kw: built.setdefault("ollama", kw))
    monkeypatch.setattr(br, "GeminiLLMAdapter", lambda **kw: built.setdefault("gemini", kw))
    br.REPORT_MODELS["gemma4:12b"].llm()
    br.REPORT_MODELS["gemini-2.5-flash"].llm()

    for kw in built.values():
        assert (kw["temperature"], kw["seed"]) == (REPORT_TEMPERATURE, REPORT_SEED)
    assert not hasattr(br, "_TEMPERATURE")


def test_샘플링_표기는_기록이_없으면_기준선이라고_밝힌다():
    from apps.agent.adapter.inbound.cli.benchmark_report import sampling_label

    assert sampling_label([{"temperature": 0.0, "seed": 42}] * 2) == "0.0/42"
    assert sampling_label([{}]) == "미기록(기준선: 로컬 0.3·Gemini 기본값)"


def test_보고서에_일관성_표를_싣는다():
    ids = ["a"]
    score = {**_score(), "sampling": "0.0/42",
             "consistency": {"outcome": 0.75, "numbers": 0.5, "text": 0.9, "alt_grades": 1.0, "scenarios": 12}}
    block = build_report_block({"qwen3.5:4b": score}, {"qwen3.5:4b": _judge([4], ids)}, {"qwen3.5:4b": 3400}, ids)
    md = render_llm_report({"date": "2026-10-06", "report": block,
                            "intent": {"rows": [], "winner": None, "tied": []}, "residency": None})

    assert "## 일관성(반복 3회)" in md
    assert "| qwen3.5:4b | 0.0/42 | 12 | 0.75 | 0.50 | 0.90 | 1.00 |" in md


def _write_runs(path, model, texts):
    import json

    path.mkdir(parents=True, exist_ok=True)
    (path / f"{model}.jsonl").write_text(
        "\n".join(json.dumps({"id": "s01", "rep": rep, "sections": {"verdict": t}}, ensure_ascii=False)
                  for rep, t in enumerate(texts)) + "\n", encoding="utf-8")


def test_비교_모드는_두_태그의_회차를_한_묶음에_섞고_mapping은_model_at_tag다(tmp_path):
    from apps.agent.adapter.inbound.cli.benchmark_report import compare_reports
    from apps.agent.adapter.inbound.cli.report_bench_scoring import judge_packets

    _write_runs(tmp_path / "report", "qwen3.5_4b", ["기준선 글", "기준선 2회차"])
    _write_runs(tmp_path / "report-guards", "qwen3.5_4b", ["가드 글"])

    reports = compare_reports(["qwen3.5:4b"], {"base": tmp_path / "report", "guards": tmp_path / "report-guards"})
    packet, mapping = judge_packets("s01", {}, reports["s01"], 0)

    assert set(mapping.values()) == {"qwen3.5:4b@base", "qwen3.5:4b@guards"}
    assert "기준선 글" in packet and "가드 글" in packet and "2회차" not in packet


def test_판정_비교는_model_at_tag별_평균과_짝지은_차이를_낸다():
    from apps.agent.adapter.inbound.cli.benchmark_report import compare_judged

    scores = {
        "m@guards": {"s01": {"faithfulness": 4, "fluency": 4}, "s02": {"faithfulness": 5, "fluency": 3}},
        "m@base": {"s01": {"faithfulness": 3, "fluency": 4}, "s02": {"faithfulness": 3, "fluency": 3}},
    }

    got = compare_judged(scores, "guards", "base")

    assert got["means"]["m@guards"] == {"faithfulness": 4.5, "fluency": 3.5, "n": 2}
    diff = got["diffs"]["m"]
    assert diff["faithfulness"][0] == 1.5 and diff["fluency"][0] == 0.0 and diff["n"] == 2


def test_샘플링_기록이_섞인_캐시는_미기록_회차도_밝힌다():
    from apps.agent.adapter.inbound.cli.benchmark_report import _BASELINE_SAMPLING, sampling_label

    assert sampling_label([{"temperature": 0.0, "seed": 42}, {}]) == f"0.0/42, {_BASELINE_SAMPLING}"


def test_비교_모드_인자가_잘못되면_parser_error로_끝난다(monkeypatch, capsys):
    import sys

    import pytest

    from apps.agent.adapter.inbound.cli import benchmark_report as br

    called = []
    monkeypatch.setitem(br._COMMANDS, "judge-export", lambda args: called.append(args))
    for argv in (["judge-export", "--compare-tag", "base"],
                 ["judge-export", "--cache-tag", "guards", "--compare-tag", "guards", "--models", "m"],
                 ["judge-export", "--compare-tag", "base", "--models", "m"]):  # 태그 없는 캐시 == base
        monkeypatch.setattr(sys, "argv", ["benchmark_report", *argv])
        with pytest.raises(SystemExit):
            br.main()
    assert called == [] and "--models" in capsys.readouterr().err


def test_시나리오_세트_인자가_시나리오_파일과_facts_폴더를_바꾼다(monkeypatch):
    import sys

    from apps.agent.adapter.inbound.cli import benchmark_report as br

    for name in ("_SCENARIOS", "_FACTS_DIR", "_RUNS", "_JUDGE"):  # main이 바꾸는 모듈 경로 — 테스트 뒤 되돌린다
        monkeypatch.setattr(br, name, getattr(br, name))
    seen = []
    monkeypatch.setitem(br._COMMANDS, "score", lambda args: seen.append((br._SCENARIOS.name, br._FACTS_DIR.name)))
    for argv in (["score"], ["score", "--scenario-set", "150"]):
        monkeypatch.setattr(sys, "argv", ["benchmark_report", *argv])
        br.main()
    assert seen == [("report_scenarios.jsonl", "report_facts"), ("report_scenarios_150.jsonl", "report_facts_150")]


def test_회차_기록에_해석_시도와_온도와_seed를_남긴다():
    from types import SimpleNamespace

    from apps.agent.adapter.inbound.cli.benchmark_report import run_record
    from apps.agent.app.ports.output.agent_port import LLMUsage
    from apps.agent.domain.services.report_sampling import REPORT_SEED, REPORT_TEMPERATURE

    attempts = [{"model": "m", "raw": "원문", "removed_sentences": 1, "links_stripped": 0, "contradiction": None}]
    interactor = SimpleNamespace(last_usage=LLMUsage(input_tokens=3, output_tokens=4), last_answer_attempts=attempts)
    row = run_record("s01", 0, {"sections": {"answer": "해석"}}, None, interactor)

    assert (row["temperature"], row["seed"]) == (REPORT_TEMPERATURE, REPORT_SEED)
    assert row["answer_attempts"] == attempts and row["sections"] == {"answer": "해석"}
    assert row["usage"] == {"input_tokens": 3, "output_tokens": 4}
