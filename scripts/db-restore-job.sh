#!/usr/bin/env bash
# 복원 Job 안에서 돈다 (deploy/k8s-jobs/db-restore.yaml) — /work/db.dump(pg_dump -Fc)를 RDS에 복원하고 비교 보고를 찍는다.
#   DATABASE_URL: Secret backend-env의 앱 연결 문자열(postgresql+psycopg://…) — psql용으로 드라이버 표기만 뗀다
set -uo pipefail

export DB="${DATABASE_URL/postgresql+psycopg:/postgresql:}"

echo "== 복원 시작 $(date -Is)"
# --clean --if-exists: 다시 돌려도(전환 때 재복원) 기존 객체를 지우고 덮는다. 소유자·권한은 RDS 마스터 사용자로
pg_restore --no-owner --no-privileges --clean --if-exists --jobs 2 -d "$DB" /work/db.dump
restore_status=$?
echo "== 복원 끝 $(date -Is) 종료 코드 $restore_status"

# pg_restore는 통계를 만들지 않는다 — 안 하면 첫 쿼리들이 느린 계획을 탄다
psql "$DB" -X -q -v ON_ERROR_STOP=1 -c "ANALYZE"
psql "$DB" -X -At -c "select 'pgvector ' || extversion from pg_extension where extname = 'vector'"

bash /scripts/db-report.sh
exit "$restore_status"
