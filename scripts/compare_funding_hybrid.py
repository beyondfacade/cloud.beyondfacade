"""공고 후보 3방식 비교 — ① 규칙만(마감 임박 순) ② RAG만(전체 색인 유사도) ③ 하이브리드(규칙 통과분을 질문 유사도로 정렬).

평가셋: data/eval/rag_evalset.jsonl 의 confirmed 질문(정답 공고 1건씩). 개발 DB 읽기 전용, 질문 임베딩은 로컬 Ollama bge-m3.
지표:
- 자격 정답 = 정답 공고가 규칙 필터(서울·전국 ∩ 소상공인·창업 ∩ 미만료)를 통과하는 질문 — 우리 서비스가 보여 줘야 하는 공고.
- Hit@8 · MRR@8 : 자격 정답 질문에서 정답이 상위 8건에 드는가(리포트·화면이 8건을 보여 준다).
- 자격 밖 노출 : 상위 8건 중 규칙을 통과하지 못하는 공고(마감·타 지역·대상 밖) 비율 — 사용자에게 지원 못 하는 공고를 보여 주는 정도.
"""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import text  # noqa: E402

from apps.funding.adapter.outbound.gateways.seoul_district_gateway import SeoulDistrictNamesGateway  # noqa: E402
from apps.funding.adapter.outbound.repositories.funding_program_repository import (  # noqa: E402
    SqlAlchemyFundingProgramRepository,
)
from apps.funding.domain.services.candidates import select_candidates  # noqa: E402
from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case  # noqa: E402
from core.matrix.grid_oracle_database_manager import get_engine  # noqa: E402

K = 8
EVALSET = Path(__file__).resolve().parents[1] / "data" / "eval" / "rag_evalset.jsonl"


def main() -> None:
    questions = [json.loads(line) for line in EVALSET.open()]
    questions = [q for q in questions if q["status"] == "confirmed"]

    programs = SqlAlchemyFundingProgramRepository().list_open_all()
    pool = select_candidates(
        programs, seoul_district_names=SeoulDistrictNamesGateway().names(), today=date.today(), limit=len(programs)
    )
    pool_ids = [f"funding:{c.program.program_id}" for c in pool]  # 규칙 순서(마감 임박 순)
    eligible = set(pool_ids)
    rule_top = pool_ids[:K]

    search = get_rag_search_use_case("bge-m3")
    embedder = search._embedder  # 실험 스크립트 — 같은 임베더로 풀 안을 점수 매긴다
    engine = get_engine()
    with engine.connect() as conn:
        indexed = {r[0] for r in conn.execute(text("select chunk_id from rag_chunk where chunk_id = any(:ids) and embedding is not null"), {"ids": pool_ids})}

    stats = {name: {"hit": 0, "rr": 0.0, "outside": 0, "shown": 0} for name in ("rule", "rag", "hybrid")}
    n_eligible = 0
    for q in questions:
        gold = q["relevant_ids"][0]
        vec = embedder.embed_query(q["question"])
        rag_top = [h.chunk_id for h in search.search(q["question"], top_k=K, source_type="funding")]
        with engine.connect() as conn:
            rows = conn.execute(
                text("select chunk_id from rag_chunk where chunk_id = any(:ids) and embedding is not null "
                     "order by embedding <=> cast(:v as vector) limit :k"),
                {"ids": pool_ids, "v": "[" + ",".join(f"{x:.7f}" for x in vec) + "]", "k": K},
            )
            hybrid_top = [r[0] for r in rows]
        ranked = {"rule": rule_top, "rag": rag_top, "hybrid": hybrid_top}
        for name, top in ranked.items():
            stats[name]["outside"] += sum(1 for cid in top if cid not in eligible)
            stats[name]["shown"] += len(top)
        if gold not in eligible:
            continue
        n_eligible += 1
        for name, top in ranked.items():
            if gold in top:
                stats[name]["hit"] += 1
                stats[name]["rr"] += 1 / (top.index(gold) + 1)

    print(f"confirmed 질문 {len(questions)}개 · 자격 정답 질문 {n_eligible}개 · 규칙 통과 공고 {len(pool_ids)}건(색인됨 {len(indexed)}건)")
    print(f"| 방식 | Hit@{K} (자격 정답 {n_eligible}문항) | MRR@{K} | 자격 밖 노출 (상위 {K}건 중) |")
    print("|---|---|---|---|")
    labels = {"rule": "① 규칙만 (마감 임박 순)", "rag": "② RAG만 (전체 색인)", "hybrid": "③ 하이브리드 (규칙 → 질문 유사도)"}
    for name, s in stats.items():
        hit = s["hit"] / n_eligible if n_eligible else 0
        mrr = s["rr"] / n_eligible if n_eligible else 0
        outside = s["outside"] / s["shown"] if s["shown"] else 0
        print(f"| {labels[name]} | {hit:.3f} ({s['hit']}/{n_eligible}) | {mrr:.3f} | {outside:.1%} |")


if __name__ == "__main__":
    main()
