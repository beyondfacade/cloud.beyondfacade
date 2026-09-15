"""RAG 색인 배치 러너 (Driving Adapter, CLI).

- 증분(기본): source_type별 existing_ids에 없는 신규 청크만 재임베딩
- --full: 전량 재색인 (임베딩 모델 교체 등으로 재계산이 필요할 때 사용)
- --provider {fp16|ollama|gemini}: 색인 임베더 선택 (기본 fp16 — 로컬 GPU, 새벽 배치)

실행: python -m apps.rag.adapter.inbound.cli.build_rag_index [--full] [--provider fp16|ollama|gemini]
"""

import argparse
import time

from apps.rag.dependencies.rag_dependencies import get_rag_index_use_case


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="전량 재색인 (기본: 증분)")
    parser.add_argument(
        "--provider",
        default="fp16",
        choices=["fp16", "ollama", "gemini"],
        help="색인 임베더 (기본: fp16)",
    )
    args = parser.parse_args()

    started = time.monotonic()
    processed = get_rag_index_use_case(provider=args.provider).index(full=args.full)
    elapsed = time.monotonic() - started

    mode = "전량" if args.full else "증분"
    print(
        f"rag indexer: {mode} 색인 {processed}건 처리 (provider={args.provider}, {elapsed:.1f}초)",
        flush=True,
    )


if __name__ == "__main__":
    main()
