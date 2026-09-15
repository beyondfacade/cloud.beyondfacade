"""rag_chunk 스키마 — vector(1536) + HNSW 인덱스."""
from sqlalchemy import text
from core.matrix.grid_oracle_database_manager import session_scope

def test_rag_chunk_table_exists_with_vector_1536():
    with session_scope() as s:
        dim = s.execute(text(
            "SELECT atttypmod FROM pg_attribute WHERE attrelid='rag_chunk'::regclass AND attname='embedding'"
        )).scalar()
    assert dim == 1536

def test_rag_chunk_hnsw_index_exists():
    with session_scope() as s:
        n = s.execute(text(
            "SELECT count(*) FROM pg_indexes WHERE tablename='rag_chunk' AND indexdef ILIKE '%hnsw%'"
        )).scalar()
    assert n == 1
