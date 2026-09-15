#!/usr/bin/env bash
# RAG 색인 배치 크론 러너 — 매일 05:50 실행 (등록: crontab, 수집 크론들 뒤)
# 증분 색인(기본) — provider 기본값 fp16(로컬 GPU, 새벽 배치는 통상 GPU 여유).
# 로그: logs/rag-indexer.log (마지막 2000줄 유지)
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.beyondfacade/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.beyondfacade/logs"
LOG_FILE="${LOG_DIR}/rag-indexer.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] rag indexer 시작"
  .venv/bin/python -m apps.rag.adapter.inbound.cli.build_rag_index
} >> "${LOG_FILE}" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] rag indexer 실패 (exit $?)" >> "${LOG_FILE}"

tail -n 2000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
