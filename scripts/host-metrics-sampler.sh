#!/usr/bin/env bash
# 설비 지표 표본 크론 러너 — 매분 실행 (등록: crontab)
# CPU·메모리·디스크·GPU 비율을 host_metric_sample에 1행 남기고 8일 지난 표본을 지운다.
# 로그: logs/host-metrics-sampler.log (마지막 2000줄 유지)
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.beyondfacade/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.beyondfacade/logs"
LOG_FILE="${LOG_DIR}/host-metrics-sampler.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] host metrics sampler 시작"
  .venv/bin/python -m apps.ops.adapter.inbound.cli.sample_host_metrics
} >> "${LOG_FILE}" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] host metrics sampler 실패 (exit $?)" >> "${LOG_FILE}"

tail -n 2000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
