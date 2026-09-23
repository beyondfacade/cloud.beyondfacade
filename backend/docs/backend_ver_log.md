# Backend Version Log

## [v0.27.0] - 2026-09-23

### Added
- **동네 프로필 조회 API** (`GET /profiles/...`) — v0.26.0이 만든 파생 지표를 화면이 읽는 길.
  설계서 §7이 "라우터는 화면과 함께"로 미뤄둔 것을 사이드패널 작업과 같이 붙였다
  - `GET /profiles/myself` — §12의 배선 검증. router → use_case → interactor → port → repository
    왕복을 하드코딩 데이터로 먼저 확인했다
  - `GET /profiles/{region_code}` — **분기를 생략하면 그 동의 최신 분기.** 화면은 어느 분기가
    최신인지 모른다. 프론트엔드에 `20262`를 박으면 다음 적재 때 조용히 옛 분기를 보여준다
  - `GET /profiles/{region_code}?year_quarter=20251` — 분기 지정
  - 없는 동·없는 분기 모두 404 `REGION_PROFILE_NOT_FOUND` 단일 코드. 에러 바디는 기존 계약
    `{error:{code,message}}` 그대로
  - 프랙탈 나머지 3파일(schema·inbound mapper·router) + `find_latest`를 UseCase·RepositoryPort·
    Interactor·Repository에 추가
  - **응답의 유형·시간대는 코드다.** 화면에 띄울 이름·괄호 설명·툴팁·서사는 프론트엔드가 갖는다
    (`industryLabel` 전례). `type_reason`만 예외로 한국어인데, 실제로 넘은 수치가 박힌 문장이라
    표현이 아니라 데이터이기 때문이다
  - `main.py`에 라우터 등록
- 테스트 6건 (`tests/test_metric_profile_api.py`) — myself 배선, 분기 생략 시 최신, 분기 지정,
  근거 수치 동반, 없는 동·없는 분기 404

### 검증
- 실DB 상대로 확인: `/profiles/1168064000`(역삼1동) → `office` · `day` ·
  "직장인구가 상주인구의 5.9배로 서울 상위 10%이고, 주말 유동이 평일보다 적습니다."
  `/profiles/9999999999` → 404 `REGION_PROFILE_NOT_FOUND`
- 테스트 298 통과 / 1 실패(`test_store_ingest.py::test_latest_source_updated_at_returns_cursor` —
  기존 알려진 건)

### 알려진 문제
- 8201의 상주 개발 서버(9/21 기동, `--reload`)가 리로드를 멈춘 채 미병합 `feature/analysis-api`의
  `/analysis` 라우트를 물고 있다. 현재 작업 트리와 맞지 않으므로 재기동이 필요하다
  (이번 검증은 8202에 별도 기동해 수행했고 끝난 뒤 정리했다)

## [v0.26.0] - 2026-09-23

### Added
- **파생 지표 2종** (`apps/metric/` 확장) — 적재한 999만 행에서 화면이 읽을 수 있는 것을 뽑는
  집계 계층. 새 BC를 만들지 않았다. `metric`은 이미 `store`+스냅샷을 읽어
  `region_industry_metric`을 배치로 만드는 집계 계층이고, 이번 파생도 성격이 같다.
  `commerce`/`neighborhood`를 가른 기준(업종 축 유무)은 파생에 적용되지 않는다 — 파생은 두
  원천을 모두 읽는다. 읽기 방향은 `metric` → `commerce`·`neighborhood`·`master` 단방향.
  설계서 `docs/superpowers/specs/2026-09-23-region-profile-design.md`
  - 프랙탈 세트 2벌(entity+ORM+orm_mapper+dto+ports input/output+interactor+repository) +
    게이트웨이 3종 + CLI + 도메인 서비스 3종. **라우터·스키마·인바운드 매퍼는 후속**
    (설계서 §7 범위 밖 — 화면과 함께 만들고 §12에 따라 `myself`로 배선부터 확인한다)
  - `region_profile_quarter` — 행정동×분기 동네 프로필. PK(region_code, year_quarter).
    유형 6종 + 시간대 라벨 + 판정 근거 지표 6개. 값 컬럼이 반복 그룹이 아니라 서로 다른
    측정값이라 유일하게 넓은 형태다(긴 형태로 내리면 "직장비와 주말지수를 같이"가 self-join).
    지표를 판정과 함께 저장하는 것은 의도한 역정규화 — 화면이 근거를 보여줘야 하는데 판정만
    있으면 999만 행에서 다시 계산해야 한다
  - `region_industry_hour_gap_quarter` — 행정동×업종×분기×시간구간 어긋남.
    PK 4컬럼. 유동인구 강도·매출 강도·차이를 함께 둔다. 단일 점수로 뭉개면 "어느 구간에서
    어긋나는가"를 말할 수 없고, 강도 둘이 없으면 "사람이 없는데 돈이 돈다"와 "사람도 돈도
    많다"를 구분할 수 없다
  - **시간대는 시간당 강도로 보정한다** (`domain/value_objects/hour_band.py`). 6구간 길이가
    6·5·3·3·4·3시간으로 다르다. 보정 없이 argmax를 취하면 **422개 동 중 375개가 `00_06`**으로
    뭉개진다(실측, 설계서 §3-1의 377/425와 일치). 유동인구와 매출 분해 양쪽에 똑같이 적용한다
  - **4블록(아침·낮·저녁·밤)** — 6구간 argmax는 조합이 16종으로 흩어지고 `00_06`·`21_24`가
    근접해 동전 던지기가 된다. 밤 블록이 그 둘을 흡수한다
  - **결정 목록** (`domain/services/typology.py`) — `if/elif`가 아니라 규칙 객체 7개 리스트
    (Chain of Responsibility, CLAUDE.md §5). 각 규칙이 판정과 근거 문장을 함께 반환하고 첫
    일치가 이긴다. 순서에 뜻이 있다 — 업무 밀집형이 앞이어야 명동·종로가 대학가형으로 새지
    않고, 대학가형이 먹자형보다 앞이어야 건대입구·신촌이 먹자형으로 새지 않는다
  - **임계값 하드코딩 금지** (`domain/services/quantiles.py`) — 11개 임계 전부 매 배치 그 창의
    422개 동 분포에서 재계산한다. 분류 문서의 수치(1.491 등)는 확인용이지 상수가 아니다
  - **판정 창은 최근 4분기** — 분기 단독은 불변 동이 75.1%, 4분기 이동평균은 81.6%다.
    원자료를 평균한 뒤 비율을 내고, **저장하는 지표도 판정에 쓰인 평활값**이라 근거 문장의
    수치와 화면 수치가 어긋나지 않는다
  - `build_region_profiles` CLI — 프로필 22분기(20211~20262), 어긋남 20분기(20211~20254).
    범위가 다른 이유는 어긋남이 매출을 필요로 하기 때문이다(설계서 §3-5). 원천이 정적
    아카이브라 크론 비대상
  - 마이그레이션 `a4e7b2c9d813`(부모 `f3c9a1d47b62`) — 테이블 2개 + 조회 인덱스 2개 +
    업종 매핑 4행. **head 처리**: v0.23.0~v0.25.0 전례대로 스크래치에 임시 ini
    (`version_locations` = 이 브랜치 versions + 미병합 리비전 2개 사본, `path_separator = space`)를
    얹어 적용했다. 리포지토리 `alembic.ini`는 건드리지 않았다
  - `migrations/env.py` — metric ORM 2종 autogenerate 등록

### Changed
- **`industry_source_code` seoul_commercial 매핑 12 → 16행.** 교차검증
  (`2026-09-23-commerce-crossvalidation.md` §3-2)이 `cafe`에 패스트푸드(CS100006)·분식(CS100008),
  `hair_salon`에 네일(CS200029)·피부(CS200030)를 더해야 우리 인허가 모집단과 맞는다고 결론냈는데
  시드는 1:1인 채였다. 그대로 뒀다면 두 업종의 시간대 매출이 조용히 과소 집계된다

### 검증 (설계서 §6 일곱 항목)
- **첫 실적재: 프로필 9,284행 + 어긋남 342,078행 / 33초.** 재실행 시 행 수 불변,
  `sum(gap)` 소수 6자리까지 동일 — 멱등 확인
- **유형 분포(20262)** 주거 251 · 먹자 55 · 업무 36 · 혼합 32 · 생활중심 25 · 대학가 23.
  분류 문서 실측(257·54·40·25·26·23)과 ±6 이내. 합 422인 것은 원천에만 있는 옛 행정동 3개가
  `region_code` NULL이라 프로필을 만들지 않기 때문이다(425 − 3)
- **상식 검증 9/9 일치** — 역삼1동·삼성1동·여의동 업무, 신촌동·안암동·흑석동 대학가,
  연남동 먹자, 중계1동·목5동 주거. 서교동(홍대) 먹자+저녁, 화양동(건대) 대학가+밤도 확인
- **상주인구 하한에 걸린 동 5개**(20262, 전 분기 누적 110행) — 둔촌제1동 16 · 반포본동 117 ·
  소공동 2,178 · 삼청동 2,247 · 명동 2,392. 반포본동 포함 확인. **설계서 §7-3이 "약 1,000명
  미만, 해당 동은 반포본동 하나"로 추정했으나 p1을 실제로 재면 2,400선이라 5개가 걸린다.**
  §3-3이 "하한값도 하드코딩하지 않고 분포에서 계산한다"고 못 박아 p1을 따랐다. 업무 밀집형이
  40 대신 36인 것의 상당 부분이 이것이다(명동·소공동·삼청동이 혼합형으로 빠진다)
- **안정성** 22분기 내내 유형 불변 338/422 = **80.1%**(기대 81% 안팎), 시간대 라벨 불변 69.0%
- **시간대 보정 전후** 보정 전 원값 argmax는 `00_06` 375 · `06_11` 35 · `17_21` 9 · `11_14` 2 ·
  `14_17` 1로 뭉개진다. 보정 후 4블록 라벨은 밤 226 · 평탄 106 · 낮 57 · 저녁 29 · 아침 4로
  흩어진다 (분류 문서 §6-3의 229·106·57·29·4와 사실상 일치)
- **어긋남 부호** 업종별 최대 어긋남 구간이 전부 상식과 맞는다 — 노래방 `21_24`(+2.06),
  당구장·헬스장·PC방 `17_21`, 학원·미용실 `14_17`, 카페·부동산 `11_14`.
  산술 불변식 `Σ(gap × 구간길이) = 0`의 최대 잔차 **5.8e-15**로 보정과 뺄셈이 닫혀 있다.
  주거형 카페 `17_21` +0.64로 양수
- **미충족 1건 — 업무 밀집형 카페 `06_11` gap이 음수(-0.30)다.** 설계서 §6-6은 양수를 기대했다.
  계산 오류가 아니라 기대의 전제가 다르다: `06_11` 유동 강도는 전 유형에서 1.00 근처로 평탄한데
  (5시간 구간이 이른 새벽을 포함한다) 카페 매출은 어느 동에서나 점심(`11_14` 3.16)이 압도해
  `06_11` 매출 강도가 0.70에 그친다. **출근길 신호는 절대 부호가 아니라 상대 순위에 있다** —
  `06_11` 카페 매출 강도는 업무 0.704 > 혼합 0.599 > 주거 0.582 > 생활중심 0.578 > 먹자 0.537 >
  대학가 0.437로 업무 밀집형이 1위다. 화면 문구는 "출근길에 매출이 몰린다"가 아니라 "다른
  동네보다 아침 매출 비중이 높다"로 써야 한다

### 알려진 한계
- `docs/erd.md` §6에 새 테이블 2개(v0.25.0의 8개 포함 총 13개)가 아직 반영되지 않았다
- 공용 DB `alembic_version`에 미병합 `feature/analysis-api` 리비전 `b2c3d4e5f6a7`가 남아 있다.
  병합 시 `alembic merge` 필요

## [v0.25.0] - 2026-09-23

### Added
- **neighborhood BC 신설** (`apps/neighborhood/`) — 서울시 상권분석서비스 **동네 맥락 7종** 적재.
  `commerce`가 업종 실적(분기×동×업종)을 담는다면 이쪽은 동네 맥락(분기×동)이다 — 누가 다니고,
  누가 일하고 살며, 무엇이 있고, 무엇에 돈을 쓰는지. 업종 축이 없다. BC를 나눈 근거는 어휘가
  다르고(매출·점포 대 유동인구·집객시설), `commerce`에 7테이블을 더하면 10이 되어 §12의 "AI가
  한 컨텍스트에 올려 이해하는 단위"가 무너지며, 소비하는 화면이 다르기 때문이다.
  설계서 `docs/superpowers/specs/2026-09-23-neighborhood-bc-design.md`
  - 프랙탈 세트 8벌(entity+ORM+orm_mapper+dto+ports input/output+interactor+repository) +
    게이트웨이 2종 + CLI. **라우터·스키마·인바운드 매퍼는 `convenience`·`childcare`·`commerce`
    전례대로 후속** (소비 라우터가 아직 없다)
  - `region_footfall_quarter` — 유동인구. PK(adstrd_code, year_quarter, dim_type, dim_key).
    total 1 · gender 2 · age 6 · hour 6 · dow 7 = 원본 1행 → 22행
  - `region_population_quarter` — 직장·상주 인구. PK에 `population_type`(worker|resident) 추가.
    total 1 · gender 2 · age 6 · gender_age 12 = 21행. **두 원천의 값 컬럼 21개가 한 글자도
    다르지 않아**(설계서 §3-3) 한 테이블로 합쳤다. 유동인구는 시간대·요일이 있고 성별×연령
    교차가 없어(흐름 대 등록 상태) 별도 테이블로 남겼다 — 합치면 "어떤 축이 어떤 인구유형에
    유효한가"를 스키마가 표현하지 못한다
  - `region_household_quarter` — 가구·아파트 스톡. 상주인구의 가구 3종(household) + 아파트
    단지·면적·가격 13종(apartment_complex/area/price). 가구 수는 인구가 아니라 주거 스톡이다
  - `region_housing_average_quarter` — **설계서 §4-3 미확정 1을 별도 테이블로 확정.**
    세대 수(개수)·평균 면적(㎡ 실수)·평균 시가(원)는 단위가 서로 달라 한 `value` 컬럼에 담으면
    dim_type을 보지 않고는 SUM/AVG가 의미를 갖지 않는다. `value_float` 추가안보다 정규화에 맞다
  - `region_facility_quarter` — 집객시설 total + 19종 = 20행
  - `region_spending_quarter` — 지출 total + 10종 = 11행
  - `region_commerce_change` — 동별 상권 변화 지표. 지표가 범주형(HH·HL·LH·LL)이라 유일하게
    넓은 형태다. `change_name`은 `change_code`에 함수 종속이라 엄밀히 3NF 위반이지만 코드 4종
    고정 매핑이고 원천이 두 컬럼을 같이 주므로 근거를 남기고 유지(§13 부분적 역정규화)
  - `seoul_commerce_change_baseline` — **2NF 분리.** 원천의 `서울_운영/폐업_영업_개월_평균`이
    행정동이 아니라 분기에만 의존한다(22분기 전부 고유값 1개). 425개 동 행에 같은 값이 반복되는
    부분 함수 종속이라 떼어냈다. 분리하면 분기만 키라 고립되므로
    **`region_commerce_change.year_quarter`가 이를 FK로 참조해 노드로 세운다**(§13 엣지).
    따라서 적재 순서는 baseline이 먼저다 (테스트로 고정)
  - **실데이터 기반 결정**: 인코딩 CP949 · 줄바꿈 LF(commerce ZIP 내 CSV는 CRLF였다),
    시점 컬럼 `기준_년분기_코드` 5자리 문자열, **범위 20211~20262 22분기**(commerce 20분기보다
    2분기 넓다 — 자르지 않고 전량 적재하고 조인 시 `<= '20254'`로 자르는 것은 조회하는 쪽 몫),
    결측은 0이 아니라 NULL 보존
  - **컬럼은 순서가 아니라 이름으로 찾는다** (commerce 분해와 반대 — 거긴 헤더 오타 때문에
    순서가 진실이었다). 데이터셋별 규칙 차이를 매핑 표에 박았다
    · 유동인구 시간대는 **밑줄** `시간대_00_06_유동인구_수` (commerce 추정매출은 물결표 `00~06`)
    · 직장은 접미사 `_직장_인구_수`, 상주는 `_상주인구_수` — 모양이 다르다
    · **소비는 `음식_지출_총금액`이 `기타_지출_총금액` 뒤에 온다.** 순서로 매핑하면 `etc`와
      `food`가 통째로 뒤바뀐다. 음식 지출은 상권 분석의 핵심 항목이라 결론이 반대가 된다
      (실 원천 1행으로 테스트 고정)
    · 헤더에 기대한 이름이 없으면 조용히 NULL을 적재하는 대신 `ValueError`로 즉시 깨뜨린다
  - **dim_key는 commerce 매출 분해와 같은 표기로 정규화**했다(`00_06`, `60_over`). 값 객체는
    도메인이라 전역 `core/`에 둘 수 없고 BC 독립성이 중복 제거보다 우선이므로
    `domain/value_objects/quarter_dimension.py`에 각자 갖는다(설계서 §5). 나중에 두 BC를 조인할 때
    구분자 차이로 어긋나지 않게 하려는 것이다
  - **region 해석**: 원천 `행정동_코드` 8자리 ↔ `region.region_code` 앞 8자리 1:1. region 427행을
    맵으로 1회 로드(행마다 조회 없음). 원천에만 있는 옛 행정동 3개(`11230536` 용신동·`11680740`
    일원2동·`11740520` 상일동)는 버리지 않고 `region_code` NULL로 적재
  - 인터랙터 7개가 공유하는 적재 절차를 `app/use_cases/region_quarter_ingest.py`에 한 벌만 뒀다
    (Template Method). 게이트웨이는 commerce 분해 전례대로 list가 아니라 **Iterator**를 돌려주고
    인터랙터가 `CHUNK_SIZE=40,000`마다 업서트(=커밋 1회)한다
  - `load_neighborhood` CLI — `--kind footfall|worker|resident|apartment|facility|spending|change|all`.
    원천 디렉토리와 테이블이 1:1이 아니다(상주 → 인구+가구, 아파트 → 스톡+평균, 상권변화 →
    baseline+동별). 원천이 정적 아카이브라 크론 비대상
  - 마이그레이션 `f3c9a1d47b62`(부모 `d8b5c3f27a41`) — 테이블 8개 + 조회 인덱스 7개.
    **head 처리**: 공용 DB `alembic_version`에 미병합 `feature/analysis-api` 리비전
    `b2c3d4e5f6a7`가 남아 있어 v0.23.0·v0.24.0 전례대로 스크래치에 임시 ini
    (`version_locations` = 이 브랜치 versions + 미병합 리비전 2개 사본, `path_separator = space`)를
    얹어 적용했다. 리포지토리 `alembic.ini`는 건드리지 않았다. autogenerate가 오탐한 무관 변경
    6건(analysis_report·llm_usage 테이블 삭제, rag_chunk HNSW 인덱스 삭제, store 지오코딩 인덱스
    삭제, store 주소 2컬럼 삭제)은 전부 걷어냈다
  - `migrations/env.py` — neighborhood ORM 8종 autogenerate 등록
  - **첫 실적재: 1,051,204행 / 1분 15초** (재실행 1분 14초, 행 수 불변·값 갱신으로 멱등 확인).
    footfall 205,700 · population 387,618(worker 191,268 + resident 196,350) · household 149,353 ·
    housing_average 9,331 · facility 187,000 · spending 102,850 · commerce_change 9,350 ·
    baseline 22. 전 테이블 22분기(20211~20262) 연속. region 미기입은 전부 위 3개 코드에서만
    발생(footfall 1,452행 = 3×22×22, 0.706%), 기입된 행의 앞 8자리 불일치 0건.
    직장인구는 414개 동으로 상주 425개 대비 11개가 비어 있음을 확인(하계2동·신정6동·가양2동·
    구로1동·항동·일원본동·일원2동·위례동·잠실7동·암사3동·둔촌1동). 아파트는 `11740690`
    둔촌1동이 20211~20213 3분기만 존재. 상권변화 지표 분포 LL 3,581 · HH 2,630 · HL 1,678 ·
    LH 1,461 (설계서 §3-6 실측치와 일치)
  - 테스트 19건 (`tests/test_neighborhood_load.py`) — CP949 파싱·년분기 문자열 보존, 데이터셋별
    컬럼 이름 매핑(지출 `음식`/`기타` 순서 함정 포함), 각 데이터셋의 원본 1행 → N행 전개와
    dim_type·dim_key 정확성, 헤더 변경 시 즉시 실패, 공란 NULL 보존, region 8자리 접두 해석과
    미매칭 행 보존, 직장인구 파일에 있는 동만 적재, 서울 평균 분기별 중복 제거, baseline FK 순서,
    실DB 멱등 업서트와 전 배선 재적재

### Notes
- **총합 일치 검증 — 원천 품질 판정** (적재 후 SQL 실측, 원본 9,350행 / 직장 9,108행 전수)

  | 데이터셋 | 축 | 정확일치 | 개별행 최대 괴리 | 총량 커버리지 |
  |---|---|---|---|---|
  | 유동인구 | gender | 49.67% | 3명 | **1.000000** |
  | 유동인구 | age | 30.23% | 5명 | **1.000000** |
  | 유동인구 | hour | 29.94% | 5명 | **1.000000** |
  | 유동인구 | dow | 27.52% | 5명 | **1.000000** |
  | 직장인구 | gender / age / gender_age | **100%** | 0 | 1.000000 |
  | 상주인구 | gender / age / gender_age | **100%** | 0 | 1.000000 |
  | 지출 | 10종 합 | **100%** | 0 | 1.000000 |
  | 집객시설 | 19종 합 | **0%** | 391개 | **0.483841** |

  - **유동인구 네 축은 모두 총계의 완전 분할이다.** 개별 행 정확일치율이 낮아 보이지만 괴리
    분포가 0명 2,573 · 1명 4,131 · 2명 1,964 · 3명 558 · 4명 114 · 5명 10으로 전부 5명 이하이고
    총량 커버리지가 소수 6자리까지 1.000000이다. 원천 반올림이며 실질 완전 분할이다.
    commerce 추정매출의 gender·age가 89.2%만 덮었던 것과 달리 **여기서는 미상 구간이 없다**
  - **직장·상주인구와 지출은 한 행도 어긋나지 않는다.** `gender_age` 12구간의 합까지 총계와
    정확히 같아, 주변합(gender·age)과 교차(gender_age)를 나란히 써도 된다
  - **집객시설만 어긋난다. `집객시설_수`(total)는 19종의 합이 아니다.** 9,350행 전부에서
    total > 19종 합이고(합이 큰 행 0건, 같은 행 0건) 비율은 최소 0.2105 · 중앙값 0.4860 ·
    최대 0.9211, 총량으로 48.4%다. 대표 사례는 중구 명동 — 전 분기에서 total 542 대 19종 합
    151(차이 391). 버스정거장을 빼면 24.6%로 더 내려가므로 특정 종이 이중계상된 것이 아니라
    **원천의 `집객시설_수`가 파일에 실리지 않은 시설 종류까지 포함하는 더 넓은 정의**로 보인다
  - **따라서 집객시설은 total과 19종을 같은 표에 나란히 놓으면 안 된다.** 19종은 "이 동에
    어떤 종류가 있는가"를 말하는 구성 지표로만 쓰고, `total`은 별도 지표로 표시하거나 쓰지
    않는다. 19종 합을 total로 나눈 비율은 의미 없는 수치다. 이 제약은 후속 라우터·리포트에
    반드시 반영한다
  - `철도_역_수`는 9,350행 전부 공란이다(NULL 100%). 원천이 서울 행정동 단위로는 집계하지
    않는 항목이다. NULL 보존이라 "0개"로 오독될 여지가 없다
- 파생 지표(동네 유형 분류, 시간대 서사 라벨, 유입·유출 지수)와 프론트엔드 연결은 설계서 §7대로
  범위 밖 — 후속 작업
- `docs/erd.md` §6 갱신은 이번 작업 범위 밖으로 남겨 둠

## [v0.24.0] - 2026-09-23

### Added
- **추정매출 분해 47컬럼 적재** (`apps/commerce/`) — v0.23.0에서 범위 밖으로 남겼던 요일·시간대·
  성별·연령대 분해를 1NF long 테이블로 적재. 프랙탈 세트 1벌 추가(entity+ORM+orm_mapper+dto+
  ports+interactor+repository) + 게이트웨이·CLI 확장. 라우터·스키마·인바운드 매퍼는 commerce BC
  전례대로 후속. 설계서 `docs/superpowers/specs/2026-09-23-commerce-bc-design.md` §4-1
  - `region_commerce_sales_breakdown` 테이블 — PK(adstrd_code, service_industry_code,
    year_quarter, dim_type, dim_key), region FK nullable, `amount`·`count` bigint nullable
  - **wide 53컬럼으로 두지 않는 근거**: 축이 늘 때마다 DDL이 필요하고 "시간대 상위 3구간" 같은
    질의가 47컬럼 UNION이 된다. (dim_type, dim_key)를 값으로 내리면 축 추가가 적재만으로 끝난다
  - **부모 `region_commerce_sales`와 복합 FK로 묶었다.** 부모 PK가 정확히 같은 3컬럼이라 대응
    UNIQUE를 새로 만들 필요가 없어 비용이 0이고, "총액 없는 분해 행"이라는 모순 상태가 DB에서
    막힌다(테스트로 고정). `region_code` FK는 부모를 거치지 않고 동 단위로 바로 조회하기 위해
    그대로 유지 — ERD §13 엣지 + 8자리↔10자리 `left()` 조인 회피(§4-1과 동일 근거)
  - 분해 축 23구간: weekpart 2(weekday·weekend) · dow 7(mon~sun) · hour 6(00_06·06_11·11_14·
    14_17·17_21·21_24) · gender 2(male·female) · age 6(10·20·30·40·50·60_over).
    금액·건수를 한 행에 같이 둔다 — 같은 구간의 두 측정치라 키가 동일하다. 쪼개면 같은 구간을
    두 번 저장하게 된다
  - **헤더 순서 기반 매핑** (`breakdown_columns`) — 원천 시간대 건수 6종 헤더가
    `시간대_00~06_매출_건수`가 아니라 **`시간대_건수~06_매출_건수`** 오타다. 이름으로 찾으면
    시간대 건수가 통째로 누락되거나 엉뚱한 구간에 붙는다. `당월_매출_건수` 위치를 기준으로
    금액 23컬럼 블록 + 같은 순서의 건수 23컬럼 블록을 잡고, 컬럼 수가 어긋나면 조용히 밀리는
    대신 ValueError로 즉시 깨뜨린다. 5개 파일 헤더 전부 동일 실측(2025년만 CRLF, 나머지 LF —
    `newline=""` csv.reader가 흡수)
  - **스트리밍 계약** — 게이트웨이가 list가 아니라 Iterator를 돌려준다. 원본 1행이 23행으로
    펼쳐져 파일 1개가 약 158만 행이라 list로 들면 한 파일치가 수백 MB다. 인터랙터가
    `CHUNK_SIZE=40,000`마다 업서트(=커밋 1회)하고 버린다. 리포지토리 배치는 8컬럼 × 8,000 =
    64,000 파라미터 < psycopg 한도 65,535. 실측 최대 상주 메모리 353MB
  - `load_commerce` CLI `--kind sales_breakdown` 추가. `all`은 sales → store → sales_breakdown
    순서로 돈다(분해는 부모 sales 행이 있어야 복합 FK를 통과한다)
  - 마이그레이션 `d8b5c3f27a41`(부모 `c7a4f2e19b35`) — 테이블 + 조회 인덱스
    `ix_region_commerce_sales_breakdown_region_industry`(region_code, 업종, 년분기, dim_type).
    **head 처리**: 공용 DB `alembic_version`에 미병합 `feature/analysis-api` 리비전
    `b2c3d4e5f6a7`가 남아 있어 이 브랜치 versions/만으로는 리비전 해석이 안 된다. v0.23.0 전례대로
    스크래치에 임시 ini(`version_locations` = 이 브랜치 versions + 미병합 리비전 2개 사본,
    `path_separator = space`)를 얹어 적용했다. 리포지토리 `alembic.ini`는 건드리지 않았다.
    autogenerate가 오탐한 무관 변경(analysis_report·llm_usage 테이블 삭제, rag_chunk HNSW 인덱스
    삭제, store 주소 2컬럼 삭제)은 전부 걷어내고 새 테이블·인덱스만 남겼다
  - `migrations/env.py` — breakdown ORM autogenerate 등록
  - **첫 실적재: 7,892,841행** (343,167 × 23, 부모 키 343,167 전수 커버, 20분기 20211~20254).
    소요 13분 07초(약 10,000행/s — 병목은 DB가 아니라 파이썬 측 파라미터 바인딩:
    부하 중 세션이 `idle in transaction / ClientRead`였다). region 미기입 49,956행(0.6329%) =
    2,172 부모행 × 23, 전부 원천에만 있는 옛 행정동 3개(11230536 용신동 24,403 · 11740520
    상일동 16,652 · 11680740 일원2동 8,901)에서만 발생. 기입된 행의 앞 8자리 불일치 0건.
    측정값 NULL 0건(원천 46개 분해 컬럼에 공란 0건 실측 — 0 채움이 아니라 원천이 실제로 빈칸이
    없다). 재실행 시 행 수 불변·값 갱신(멱등 확인 — 2회차 12분 24초, 7,892,841행 전량
    업서트). VACUUM ANALYZE 후 테이블 총 크기 1,818MB(데이터 + PK·조회 인덱스 2종)

### Notes
- **축별 합계 일치 검증 — 원천 품질 판정** (343,167 부모행 전수, 적재 후 SQL 실측)

  | 축 | 금액 정확일치 | 건수 정확일치 | 개별행 최대 괴리 | 총량 커버리지(금액/건수) |
  |---|---|---|---|---|
  | weekpart | 99.992% | 99.985% | 2원 / 2건 | 1.000000 / 1.000000 |
  | dow | 99.984% | 99.982% | 4원 / 4건 | 1.000000 / 1.000000 |
  | hour | 99.984% | 99.981% | 5원 / 4건 | 1.000000 / 1.000000 |
  | gender | 36.042% | 35.707% | 410,803,487,481원 | **0.892166** / 0.959266 |
  | age | 35.922% | 35.417% | 410,803,487,480원 | **0.892167** / 0.959266 |

  - **weekpart·dow·hour 세 축은 총액의 완전 분할이다.** 불일치는 각각 27·54·54행(전체의 0.02%
    이하)뿐이고 괴리가 최대 5원·5건이라 원천 반올림으로 설명된다. 시간대 질문("출근 시간대에
    매출이 몰리는가")은 이 데이터로 그대로 답할 수 있다
  - **gender·age 두 축은 완전 분할이 아니다.** 인구속성이 확인되지 않은 거래가 빠져 금액의
    89.2%, 건수의 95.9%만 덮는다. 두 축의 커버리지가 소수 6자리까지 같아(0.892166 vs 0.892167)
    **같은 부분집합을 성별/연령으로 각각 자른 것**임이 확인된다. 건수 커버리지(95.9%)가 금액
    커버리지(89.2%)보다 높다 — 미상 거래의 건당 금액이 크다는 뜻이고, 법인카드·고액결제가
    인구속성 없이 집계된다는 해석과 맞는다
  - 최악 사례는 용산 한강로동 `CS300003` 컴퓨터및주변장치판매 2021Q4로 성별 커버리지 46.19%
    (총액 7,634억 중 3,526억만 성별 분해). 용산전자상가 B2B 거래 성격과 일치한다
  - **따라서 gender·age 축은 절대금액이 아니라 축 내부 구성비로만 써야 한다.** "이 동 카페
    30대 매출 = N원"은 89% 표본 위의 값이라 총액과 나란히 놓으면 안 된다. 구성비("30대가
    성별·연령 확인분의 몇 %")는 유효하다. 이 제약은 후속 라우터·리포트에서 반드시 반영한다
- 설계서 §6 교차검증 3~5(점포 수 모집단 괴리, cafe·gym 매핑 판정, HANDOFF 첫 질문 시범 답변)는
  v0.23.0에 이어 여전히 후속
- `docs/erd.md` §6 갱신은 이번 작업 범위 밖으로 남겨 둠

## [v0.23.0] - 2026-09-23

### Added
- **commerce BC 신설** (`apps/commerce/`) — 서울시 상권분석서비스 행정동 계열 적재.
  convenience·childcare 전례대로 소비 라우터가 아직 없어 entity+ORM+orm_mapper+dto+ports+
  interactor+gateway+repository+CLI 구성 (라우터·스키마·인바운드 매퍼는 후속).
  설계서 `docs/superpowers/specs/2026-09-23-commerce-bc-design.md`
  - **원천**: 서울 열린데이터광장 공개분 로컬 CSV (`data/raw/seoul_commerce/`, 공공누리 1유형,
    API 호출 0회). 빅데이터캠퍼스 카드소비는 원 수치 반출 불가라 사용하지 않음
    · `sales_adstrd/` OA-22175 추정매출-행정동 연도별 5파일
    · `store_adstrd/` OA-22172 점포-행정동 연도별 5파일
  - `region_commerce_sales` 테이블 — PK(adstrd_code, service_industry_code, year_quarter),
    region FK nullable, 당월 매출 금액·건수. 요일·시간대·성별·연령대 분해 47컬럼은 범위 밖
    (적재 시 wide 53컬럼이 아니라 `(dim_type, dim_key, amount, count)` long 테이블로 1NF 준수)
  - `region_commerce_store` 테이블 — 같은 PK + 점포 수·유사 업종 점포 수·개업률/폐업률·
    개폐업 점포 수·프랜차이즈 점포 수
  - **industry_id를 사실 테이블에 저장하지 않는 근거**: cafe(휴게음식점 모집단 ↔ 커피-음료)와
    gym(체력단련장업 ↔ 스포츠클럽) 매핑이 미확정이라, 박아 넣으면 매핑 변경 때마다 34만/70만 행
    재적재가 필요하다. `industry_source_code`를 거쳐 조인한다
  - **실데이터 기반 결정**: 인코딩 CP949, 연도 컬럼은 `기준_년_코드`가 아니라 `기준_년분기_코드`
    5자리 문자열(`20251`=2025Q1 — 정수로 바꾸면 연도와 구분 불가), 점포 쪽 표기는 `개업_율`/
    `폐업_률` 비대칭(원천 그대로), 매출 헤더 오타 `시간대_건수~06_매출_건수`(분해 컬럼을 이름으로
    찾는 코드는 순서 기준 필요), 결측은 0이 아니라 NULL 보존(childcare `EW_CNT_TOT` 전례).
    원천 전량에 공란·비수치·PK 중복 0건 실측
  - **region 해석**: 원천 `행정동_코드` 8자리 ↔ `region.region_code` 10자리 앞 8자리 1:1
    (427행 접두 충돌 0건). region 427행을 8자리 키 맵으로 1회 로드 — 행마다 조회하지 않음.
    원천에만 있는 옛 행정동 3개(`11230536` 용신동·`11680740` 일원2동·`11740520` 상일동)는
    **버리지 않고 region_code NULL로 적재**한다. 용신동을 신설동·용두동으로 쪼개는 안분은
    근거가 없어 하지 않음. 결과적으로 우리 427개 동 중 5개는 매출·점포 데이터가 없다
  - `load_commerce` CLI — `python -m apps.commerce.adapter.inbound.cli.load_commerce [--kind sales|store|all]`.
    원천이 정적 아카이브라 크론 비대상 (갱신은 파일 재확보 후 재실행)
  - 마이그레이션 `c7a4f2e19b35` — 두 테이블 + 조회용 복합 인덱스 2개 +
    `industry_source_code` `source_system='seoul_commercial'` 12행 시드
    (academy 4행 + 8종 각 1행, childcare는 원천에 대응 업종 부재). autogenerate 오탐을 피하려
    수기 작성 — 이 브랜치 head와 실DB 리비전이 갈라져 있어 autogenerate가 무관한 삭제를 오탐한다
  - **첫 실적재**: sales 343,167행 · store 704,470행 (20분기 2021Q1~2025Q4 연속, 결측 분기 없음).
    업종 고유값 sales 63 · store 100(카드매출 추정이 가능한 업종만 매출에 존재), 행정동 425개.
    region 미기입 sales 2,172행(0.633%) · store 4,798행(0.681%) — 전부 위 3개 코드에서만 발생,
    기입된 행의 앞 8자리 불일치 0건. 로더 재실행 시 행 수 불변·값 갱신(멱등 확인)
  - 테스트 6건 (`tests/test_commerce_load.py`) — CP949 디코딩·년분기 문자열 보존·컬럼 매핑,
    `개업_율`/`폐업_률` 비대칭 표기, 공란 NULL 보존, 8자리 접두 해석과 미매칭 행 보존,
    실DB 멱등 업서트(행 수 불변·값 갱신) + 게이트웨이→인터랙터→리포지토리 전 배선 재적재
  - `migrations/env.py` — commerce ORM 2종 autogenerate 등록

### Notes
- 설계서 §6 교차검증 5항목 중 1·2(행 수·분기·region 해석률)만 이번에 수치로 확정. 3~5
  (상권분석 점포 수 ↔ `region_industry_metric.store_count` 모집단 괴리, cafe·gym 매핑 판정,
  HANDOFF 첫 질문 시범 답변)는 후속
- `docs/erd.md` §6 갱신은 이번 작업 범위 밖으로 남겨 둠

## [v0.20.0] - 2026-09-17

### Added
- **childcare BC 신설** (`apps/childcare/`) — 어린이집 축: 정원 대비 현원(가동률)·입소대기 직접 관측
  (brainstorming §3.5 "어린이집은 가동률이 그대로 보인다"). convenience 전례대로 소비 라우터가 아직
  없어 entity+ORM+ports+interactor+gateway+repository+CLI 구성 (라우터 후속)
  - **원천**: 어린이집정보공개포털 cpmsapi030 × 자치구 25회/스냅샷 (`CHILDCARE_API_KEY` 운영계정 —
    일 1,000회 한도의 2.5%). https 전용(http는 빈 응답), XML, 1회 호출에 구 전체 반환(페이징 없음 —
    최다 송파 274건), 인증 실패도 HTTP 200 + `<errcode>` 본문 → 게이트웨이가 RuntimeError로 전파
  - `childcare_center` 테이블 — 시설. PK=stcode, district FK 필수(요청 arcode), region FK nullable
    (좌표 공간조인 — store `RegionIndex` 읽기 전용 재사용, tobacco 전례), 유형·상태·주소·좌표·
    인가/휴지/폐지일, 관측 필드 first/last_seen_on(재수집 시 first_seen·region_code 보존)
  - `childcare_center_stat` 테이블 — PK(center_id, base_date=datastdrdt) 기준일별 정원·현원·
    입소대기·반 수·보육교직원 수. **시설 행에 덮어쓰지 않는 근거**: 현원·대기는 시점마다 변해
    덮어쓰면 가동률 추이가 복구 불가로 소실
  - 실데이터 기반 결정: `crchcnt`=`CHILD_CNT_TOT`, `chcrtescnt`=`EM_CNT_TOT` 전수 일치(중복 필드 1개만
    저장), `EW_CNT_TOT` 공란은 NULL 보존("0" 표기 실측 0건이라 0 추정 금지), 상태 공란 3건(현원 0)
    NULL 보존, 대표자명(가정 어린이집 개인 실명) 미수집, 연령별 세부는 1NF상 age_band 행 테이블로 후속
  - **공간조인 가드**: 판정 행정동이 등록 자치구 밖(region_code 앞 5자리 불일치)이면 미기입 —
    동작구 등록 시설 좌표가 시청 인근(중구)을 가리키는 원천 오류 실측
  - 마이그레이션 `8236d5263b60` — 두 테이블 + `ix_childcare_center_region_last_seen`
    (autogenerate가 잡은 rag_chunk HNSW 인덱스 삭제 오탐은 제거)
  - **첫 실적재: 3,940건** (API 25회, 실패 구 0): 상태 정상 3,805·재개 72·휴지 60·공란 3,
    유형 국공립 1,851·가정 985·민간 711·직장 299·법인·단체등 57·협동 21·사회복지법인 16.
    좌표 결측 7, region 기입 3,912(미판정 21 — 자치구 불일치·경계 밖), 행정동 426/427 커버.
    서울 가동률 67.8%(현원 130,019/정원 191,788, 정원 초과 0) — 구별 최저 종로 56.9%·최고 성북 76.5%.
    입소대기 채움 3,415건, 최다 송파 위례새솔어린이집 692명(정원 230)
  - `scripts/childcare-collector.sh` + 크론 등록 (매주 월 05:30) — 로그 `logs/childcare-collector.log`
  - `core/matrix/grid_keymaker_secret_manager.py` — `childcare_api_key` 설정 추가
  - 테스트 11건 — 게이트웨이 XML 픽스처(실응답 사본 필드 매핑·공란 대기/좌표/상태 None·errcode 전파)
    + 실DB 업서트(first/last_seen·같은 기준일 멱등·새 기준일 이력 누적·소실 시 last_seen 정지·
    상태 공란 적재·재수집 시 region_code 보존) + 공간조인 자치구 가드 순수 함수
    — 전체 193건 중 192 passed (기지 실패 1건: test_store_ingest 실DB 커서 테스트, 기존 상태 유지)
- **childcare 조회 API 2종** (지도 마커·사이드패널 소비처 — 1테이블 1라우터, §12 11-File Set 완비)
  - `GET /childcare-centers/myself`, `GET /childcare-centers?region=` — 운영 중·좌표 보유 시설 +
    시설별 최신 현황(유형·상태·정원·현원·입소대기·기준일) 마커 계약
  - `GET /childcare-center-stats/myself`, `GET /childcare-center-stats/summary?region=` — 행정동 운영 중
    시설 최신 현황 합계(시설 수·정원·현원·가동률·입소대기 합·기준일). 합산 규칙은 도메인
    `ChildcareRegionSummary.of`(정원 0이면 가동률 None, 대기 전 시설 공란이면 None)
  - 미등록 행정동은 404 `REGION_NOT_FOUND` (`RegionCatalogGateway` — master region 존재 확인, 어댑터 레이어 cross-BC)
  - **운영 중 판정 = 자치구 최신 관측일(max last_seen_on)에 관측된 시설** — 전역 최대가 아니라 자치구 단위라
    한 구 수집이 실패해도 그 구 시설이 지도에서 사라지지 않음. 조인 쿼리 `operating_centers_with_latest_stat`을
    조회 리포지토리 2종이 공유
  - 실서버 검증: 청운효자동 4곳·가동률 62.1%·입소대기 108건, 미등록 region 404
  - 테스트 9건 — myself 배선 2·마커/요약 계약·404 에러 바디·도메인 합산 2(Fake 포트) + 실DB 리포지토리 2
    (소실 시설 제외·좌표 없는 시설은 마커 제외/요약 포함·시설별 최신 기준일 선택)
    — 전체 202건 중 201 passed (기지 실패 1건 동일)
- **convenience 조회 API** (`apps/convenience` — v0.18.0 수집 전용 BC에 지도 소비처 추가, §12 11-File Set 완비)
  - `GET /convenience-stores/myself`, `GET /convenience-stores?region=` — 좌표 보유 현행 편의점 마커
    (상호·지점명·브랜드·좌표·도로명주소)
  - `GET /convenience-stores/summary?region=` — 행정동 현행 편의점 수·브랜드 분포(건수 내림차순·동수는 브랜드명 순,
    미확인 None은 맨 뒤)·원천 기준연월. 합산 규칙은 도메인 `ConvenienceRegionSummary.of`
  - 미등록 행정동 404 `REGION_NOT_FOUND` (BC별 `RegionCatalogGateway` — BC 간 직접 import 금지로 childcare와 별도)
  - **현행 판정 = 행정동 최신 관측일(max last_seen_on)** — 수집 단위가 행정동이라 동 단위 판정
  - 실서버 검증: 역삼1동 149곳(GS25 54·세븐일레븐 49·CU 34·이마트24 7·미니스톱 2·기타 3, 기준 202606), 미등록 region 404
  - 테스트 7건 — myself 배선·마커 계약(좌표 없는 행 제외)·요약 계약·404·도메인 정렬/빈 목록(Fake 포트) +
    실DB 리포지토리 1(소실 점포·이전 스냅샷 제외) — 전체 209건 중 208 passed (기지 실패 1건 동일)
- **어린이집·편의점 점포수 지표** (`apps/metric`) — 단계구분도 `점포수`·사이드패널 점포수 카드가 두 업종에서도 채워짐
  - `SnapshotStoreCountPort` + `ChildcareStoreCountGateway`·`ConvenienceStoreCountGateway` — 조회 API와 같은 현행 판정
    (어린이집 자치구 최신 관측·region 기입분, 편의점 행정동 최신 관측)으로 행정동별 현행 점포수, 연도 = 최신 관측일 연도
  - `RegionIndustryMetricInteractor.build`가 store 원천 연도 집계에 스냅샷 점포수를 합류 (`snapshot_counts` 주입, 기본 빈 목록)
  - **개폐업 수·폐업률·성장률은 0이 아니라 NULL** — 스냅샷 원천은 개폐업 이력이 없다(어린이집: 원천이 폐지 시설 미반환,
    편의점: 상가정보 업소번호 재생성 이력). 과거 연도(2019~2025)도 복원 불가라 관측 연도(2026)에만 적재.
    편의점 담배소매인(`tobacco_retailer`) 지정·취소일 대체 산출은 검토 후 채택하지 않음(슈퍼·가판 혼재)
  - 마이그레이션 `e2a08b1e8f19` — `region_industry_metric.open_count`/`close_count` nullable
    (autogenerate의 rag_chunk HNSW 인덱스 삭제 오탐 제거)
  - 재집계 21,005건: childcare 2026 426개 동·합계 3,912(= region 기입 시설 수), convenience_store 2026 427개 동·합계 9,395
    (= 적재 점포 수) — 청운효자동 어린이집 점포수 4개·역삼1동 편의점 149개 카드 실확인, 폐업률 조회는 빈 배열
  - 반영 주기: `build_metrics`는 store-collector 크론(매일 04:20) 후속 — 월요일 스냅샷(05:30·05:40)은 다음 날 지표에 반영
  - 테스트 4건 — 스냅샷 점포수 합류(개폐업·비율 None, 점포수 조회값·폐업률 빈 배열)·대상 연도 밖 제외(Fake 포트) +
    실DB 게이트웨이 2(소실·region 미기입 제외) — 전체 213건 중 212 passed (기지 실패 1건 동일)

## [v0.19.0] - 2026-09-15

### Added
- **`apps/rag` BC 신설** — RAG 색인·검색 전 태스크(1~7) 완주. 스펙(§0) 혼용 구도: **색인 임베더는
  provider 선택(fp16/ollama/gemini)**, **검색(query) 임베더는 Ollama Q4 고정**(저지연·상시 가용)
  - `rag_chunk` 테이블 — `vector(1536)` + HNSW 인덱스, source_type/source_id 복합 인덱스,
    region_code FK(nullable)
  - `EmbeddingPort` + 어댑터 3종: `OllamaQwen3EmbeddingAdapter`(색인 Q4 + 검색 고정),
    `Fp16Qwen3EmbeddingAdapter`(로컬 GPU, 지연 로딩), `GeminiEmbeddingAdapter`(온라인, 429 재시도)
    — 3개 전부 1536차원 규격 통일
  - `build_funding_chunk`/`build_news_chunk` 순수 빌더 + `FundingRagSourceGateway`/
    `NewsRagSourceGateway`(cross-BC 접근은 게이트웨이 파일 안에만 국한)
  - `SqlAlchemyRagRepository` — chunk_id 업서트, 코사인 유사도 검색(`exclude_expired_funding`
    기본 True — funding만 outerjoin, non-funding은 NULL join으로 드롭되지 않게 조건 구성)
  - `RagIndexUseCase`/`RagSearchUseCase`(ISP로 role별 분리) + `RagIndexInteractor`/
    `RagSearchInteractor` — 색인/검색이 서로 다른 EmbeddingPort 구현을 주입받아 혼용 구도를 코드로 강제
  - `build_rag_index.py`(CLI, `--full`/`--provider`) + `scripts/rag-indexer.sh` 크론(매일 05:50,
    provider=fp16 명시 — 크론이 조용히 다른 모델로 색인해 혼용 구도가 깨지는 사고 방지)
  - **초기 색인 실행: 6,157건** (funding 1,761 + news 4,396) — **Q4(ollama)로 수행**.
    fp16 전량 재색인은 GPU 점유(다른 상주 모델)로 보류 중 — 필요 시 수동
    `--full --provider fp16` 실행 필요 (Task 6에서 파킹, 본 태스크에서도 동일 사유로 재확인)
  - `get_rag_search_use_case(provider: str = "ollama")` — 레지스트리 재사용으로 검색 임베더를
    fp16/gemini로도 스왑 가능하게 확장(운영 기본값은 그대로 ollama, 평가 하네스 전용 확장)
- **Recall@5 평가 하네스** (`evaluate_rag.py`, CLI) — 순수 함수 `recall_at_k(relevant, ranked, k=5)`,
  `mrr(relevant, ranked)` + `--evalset`/`--provider {ollama,fp16,gemini}` 실행 →
  콘솔 출력 + `data/eval/results/rag_{provider}_{YYYYMMDD_HHMMSS}.json` 저장.
  status=confirmed만 본지표, candidate 포함 전체 수치는 "(참고)" 라벨로 분리(후보 평가셋은
  미검수라 본지표에 넣지 않음)
- **평가셋 후보 생성** (`generate_evalset.py`, CLI) — 색인된 funding 청크를 chunk_id 오름차순
  정렬 후 앞 50건 결정적 표본 추출 → 각 content를 Ollama `/api/chat` gemma3:12b에
  "이 공고를 찾을 법한 자연어 질문 1개(공고명 복사 금지)" 프롬프트로 전송해 질문 생성 →
  `data/eval/rag_evalset.jsonl`(status=candidate) 50행 생성 완료(약 54초 소요)
  - **candidate → confirmed 승격은 사용자 검수 몫 — 이 태스크의 범위 밖**
  - 하네스 시운전(candidate 50건, "(참고)" 수치): `--provider ollama` → **Recall@5 0.900, MRR 0.782**.
    `--provider fp16`은 **BLOCKED-on-GPU** — 실행 시점 nvidia-smi 여유 VRAM 2.4~2.6GB
    (fp16 로딩에 필요한 ~9GB 미달, 다른 Ollama 상주 모델이 13GB대 점유 중) — 직접
    unload/kill 금지 방침에 따라 스킵. Task 6의 파킹 사유와 동일한 GPU 제약이 반복 관측됨
  - `--provider gemini`는 이번 태스크에서 실행하지 않음(비용/쿼터 보존 — 사용자 지시)
- 테스트: `tests/test_rag_eval_harness.py` (recall_at_k·mrr 순수 함수 4케이스 —
  적중/미적중/부분적중/역순위)

## [v0.18.0] - 2026-09-07

### Added
- **convenience BC 신설** (`apps/convenience/`) — 편의점 분석 축 2단계: 현행 스냅샷 수집
  (brainstorming §3.5 "편의점 신규 출점 = 검증된 상권 프록시"). tobacco 전례대로 소비
  라우터가 아직 없어 entity+ORM+ports+interactor+gateway+repository+CLI 구성 (라우터 후속),
  스냅샷 수집 흐름은 broker 전례(포트·인터랙터·Fake 게이트웨이 테스트)를 따름
  - **원천**: 소진공 상가정보 sdsc2 `storeListInDong` × 행정동 427회/스냅샷
    (indsSclsCd=G20405 체인화 편의점, DATA_GO_KR_API_KEY — 일 한도 10,000회의 4.3%).
    실호출 검증: numOfRows=1000 1페이지 수신(최다 역삼1동 149건), WGS84 좌표 원값 제공,
    adongCd 8자리 = region_code 앞 8자리 — 427개 region 프리픽스 유일 DB 실측이라
    공간조인 폴백 없이 요청 행정동을 그대로 FK 기입
  - `convenience_store` 테이블 — ERD 15테이블 밖 **보조 테이블** (erd.md §2 노드·엣지 추가):
    PK=bizesId(상가업소번호), region FK 필수, 상호·지점명·브랜드(상호 기반 추출 역정규화 —
    §5 키워드 dict 디스패치, 미확인 None)·좌표·도로명/지번주소·기준연월(stdrYm).
    **store에 넣지 않는 근거**: 상가정보는 개폐업 시계열 불가(api.md §2-3) — store에 섞으면
    region_industry_metric 개폐업 지표가 오염된다. 개폐업 이력은 tobacco_retailer 담당
  - **관측 필드 `first_seen_on`/`last_seen_on`** — broker 전례의 스냅샷 소실 패턴:
    멱등 업서트가 first_seen(최초 관측)은 보존하고 last_seen만 전진 → 소실(last_seen 정지)
    = "폐점 추정 후보"를 후속 분석이 판정. broker와 달리 close_date 추정은 하지 않음
    (관측과 해석의 분리 — 원천이 개폐업 진실 소스가 아니므로)
  - 마이그레이션 `5a21ef1efab1` — `convenience_store` 테이블
    (+ ix_convenience_store_region_last_seen: 행정동×최근 관측 경쟁밀도 조회 축)
  - **첫 실적재: 9,395건 업서트** (API 427회 호출 — 계획과 정확히 일치, 실패 행정동 0):
    좌표·region_code 채움 100%, FK 고아 0, 행정동 427/427 전 커버, 기준연월 202606 단일.
    브랜드 분포: GS25 2,847(30.3%) · CU 2,643(28.1%) · 세븐일레븐 2,507(26.7%) ·
    기타 641(6.8%) · 이마트24 613(6.5%) · 미니스톱 144(1.5%).
    구별 상위: 강남 803 · 송파 583 · 강서 529 · 마포 511 · 영등포 502.
    행정동 상위: 역삼1동 149 · 가산동 135 · 서교동 119. psql 표본(역삼1동): GS25역삼대홍점·
    씨유역삼미래점 등 실명 확인. 기타 표본 재검으로 브랜드 사전 보강
    (지에스 '25' 생략 상호 → GS25, 비지에프(BGF리테일=CU 운영사) → CU, 101건 재산출 갱신)
  - `scripts/convenience-collector.sh` + 크론 등록 (매주 월 05:40) — **주 1회 근거**:
    원천이 기준연월(stdrYm) 단위로 갱신되는 느린 스냅샷(현재 202606)이라 일 단위 무의미,
    신규 출점 신호는 주 단위 해상도로 충분. 로그 `logs/convenience-collector.log`
  - 테스트 10건 — 게이트웨이 픽스처 파싱(실응답 사본·브랜드 추출 변형·좌표 결측·페이징·
    빈 행정동·오류 resultCode) + 실DB 멱등 업서트(first/last_seen 관측·소실 시 last_seen
    정지·재등장 시 first_seen 보존·배치 내 중복 제거)
    — 전체 135건 중 134 passed (기지 실패 1건: test_store_ingest 실DB 커서 테스트, 기존 상태 유지)

## [v0.17.0] - 2026-09-07

### Added
- **tobacco BC 신설** (`apps/tobacco/`) — 편의점 분석 축 1단계: 담배소매인 지정 현황 적재
  (brainstorming §3.5 — 담배소매인 지정이 사실상 편의점 출점 가능 여부를 결정하는 변수).
  지정일자·폐업/취소일자·상세영업상태가 있어 지정·폐지 시계열 분석 대상 → BC 신설,
  단 현 단계 소비처(라우터)가 없어 rent 전례대로 entity+ORM+CLI 최소 구성 (라우터 후속)
  - **원천 선택**: `data/raw/tobacco_retail/` 인허가 「기타_담배소매업」 서울 아카이브 CSV
    (2026-08-25 확보 불변 원본, 95,402행·24컬럼 실측 — API 호출 0회). 공공데이터포털
    표준데이터 CSV(매일 갱신)는 **좌표 부재**(api.md §2-4 실확인)라 배제 — 아카이브는
    좌표정보(X)(Y) 90.1%(영업중 97.3%) 포함 + 전 기간(1900s~2026) 개폐업 이력 보유
  - `tobacco_retailer` 테이블 — ERD 15테이블 밖 **보조 테이블** (erd.md §2 노드·엣지 추가):
    PK=관리번호(중복 0 실측), district FK 필수(개방자치단체코드↔opn_authority_code 25구 전수),
    region FK nullable(공간조인 후 채움 — store 전례), 상세영업상태 코드·명, 지정/인허가/폐업/
    취소일자, WGS84 좌표, 도로명·지번주소(좌표 결측분 지오코딩 대기열용), 데이터갱신시점.
    store에 합치지 않는 근거: 담배소매인은 점포가 아니라 **지정 권리** — industry FK 불성립
  - 적재 CLI `load_tobacco_retailer.py` — CP949 CSV 파싱, EPSG:5174→WGS84 변환+서울 범위
    검증·불량 날짜 월말 클램프(store 전례와 동일 로직), PK 멱등 업서트(region_code 보존),
    적재 직후 행정동 공간조인까지 일괄 수행. **store BC의 `RegionIndex`를 읽기 전용 재사용**
    (타 BC 무수정 — adapter 레이어 간 import, assign_regions 전례)
  - **첫 실적재: 95,402행 업서트** (자치구 미매칭 0) — 좌표 85,959건(90.1%, 서울 밖 이상좌표
    1건 폐기), region_code 85,948건 기입(좌표 보유분의 99.99%, 미판정 11건).
    상태 분포: 폐업 67,752 / 정상영업 15,615 / 지정취소 6,677 / 직권취소 5,240 / 기타 118.
    구별 영업중 상위: 강남 1,025 · 중구 885 · 강서 844 · 송파 808. 지정일자 채움 72,466(76.0%).
    psql 표본(강남): 지에스25역삼허브(2026-08-14 지정, 역삼1동) 등 편의점 실명 확인
  - **SGIS 지오코딩 대기열**: 영업중 좌표 결측 416건(2.7%) — 이 중 404건 지번주소 보유
    (api.md ⑨ 발급 트리거 ② 해당 여부는 소량이라 보류 판단 여지)
  - 테스트 6건 — CSV 실측 행 파싱(필드 매핑·WGS84 변환·서울 밖 좌표 폐기·공란 날짜/좌표·
    불량 날짜 클램프·미지 자치단체 스킵) + 실DB 멱등 업서트(상태 갱신·region_code 보존)
    — 전체 125건 중 124 passed (기지 실패 1건: test_store_ingest 실DB 커서 테스트, 기존 상태 유지)
  - **크론 비대상**: 원천이 정적 아카이브 파일(불변 원본) — 갱신은 파일 재확보 후 재실행(멱등).
    증분 갱신 후속 경로: 행안부 인허가 API 담배소매업 슬러그(DAT_UPDT_PNT 커서, store_collector 전례)
- **편의점 식별 경로 실확인** (구현 아님 — 조사 3호출): 소진공 상가정보 API(sdsc2)에서
  편의점 = `indsSclsCd G20405`(소매>종합 소매>편의점, KSIC G47122 체인화 편의점) 확정.
  응답에 WGS84 경위도·도로명주소 포함, `adongCd` 8자리 = region_code 앞 8자리로 매핑 가능
  (역삼1동 11680640 실확인). 반경 300m 표본 22건 — 후속: storeListInDong×행정동 427회/일
  스냅샷 수집으로 현재 경쟁밀도 축 구축(개폐업 시계열은 불가 — api.md §2-3, 담배소매인이 담당)

### Changed
- `migrations/env.py` — tobacco_retailer ORM 등록 (마이그레이션 a6376277270d)
- `docs/erd.md` — tobacco_retailer 노드·엣지(district 필수/region nullable) 및
  보조 테이블 추가 근거 명시 (§2 실구현 정정)

## [v0.16.0] - 2026-09-07

### Added
- **ECOS 121Y006 가중평균 대출금리 3계열 적재** — 계산기(§brainstorming 8.1③) 대출금리 추정 축.
  `interest_rate`에 base와 병행 적재 (id 프리픽스 규약 `{rate_type}:{YYYYMM}` 일관):
  - `loan_corp` = 기업대출(BECBLA02, 상위 벤치마크), `loan_sme` = 중소기업대출(BECBLA0202,
    소상공인 차주 근사), `loan_facility` = 시설자금대출(BECBLA0204, 상가 등 부동산 취득 최근접)
  - 신규취급액 기준·월별·2019-01~현재 — 실적재 273행(계열당 91행, 201901~202607)
  - 2022 급등 사이클 실측: 기업대출 3.30%(202201)→5.67%(202211) — 기대 패턴 일치
- `apps/shock/adapter/outbound/gateways/ecos_gateway.py` — `EcosSeries` VO로 시리즈 파라미터화,
  `EcosLoanRateGateway`(121Y006 3계열) 추가. 기존 `parse_rates`는 기본값(base)으로 하위호환
- `apps/shock/adapter/inbound/cli/load_loan_rate.py` — 적재 러너(Driving Adapter, 멱등 업서트 재사용)
- `tests/test_loan_rate_gateway.py` — 실응답 픽스처 파싱·id 규약·3계열 구성 검증 2건
- `scripts/interest-rate-collector.sh`에 loan rate collector 단계 추가 (주 1회 크론 — 월 공표라 충분)

### Changed
- **COFIX(은행연합회 소비자포털) 스크래핑 최종 포기 → 121Y006 대체 경위**: ECOS에 COFIX 부재
  전수 확인(docs/api.md) 후 은행연합회 `portal.kfb.or.kr/fingoods/cofix.php` 스크래핑을 구현했으나,
  `portal.kfb.or.kr/robots.txt`가 `User-agent: * / Disallow: /`(전 경로·전 UA 수집 금지)임을 확인.
  ※ curl 기본 UA에는 오류 안내 페이지(200)가 와서 "robots 부재"로 오인 소지 — 브라우저·봇·httpx UA
  교차 확인으로 전면 불허 확정. robots 존중 원칙에 따라 우회 없이 중단·전량 원복하고, api.md에
  기록된 1차 대안인 ECOS 121Y006(정식 API)으로 대출금리 축을 대체. 은행연합회 수집 허가 문의는
  사용자 판단으로 이관

## [v0.15.1] - 2026-09-07

### Changed
- **도커 백엔드 이미지 갱신** — 13일 전 구버전(v0.5 이전, metric/funding/shock 라우터 없음)으로 돌던
  `beyondfacade-api` 컨테이너를 v0.15.0(27b03b8) 코드로 재빌드·재기동 (`docker compose build backend` +
  `up -d --no-deps backend`, db/redis/neo4j는 미재시작). 코드·compose 변경 없음
- 갱신 후 실검증 (호스트 8200, 외부 API 키 없이 — 대상 엔드포인트 전부 DB·로컬 파일만 사용):
  - `GET /health` 200, `GET /metrics/myself` 200 (배선 검증)
  - `GET /metrics?industry=cafe&metric=closure_rate&year=2025` → 427행
  - `GET /funding?limit=3`, `GET /shocks?limit=3` → 실데이터 정상
  - `GET /regions/geojson` → 200, 5.4MB gzip 대상, FeatureCollection 427 features —
    **BoundaryFileReader `parents[6]` 경로 실검증**: 컨테이너 안에서 `/app/apps/...` 기준 `parents[6]` = `/`,
    geometry_ref(`data/geojson/regions/*.json`)가 compose의 `./data:/data` 마운트와 정확히 일치해 수정 불요.
    단, 이미지 내 코드 깊이가 달라지면(예: WORKDIR 변경) 깨질 수 있는 암묵 결합이므로 주의
- 기지 이슈(미수정, 기록만): docker-compose.yml frontend 매핑 `3200:3000`은 `next dev -p 3200`과 불일치
  (frontend 코드가 main에 없어 포스트MVP로 이연)

### Added
- `CLAUDE.md` Part V(프론트엔드 구조 규칙) 성문화 — §14 Feature-Sliced 구조(feature 간 import 금지),
  §15 Mock API 계약(`{error:{code,message}}`), §16 토큰 기반 스타일·다크모드(data-theme),
  §17 TanStack Query 관행, §18 MapLibre WebGL 브리징, §19 Vitest·TDD.
  `.worktrees/frontend-mvp/frontend` 실코드 관행 기반 (backend/docs·frontend/docs CLAUDE.md는 심볼릭 링크 — 자동 반영 확인)

## [v0.15.0] - 2026-09-07

### Added
- **rent BC 신설** (`apps/rent/`) — 월세vs매입 계산기(brainstorming §8.1③) 임대료·공실률 데이터 계층
  - **R-ONE 상업용부동산 임대동향조사 적재** — reb.or.kr `SttsApiTblData.do` (2026-09-07 실호출 검증:
    WRTTIME_IDTFR_ID(YYYYQQ)·CLS_ID·CLS_NM·CLS_FULLNM·DTA_VAL·UI_NM, 오류는 200+RESULT 바디 — ECOS 전례)
  - **지역 단위 실확인: 자치구가 아니라 상권/권역/시도** (CLS_FULLNM "서울>강남>테헤란로" 3계층)
    → erd.md 초안 정정: 원천 지역명 보존(cls_id/region_name/region_path/region_level),
    district_code FK **nullable**(의도된 미연결 — 상권·자치구 경계 불일치, 매핑 후속),
    초안의 sale_price_avg는 실거래가 후속 수집 시 추가로 유보 (실데이터 기반 원칙)
  - `rent_price` 테이블 — id=`{building_type}:{cls_id}:{period}` PK, 임대료(천원/㎡)·공실률(%)이
    별도 통계표로 오므로 **같은 PK 행에 지표별 컬럼 병합 업서트**(서로를 지우지 않음 — 멱등),
    rent_statbl_id/vacancy_statbl_id로 값별 원천 통계표(표본 빈티지) 추적. ORM+마이그레이션(13e7c1526fef)+
    적재 CLI(`load_rent_price.py`) — 라우터 후속(master 전례)
  - **통계표 매핑표 확정** (SttsApiTbl.do 전수 738개 조회) — 표본 기준연도(빈티지)별 분리 제공이라
    2019~최신 연결에 빈티지 5개(2019/2020/2021/2022~/2024Q3~) × 지표 2(임대료·공실률) × 상가 2(중대형·소규모)
    = **통계표 20개** (`rone_gateway.py` `_TABLES` 정본, docs/api.md ⑫에 표 기록). 시리즈별 옛→새 순서 적재로
    빈티지 경계 중복 시 새 표본 우선
  - **첫 실적재: R-ONE API 39회 호출(자체 키, 순차), 서울 관측 7,244행 → rent_price 3,638행**
    (임대료 3,622·공실률 3,622 병합, 편측 16+16) — 2019Q1~2026Q2 30개 분기, 관측 지역 88개
    (시도 1·권역 4·상권 계층, 중대형 1,754행·소규모 1,584행 상권 단위)
  - psql 표본: 테헤란로 중대형 임대료 47.7(2019Q1)→52.5천원/㎡(2026Q2), 광화문 중대형 공실률
    10.0(2019Q1)→18.1(2022Q1 코로나)→5.2%(2026Q2) — 계산기 임대료·공실 리스크 축 검증
- 테스트 6건 — R-ONE 파싱 4(실응답 픽스처 필드 매핑·결정적 ID·서울 필터·지역 계층/오류 바디/결측 방어/
  분기 표기 변환) + rent_price 병합 업서트 2(임대료·공실률 같은 행 병합·district NULL/멱등·최신값 갱신)
  — 전체 117건 중 116 passed (기지 실패 1건: test_store_ingest 실DB 커서 테스트, 기존 상태 유지)

### Changed
- `core/matrix/grid_keymaker_secret_manager.py` — `rone_api_key` 추가 (.env `RONE_API_KEY` 기발급)
- `migrations/env.py` — rent_price ORM 등록
- `scripts/interest-rate-collector.sh` — 기준금리 뒤에 rent_price 수집 단계 추가 (주 1회 크론 통합 —
  분기 공표 데이터라 별도 스크립트 불요, store-collector 다단계 전례)
- `docs/erd.md` — rent_price·interest_rate를 실구현 컬럼으로 정정 + 실구현 정정 절 신설:
  interest_rate 초안의 bank_tier/credit_band/avg_rate는 은행연합회 공시 대출금리 축(은행군×신용등급 격자)
  → 후속 수집 시 **별도 테이블(예: loan_rate)로 유보** 명시 (ECOS 시계열과 축이 달라 혼합 금지)
- `docs/api.md` ⑫ — R-ONE 적재 구현 확정 사항(실필드·지역 단위·빈티지 매핑표 20개·표본 개편 불연속 주의) 기록

### Removed
- (계획 변경) **ECOS COFIX 적재 보류** — ECOS 오픈 API 전체 통계표 839개 전수 + 금리 관련 표
  (722Y001/817Y002/721Y001/121Y002·006·013·015) 항목 전수 + 100대 통계지표 확인 결과 **코픽스/COFIX 부재 실확인**
  (2026-09-07, ECOS 조회 8회). COFIX(신규취급액 기준) 원천은 은행연합회 소비자포털 공시 → 은행연합회
  후속 수집 범위로 이동 (임의 대체 적재 금지 원칙). 계산기 금리 보정 축은 당분간 기준금리(`base:{YYYYMM}`)만

## [v0.14.0] - 2026-09-07

### Added
- **shock BC 신설** (`apps/shock/`) — 특이변수(외생 충격) 데이터 계층 (brainstorming §5.2 4계층 분류, ERD shock_event 계열)
  - `shock_event` Fractal 11-File Set — 계층은 `ShockLayer` StrEnum(policy/macro/trend/regional, if 분기 금지),
    영향도는 `Severity` StrEnum(critical/high/medium/low). 엔티티 불변식: 출처(source) 없는 충격 등록 거부,
    layer·severity 값 검증, 종료일<시행일 거부. 라우터는 `GET /shocks/myself`(§12 배선 검증) +
    `GET /shocks?industry=&limit=`(시행일 오름차순 타임라인, 업종 영향 동봉) 최소 구성
  - `shock_event_industry` M:N (event_id+industry_id PK, FK 강제, severity) — 업서트 시 영향 행 교체(멱등),
    `shock_event_region` M:N (④지역 이벤트용 자리 — MVP 빈 테이블, 뉴스 기반 감지 후속)
  - `ShockEventSourcePort` 1개에 소스 어댑터 2종 — 거리두기 API·시드 파일이 같은 계약으로 들어온다 (OCP)
- **코로나 거리두기 이력 적재** — data.go.kr **15098772**(ODMS_COVID_12, 2026-09-07 실호출 검증:
  2020-12-08~2021-10-31 일별 328건 결측 없음, 실필드 stdDay·seoLvl·socdisLvl·시도별 Lvl/Rmk)
  - `CovidDistancingGateway` — 1회 호출 전량 수신(호출 수 로그), 서울(seoLvl) 동일 단계 연속 구간 압축 →
    shock_event 3건(2.5단계 2020-12-08~/2단계 2021-02-15~/4단계 2021-07-08~2021-10-31), 결정적 event_id로 재적재 멱등.
    severity 밴드 상수(§5.2 노래방·PC방·헬스장·당구장 ≫ 카페): 2.5+↑ critical/high, 2단계 high/medium
  - `load_distancing.py` CLI — 과거 이력 1회성, 크론 불요
- **①계층 정책 충격 시드** — `shock_events_seed.json`(시드 파일, 전 행 출처 명시) + `seed_shock_events.py` CLI, 23건
  - API 미커버 거리두기 보충: 1차 거리두기~수도권 2단계(2020-03-22~2020-12-07 공백 없는 연속 8구간,
    질병관리청·중대본 보도자료 기준) + 위드코로나(2021-11-01)·재강화(2021-12-18~2022-04-17) — covid 계열 총 13건 연속 커버
  - 최저임금 연도별 고시 2019~2026 (시급 8,350→10,320원, 실제 금액·인상률·1/1 시행) — 편의점 high·카페 medium
  - 주 52시간제 단계 시행 3건 (2018-07-01 300인↑/2020-01-01 50~299인/2021-07-01 5~49인) — 노래방·당구장 medium
  - 1차 긴급재난지원금(2020-05-04)·소상공인 손실보상제(2021-10-27) — 전 업종 연결, **지원금 폐업 '지연' 왜곡
    주의(§5.2 ⚠️)를 description에 명시**해 후속 분석이 참조
- **②거시 — 한국은행 기준금리 적재** — ECOS StatisticSearch 722Y001(월)/0101000 (2026-09-07 실호출 검증:
  TIME·DATA_VALUE·UNIT_NAME, 2019-01~2026-08 92행)
  - `interest_rate` 독립 시계열 (계산기·부동산 분석 공용 — erd.md §4 역정규화 근거. 컬럼은 실데이터 기반 확정:
    id=`{rate_type}:{period}` PK, rate_type="base", period YYYYMM, rate, unit, stat_code, item_code —
    가중평균 대출금리 121Y006 확장 대비). ORM+CLI(`load_interest_rate.py`), 라우터 후속
  - 실적재: 92행, 변경점 20건 — 1.75%(2019-01)→0.5%(2020-05 저점)→3.5%(2023-01 고점)→2.5%(2025-05)→3.0%(2026-08)
    사이클 확인. ECOS 오류(200+RESULT 바디)는 RuntimeError 변환
- `scripts/interest-rate-collector.sh` — 주 1회(월 05:20) 크론 러너 (기존 수집기 관행)
- 테스트 17건 — 거리두기 파싱 4(실응답 픽스처 구간 압축/결정적 ID·출처/severity 매핑/빈 입력)
  + 시드 5(출처·계층·업종 무결성/API 이전 구간 연속 커버/최저임금 실값/왜곡 경고) + ingest 3(업서트 멱등/영향 행 교체/업종 필터)
  + myself 2 + ECOS 파싱 3(실필드/오류 바디/비수치 방어) + interest_rate 업서트 1
  — 전체 111건 중 110 passed (기지 실패 1건: test_store_ingest 실DB 커서 테스트, 기존 상태 유지)
- 실적재 검증(psql): shock_event 26건(policy 26 — ②거시는 interest_rate 테이블 담당), 업종 연결 105건,
  covid 계열 13건 2020-03-22~2022-04-17 공백 0일, shock_event_region 0건(설계 의도), 재실행 신규 0/갱신 0(멱등)

### Changed
- `main.py` — shock_router 등록, `migrations/env.py` — shock ORM 4종 등록 (마이그레이션 2bd709bb5837)
- `core/matrix/grid_keymaker_secret_manager.py` — `ecos_api_key` 추가 (.env `ECOS_API_KEY`)

## [v0.13.0] - 2026-09-07

### Added
- **부동산중개업(real_estate) 수집** — 브이월드 NED `getEBOfficeInfo` (data.go.kr 15123990 LINK 실체) → store
  - 원천 확정 경위: 시드된 15123990은 LINK형 → 실체는 브이월드 NED API (인증: `VWORLD_API_KEY`+domain,
    data.go.kr 쿼터 미사용). 속성 응답에 **좌표·폐업일 없음 실확인** — 브이월드 일간 파일(부동산중개업공간정보 SHP,
    좌표 포함)은 다운로드가 로그인 세션 필수(비로그인 200+0바이트 실측)라 기각, SGIS 지오코딩은 키 미발급으로 보류
  - `MolitBrokerGateway` (Driven Adapter) — ldCode=district_code(시군구 5자리) 순차 페이징(1회 1,000행 실측 허용),
    재시도(지수 백오프)·YYYY-MM-DD 방어 파싱(월말 클램프, MOIS 전례). 상태 무필터 조회가 전 상태 포함
    (강남 2,990 = 영업중 2,972+휴업 16+업무정지 2 실측). **lat/lng NULL 적재 — SGIS 지오코딩 후속 대상(학원과 동일 대기열)**
  - store 매핑 (실응답 기반): jurirno+ldCode→store_id(`real_estate:{구코드}:{등록번호}`, 자치구 내 유일 실확인),
    bsnmCmpnm→name, registDe→open_date, sttusSeCode→status(dict 디스패치: 1→open, 2→suspended,
    미지 코드는 원문 보존 — 실적재에서 휴업연장·업무정지 관측), lastUpdtDt→source_updated_at
  - **폐업은 스냅샷 소실 기반 추정(관측일 기록)** — 원천이 폐업분 미제공(sttusSeCode=3 조회 totalCount 0 실확인).
    업서트 후 DB에 있으나 이번 스냅샷에 없는 점포를 close_date=관측일, `closed_estimated`/"폐업(추정)"으로 기록.
    최초 적재일은 비교 기준이 없어 발동 금지(테스트 검증). **과거 폐업 이력 없음 — 개폐업 시계열은 적재 시작일(2026-09-07)부터**
  - 재수집 업서트의 위치 이월(`_carry_location`) — 후속 지오코딩·공간조인이 채울 lat/lng/region_code를
    일일 전량 재수집이 지우지 않도록 기존 값을 엔티티에 이월 (테스트 검증)
  - `BrokerSnapshotInteractor`(+ input/output port — `BrokerGatewayPort`·`StoreSnapshotRepositoryPort` ISP 분리),
    저장소에 `active_store_ids`/`existing_locations`/`mark_closed` 추가
  - `broker_collector.py` (Driving Adapter, CLI) — source_system→게이트웨이 **팩토리 레지스트리**(§5, 분기 없이 등록으로 확장).
    **첫 실적재: 25개 구 25,317건 전량(영업중 25,237·휴업 58·업무정지 17·휴업연장 5), API 35회 호출, 폐업 추정 0건(최초)**
- 테스트 12건 — 게이트웨이 7건(필드 매핑/상태 dict 디스패치·미지 코드 보존/날짜 클램프/페이징 종료/오류 페이로드)
  + ingest 5건(최초 적재 폐업 추정 금지/소실 폐업 추정/재등장 복원·기폐업 재추정 금지/지오코딩 결과 보존/레지스트리)
  — 전체 94건 중 93 passed (기지 실패 1건: test_store_ingest 실DB 커서 테스트, 기존 상태 유지)

### Changed
- `scripts/store-collector.sh` — academy_collector 뒤에 broker_collector 단계 추가 (일 배치 동일 크론)
- 좌표 부재로 real_estate는 assign_regions·build_metrics 대상 제외 (SGIS 지오코딩 후 합류 — region_code NULL 상태,
  region_industry_metric의 real_estate 지표는 지오코딩 후속 완료 시 생성)

## [v0.12.0] - 2026-09-07

### Added
- **학원(academy) 수집** — 서울 열린데이터광장 OA-20528(`neisAcademyInfo`) → store + 신규 **academy_course** 테이블 (store 1:N)
  - `SeoulAcademyGateway` (Driven Adapter) — 1회 1,000건 페이징(초과 시 ERROR-336 실확인), 재시도(지수 백오프)·
    YYYYMMDD 방어 파싱(월말 클램프, MOIS 전례). **원천에 좌표 없음 → lat/lng NULL 적재, SGIS 지오코딩 후속 대상**
    (부동산과 동일 대기열). 갱신시점 필터 없음(현행 스냅샷만) → 매 실행 전량 재수집(업서트 멱등), `LOAD_DT`→source_updated_at
  - store 매핑 (실응답 기반): PEI_DSGN_NO→store_id(`academy:seoul:{번호}`, 서울 전역 유일 실확인), PEI_NM→name,
    ADMDST_NM↔district.name→district_code(공란 40행은 도로명주소 2번째 어절로 복구 — 전량 매칭),
    ESTBL_YMD→open_date, REG_STTS_NM→status(dict 디스패치: 개원→open 등, 폐원일 필드 없어 close_date는 NULL)
  - 교습계열(FLD_NM)→subcategory_id dict 디스패치 (§3.6 5축): 입시.검정 및 보습→exam, 예능(대)·기예(대)→arts,
    국제화→language, 직업기술·정보→vocational, 독서실→studyroom — 종합(대)·기타(대)·인문사회(대)는 5축 밖이라 미매핑(NULL)
  - academy_course: 수강료 공개 항목(INDV_ATNLC_AMT_CN `항목명:금액`) 우선, 없으면 교습과정명(TRNG_CRS_LIST_NM)
    — **course_name 원문 보존 = 대상학년 LLM 추출 원천 (추출은 후속 범위, target_grade는 현재 NULL)**.
    재적재 멱등: 점포 단위 delete+insert (`replace_for_stores`)
  - `AcademyCourseInteractor`(+ input/output port·entity·dto·orm·orm_mapper·repository) — store 업서트 후 course 재적재(FK 순서)
  - `academy_collector.py` (Driving Adapter, CLI) — **첫 실적재: 점포 25,514건(전량), 교습과정 64,203건, API 26회 호출**
    (일 1,000회 한도 대비 2.6%). 상태 분포: 개원 100%(원천이 현행 등록분만 제공 — 개폐업 시계열은 주기 스냅샷으로 축적),
    서브카테고리 매핑 24,003건(94.1%), 수강료 보유 41,332건(평균 222,954원·중위 180,000원)
- 마이그레이션 `5e26dfc27428` — `academy_course` 테이블 (store FK, store_id 인덱스)
- 테스트 11건 — 게이트웨이 파싱 9건(YYYYMMDD 클램프/수강료 항목/과정 폴백/서브카테고리·상태 매핑/구 공란 주소 복구/
  구 미매칭 스킵 보고) + ingest 2건(store+course 적재 / 재수집 시 course 잔재 없는 교체 멱등)
  — 전체 82건 중 81 passed (기지 실패 1건: test_store_ingest 실DB 커서 테스트, 기존 상태 유지)
- `Settings`에 `seoul_open_data_api_key` 필드 추가 (.env 기존 키 사용)

### Changed
- `scripts/store-collector.sh` — store_collector 뒤에 academy_collector 단계 추가 (일 배치 동일 크론)
- `docs/erd.md` academy_course 실컬럼 기반 정정 — course_id(`store_id:연번`)·course_name(수강료 항목명 또는
  교습과정명, 원문 보존)·tuition_fee nullable(공개 항목만)·target_grade(LLM 추출 후속, 현재 NULL)
- 좌표 부재로 academy는 assign_regions·build_metrics 대상 제외 (지오코딩 후 합류 — region_code NULL 상태)

## [v0.11.0] - 2026-09-07

### Added
- **population_stat 테이블** — 주민등록 인구 (행정동×연월×성별×5세 연령구간, 학원·어린이집 수요 변수 + 배후인구 축)
  - 원천: 기존 아카이브 `data/raw/jumin/연령별*.csv` 재사용 (행안부 연령별 인구현황, 신규 다운로드 없음)
  - 실컬럼 기반 정정 (docs/erd.md): wide 208컬럼(`{YYYY년MM월}_{계|남|여}_{연령구간}`) → long 변환,
    PK(region_code, period, gender, age_from) — 계·총인구수·연령구간인구수는 남/여 합산 도출값이라 미저장(3NF),
    초안의 pop_type(상주/생활/직장/외국인)·nationality는 주민등록 원천에 없어 제거 (생활인구 등은 별도 테이블로 후속)
  - `population_stat_orm.py` + 마이그레이션 `945d0433e675` (region FK, period 인덱스)
  - `load_population.py` (Driving Adapter, CLI) — 서울 행정동 필터(행정기관코드 10자리 파싱, seed_master 전례)
    + PK 기준 `ON CONFLICT DO UPDATE` 멱등 업서트, region 미매칭(폐지동) 스킵·건수 보고
  - **첫 적재: 142,632건** — 2019~2025 각년 12월 + 2026-06(최신월) 8개 연월
    (커버리지 201912 421/427 → 202512·202606 427/427, 미매칭 스킵은 분동 전 폐지동: 용신동 등 최대 3동)
  - 표본 검증: 역삼1동 2026-06 연령 21구간 남녀 분포(합 34,262)·학령인구 5~19세 1,562명, 서울 합계 9,289,813명
- 테스트 4건 — 헤더 파싱(대상 연월·남녀·연령구간 선별) / 행 필터(시총계·자치구·타시도 제외, 폐지동 스킵 보고,
  천단위 콤마) / 분기 파일 탐색 / 실적재 멱등·427 전체 커버·실 CSV 교차검증(역삼1동 남 0~4세 211)
  — 전체 71건 중 70 passed (기지 실패 1건: test_store_ingest 실DB 커서 테스트, 기존 상태 유지)

## [v0.10.0] - 2026-09-07

### Added
- **funding BC 신설** (`apps/funding/`) — funding_program Fractal 11-File Set (정책자금 공고 수집, 기업마당 bizinfo)
  - `BizinfoGateway` (Driven Adapter) — `bizinfo.go.kr/uss/rss/bizinfoApi.do` JSON, `searchCnt=3000`
    **1회 호출 전량 수신** (~1,500건 상시, 페이징 불필요). 원천 ID(`pblancId`)·원문 링크 없는 항목 제외
  - 실응답 컬럼 매핑 (샘플 3건 실확인, docs/erd.md funding_program 실컬럼 기반 정정):
    pblancId→program_id(PK), pblancNm→title, jrsdInsttNm→org, excInsttNm→exec_org,
    pldirSportRealmLclasCodeNm/MlsfcCodeNm→field_category/subcategory, trgetNm→target_text,
    hashtags→hashtags(**원문 보존 — LLM 구조화 추출 원천, 추출은 후속 작업**),
    reqstBeginEndDe→apply_period(원문)+apply_begin/deadline(방어적 파싱 — "예산 소진시"·"상시" 등 비일자는 None),
    bsnsSumryCn→summary(태그 제거 1,000자 발췌 — 본문 전문 저장 금지), pblancUrl→url(UK, 원문 링크 필수)
  - 업서트 멱등: program_id 기준, 원천 갱신시점(`updtPnttm`) 변경분만 갱신 — 마감 연장(변경 공고) 반영
  - 만료 처리: `refresh_expirations` — `deadline < today → is_expired=True`, 연장·상시 전환 시 복원 (일 배치)
  - `GET /funding/myself`(배선 검증) + `GET /funding?limit=` — 미만료만 마감 임박순(마감일 오름차순, 상시는 뒤),
    limit 1~100 위반 시 400 `INVALID_LIMIT` — 에러 바디 단일 형식 `{error:{code,message}}`
  - `funding_collector.py` (CLI) — 전량 수집·업서트+만료 갱신. **첫 적재: 1,499건**
    (마감일 파싱 594건 / 상시·예산소진 등 비일자 905건 — 원문 전수 검증, 만료 0건: API가 접수중 공고만 제공)
- 마이그레이션 `a66c8cd01cd2` — `funding_program` 테이블 (url UK, (is_expired, deadline) 조회 인덱스)
- `scripts/funding-collector.sh` — 일 1회 크론(05:10) 등록, 로그 `logs/funding-collector.log`
- `Settings`에 `bizinfo_api_key` 추가 (`BIZINFO_API_KEY`)
- 테스트 11건 — 게이트웨이 파싱 픽스처 4(실응답 표본 매핑·ID/URL 부재 제외·기간 방어 파싱·요약 발췌) /
  ingest 업서트 멱등·배치 내 dedup 1 / 만료 판정 2(엔티티 규칙·배치 만료/복원/상시) /
  목록 3(임박순·만료 제외·limit·400 바디) / myself 배선 1 — 전체 66 passed
  (기지 실패 1건: test_store_ingest 실DB 커서 테스트, 기존 상태 유지)

### Changed
- `main.py`에 funding 라우터 등록
- `migrations/env.py` autogenerate 대상에 funding_program ORM 등록
- `docs/erd.md` funding_program — 문서 스펙 추정 컬럼(limit_amount·rate_info·region_scope)을
  실응답 컬럼 기반으로 정정 (LLM 추출 컬럼은 후속 작업에서 M:N과 함께 재도입)

## [v0.9.0] - 2026-09-07

### Added
- **metric BC 신설** (`apps/metric/`) — region_industry_metric Fractal 11-File Set
  - `GET /metrics/myself`(배선 검증) + `GET /metrics?industry=&metric=&year=` → `[{region_code, value}]`
    단계구분도 프론트엔드 계약 (value None 행 제외, metric은 Strategy 테이블 디스패치)
  - 미지원 metric 404 `METRIC_NOT_FOUND` / 미등록 industry 404 `INDUSTRY_NOT_FOUND` —
    에러 바디 단일 형식 `{error:{code,message}}`
  - `build_metrics.py` (CLI) — store 원천(region_code 보유분)만 읽어 행정동×업종×연도(2019~2026)
    지표 업서트, 재실행 멱등. **첫 적재: 20,152건** (427개 행정동 × 수집 업종 6종 × 8개년)
    - store_count: 연도 말(12-31) 기준 영업 중 / open·close_count: 당해 개폐업
    - closure_rate·growth_rate: 전년 말 store_count 분모 (전년 0이면 None 가드)
  - `StoreStatsGateway`·`IndustryCatalogGateway` (Driven Adapter) — cross-BC 접근은 어댑터 레이어에서만
- 마이그레이션 `b0aeecac90e6` — `region_industry_metric` 테이블 (복합 PK region_code+industry_id+year,
  region·industry FK, 업종×연도 조회 인덱스)
- store BC — `GET /stores?region=&industry=` 영업 중(close_date 없음)·좌표 보유 점포 마커 목록
  `[{store_id, name, lat, lng, status_name, open_date}]`, 미등록 industry 404 `INDUSTRY_NOT_FOUND`
- master BC — `GET /regions/{region_code}/summary?industry=` 사이드패널 fact 카드 3장
  (점포수 "N개" / 폐업률 "X.X%" / 성장률 "±X.X%") — 최신 연도(2026) metric 기준,
  집계 없으면 value="데이터 없음", 미등록 region_code 404 `REGION_NOT_FOUND`
  - `RegionMetricSummaryPort` + `MetricSummaryGateway` — metric BC UseCase 호출 (cross-BC는 어댑터에서만)
- 테스트 24건 추가 — metric 13(빌드 계산·전년 0 가드·멱등·조회·404 바디·myself) /
  store 4(목록·404) / master summary 8(카드 포맷·데이터 없음·404) — 전체 55 passed
  (기지 실패 1건: test_store_ingest 실DB 커서 테스트, 기존 상태 유지)

### Changed
- `main.py`에 metric 라우터 등록
- `scripts/store-collector.sh` 일일 크론에 assign_regions 후속으로 build_metrics 추가
- `migrations/env.py` autogenerate 대상에 region_industry_metric ORM 등록

## [v0.8.0] - 2026-09-07

### Added
- **region Fractal 11-File Set** (`apps/master/`) — master BC 최초 라우터. `GET /regions/myself`(배선 검증) + `GET /regions/geojson`
  - `/regions/geojson` — 서울 행정동 427개 경계 FeatureCollection. `properties = {region_code, name}` 프론트엔드 계약 충족
    (name은 경계 파일 properties가 `adm_nm`/`emd_kor_nm`로 혼재하므로 DB `region.name` 조인으로 통일)
  - 좌표 소수 5자리 절삭(≈1.1m) — 응답 8.1MB → 5.4MB, gzip 시 849KB. 원본 파일은 원 정밀도 유지(공간조인용)
  - `CachingRegionUseCaseProxy` (GoF Proxy) — FeatureCollection 프로세스 수명 캐시 (경계는 반기 갱신 데이터)
  - `BoundaryFileReader` (Driven Adapter) — `geometry_ref` repo root 상대경로 판독
- `tests/test_master_region_myself.py` — 배선 검증 1건
- `tests/test_master_region_geojson.py` — FeatureCollection 조립·DB name 조인·geometry_ref 부재 제외·좌표 절삭·Proxy 캐시 4건

### Changed
- `main.py` — region 라우터 마운트, CORS 미들웨어(프론트 3200 오리진), GZip 미들웨어(1KB 이상 응답 압축)

## [v0.7.0] - 2026-08-26

### Added
- store 행정동 공간조인 — `region_code` **282,752/282,764 기입** (좌표 보유분의 99.996%, 8초)
  - `assign_regions.py` (CLI) — `RegionIndex`: 경계 GeoJSON(v0.6.0) 427개 shapely `STRtree`
    포함(within) 일괄 판정 + 경계 틈·변환 오차 스냅(최근접 ≤0.0005°≈50m)
  - PostGIS 부재(pgvector 이미지)에 따른 앱사이드 조인 — 명시적 인프라 정합 판단
  - 멱등: 기본 `region_code IS NULL`만 판정, `--full`로 전체 재판정(경계 갱신 시)
  - 미판정 12건: 좌표가 서울 경계 밖(수원·성남·부천 등 원천 좌표 이상) — NULL 유지가 정답
  - 교차검증: 판정 행정동의 구 vs 인허가 관할구 불일치 28건(0.01%) — 경계 인접·원천 좌표 오류,
    실좌표 기준 판정 유지
  - 테스트 4건: 포함 판정 / 허용 오차 스냅 / 원거리 None / 일괄=단건 일치 (전체 28 passed)
- `scripts/store-collector.sh` 일일 크론에 공간조인 후속 실행 추가 (신규 수집분 자동 채움)
- `requirements.txt`: shapely==2.1.2 추가

## [v0.6.0] - 2026-08-26

### Added
- 행정동 경계 적재 — 브이월드 WFS `lt_c_cademd`(기준일 2024-06-30) 서울 426동 1회 수신
  - `VworldBoundaryGateway` (Driven Adapter) — WFS 행정동 + 데이터 API `LT_C_ADEMD_INFO`(법정동)
    - **인증 확정 (실호출 진단)**: 데이터·WFS API는 `domain` 파라미터가 인증키 등록 서비스URL
      (`beyondfacade.cloud`)과 일치해야 통과 — 불일치 시 `INCORRECT_KEY` (타일·검색 API는 무관)
  - `load_boundaries.py` (CLI) — adm_cd(통계청 8자리)↔region_code(행안부 10자리) 코드 체계 불일치를
    (구, 정규화 동명) 매칭으로 해소: 서수 '제' 제거(창신제1동→창신1동, 동명 '홍제N동'의 '제'는 보존),
    중복 동명(신사동 등)은 유일 동명에서 학습한 통계청 구코드로 해소. 중복 배정 시 실패(ValueError)
  - **용두동·신설동 보충**: 경계 기준일 이후 분동(구 용신동)이라 행정동 레이어에 없음 —
    법정동 경계(11230102·11230101)로 1:1 대체 (분동 후 행정동 경계 = 법정동 경계)
  - 산출: `data/geojson/regions/{region_code}.json` (provenance: adm_cd·base_date·source_layer 보존)
    → `region.geometry_ref` **427/427 전체 기입** (멱등 재실행 검증)
  - 검증: 좌표 전수 서울 범위(126.5~127.4, 37.3~37.8) 내, 지오메트리 MultiPolygon 확인
- 테스트 7건: 정규화 2(DB/WFS 비대칭 '제' 규칙) / 매칭 4(유일·중복해소·미매칭·중복배정 거부) / 파일 왕복 1
- `Settings`에 `vworld_api_key`·`vworld_service_domain` 추가

## [v0.5.1] - 2026-08-25

### Fixed
- store 초기적재 중단 원인 3종 방어 (원천 불량 날짜 실존 — 예: 2006-02-29)
  - 날짜 클램핑(월말 초과 일자 보정), 요청 재시도(백오프), (업종×자치구) 타깃별 에러 격리
- store_id 기준 업서트로 재수집 시 중복 없이 복구 — 전체 재적재 297,079건 / 실패 0 최종 검증

## [v0.5.0] - 2026-08-25

### Added
- `apps/store` BC — 인허가 점포 Fractal 11-File Set (P0 개폐업 시계열)
  - `GET /stores/myself` 배선 검증, ingest UseCase(업종×자치구 단위 증분 수집·업서트)
  - `MoisPermitGateway` — 행안부 인허가 API 페이징 순회, **EPSG:5174→WGS84 좌표 변환**
    (브이월드 실좌표와 3m 이내 교차검증으로 좌표계 확정), 서울 범위 밖 좌표는 결측 처리
  - `SqlAlchemyStoreRepository` — store_id(관리번호) 기준 업서트 + 증분 커서(`latest_source_updated_at`)
  - `store_collector.py` (CLI) — 대상 자동 구성: industry_source_code(mois_permit) × district
- 마이그레이션 `43367fbe8af0` — `store` 테이블(FK 4종 + 증분 인덱스), `district.opn_authority_code`(UNIQUE)
- **개방자치단체코드 25개 구 전수 확보** (실호출 교차확인: 3000000 종로구 ~ 3240000 강동구) → district 시드 갱신
- 시범 수집 검증: 종로구 당구장 619건 (폐업 473 포함 — 이력 전체), 좌표 채움 90%
- **전체 초기적재 실행** (6업종 × 25구, 백그라운드) + `scripts/store-collector.sh` 일일 증분 크론(매일 04:20)
- 테스트 3건: myself 배선 / 업서트(신규+상태변경 갱신) / 증분 커서
- `requirements.txt`: pyproj==3.7.2 추가, `Settings`에 `data_go_kr_api_key` 추가

### Changed
- `main.py`에 store 라우터 등록
- `docs/erd.md` store 실데이터 기반 정정 — name·district_code·status_code/name·source_updated_at 추가,
  region_code nullable(공간조인 후 채움), 좌표 EPSG:5174 변환 명시

## [v0.4.0] - 2026-08-25

### Added
- `apps/news` BC — **첫 완전한 Fractal 11-File Set** (router·use_case·interactor·input/output port·repository·schema·dto·orm·entity·mapper·orm_mapper 전부 구현)
  - `GET /news/myself` 배선 검증 엔드포인트 (§12 규칙 — 하드코딩 왕복으로 DI 검증)
  - ingest UseCase: 키워드별 뉴스 수집 → article_id(sha1(url)) 기준 배치 내·실행 간 중복 제거 적재
  - `NaverNewsGateway` (Driven Adapter) — NAVER API HUB 뉴스 검색, HTML 태그 제거·RFC822 일시 파싱
  - `news_poller.py` (Driving Adapter, CLI) — 기본 키워드 = district 마스터 25개 구 × "상권"
- 마이그레이션 `45043069cde6` — `news_article` 테이블 (url UNIQUE, region_code FK nullable)
- `scripts/news-poller.sh` + 크론 등록 (매시 10분) — 로그 `logs/news-poller.log`
- **첫 실수집 완료: 기사 1,838건 적재** (2026-08-25 16:22, 뉴스 시계열 축적 시작점)
- 테스트 2건: myself 배선(TestClient) / ingest 중복제거·멱등(Fake 게이트웨이 + 실 DB)
- `Settings`에 `naver_ncp_api_key_id`/`naver_ncp_api_key` 필드 추가

### Changed
- `main.py`에 news 라우터 등록
- `docs/erd.md` news_article 실데이터 기반 정정 — description 추가·press nullable·published_at datetime·url UNIQUE, event_id는 shock_event BC 생성 시 컬럼+FK 동시 추가로 유보

## [v0.3.0] - 2026-08-25

### Added
- Alembic 마이그레이션 체계 — `alembic.ini` + `migrations/` (env.py가 전역 Secret 매니저에서 URL을, `OrmBase.metadata`에서 autogenerate 대상을 가져옴)
- `apps/master` BC (dummy 템플릿 복사 1호) — 마스터 계층 5테이블 ORM: `district_orm`, `region_orm`, `industry_orm`, `industry_source_code_orm`, `industry_subcategory_orm`
- 마이그레이션 `9af965caa6ab` 적용 — 마스터 5테이블 생성 (FK 제약 포함)
- `apps/master/adapter/inbound/cli/seed_master.py` — 시드 러너(Driving Adapter, 멱등 merge)
  - district 25·region 427: 주민등록 인구세대 CSV의 행정기관코드 파싱 (실데이터 기반)
  - industry 10종(수요동인 4유형), 원천코드 매핑 9건(확정분만), 서브카테고리 8건(교습계열 5+미용세분 3)
- `tests/test_master_seed.py` — 시드 멱등성·건수·FK 고아 0건·수요동인 4유형 검증 3건

## [v0.2.0] - 2026-08-25

### Added
- `core/matrix/grid_keymaker_secret_manager.py` — 전역 Secret 매니저 (pydantic-settings, OS 환경변수 > backend/.env 우선순위, `get_settings()` 캐시 싱글턴)
- `core/matrix/grid_oracle_database_manager.py` — 전역 DB 매니저 (SQLAlchemy engine/session 싱글턴, 공용 `OrmBase`, FastAPI Depends용 `get_session` + 배치용 `session_scope`)
- `tests/test_core_matrix.py` — core 매니저 TDD 검증 4건 (설정 로딩·싱글턴·실 DB SELECT 1·pgvector 확장 존재)
- `requirements.txt` 추가: dependency-injector(DI 컨테이너), pytest, httpx

### Changed
- `apps/dummy` 골격을 CLAUDE.md §12 정본 구조로 정정 — `app/use_case`→`use_cases`, `app/ports`에 `input/`·`output/` 분리, `adapter/outbound/mappers`→`orm_mappers`, `orm`→`orms`, `repositories`·`adapter/inbound/mappers` 신설

## [v0.1.0] - 2026-08-24

### Added
- `backend/Dockerfile` — python:3.14-slim 기반 uvicorn 실행 이미지
- `backend/.dockerignore` — .venv, __pycache__, .env, docs 제외
- `backend/requirements.txt` — fastapi, uvicorn, sqlalchemy, psycopg, alembic, pydantic-settings
- `backend/main.py` — 최소 FastAPI 앱 + `GET /health` (컨테이너 기동 검증용)
- 루트 `docker-compose.yml` — 프로젝트명 `beyondfacade`, 서비스: db(pgvector/pgvector:pg17), neo4j(5-community), redis(7-alpine), backend, frontend(프로필), cloudflared(프로필)
  - 컨테이너 이름 `beyondfacade-*` 접두사 — 동일 호스트의 foodopsagent·lifetutorial 프로젝트와 격리
  - 호스트 포트: DB 5434, Neo4j 7475/7688, Redis 6380, API 8200 (기존 프로젝트 점유 포트 회피, 127.0.0.1 바인딩)
  - `./data` 바인드 마운트(/data) — 원본 CSV 아카이브 적재용, .gitignore 등록
- pgvector 확장 활성화 확인 (vector 0.8.5)
