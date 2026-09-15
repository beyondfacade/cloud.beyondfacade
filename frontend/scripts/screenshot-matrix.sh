#!/usr/bin/env bash
# 스크린샷 매트릭스: 화면(/, 동 선택 후 점포 마커, /analysis 시작 전·진행 중·완료) × 테마(light/dark) × 뷰포트(1440/1024)
# → frontend/screenshots/ 에 저장 (해당 디렉토리는 .gitignore 대상 — 커밋되지 않음).
#
# 전제: http://localhost:3200 (또는 $BASE_URL)에 dev 서버가 떠 있어야 한다 (npm run dev).
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3200}"
export AGENT_BROWSER_ARGS="${AGENT_BROWSER_ARGS:---no-sandbox}"

AB() { npx -y agent-browser "$@" >/dev/null; }

# 중간 실패로 스크립트가 조기 종료돼도 헤드리스 브라우저/데몬 프로세스가 남지 않도록 정리한다.
trap 'AB close >/dev/null 2>&1 || true' EXIT

if ! curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q "200"; then
  echo "오류: $BASE_URL 에서 dev 서버 응답이 없습니다. 먼저 'npm run dev'로 서버를 띄운 뒤 다시 실행하세요." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# agent-browser 데몬은 최초 실행 시점의 cwd를 유지하므로, 스크린샷 경로는 항상 절대경로로 지정한다.
OUT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/screenshots"
mkdir -p "$OUT_DIR"

REGION="1168064000"
INDUSTRY="cafe"
VIEWPORTS=("1440:900" "1024:768")
THEMES=("light" "dark")

AB close || true

for vp in "${VIEWPORTS[@]}"; do
  W="${vp%%:*}"
  H="${vp##*:}"
  AB set viewport "$W" "$H"

  for theme in "${THEMES[@]}"; do
    echo "뷰포트 ${W}x${H} / 테마 ${theme}"

    # --- 지도 탐색(/) ---
    AB open "$BASE_URL/"
    AB wait --load networkidle
    if [[ "$theme" == "dark" ]]; then
      AB find role button click --name "테마 전환"
      sleep 1
    fi
    AB screenshot "$OUT_DIR/map_${theme}_${W}.png"

    # --- 지도 탐색: 동 선택 후 점포 마커/클러스터 ---
    AB navigate "$BASE_URL/?region=${REGION}&industry=${INDUSTRY}"
    AB wait --load networkidle
    if [[ "$theme" == "dark" ]]; then
      AB find role button click --name "테마 전환"
      sleep 1
    fi
    sleep 1
    AB screenshot "$OUT_DIR/map-markers_${theme}_${W}.png"

    # --- AI 분석: 시작 전 ---
    AB navigate "$BASE_URL/analysis?region=${REGION}&industry=${INDUSTRY}"
    AB wait --load networkidle
    if [[ "$theme" == "dark" ]]; then
      AB find role button click --name "테마 전환"
      sleep 1
    fi
    AB screenshot "$OUT_DIR/analysis-idle_${theme}_${W}.png"

    # --- AI 분석: 진행 중 ---
    AB find text "분석 시작" click
    sleep 1.5
    AB screenshot "$OUT_DIR/analysis-progress_${theme}_${W}.png"

    # --- AI 분석: 완료 ---
    AB wait --text "참고 자료"
    AB screenshot "$OUT_DIR/analysis-done_${theme}_${W}.png"
  done
done

echo "완료: $OUT_DIR/ 에 스크린샷 저장됨"
ls -1 "$OUT_DIR"
