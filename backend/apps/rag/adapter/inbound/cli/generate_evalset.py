"""RAG 평가셋 후보 생성 — 색인 청크 표본 → LLM이 "그 문서를 찾을 법한 질문" 1개 생성 (Driving Adapter, CLI).

rag_chunk를 chunk_id 오름차순으로 결정적으로 표본 추출한다(비결정 랜덤 금지 — 재현 가능한 평가셋).
이미 평가셋에 있는 chunk_id는 건너뛰고 뒤에 이어 붙인다(--append 기본). funding은 미만료 공고만 —
검색이 만료 공고를 제외하므로(rag_repository.exclude_expired_funding) 만료 공고는 정답이 될 수 없다.

질문 생성기는 Strategy — ollama(gemma3, 9/15 최초 50건)·claude(Opus 5, 9/24 확장분). 둘 다
status=candidate로 적재하고 승격은 judge_evalset(1차) + 사람 검수(review_evalset) 몫이다.

실행: python -m apps.rag.adapter.inbound.cli.generate_evalset --provider claude --source-type funding --limit 110
"""

import argparse
import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path

from sqlalchemy import select

from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm
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
    def __init__(self, model: str) -> None:
        import anthropic

        from core.matrix.grid_keymaker_secret_manager import get_settings

        os.environ.setdefault("ANTHROPIC_API_KEY", get_settings().anthropic_api_key)
        self._client = anthropic.Anthropic()
        self._model = model

    def generate(self, source_type: str, content: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            output_config={"effort": "low"},
            system=_CLAUDE_SYSTEM,
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


def _fetch_chunks(source_type: str) -> list[dict]:
    stmt = (
        select(RagChunkOrm.chunk_id, RagChunkOrm.content)
        .where(RagChunkOrm.source_type == source_type)
        .order_by(RagChunkOrm.chunk_id)
    )
    if source_type == "funding":  # 만료 공고는 검색에서 제외되므로 정답이 될 수 없다
        stmt = stmt.join(FundingProgramOrm, FundingProgramOrm.program_id == RagChunkOrm.source_id).where(
            FundingProgramOrm.is_expired.is_(False)
        )
    with session_scope() as session:
        return [{"chunk_id": row.chunk_id, "content": row.content} for row in session.execute(stmt).all()]


def _existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        json.loads(line)["relevant_ids"][0]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="claude", choices=list(_GENERATORS))
    parser.add_argument("--model", default=None, help="생성 모델 (기본: ollama=gemma3:12b, claude=claude-opus-5)")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434", help="Ollama 서버 URL")
    parser.add_argument("--source-type", default="funding", choices=list(_DOC_LABEL))
    parser.add_argument("--limit", type=int, default=50, help="추가 건수 (기본 50)")
    parser.add_argument("--output", default=_EVALSET)
    args = parser.parse_args()

    output_path = _REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
