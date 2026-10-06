#!/usr/bin/env bash
# ④지역 이벤트 수집기 크론 러너 — 주 1회 실행 (등록: crontab, 미등록 상태)
# 서울 열린데이터광장 OA-22856 도시정비사업·OA-16096 대규모점포·OA-15818 아파트
# → shock_event(layer=regional) + shock_event_region 업서트(멱등). 서울 API 6회·SGIS 지오코딩 ~120회
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.beyondfacade/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.beyondfacade/logs"
LOG_FILE="${LOG_DIR}/regional-event-collector.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] regional event collector 시작"
  .venv/bin/python -m apps.shock.adapter.inbound.cli.load_regional_events
} >> "${LOG_FILE}" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] regional event collector 실패 (exit $?)" >> "${LOG_FILE}"

tail -n 2000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
