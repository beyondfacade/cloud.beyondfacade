"""RAG 검색 품질 평가 하네스 — Hit@5·MRR (Driving Adapter, CLI).

평가셋 jsonl 1행: {"question": str, "relevant_ids": ["funding:PBLN_..."], "source_type": str,
"status": "candidate"|"confirmed"|"rejected"}.

relevant_ids는 "이 중 아무거나 맞으면 정답"인 동치 집합이다 — 뉴스는 같은 보도자료를 받은 기사가 3~50건이라
(2026-09-24 실측) 사건 단위 다중 정답으로 둔다. 그래서 지표는 Recall(정답 중 몇 개를 찾았나)이 아니라
Hit@k(정답 중 하나라도 top-k에 있나)다. 단일 정답 행에선 둘이 같아 이전 수치와 비교 가능하다.

status=confirmed만 본지표로 집계한다 — candidate는 gemma3가 자동 생성한 미검수 질문이라
품질이 보증되지 않으므로, 전체(confirmed+candidate) 수치는 "(참고)" 라벨로만 표시한다.
confirmed 승격은 사용자 검수 몫(이 CLI의 범위 밖 — backend_ver_log.md v0.19.0 참고).

provider는 검색(query) 임베더만 스왑한다(색인은 이미 완료된 벡터를 그대로 검색) —
dependencies의 레지스트리(get_rag_search_use_case)를 재사용해 어댑터 구성을 중복하지 않는다.

실행: python -m apps.rag.adapter.inbound.cli.evaluate_rag \
      --evalset data/eval/rag_evalset.jsonl --provider ollama|fp16|gemini
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case

# apps/rag/adapter/inbound/cli/evaluate_rag.py → parents[6] == 리포지토리 루트
# (data/eval/은 backend/ 밖 repo-root 디렉터리 — CLI를 backend/에서 실행해도 경로가 맞아야 한다)
_REPO_ROOT = Path(__file__).resolve().parents[6]
_TOP_K = 5


def hit_at_k(relevant: set[str], ranked: list[str], k: int = 5) -> float:
    """상위 k개 안에 relevant(동치 집합) 중 하나라도 있으면 1.0, 없으면 0.0. relevant가 비면 0.0."""
    return 1.0 if set(ranked[:k]) & relevant else 0.0


def mrr(relevant: set[str], ranked: list[str]) -> float:
    """첫 적중 순위의 역수(Reciprocal Rank). 랭킹 전체에서 적중이 없으면 0.0."""
    for rank, chunk_id in enumerate(ranked, start=1):
        if chunk_id in relevant:
            return 1.0 / rank
    return 0.0


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _REPO_ROOT / path


def _load_evalset(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _evaluate_rows(rows: list[dict], search_use_case) -> list[dict]:
    results = []
    for row in rows:
        relevant = set(row["relevant_ids"])
        hits = search_use_case.search(
            row["question"], top_k=_TOP_K, source_type=row.get("source_type")
        )
        ranked = [hit.chunk_id for hit in hits]
        results.append(
            {
                "question": row["question"],
                "status": row["status"],
                "hit_at_5": hit_at_k(relevant, ranked, _TOP_K),
                "mrr": mrr(relevant, ranked),
            }
        )
    return results


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evalset", default="data/eval/rag_evalset.jsonl")
    parser.add_argument(
        "--provider", default="ollama", choices=["ollama", "fp16", "gemini"]
    )
    args = parser.parse_args()

    evalset_path = _resolve(args.evalset)
    rows = _load_evalset(evalset_path)

    search_use_case = get_rag_search_use_case(provider=args.provider)
    per_row = _evaluate_rows(rows, search_use_case)

    confirmed = [r for r in per_row if r["status"] == "confirmed"]
    confirmed_hit = _mean([r["hit_at_5"] for r in confirmed])
    confirmed_mrr = _mean([r["mrr"] for r in confirmed])
    reference_hit = _mean([r["hit_at_5"] for r in per_row])
    reference_mrr = _mean([r["mrr"] for r in per_row])

    print(
        f"rag evaluate: evalset={evalset_path.name} provider={args.provider} "
        f"총 {len(rows)}건 (confirmed {len(confirmed)} / candidate {len(rows) - len(confirmed)})",
        flush=True,
    )
    if confirmed:
        print(
            f"[본지표] confirmed {len(confirmed)}건 — "
            f"Hit@5: {confirmed_hit:.3f}, MRR: {confirmed_mrr:.3f}",
            flush=True,
        )
    else:
        print("[본지표] confirmed 0건 — 평가 불가 (사용자 검수 후 승격 대기)", flush=True)
    print(
        f"(참고) 전체(confirmed+candidate) {len(per_row)}건 — "
        f"Hit@5: {reference_hit:.3f}, MRR: {reference_mrr:.3f}",
        flush=True,
    )

    results_dir = _resolve("data/eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = results_dir / f"rag_{args.provider}_{timestamp}.json"
    out_path.write_text(
        json.dumps(
            {
                "provider": args.provider,
                "evalset": str(evalset_path),
                "timestamp": timestamp,
                "total": len(rows),
                "confirmed_count": len(confirmed),
                "candidate_count": len(rows) - len(confirmed),
                "confirmed_metrics": (
                    {"hit_at_5": confirmed_hit, "mrr": confirmed_mrr} if confirmed else None
                ),
                "reference_metrics_all_rows": {
                    "hit_at_5": reference_hit,
                    "mrr": reference_mrr,
                },
                "per_row": per_row,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"결과 저장: {out_path}", flush=True)


if __name__ == "__main__":
    main()
