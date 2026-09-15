"""RAG 평가셋 후보 생성 — funding 청크 샘플 → gemma3(Ollama /api/chat)로 자연어 질문 생성.

이미 색인된 rag_chunk(source_type='funding')에서 chunk_id 오름차순 정렬 후 앞 N건을
결정적으로 표본 추출한다(비결정 랜덤 표본 금지 — 재현 가능한 평가셋을 위함). 각 청크의
content를 gemma3:12b에 "이 공고를 찾을 법한 자연어 질문 1개(공고명 복사 금지)" 프롬프트로
보내 질문을 생성하고, status=candidate로 jsonl에 적재한다.

candidate → confirmed 승격은 사용자 검수 몫이며 이 CLI의 범위 밖이다
(backend_ver_log.md v0.19.0 참고).

실행: python -m apps.rag.adapter.inbound.cli.generate_evalset [--limit 50] [--model gemma3:12b]
"""

import argparse
import json
import time
from pathlib import Path

import httpx
from sqlalchemy import select

from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm
from core.matrix.grid_oracle_database_manager import session_scope

# apps/rag/adapter/inbound/cli/generate_evalset.py → parents[6] == 리포지토리 루트
_REPO_ROOT = Path(__file__).resolve().parents[6]

_PROMPT_TEMPLATE = (
    "다음은 정책자금 공고 내용이다. 이 공고를 찾기 위해 사용자가 검색창에 입력할 법한 "
    "자연어 질문을 한국어로 딱 1개만 만들어라. 공고명을 그대로 베끼지 말고, "
    "질문 문장 하나만 출력하라 (다른 설명이나 따옴표 없이).\n\n공고 내용:\n{content}"
)


def _fetch_funding_sample(limit: int) -> list[dict]:
    with session_scope() as session:
        rows = session.execute(
            select(RagChunkOrm.chunk_id, RagChunkOrm.content)
            .where(RagChunkOrm.source_type == "funding")
            .order_by(RagChunkOrm.chunk_id)
            .limit(limit)
        ).all()
        return [{"chunk_id": row.chunk_id, "content": row.content} for row in rows]


def _generate_question(client: httpx.Client, model: str, content: str) -> str:
    response = client.post(
        "/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": _PROMPT_TEMPLATE.format(content=content)}],
            "stream": False,
        },
    )
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _REPO_ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50, help="표본 건수 (기본 50)")
    parser.add_argument("--model", default="gemma3:12b", help="질문 생성 모델")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434", help="Ollama 서버 URL")
    parser.add_argument("--output", default="data/eval/rag_evalset.jsonl")
    args = parser.parse_args()

    sample = _fetch_funding_sample(args.limit)
    output_path = _resolve(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    # 기본 httpx 타임아웃(5s)은 gemma3 응답 생성 시간에 부족 — 케이스당 수 초~수십 초 허용
    with httpx.Client(base_url=args.base_url, timeout=120.0) as client:
        with output_path.open("w", encoding="utf-8") as f:
            for i, chunk in enumerate(sample, start=1):
                question = _generate_question(client, args.model, chunk["content"])
                row = {
                    "question": question,
                    "relevant_ids": [chunk["chunk_id"]],
                    "source_type": "funding",
                    "status": "candidate",
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"[{i}/{len(sample)}] {chunk['chunk_id']} -> {question}", flush=True)

    elapsed = time.monotonic() - started
    print(
        f"generate_evalset: {len(sample)}건 생성 완료 → {output_path} ({elapsed:.1f}초)",
        flush=True,
    )


if __name__ == "__main__":
    main()
