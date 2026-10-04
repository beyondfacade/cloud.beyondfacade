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
