# Backend Version Log

## [v0.19.0] - 2026-09-15

### Added
- `apps/rag/adapter/outbound/repositories/rag_repository.py` — `SqlAlchemyRagRepository`
  (`RagRepositoryPort` 구현): `upsert_chunks`(merge 업서트), `existing_ids`, `search`(pgvector
  코사인 거리 정렬, score = 1 - cosine_distance)
  - 만료 공고 필터(`exclude_expired_funding`): `apps.funding`의 `FundingProgramOrm`을 이 파일에만
    한정해 import(플랜 승인 사항, cross-BC). `outerjoin` 조건에 `source_type == "funding"`을 넣고
    `where(or_(source_type != "funding", is_expired == False))`로 구성해, non-funding 청크가
    outer join NULL 때문에 통째로 드롭되는 사고를 방지
- `tests/test_rag_repository.py` — 실 DB 기반 6건(축 벡터 코사인 정렬·기본 필터 non-funding 보존·
  source_type 필터·만료 funding 제외·existing_ids·업서트 갱신)

### Fixed
- `apps/rag/adapter/outbound/orms/rag_chunk_orm.py` — FK 대상 `region` 테이블 ORM을 명시 import하지
  않아 단독 실행 시 `NoReferencedTableError` 발생하던 문제 수정 (store_orm.py와 동일한 기존 관행 적용)

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
