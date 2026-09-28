# 업종 확장 — 일반음식점 계열 추가 설계

> 작성 2026-09-28 · 백엔드 v0.38.0 / 프론트 v0.26.0 기준
> 선행 문서: `docs/HANDOFF.md` §0(네거티브 리포트 방향), `docs/superpowers/specs/2026-09-23-commerce-bc-design.md` §3-2(업종 코드 매핑), `docs/api.md` §5.1(인허가 API 스펙)

## 1. 목적

골목상권의 핵심은 음식인데 현재 10업종에는 카페(휴게음식점)뿐이다. 네거티브 리포트("이 동네에서 이 장사는 하지 마라")가 설득력을 가지려면 회전이 가장 빠른 음식 업종이 있어야 한다.
이 문서는 **일반음식점 인허가 1개 원천으로 음식 업종 여러 개를 한 번에 붙이는** 방법을 정한다.

## 2. 2026-09-28 실측 — 붙일 수 있다는 근거

| 확인 항목 | 결과 |
|---|---|
| 상권분석서비스 아카이브 | **점포 100종·매출 63종 전부 적재돼 있음**(2021Q1~2025Q4). 한식 CS100001·중식 CS100002·일식 CS100003·양식 CS100004·제과 CS100005·패스트푸드 CS100006·치킨 CS100007·분식 CS100008·호프 CS100009가 이미 `region_commerce_sales`·`region_commerce_store`에 있다. `franchise_store_count` 컬럼도 있다 |
| 인허가 일반음식점 API | `general_restaurants/info` 우리 키로 200. **강남구만 51,402건**, 폐업 포함. 컬럼은 기존 6종과 동일(`BPLC_NM`·`LCPMT_YMD`·`CLSBIZ_YMD`·`CRD_INFO_X/Y`·`DAT_UPDT_PNT`) + **`BZSTAT_SE_NM`(업태구분명)** |
| 업태 분포(강남 **전수 51,402건**, 0단계 파일럿 9/28) | 한식 38.1% · 경양식 23.4% · 분식 10.7% · **기타 9.6%** · 일식 6.3% · 중국식 2.7% · 패스트푸드 1.7% · 호프/통닭 1.5% · **통닭(치킨) 1.1%** · 외국음식전문점 0.9% · 까페 0.8% · 정종/대포집/소주방 0.7% · 김밥(도시락) 0.6% · 뷔페식 0.4% · 전통찻집 0.3% · 감성주점 0.3% · 식육(숯불구이) 0.2% · 그 외 10종 각 0.1% 이하. (처음 표본 100건의 '기타 44%'는 최신순 정렬 편향이었다) |
| 컬럼 채움률(전수) | 상호·업태·인허가일·갱신시점·지번주소 100% · 폐업일 76.2% · **좌표 97.3%(영업중 99.6%)** · 도로명 60% · 전화 51%. 종업원수·보증금·홈페이지 등 12개 컬럼은 전부 빈값 |
| 영업상태 | 폐업 39,187(76%) · 영업 12,215. 인허가 연도 2015 이전 34,362(67%) — 생존 이력이 깊다 |
| '기타' 상호 표본 | 다수가 "(한시적)" 팝업·행사 영업, 백화점 입점, 무국적 퓨전 → 업태와 무관하게 "(한시적)"은 제외 표식으로 처리 |
| 다른 인허가 슬러그 | `bakeries`·`laundries`·`pharmacies`·`lodgings` → 403(`SERVICE_KEY…`): API는 있고 **활용신청만 안 됨**. `bakery`·`liquor_stores` → 400: 슬러그 아님 |
| 서울 전체 규모(추정) | 강남 5.1만 × 25구 ≈ **50만 건** — 현재 `store` 34.9만의 1.4배 |

## 3. 결정 사항

### 3-1. 추가 업종 — 1차 6종, 2차 2종

| 순서 | industry_id | 이름 | 수요동인 | 인허가 업태(`BZSTAT_SE_NM`) | 상권분석 코드 |
|---|---|---|---|---|---|
| 1차 | `korean_food` | 한식 | daily | 한식 | CS100001 |
| 1차 | `chinese_food` | 중식 | daily | 중국식 | CS100002 |
| 1차 | `japanese_food` | 일식 | daily | 일식 · 복어취급 · 횟집 | CS100003 |
| 1차 | `western_food` | 양식 | daily | 경양식 · 패밀리레스트랑 · 외국음식전문점(인도,태국등) | CS100004 |
| 1차 | `snack` | 분식 | daily | 분식 · 김밥(도시락) | CS100008 |
| 1차 | `pub` | 호프·주점 | leisure | 호프/통닭 · 정종/대포집/소주방 · 감성주점 · 라이브카페 · 통닭(치킨) | CS100009 (+ CS100007 치킨은 §3-3) |
| 1차(비노출) | `restaurant_other` | 음식점(기타) | — | 기타 · 그 외 전부 | 없음 |
| 1차(조건부) | `chicken` | 치킨 | daily | 통닭(치킨) — **2015년 이후 신규 없음, §3-3** | CS100007 |
| 2차 | `bakery` | 제과점 | daily | 별도 슬러그 `bakeries` (활용신청 필요) | CS100005 |

- **`restaurant_other`는 반드시 둔다.** 표본의 44%가 '기타'라 버리면 폐업 마커와 포화 신호의 분모("음식점 전체")가 깨진다. 화면 업종 select에는 안 나오고, 지도 폐업 마커의 "음식점 전체" 레이어와 포화 계산에서만 쓴다.
- 패스트푸드(CS100006)는 프랜차이즈 비중이 커 개인 창업 경고 대상이 아니므로 제외. 카페의 상권분석 매핑에 이미 CS100006·CS100008이 섞여 있는데(교차검증 §3-2의 잠정 조치) **분식이 독립 업종이 되면 `cafe`↔CS100008 행은 제거**한다. CS100006은 그대로 둔다(휴게음식점 모집단 보정).
- 위 업태 매핑표는 **§5의 0단계(강남구 파일럿) 전수 분포를 본 뒤 확정**한다. 표본 100건은 이름을 아는 용도일 뿐이다.

### 3-2. 왜 업종 6개가 아니라 "슬러그 1개 + 분류기"인가

현재 수집기는 `industry_source_code(mois_permit)` 행마다 (업종 × 25구) 타깃을 만들고 `store_id`를 `{industry_id}:{자치구}:{MNG_NO}`로 찍는다. 6업종을 각각 `general_restaurants` 슬러그로 등록하면 **같은 50만 건을 6번 받아 6벌 저장**한다. 그래서:

- 인허가 타깃은 **슬러그 단위**로 1개(`general_restaurants` × 25구).
- 한 건의 `industry_id`는 수집 시점에 **분류기(Strategy)** 가 업태로 정한다. 기존 6슬러그는 "고정 업종" 전략(지금과 동일 동작).
- `store_id` 접두는 슬러그 기반 `restaurant:{자치구}:{MNG_NO}`. 업태가 바뀌어 재분류돼도 같은 행이 업데이트된다. 기존 행의 접두(`cafe:` 등)는 건드리지 않는다.
- 증분 커서(`latest_source_updated_at`)는 현재 (industry_id, district) 키인데, 슬러그 아래 업종이 여럿이면 **슬러그의 업종 집합 전체의 max**를 써야 한다. 포트 시그니처를 `industry_ids: list[str]`로 넓힌다.

### 3-3. 치킨 — 업태는 있으나 2015년 이후 신규가 없다 (파일럿 실측으로 수정)

파일럿 전수에서 '통닭(치킨)' 업태가 572건 별도로 존재해 분류기에는 `chicken`을 넣었다. 그런데 **적재 후 확인하니 그 572건의 최근 인허가일이 2015-05-22**다. 2015년 이후 새 치킨집은 '호프/통닭'(→ pub)이나 '기타'로 들어온다. 즉 인허가 층의 `chicken`은 2015년에 멈춘 과거 모집단이다.

- `chicken` 업종·CS100007 매핑·분류 규칙은 그대로 둔다 (상권분석 층의 매출·프랜차이즈 신호는 온전하다).
- **인허가 기반 신호(순유출·생존·조기 폐업)에서 `chicken`은 제외**한다. 판정 카드는 상권분석 신호만으로 내거나 판정 대상에서 보류.
- 2차 후보: '호프/통닭'·'기타' 중 상호 키워드(치킨·통닭·닭)로 `chicken`을 떼는 휴리스틱. 강남 파일럿에서 정밀도를 재고 60% 미만이면 포기.

### 3-4. 상권분석 매핑은 행 추가로 끝난다

`industry_source_code(seoul_commercial)`에 위 표의 코드를 넣으면 시간대 갭(`hour_gap_source_gateways`)·매출·점포·프랜차이즈 조회가 그대로 새 업종을 본다. 코드 변경 없음. 마이그레이션 1개(시드 + `cafe`↔CS100008 삭제).

## 4. 변경 범위 — 파일 단위

### 4-1. 백엔드 (store BC, master BC)

| 계층 | 파일 | 변경 |
|---|---|---|
| master 시드 | `apps/master/adapter/inbound/cli/seed_master.py` | `_INDUSTRIES`에 7행(`restaurant_other` 포함), `_SOURCE_CODES`에 `("restaurant_other", "mois_permit", "general_restaurants")` 1행. **seoul_commercial 코드는 마이그레이션에서** |
| migration | `migrations/versions/xxxx_food_industries.py` | industry 7행 · industry_source_code mois 1행 + seoul_commercial 6행 · `cafe`↔CS100008 삭제. downgrade 역순 |
| store domain | `apps/store/domain/services/permit_industry_classifier.py` **신규** | `PermitIndustryClassifier` 추상 + `FixedIndustry(industry_id)` + `BusinessTypeClassifier(mapping, fallback)`. 순수 파이썬, 프레임워크 import 없음 |
| store dto | `apps/store/app/dtos/store_dto.py` | `IngestTarget.industry_id` → 의미를 "앵커 업종"으로 문서화. `industry_ids: tuple[str, ...]` 추가(커서용) |
| store port | `apps/store/app/ports/output/store_port.py` | `latest_source_updated_at(industry_ids: list[str], district_code)`, `active_store_ids`·`existing_locations` 동일하게 |
| store repo | `apps/store/adapter/outbound/repositories/store_repository.py` | `industry_id == x` → `industry_id.in_(xs)` |
| gateway | `apps/store/adapter/outbound/gateways/mois_permit_gateway.py` | `_to_entity`가 `classifier.classify(item)`로 `industry_id` 결정, `store_id` 접두는 `target.store_prefix`(기존 슬러그 = industry_id, 신규 = `restaurant`) |
| gateway 조립 | `apps/store/dependencies/…` 또는 gateway 생성자 | `{slug: classifier}` 맵 — `general_restaurants`만 `BusinessTypeClassifier`, 나머지 `FixedIndustry` |
| collector | `apps/store/adapter/inbound/cli/store_collector.py` | `_build_targets`가 mois 행을 **슬러그로 그룹**해 타깃 1개/구, `industry_ids`는 그 슬러그의 업종 집합. `--industry` 옵션은 슬러그 매칭으로 재정의 |
| 지오코딩 큐 | `list_pending(industry_ids)` | 좌표는 원천이 주므로 대상 아님(좌표 결측만 SGIS). 변경 없음 |
| metric | `store_stats_gateway.py` | `group_by(region_code, industry_id)`라 **자동 포함**. `_NO_CLOSURE_HISTORY`에 넣지 않는다(음식점은 폐업일자 있음) |
| intent | `apps/intent/domain/value_objects/industry_synonyms.py` | 한식·밥집·식당·국밥 / 중국집·중식 / 일식·초밥·횟집 / 양식·파스타·레스토랑 / 분식·김밥·떡볶이 / 호프·술집·주점·포차 → 각 id. `restaurant_other`는 동의어 없음(관문에서 못 고르게) |
| agent 프리필 | finance BC 프리필의 업종별 기본값 | 음식 업종의 월매출·임대료 프리필 근거를 CS 코드 매출에서 읽는지 확인 — 읽는다면 변경 없음 |

**Store 엔티티는 바꾸지 않는다.** `subcategory_id`가 이미 있으니 원 업태명은 `industry_subcategory`에 넣지 않고 우선 버린다(1차). 2차 치킨 분리 때 필요하면 그때 업태를 저장한다.

### 4-2. 프론트엔드

| 파일 | 변경 |
|---|---|
| `shared/industries.ts` | `INDUSTRIES`에 6개 추가(`restaurant_other` 제외), `INDUSTRY_LABELS` |
| `features/agent-report/lib/example-questions.ts` | 6업종 × 3문구 (리포트 5섹션 축 유지) |
| `features/map-explorer/lib/map-state.ts` | `SNAPSHOT_INDUSTRIES`·`NO_CLOSURE_HISTORY_INDUSTRIES` **변경 없음** |
| `marker-strategies.ts`·`side-panel.tsx` | `Partial` 맵이라 변경 없음. 폐업 마커(HANDOFF §0-3)는 별도 작업 |
| `app/api/mock/*` | 픽스처 업종 목록에 6개 반영 + 라우트 계약 테스트(§15) |
| `analysis-form.tsx` | select가 `INDUSTRIES`를 돌므로 자동 |

업종 select는 **판정 대상 14종**만 보인다(학원·어린이집은 `HANDOFF.md` §0-11 결정으로 보조축 전환 — 마스터·적재·크론은 유지, select·관문·판정 카드에서만 제외). 14개도 길므로 **그룹 optgroup**(음식 / 생활 / 여가)으로 묶는다 — `industry.demand_type`이 이미 있으니 그 축을 쓴다.

### 4-3. 크론·운영

- 초기 적재 50만 건: 기존 크론(04:20 store-collector)에 섞지 않는다. `--industry general_restaurants --full`로 **새벽 수동 1회**, 구별 소요를 로그로 남긴다. 강남 5.1만 건 = 515페이지(100건/페이지)라 구당 수 분, 전체 1~2시간 추정.
- 이후 증분은 기존 크론이 자동 포함(타깃 빌더가 시드에서 읽으므로).
- 도커 이미지(8200)는 조회 전용이라 마이그레이션만 적용하면 된다.

## 5. 작업 순서 — TDD 단계

각 단계는 실패 테스트 → 최소 구현 → 리팩터. 버전은 백엔드 v0.39.0(minor: 업종 추가), 프론트 v0.27.0.

| 단계 | 내용 | 완료 기준 |
|---|---|---|
| 0 파일럿 | 강남구 `general_restaurants` 전량 1회 수집을 **임시 스크립트로 파일에만** 저장(DB 미적재). 업태 전수 분포표 → §3-1 매핑 확정. '기타'의 상호 표본 200건 눈으로 확인 | 분포표가 이 문서 §2에 추가됨 |
| 1 분류기 | `PermitIndustryClassifier` 단위 테스트: 업태→업종, 미매핑→`restaurant_other`, 공백·NFC 정규화, 고정 전략은 항상 앵커 반환 | 테스트 green, 프레임워크 import 0 |
| 2 마스터 | 마이그레이션 + 시드. `cafe`↔CS100008 삭제 | `alembic upgrade head` 멱등, `industry` 17행 |
| 3 수집기 | 타깃 빌더 슬러그 그룹화 테스트(기존 6슬러그 타깃 수 불변, restaurant 25개), 커서 `in_` 테스트(Fake repo), gateway `_to_entity` 분류 테스트 | 기존 store 테스트 전부 green |
| 4 적재 | 강남구 1구 실적재 → `store` 업종별 count·좌표율·폐업율 STATUS §2 형식으로 기록 → 24구 | 서울 전체 count, 좌표율 ≥ 95% |
| 5 지표 | `build_metrics` 재실행 → `region_industry_metric`에 6업종 2019~2026 생성. API `GET /metrics?industry=korean_food` 200 | 행수 = 6 × 427 × 8 근사 |
| 6 관문 | 동의어 추가 + intent 테스트("역삼동 국밥집" → korean_food) | |
| 7 프론트 | industries·라벨·예시 질문·mock 픽스처·optgroup. 계약 테스트 | Vitest green, 지도에서 한식 단계구분도 표시 |
| 8 문서 | STATUS §2-2 표에 6업종 행, api.md §0 갱신, ver_log | |

## 5-1. 진행 기록

| 일시 | 단계 | 결과 |
|---|---|---|
| 9/28 15:xx | 0 파일럿 | 강남구 51,402건 JSONL(`data/raw/mois_permit/`, git 무시) → §2 전수 분포. 스크립트 `scripts/pilot_general_restaurants.py`·`pilot_analyze_general_restaurants.py` |
| 9/28 16:xx | 1~3 분류기·마이그레이션·수집기 | `b7c8d9e0f1a2` 적용(industry 18행, cafe↔CS100008 삭제). 신규 테스트 13 + 갱신 4, 백엔드 전체 **542 passed** |
| 9/28 16:xx | 4 적재(강남구) | 51,402건 업서트 → 공간조인 50,022(미판정 32) → 지표 29,229행(+1,400). store 전체 **400,598**. 업종별: 한식 19,632 · 양식 12,520 · 기타 6,945 · 분식 5,784 · 일식 3,243 · 중식 1,394 · 호프주점 1,312 · 치킨 572 |
| 9/28 16:xx | 5·6 검증 | `GET /metrics?metric=closure_rate&industry=korean_food&year=2025` 200 (강남 22동 값) · `POST /intent` "역삼동에 국밥집" → korean_food + 역삼1·2동 후보 |
| 9/28 21:17~22:23 | 4 적재(24구) | 구별 순차 `--district X --industry general_restaurants --full` nohup, **구당 2~4분, 총 66분**(예상 3시간보다 훨씬 빠름). 실패 구 없음. 공간조인 456,086건 판정 → 456,046 기입(미판정 40·구 교차 불일치 48). 지표 업서트 55,093행 |
| 9/28 22:25 | 5 검증(전 서울) | store **888,308**행(음식 539,112 = 한식 226,118 · 분식 82,817 · 기타 71,091 · 양식 56,427 · 호프주점 52,114 · 일식 23,753 · 중식 17,389 · 치킨 9,403). `GET /metrics?metric=closure_rate&industry=korean_food&year=2025` **427동**(8201·8200 모두 200). 치킨 최근 개업 2017-09-25(전 서울 기준, 강남 파일럿의 2015보다 늦지만 결론 동일) |
| 9/28 21:20 | 7 프론트 | **FE v0.28.0**(6ac2b1b): `shared/industries.ts` 라벨 16·판정 대상 14·`INDUSTRY_GROUPS` 음식/생활/여가, 컨트롤바·분석 폼 optgroup, 관문 칩 14종, 예시 질문 6종×3, mock 동의어·가드. Vitest 326/326 |
| 9/28 22:30 | 8 문서 | STATUS §2-2·2-3, api.md §0, HANDOFF §0-9, 이 표 |
| — | 후속 | 점포 표본 `store-samples.ts` 음식 업종 추출 · 음식 좌표 결측(5~7%) 지오코딩 대상 여부 · 2차 치킨/제과 결정 |

## 6. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| '기타' 44%가 실제로 더 클 수 있음 | 0단계에서 전수 확인. 60%를 넘으면 상호 키워드 보조 분류(한식: 국밥·백반·찌개 / 분식: 김밥·떡볶이)를 1차에 넣을지 결정 |
| 인허가 업종 정의 ≠ 상권분석 업종 정의 | 두 층의 동×업종 점포수를 교차검증(commerce-crossvalidation.md 방식). 괴리 30% 초과 업종은 화면에서 "정의 차이" 안내 |
| 50만 건 적재 중 API 5xx | gateway 재시도 3회 있음. 구 단위 실패는 `--district`로 재실행 |
| `store` 테이블 85만 행 → 지도 점 로드 | 동 선택 시에만 로드하는 현행 가드 유지. 폐업 마커는 최근 2년로 한정 |
| 업종 select 16개 | optgroup + 관문(채팅) 우선이라 select는 보조 |

## 7. 이 문서가 결정하지 않는 것

- 네거티브 신호 5종의 계산식과 임계값 — `HANDOFF.md` §0-8 팀 결정 후 별도 설계
- 치킨·제과 2차 — 1차 적재 후 파일럿 결과로 결정
- 세탁소·약국·숙박 — 데이터는 열 수 있으나 소자본 골목 창업 타깃과 거리가 있어 보류
