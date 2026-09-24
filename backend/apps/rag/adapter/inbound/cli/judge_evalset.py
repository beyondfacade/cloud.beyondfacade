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

_SYSTEM = """당신은 정책자금 공고 검색(RAG) 평가셋의 검수자다.
평가셋의 한 행은 (질문, 정답 공고) 쌍이다. 검색 엔진이 그 질문으로 그 공고를 상위에 올려야 "맞춘 것"으로 친다.
따라서 질문은 다음을 만족해야 O다:
- 소상공인·중소기업 사용자가 검색창에 실제로 칠 법한 자연어 질문이다 (공고명을 그대로 베낀 것이 아니다).
- 공고의 핵심(대상·지역·분야·지원 내용)과 맞아, 이 공고가 그 질문의 타당한 정답이다.
- 너무 일반적이어서 수십 개 공고가 똑같이 정답이 되는 질문이 아니다 (예: "정부 지원금 있나요?").
그 외(공고와 어긋남·핵심 조건 누락으로 구분 불가·공고명 복사·비문)는 X.
X이거나 O라도 더 좋은 표현이 있으면 better_question에 한 문장으로 제안하고, 없으면 null."""

_USER = """[질문]
{question}

[정답 공고]
제목: {title}
기관: {org}
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

    rows = _load_rows(_REPO_ROOT / args.evalset)
    cards = _fetch_cards([r["relevant_ids"][0].split(":", 1)[1] for r in rows])
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
