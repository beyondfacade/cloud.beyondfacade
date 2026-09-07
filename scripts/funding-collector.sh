#!/usr/bin/env bash
# 정책자금 공고 수집기 크론 러너 — 매일 05:10 실행 (등록: crontab)
# 기업마당 API 1회 호출 전량 수신 → 업서트(멱등) → 만료 갱신
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.beyondfacade/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.beyondfacade/logs"
LOG_FILE="${LOG_DIR}/funding-collector.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] funding collector 시작"
  .venv/bin/python -m apps.funding.adapter.inbound.cli.funding_collector
} >> "${LOG_FILE}" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] funding collector 실패 (exit $?)" >> "${LOG_FILE}"

tail -n 2000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
