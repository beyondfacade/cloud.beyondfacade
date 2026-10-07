#!/usr/bin/env bash
# 부하 테스트 전용 환경 (testplan §7). 운영 8200·개발 8201과 개발 DB(5434)는 건드리지 않는다.
#   scripts/load/env.sh up       테스트 DB(5437, 개발 DB 복제·pg_stat_statements) + 테스트 API(8202, LLM_MODE=fake) 띄우기
#   scripts/load/env.sh api      API 이미지만 다시 빌드·재시작 (설정 하나 바꿔 다시 잴 때, §6 "한 번에 하나만")
#   scripts/load/env.sh monitor  5초마다 CPU·메모리·DB 연결 상태를 logs/load/monitor-<시각>.csv에 기록 (Ctrl+C로 종료)
#   scripts/load/env.sh k6 <스크립트> [-e K=V ...]   k6를 도커로 실행 (k6 전용 코어, 요약 JSON은 logs/load/)
#   scripts/load/env.sh down     테스트 컨테이너 둘 다 지우기
# 실제 Gemini를 쓰는 ⑦ 트랙만 LLM_MODE=live scripts/load/env.sh api 로 바꿔 띄운다(요금 발생).
# NOFILE=65536 이면 API 컨테이너의 열린 파일(소켓) 한도를 올린다 — 기본은 도커 기본값 1,024(운영 8200과 같음).
# WORKERS=4 이면 API를 uvicorn 워커 4개로 띄운다(WEB_CONCURRENCY) — 기본 1 = 1~3차와 같은 조건.
# BIND=100.126.91.1 이면 테스트 API를 그 주소(Tailscale)로 연다 — 원격 k6용(docs/testplanhandoff.md). 기본 127.0.0.1(이 머신에서만).
# CPU 나누기(12코어): API 0-3 · 테스트 DB 4-7 · k6 8-11 — 서로 CPU를 뺏어 결과가 흔들리지 않게.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEV_DB=beyondfacade-db
DB=beyondfacade-loadtest-db
API=beyondfacade-loadtest-api
IMAGE=beyondfacade-api:loadtest
NET=beyondfacade-loadtest
PG_USER=beyondfacade
PG_DB=beyondfacade
LOG_DIR="$ROOT/logs/load"
mkdir -p "$LOG_DIR"

psql_test() { docker exec "$DB" psql -U "$PG_USER" -d "$PG_DB" -Atc "$1"; }

db_up() {
  if docker ps -a --format '{{.Names}}' | grep -qx "$DB"; then
    docker start "$DB" >/dev/null
    echo "테스트 DB 재사용: $DB"
    return
  fi
  docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null
  docker run -d --name "$DB" --network "$NET" --cpuset-cpus 4-7 \
    -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_USER" -e POSTGRES_DB="$PG_DB" \
    -p 127.0.0.1:5437:5432 pgvector/pgvector:pg17 \
    -c shared_preload_libraries=pg_stat_statements >/dev/null
  until docker exec "$DB" pg_isready -U "$PG_USER" -d "$PG_DB" -q; do sleep 1; done
  sleep 2
  echo "개발 DB → 테스트 DB 복제 중 (약 3GB, 몇 분)…"
  docker exec "$DEV_DB" pg_dump -U "$PG_USER" -Fc "$PG_DB" \
    | docker exec -i "$DB" pg_restore -U "$PG_USER" -d "$PG_DB" --no-owner
  psql_test "CREATE EXTENSION IF NOT EXISTS pg_stat_statements" >/dev/null
  psql_test "ANALYZE" >/dev/null
  echo "테스트 DB 준비: $(psql_test "select pg_size_pretty(pg_database_size(current_database()))")"
}

api_up() {
  docker build -q -t "$IMAGE" "$ROOT/backend" >/dev/null
  docker rm -f "$API" >/dev/null 2>&1 || true
  docker run -d --name "$API" --network "$NET" --cpuset-cpus 0-3 \
    --env-file "$ROOT/backend/.env" \
    -e DATABASE_URL="postgresql+psycopg://$PG_USER:$PG_USER@$DB:5432/$PG_DB" \
    -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    -e LLM_MODE="${LLM_MODE:-fake}" \
    -e WEB_CONCURRENCY="${WORKERS:-1}" \
    ${NOFILE:+--ulimit nofile=$NOFILE:$NOFILE} \
    --add-host host.docker.internal:host-gateway \
    -v "$(readlink -f "$ROOT/data/geojson")":/data/geojson:ro \
    -p "${BIND:-127.0.0.1}":8202:8000 "$IMAGE" >/dev/null
  until curl -sf "http://${BIND:-127.0.0.1}:8202/health" >/dev/null; do sleep 1; done
  echo "테스트 API: http://${BIND:-127.0.0.1}:8202 (LLM_MODE=${LLM_MODE:-fake}, 워커 ${WORKERS:-1}개, 열린 파일 한도 $(docker exec "$API" sh -c 'ulimit -Sn'))"
}

monitor() {
  local out="$LOG_DIR/monitor-$(date +%m%d-%H%M%S).csv"
  echo "time,api_cpu,api_mem,db_cpu,db_mem,db_active,db_idle,db_waiting_lock" > "$out"
  echo "기록 중: $out (Ctrl+C로 종료)"
  while true; do
    local stats conn
    stats=$(docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' "$API" "$DB" \
      | awk '{print $2","$3}' | paste -sd, -)
    conn=$(psql_test "select count(*) filter (where state='active'), count(*) filter (where state='idle'),
      count(*) filter (where wait_event_type='Lock') from pg_stat_activity where datname='$PG_DB'" | tr '|' ',')
    echo "$(date +%H:%M:%S),$stats,$conn" | tee -a "$out"
    sleep 5
  done
}

run_k6() {
  local script="$1"; shift
  local stamp; stamp=$(date +%m%d-%H%M%S)
  docker run --rm --network host --cpuset-cpus 8-11 -u "$(id -u):$(id -g)" \
    -v "$ROOT:/w" -w /w grafana/k6 run "$@" \
    --summary-export "logs/load/summary-$(basename "$script" .js)-$stamp.json" "$script"
}

case "${1:-}" in
  up) db_up; api_up ;;
  api) api_up ;;
  monitor) monitor ;;
  k6) shift; run_k6 "$@" ;;
  down) docker rm -f "$API" "$DB" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; echo "테스트 컨테이너 삭제" ;;
  *) sed -n '2,9p' "$0"; exit 1 ;;
esac
