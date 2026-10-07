#!/usr/bin/env bash
# 원격 k6용 서버 측 준비 (docs/testplanhandoff.md) — k6는 다른 머신에서 돌고, 이 머신은 API·DB만.
#   scripts/load/stage_begin.sh <단계이름>     예: ceiling-remote
# run_stage.sh의 앞부분과 같은 조건: API 재시작(BIND·WORKERS·LLM_MODE 반영) → pg_stat_statements 초기화 → 30초 안정화
# → 모니터(5초)·GPU(2초) 기록 시작. 출력 마지막 줄 = 단계 폴더 경로(stage_end.sh에 넘긴다).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
NAME=$1
OUT="logs/load/$NAME-$(date +%m%d-%H%M)"
mkdir -p "$OUT"
LLM_MODE="${LLM_MODE:-fake}" scripts/load/env.sh api
docker exec beyondfacade-loadtest-db psql -U beyondfacade -d beyondfacade -c "select pg_stat_statements_reset()" >/dev/null
sleep 30
echo "start $(date '+%F %T') stage=$NAME llm_mode=${LLM_MODE:-fake} workers=${WORKERS:-1} bind=${BIND:-127.0.0.1} k6=remote" > "$OUT/meta.txt"
nohup scripts/load/env.sh monitor > "$OUT/monitor.log" 2>&1 < /dev/null &
echo $! > "$OUT/monitor.pid"
nohup nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,power.draw --format=csv -l 2 > "$OUT/gpu.csv" 2>&1 < /dev/null &
echo $! > "$OUT/gpu.pid"
echo "$OUT"
