# 질문 유형별 직접 답 — 첫 문장·근거는 코드, 해석은 LLM (설계)

- 날짜: 2026-10-05
- 브랜치: `feat/question-answer` (기반 main `7f80bdc`, 워크트리 `.worktrees/question-answer`)
- 버전: backend v0.69.0, frontend 다음 minor(Codex 위임)
- 상태: 사용자 승인 설계(대화 1~3부), 스펙 검토 대기
- 선행: `2026-10-05-report-code-first-design.md`(6개 절 코드, 해석 한 단락 LLM)

## 1. 배경과 목표

코드 우선 구조(BE v0.68.0) 뒤 사람 검수 2차(`data/eval/results/report-code-first-2026-10-05/final/human_review_2.json`)에서 질문이 있는 리포트 16건 중 **12건이 "질문에 답하지 못함"**이었다. Claude 판정자는 전부 "답함"으로 봤다 — 판정자가 후하다.

못 답한 사례를 대조하면 원인은 문장력이 아니라 **질문이 묻는 사실이 해석 입력에 없다**는 것이다.

| 질문 | 해석이 한 말 | 빠진 사실 |
|---|---|---|
| 은행 대출 받아서 차려도 될까요? | 일반 위험 반복 | 금리·상환 부담, 자금 계획 화면 안내 |
| 모아 둔 돈이 5천만 원인데 시작할 수 있을까요? | "위험 부담이 크다" | `facts.budget`이 null(질문 속 금액을 읽지 않음), 매출·임대료 근거 없음 |
| 주말 손님 위주로 생각하는데 어떨까요? | "시간대 자료 부족" | `profile.weekend_index`가 facts에 있으나 본문에 없음 |
| 여기서 양식집 차려도 괜찮을까요? (경고 없음) | "긍정적인 환경" | 경고 없음 ≠ 장사가 된다. 사람 메모 "긍정적인 명확한 근거도 없음" |
| 주말 손님 (평창동) | — | 사람 메모 "거주민 생활수준 고려" — 아파트 평균가·연령 구성이 facts에만 있음 |
| 한식당 괜찮은 자리일까요? | — | 사람 메모 "뉴스 참고가 됐으면" |

또 HANDOFF §0-14는 "관문이 질문 유형을 이미 뽑는다"고 적었지만 **사실이 아니다** — 의도 관문(`apps/intent`)은 동·업종·예산만 뽑는다.

목표: **질문이 있으면 해석 맨 위 첫 문장(직접 답)과 그 근거 줄을 코드가 질문 유형에 맞춰 쓰고, LLM은 그 아래 해석 2~3문장만 쓴다.** 같은 질문에는 같은 직접 답이 나오고, "경고 없음"을 "괜찮다"로 부풀리지 않는다.

비목표: 같은 질문 캐시(HANDOFF §0-14 3번), 질문 없는 총평 개선, §0-14 2번 작은 코드 후속(숫자 가드 오삭제 등), 의도 관문 스키마 변경, 판정 로직 변경.

## 2. 결정 사항 (사용자 확정)

| 결정 | 내용 |
|---|---|
| 직접 답 작성자 | **코드** — 질문 유형 × 판정 등급으로 첫 문장 고정. LLM은 뒤에 해석만 |
| 유형 판별 | **키워드 규칙**(결정적, LLM 호출 없음). 겹치면 고정 우선순위로 하나 |
| 근거 위치 | 해석 상자 안 — 첫 문장 아래 근거 1~3줄(코드), 그 아래 AI 해석 |
| 질문 없음 | 지금과 같다 — 코드 첫 문장 없이 LLM 총평 |
| 자료 부족 동네 | 지금과 같다 — `scarce_lead`만, LLM 호출 없음 |
| 뉴스 | 본문에 [참고 신호]로 — 동 이름이 든 기사만 |

## 3. 리포트 구성과 SSE

```
answer_lead   ← 코드  질문에 대한 직접 답(첫 문장) + 근거 줄   ★ 신규, 질문 있을 때만
answer        ← LLM  해석 2~3문장 (숫자 금지)                  (질문 없으면 지금처럼 총평 3~5문장)
verdict … funding ← 코드 6개 절 (지금과 같다, conditions에 두 줄 추가 — §6)
```

이벤트 순서:

1. `agent_status`·`facts` — 지금과 같다(facts에 키 하나 추가 — §7).
2. 코드 절을 `report_delta`로 **즉시** — 질문이 있고 자료 부족 동네가 아니면 `answer_lead`를 6개 절과 함께 먼저 내보낸다. 사실 수집 직후 직접 답이 뜬다.
3. LLM `answer` — 지금처럼 모아서 가드 뒤 한 번에.
4. `report_done` — 지금과 같다.

- 자료 부족 동네: `answer_lead`를 내지 않는다. `answer`는 지금처럼 `scarce_lead` 코드 문장.
- 해석 실패(폴백): `answer_lead`는 이미 나갔으므로 `answer`의 폴백 문장만 바뀐다 — "해석을 만들지 못했습니다. 위 답과 아래 사실을 직접 확인해 주세요."
- 대안 안내 문장(`alternatives_pointer`)은 지금처럼 `answer` 끝에 붙인다.
- 저장: `answer_lead`도 섹션으로 저장한다(`section_stream.SECTION_ORDER`에서 `answer` 앞). **옛 저장 리포트(answer_lead 없음)도 그대로 열려야 한다.**

## 4. 질문 유형 — `apps/agent/domain/services/question_topic.py` (순수, stdlib)

`classify(question: str | None) -> QuestionTopic | None` — 질문이 없거나 공백이면 None.
`QuestionTopic`은 frozen dataclass `{kind: str, band: str | None}` — `band`는 시간대 유형에서 묻는 구간.

규칙은 **우선순위 순서의 표**(Chain of Responsibility) — 위에서부터 처음 걸린 규칙 하나:

| 순위 | kind | 키워드(예, 정규식으로 구현) |
|---|---|---|
| 1 | `loan` | 대출, 빌려, 융자 |
| 2 | `budget` | 금액 표현(`\d+(\.\d+)?\s*(억|천만|천|만)` + 원 문맥), 모아 둔 돈, 자본금, 예산 |
| 3 | `hours` | 점심, 저녁, 밤, 늦게, 새벽, 아침, 주말, 평일 |
| 4 | `competition` | 이미 많, 벌써 여러, 경쟁, 포화 |
| 5 | `customers` | 외국인, 중국인, 어르신, 노인, 학생, 직장인, 주민, 손님층 |
| 6 | `covid` | 코로나, 팬데믹 |
| 7 | `general` | 위에 안 걸린 모든 질문 |

- `hours`의 `band`: 점심→`lunch`(11~14), 저녁→`evening`(17~21), 밤·늦게·새벽→`night`(21~24·00~06), 아침→`morning`(06~11), 주말·평일→`weekend`. 여러 개면 문장 안에서 먼저 나온 것.
- 예산 금액 파싱은 여기서 하지 않는다 — §7 `budget`.
- **평가셋 질문 73개 전부**에 기대 kind(와 band)를 붙인 표를 테스트로 고정한다(73/73).

## 5. 직접 답과 근거 — `apps/agent/domain/services/question_answer.py` (순수, stdlib)

유형마다 Strategy 클래스 하나, 공통 추상 기반:

```python
class TopicAnswer(ABC):
    def lead(self, facts: dict, topic: QuestionTopic) -> str: ...      # 첫 문장 (공통 구현 + 유형별 머리말)
    @abstractmethod
    def evidence(self, facts: dict, topic: QuestionTopic) -> list[str]: ...  # 근거 1~3줄
```

`answer_lead(facts, topic) -> str` — kind → Strategy 표(dict)로 고르고 `lead` + 근거 줄을 마크다운으로 잇는다.
`report_sections.py`의 원칙을 그대로 따른다: 숫자에는 범위(무엇의·어디의·언제의), 자료가 없으면 `missing(이유)`, 태그는 코드가 붙인다(정형 `[확인된 사실]`, 뉴스 `[참고 신호]`).

### 5-1. 첫 문장 (판정 등급 → 문장, 공통)

| 판정 | 문장 |
|---|---|
| red | "{머리말} {동} {업종}은 권하지 않습니다 — 비추천 신호 N개({켜진 신호 이름})." |
| orange | "{머리말} {동} {업종}은 조건부입니다 — {켜진 신호 이름}을 먼저 확인해야 합니다." |
| clear | "{머리말} {동} {업종}은 경고 신호가 없습니다 — 다만 이것이 장사가 된다는 근거는 아닙니다." |

- 머리말: 질문 맥락 한 마디 — budget "예산 {금액}으로 보면", loan "대출을 끼고 시작한다면", hours "{구간} 위주로 보면", 나머지는 없음.
- budget은 문장 끝에 "예산이 충분한지는 이 리포트로 판단할 수 없습니다."를 덧붙인다 — 판정을 예산 탓으로 읽지 않게.
- 신호 이름은 `report_sections._SIGNAL_LABELS`, 등급 라벨은 `_VERDICT_LABELS`를 그대로 쓴다(공개 이름으로 승격). insufficient는 여기 오지 않는다(자료 부족 경로).

### 5-2. 근거 줄 (유형별)

| kind | 근거 줄 |
|---|---|
| general | ① 넘지 않은 경고 기준(꺼진 신호 이름 목록) ② 이 동·업종 점포당 월 평균 매출(분기·점포 수, 단서 "신규 점포는 평균 아래서 시작하는 경우가 많습니다") |
| budget | ① 입력 예산 ② 점포당 월 평균 매출 ③ 권역 상가 임대료 ㎡당 월(권역 경로·R-ONE, 단서 "행정동 자료 없음 — 권역 평균") ④ "보증금·권리금·인테리어 비용 자료가 없어 예산이 충분한지는 판단할 수 없습니다 — 자금 계획 화면에서 계산하세요." |
| loan | ① 공시 평균 대출 금리(ECOS 기준월, "예상치 — 실제 심사 금리와 다릅니다") ② "대출 원리금은 매출과 관계없이 매달 나갑니다 — 자금 계획 화면에서 상환액을 넣어 손익분기를 확인하세요." 은행·상품 이름은 쓰지 않는다(응답 규칙 ③) |
| hours (band≠weekend) | 묻는 구간의 사람 흐름·업종 매출 강도 — "{구간}({동} 유동인구·{업종} 매출, {분기}): 사람 흐름은 시간당 하루 평균의 {x}배, 매출은 {y}배". 구간이 원천 6구간 여럿이면(밤=21_24·00_06) 각각 한 줄. `hour_gap` 자료가 없으면 자료 부족 줄 + 동 사람 흐름(가장 많은 때·적은 때, `profile`) |
| hours (weekend) | "주말({동}, {분기}): 주말 하루 유동인구는 평일 하루의 {x}배 — 같은 유형({유형명}) {n}개 동 중앙값 {m}배" |
| competition | ① 포화 신호 근거(`verdict.signals[saturation].evidence` 그대로) ② 점포 수 추이 — 최근 3개 연도 연말 점포 수(`metrics_history`) ③ 순유출 신호 근거(최근 12개월 개업·폐업) |
| customers | ① 주민 연령 구성(`population`, 기준월) — 60세 이상·20~39세 비율 ② 유동인구 연령 상위 2구간(`profile.footfall_age_mix`) ③ 직장인구/상주인구 비. 질문에 외국인·중국인이 있으면 "외국인 주민·방문객 자료는 없습니다." 줄 추가(질문 전제를 사실로 받지 않음, 응답 규칙 ①) |
| covid | ① 2019~2023년 연간 폐업률 한 줄(`metrics_history`) + 재난지원 왜곡 단서(`_DISASTER_NOTE`) ② 최근 완결 연도 폐업률 |

- 매출·임대료·금리는 `facts.finance`(§7)에서 온다. 값이 null이면 그 줄은 `missing(이유)`.
- 근거 줄이 본문 절과 겹쳐도 된다 — 상자는 질문에 대한 답이다.
- 백분율·배수 표기 자릿수는 `report_sections`의 기존 표기를 따른다.

## 6. 본문 보강 — "그래도 한다면"(conditions)에 두 줄 (모든 리포트)

1. **거주민 줄**: "[확인된 사실] 주민({동}, {기준월} 주민등록): 60세 이상 {a}%, 20~39세 {b}% · 아파트 평균 시가 약 {c}억 원(동별 편차가 커 참고값입니다)." — `population`·`profile.apartment_avg_price_won`. 없는 값은 그 부분만 자료 부족.
2. **뉴스 줄**: "[참고 신호] 이 동네 이름이 나온 최근 뉴스: {제목}({날짜}) · …" 최대 3건 — `facts.news` 중 **기사 본문에 동 이름(번호·"제"·"동" 뗀 어간, 예: 상도제1동→상도)이 든 것만**, 최신순. 해당 기사가 없으면 줄을 뺀다(150건 중 61건에 해당 기사 있음 — 나머지 뉴스는 다른 구 기사가 섞인다).

LLM 지시에 추가: "뉴스는 [참고 신호]라고 밝히고만 쓴다. 뉴스로 판정·직접 답을 바꾸지 않는다."

## 7. facts 변경 (프론트 계약 — 선택 필드)

- `budget`: 폼 예산이 없고 질문에 금액이 있으면 질문 속 금액. 파싱은 의도 관문의 `parse_budget`을 agent 게이트웨이로 감싸 재사용한다(기존 agent 게이트웨이가 타 BC `dependencies`·도메인을 import하는 패턴). 폼 예산이 있으면 폼 값 우선.
- `finance` **신규 키**(`FACTS_KEYS` 맨 뒤): 자금 계획 프리필(`FinanceUseCase.prefill`)의 `expected_monthly_revenue`·`rent_per_m2`·`loan_rate`를 `{value, unit, basis, caveat}` 그대로. 실패는 다른 항목처럼 `{"available": false, "reason": ...}`. 항상 수집한다(조회 1건, 병렬 수집 안).
- `report_facts.ReportFactsCollector`에 포트 2개 추가: `FinanceFactsPort.prefill(region, industry)`, `QuestionBudgetPort.parse(question)`.

## 8. 해석 LLM 입력과 지시 — `analysis_interactor.py`

질문이 있고 자료 부족 동네가 아닐 때 사용자 메시지:

```
분석 지역: … / 업종: …
사용자 질문: …
질문 유형: {kind 한국어 이름}
[이미 화면에 나간 직접 답과 근거]   ← answer_lead 그대로
[리포트 본문]                       ← 6개 절
```

SYSTEM_PROMPT 변경(질문 있는 경우):
- "직접 답(첫 문장)과 근거는 이미 위에 있다. 그 답이 왜 그런지 본문을 근거로 **2~3문장** 해석한다. 직접 답을 되풀이하지 않는다."
- "직접 답의 결론을 뒤집거나 흐리지 않는다(예: 권하지 않는다를 '해볼 만하다'로)."
- 숫자 금지·판정 등급 유지·자료 부족 추정 금지·응답 규칙 ①②③ — 지금과 같다. 뉴스 규칙 §6 추가.

질문이 없을 때는 지금 SYSTEM_PROMPT·메시지와 같다(총평 3~5문장) — 뉴스 규칙만 추가.
가드(`guard_answer`)는 LLM 부분에만 — 지금과 같다. 코드 줄의 숫자는 가드 대상이 아니다.

## 9. 프론트 (Codex 위임)

- 리포트 맨 위를 **"질문에 대한 답" 상자**로: `answer_lead`(코드, 즉시) 위, 그 아래 "AI 해석" 라벨과 `answer`. `answer_lead`가 없으면(질문 없음·자료 부족·옛 리포트) 지금 모양 그대로.
- 해석 대기 중에는 상자 안 "AI 해석" 자리에 자리 표시(높이 확보) — HANDOFF §0-14 2번 화면 항목 중 이 상자에 해당하는 것만.
- `shared/api/types.ts`에 `facts.finance`(선택)와 `answer_lead` 절 추가, mock 라우트·픽스처·계약 테스트 맞춤.
- 저장 리포트 재열람 경로도 `answer_lead`를 읽는다(없으면 생략).

## 10. 평가

### 10-1. 결정적 검사 (단위 테스트, LLM 없음)
- `question_topic`: 평가셋 질문 73개 기대 유형 표 — **73/73**. 질문 없음·공백 → None.
- `question_answer`: 유형마다 판정 3등급 첫 문장, 근거 줄의 자료 있음/없음(`missing(이유)`) — 요청된 동작만.
- 본문 두 줄: 거주민 줄 값 있음/없음, 뉴스 줄 동 이름 필터(있음/없음 → 줄 생략).
- 벤치 `sections-check`가 `answer_lead`도 검사 — 범위 없는 숫자 줄 0, 자료 부족 이유 누락 0(150건).

### 10-2. LLM 재평가
`benchmark_report run/score --scenario-set 150 --cache-tag topic150` — gemini-2.5-flash·gemma4:12b 각 150건, 온도 0·seed 42.
- 얼린 facts(`data/eval/report_facts_150/*.json`)에는 `finance`와 질문 속 예산이 없다. **다시 얼리지 않고 두 키만 보강**한다(`freeze --augment` 같은 하위 명령 — 다른 키는 그대로 둬 이전 결과와 비교 가능하게). `finance`는 현재 DB의 프리필, `budget`은 시나리오 질문에서 파싱(폼 예산 없음).
- 해석 핵심 오류(Claude 판정, 자료 부족 34건 제외 116건): 현재 Gemini 17.2%(10.9~25.4%)·12b 37.9%(29.1~47.4%)보다 **나빠지지 않을 것**(95% 구간이 겹치면 동등).
- 기록: 폴백, 가드가 지운 문장, 해석 p95(현재 4.4초 — 입력이 근거 줄만큼 는다).

### 10-3. 판정 기준표 v2 — `data/eval/report_answer_rubric.md`
- `answered`: 답 상자 전체(첫 문장·근거·해석)를 본다. **질문의 구체 요소(금액·시간대·경쟁·대상 고객·대출·코로나)에 대한 근거 또는 "판단 불가 + 이유"**가 있으면 답함, 일반론뿐이면 못 답함.
- `core_error`: LLM 해석만 본다. 기존 항목 + "**코드 첫 문장의 결론을 뒤집거나 흐림**".
- 판정 묶음(packet)에 `answer_lead`를 넣는다.

### 10-4. 사람 검수 3차 (완료 기준의 중심)
- 2차와 같은 시나리오 중 **질문 있는 16건**, 운영 기본 Gemini 하나. 화면: 질문 → 답 상자(첫 문장·근거·AI 해석). 묻는 것은 "질문에 답했나(예/아니오) + 메모"뿐 — 1·2차 모두 사람이 채우지 못한 핵심 오류 칸은 두지 않는다. 비공개 artifact + db.
- **목표: 답함 12/16 이상**(2차 4/16).

## 11. 완료 기준

1. 백엔드·프론트 테스트 전부 통과.
2. 유형 분류 73/73.
3. 코드 절 검사(`answer_lead` 포함) 문제 0.
4. LLM 해석 오류율 비악화(§10-2).
5. 사람 3차 답함 12/16 이상.
6. 버전 로그(BE v0.69.0·FE minor) 기록, main 머지는 사용자 결정.

## 12. 영향 파일 (예상)

- 신규: `apps/agent/domain/services/question_topic.py`, `question_answer.py`(+ 테스트), `apps/agent/adapter/outbound/gateways/finance_facts_gateway.py`, `question_budget_gateway.py`
- 변경: `report_sections.py`(conditions 두 줄, 라벨 공개), `report_facts.py`(finance·budget), `agent_port.py`(포트 2개), `analysis_interactor.py`(answer_lead·메시지·지시·폴백), `section_stream.py`(순서), agent `dependencies`(배선), `benchmark_report`(sections-check·facts 보강)·`report_bench_scoring`(packet), `data/eval/report_answer_rubric.md`
- 프론트: `shared/api/types.ts`, `features/agent-report/*`, `app/api/mock/*`
