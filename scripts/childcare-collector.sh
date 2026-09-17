#!/usr/bin/env bash
# 어린이집 스냅샷 수집기 크론 러너 — 매주 월요일 05:30 실행 (등록: crontab)
# 주 1회 근거: 원천 기준일(datastdrdt)은 매일 갱신되지만 정원·현원·대기는 월 단위로 움직이고,
# 폐원(응답 소실) 신호도 주 단위 해상도면 충분. 이력 행은 기준일마다 쌓이므로 일 단위는 행만 7배.
# 호출 25회/회 — 어린이집정보공개포털 운영계정 일 한도 1,000회의 2.5%
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.beyondfacade/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.beyondfacade/logs"
LOG_FILE="${LOG_DIR}/childcare-collector.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] childcare collector 시작 (자치구 25회 호출)"
  .venv/bin/python -m apps.childcare.adapter.inbound.cli.childcare_collector
} >> "${LOG_FILE}" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] childcare collector 실패 (exit $?)" >> "${LOG_FILE}"

tail -n 5000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
