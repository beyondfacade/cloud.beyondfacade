#!/usr/bin/env bash
# 원격 k6용 서버 측 정리 — stage_begin.sh가 출력한 단계 폴더를 받는다.
#   scripts/load/stage_end.sh logs/load/<단계>-<시각>
# 모니터·GPU 기록 종료(PID 파일로만) → 느린 쿼리 상위 20 · API 로그 저장. k6 결과(summary.json·raw.csv.gz·k6.txt)는 원격에서 이 폴더로 복사해 온다.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
OUT=$1
for f in "$OUT/monitor.pid" "$OUT/gpu.pid"; do [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null; rm -f "$f"; done
echo "end $(date '+%F %T')" >> "$OUT/meta.txt"
docker exec beyondfacade-loadtest-db psql -U beyondfacade -d beyondfacade -c "select calls, round(mean_exec_time::numeric,1) mean_ms, round(max_exec_time::numeric,1) max_ms,
  round(total_exec_time::numeric) total_ms, left(regexp_replace(query,'\s+',' ','g'),160) query
  from pg_stat_statements order by total_exec_time desc limit 20" > "$OUT/pg_top.txt" 2>&1
docker logs beyondfacade-loadtest-api > "$OUT/api.log" 2>&1
echo "정리 끝: $OUT"
