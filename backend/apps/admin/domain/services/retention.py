"""관리자 기록 보존 기간 — 매일 정리 작업(admin_housekeeping)이 이보다 오래된 행을 지운다."""

from datetime import timedelta

ACCESS_EVENT_RETENTION = timedelta(days=90)  # 스캐너 탐색이 매일 쌓이는 표 — 분기 단위 추적이면 충분
AUDIT_RETENTION = timedelta(days=365)  # 관리자 조치는 연 단위로 되짚을 수 있어야 한다
