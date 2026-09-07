#!/usr/bin/env bash
# 편의점 스냅샷 수집기 크론 러너 — 매주 월요일 05:40 실행 (등록: crontab)
# 주 1회 근거: 원천(소진공 상가정보)이 기준연월(stdrYm) 단위로 갱신되는 느린 스냅샷이라
# 일 단위 수집은 무의미하고, 신규 출점("검증된 상권" 프록시, brainstorming §3.5) 신호는
# 주 단위 해상도면 충분. 호출 427회/회 — data.go.kr 일 한도 10,000회의 4.3%
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.beyondfacade/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.beyondfacade/logs"
LOG_FILE="${LOG_DIR}/convenience-collector.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] convenience collector 시작 (행정동 427회 호출)"
  .venv/bin/python -m apps.convenience.adapter.inbound.cli.convenience_collector
} >> "${LOG_FILE}" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] convenience collector 실패 (exit $?)" >> "${LOG_FILE}"

tail -n 5000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
