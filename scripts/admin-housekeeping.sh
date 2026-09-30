#!/usr/bin/env bash
# 관리자 기록 보존 정리 크론 러너 — 매일 03:30 실행 (등록: crontab)
# 보안 이벤트 90일·감사 로그 365일이 지난 행과 만료된 세션·IP 차단을 지운다.
# 로그: logs/admin-housekeeping.log (마지막 2000줄 유지)
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.beyondfacade/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.beyondfacade/logs"
LOG_FILE="${LOG_DIR}/admin-housekeeping.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] admin housekeeping 시작"
  .venv/bin/python -m apps.admin.adapter.inbound.cli.admin_housekeeping
} >> "${LOG_FILE}" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] admin housekeeping 실패 (exit $?)" >> "${LOG_FILE}"

tail -n 2000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
