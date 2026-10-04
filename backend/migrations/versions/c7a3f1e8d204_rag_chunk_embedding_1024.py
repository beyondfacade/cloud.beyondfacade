"""rag_chunk embedding 1536 -> 1024 (bge-m3 운영 전환)

차원이 달라 기존 벡터는 변환할 수 없다. 그래서 embedding을 NULL로, embedded_by도 NULL로
비운다 — 적용 후 반드시 `build_rag_index --full`로 전량 재색인해야 검색이 동작한다.
(근거: data/eval/results/embedding-benchmark-2026-10-04/report.md)

Revision ID: c7a3f1e8d204
Revises: b5e9d2c4a817
Create Date: 2026-10-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c7a3f1e8d204'
down_revision: Union[str, Sequence[str], None] = 'b5e9d2c4a817'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _retype_embedding(dim: int) -> None:
    """HNSW 인덱스 drop → 컬럼 차원 변경(기존 벡터 폐기) → 모델 표식 비움 → 인덱스 재생성."""
    op.execute("DROP INDEX IF EXISTS ix_rag_chunk_embedding_hnsw")
    op.execute(f"ALTER TABLE rag_chunk ALTER COLUMN embedding TYPE vector({dim}) USING NULL")
    op.execute("UPDATE rag_chunk SET embedded_by = NULL")
    op.execute("CREATE INDEX ix_rag_chunk_embedding_hnsw ON rag_chunk USING hnsw (embedding vector_cosine_ops)")


def upgrade() -> None:
    """Upgrade schema."""
    _retype_embedding(1024)


def downgrade() -> None:
    """Downgrade schema. 벡터는 복원되지 않는다(NULL) — 이전 모델로 전량 재색인 필요."""
    _retype_embedding(1536)
