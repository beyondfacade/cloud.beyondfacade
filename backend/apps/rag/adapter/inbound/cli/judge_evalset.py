"""RAG 평가셋 Claude 1차 판정 — candidate 질문이 공고를 찾을 법한지 Claude가 O/X를 매겨 검수 시트에 기입 (Driving Adapter, CLI).

사람 검수(review_evalset)의 앞단이다. 결과는 jsonl이 아니라 `rag_evalset_review.md`의 판정란에
`판정: O  # claude: 이유 | 제안: 더 나은 질문` 형태로 들어가므로, 사람이 시트에서 뒤집은 뒤 `review_evalset apply`
로 반영한다. 질문 줄은 건드리지 않는다(제안은 메모로만).

키: backend/.env 의 ANTHROPIC_API_KEY (Settings가 읽어 os.environ 으로 넘긴다).
실행: python -m apps.rag.adapter.inbound.cli.judge_evalset [--model claude-opus-5] [--workers 5]
"""

import argparse
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from apps.rag.adapter.inbound.cli.review_evalset import (
    ProgramCard,
    _fetch_cards,
    _load_rows,
)

_REPO_ROOT = Path(__file__).resolve().parents[6]
_EVALSET = "data/eval/rag_evalset.jsonl"
_SHEET = "data/eval/rag_evalset_review.md"

# 판정 기준은 하나다(2026-09-24 사람 검수에서 확정, STATUS §4-4). 통합공고·분야별 예외를 두면 같은 성격의 행이
# O/X로 갈려 불일치가 난다 — 1차 판정 50건 중 10건이 그 이유로 뒤집혔다.
_SYSTEM = """당신은 정책자금 공고·지역상권 뉴스 검색(RAG) 평가셋의 검수자다.
평가셋의 한 행은 (질문, 정답 문서) 쌍이다. 문서는 공고 또는 기사다. 검색 엔진이 그 질문으로 그 문서를 상위에 올려야 "맞춘 것"으로 친다.

판정 기준은 하나다:
- 질문에 담긴 정보만으로 이 문서가 다른 유사 문서보다 **우선적으로** 정답이 될 수 있으면 O.
- 같은 질문에 여러 문서가 자연스럽게 정답이 될 수 있으면 X (같은 사건을 다룬 다른 언론사 기사가 여럿이어도 X).

기준을 적용할 때:
- 통합공고도 예외가 아니다. 질문에 "전체 사업을 한눈에", "통합 안내" 같은 의도가 드러날 때만 O. 분야만 말하면
  그 분야의 개별 공고들과 경합하므로 X.
- 공고의 핵심이 지원방식(전문가 상담·멘토링·인증·지정 등)이면 질문에 그 방식이 담겨야 한다. 분야·지역만 말하면 X.
- 대상 조건(규모·업종·상태)이 공고를 가르는 핵심이면 질문에 담겨야 한다.
- 제목을 그대로 베낀 것, 문서 내용과 어긋나는 것, 비문은 X.
- 소상공인·중소기업 사용자가 검색창에 실제로 칠 법한 자연어여야 한다.

X이거나 O라도 변별력을 높일 표현이 있으면 better_question에 한 문장으로 제안하고, 없으면 null."""

_USER = """[질문]
{question}

[정답 문서]
제목: {title}
기관/언론사: {org}
대상: {target}
분야: {field}
기간: {period}
요약: {summary}"""


class Judgment(BaseModel):
    verdict: Literal["O", "X"]
    reason: str
    better_question: str | None = None


@dataclass(frozen=True)
class _Item:
    chunk_id: str
    question: str
    card: ProgramCard


_VERDICT_LINE = re.compile(r"^판정:.*$")


def pending_rows(rows: list[dict]) -> list[dict]:
    """아직 판정이 없는 행만 — confirmed·rejected는 사람이 확정한 것이라 다시 묻지 않는다."""
    return [r for r in rows if r["status"] == "candidate"]


def annotate_sheet(sheet: str, judgments: dict[str, Judgment]) -> str:
    """항목별 `판정:` 줄을 Claude 판정으로 채운다. 판정이 없는 항목은 그대로, 헤더는 손대지 않는다."""
    id_re = re.compile(r"^## \d+\. (\S+)\s*$")
    out, chunk_id = [], None
    for line in sheet.split("\n"):
        if m := id_re.match(line):
            chunk_id = m.group(1)
        elif chunk_id and _VERDICT_LINE.match(line) and chunk_id in judgments:
            j = judgments[chunk_id]
            memo = f"claude: {j.reason}" + (f" | 제안: {j.better_question}" if j.better_question else "")
            line = f"판정: {j.verdict}  # {memo}"
            chunk_id = None
        out.append(line)
    return "\n".join(out)


def _judge(client, model: str, item: _Item) -> Judgment:
    c = item.card
    response = client.messages.parse(
        model=model,
        max_tokens=2048,
        output_config={"effort": "low"},
        system=_SYSTEM,
        messages=[{"role": "user", "content": _USER.format(
            question=item.question, title=c.title, org=c.org, target=c.target or "-",
            field=c.field or "-", period=c.period, summary=(c.summary or "(요약 없음)").replace("\n", " "),
        )}],
        output_format=Judgment,
    )
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        raise RuntimeError(f"{item.chunk_id}: stop_reason={response.stop_reason}")
    return response.parsed_output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-opus-5")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--evalset", default=_EVALSET)
    parser.add_argument("--sheet", default=_SHEET)
    args = parser.parse_args()

    import anthropic

    from core.matrix.grid_keymaker_secret_manager import get_settings

    os.environ.setdefault("ANTHROPIC_API_KEY", get_settings().anthropic_api_key)
    client = anthropic.Anthropic()

    rows = pending_rows(_load_rows(_REPO_ROOT / args.evalset))
    cards = _fetch_cards([r["relevant_ids"][0] for r in rows])
    items = [_Item(r["relevant_ids"][0], r["question"], cards[r["relevant_ids"][0].split(":", 1)[1]]) for r in rows]

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        judgments = dict(zip((i.chunk_id for i in items), pool.map(lambda i: _judge(client, args.model, i), items)))

    sheet_path = _REPO_ROOT / args.sheet
    sheet_path.write_text(annotate_sheet(sheet_path.read_text(encoding="utf-8"), judgments), encoding="utf-8")
    o = sum(1 for j in judgments.values() if j.verdict == "O")
    print(f"claude 판정 {len(judgments)}건 → O {o} / X {len(judgments) - o} → {sheet_path}", flush=True)
    for item in items:
        j = judgments[item.chunk_id]
        print(f"  [{j.verdict}] {item.question}  — {j.reason}" + (f"  → {j.better_question}" if j.better_question else ""))


if __name__ == "__main__":
    main()
