#!/usr/bin/env bash
# E2E 여정: / → 동 폴리곤 클릭 → 사이드패널 확인 → 점포 마커 로드 확인 → [AI 분석] 클릭
#           → /analysis 프리필 확인 → 분석 시작 → report_done까지 대기 → 리포트 텍스트 존재 assert
#
# 전제: http://localhost:3200 (또는 $BASE_URL)에 dev 서버가 떠 있어야 한다 (npm run dev).
# agent-browser는 전역 설치가 안 된 환경을 고려해 npx로 실행한다.
#
# 실행 모드 (동 폴리곤 클릭 단계):
#   기본 (E2E_XFAIL_CLICK 미설정 또는 0): 클릭 후 region= 쿼리 파라미터가 갱신되지 않으면
#     실패로 간주하고 비정상 종료(exit 1)한다. 클릭 회귀를 은폐하지 않기 위한 기본 동작이다.
#   E2E_XFAIL_CLICK=1: 알려진 지도 렌더링 버그(폴리곤 클릭 히트테스트 미동작,
#     task-9-report.md 참고)로 인한 실패를 명시적으로 예상하고 폴백 내비게이션으로
#     나머지 여정을 계속 검증한다. 이 경우 최종 요약(stdout)에 "XFAIL: 폴리곤 클릭"
#     줄이 출력된다. 지도 버그가 수정된 뒤에는 이 환경변수 없이 실행해 실제 클릭
#     경로가 통과하는지 확인해야 한다.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3200}"
# 컨테이너/CI 등 Chrome 샌드박스 네임스페이스 제약이 있는 환경을 위한 기본값 — 호출자가 이미 지정했으면 존중한다.
export AGENT_BROWSER_ARGS="${AGENT_BROWSER_ARGS:---no-sandbox}"

AB() { npx -y agent-browser "$@"; }

# 중간 실패로 스크립트가 조기 종료돼도 헤드리스 브라우저/데몬 프로세스가 남지 않도록 정리한다.
trap 'AB close >/dev/null 2>&1 || true' EXIT

if ! curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q "200"; then
  echo "오류: $BASE_URL 에서 dev 서버 응답이 없습니다. 먼저 'npm run dev'로 서버를 띄운 뒤 다시 실행하세요." >&2
  exit 1
fi

VIEWPORT_W=1440
VIEWPORT_H=900
DONG_CODE="1168064000"
INDUSTRY="cafe"

AB close >/dev/null 2>&1 || true

echo "[1/8] 지도 탐색(/) 오픈"
AB set viewport "$VIEWPORT_W" "$VIEWPORT_H" >/dev/null
AB open "$BASE_URL/" >/dev/null
AB wait --load networkidle >/dev/null

# 역삼1동(fixtures.ts DONGS[0], region_code 1168064000) 폴리곤 중심의 페이지 절대 좌표를
# 런타임에 계산한다. 하드코딩하면 상단바/컨트롤바 높이가 바뀔 때마다 조용히 빗나가므로,
# 지도 컨테이너의 실제 bounding rect + 웹 메르카토르 투영(bearing/pitch 0)으로 매번 구한다.
CLICK_POINT="$(cat <<'EOF' | AB eval --stdin
(() => {
  const el = document.querySelector(".maplibregl-map");
  if (!el) return "";
  const r = el.getBoundingClientRect();
  const world = 512 * Math.pow(2, 11);            // map-view.tsx INITIAL_ZOOM
  const px = (lng) => ((lng + 180) / 360) * world;
  const py = (lat) => {
    const s = Math.sin((lat * Math.PI) / 180);
    return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * world;
  };
  const center = [126.99, 37.55];                 // map-view.tsx SEOUL_CENTER
  const target = [127.02625, 37.5];               // 역삼1동 사각형 중심
  const x = Math.round(r.left + r.width / 2 + (px(target[0]) - px(center[0])));
  const y = Math.round(r.top + r.height / 2 + (py(target[1]) - py(center[1])));
  return x + " " + y;
})()
EOF
)"
read -r CLICK_X CLICK_Y <<<"$(echo "$CLICK_POINT" | tr -cd '0-9 \n')"
if [[ -z "${CLICK_X:-}" || -z "${CLICK_Y:-}" ]]; then
  echo "오류: 지도 컨테이너를 찾지 못해 클릭 좌표를 계산할 수 없습니다 (응답: $CLICK_POINT)." >&2
  exit 1
fi

echo "[2/8] 동 폴리곤 클릭 (역삼1동, x=$CLICK_X y=$CLICK_Y)"
AB mouse move "$CLICK_X" "$CLICK_Y" >/dev/null
AB mouse down left >/dev/null
AB mouse up left >/dev/null
sleep 1

CLICK_XFAIL=0
CURRENT_URL="$(AB get url)"
if [[ "$CURRENT_URL" != *"region="* ]]; then
  if [[ "${E2E_XFAIL_CLICK:-0}" == "1" ]]; then
    # 알려진 환경 이슈: 일부 헤드리스/샌드박스 제약 환경에서는 MapLibre GeoJSON 소스의
    # 타일링이 끝나지 않아 폴리곤 클릭 히트테스트가 동작하지 않는 경우가 있다
    # (frontend/.superpowers/sdd/2026-08-25-frontend-mvp/task-9-report.md 참고).
    # E2E_XFAIL_CLICK=1로 명시적으로 opt-in한 경우에만 동일한 최종 상태로 폴백해
    # 나머지 여정을 계속 검증한다.
    CLICK_XFAIL=1
    echo "  경고: 폴리곤 클릭이 사이드패널에 반영되지 않았습니다. E2E_XFAIL_CLICK=1이므로 region 쿼리 파라미터로 폴백합니다." >&2
    AB navigate "$BASE_URL/?region=${DONG_CODE}&industry=${INDUSTRY}" >/dev/null
    AB wait --load networkidle >/dev/null
  else
    echo "오류: 폴리곤 클릭이 region= 쿼리 파라미터에 반영되지 않았습니다 (클릭 회귀 가능성)." >&2
    echo "  알려진 지도 렌더링 버그로 인한 실패라면 E2E_XFAIL_CLICK=1로 재실행해 나머지 여정만 검증할 수 있습니다 (task-9-report.md 참고)." >&2
    exit 1
  fi
fi

echo "[3/8] 사이드패널 확인"
AB wait --text "AI 분석 →" >/dev/null

echo "[4/8] 점포 마커 로드 확인"
# store-markers.tsx는 regionCode가 선택된 뒤에만 GET /api/mock/stores를 호출한다(성능 가드).
# 클러스터 원(WebGL 캔버스)은 DOM으로 직접 검사할 수 없으므로, 그 트리거인 네트워크 요청 발생 여부로
# "동 선택 → 마커 데이터 로드" 배선이 실제로 동작함을 검증한다.
STORE_REQUESTS="$(AB network requests --filter "/api/mock/stores")"
if [[ "$STORE_REQUESTS" != *"region=${DONG_CODE}"* ]]; then
  echo "오류: 동 선택 후 /api/mock/stores 요청을 찾지 못했습니다 (마커 로드 배선 회귀 가능성)." >&2
  echo "$STORE_REQUESTS" >&2
  exit 1
fi

echo "[5/8] [AI 분석] 클릭"
AB find text "AI 분석 →" click >/dev/null
AB wait --text "분석 시작" >/dev/null

echo "[6/8] /analysis 프리필 확인"
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

echo "[7/8] 분석 시작 → report_done 대기"
AB find text "분석 시작" click >/dev/null
AB wait --text "참고 자료" >/dev/null

echo "[8/8] 리포트 텍스트 존재 확인"
REPORT_TEXT="$(AB get text body)"
if ! echo "$REPORT_TEXT" | grep -q "종합 진단"; then
  echo "오류: 리포트 텍스트를 찾을 수 없습니다." >&2
  exit 1
fi

echo "성공: E2E 여정 완료 (리포트 텍스트 확인됨)"
if [[ "$CLICK_XFAIL" == "1" ]]; then
  echo "XFAIL: 폴리곤 클릭 (지도 렌더링 버그) — E2E_XFAIL_CLICK=1로 폴백 내비게이션 사용, 실제 클릭 경로는 검증되지 않았습니다."
fi
