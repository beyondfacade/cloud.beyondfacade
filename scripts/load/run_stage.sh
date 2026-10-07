#!/usr/bin/env bash
# 혼합 부하 한 단계를 같은 조건으로 실행 (testplan §4 ③~⑦) — 결과는 logs/load/<profile>-<시각>/ 한 폴더에
#   scripts/load/run_stage.sh <PROFILE> [k6 -e 인자...]      LLM_MODE=live|fake(기본 fake)로 API 모드, NOFILE=65536으로 파일 한도 선택
# 조건 고정: API 컨테이너 재시작(메모리 비움) → pg_stat_statements 초기화 → 30초 안정화 → monitor + k6
# 끝나면 느린 쿼리 상위 20·API 로그를 같은 폴더에 남긴다.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PROFILE=$1; shift
OUT="logs/load/$PROFILE${NOFILE:+-nofile$NOFILE}-$(date +%m%d-%H%M)"
mkdir -p "$OUT"
psql_test() { docker exec beyondfacade-loadtest-db psql -U beyondfacade -d beyondfacade -c "$1"; }

LLM_MODE="${LLM_MODE:-fake}" scripts/load/env.sh api
psql_test "select pg_stat_statements_reset()" >/dev/null
sleep 30
echo "start $(date '+%F %T') profile=$PROFILE llm_mode=${LLM_MODE:-fake} nofile=$(docker exec beyondfacade-loadtest-api sh -c 'ulimit -Sn') args=$*" > "$OUT/meta.txt"
scripts/load/env.sh monitor > "$OUT/monitor.log" 2>&1 &
MON=$!
docker run --rm --network host --cpuset-cpus 8-11 -u "$(id -u):$(id -g)" -v "$ROOT:/w" -w /w grafana/k6 run \
  -e PROFILE="$PROFILE" "$@" --summary-export "$OUT/summary.json" --out "csv=$OUT/raw.csv.gz" \
  scripts/load/load.js > "$OUT/k6.txt" 2>&1
CODE=$?
kill $MON; wait $MON 2>/dev/null
echo "end $(date '+%F %T') k6_exit=$CODE" >> "$OUT/meta.txt"
psql_test "select calls, round(mean_exec_time::numeric,1) mean_ms, round(max_exec_time::numeric,1) max_ms,
  round(total_exec_time::numeric) total_ms, left(regexp_replace(query,'\s+',' ','g'),160) query
  from pg_stat_statements order by total_exec_time desc limit 20" > "$OUT/pg_top.txt" 2>&1
docker logs beyondfacade-loadtest-api > "$OUT/api.log" 2>&1
echo "$OUT k6_exit=$CODE"
