#!/usr/bin/env bash
# 한국은행 기준금리 + R-ONE 임대동향 수집기 크론 러너 — 주 1회(월 05:20) 실행 (등록: crontab)
# ECOS 722Y001 월별 기준금리 → interest_rate 업서트(멱등)
# R-ONE 임대료·공실률(분기, 통계표 20개) → rent_price 업서트(멱등) — 분기 공표라 주 1회로 충분
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.beyondfacade/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.beyondfacade/logs"
LOG_FILE="${LOG_DIR}/interest-rate-collector.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] interest rate collector 시작"
  .venv/bin/python -m apps.shock.adapter.inbound.cli.load_interest_rate
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] rent price collector 시작"
  .venv/bin/python -m apps.rent.adapter.inbound.cli.load_rent_price
} >> "${LOG_FILE}" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] interest/rent collector 실패 (exit $?)" >> "${LOG_FILE}"

tail -n 2000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
