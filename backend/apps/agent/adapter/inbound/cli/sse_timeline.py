"""SSE 타임라인 측정 CLI — 이벤트가 **언제** 도착하는지 초 단위로 찍는다 (설계서 §6).

실행:
  cd backend && .venv/bin/python -m apps.agent.adapter.inbound.cli.sse_timeline \
      --base http://127.0.0.1:8201 --region 1168064000 --industry korean_food [--budget 50000000]

프론트(3200) 경유가 아니라 백엔드에 바로 붙는다 — 프록시 버퍼링을 빼고 서버 자체의 도달 시각만
본다. 화면이 느린지 서버가 느린지 가르는 데 쓴다.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Iterator

import httpx

# 이벤트 종류별 꼬리 표기 — if/elif 대신 테이블 디스패치 (CLAUDE.md §5)
_TAIL = {
    "agent_status": lambda payload: f"{payload.get('agent')}/{payload.get('status')}",
    "tool_call": lambda payload: f"{payload.get('agent')}/{payload.get('tool')}",
    "report_delta": lambda payload: str(payload.get("section")),
    "facts": lambda payload: f"{len(json.dumps(payload.get('facts') or {}, ensure_ascii=False))}자",
    "report_done": lambda payload: f"인용 {len(payload.get('citations') or [])}건",
}

# 요약 행 — (마크 키, 라벨, §6 목표 초)
_SUMMARY_ROWS = (
    ("first", "첫 이벤트", 0.2),
    ("facts", "facts", 0.7),
    ("report_delta", "첫 report_delta", 4.0),
    ("report_done", "report_done", 20.0),
)


def format_line(elapsed: float, event_type: str, payload: dict) -> str:
    """`+t.s event 꼬리` 한 줄."""
    tail = _TAIL.get(event_type, lambda payload: "")(payload)
    return f"+{elapsed:6.2f}s {event_type:<13} {tail}".rstrip()


def summary_lines(marks: dict[str, float], chars: int, deltas: int) -> list[str]:
    """§6 목표 대비 요약 — 도달하지 않은 이벤트는 '—'."""
    lines = ["", "--- 요약 (설계서 §6 목표) ---"]
    for key, label, target in _SUMMARY_ROWS:
        at = marks.get(key)
        if at is None:
            lines.append(f"{label}: — (도달 안 함)")
            continue
        lines.append(f"{label}: {at:.2f}s (목표 {target:.1f}s, {'OK' if at <= target else 'NG'})")
    lines.append(f"리포트: 조각 {deltas}개 · {chars}자")
    return lines


def _events(client: httpx.Client, base: str, analysis_id: str) -> Iterator[dict]:
    """SSE 프레임(`event:`/`data:`/빈 줄)을 payload dict로 푼다."""
    with client.stream("GET", f"{base}/analysis/{analysis_id}/events") as response:
        response.raise_for_status()
        data: list[str] = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data.append(line[len("data: ") :])
            elif not line.strip() and data:
                yield json.loads("\n".join(data))
                data = []
        if data:
            yield json.loads("\n".join(data))


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="분석 SSE 타임라인 측정")
    parser.add_argument("--base", default="http://127.0.0.1:8201", help="백엔드 베이스 URL")
    parser.add_argument("--region", required=True, help="행정동 코드")
    parser.add_argument("--industry", required=True, help="업종 ID")
    parser.add_argument("--budget", type=int, default=None, help="세션 예산(원)")
    parser.add_argument("--question", default=None, help="사용자 질문")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    body = {"region": args.region, "industry": args.industry}
    if args.question:
        body["question"] = args.question
    if args.budget is not None:
        body["budget"] = args.budget

    marks: dict[str, float] = {}
    chars = 0
    deltas = 0
    with httpx.Client(timeout=600.0) as client:
        started = time.monotonic()
        analysis_id = client.post(f"{args.base}/analysis", json=body).json()["analysis_id"]
        for payload in _events(client, args.base, analysis_id):
            elapsed = time.monotonic() - started
            event_type = str(payload.get("type") or "?")
            print(format_line(elapsed, event_type, payload), flush=True)
            marks.setdefault("first", elapsed)
            marks.setdefault(event_type, elapsed)
            if event_type == "report_delta":
                deltas += 1
                chars += len(payload.get("markdown") or "")

    for line in summary_lines(marks, chars, deltas):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
