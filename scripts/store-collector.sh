#!/usr/bin/env bash
# 인허가 점포 증분 수집기 크론 러너 — 매일 04:20 실행 (등록: crontab)
# DB의 (업종×자치구) 최근 갱신시점 커서 기준 증분만 수집 (DAT_UPDT_PNT::GTE)
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.beyondfacade/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.beyondfacade/logs"
LOG_FILE="${LOG_DIR}/store-collector.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] store collector 시작"
  .venv/bin/python -m apps.store.adapter.inbound.cli.store_collector
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] academy collector (서울 학원·교습소 스냅샷 전량, ~26회 호출)"
  .venv/bin/python -m apps.store.adapter.inbound.cli.academy_collector
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] broker collector (부동산중개업 스냅샷 전량 + 폐업 추정, ~35회 호출)"
  .venv/bin/python -m apps.store.adapter.inbound.cli.broker_collector
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] region 공간조인 (신규분)"
  .venv/bin/python -m apps.store.adapter.inbound.cli.assign_regions
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 지표 배치 집계 (region_industry_metric)"
  .venv/bin/python -m apps.metric.adapter.inbound.cli.build_metrics
} >> "${LOG_FILE}" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] store collector 실패 (exit $?)" >> "${LOG_FILE}"

tail -n 5000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
