// ② 엔드포인트 단독 계단 (testplan §4) — 초당 요청 수를 5→…→1,500으로 올리며 API별 한계 RPS를 찾는다.
// 사람 수가 아니라 초당 요청 수를 직접 정하므로(arrival-rate) TPS 1,500까지 바로 걸 수 있다. 깨지면(에러 5%·p95 3초) 멈춘다.
//   k6 run -e API=summary scripts/load/endpoint.js
// API: search(지원사업 질문 검색 — 임베딩) · geojson(백엔드 /regions/geojson — main 프론트가 /map 진입마다 받는다, H4) · summary · verdicts · verdict · stores · simulate
import http from 'k6/http';
import { check } from 'k6';
import { BASE, pickPair, pickQuery } from './lib/data.js';

const API = __ENV.API || 'summary';

const SIM_INPUT = JSON.stringify({
  deposit: 30000000, key_money: 20000000, interior_cost: 40000000, equipment_cost: 20000000,
  monthly_rent: 2500000, monthly_payroll: 3000000, monthly_insurance: 300000,
  cost_ratio: 0.35, fee_ratio: 0.03, equity: 50000000, desired_loan: 60000000,
  loan_rate: 0.05, expected_monthly_revenue: 15000000,
});

const REQUESTS = {
  geojson: () => http.get(`${BASE}/regions/geojson`, { headers: { 'Accept-Encoding': 'gzip' }, tags: { api: 'geojson' } }),
  summary: (p) => http.get(`${BASE}/regions/${p.region}/summary?industry=${p.industry}`, { tags: { api: 'summary' } }),
  verdicts: (p) => http.get(`${BASE}/verdicts?industry=${p.industry}`, { tags: { api: 'verdicts' } }),
  verdict: (p) => http.get(`${BASE}/verdicts/${p.region}?industry=${p.industry}`, { tags: { api: 'verdict' } }),
  stores: (p) => http.get(`${BASE}/stores?region=${p.region}&industry=${p.industry}&status=open`, { tags: { api: 'stores' } }),
  simulate: () => http.post(`${BASE}/finance/simulate`, SIM_INPUT, { headers: { 'Content-Type': 'application/json' }, tags: { api: 'simulate' } }),
  // 지원사업 질문 검색 — 요청마다 임베딩 1회(Ollama bge-m3, 로컬 GPU). 실패·5초 초과면 200 + available=false
  search: (p) => http.get(`${BASE}/funding/support?region=${p.region}&industry=${p.industry}&q=${encodeURIComponent(pickQuery())}`, { tags: { api: 'search' } }),
};
if (!REQUESTS[API]) throw new Error(`알 수 없는 API: ${API} (${Object.keys(REQUESTS).join(', ')})`);

const rates = [5, 10, 20, 40, 80, 160, 320, 640, 1000, 1500];

export const options = {
  scenarios: {
    [API]: {
      executor: 'ramping-arrival-rate',
      startRate: rates[0],
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 2000,   // 필요 VU ≈ RPS × 응답 시간 — 1,500 RPS × 1초여도 1,500
      stages: rates.flatMap((rate) => [{ duration: '10s', target: rate }, { duration: '1m', target: rate }]),
    },
  },
  // 계단마다 p95·에러율을 보고 "어느 RPS에서 꺾였나"를 기록한다(§9). 깨짐 기준(§4 ④)을 넘으면 1분 뒤 멈춘다
  thresholds: {
    http_req_failed: [{ threshold: 'rate<0.05', abortOnFail: true, delayAbortEval: '1m' }],
    http_req_duration: [{ threshold: 'p(95)<3000', abortOnFail: true, delayAbortEval: '1m' }],
  },
};

export default function () {
  const res = REQUESTS[API](pickPair());
  check(res, { '200': (r) => r.status === 200 });
  if (API === 'search') check(res, { '검색 가능(임베딩 성공)': (r) => r.status === 200 && r.json('search.available') === true });
}
