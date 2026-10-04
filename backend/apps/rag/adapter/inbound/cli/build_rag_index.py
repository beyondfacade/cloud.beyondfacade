"""RAG 색인 배치 러너 (Driving Adapter, CLI).

- 증분(기본): source_type별 existing_ids에 없는 신규 청크만 재임베딩
- --full: 전량 재색인 (임베딩 모델 교체 등으로 재계산이 필요할 때 사용)
- --provider: 색인 임베더 선택 (운영 레지스트리 키, 기본 bge-m3 — Ollama, 1024차원)

실행: python -m apps.rag.adapter.inbound.cli.build_rag_index [--full] [--provider bge-m3]
"""

import argparse
import time

from apps.rag.dependencies.rag_dependencies import INDEX_PROVIDERS, get_rag_index_use_case


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="전량 재색인 (기본: 증분)")
    parser.add_argument(
        "--provider",
        default="bge-m3",
        choices=INDEX_PROVIDERS,
        help="색인 임베더 (기본: bge-m3)",
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
