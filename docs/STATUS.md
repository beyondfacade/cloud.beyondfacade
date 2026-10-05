# STATUS — 실DB 기준 현재 상태 (정본)

> **작성 2026-09-24 09:40 KST · `main` = `origin/main` = `881626e`**
> 이 문서는 문서·메모를 믿지 않고 **DB·크론 로그·git을 직접 재서** 만든 것이다. 오늘 하루에만 낡은 기록
> 때문에 서브에이전트에 틀린 전제를 세 번 넘겼다(SGIS·fp16·`operating_months` 범위). 그 반복을 끊기 위한
> 단일 정본이다. `docs/HANDOFF.md`(9/22판)와 `RESUME-260923.md`는 **이 문서로 대체**된다.
>
> **갱신 규칙**: 상태를 물을 일이 생기면 이 문서를 고치기 전에 §1의 방법으로 DB를 다시 잰다. 문서는 결과지,
> 원천이 아니다.

## 0. 30초 요약

| 영역 | 상태 |
|---|---|
| 로드맵 T0~T4 (관문 → 무대 → 계획 → 조달·준비) | ✅ **전부 `main`에 병합·푸시** |
| 테스트 | 백엔드 **505 passed** · 프론트 **280 passed** · E2E 11단계 **`881626e`에서 전 구간 통과**(9/24 09:45) |
| 데이터 | 36테이블, 약 1,050만 행. 서울 상권분석서비스 계열 999만 + 인허가·마스터·RAG |
| 운영 크론 6종 | 전부 오늘(9/24) 정상 실행 |
| **결함 발견 (오늘)** | ① 테스트가 dev DB를 직접 쓰던 것 — **9/24 수정, v0.35.2, `beyondfacade_test`로 격리**(§4-1) · ② 도커 8200 — **9/24 재빌드 완료(v0.35.3 이미지)** · ③ 학원 폐업률 0 → **9/24 NULL로 통일, BE v0.35.3/FE v0.24.1**(§4-3) |
| 사람 판단이 필요한 것 | **앱 실배포 미완**(Vercel 프로젝트·터널 토큰 없음, §4-6) · 브랜치 삭제·AWS 쿼터 결정. 그 외는 §4-5 외부 대기 |

## 1. 재는 방법 (이 문서를 다시 만들 때)

```bash
cd backend
# 전 테이블 행수·시점범위
.venv/bin/python - <<'PY'
from sqlalchemy import text; from core.matrix.grid_oracle_database_manager import get_engine
with get_engine().connect() as c:
    for (t,) in c.execute(text("select table_name from information_schema.tables where table_schema='public' order by 1")):
        print(t, c.execute(text(f'select count(*) from "{t}"')).scalar())
PY
crontab -l | grep beyondfacade            # 크론 6종
for f in logs/*.log; do tail -2 $f; done   # 마지막 실행
git log --oneline -1 main; git status --short
.venv/bin/python -m pytest -q | tail -1; (cd ../frontend && npx vitest run 2>&1 | grep "Tests ")
```

## 2. 데이터 — 테이블별 (실측 2026-09-24)

범례: ✅ 완료·사용 중 / 🟡 부분 / ⚪ 설계상 빈 테이블 / ❌ 미완

### 2-1. 마스터 (master BC)

| 테이블 | 행 | 상태 | 비고 |
|---|---:|---|---|
| region | 427 | ✅ | 행정동 10자리. 이름 중복은 `신사동`(강남·관악)뿐 — 관문 파서 근거 |
| district | 25 | ✅ | |
| industry | 10 | ✅ | academy·billiard·cafe·childcare·convenience_store·gym·hair_salon·karaoke·pc_bang·real_estate |
| industry_source_code | 25 | ✅ | seoul_commercial 16행 포함(cafe 3코드·hair_salon 3코드 — v0.26.0 보정) |
| industry_subcategory | 8 | ✅ | |
| population_stat | 142,632 | ✅ | 201912~**202606**. 2026.07분은 공표 확인 후 1파일 추가(외부 대기) |

### 2-2. 인허가·점포 (store BC + 스냅샷 BC)

| 업종 | 총 | 좌표 | region | 영업중 | 폐업 | 상태 |
|---|---:|---:|---:|---:|---:|---|
| cafe | 147,291 | 141,006 | 140,998 | 36,902 | 110,389 | ✅ |
| hair_salon | 99,737 | 93,744 | 93,741 | 33,592 | 66,145 | ✅ |
| real_estate | 25,435 | 25,299 | 25,281 | 24,798 | 637 | ✅ 폐업은 스냅샷 소실 추정(9/7~) |
| academy | 25,554 | 25,504 | 25,504 | 25,554 | **0** | ✅ 원천에 폐업 이벤트가 없다 → 9/24부터 폐업률·성장률 NULL(childcare와 동일 규칙, §4-3) |
| pc_bang | 16,853 | 16,305 | 16,305 | 4,502 | 12,351 | ✅ |
| billiard | 14,038 | 13,209 | 13,209 | 2,661 | 11,377 | ✅ |
| karaoke | 12,803 | 12,315 | 12,315 | 5,558 | 7,245 | ✅ |
| gym | 7,332 | 7,144 | 7,143 | 4,488 | 2,844 | ✅ |
| korean_food | 226,118 | 211,434 | 211,429 | 52,604 | 173,514 | ✅ 9/28 적재 (인허가 일반음식점 → 업태 분류기) |
| snack | 82,817 | 75,013 | 75,012 | 7,912 | 74,905 | ✅ 9/28 |
| restaurant_other | 71,091 | 69,105 | 69,103 | 23,571 | 47,520 | ✅ 9/28 **비노출** — 폐업 마커·포화 분모용 |
| western_food | 56,427 | 52,993 | 52,992 | 10,982 | 45,445 | ✅ 9/28 |
| pub | 52,114 | 49,568 | 49,567 | 10,991 | 41,123 | ✅ 9/28 |
| japanese_food | 23,753 | 22,755 | 22,755 | 7,624 | 16,129 | ✅ 9/28 |
| chinese_food | 17,389 | 16,177 | 16,177 | 4,849 | 12,540 | ✅ 9/28 |
| chicken | 9,403 | 9,033 | 9,033 | 1,600 | 7,803 | 🟡 9/28. **최근 개업 2017-09-25** — 인허가 '통닭' 업태가 그 뒤 신규 발급 없음(설계서 §3-3) → 인허가 기반 신호에서 제외 |
| **store 합계 (9/28 실측)** | **888,308** | | | | | 9/24 349,043 + 음식 539,112(영업 120,133 · 폐업 418,979). 최근 개업 2026-09-23. 음식 좌표 결측 약 5~7%(한식 14,684행 등)는 원천이 좌표를 안 준 행 — 지오코딩 대상 포함 여부는 미결정 |
| academy_course | 64,415 | | | | | ✅ |
| childcare_center / _stat | 3,940 / 7,880 | 좌표·region 100% | | | | ✅ 스냅샷 2회(9/17·9/21), 주간 크론 |
| convenience_store | 9,395 | 100% | | | | ✅ 스냅샷 9/21, 주간 크론 |
| tobacco_retailer | 95,402 | | 85,948 (90.1%) | | | ✅ 편의점 출점 축. 미배정 10%는 좌표 부재 |

판정 원천(9/29, BE v0.46.0): `region_industry_verdict.basis` — `permit`/`proxy`(편의점 = 담배소매인 에피소드 21,126개, 기준일 2026-08-21)/`aggregate`(부동산 = 상권분석 CS200033, 개업 수 2024Q1~ 단절). 판정 대상 12종 — 재포함 게이트 미달(편의점 경고 lift 1.00×·부동산 1.04×, 기준 1.10×)로 실DB 배치 5,124건(427동×12업종)은 전부 `basis=permit`.

**SGIS 지오코딩은 완료됐다.** 학원·부동산 99.5~99.8% 좌표. 미좌표 잔여는 지오코딩 실패가 아니라 **주소 자체가 없는 행**(학원 50 중 46, 부동산 136 중 134)과 폐업 업소다. 키는 `backend/.env`에 있고 실호출 검증됨(9/24). 배치 중단 버그(불량 주소 `-200` → 예외) 수정 `8e47dbd`.

### 2-3. 집계·파생 (metric BC)

| 테이블 | 행 | 범위 | 상태 |
|---|---:|---|---|
| region_industry_metric | **55,093** (9/28) | 2019~2026 · **18업종**(음식 8종 27,264행 추가) | ✅ 매일 04:20 재집계. **어린이집·편의점은 2026 점포수만**(스냅샷 원천, 폐업률·성장률 NULL) — 화면이 `metric-coverage.ts`로 연도 보정·안내(v0.24.0) |
| region_profile_quarter | 9,284 | 20211~20262 · 422동 | ✅ 유형 6종·시간대 라벨·근거 7지표·4블록 강도. 배치 `build_region_profiles`(33초) |
| region_industry_hour_gap_quarter | 342,078 | 20211~**20254** · 9업종 | ✅ 매출이 20254까지라 여기까지. 패널 차트용(단계구분도 아님) |

### 2-4. 상권·동네 맥락 (commerce·neighborhood BC — 서울 상권분석서비스, 정적 아카이브)

| 테이블 | 행 | 범위 | 상태 |
|---|---:|---|---|
| region_commerce_sales | 343,167 | 20211~20254 | ✅ |
| region_commerce_sales_breakdown | 7,892,841 | 20211~20254 | ✅ 요일·시간·성별·연령. **성별·연령은 금액 89.2%만** — 구성비로만 쓴다 |
| region_commerce_store | 704,470 | 20211~20254 | ✅ |
| region_commerce_change | 9,350 | 20211~**20262** | ✅ 영업/폐업 개월·변화 4종. 지도 `operating_months` 원천 — **22분기 전량, 공백 없음** |
| seoul_commerce_change_baseline | 22 | 20211~20262 | ✅ 서울 평균(분기당 1행) |
| region_footfall_quarter | 205,700 | 20211~20262 | ✅ |
| region_population_quarter | 387,618 | 20211~20262 | ✅ **직장인구는 414동(11동 결측 → 0으로 읽지 말 것)** |
| region_household_quarter | 149,353 | 20211~20262 | 🟡 **아파트 가구 수 컬럼 전 행 0**(원천 미제공) |
| region_housing_average_quarter | 9,331 | 20211~20262 | ✅ 평균 시가는 편차 극단 — 참고값 |
| region_facility_quarter | 187,000 | 20211~20262 | ✅ **`total` ≠ 19종 합**(더 넓은 정의), `train_station` 전 행 NULL |
| region_spending_quarter | 102,850 | 20211~20262 | ✅ **KB카드 가맹점 매출(발생지)**이지 주민 지출이 아님 |

### 2-5. 정책·시장 신호 (funding·news·shock·rent BC)

| 테이블 | 행 | 상태 | 비고 |
|---|---:|---|---|
| funding_program | 2,068 | ✅ | 기업마당, 매일 05:10. 만료 510·미만료 1,558(상시 980). **§4-1 결함 참조** |
| news_article | 5,824 | ✅ | 매시 10분, 최근 24h 166건 |
| shock_event / _industry | 26 / 107 | ✅ | 거리두기·정책 26건 |
| shock_event_region | 0 | ⚪ | region 범위 이벤트가 0건이라 **설계상 빈 테이블** |
| interest_rate | 365 | ✅ | ECOS base(202608)·loan_corp·loan_facility·loan_sme(202607). 주 1회 |
| rent_price | 3,638 | ✅ | R-ONE 2019Q1~2026Q2. **상권(83)·권역(4) 단위, 동 매핑 없음** → finance 프리필은 구→권역 근사 |

### 2-6. RAG·에이전트 (rag·agent BC)

| 테이블 | 행 | 상태 | 비고 |
|---|---:|---|---|
| rag_chunk | 8,905 | ✅ | news 6,640 + funding 2,265. **전량 `bge-m3`**(vector(1024), 10/4 전량 재색인 — GPU 101초). `region_code` 컬럼은 0건(미사용) |
| analysis_report / llm_usage | 21 / 21 | ✅ | 모델별 gemma3 1 · gemma4 18 · **gemini-2.5-flash 2**(v0.35.0 혼합 배선 이후) |

## 3. 파이프라인·크론 (전부 오늘 9/24 정상)

| 크론 | 일정 | 마지막 실행 | 결과 |
|---|---|---|---|
| news-poller | 매시 10분 | 09:10 | 신규 4건 |
| store-collector | 04:20 | 04:32 | 지표 27,829건 재집계 |
| funding-collector | 05:10 | 05:10 | 신규 36 · 만료 510 |
| rag-indexer | 05:50 | 05:50 | 증분(`--provider bge-m3`, 10/4 전환) |
| childcare-collector | 월 05:30 | 9/21 | 3,940건 |
| convenience-collector | 월 05:40 | 9/21 | 9,395건(API 427회) |

`refresh_expirations`는 크론 안에서 정상 동작한다(커밋됨). 되돌리는 건 크론이 아니라 **테스트**다(§4-1).

## 4. 안 된 것 · 결함 · 판단 대기

### 4-1. ✅ 테스트가 dev DB를 직접 쓴다 — 9/24 발견, **9/24 수정 (백엔드 v0.35.2)**

`backend/tests/conftest.py`가 없어 `session_scope`·`SqlAlchemy*Repository`를 직접 여는 테스트가
`.env`의 dev DB(5434)에 썼다. 증명: `test_funding_expiry.py`가 `refresh_expirations(date(2026,9,7))`를 부르면
"연장 복원" 절이 9/7 이후 마감 행을 전부 `is_expired=False`로 되돌린다 — 단독 실행으로 **510 → 0 재현**,
배치 재실행으로 복구(9/24 09:35). T4-1이 "크론이 안 돈다"고 오판한 원인이다.

**수정(9/24)** — 대구 `conftest.py` 이식 + 마이그레이션 2건 손질:
- `backend/tests/conftest.py`: 앱 import 전 `os.environ["DATABASE_URL"]`을 `beyondfacade_test`로 강제
  (`get_settings.cache_clear()`), session autouse 픽스처가 DB 생성(없으면) → `alembic upgrade head` → `seed_all()`.
  개발 DB를 가리키면 assert로 중단.
- `66a23fb0c6e9` rag_chunk에 `CREATE EXTENSION IF NOT EXISTS vector` 추가. `c7a4f2e19b35`·`a4e7b2c9d813`의
  `industry_source_code` bulk_insert는 `industry`가 비어 있으면 건너뛴다(빈 DB에서 FK 위반 → 전체 롤백 방지).
- 검증: `beyondfacade_test` DROP 후 `pytest tests` 한 번에 **505 passed (7.05s)**, dev `funding_program`
  expired **510 유지**, 재실행 멱등. 이제 전체 pytest 후 플래그 복구가 필요 없다.
- 남는 것: 빈 DB엔 `seoul_commercial` 업종 코드(16행)가 시드되지 않는다 — 테스트는 의존하지 않고 dev DB엔
  이미 있다. 새 환경을 세울 일이 생기면 `seed_master`로 옮긴다.

### 4-2. ✅ 도커 `beyondfacade-api`(8200) — 9/24 재빌드
9/23 22:40 이미지(≈`73cc401`)가 25커밋 낡아 `/intent`·`/finance`·`/hour-gaps`·`/profiles/types`·
`/commerce-changes/{region}`·혼합 LLM이 없었다. 9/24 `docker compose build backend && up -d backend`로 v0.35.3
기준 재빌드 — openapi 39 paths, 위 5종 확인. 8201(uvicorn `--reload`, 메인 체크아웃)이 개발 정본인 건 그대로.
main이 전진하면 다시 낡는다 — 배포 전 재빌드가 규칙.

### 4-3. ✅ 학원 폐업률 0은 값이 아니다 — **9/24 수정 (백엔드 v0.35.3 · 프론트 v0.24.1)**
`store.academy`에 `close_date`가 한 건도 없다(원천 서울 학원 API가 폐업을 안 준다). 집계가 그걸 폐업률 **0.0**으로
세어 학원 3,388행에 값이 있었다 — 어린이집·편의점은 같은 이유로 NULL인데 학원만 0이라 비일관.
**수정**: `StoreStatsGateway`가 학원의 `close_count`를 None으로 주고 인터랙터가 비율도 None으로 둔다. dev DB
재빌드로 학원 3,408행 전부 closure_rate·growth_rate NULL. 프론트는 `NO_CLOSURE_HISTORY_INDUSTRIES`(스냅샷 2종 +
학원)로 셀렉터 안내·mock을 맞췄다. 학원 점포수는 전 연도에 그대로 있다(스냅샷과 다른 점).
남는 사실: 학원 원천은 현재 "개원" 상태만 준다(25,554행 전부) — 원천에서 사라진 학원은 store에 남는다.

### 4-4. 사람 판단 대기
- **RAG 평가셋 검수 — 9/24 완료.** `data/eval/rag_evalset.jsonl` 50건(gemma3:12b 생성, 9/15) → Claude 1차 판정
  (`judge_evalset`, Opus 5) O 40 / X 10 → 사람 검수가 판정 기준을 하나로 통일하며 10건 뒤집음 → **confirmed 30 /
  rejected 20**. 기준(v0.36.2 프롬프트에 박음): 질문만으로 이 공고가 다른 유사 공고보다 우선 정답이어야 O, 여러
  공고가 자연스럽게 정답이면 X, 통합공고도 예외 없음. 본지표 — **fp16 Recall@5 1.000 · MRR 0.923 / ollama 1.000 ·
  0.900**. 뉴스 청크는 여전히 0건.
  선택 사항: X 20건은 시트(`rag_evalset_review.md`)의 제안 질문을 채택하면 O가 된다(질문 줄 수정 후 `review_evalset
  apply`). 48·49번(경북 융자 2건)은 O지만 서로 검색될 여지가 있어 제안 문구로 보강 권고.
- **평가셋 확장(9/24 저녁, v0.37.0)** — funding 110 + news 40 추가 → **200건**(candidate 150, 시트 51~200번).
  처음엔 gemma3로 생성했다가(38b65c9) 사용자 요청으로 **Claude(세션)가 문서 카드를 읽고 150건을 직접 다시 썼다**
  (단일 기준 적용, 24~45자). fp16 자체 점검: top-5 적중 142/150, 1위 123/150 — 놓친 8건은 전부 뉴스(같은 사건
  기사 여럿·corpus 잡음). 뉴스 40건은 처음 들어간 뉴스 표본이라 인사·분양·팝업 등 상권 무관 기사가 많고, 같은 사건을
  다룬 기사가 3~7건인 항목 8건엔 시트에 "작성 메모"를 달았다(단일 기준상 X 가능성).
  **9/24 밤 외부 판정 2종 수신** — Claude Fable(`data/eval/재판정_51-200.md`)·ChatGPT(`51-200_재평가_결과.md`) 둘 다
  **O 141 / X 9, X 집합 동일**(155 인천 누락 + 뉴스 동일 사건 중복 8건). 그대로 반영 → **confirmed 171 / rejected 29**.
  본지표(171건): fp16 Recall@5 0.971·MRR 0.899 / ollama 0.971·0.895. 원천별(fp16): funding 139건
  R@5 1.000·MRR 0.973, news 32건 R@5 0.844·MRR 0.578.
  **9/24 밤 결정 2건 실행(v0.37.1)**: ① 뉴스 다중 정답 — 40건 중 29건에 같은 사건 기사를 relevant_ids로 묶음
  (2~51건), 지표를 Hit@5로 전환, 보류 8건 해소. 뉴스 MRR 0.578→0.865(측정 왜곡이었음). ② 수치 과다 질문 10건 +
  155번 완화 → **candidate 11건 재판정 대기**(시트에 "재판정 필요" 표시, 외부 판정 md로 받으면 반영).
  → 완화 11건 외부 재판정 **전부 O**(9/24 밤): confirmed 180, fp16 Hit@5 1.000·MRR 0.946 / ollama 1.000·0.942.
  같은 기준으로 수치 2개 이상 남은 9건 중 6건(78·104·105·120·137·138)을 2차 완화 → 외부 재판정 **전부 O**.
  131·132·141은 같은 시 유사 공고와 수치로만 갈려 유지. **평가셋 검수 종료: confirmed 180 / rejected 20 / candidate 0.**
  남은 관찰: GPT 지적한 뉴스 `matched_keyword`는 수집 키워드일 뿐 NER 태그가 아니라 평가엔 무관 — 뉴스를 지역 신호로
  쓸 때 본문 지역 추출이 따로 필요.
  **9/25 v0.38.0 — 뉴스 검색 시점 같은 사건 접기 적용**(제목 Jaccard 0.3·3일 창, 뉴스만 top_k×10 후 접기). 뉴스 40문항
  top-5의 같은 사건 기사 평균 2.98→2.00, 5/5 문항 12→4, Hit 손실 0. 더 공격적인 규칙(임계 완화·앵커·임베딩 코사인·
  요약 J)은 전부 Hit을 깎아 기각. 남은 대형 보도자료 4건은 수집 시 사건 클러스터링이 필요(후속).
- **임베딩 모델 평가(10/4)** — 9조합(bge-m3, qwen3, gemini-001, gemini-2 × 차원)을 같은 코퍼스·평가셋으로 비교(spec `docs/superpowers/specs/2026-10-04-embedding-benchmark-design.md`).
  평가셋 재검수 후 confirmed 233(base 179 + hard 54) / rejected 27 — 9/24 수치와 직접 비교 불가.
  로컬: **qwen3@1536 유지**(bge-m3@1024와 bootstrap 동률, 교체 근거 없음). API: **gemini-001@1024**(규칙상: 6조합 동률 → 1024차원 둘 중 p95 짧은 쪽; 001은 2028-05-14 단종 예정, 동률인 gemini-2@1024가 실무 대안).
  gemini-2 1회 색인 약 $0.31(표준), gemini-001은 가격표에 없음. 보고서: `data/eval/results/embedding-benchmark-2026-10-04/report.md`.
  **최종 결정(10/4): 운영 임베딩을 bge-m3@1024(Ollama, 색인·질의 동일)로 전환** — qwen3@1536과 MRR 동률(0.940 vs 0.935, +0.005 [−0.018, +0.028]), GPU 메모리 664MB vs 4.4GB, CPU만으로도 운영 가능(질의 p95 149ms, GPU 대비 코사인 ≥0.99998).
  마이그레이션 `c7a3f1e8d204` 적용·8,905건 전량 재색인(101초) 후 운영 평가(confirmed 233): Hit@5 0.983 / MRR 0.930 (전환 전 qwen3 운영 0.991 / 0.930, `data/eval/results/rag_bge-m3_20261004_231013.json`). 기존 테이블 백업 `data/backups/rag_chunk_qwen1536_20261004.dump`(gitignore).
- **LLM 모델 평가(10/5)** — 평가셋: 리포트 12 시나리오×3회, 관문 80건(confirmed). 결과: **두 역할 모두 엄격 게이트를 통과한 로컬 모델 없음**. 리포트는 로컬 전원 탈락(Gemini도 규칙 게이트 탈락, 주로 신뢰 등급 표기). 관문은 스펙 범위(missing·out_of_scope 26건) 지어내기로 gemma4:12b 0.077 탈락(이전 범위 0.039 — 서울 밖 지명을 서울 동으로 채움 2건), Gemini는 통과(0.988).
  참고(결정 아님): 리포트 품질 12b 6.00 vs e4b 5.42 동률(+0.58 [−0.17, +1.25]) → VRAM 우선 e4b, 관문 로컬 최고 12b(0.887). 로컬 채택 전 프롬프트·형식 작업(신뢰 등급 태그, 공고 번호·URL 그대로 옮기기) 후 재측정 필요 — 트레이드오프는 `notes.md`.
  운영 버그(10/5 해소, v0.66.1): 운영 Ollama 폴백(`analysis_dependencies._local`)이 num_ctx 없이 호출해 Ollama 0.31.2 기본값으로 약 2k 토큰만 읽던 문제(§4-4-2). 보고서: `data/eval/results/llm-benchmark-2026-10-05/report.md`·`notes.md`(spec `docs/superpowers/specs/2026-10-04-llm-benchmark-design.md`).
- 두뇌 비교(`data/eval/results/agent_compare.md`)로 리포트는 **혼합(Gemini 우선·로컬 폴백)** 채택 완료.

### 4-4-1. 도커 컨테이너에서 호스트 Ollama 접근 불가 — 10/4 해소 (v0.65.1)
`beyondfacade-api`(8200) 컨테이너에서 Ollama 어댑터 기본 주소 `http://127.0.0.1:11434`로는 호스트 Ollama에 닿지 못했다(ConnectError, bge-m3 전환 전부터 있던 문제).
`Settings.ollama_base_url`(env `OLLAMA_BASE_URL`, 기본 127.0.0.1)로 바꾸고 compose에 `OLLAMA_BASE_URL=http://host.docker.internal:11434` + `extra_hosts: host-gateway`를 넣었다.
재빌드 후 컨테이너에서 RAG 검색 3건·운영 점검 Ollama 도달(모델 12개) 확인.

### 4-4-2. 운영 Ollama 폴백 컨텍스트 잘림 — 10/5 해소 (v0.66.1)
`analysis_dependencies._local`이 num_ctx를 지정하지 않아 Ollama 0.31.2 기본 컨텍스트로 호출된다. 실측(10/5, 약 29,400자 한국어 합성 입력): 기본 컨텍스트에서 qwen3.5:4b prompt_eval_count 2,050, gemma4:12b 2,051 — num_ctx 32,768에서는 qwen3.5:4b 17,422. 즉 기본값은 입력을 약 2k 토큰에서 잘라 읽는다(합성 입력 수치이며 리포트 프롬프트 자체의 크기가 아님). 실제 리포트 첫 턴 프롬프트는 num_ctx 32,768에서 13.1k~14.1k 토큰으로 실측(도구 없이 13,111, 도구 포함 14,143)이라 운영 폴백은 facts 대부분이 잘린 채 리포트를 쓴다. 벤치마크는 num_ctx 32,768로 측정. 해소: 폴백 어댑터(`_local`)와 운영 점검 프로브에 num_ctx 32,768 지정(bge-m3와 동시 상주 9.8GB 실측). 두 상수는 테스트가 같음을 고정한다.

### 4-5. 외부 대기·자료 한계 (코드로 못 푸는 것)
- 주민등록 인구 2026.07분 공표 후 1파일 추가
- 임대료 동 단위 해상도(국토부 상업용 실거래가 — 포스트MVP)
- 서울신보·금감원 공시 금융상품 정본(T4-3 조사) — 현재 후보는 기업마당 92건 풀 + ECOS 금리뿐
- 지출 항목 구성비(본사·온라인 가맹점 필터 필요)
- 카탈로그 전환: 지표 7개·드리프트 없음 → 아직 아님(`specs/…map-metric-contract.md` §6). 단 여섯 번째
  "지표당 아는 것"이 (업종,지표) 쌍이라 전환 시 `map_metric` 한 테이블로는 부족(v0.24.0 기록)

### 4-6. 배포·운영 잔여 (9/25 기록 재점검에서 발견 — HANDOFF·로드맵 T5 승계)
- **앱 실배포가 없다.** 프론트는 Vercel 계정(`amysoo02-7611`)에 이 앱 프로젝트가 없고, 백엔드 공개용 Cloudflare 터널은
  compose에 프로필(`--profile tunnel`)만 있고 `.env`의 `TUNNEL_TOKEN`이 비어 있다. `beyondfacade.cloud`는 GitHub Pages 문서만
  200. 배포하려면: Vercel 프로젝트 신설 + `NEXT_PUBLIC_API_BASE` → 터널 도메인 + 터널 토큰 발급 + `cloudflared` 기동.
  현재 서비스는 로컬(3200 → 8201)에서만 돈다.
- **어린이집·편의점 폐업률** — 원천이 폐지 시설을 안 주므로 월간 스냅샷 소실(`last_seen_on` 정지)로만 산출 가능.
  9/25 현재 관측일 **1회(9/21)** 뿐이라 몇 달 누적 뒤 산출 방식을 정한다(시간 대기).
- 사용자 결정: 원격 `origin/feature/analysis-api`·로컬 `feature/frontend-mvp`(둘 다 병합됨) 삭제 여부 · AWS G 인스턴스 쿼터
  신청(8/25 이월 — 로컬 RTX 5060 Ti가 생겨 필요성 재검토) · 외부 판정 md 2개가 작업 트리에서 삭제됨(git엔 커밋돼 있음,
  삭제를 커밋할지)
- 로드맵 T5(fp16 재색인·평가셋 검수·SGIS 키)는 전부 끝났고, 카탈로그 전환 조건 감시만 §4-5에 남아 있다.
  HANDOFF의 "포스트MVP 9건"은 FE v0.14.4에서 전부 처리됐음(코드 대조 9/25).

### 4-7. 대구 분화본 대조 (9/25) — "대구 보고 가져오기" 방향의 잔여
설계서 `chat-first-direction.md` §2가 정한 이식 범위(관문 구조·파서·엔진·상담 준비자료)는 T1~T4로 **전부 끝났다.**
의도적으로 안 가져온 것(위험도 점수·`district` 파라미터·랜드마크 사전·상품 매칭·consultation/product/matching BC)은
설계서·로드맵(T4-1 "상품 매칭이 아니다")에 근거가 있다. 대구에만 있고 **여기서 아직 결정이 없는 것**:
- **실배포** — 대구는 9/20 Vercel + Cloudflare 터널 + systemd 백엔드로 프로덕션 E2E PASS. 런북 `cloud.localhostdaegu/docs/deploy-vercel-cloudflare.md`가 그대로 쓸 만하다. 대구가 배포에서 배운 것: `CORS_ALLOW_ORIGINS`, uvicorn 단일 워커(분석 저장소 인메모리), SSE 프록시 버퍼링 off, 수동 uvicorn 대신 systemd 유닛.
- **모바일 지도** — 대구는 페르소나 테스트 후속(9/19)으로 모바일 지도·조정 안내를 넣었다. 여기 `map-explorer` 컴포넌트엔 반응형 분기가 0개.
- ~~AI 분석 예시 질문 칩~~ — **9/25 FE v0.25.0 이식 완료**(업종별 3개, 섹션 계약에 맞춘 서울 문구, 테스트 7건).
- 정리 대상: `backend/apps/ontology`·`apps/dummy`는 파일 0개인 빈 디렉터리(죽은 골격) · `tobacco` BC는 데이터만 있고 소비처 없음(편의점 대체 산출 안 하기로 결정됨).
"신규 데이터 → 프론트 반영" 축은 36테이블 중 소비처 없는 것이 tobacco뿐 — 나머지는 프로필·지표·finance·agent 도구가 읽는다.

## 5. 코드·기능 — 무엇이 어디까지 됐나

### 5-1. API 15개 라우터 (`backend/main.py`)
`/analysis`(SSE 리포트) · `/intent`(관문 파서+진단) · `/profiles`(동네 프로필·유형·지표 목록) · `/hour-gaps` ·
`/commerce-changes`(지도·상세+서울평균) · `/metrics` · `/regions` · `/stores` · `/finance`(simulate·prefill·questions) ·
`/funding`(목록·candidates) · `/news` · `/shocks` · `/childcare-centers` · `/childcare-center-stats` · `/convenience-stores`

### 5-2. 프론트 4 라우트 · feature 5개
`/`(랜딩+관문 `intent-gate`) · `/map`(`map-explorer`: **판정 단계구분도만** + brief 한 화면 — 9/29 화면 재편 FE v0.31.0, 지표 8개 선택기는 제거) ·
`/plan`(`plan`: 프리필→계산→비교→조달·준비) · `/analysis`(`agent-report` SSE — URL에 동·업종이 있으면 자동 시작, `facts` 이벤트로 시각 자료 즉시 렌더 + 섹션 5개 토큰 스트리밍, 9/29 리포트 v2). `landing`.

### 5-3. 로드맵 산출물 (전부 main)
| 단계 | 백엔드 | 프론트 | 핵심 |
|---|---|---|---|
| T0 합치기 | — | — | 세 갈래 병합, alembic head 1개(`e6f7a8b9c0d1` 최신) |
| T1 관문 | v0.31.0 intent BC | v0.18.x | 규칙 우선 파서·LLM 폴백(Gemini)·한 줄 진단 |
| T2 무대 | v0.32.0 | v0.19~v0.21 | `/profiles/types`·`/hour-gaps`·4블록·두 선·벤치마크 |
| T3 계획 | v0.33.0 finance BC | v0.22.x | 대구 엔진 이식·실측 프리필(월매출 2,613만/역삼1동 카페) |
| T4 조달·준비 | v0.34.0·v0.35.0 | v0.23.0 | 후보 92건 풀·질문 11규칙·준비자료·**혼합 LLM** |
| 부채 | v0.35.1 SGIS 버그 | v0.24.0 커버리지 | |

### 5-4. 검증 상태
- 백엔드 pytest **505 passed**(9/24, `beyondfacade_test` 격리 후 재확인) — dev DB를 건드리지 않는다(§4-1)
- 프론트 vitest **280 passed**, `tsc` clean
- E2E 11단계 — **`881626e`(main HEAD)에서 전 구간 통과**(9/24 09:45): 리포트 4,396자 · `/plan` 조달 필요 348만 · 후보 8건 · 질문 8개 · 준비자료 2,900자

## 6. 환경·서버

| | 값 |
|---|---|
| DB | `beyondfacade-db`(pgvector pg17) **127.0.0.1:5434**, `now()`는 **UTC**. 대구 분화본은 별도 DB(5437) — 섞이지 않음 |
| 백엔드 dev | uvicorn `--reload` **8201**, cwd `backend/`(메인 체크아웃). 워처가 편집을 놓친 적 2회 → 실호출 전 로그 확인 |
| 프론트 dev | next **3200**, `NEXT_PUBLIC_API_BASE=/api/backend` → 8201 프록시. 브라우저는 노트북(원격 SSH) |
| 도커 | 8200 조회 전용, **낡음**(§4-2) |
| LLM | 리포트 `hybrid`(gemini-2.5-flash → gemma4:12b) · 관문 폴백 gemini-2.5-flash · RAG 임베딩 bge-m3(Ollama, 1024, 색인·질의 동일) · GPU RTX 5060 Ti 16GB 유휴 |
| 키 | `backend/.env`에 GEMINI·SGIS·VWORLD 등 설정됨(값은 열람하지 않음). **Anthropic 키는 미설정** |
| git | `main` 단일. 원격 `origin/feature/analysis-api`(병합됨, 삭제는 사용자 결정), 로컬 `feature/frontend-mvp`(병합됨). 작업 트리엔 `docs/jekyll.md`(지킬 세션 산출물)만 |

## 7. 오늘 낡은 기록으로 틀렸던 것 — 재발 방지

| 틀린 전제 | 출처 | 실제 |
|---|---|---|
| "SGIS 키 부재로 지오코딩 차단" | HANDOFF 9/17 | 9/22 `feature/analysis-api`에서 완료·병합됨 |
| "RAG 코퍼스 전량 Q4, fp16 재색인 대기" | 메모리 | 7,883건 전량 fp16 |
| "`operating_months` 20254까지 → 빈 지도" | 내 T2-2 해석 | 22분기 전량. 빈 지도는 (업종,지표) 쌍에 있었음 |
| "만료 크론이 안 돈다" | T4-1 관찰 | 크론 정상. **테스트가 되돌린 것**(§4-1) |

**규칙**: 재개·위임 전에 문서가 아니라 §1의 방법으로 DB·로그·git을 먼저 잰다. 문서는 결과지, 원천이 아니다.
