"""관문 evaluate — 1회차 기록이 빠진 모델은 요약에서 제외."""

import argparse
import json

from apps.intent.adapter.inbound.cli import benchmark_intent as bi


def _write(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def test_미완료_모델은_요약에서_제외(tmp_path, monkeypatch):
    exp = {"region_name": "a", "industry_id": "b", "budget_krw": None}
    evalset = tmp_path / "evalset.jsonl"
    _write(evalset, [{"id": f"i{n}", "text": "t", "kind": "k", "expected": exp, "status": "confirmed"} for n in (1, 2)])
    cache = tmp_path / "cache"
    cache.mkdir()
    got = {"region_name": "a", "industry_id": "b", "budget_krw": None}
    _write(cache / "gemma4_12b.jsonl", [{"id": f"i{n}", "rep": 0, "ms": 10.0, "got": got} for n in (1, 2)])
    _write(cache / "gemma4_e4b.jsonl", [{"id": "i1", "rep": 0, "ms": 10.0, "got": got}])
    summary = tmp_path / "summary.json"
    monkeypatch.setattr(bi, "_EVALSET", evalset)
    monkeypatch.setattr(bi, "_CACHE", cache)
    monkeypatch.setattr(bi, "_SUMMARY", summary)

    bi._cmd_evaluate(argparse.Namespace())

    out = json.loads(summary.read_text(encoding="utf-8"))
    assert list(out) == ["gemma4:12b"] and out["gemma4:12b"]["per_row_both"] == [1.0, 1.0]
