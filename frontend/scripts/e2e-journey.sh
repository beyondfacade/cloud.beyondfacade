#!/usr/bin/env bash
# E2E 여정: /map → 동 폴리곤 클릭 → 사이드패널 확인 → 점포 마커 로드 확인 → [AI 분석] 클릭
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

if ! curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/map" | grep -q "200"; then
  echo "오류: $BASE_URL 에서 dev 서버 응답이 없습니다. 먼저 'npm run dev'로 서버를 띄운 뒤 다시 실행하세요." >&2
  exit 1
fi

VIEWPORT_W=1440
VIEWPORT_H=900
DONG_CODE="1168064000"
INDUSTRY="cafe"

# 앱의 API 베이스는 shared/config.ts가 NEXT_PUBLIC_API_BASE ?? "/api/mock"으로 정한다.
# 스크립트가 /api/mock을 하드코딩하면 실 백엔드 프록시로 띄운 개발 서버에서 항상 실패하므로,
# next가 자동으로 읽는 .env.local을 스크립트도 같은 우선순위로 따라 읽는다.
API_BASE="${NEXT_PUBLIC_API_BASE:-}"
if [[ -z "$API_BASE" ]]; then
  for envfile in "$(dirname "${BASH_SOURCE[0]}")/../.env.local" "$(dirname "${BASH_SOURCE[0]}")/../.env"; do
    [[ -f "$envfile" ]] || continue
    line="$(grep -m1 '^NEXT_PUBLIC_API_BASE=' "$envfile" || true)"
    if [[ -n "$line" ]]; then API_BASE="${line#NEXT_PUBLIC_API_BASE=}"; break; fi
  done
fi
API_BASE="${API_BASE:-/api/mock}"
echo "API 베이스: $API_BASE"

AB close >/dev/null 2>&1 || true

# [0/8] 채팅 관문 — 홈 입력창에 문장을 넣고 /map?region= 착지까지. 실 백엔드면 진단 문장을 거쳐
# 1.5초 뒤 자동 이동한다(diagnosis-line.tsx). 관문 검증만 하고 이후 단계는 기존대로 /map을 직접 연다.
# 입력은 agent-browser 버전에 따라 fill 명령이 달라 React의 onChange가 확실히 잡히는 native setter로 넣는다.
echo "[0/8] 채팅 관문(/) — 문장 입력 → /map?region 착지"
AB set viewport "$VIEWPORT_W" "$VIEWPORT_H" >/dev/null
AB open "$BASE_URL/" >/dev/null
AB wait --load networkidle >/dev/null
AB wait --text "찾아보기" >/dev/null
cat <<'JS' | AB eval --stdin >/dev/null
(() => {
  const input = document.getElementById("intent-text");
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
  setter.call(input, "역삼1동에 카페, 예산 5천");
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.form.requestSubmit();
})()
JS
GATE_DEADLINE=$((SECONDS + 30))
while :; do
  GATE_URL="$(AB get url)"
  if [[ "$GATE_URL" == *"/map?"*"region=${DONG_CODE}"* ]]; then break; fi
  if (( SECONDS > GATE_DEADLINE )); then
    echo "오류: 관문이 30초 안에 /map?region=${DONG_CODE}로 착지하지 않았습니다 (현재 URL: $GATE_URL)" >&2
    exit 1
  fi
  sleep 1
done
echo "  관문 착지 확인: $GATE_URL"

echo "[1/8] 지도 탐색(/map) 오픈"
AB set viewport "$VIEWPORT_W" "$VIEWPORT_H" >/dev/null
AB open "$BASE_URL/map" >/dev/null
AB wait --load networkidle >/dev/null

# 대상 동 폴리곤 중심의 페이지 절대 좌표를 런타임에 계산한다.
# 좌표를 하드코딩하면 ①상단바·컨트롤바 높이가 바뀔 때 ②목 픽스처가 아닌 실 행정동 경계로
# 띄웠을 때 조용히 빗나간다(목의 역삼1동 사각형 중심은 실경계에서 다른 동이다).
# 그래서 지도에 실제로 그려진 경계 GeoJSON을 API 베이스에서 받아 대상 동의 중심을 구한 뒤,
# 지도 컨테이너의 실제 bounding rect + 웹 메르카토르 투영(bearing/pitch 0)으로 화면 좌표를 만든다.
CLICK_POINT="$(cat <<EOF | AB eval --stdin
(async () => {
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
  const res = await fetch("${API_BASE}/regions/geojson");
  const gj = await res.json();
  const f = gj.features.find((f) => f.properties.region_code === "${DONG_CODE}");
  if (!f) return "";
  // 폴리곤/멀티폴리곤의 모든 꼭짓점 평균 — 볼록·오목 상관없이 경계 안쪽에 충분히 든다.
  const pts = JSON.stringify(f.geometry.coordinates).match(/-?\\d+\\.?\\d*,-?\\d+\\.?\\d*/g) ?? [];
  let sx = 0, sy = 0;
  for (const p of pts) { const [a, b] = p.split(","); sx += +a; sy += +b; }
  const target = [sx / pts.length, sy / pts.length];
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
    AB navigate "$BASE_URL/map?region=${DONG_CODE}&industry=${INDUSTRY}" >/dev/null
    AB wait --load networkidle >/dev/null
  else
    echo "오류: 폴리곤 클릭이 region= 쿼리 파라미터에 반영되지 않았습니다 (클릭 회귀 가능성)." >&2
    echo "  알려진 지도 렌더링 버그로 인한 실패라면 E2E_XFAIL_CLICK=1로 재실행해 나머지 여정만 검증할 수 있습니다 (task-9-report.md 참고)." >&2
    exit 1
  fi
fi

# 이후 단계는 "의도한 동"이 아니라 "실제로 선택된 동"을 기준으로 검증한다.
# 경계 데이터가 목 픽스처(사각형)냐 실 행정동이냐에 따라 같은 좌표가 다른 동에 떨어지므로,
# 특정 동을 맞히는 것이 아니라 "동 선택 → 마커 로드 → 분석 프리필" 배선을 확인하는 것이 목적이다.
SELECTED_REGION="$(AB get url | sed -n 's/.*[?&]region=\([0-9]*\).*/\1/p')"
if [[ -z "$SELECTED_REGION" ]]; then
  echo "오류: 선택된 region 코드를 URL에서 읽지 못했습니다." >&2
  exit 1
fi
if [[ "$SELECTED_REGION" != "$DONG_CODE" ]]; then
  echo "  참고: 클릭이 목표 동($DONG_CODE)이 아니라 $SELECTED_REGION 에 들어갔습니다. 배선 검증은 이 동으로 계속합니다."
fi

echo "[3/8] 사이드패널 확인"
AB wait --text "AI 분석 →" >/dev/null

echo "[4/8] 점포 마커 로드 확인"
# region-markers.tsx는 regionCode가 선택된 뒤에만 점포 조회를 호출한다(성능 가드).
# 클러스터 원(WebGL 캔버스)은 DOM으로 직접 검사할 수 없으므로, 그 트리거인 요청 발생 여부로
# "동 선택 → 마커 데이터 로드" 배선이 실제로 동작함을 검증한다.
# agent-browser의 `network requests`는 문서·스크립트·스타일·폰트만 기록하고 fetch/XHR은 남기지
# 않으므로(0.27.0 실측), 브라우저 자체 리소스 타이밍 기록을 읽는다.
STORE_REQUESTS="$(cat <<EOF | AB eval --stdin
performance.getEntriesByType("resource").map((e) => e.name)
  .filter((n) => n.includes("${API_BASE}/stores")).join("\\n") || "(없음)"
EOF
)"
if [[ "$STORE_REQUESTS" != *"region=${SELECTED_REGION}"* ]]; then
  echo "오류: 동 선택 후 ${API_BASE}/stores 요청을 찾지 못했습니다 (마커 로드 배선 회귀 가능성)." >&2
  echo "$STORE_REQUESTS" >&2
  exit 1
fi

echo "[5/8] [AI 분석] 클릭"
# 사이드패널이 길어져(동네 프로필 섹션) CTA가 패널 스크롤 영역 아래로 밀린다. 화면 밖 요소를 클릭하면
# agent-browser는 조용히 빗나가고 URL이 안 바뀐다(2026-09-23 재현: top 1208px / 뷰포트 577px). 먼저 보이게 한다.
# 상단 바에도 "AI 분석" 탭이 있으므로 href로 사이드패널 링크를 특정한다.
AB eval "document.querySelector('a[href^=\"/analysis?\"]')?.scrollIntoView({block:'center'})" >/dev/null
AB find text "AI 분석 →" click >/dev/null
AB wait --text "분석 시작" >/dev/null

echo "[6/8] /analysis 프리필 확인"
PREFILL="$(cat <<'EOF' | AB eval --stdin
(() => {
  const byLabel = (text) => Array.from(document.querySelectorAll("label"))
    .find((l) => l.textContent.trim().startsWith(text))
    ?.querySelector("input,select")?.value ?? "";   // 업종은 v0.14.x부터 select다 — input만 읽으면 ""가 된다
  return JSON.stringify({ region: byLabel("지역 코드"), industry: byLabel("업종") });
})()
EOF
)"
echo "  프리필 값: $PREFILL"
if [[ "$PREFILL" != *"$SELECTED_REGION"* ]] || [[ "$PREFILL" != *"$INDUSTRY"* ]]; then
  echo "오류: /analysis 프리필이 예상과 다릅니다 (region=$SELECTED_REGION, industry=$INDUSTRY 기대)." >&2
  exit 1
fi

# 리포트 article의 상태와 본문 길이를 한 줄로 돌려준다. 완료 대기(7)와 본문 확인(8)이 같이 쓴다.
report_state() {
  cat <<'JS' | AB eval --stdin
(() => {
  const el = document.querySelector('[aria-label="상권 분석 리포트"]');
  if (!el) return "NO_ARTICLE 0";
  const head = el.querySelector("header")?.textContent ?? "";
  const body = (el.textContent ?? "").replace(/\s+/g, " ").trim();
  const status = head.includes("작성 완료") ? "DONE"
    : head.includes("작성 중단") ? "ABORTED" : "IN_PROGRESS";
  return status + " " + body.length;
})()
JS
}

echo "[7/8] 분석 시작 → 리포트 완료 대기"
AB find role button click --name "분석 시작" >/dev/null
# 빈 상태 안내문("분석 내용과 참고 자료가 이곳에 차례로 모입니다")에도 "참고 자료"가 들어 있어
# `wait --text "참고 자료"`는 분석이 시작되기도 전에 즉시 통과한다. 목 응답은 빨라 우연히 맞았지만
# 실 백엔드는 LLM 생성이라 느려 그대로 8단계에서 빈 화면을 보게 된다.
# 완료 판정은 리포트 article의 상태(작성 완료)로만 한다.
REPORT_TIMEOUT="${E2E_REPORT_TIMEOUT:-300}"
DEADLINE=$((SECONDS + REPORT_TIMEOUT))
while :; do
  REPORT_STATE="$(report_state)"
  REPORT_STATUS="$(echo "$REPORT_STATE" | tr -cd 'A-Z_')"
  case "$REPORT_STATUS" in
    DONE) break ;;
    ABORTED)
      echo "오류: 분석이 '작성 중단' 상태로 끝났습니다 (SSE 오류 가능성)." >&2
      exit 1 ;;
  esac
  if (( SECONDS > DEADLINE )); then
    echo "오류: ${REPORT_TIMEOUT}초 안에 리포트가 완료되지 않았습니다 (마지막 상태=$REPORT_STATUS)." >&2
    echo "  실 백엔드 분석이 느리면 E2E_REPORT_TIMEOUT으로 늘릴 수 있습니다." >&2
    exit 1
  fi
  sleep 3
done

echo "[8/8] 리포트 본문 확인"
# 목 픽스처의 특정 문구("종합 진단")를 찾으면 실 백엔드에서는 항상 실패한다 — 본문은 매번 새로
# 생성되기 때문이다. 원천과 무관하게 "빈 껍데기가 아닌가"만 본다.
REPORT_LEN="$(echo "$REPORT_STATE" | tr -cd '0-9')"
if (( ${REPORT_LEN:-0} < 200 )); then
  echo "오류: 리포트가 완료 상태이나 본문이 ${REPORT_LEN:-0}자뿐입니다." >&2
  exit 1
fi
echo "  리포트 본문 ${REPORT_LEN}자 확인"

echo "성공: E2E 여정 완료 (리포트 텍스트 확인됨)"
if [[ "$CLICK_XFAIL" == "1" ]]; then
  echo "XFAIL: 폴리곤 클릭 (지도 렌더링 버그) — E2E_XFAIL_CLICK=1로 폴백 내비게이션 사용, 실제 클릭 경로는 검증되지 않았습니다."
fi
