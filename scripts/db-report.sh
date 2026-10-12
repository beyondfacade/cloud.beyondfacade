#!/usr/bin/env bash
# DB 비교 보고 — 테이블별 행수 + 벡터 검색 표본(정확 검색 top-5). 로컬과 RDS에서 같은 파일을 돌려 diff한다.
#   DB: psql 연결 문자열 (예: postgresql://user:pw@host:5432/db, 로컬 컨테이너 안이면 postgresql:///beyondfacade?user=beyondfacade)
# scripts/db-restore.sh가 로컬(docker exec)·RDS(복원 Job, ConfigMap)에서 부른다.
set -euo pipefail

q() { psql "$DB" -X -At -v ON_ERROR_STOP=1 -c "$1"; }

echo "== 행수"
for t in $(q "select tablename from pg_tables where schemaname = 'public' order by 1"); do
  printf '%s\t%s\n' "$t" "$(q "select count(*) from \"$t\"")"
done

echo "== 벡터 표본"
# 인덱스(HNSW, 근사)를 끄고 정확 검색 — 같은 데이터면 같은 결과
psql "$DB" -X -At -q -v ON_ERROR_STOP=1 <<'SQL'
SET enable_indexscan = off;
SET enable_bitmapscan = off;
SELECT string_agg(chunk_id, ',' ORDER BY d, chunk_id)
FROM (
  SELECT chunk_id, embedding <=> (SELECT embedding FROM rag_chunk WHERE embedding IS NOT NULL ORDER BY chunk_id LIMIT 1) AS d
  FROM rag_chunk WHERE embedding IS NOT NULL
  ORDER BY d, chunk_id LIMIT 5
) s;
SQL
echo "== 끝"
