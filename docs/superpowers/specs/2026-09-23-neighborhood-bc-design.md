# neighborhood BC — 동네 맥락 데이터 적재

> 작성 2026-09-23 · 대상 브랜치 `codex/seoul-atlas-landing` · 백엔드 v0.25.0
> 선행: `2026-09-23-commerce-bc-design.md`, `2026-09-23-commerce-crossvalidation.md`, `HANDOFF-260918.md` §2-1

## 1. 왜 새 BC인가

`commerce` BC는 **업종 실적**을 담는다. 분기 × 행정동 × 업종 세 키로 매출·점포·개폐업을 말한다.

이번 7종은 **동네 맥락**이다. 분기 × 행정동 두 키로 누가 다니고, 누가 일하고 살며, 무엇이 있고, 무엇에 돈을 쓰는지를 말한다. 업종 축이 없다.

경계를 나누는 근거 셋.

- **어휘가 다르다.** 매출·점포·프랜차이즈 대 유동인구·집객시설·지출항목. DDD의 Bounded Context는 일관된 모델 하나의 경계다.
- **§12의 근거가 무너진다.** `commerce`에 이미 3테이블이 있다(`region_commerce_sales`, `region_commerce_store`, `region_commerce_sales_breakdown`). 7을 더하면 10이다. "AI가 컨텍스트에 한 번에 올려 이해하는 단위"가 성립하지 않는다.
- **소비하는 화면이 다르다.** 동네 프로필(사이드패널)은 이쪽만 쓰고, 업종 분석은 `commerce`를 쓴다.

BC 이름은 `apps/neighborhood`.

## 2. 원천 (2026-09-23 확보 완료)

`data/raw/seoul_commerce/` — 무결성·SHA256은 같은 경로 `MANIFEST.md`. 루트 `data/`는 git 무시 대상.

| 디렉토리 | infId | 행 | 컬럼 |
|---|---|---|---|
| `footfall_adstrd/` | OA-22178 길단위인구-행정동 | 9,350 | 25 |
| `worker_adstrd/` | OA-22184 직장인구-행정동 | 9,108 | 24 |
| `resident_adstrd/` | OA-22183 상주인구-행정동 | 9,350 | 27 |
| `facility_adstrd/` | OA-22169 집객시설-행정동 | 9,350 | 23 |
| `spending_adstrd/` | OA-22166 소비-행정동 | 9,350 | 14 |
| `apartment_adstrd/` | OA-22163 아파트-행정동 | 9,331 | 18 |
| `change_adstrd/` | OA-15575 상권변화지표-행정동 | 9,350 | 9 |

합계 65,189행 / 9.1MB. 전부 공공누리 1유형(출처표시, 상업적 이용·변경 가능), 제3저작권자 없음.

**취득 경로가 기존 3종과 다르다.** 7종 모두 ZIP 배포가 없다. 데이터셋 페이지의 파일 목록이 비어 있고(`fileCnt = 0`) `frmFile`의 `infSeq`도 빈 값이다. 폐기된 것이 아니라(갱신일 2026-09-11) 애초에 파일 첨부가 없다. 포털 시트 탭의 전체 CSV 내려받기를 쓴다. 인증키·로그인 불필요.

```
POST https://datafile.seoul.go.kr/bigfile/iot/sheet/csv/download.do
srvType=S&infId={infId}&serviceKind=0&pageNo=1&gridTotalCnt=&ssUserId=SAMPLE_VIEW
&strWhere=&strOrderby=STDR_YYQU_CD+DESC&filterCol=&txtFilter=
```

공통 사항.

- 인코딩 **CP949**, 줄바꿈 **LF** (기존 ZIP 내 CSV는 CRLF).
- 시점 컬럼은 기존과 같은 `기준_년분기_코드` 5자리 문자열(`20251`).
- 연도 분할 없이 **전 기간 단일 파일**.

## 3. 검증 결과

### 3-1. 시점 범위가 기존보다 2분기 넓다

7종은 **20211~20262, 22분기**다. `commerce`의 매출·점포는 20211~20254, 20분기다.

**조인할 때 `year_quarter <= '20254'`로 잘라야 격자가 맞는다.** 자르지 않으면 2026년 1~2분기에 매출·점포가 NULL인 행이 생긴다.

### 3-2. 행정동 커버리지가 데이터셋마다 다르다

7종 모두 원천 425개 마스터의 부분집합이며, 마스터에 없는 코드는 0건이다.

| 데이터셋 | 고유 동 | 비고 |
|---|---|---|
| 유동인구·상주인구·집객시설·소비·상권변화 | 425 | 425 × 22 = 9,350 완전 격자 |
| 아파트 | 425 | `11740690`(둔촌1동)이 20211~20213 3분기만 존재 → 이후 424 |
| **직장인구** | **414** | 11개 부족 |

직장인구 누락 11개: 하계2동·신정6동·가양2동·구로1동·항동·일원본동·일원2동·위례동·잠실7동·암사3동·둔촌1동.

**내부 조인 금지.** 동이 425 → 414로 줄어든다. 반드시 LEFT JOIN하고 없음은 NULL로 둔다.

우리 `region` 427개 중 5개(신설동·용두동·개포3동·상일제1동·상일제2동)는 원천이 옛 행정동 체계를 유지해 데이터가 없다. `commerce`와 같은 방침이다 — `region_code` nullable FK, 안분 금지, 화면에서 0이 아니라 없음으로 표시.

### 3-3. 직장인구와 상주인구는 축이 완전히 같다

두 데이터셋의 값 컬럼 21개가 한 글자도 다르지 않다.

```
총 · 남성 · 여성 · 연령대_10~60_이상(6)
· 남성연령대_10~60_이상(6) · 여성연령대_10~60_이상(6)
```

상주인구에만 `총_가구_수`, `아파트_가구_수`, `비_아파트_가구_수` 3개가 더 있다.

같은 개념(등록 기반 인구를 성·연령으로 센 것)의 두 인스턴스이므로 한 테이블에 `population_type`으로 구분한다. 가구 3종은 인구가 아니라 주거 스톡이므로 아파트 쪽으로 보낸다.

### 3-4. 유동인구는 축이 다르다

시간대 6구간과 요일 7종이 있는 대신 성별×연령 교차가 없다. 흐름(flow)을 센 것이고 나머지 둘은 등록 상태(stock)다. 커버리지도 425 대 414로 다르다. **합치면 스키마가 표현하지 못하는 제약이 생긴다** — 어떤 축이 어떤 인구유형에 유효한지를 코드가 알아야 한다. 별도 테이블로 둔다.

### 3-5. 서울 평균은 2NF 위반이다

상권변화 데이터의 `서울_운영_영업_개월_평균`·`서울_폐업_영업_개월_평균`은 **행정동이 아니라 분기에만 의존한다.** 22개 분기 전부에서 고유값이 하나였다. 예: 20251 → 운영 111개월, 폐업 52개월이 425개 동에 그대로 반복된다.

부분 함수 종속이므로 §13에 따라 별도 테이블로 분리한다.

분리하면 그 테이블은 분기만 키라 어디에도 붙지 않는다. §13의 "어떤 테이블도 고립된 채로 존재할 수 없다"에 걸린다. **동별 변화 테이블이 `year_quarter`를 외래키로 참조하게 해서 노드로 세운다.**

### 3-6. 상권변화지표는 범주형이다

| 코드 | 이름 | 전체 건수 |
|---|---|---|
| LL | 다이나믹 | 3,581 |
| HH | 정체 | 2,630 |
| HL | 상권축소 | 1,678 |
| LH | 상권확장 | 1,461 |

숫자가 아니므로 숫자 값 컬럼에 담기지 않는다. 이 데이터셋만 넓은 형태로 둔다.

### 3-7. 컬럼 이름 규칙이 데이터셋마다 다르다

**순서 기반 매핑을 쓰면 틀린다. 반드시 이름으로 찾되, 데이터셋별 규칙 차이를 반영한다.**

- 유동인구 시간대는 밑줄: `시간대_00_06_유동인구_수`. 추정매출은 물결표: `시간대_00~06_매출_금액`.
- 소비는 `음식_지출_총금액`이 `기타_지출_총금액` **뒤에** 온다. 항목 순서가 사전순도 논리순도 아니다.
- 추정매출 분해는 시간대 *건수* 컬럼에 원천 오타가 있다(`시간대_건수~06_매출_건수`). 이 7종에는 해당 없음.

## 4. 테이블 설계 — 7개

`commerce`와 동일한 방침을 따른다.

- 원천 8자리 `행정동_코드`를 `adstrd_code`로 그대로 저장한다.
- `region_code`는 앞 8자리가 일치할 때만 채우는 nullable FK다. 실제 FK로 드는 것은 의도적 역정규화이며 근거는 두 가지다. 8자리와 10자리를 `left()`로 조인하면 인덱스를 못 타고, §13이 모든 테이블에 엣지를 요구한다.
- `year_quarter`는 5자리 문자열. 정수 변환 금지.
- 결측은 0으로 채우지 않고 NULL 보존.
- PK 기준 `ON CONFLICT DO UPDATE`로 멱등.

### 4-1. `region_footfall_quarter` — 유동인구

```
PK(adstrd_code, year_quarter, dim_type, dim_key)

adstrd_code   varchar(8)
year_quarter  varchar(5)
dim_type      varchar   total | gender | age | hour | dow
dim_key       varchar   아래 표
region_code   FK → region  nullable
headcount     bigint    사람 수 — 원천 공란은 NULL
```

| dim_type | dim_key | 개수 |
|---|---|---|
| total | all | 1 |
| gender | male, female | 2 |
| age | 10, 20, 30, 40, 50, 60_over | 6 |
| hour | 00_06, 06_11, 11_14, 14_17, 17_21, 21_24 | 6 |
| dow | mon, tue, wed, thu, fri, sat, sun | 7 |

원본 1행 → 22행. 9,350 × 22 ≈ **20.6만 행**.

### 4-2. `region_population_quarter` — 직장·상주 인구

```
PK(adstrd_code, year_quarter, population_type, dim_type, dim_key)

population_type  varchar   worker | resident
dim_type         varchar   total | gender | age | gender_age
dim_key          varchar   아래 표
headcount        bigint
(나머지 공통 컬럼 동일)
```

| dim_type | dim_key | 개수 |
|---|---|---|
| total | all | 1 |
| gender | male, female | 2 |
| age | 10, 20, 30, 40, 50, 60_over | 6 |
| gender_age | male_10 … male_60_over, female_10 … female_60_over | 12 |

원본 1행 → 21행. (9,108 + 9,350) × 21 ≈ **38.8만 행**.

`gender`와 `age`는 `gender_age`의 주변합이다. 원천이 주는 값을 그대로 보존하며, 합이 맞는지는 §6에서 검증한다.

### 4-3. `region_household_quarter` — 가구·아파트

상주인구의 가구 3종과 아파트 데이터셋을 합친다. 둘 다 주거 스톡이다.

```
PK(adstrd_code, year_quarter, dim_type, dim_key)

dim_type   varchar   household | apartment_complex | apartment_area | apartment_price
dim_key    varchar   아래 표
value      bigint    세대 수 또는 단지 수 — 원천 공란은 NULL
```

| dim_type | dim_key | 원천 |
|---|---|---|
| household | total, apartment, non_apartment | 상주인구의 총_가구_수·아파트_가구_수·비_아파트_가구_수 |
| apartment_complex | count | 아파트_단지_수 |
| apartment_area | under_66, 66, 99, 132, 165 | 면적 구간별 세대 수 |
| apartment_price | under_100m, 100m, 200m, 300m, 400m, 500m, over_600m | 가격 구간별 세대 수 |

평균값 2개(`아파트_평균_면적`, `아파트_평균_시가`)는 세대 수가 아니라 단위가 다르다. 같은 `value` 컬럼에 담으면 의미가 섞인다. 별도 테이블 `region_housing_average_quarter`로 뺀다.

```
region_housing_average_quarter
PK(adstrd_code, year_quarter)
avg_area_m2   float    아파트_평균_면적
avg_price     bigint   아파트_평균_시가
region_code   FK → region  nullable
```

긴 형태 약 **17만 행** + 평균 9,331행.

> **미확정 1** — 평균 2개를 별도 테이블로 뺄지, `region_household_quarter`에 `value_float` 컬럼을 하나 더 둘지. 전자가 정규화에 맞고 후자가 파일 수를 줄인다. 구현 시작 전에 결정한다. 이 설계서의 기본값은 **별도 테이블**이다.

### 4-4. `region_facility_quarter` — 집객시설

```
PK(adstrd_code, year_quarter, facility_type)

facility_type  varchar   total + 19종
facility_count int       원천 공란은 NULL
```

19종: `government`(관공서), `bank`(은행), `general_hospital`(종합병원), `hospital`(일반 병원), `pharmacy`(약국), `kindergarten`(유치원), `elementary_school`(초등학교), `middle_school`(중학교), `high_school`(고등학교), `university`(대학교), `department_store`(백화점), `supermarket`(슈퍼마켓), `theater`(극장), `lodging`(숙박 시설), `airport`(공항), `train_station`(철도 역), `bus_terminal`(버스 터미널), `subway_station`(지하철 역), `bus_stop`(버스 정거장).

`total`은 원천의 `집객시설_수`다. 19종의 합과 일치하는지는 §6에서 검증한다.

원본 1행 → 20행. 9,350 × 20 = **18.7만 행**.

### 4-5. `region_spending_quarter` — 지출

**정의 확인 결과 (2026-09-23)** — 상세는 `2026-09-23-spending-definition.md`.

이 데이터는 **주민이 쓴 돈이 아니다.** 서울시 골목상권 분석서비스의 출처표가 원천을 `KB카드 / 가맹점 매출`로 명시한다. 즉 **발생지 기준**이며, 10개 항목이 KB카드 소비트렌드 비율 분류와 정확히 일치한다. 추정매출은 신한카드 결제액을 보정한 값이라 **둘 다 발생지이고 카드사만 다르다.**

데이터도 같은 말을 한다. 1인당 분기 지출 중앙값이 21.5만원으로 실제 가계 지출의 5% 수준이고, 로그 지출이 직장인구와 r=0.658로 붙는 반면 상주인구와는 r=0.135에 그친다.

**따라서 유입·유출 지수는 폐기한다.** 지출과 매출의 비율은 서울 전체 20분기 내내 0.41~0.51에 갇혀 있다. 상권 성격이 아니라 두 카드사의 점유율 차이를 재고 있을 뿐이다. 거주지 기준 소비 데이터는 상권분석서비스 계열에 존재하지 않는다.

**지출 구성비는 조건부로 쓸 수 있다.** "주민이 쓴 돈"이 아니라 **"이 동 가맹점에서 결제되는 돈의 구성"**으로 서술하면 성립하고, 창업 업종 판단에는 오히려 더 직접적이다. 다만 본사·온라인 가맹점 오염을 걸러야 한다. 상위 5개 동(소공동·구로3동·문래동·역삼1동·역삼2동)이 서울 전체 지출의 61%를 차지하고 각각 단일 항목이 90~99%다. 2단 필터(단일 항목 50% 이상 제외, 1인당 분기 지출 150만원 이상 제외) 후 405개 동이 남고, 그 표본에서 교육 상위에 중계·대치·목동이, 유흥 상위에 이태원·신림·서교가 나와 현실과 맞는다.

지출에는 결손이 없다. 10항목 합이 총액과 정확히 일치하며 성별·연령 분해 컬럼 자체가 없다.


```
PK(adstrd_code, year_quarter, spending_category)

spending_category  varchar   total + 10종
amount             bigint    원천 공란은 NULL
```

10종: `grocery`(식료품), `clothing_shoes`(의류·신발), `household_goods`(생활용품), `medical`(의료비), `transport`(교통), `education`(교육), `entertainment`(유흥), `leisure_culture`(여가·문화), `etc`(기타), `food`(음식).

**원천 컬럼 순서에서 `음식`이 `기타` 뒤에 온다.** 순서로 매핑하면 두 항목이 뒤바뀐다.

원본 1행 → 11행. 9,350 × 11 ≈ **10.3만 행**.

### 4-6. `region_commerce_change` — 동별 상권 변화

반복 그룹이 없으므로 넓은 형태다.

```
PK(adstrd_code, year_quarter)

change_code        varchar(2)  HH | HL | LH | LL
change_name        varchar     정체 | 상권축소 | 상권확장 | 다이나믹
operating_months   float       운영_영업_개월_평균
closed_months      float       폐업_영업_개월_평균
region_code        FK → region  nullable
year_quarter       FK → seoul_commerce_change_baseline.year_quarter
```

`change_name`은 `change_code`에 함수 종속이라 엄밀히는 3NF 위반이다. 코드 4종의 고정 매핑이고 별도 룩업 테이블을 만드는 편익이 없으므로 **명시적 근거를 남기고 유지한다**(§13이 허용하는 부분적 역정규화). 원천이 두 컬럼을 같이 주므로 원본 보존의 의미도 있다.

9,350행.

### 4-7. `seoul_commerce_change_baseline` — 서울 평균

```
PK(year_quarter)

seoul_operating_months  float   서울_운영_영업_개월_평균
seoul_closed_months     float   서울_폐업_영업_개월_평균
```

22행. §3-5의 2NF 분리 결과다. `region_commerce_change`가 참조하므로 고립되지 않는다.

### 4-8. 규모 합계

긴 형태 전부 합쳐 약 **106만 행**. `commerce`의 매출 분해(약 789만 행)보다 작다.

## 5. 값 객체

시간대 6구간과 연령 6구간이 `commerce`의 매출 분해와 **값이 완전히 같다.** 구분자만 물결표와 밑줄로 다르다.

§12는 여러 엔티티가 횡단 공유하는 공통 VO를 `domain/value_objects/`에 두도록 허용한다. 다만 이 공유는 **BC를 가로지른다.** 값 객체는 도메인이므로 §11이 말하는 전역 인프라 `core/`에 둘 수 없다.

**각 BC가 자기 값 객체를 갖고 중복을 감수한다.** BC 독립성이 중복 제거보다 우선이다. 대신 두 BC가 같은 구간을 쓴다는 사실을 여기 남겨, 나중에 조인할 때 구분자 차이로 어긋나지 않게 한다. 저장하는 `dim_key`는 양쪽 모두 `00_06` 형태로 정규화한다.

## 6. 적재 후 검증

1. **행 수**: 7개 원천의 행 수와 전개 배수가 맞는가. 22분기가 전부 있는가.
2. **region 해석률**: 미매칭이 §3-2의 3코드(`11230536`·`11680740`·`11740520`)에서만 나오는가.
3. **직장인구 414개 동**: 다른 데이터셋과 달리 11개가 비는 것이 확인되는가.
4. **총합 일치** — 원천 품질 판정의 핵심.
   - 유동인구: `gender` 합 = `age` 합 = `hour` 합 = `dow` 합 = `total`인가.
   - 직장·상주: `gender` 합 = `age` 합 = `gender_age` 합 = `total`인가.
   - 집객시설: 19종 합 = `total`인가.
   - 지출: 10종 합 = `total`인가.
   - **어긋나면 비율과 대표 사례를 기록한다.** 반올림·비식별 처리로 어긋날 수 있다. 어긋난 채로 화면에 쓰면 합이 안 맞는 표가 나온다.
5. **아파트 둔촌1동**: `11740690`이 20211~20213 3분기만 있는지.
6. **서울 평균**: 22행이고 `region_commerce_change`의 모든 분기가 참조 가능한지.
7. **멱등**: 재실행 후 행 수 불변, 값 갱신.

## 6-1. 적재 후 확인된 원천 함정 셋 (2026-09-23)

후속 작업이 반드시 반영해야 하는 사항이다. 상세는 `2026-09-23-neighborhood-typology.md`.

### ① 시간대 6구간은 길이가 다르다 — 시간당 강도로 보정해야 한다

| 구간 | 00_06 | 06_11 | 11_14 | 14_17 | 17_21 | 21_24 |
|---|---|---|---|---|---|---|
| 길이 | 6h | 5h | 3h | 3h | 4h | 3h |

원값을 그대로 비교하면 긴 구간이 무조건 커진다. 실제로 **425개 동 중 377개가 `00_06`이 최대**로 나온다. 새벽에 사람이 가장 많은 동네가 서울에 377곳일 리 없다.

**구간 값을 구간 길이로 나눈 시간당 강도로 비교한다.** 이 보정은 유동인구뿐 아니라 `commerce`의 매출 분해에도 똑같이 적용된다. 두 데이터가 같은 6구간을 쓰기 때문이다. 시간대 비교·피크 판정·서사 라벨 생성 전부에 해당한다.

### ② 상주인구의 `아파트_가구_수`는 전 행이 0이다

9,350행 전부 0이고 최댓값도 0이다. 같은 행의 `총_가구_수`와 `비_아파트_가구_수`는 정상이며 서로 같다(최댓값 28,118 일치). 즉 원천이 아파트 가구를 분리해 채우지 않는다.

적재된 `region_household_quarter`의 `dim_type='household'`, `dim_key='apartment'` 행은 **전부 0이며 사용 불가**다. 0을 "아파트 가구가 없다"로 읽으면 안 된다. 아파트 관련 판단은 `dim_type='apartment_*'` 계열과 `region_housing_average_quarter`로만 한다.

원천이 준 값을 그대로 보존한 것이므로 적재를 고치지 않는다. 조회하는 쪽이 이 컬럼을 쓰지 않으면 된다.

### ③ 집객시설 총계는 19종의 합이 아니다

`facility_type='total'`이 9,350행 전부에서 19종 합보다 크다. 비율 중앙값 0.486, 최소 0.211. 대표 사례는 중구 명동으로 전 분기 총계 542 대 19종 합 151이다.

파일에 없는 시설 종류까지 포함하는 더 넓은 정의로 보인다. **총계와 19종을 같은 표에 나란히 놓으면 합이 안 맞는 화면이 나온다.** 19종은 구성 지표로, 총계는 별도 지표로 쓴다. 19종 합을 총계로 나눈 비율은 의미가 없다.

부수적으로 `railway_station`(철도_역_수)은 9,350행 전부 NULL이다. 원천이 행정동 단위로 집계하지 않는 항목이다.

## 7. 범위 밖

- 파생 지표(동네 유형 분류, 시간대 서사 라벨, 유입·유출 지수). 적재 후 별도 작업으로 집계 계층에 둔다. 규칙이 바뀔 수 있으므로 기존 `region_industry_metric`처럼 배치 재생성 가능하게 만든다.
- 라우터·스키마·인바운드 매퍼. `convenience`·`childcare`·`commerce` 전례대로 후속. 만들 때 §12에 따라 `myself` 엔드포인트로 배선부터 확인한다.
- 프론트엔드 연결(사이드패널 동네 프로필, 지도 지표 추가, AI 리포트 슬롯 고정).
- 생활인구(OA-14991). 여전히 범위 밖이다.

## 8. 완료 기준

- 7개 테이블이 생성되고 22분기 전량이 멱등하게 적재된다.
- §6의 일곱 항목이 수치로 기록된다. 특히 4번 총합 일치 결과는 반드시 남긴다.
- 단위 테스트가 통과한다. 최소한 CP949 파서, 데이터셋별 컬럼 이름 규칙(특히 지출의 `음식`·`기타` 순서), region 해석과 미매칭 3코드 보존, 멱등 업서트를 덮는다.
- `docs/erd.md` §6과 `backend/docs/backend_ver_log.md` v0.25.0이 갱신된다.
- `domain/`·`app/use_cases/`에 FastAPI·SQLAlchemy import가 없다(§12 Boundary Gate).

## 9. 마이그레이션 주의

공용 DB의 alembic head가 둘이다. 미병합 `feature/analysis-api`의 리비전과 이 브랜치의 리비전이 공존한다. `backend/docs/backend_ver_log.md` v0.23.0의 마이그레이션 항목에 적용 방식이 기록돼 있으니 같은 방식을 따른다. 새 리비전의 부모는 이 브랜치 head로 둔다.

autogenerate는 무관한 테이블 삭제를 오탐한다. 생성 결과를 눈으로 확인하고 이 7개 테이블 외의 변경은 지운다.
