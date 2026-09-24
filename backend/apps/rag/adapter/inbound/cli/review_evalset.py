"""RAG 평가셋 사람 검수 — markdown 시트 생성 → VS Code에서 판정 → jsonl 반영 (Driving Adapter, CLI).

candidate 질문(gemma3 자동 생성)이 "그 공고를 찾을 법한 질문"인지 사람이 본다. 시트의 각 항목에
  판정: O   ← 적합 → status=confirmed (질문 줄을 고쳤으면 고친 질문으로)
  판정: X   ← 부적합 → status=rejected (evaluate_rag는 confirmed만 본지표로 집계)
  판정:     ← 비움 → candidate 그대로
를 적는다. 판정 뒤 `#`로 메모를 달아도 된다.

실행:
  python -m apps.rag.adapter.inbound.cli.review_evalset sheet   # data/eval/rag_evalset_review.md 생성
  python -m apps.rag.adapter.inbound.cli.review_evalset apply   # 시트 → rag_evalset.jsonl 반영
"""

import argparse
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# apps/rag/adapter/inbound/cli/review_evalset.py → parents[6] == 리포지토리 루트
_REPO_ROOT = Path(__file__).resolve().parents[6]
_EVALSET = "data/eval/rag_evalset.jsonl"
_SHEET = "data/eval/rag_evalset_review.md"

_HEADER = """# RAG 평가셋 검수 시트

각 항목의 **질문**이 아래 **공고**를 찾기 위해 사용자가 실제로 입력할 법한 질문이면 `판정: O`, 아니면 `판정: X`.
질문이 어색하지만 살릴 만하면 **질문 줄을 직접 고치고** `판정: O`. 비워 두면 미검수(candidate)로 남는다.
`판정: X  # 이유` 처럼 `#` 뒤에 메모 가능. 다 적은 뒤:

    cd backend && .venv/bin/python -m apps.rag.adapter.inbound.cli.review_evalset apply

---
"""

_ITEM = """## {n}. {chunk_id}
질문: {question}
공고: **{title}** — {org} · 대상 {target} · {field} · 기간 {period}
> {summary}
> {url}
판정: 

"""

_ID_RE = re.compile(r"^## \d+\. (\S+)\s*$")
_QUESTION_RE = re.compile(r"^질문:\s*(.*?)\s*$")
_VERDICT_RE = re.compile(r"^판정:\s*([^#\s]*)\s*(?:#.*)?$")


@dataclass(frozen=True)
class ProgramCard:
    program_id: str
    title: str
    org: str
    target: str | None
    field: str | None
    period: str
    summary: str | None
    url: str


def render_sheet(rows: list[dict], cards: dict[str, ProgramCard]) -> str:
    items = []
    for n, row in enumerate(rows, start=1):
        chunk_id = row["relevant_ids"][0]
        card = cards[chunk_id.split(":", 1)[1]]
        items.append(
            _ITEM.format(
                n=n,
                chunk_id=chunk_id,
                question=row["question"],
                title=card.title,
                org=card.org,
                target=card.target or "-",
                field=card.field or "-",
                period=card.period,
                summary=(card.summary or "(요약 없음)").replace("\n", " "),
                url=card.url,
            )
        )
    return _HEADER + "".join(items)


def parse_sheet(text: str) -> dict[str, tuple[str | None, str]]:
    """chunk_id → (판정 O/X/None, 시트에 적힌 질문). 판정은 대소문자 무시."""
    verdicts: dict[str, tuple[str | None, str]] = {}
    chunk_id: str | None = None
    question = ""
    for line in text.split("\n"):
        if m := _ID_RE.match(line):
            chunk_id, question = m.group(1), ""
        elif m := _QUESTION_RE.match(line):
            question = m.group(1)
        elif (m := _VERDICT_RE.match(line)) and chunk_id:
            mark = m.group(1).upper() or None
            verdicts[chunk_id] = (mark, question)
            chunk_id = None
    return verdicts


def _confirm(row: dict, question: str) -> dict:
    return {**row, "question": question, "status": "confirmed"}


def _reject(row: dict, question: str) -> dict:
    return {**row, "status": "rejected"}


def _keep(row: dict, question: str) -> dict:
    return dict(row)


# Strategy (GoF) — 판정 기호 → 행 변환. if/elif 대신 테이블 디스패치
_VERDICT_HANDLERS: dict[str | None, Callable[[dict, str], dict]] = {
    "O": _confirm,
    "X": _reject,
    None: _keep,
}


def apply_verdicts(rows: list[dict], verdicts: dict[str, tuple[str | None, str]]) -> list[dict]:
    out = []
    for row in rows:
        chunk_id = row["relevant_ids"][0]
        mark, question = verdicts.get(chunk_id, (None, row["question"]))
        handler = _VERDICT_HANDLERS.get(mark)
        if handler is None:
            raise ValueError(f"{chunk_id}: 판정은 O/X/빈칸만 — '{mark}'")
        out.append(handler(row, question or row["question"]))
    return out


# ── 파일·DB (어댑터 경계) ────────────────────────────────────────────────


def _load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _fetch_cards(program_ids: list[str]) -> dict[str, ProgramCard]:
    from sqlalchemy import select

    from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
    from core.matrix.grid_oracle_database_manager import session_scope

    with session_scope() as session:
        rows = session.execute(
            select(FundingProgramOrm).where(FundingProgramOrm.program_id.in_(program_ids))
        ).scalars()
        return {
            r.program_id: ProgramCard(
                program_id=r.program_id,
                title=r.title,
                org=r.org,
                target=r.target_text,
                field="/".join(x for x in (r.field_category, r.field_subcategory) if x) or None,
                period=r.apply_period,
                summary=r.summary,
                url=r.url,
            )
            for r in rows
        }


def _cmd_sheet(evalset: Path, sheet: Path) -> None:
    rows = _load_rows(evalset)
    cards = _fetch_cards([r["relevant_ids"][0].split(":", 1)[1] for r in rows])
    sheet.write_text(render_sheet(rows, cards), encoding="utf-8")
    print(f"검수 시트 생성: {sheet} ({len(rows)}건) — VS Code에서 판정을 적은 뒤 apply", flush=True)


def _cmd_apply(evalset: Path, sheet: Path) -> None:
    rows = _load_rows(evalset)
    out = apply_verdicts(rows, parse_sheet(sheet.read_text(encoding="utf-8")))
    evalset.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    counts = {s: sum(1 for r in out if r["status"] == s) for s in ("confirmed", "rejected", "candidate")}
    edited = sum(1 for a, b in zip(rows, out) if a["question"] != b["question"])
    print(
        f"반영 완료: confirmed {counts['confirmed']} / rejected {counts['rejected']} / "
        f"candidate {counts['candidate']} (질문 수정 {edited}건) → {evalset}",
        flush=True,
    )


_COMMANDS: dict[str, Callable[[Path, Path], None]] = {"sheet": _cmd_sheet, "apply": _cmd_apply}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=list(_COMMANDS))
    parser.add_argument("--evalset", default=_EVALSET)
    parser.add_argument("--sheet", default=_SHEET)
    args = parser.parse_args()
    _COMMANDS[args.command](_REPO_ROOT / args.evalset, _REPO_ROOT / args.sheet)


if __name__ == "__main__":
    main()
