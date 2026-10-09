// 예상 유저 흐름 = k6 시나리오 (testplan §2). API 경로·파라미터는 frontend/src/features/*/api.ts와 같다.
// 태그 api=…로 API별 p95를 따로 잰다(§5 합격 기준).
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { BASE, EMBED_SHARE, pickPair, pickQuery, think } from './data.js';

// GZIP=1이면 모든 요청에 Accept-Encoding: gzip — 실제 브라우저와 같게 (10차). 없으면 1~9차처럼 geojson만.
const ENCODING = __ENV.GZIP === '1' ? { 'Accept-Encoding': 'gzip' } : {};
const JSON_HEADERS = { 'Content-Type': 'application/json', ...ENCODING };

function get(path, api, params = {}, ok = [200]) {
  const res = http.get(`${BASE}${path}`, { ...params, headers: { ...ENCODING, ...params.headers }, tags: { api } });
  check(res, { [`${api} 200`]: (r) => ok.includes(r.status) });
  return res;
}

function post(path, body, api, params = {}) {
  const res = http.post(`${BASE}${path}`, JSON.stringify(body), { headers: JSON_HEADERS, ...params, tags: { api } });
  check(res, { [`${api} 200`]: (r) => r.status === 200 });
  return res;
}

// A. 지도 탐색자 (60%) — main 프론트는 /map 진입마다 백엔드 경계(/regions/geojson)를 받는다(H4).
// 경계가 정적 파일로 바뀌면(serverplan K3) geojson 호출을 뺀다.
export function mapExplorer() {
  const first = pickPair();
  group('지도 진입', () => {
    get('/regions/geojson', 'geojson', { headers: { 'Accept-Encoding': 'gzip' } });   // 브라우저와 같게
    get(`/verdicts?industry=${first.industry}`, 'verdicts');
  });
  sleep(think(5, 10));
  const clicks = 3 + Math.floor(Math.random() * 3);
  for (let i = 0; i < clicks; i++) {
    const p = pickPair();
    group('동 클릭', () => {
      get(`/regions/${p.region}/summary?industry=${p.industry}`, 'summary');
      // 자료 없는 동(5곳)은 설계대로 404 '자료 없음' — 실패로 세지 않는다(1차 결과 (g)5)
      get(`/profiles/${p.region}`, 'profile', { responseCallback: http.expectedStatuses(200, 404) }, [200, 404]);
      get(`/verdicts/${p.region}?industry=${p.industry}`, 'verdict');
      get(`/verdicts/${p.region}/alternatives?industry=${p.industry}`, 'alternatives');
      get(`/stores?region=${p.region}&industry=${p.industry}&status=open`, 'stores');
    });
    sleep(think(5, 15));
  }
}

// B. 질문 → AI 리포트 (10%, 가장 비쌈) — LLM=1일 때만 돈다. 가짜 LLM 컨테이너(LLM_MODE=fake)면 요금 없음,
//    실제 Gemini 컨테이너면 요금·한도 발생(testplan §7-4 (c) — ⑦ 트랙만).
// NO_THINK=1이면 생각·읽기 시간 없이 바로 다음 분석 — VU 수 = 동시 분석 수 (⑦ 보강: 동시 35건까지 실제로 올린다)
const AI_THINK = __ENV.NO_THINK === '1' ? 0 : 1;

export function aiReport() {
  const p = pickPair();
  group('질문', () => post('/intent', { text: `${p.name}에서 ${p.label} 창업하려고 해요` }, 'intent', { timeout: '30s' }));
  sleep(AI_THINK * think(3, 5));
  group('리포트', () => {
    // MODEL=gemini면 Gemini 단독(폴백 없음) — ⑦에서 한도에 걸리는 지점을 오퍼스 폴백 없이 본다
    const body = __ENV.MODEL ? { region: p.region, industry: p.industry, model: __ENV.MODEL } : { region: p.region, industry: p.industry };
    // 질문이 있으면 지원사업 후보를 질문 유사도로 정렬한다 = 임베딩 1회 (2차)
    if (Math.random() < EMBED_SHARE) body.question = `${p.label} 창업할 때 ${pickQuery()} 관련 지원을 받을 수 있을까요?`;
    const created = post('/analysis', body, 'analysis_create');
    if (created.status !== 200) return;
    // k6 기본 http.get은 SSE가 끝날 때까지 기다린다 — 전체 완료 시간만 잰다(첫 글자는 xk6-sse 필요, §7-6)
    const stream = get(`/analysis/${created.json('analysis_id')}/events`, 'analysis_stream', { timeout: '120s' });
    // 해석 실패 시 코드 대체 문장("…해석을 만들지 못했습니다…") — 200이어도 LLM은 실패한 것
    check(stream, { 'analysis LLM 해석 성공': (r) => r.status === 200 && !String(r.body).includes('해석을 만들지 못했습니다') });
  });
  sleep(AI_THINK * think(30, 60));
}

const PLAN_INPUT = {
  deposit: 30000000, key_money: 20000000, interior_cost: 40000000, equipment_cost: 20000000,
  monthly_rent: 2500000, monthly_payroll: 3000000, monthly_insurance: 300000,
  cost_ratio: 0.35, fee_ratio: 0.03, equity: 50000000, desired_loan: 60000000,
  loan_rate: 0.05, expected_monthly_revenue: 15000000,
};

// C. 자금 계획 (20%) — LLM 없음
export function financePlan() {
  const p = pickPair();
  group('계획 진입', () => {
    get(`/finance/prefill?region=${p.region}&industry=${p.industry}`, 'prefill');
    get(`/funding/candidates?stage=pre&industry=${p.industry}&region=${p.region}`, 'candidates');
    get(`/regions/${p.region}/summary?industry=${p.industry}`, 'summary');
    post('/finance/questions', { input: PLAN_INPUT }, 'questions');
  });
  sleep(think(10, 20));
  const tries = 2 + Math.floor(Math.random() * 2);
  for (let i = 0; i < tries; i++) {
    const revenue = PLAN_INPUT.expected_monthly_revenue * (0.7 + Math.random() * 0.6);
    group('값 바꿔 계산', () => post('/finance/simulate', { ...PLAN_INPUT, expected_monthly_revenue: Math.round(revenue) }, 'simulate'));
    sleep(think(3, 8));
  }
}

// D. 지원사업 안내 (10%) — LLM 없음
export function supportFinder() {
  const p = pickPair();
  group('지원사업', () => {
    get(`/funding/support?region=${p.region}&industry=${p.industry}`, 'support');
    if (Math.random() < EMBED_SHARE) {
      // 질문 검색 = 임베딩 1회. 임베딩 실패·5초 초과면 200이어도 available=false — 따로 센다
      const found = get(`/funding/support?region=${p.region}&industry=${p.industry}&q=${encodeURIComponent(pickQuery())}`, 'search');
      check(found, { '검색 가능(임베딩 성공)': (r) => r.status === 200 && r.json('search.available') === true });
    }
    get(`/regions/${p.region}/summary?industry=${p.industry}`, 'summary');
  });
  sleep(think(10, 20));
}
