"""RAG 평가셋 후보 생성 — 색인 청크 표본 → LLM이 "그 문서를 찾을 법한 질문" 1개 생성 (Driving Adapter, CLI).

rag_chunk를 chunk_id 오름차순으로 결정적으로 표본 추출한다(비결정 랜덤 금지 — 재현 가능한 평가셋).
이미 평가셋에 있는 chunk_id는 건너뛰고 뒤에 이어 붙인다(--append 기본). funding은 미만료 공고만 —
검색이 만료 공고를 제외하므로(rag_repository.exclude_expired_funding) 만료 공고는 정답이 될 수 없다.

질문 생성기는 Strategy — ollama(gemma3, 9/15 최초 50건)·claude(Opus 5, 9/24 확장분). 둘 다
status=candidate로 적재하고 승격은 judge_evalset(1차) + 사람 검수(review_evalset) 몫이다.

실행: python -m apps.rag.adapter.inbound.cli.generate_evalset --provider claude --source-type funding --limit 110
어려운 질문(spec 2026-10-04 §3): --hard-kind colloquial|sibling|news_event --limit 20 (claude 전용, subset=hard)
"""

import argparse
import json
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm
from apps.rag.domain.entities.rag_chunk_entity import RagHit
from apps.rag.domain.services.same_event_collapser import same_event
from core.matrix.grid_oracle_database_manager import session_scope

# apps/rag/adapter/inbound/cli/generate_evalset.py → parents[6] == 리포지토리 루트
_REPO_ROOT = Path(__file__).resolve().parents[6]
_EVALSET = "data/eval/rag_evalset.jsonl"

_DOC_LABEL = {"funding": "정책자금 공고", "news": "지역 상권 뉴스 기사"}

_OLLAMA_PROMPT = (
    "다음은 {label} 내용이다. 이 문서를 찾기 위해 사용자가 검색창에 입력할 법한 "
    "자연어 질문을 한국어로 딱 1개만 만들어라. 제목을 그대로 베끼지 말고, "
    "질문 문장 하나만 출력하라 (다른 설명이나 따옴표 없이).\n\n문서 내용:\n{content}"
)

# 판정 기준(judge_evalset._SYSTEM, STATUS §4-4)을 생성 단계에 그대로 건다 — 생성부터 변별력 있는 질문을 노린다
_CLAUDE_SYSTEM = """당신은 정책자금·지역상권 검색(RAG) 평가셋을 만드는 사람이다.
주어진 문서 하나에 대해, 소상공인·중소기업 사용자가 검색창에 실제로 칠 법한 한국어 자연어 질문을 딱 1개 만든다.

질문은 이 기준을 만족해야 한다: **질문에 담긴 정보만으로 이 문서가 다른 유사 문서보다 우선적으로 정답이 되어야 한다.**
- 문서를 다른 유사 문서와 갈라 주는 핵심(지역·대상 조건·지원방식·고유한 사건이나 이름)을 질문에 담는다.
- 통합공고·종합안내 문서라면 "전체 사업을 한눈에", "통합 안내" 의도를 질문에 드러낸다.
- 제목을 그대로 베끼지 않는다. 사용자 말투의 짧은 한 문장(20~45자)으로 쓴다.
- 문서에 없는 사실을 지어내지 않는다.

출력은 질문 문장 하나뿐이다. 따옴표·설명·번호를 붙이지 않는다."""

_HARD_COMMON = """질문은 이 기준을 만족해야 한다: **질문에 담긴 정보만으로 이 문서가 다른 유사 문서보다 우선적으로 정답이 되어야 한다.**
- 문서에 없는 사실을 지어내지 않는다.
- 출력은 질문 문장 하나뿐이다. 따옴표·설명·번호를 붙이지 않는다."""

# 어려운 질문 3종 (spec §3) — 검색 모델의 변별력을 재기 위해 표면 단어 겹침을 일부러 줄인다
_HARD_SYSTEMS = {
    "colloquial": f"""당신은 정책자금 검색(RAG) 평가셋의 어려운 질문을 만드는 사람이다.
가게를 차리려는 사람이 친구에게 묻듯 구어체로 묻는 한국어 질문을 딱 1개 만든다(15~45자).
- 공고 제목·본문의 핵심 단어(사업명·지원방식 명칭·기관명)를 그대로 쓰지 않고 일상어로 바꿔 말한다.
- 그래도 지역·대상 조건·지원 내용은 의미로 담아 이 공고를 가리켜야 한다.
{_HARD_COMMON}""",
    "sibling": f"""당신은 정책자금 검색(RAG) 평가셋의 어려운 질문을 만드는 사람이다.
[정답 문서]와 헷갈리기 쉬운 [유사 문서]가 주어진다. [정답 문서]만 가리키는 한국어 질문을 딱 1개 만든다(20~50자).
- 두 문서를 가르는 조건(대상·지원방식·금액 성격·지역·기간)을 질문에 담는다. [유사 문서]에도 맞는 질문은 실패다.
- 제목을 그대로 베끼지 않는다.
{_HARD_COMMON}""",
    "news_event": f"""당신은 지역 상권 뉴스 검색(RAG) 평가셋의 어려운 질문을 만드는 사람이다.
이 기사가 다룬 사건을 찾는 한국어 질문을 딱 1개 만든다(15~45자).
- 헤드라인의 단어를 그대로 쓰지 않고 사건의 내용(무엇이·어디서·어떻게 됐는지)으로 묻는다.
- 같은 사건을 다룬 다른 언론사 기사도 정답으로 치므로 언론사·기자는 묻지 않는다.
{_HARD_COMMON}""",
}
_HARD_SOURCE = {"colloquial": "funding", "sibling": "funding", "news_event": "news"}


class QuestionGenerator(ABC):
    @abstractmethod
    def generate(self, source_type: str, content: str) -> str: ...


class OllamaGemmaGenerator(QuestionGenerator):
    def __init__(self, base_url: str, model: str) -> None:
        import httpx

        # 기본 httpx 타임아웃(5s)은 gemma3 응답 생성 시간에 부족 — 케이스당 수 초~수십 초 허용
        self._client = httpx.Client(base_url=base_url, timeout=120.0)
        self._model = model

    def generate(self, source_type: str, content: str) -> str:
        response = self._client.post(
            "/api/chat",
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": _OLLAMA_PROMPT.format(
                    label=_DOC_LABEL.get(source_type, "문서"), content=content)}],
                "stream": False,
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"].strip()


class ClaudeGenerator(QuestionGenerator):
    def __init__(self, model: str, system: str = _CLAUDE_SYSTEM) -> None:
        import anthropic

        from core.matrix.grid_keymaker_secret_manager import get_settings

        os.environ.setdefault("ANTHROPIC_API_KEY", get_settings().anthropic_api_key)
        self._client = anthropic.Anthropic()
        self._model = model
        self._system = system

    def generate(self, source_type: str, content: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            output_config={"effort": "low"},
            system=self._system,
            messages=[{"role": "user", "content": f"[{_DOC_LABEL.get(source_type, '문서')}]\n{content}"}],
        )
        if response.stop_reason != "end_turn":
            raise RuntimeError(f"stop_reason={response.stop_reason}")
        return next(b.text for b in response.content if b.type == "text").strip().strip('"“”')


# Factory — provider 문자열 → 생성기. if/elif 대신 테이블
_GENERATORS = {
    "ollama": lambda a: OllamaGemmaGenerator(a.base_url, a.model or "gemma3:12b"),
    "claude": lambda a: ClaudeGenerator(a.model or "claude-opus-5"),
}


def select_new_chunks(chunks: list[dict], existing_ids: set[str], limit: int) -> list[dict]:
    """chunk_id 순서를 지키며 평가셋에 없는 것만 앞에서 limit개."""
    picked = [c for c in chunks if c["chunk_id"] not in existing_ids]
    return picked[:limit]


def build_row(chunk: dict, question: str) -> dict:
    return {
        "question": question,
        "relevant_ids": [chunk["chunk_id"]],
        "source_type": chunk["chunk_id"].split(":", 1)[0],
        "status": "candidate",
    }


_TOKEN = re.compile(r"[가-힣A-Za-z0-9]+")
_SIBLING_MIN_JACCARD = 0.3  # same_event_collapser의 제목 Jaccard 기준과 같은 값


@dataclass(frozen=True)
class HardItem:
    chunk_id: str
    prompt_input: str
    relevant_ids: list[str]


def _title_tokens(content: str) -> set[str]:
    return {t for t in _TOKEN.findall(content.split("\n", 1)[0]) if len(t) >= 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def pick_sibling(chunk: dict, pool: list[dict]) -> dict | None:
    """제목 토큰이 가장 많이 겹치는 다른 공고(임베딩 모델 무관 — spec §3 모델 중립 선정)."""
    target = _title_tokens(chunk["content"])
    scored = [
        (_jaccard(target, _title_tokens(c["content"])), c["chunk_id"], c)
        for c in pool
        if c["chunk_id"] != chunk["chunk_id"]
    ]
    scored = [s for s in scored if s[0] >= _SIBLING_MIN_JACCARD]
    if not scored:
        return None
    return min(scored, key=lambda s: (-s[0], s[1]))[2]


def select_colloquial(chunks: list[dict], existing: set[str], limit: int) -> list[HardItem]:
    return [HardItem(c["chunk_id"], c["content"], [c["chunk_id"]]) for c in select_new_chunks(chunks, existing, limit)]


def select_sibling(chunks: list[dict], existing: set[str], limit: int) -> list[HardItem]:
    items: list[HardItem] = []
    for chunk in select_new_chunks(chunks, existing, len(chunks)):
        sibling = pick_sibling(chunk, chunks)
        if sibling is None:
            continue
        prompt = f"[정답 문서]\n{chunk['content']}\n\n[유사 문서]\n{sibling['content']}"
        items.append(HardItem(chunk["chunk_id"], prompt, [chunk["chunk_id"]]))
        if len(items) == limit:
            break
    return items


def _hit(chunk: dict) -> RagHit:
    return RagHit(
        chunk_id=chunk["chunk_id"], source_type="news", source_id=chunk["chunk_id"].split(":", 1)[1],
        content=chunk["content"], score=0.0, url=None, org=None, published_at=chunk["published_at"],
    )


def select_news_event(chunks: list[dict], existing: set[str], limit: int) -> list[HardItem]:
    """같은 사건 기사(same_event: 제목 Jaccard ≥ 0.3·보도일 ±3일)를 정답 묶음으로. 기존 정답과 겹치는 사건은 건너뛴다."""
    seen = set(existing)
    items: list[HardItem] = []
    for chunk in chunks:
        if chunk["chunk_id"] in seen:
            continue
        target = _hit(chunk)
        cluster = [chunk["chunk_id"]] + sorted(
            c["chunk_id"] for c in chunks if c["chunk_id"] != chunk["chunk_id"] and same_event(target, _hit(c))
        )
        if seen & set(cluster):
            continue
        seen |= set(cluster)
        items.append(HardItem(chunk["chunk_id"], chunk["content"], cluster))
        if len(items) == limit:
            break
    return items


_HARD_SELECTORS = {"colloquial": select_colloquial, "sibling": select_sibling, "news_event": select_news_event}


def build_hard_row(item: HardItem, question: str, kind: str) -> dict:
    return {
        "question": question,
        "relevant_ids": item.relevant_ids,
        "source_type": item.chunk_id.split(":", 1)[0],
        "status": "candidate",
        "subset": "hard",
        "hard_kind": kind,
    }


def _fetch_chunks(source_type: str) -> list[dict]:
    stmt = (
        select(RagChunkOrm.chunk_id, RagChunkOrm.content, RagChunkOrm.published_at)
        .where(RagChunkOrm.source_type == source_type)
        .order_by(RagChunkOrm.chunk_id)
    )
    if source_type == "funding":  # 만료 공고는 검색에서 제외되므로 정답이 될 수 없다
        stmt = stmt.join(FundingProgramOrm, FundingProgramOrm.program_id == RagChunkOrm.source_id).where(
            FundingProgramOrm.is_expired.is_(False)
        )
    with session_scope() as session:
        return [
            {"chunk_id": row.chunk_id, "content": row.content, "published_at": row.published_at}
            for row in session.execute(stmt).all()
        ]


def _existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        json.loads(line)["relevant_ids"][0]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def _all_relevant_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        cid
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for cid in json.loads(line)["relevant_ids"]
    }


def _run_hard(args, output_path: Path) -> None:
    kind = args.hard_kind
    source_type = _HARD_SOURCE[kind]
    items = _HARD_SELECTORS[kind](_fetch_chunks(source_type), _all_relevant_ids(output_path), args.limit)
    generator = ClaudeGenerator(args.model or "claude-opus-5", system=_HARD_SYSTEMS[kind])
    with output_path.open("a", encoding="utf-8") as f:
        for i, item in enumerate(items, start=1):
            question = generator.generate(source_type, item.prompt_input)
            f.write(json.dumps(build_hard_row(item, question, kind), ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i}/{len(items)}] {kind} {item.chunk_id} (정답 {len(item.relevant_ids)}건) -> {question}", flush=True)
    print(f"generate_evalset: hard/{kind} {len(items)}건 추가 → {output_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="claude", choices=list(_GENERATORS))
    parser.add_argument("--model", default=None, help="생성 모델 (기본: ollama=gemma3:12b, claude=claude-opus-5)")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434", help="Ollama 서버 URL")
    parser.add_argument("--source-type", default="funding", choices=list(_DOC_LABEL))
    parser.add_argument("--limit", type=int, default=50, help="추가 건수 (기본 50)")
    parser.add_argument("--output", default=_EVALSET)
    parser.add_argument("--hard-kind", default=None, choices=list(_HARD_SYSTEMS), help="어려운 질문 종류 (claude 전용)")
    args = parser.parse_args()

    output_path = _REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.hard_kind:
        _run_hard(args, output_path)
        return
    sample = select_new_chunks(_fetch_chunks(args.source_type), _existing_ids(output_path), args.limit)
    generator = _GENERATORS[args.provider](args)

    started = time.monotonic()
    with output_path.open("a", encoding="utf-8") as f:
        for i, chunk in enumerate(sample, start=1):
            question = generator.generate(args.source_type, chunk["content"])
            f.write(json.dumps(build_row(chunk, question), ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i}/{len(sample)}] {chunk['chunk_id']} -> {question}", flush=True)

    elapsed = time.monotonic() - started
    print(
        f"generate_evalset: {args.source_type} {len(sample)}건 추가 → {output_path} ({elapsed:.1f}초, provider={args.provider})",
        flush=True,
    )


if __name__ == "__main__":
    main()
