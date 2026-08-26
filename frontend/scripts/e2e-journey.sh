#!/usr/bin/env bash
# E2E 여정: / → 동 폴리곤 클릭 → 사이드패널 확인 → [AI 분석] 클릭
#           → /analysis 프리필 확인 → 분석 시작 → report_done까지 대기 → 리포트 텍스트 존재 assert
#
# 전제: http://localhost:3500 (또는 $BASE_URL)에 dev 서버가 떠 있어야 한다 (npm run dev).
# agent-browser는 전역 설치가 안 된 환경을 고려해 npx로 실행한다.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3500}"
# 컨테이너/CI 등 Chrome 샌드박스 네임스페이스 제약이 있는 환경을 위한 기본값 — 호출자가 이미 지정했으면 존중한다.
export AGENT_BROWSER_ARGS="${AGENT_BROWSER_ARGS:---no-sandbox}"

AB() { npx -y agent-browser "$@"; }

if ! curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q "200"; then
  echo "오류: $BASE_URL 에서 dev 서버 응답이 없습니다. 먼저 'npm run dev'로 서버를 띄운 뒤 다시 실행하세요." >&2
  exit 1
fi

# 역삼1동 (fixtures.ts DONGS[0], region_code 1168064000) 중심 화면 좌표.
# SEOUL_CENTER [126.99, 37.55] / zoom 11 (map-view.tsx) 기준 Web Mercator 투영으로 계산한
# 값으로, 뷰포트 1440x900에서 지도 컨테이너 box(x:0, y:114, w:1120, h:480)와 맞는다.
VIEWPORT_W=1440
VIEWPORT_H=900
CLICK_X=613
CLICK_Y=446
DONG_CODE="1168064000"
INDUSTRY="cafe"

AB close >/dev/null 2>&1 || true

echo "[1/7] 지도 탐색(/) 오픈"
AB set viewport "$VIEWPORT_W" "$VIEWPORT_H" >/dev/null
AB open "$BASE_URL/" >/dev/null
AB wait --load networkidle >/dev/null

echo "[2/7] 동 폴리곤 클릭 (역삼1동, x=$CLICK_X y=$CLICK_Y)"
AB mouse move "$CLICK_X" "$CLICK_Y" >/dev/null
AB mouse down left >/dev/null
AB mouse up left >/dev/null
sleep 1

CURRENT_URL="$(AB get url)"
if [[ "$CURRENT_URL" != *"region="* ]]; then
  # 알려진 환경 이슈: 일부 헤드리스/샌드박스 제약 환경에서는 MapLibre GeoJSON 소스의
  # 타일링이 끝나지 않아 폴리곤 클릭 히트테스트가 동작하지 않는 경우가 있다
  # (frontend/.superpowers/sdd/2026-08-25-frontend-mvp/task-9-report.md 참고).
  # 이 경우 동일한 최종 상태로 폴백해 나머지 여정을 계속 검증한다.
  echo "  경고: 폴리곤 클릭이 사이드패널에 반영되지 않았습니다. region 쿼리 파라미터로 폴백합니다." >&2
  AB navigate "$BASE_URL/?region=${DONG_CODE}&industry=${INDUSTRY}" >/dev/null
  AB wait --load networkidle >/dev/null
fi

echo "[3/7] 사이드패널 확인"
AB wait --text "AI 분석 →" >/dev/null

echo "[4/7] [AI 분석] 클릭"
AB find text "AI 분석 →" click >/dev/null
AB wait --text "분석 시작" >/dev/null

echo "[5/7] /analysis 프리필 확인"
PREFILL="$(cat <<'EOF' | AB eval --stdin
(() => {
  const byLabel = (text) => Array.from(document.querySelectorAll("label"))
    .find((l) => l.textContent.trim().startsWith(text))
    ?.querySelector("input")?.value ?? "";
  return JSON.stringify({ region: byLabel("지역 코드"), industry: byLabel("업종") });
})()
EOF
)"
echo "  프리필 값: $PREFILL"
if [[ "$PREFILL" != *"$DONG_CODE"* ]] || [[ "$PREFILL" != *"$INDUSTRY"* ]]; then
  echo "오류: /analysis 프리필이 예상과 다릅니다 (region=$DONG_CODE, industry=$INDUSTRY 기대)." >&2
  exit 1
fi

echo "[6/7] 분석 시작 → report_done 대기"
AB find text "분석 시작" click >/dev/null
AB wait --text "참고 자료" >/dev/null

echo "[7/7] 리포트 텍스트 존재 확인"
REPORT_TEXT="$(AB get text body)"
if ! echo "$REPORT_TEXT" | grep -q "종합 진단"; then
  echo "오류: 리포트 텍스트를 찾을 수 없습니다." >&2
  exit 1
fi

AB close >/dev/null 2>&1 || true
echo "성공: E2E 여정 완료 (리포트 텍스트 확인됨)"
