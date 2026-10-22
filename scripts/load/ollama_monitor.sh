#!/usr/bin/env bash
# 부하 테스트 중 임베딩 서버(Ollama) 기록 — aws.sh의 monitor는 API 파드만 본다 (11-4에서 즉석으로 쓰던 것, 12차부터 GPU 열 추가)
#   scripts/load/ollama_monitor.sh <출력 csv> [초, 기본 3000]
# 15초마다: Ollama 파드 CPU·메모리 합, 그 15초 동안 /api/embed 성공(200)·취소(4xx — API가 5초에 포기) 수와 성공 지연 중앙값,
# GPU 사용률·메모리(GPU 파드가 있을 때), 노드 수. aws.sh stage와 같은 시간에 따로 띄운다
set -uo pipefail
NS=beyondfacade
out=$1
end=$(( $(date +%s) + ${2:-3000} ))
echo "time,cpu_m,mem_mi,embed_200,embed_4xx,embed_p50_s,gpu_util_pct,gpu_mem_mib,nodes" > "$out"
while [ "$(date +%s)" -lt "$end" ]; do
  top=$(kubectl -n "$NS" top pods -l app=ollama --no-headers 2>/dev/null | awk '{c+=$2; m+=$3} END {print c+0","m+0}')
  log=$(kubectl -n "$NS" logs -l app=ollama --since=15s --tail=-1 2>/dev/null | grep '/api/embed')
  ok=$(grep -c '| 200 |' <<<"$log")
  cancel=$(grep -cE '\| 4[0-9][0-9] \|' <<<"$log")
  p50=$(grep '| 200 |' <<<"$log" | awk -F'|' '{print $3}' | python3 -c "
import re, statistics, sys
unit = {'µs': 1e-6, 'ms': 1e-3, 's': 1, 'm': 60}
v = [float(m.group(1)) * unit[m.group(2)] for m in (re.match(r'\s*([\d.]+)(µs|ms|s|m)', l) for l in sys.stdin) if m]
print(round(statistics.median(v), 3) if v else '')")
  gpu=$(kubectl -n "$NS" exec deploy/ollama-gpu -c ollama -- nvidia-smi --query-gpu=utilization.gpu,memory.used \
    --format=csv,noheader,nounits 2>/dev/null | tr -d ' ' | head -1)
  nodes=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
  echo "$(date +%H:%M:%S),$top,$ok,$cancel,$p50,${gpu:-,},$nodes" >> "$out"
  sleep 15
done
