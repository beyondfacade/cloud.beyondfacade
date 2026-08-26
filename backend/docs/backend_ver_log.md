# Backend Version Log

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
