// 혼합 부하 (testplan §4 ①③④⑤⑥⑦). 페르소나 비율 A 60 : B 10 : C 20 : D 10 으로 VU를 나눈다.
//   k6 run -e PROFILE=smoke scripts/load/load.js          ① 스크립트 확인 (페르소나마다 1바퀴)
//   k6 run -e PROFILE=load  scripts/load/load.js          ③ 동접 100명 25분 유지
//   k6 run -e PROFILE=stress scripts/load/load.js         ④ 1,000명까지 계단, 에러 5%·p95 3초 넘으면 중단
//   k6 run -e PROFILE=spike scripts/load/load.js          ⑤ 10초 만에 500명
//   k6 run -e PROFILE=soak  scripts/load/load.js          ⑥ 50명 1시간 50분
//   k6 run -e PROFILE=llm -e LLM=1 -e LLM_TARGET=live -e MODEL=gemini scripts/load/load.js   ⑦ 동시 분석 4→8→16→35(Gemini 단독) + 지도 탐색 낮은 부하
// 대상: -e BASE=http://localhost:8202 (부하 테스트 컨테이너 — scripts/load/env.sh up). 운영·개발(8200·8201)에는 걸지 않는다. LLM=1이 없으면 페르소나 B(Gemini 호출·리포트 DB 저장)는 빠진다.
// k6 설치 없이: docker run --rm --network host -v "$PWD:/w" -w /w grafana/k6 run -e PROFILE=smoke scripts/load/load.js
// 주의(testplan §7): k6는 대상 서버와 다른 머신에서 돌린다 · 개발 DB를 같이 쓰는 서버엔 smoke 말고 걸지 않는다 ·
//   LLM=1은 analysis_report·LLM 사용량을 DB에 남긴다(테스트 전후 건수 기록 후 정리)
import { aiReport, financePlan, mapExplorer, supportFinder } from './lib/personas.js';

export { aiReport, financePlan, mapExplorer, supportFinder };

const PROFILE = __ENV.PROFILE || 'smoke';
const WITH_LLM = __ENV.LLM === '1';
const PERSONAS = [
  ['mapExplorer', 0.6],
  ['aiReport', 0.1],
  ['financePlan', 0.2],
  ['supportFinder', 0.1],
].filter(([name]) => WITH_LLM || name !== 'aiReport');

// [지속 시간, 전체 동접] 계단 — 페르소나별 VU는 비율로 나눈다
const STAGES = {
  load: [['2m', 50], ['3m', 100], ['25m', 100], ['2m', 0]],
  stress: [['2m', 100], ['3m', 100], ['2m', 200], ['3m', 200], ['2m', 400], ['3m', 400],
    ['2m', 700], ['3m', 700], ['2m', 1000], ['3m', 1000], ['2m', 0]],
  spike: [['1m', 5], ['10s', 500], ['1m', 500], ['10s', 5], ['2m', 5]],
  soak: [['2m', 50], ['110m', 50], ['1m', 0]],   // 실행 도구 2시간 제한 안에 끝나게 1시간 50분 유지
};

// B를 빼면 남은 페르소나끼리 비율을 다시 나눠 전체 동접을 목표에 맞춘다
const RATIO_SUM = PERSONAS.reduce((sum, [, ratio]) => sum + ratio, 0);
const share = (total, ratio) => (total === 0 ? 0 : Math.max(1, Math.round((total * ratio) / RATIO_SUM)));

function scenarios() {
  if (PROFILE === 'smoke') {
    return Object.fromEntries(PERSONAS.map(([name]) =>
      [name, { executor: 'per-vu-iterations', exec: name, vus: 1, iterations: 1 }]));
  }
  if (PROFILE === 'llm') {
    if (!WITH_LLM) throw new Error('PROFILE=llm은 LLM=1과 함께 쓴다 (Gemini 요금·한도 발생)');
    const steps = [4, 8, 16, 35].flatMap((n) => [{ duration: '1m', target: n }, { duration: '4m', target: n }]);
    return {
      aiReport: { executor: 'ramping-vus', exec: 'aiReport', startVUs: 0, stages: steps },
      mapExplorer: { executor: 'constant-vus', exec: 'mapExplorer', vus: 10, duration: '20m' },
    };
  }
  const stages = STAGES[PROFILE];
  if (!stages) throw new Error(`알 수 없는 PROFILE: ${PROFILE}`);
  return Object.fromEntries(PERSONAS.map(([name, ratio]) => [name, {
    executor: 'ramping-vus',
    exec: name,
    startVUs: 0,
    stages: stages.map(([duration, total]) => ({ duration, target: share(total, ratio) })),
    gracefulRampDown: '30s',
  }]));
}

// 합격 기준 (testplan §5, 10/7 확정). LLM_TARGET=fake(기본)면 /intent는 고정 3초 + 서버 몫 0.5초.
const LLM_TARGET = __ENV.LLM_TARGET || 'fake';
const GENERAL = ['p(95)<500', 'p(99)<1000'];
const thresholds = {
  http_req_failed: [PROFILE === 'load' ? 'rate<0.001' : 'rate<0.01'],
  'http_req_duration{api:geojson}': ['p(95)<2000'],
  'http_req_duration{api:verdicts}': GENERAL,
  'http_req_duration{api:summary}': GENERAL,
  'http_req_duration{api:profile}': GENERAL,
  'http_req_duration{api:verdict}': GENERAL,
  'http_req_duration{api:alternatives}': GENERAL,
  'http_req_duration{api:stores}': GENERAL,
  'http_req_duration{api:prefill}': GENERAL,
  'http_req_duration{api:candidates}': GENERAL,
  'http_req_duration{api:support}': GENERAL,
  'http_req_duration{api:simulate}': ['p(95)<300'],
  'http_req_duration{api:intent}': [LLM_TARGET === 'fake' ? 'p(95)<3500' : 'p(95)<5000'],
  'http_req_duration{api:analysis_stream}': ['p(95)<60000'],
};
if (PROFILE === 'stress') {
  // Breakpoint: 깨지는 지점을 기록하고 멈춘다
  thresholds.http_req_failed = [{ threshold: 'rate<0.05', abortOnFail: true, delayAbortEval: '1m' }];
  thresholds.http_req_duration = [{ threshold: 'p(95)<3000', abortOnFail: true, delayAbortEval: '1m' }];
}

export const options = { scenarios: scenarios(), thresholds };
