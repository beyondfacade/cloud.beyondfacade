---
layout: post
title: 개발 일지
permalink: /docs/devlog.html
date: 2026-10-08
categories: devlog
---

# 개발 일지

> 프로젝트: 상권 데이터 구조화 및 창업 분석 Hybrid RAG용 Agent 개발 (Metabole)
> 팀: Beyond Facade — 김충식 · 이은상 · 신채연

## 2026-08-24

### 1. 개발 환경 구축

- Claude Code 프로젝트 스킬 설치: obra/superpowers v6.3.0 스킬 14종 → `.claude/skills/`
  (brainstorming, TDD, systematic-debugging, writing-plans 등)
- 백엔드 가상환경 생성: `backend/.venv` (Python 3.14.6, uv)
- `.gitignore` 3곳 정비: 루트(`.env`, `.venv/`) / `backend/`(`.venv/`, `.env`) / `frontend/`(`.env`, `.env.local`)
  — `git check-ignore`로 시크릿 파일 무시 검증 완료

### 2. 기준 문서 작성 — `docs/brainstorming.md`

개발 제안서(개발 기간 2026-08-20 ~ 10-08, 7주)를 기반으로 초기 개발의 기준 문서를 작성하고
브레인스토밍을 통해 아래 사항을 확정.

#### 확정 사항

- **지역 범위: 서울 한정** — 추정매출·생활인구가 완결된 공공데이터는 서울시 상권분석서비스가 유일.
  코어 지표(전국 공통 데이터 기반)와 확장 지표(서울 전용)를 코드 레벨에서 분리해 추후 확장 대비
- **타겟 업종: 10종 확정** — 수요 동인 유형 축으로 설계
  - 일상소비형: 카페, 편의점, 미용실
  - 여가형: 노래방, PC방, 헬스장, 당구장
  - 경기민감형: 부동산(공인중개사무소)
  - 인구구조 민감형: 학원, 어린이집
- **학원 서브카테고리**: "학원 1업종 × 2축(교습계열 × 대상학년)" 모델.
  교습계열은 서울시 학원·교습소 데이터(NEIS 원천) 원본 필드, 대상 학년은 교습과정명 LLM 구조화 추출

#### 공공데이터 소스 확정 (API 제공 여부 검증 완료)

- 상권 코어: 소진공 상가정보, 행안부 LOCALDATA 인허가(개폐업), 서울시 상권분석서비스,
  서울 생활인구, 국토부 실거래가
- 정책자금 공고 (API 검증): 기업마당(중앙+지자체 통합, 1순위), K-Startup, 중소벤처24,
  보조금24, 온통청년 — 5곳 API 확인 / 소진공·지역신보·서울시는 스크래핑 후보
- 뉴스: 빅카인즈(한국언론진흥재단), 네이버 뉴스 API — 특이변수 감지 센서
- 인구: 행안부 주민등록(연령별), 외국인주민 현황(국적별)

#### 분석 변수 체계

- **전통 변수 8종**: 유동인구, 배후인구, 경쟁밀도, 개폐업률·생존율, 임대료·공실률, 접근성, 추정매출, 집객시설
- **특이변수 4계층 프레임**: ①정책·규제(거리두기, 최저임금, 주52시간 등) ②거시경제(금리, 물가, 에너지 요금)
  ③사회·트렌드(무인점포, 홈트, 유행 사이클 — 뉴스 언급량이 센서) ④지역 이벤트(GTX 개통, 재개발, 대형시설 개폐점)
- 재난지원금의 폐업 지연 왜곡(종료 후 폐업 절벽) 보정 원칙 수립
- 외국인 거주 인구는 "상권 악화 지표"가 아닌 **"수요 구성 변화 지표"**로 모델링
  (업종 타겟과 인구 구성의 정합성 점수화, 차별적 출력 금지 규칙 명시)

#### 서비스 설계

- **브이월드 지도 시각화**: 배경지도(WMTS)+행정동 경계(WFS)+지오코딩은 브이월드,
  성장률·폐업률 지표는 LOCALDATA 기반 자체 산출 → 단계구분도 + 업종 토글 + 시계열 슬라이더(2019~)
- **금융 연계**:
  - 정책자금 공고 요약 카드 + 원문 링크 (신청·중개 없음 — 금소법 경계 준수)
  - 월세 vs 매입 대출 계산기: 신용도 자가 입력 × 1군/2군 은행 평균 공시금리(은행연합회),
    실거래가 기반 매입가 추정, 취득세 등 부대비용 포함 손익분기 — 예상 계산까지만
- **업종 간 교차 시그널** (post-MVP 후보): 어린이집 폐원→학원 수요 선행지표,
  편의점 출점→검증된 상권 프록시, 여가형 3종(PC방·노래방·당구장)→세대별 수요 프로파일

#### MVP 일정 (7주)

| 주차 | 내용 |
|---|---|
| 1~2주 | 공공데이터 API 검증, 업종코드 매핑표(10종), ERD 설계 |
| 3~4주 | 수집 파이프라인 + Fractal 11-File Set 구현 |
| 5주 | 전통 변수 산출 + 상권×업종 분석 |
| 6주 | 특이변수 통합, Hybrid RAG Chunking |
| 7주 | 평가(Recall@5 목표 91.5%), 데모 배포 |

### 3. ERD 초안 설계 — `docs/erd.md`

- **3계층 접근**: 마스터(region·district·industry 허브) → 원천(3NF 엄격 적용) → 집계(역정규화 허용 구역)
- **MVP 15개 테이블** Mermaid erDiagram으로 작성 (M:N 매핑 3개 포함) — 테이블 1개 = Fractal 11-File Set 1개
- 1NF→3NF 정규화 검증 기록, 역정규화 4건은 근거 명시 (예: `region_industry_metric` 사전 집계 — 지도 latency)
- 모든 테이블이 마스터 허브까지 FK 경로 보유 — 고립 테이블·고아 레코드 원천 차단 (FK는 실제 DB 제약으로 강제)

### 4. API 수급 계획 검증 — `docs/api.md`

**27개 데이터 소스 웹 실사** (실제 페이지·엔드포인트·인증 체계 확인) 후 수급 방식 확정.

#### 설계에 영향을 주는 치명적 발견 5가지

1. 서울시 추정매출 공식 경로는 **2021년 이후만 잔존** → 코로나 회복 판정 지표를 매출 → 개폐업률·점포수(LOCALDATA)로 변경
2. 서울 생활인구 행정동 기반 생산 **2026-07-31 종료** → 격자(250m) 기반 + 격자→행정동 매핑으로 설계
3. 상가정보 API는 현재 스냅샷 전용(점포 단위 시계열 연계 불가) → LOCALDATA가 개폐업 시계열의 유일한 진실 소스
4. 브이월드 지오코더 **결과 저장 금지 약관** → 좌표 포함 원천 우선, 소량만 SGIS 지오코딩
5. 상가 임대 실거래 API 부재 → 부동산원 R-ONE 임대동향(지역 평균)으로 대체

- 발급 계정·인증키 **11곳 체크리스트** 작성 (승인 대기 4곳 우선 신청 원칙) — ECOS는 샘플 키로 실호출 검증 완료
- 스크래핑·수기 확정: 은행연합회 금리, 거리두기 2020.2~11 이력 등

### 5. Docker 인프라 구축 — Backend v0.1.0 / Frontend v0.1.0

- 루트 `docker-compose.yml` (프로젝트명 `beyondfacade`): db(pgvector/pgvector:pg17), neo4j(5-community), redis(7-alpine), backend, frontend·cloudflared(프로필)
- 호스트 포트: DB 5434, Neo4j 7475/7688, Redis 6380, API 8200, 프론트 3200 — 동일 호스트 타 프로젝트와 격리, 127.0.0.1 바인딩
- `backend/Dockerfile`(python:3.14-slim + uvicorn), 최소 FastAPI 앱 `GET /health`로 스택 기동 검증, pgvector 0.8.5 확장 활성화 확인
- `frontend/Dockerfile`(node:22-alpine, 로컬 개발용 — 배포는 Vercel)
- PostgreSQL·Neo4j에 강력 랜덤 자격증명 적용, `backend/.env` 템플릿에 외부 API 키 플레이스홀더 11개 정리 (git 커밋 금지 검증 완료)

### 6. 데이터 확보 — 서울 상권 추정매출 2017~2021

- GitHub 미러에서 **연간 CSV 5개(2017~2021) 전량 확보** → `data/raw/seoul_sales/` (공식 경로에서 삭제된 2017~2020 포함)
- `MANIFEST.md`에 출처·라이선스(KOGL 1유형, 출처표시)·SHA256 무결성 기록
- 주 지표는 개폐업률·점포수 유지, 매출은 교차검증·RAG 보조 근거로 활용

### 7. 개발 일지 자동화

- `scripts/jekyll-devlog.sh` 작성 + 크론 등록(매일 23:55) — 일일 개발 내용을 이 문서의 일자별 섹션으로 자동 집계
- `docs/jekyll.md`를 단일 포스트에서 일자별 섹션(`## 날짜`) 반복 구조로 개편, permalink `/docs/devlog.html` 고정

### 다음 작업

- [x] ERD 초안 설계 (테이블 = Fractal 11-File Set 단위) — `docs/erd.md` 15개 테이블
- [x] 공공데이터포털 API 키 발급 (상가정보·인허가·기업마당 등) — 8/25 완료
- [x] 브이월드 API 키 발급 + 데모 도메인 등록 — 8/25 완료
- [ ] 10종 업종코드-데이터소스 매핑표 확정 → `industry_source_code` 시드 데이터
- [ ] `docs/api.md` §7 열린 질문 팀 결정 (회복 판정 지표 변경 승인 등)
- [ ] 자동 일지 크론 첫 실행 확인 후 `scripts/jekyll-devlog.sh` 커밋

## 2026-08-25

### 1. [데이터 수급] API 수급 계획 재검증 — 4건 정정 (`docs/api.md`)

웹 실사 재검증으로 8/24 계획 대비 변경 4건 확정:

1. **LOCALDATA(지방행정인허가) 서비스 종료 확인** — localdata.go.kr은 2026-04-16 0시부로 폐쇄,
   공공데이터포털로 일원화 (인허가 195종 + 생활편의 14종 = 209종, 인허가 이력 데이터 신규 제공).
   별도 회원가입·인증키 절차 소멸 → data.go.kr 키 하나로 커버
2. **빅카인즈 완전 유료 전환 확정** (2025~) → MVP 뉴스 수집은 네이버 폴링 단독으로 확정 (열린 질문 §7-3 해소)
3. **K-Startup API 수급 불가 확정** — 구 API 폐기 공지 + 후속 조회서비스 포털 미노출 (신청 경로 없음)
   → 공고 수집은 기업마당 API로 일원화, 공백 시에만 k-startup.go.kr 크롤링 검토
4. **별도 발급처 2곳 식별** — R-ONE은 reb.or.kr/r-one 자체 키(data.go.kr 아님),
   어린이집은 어린이집정보공개포털(info.childcare.go.kr) 자체 키(개발계정 승인제, 일 1,000회)

### 2. [데이터 수급] API 키 발급 완료 + 전건 실호출 검증

**발급 완료 8곳 (전부 실호출 검증 통과):**

| 발급처 | 검증 내용 |
|---|---|
| 브이월드 | 활용API 선택 가이드 후 발급 (지오코더·2D데이터·검색·타일 등) |
| 서울 열린데이터광장 | 일반 인증키 (실시간 지하철 키 불필요 확인) |
| 기업마당 | 공고 JSON 실수신 (등록 IP 호출 조건 동시 확인) |
| 한국은행 ECOS | 발급 키로 기준금리 재검증 (2026-08 기준 2.75%) |
| KOSIS | 발급 완료 |
| 부동산원 R-ONE | 통계표 목록 + 임대가격지수 실데이터 수신 (임대 관련 통계표 265개, 2013Q1~ 상권 단위) |
| 공공데이터포털 | 활용신청 12건 완료 — 실거래가(강남구 2026-06)·상가정보(반경조회)·인허가 실수신 |
| 온통청년 | 청년정책API 승인 완료 — 정책 2,728건 수신 (신형 `getPlcy` 엔드포인트 확인) |

- **승인 대기 1곳**: 어린이집정보공개포털 (개발계정 신청 완료)
- **잔여 1곳**: 네이버 개발자센터 — 뉴스 시계열이 등록일부터 쌓이므로 최우선 전달 (백엔드 담당 가이드 작성)
- **SGIS는 폴백으로 우선순위 하향** — 담배·인허가 데이터 좌표 포함 확인으로 지오코딩 수요 축소,
  브이월드 WFS 문제 시 또는 좌표 결측 유의미할 때 발급 (즉시 발급이라 리드타임 리스크 없음)

### 3. [데이터 수급] 신규 인허가 API 스펙 완전 확보 (P0 핵심 수확)

구 LOCALDATA의 후속 API 구조를 실호출로 해명 — ERD 설계의 실데이터 근거 확보:

- 엔드포인트: `apis.data.go.kr/1741000/{업종슬러그}/{info|history}` — 업종별 개별 데이터셋 구조
- 우리 7개 업종 슬러그 전수 추출: `general_restaurants`(일반음식점) / `rest_cafes`(휴게음식점) /
  `beauty_salons` / `fitness_centers` / `billiard_halls` / `karaoke_rooms` / `pc_bangs`
- **`/history` = 특정 일자 기준 상태 조회** (`cond[BASE_DATE::EQ]`) — 개폐업 시계열 구축의 핵심
- 증분 수집: `cond[DAT_UPDT_PNT::GTE]`(데이터갱신시점), 자치구 단위: `cond[OPN_ATMY_GRP_CD::EQ]`
- 실응답 컬럼 확인: 인허가일자·폐업일자·영업상태·주소·**좌표(CRD_INFO_X/Y)** — 페이지당 최대 100행(페이징 필요)
- 부동산중개업은 행안부 통합 목록에 없음 → 국토부 중개업정보(15123990) 대체 검토

### 4. [데이터 확보] 주민등록 인구 + 담배소매업 적재 (`data/raw/`)

- **주민등록 인구** (`data/raw/jumin/` + MANIFEST): 연령별(5세 단위) 38파일 2017.01~2026.06 +
  인구세대 10파일 2017.01~2026.07 — 무결성 검증에서 깨진 파일 1개·연령 단위 불일치 5개 발견 → 재다운로드로 전량 정상화.
  MVP 조회기간 2017.01~ 확정 (생활인구·매출 시계열 정합 + 코로나 전 3년 기준선)
- **담배소매업** (`data/raw/tobacco_retail/` + MANIFEST): 서울 95,402행, 폐업 포함 전 기간.
  **좌표 포함 확인 (영업중 기준 97.3% 채움)** → 당초 "좌표 없음, 지오코딩 필요" 판단 정정 — 지오코딩 불필요
- 다운로드 제약 실측 기록: 인구세대 최대 1년 / 연령별 최대 3개월 범위

### 5. [아키텍처] 멀티에이전트 + AWS 인프라 설계 확정 (`docs/agent-architecture.md` 신규)

- **에이전트 구성**: 오케스트레이터 + 전문가 3 (상권 진단 / 충격·정책 분석 / 정책자금·금융) —
  업종별이 아니라 **분석 축별** 분할 (brainstorming §5.3 이원 축 = 에이전트 경계)
- **원칙**: 숫자는 배치 산출(결정론), 에이전트는 검색·판단·합성만 / **Port = Tool**
  (Fractal 11-File Set의 UseCase가 곧 에이전트 도구 — 헥사고날의 런타임 연장)
- 응답 규칙(외국인 변수·지원금 왜곡·금융 규제·신뢰 등급)은 오케스트레이터 한 곳에 집중
- **구축 순서**: 도구 완성(~4주) → 단일 에이전트(5주) → 멀티 분리(6주) — Port 기반이라 분리는 리팩토링
- **AWS $400 크레딧 운용 확정**: 9월 하순까지 로컬 개발 → 종료 2주 전 EC2 배포(모델 병렬 서빙).
  2주 예산 ~$300 (스팟 GPU 2대 + CPU 1대 + S3), 발표 당일만 온디맨드 전환.
  즉시 액션: **G 인스턴스 쿼터 증설 신청** / 9월 중 스모크 배포 1회 (<$5)

### 6. [문서화] 운영 가이드·기록 정비

- SGIS·네이버 개발자센터 발급 절차 상세 가이드 작성 (백엔드 담당자 전달용 — 인증 구조·쿼터·폴링 설계 포함)
- `backend/.env` 정비: 폐기 항목 제거(LOCALDATA·빅카인즈), 신규 추가(R-ONE·어린이집)
- `docs/api.md` 전면 갱신: 발급 현황 체크리스트, 데이터셋 ID 전수 확인표, 정정 이력

### 7. [백엔드] core 인프라 + master/news/store BC 구현 — Backend v0.2.0~v0.5.1

모듈러 모놀리스 골격 위에 첫 Bounded Context 3개를 Fractal 11-File Set으로 구현 (테스트 17건, 커밋 5a971f4):

- **v0.2.0 — core/matrix 전역 인프라**: Secret 매니저(pydantic-settings, 환경변수 > `.env` 우선순위)
  + DB 매니저(SQLAlchemy engine/session 싱글턴, 공용 `OrmBase`) — TDD 4건(실 DB SELECT 1·pgvector 확장 확인 포함).
  `apps/dummy` 골격을 CLAUDE.md §12 정본 구조로 정정
- **v0.3.0 — Alembic + master BC**: 마이그레이션 체계 도입, 마스터 계층 5테이블 생성.
  시드 러너(멱등 merge)로 자치구 25 · 행정동 427(주민등록 CSV 실데이터 파싱) · 업종 10종 · 원천코드 매핑 9건 · 서브카테고리 8건 적재
- **v0.4.0 — news BC (첫 완전한 11-File Set)**: `GET /news/myself` 배선 검증 → `NaverNewsGateway`(네이버 API HUB) →
  sha1(url) 기준 중복 제거 적재. 폴러 CLI + 크론(매시 10분) 가동 — **첫 실수집 기사 1,838건** (뉴스 시계열 축적 시작점, 8/24 최우선 과제 해소)
- **v0.5.0 — store BC (P0 개폐업 시계열)**: `MoisPermitGateway` 행안부 인허가 API 페이징 순회 +
  **EPSG:5174→WGS84 좌표 변환**(브이월드 실좌표와 3m 이내 교차검증), 관리번호 기준 업서트 + 증분 커서.
  개방자치단체코드 25개 구 전수 확보, 시범 수집 종로구 당구장 619건(폐업 473 포함, 좌표 채움 90%) 후 전체 초기적재(6업종 × 25구) 실행
- **v0.5.1 — 수집기 내결함성**: 초기적재 검증 중 원천의 비정상 일자(월말 초과)로 수집 중단되는 결함 발견 →
  날짜 클램프 + 재시도 + 대상(업종×자치구)별 오류 격리로 보강, 업종:자치구:관리번호 조합키로 전량 재수집 가동(5.5만+ 건 적재 확인)

### 8. [프론트엔드] MVP 설계 스펙 + SDD Task 1~8 구현 — Frontend v0.2.0~v0.6.1

- **설계 스펙 확정**: `docs/superpowers/specs/2026-08-25-frontend-design.md` (§1~§5 승인) —
  2탭 구조(지도 탐색 + AI 분석), mock API 계약 우선 개발, 전체 11개 Task 계획
- **SDD(subagent-driven-development) 워크플로로 Task 1~8 완료**: 태스크마다 TDD Red→Green + 독립 서브에이전트 리뷰 게이트 통과.
  워크트리 `feature/frontend-mvp` 브랜치, 커밋 10개, **테스트 19건 전부 통과** + 프로덕션 빌드 검증
- **v0.2.0**: Next.js 16 스캐폴드(TypeScript, App Router, Tailwind) + vitest + `shared/config`
- **v0.2.x~v0.3.x**: 시맨틱 디자인 토큰 2벌 + 테마 토글 / **지도 탭** — MapLibre + 브이월드 라이트·다크 래스터 타일,
  행정동 단계구분도(색약 안전 5스톱 보간), 선택 강조 + 클릭 핸들링. v0.3.1에서 테마 전환 시 강조색 미갱신 버그·하드코딩 hex 제거
- **v0.4.0~v0.5.0**: URL ↔ 상태 양방향 동기화(업종/지표/연도 컨트롤바) / 사이드패널(region summary 쿼리, 404 분기) +
  신뢰 배지(`fact`/`signal`) + `/analysis` 딥링크
- **v0.6.0~v0.6.1**: **AI 분석 탭** — SSE `EventSource` 구독 → 순수 리듀서로 에이전트 4행 진행 패널 + 마크다운 리포트(섹션 순서 고정, 계산기 표 렌더).
  리뷰 게이트에서 잡힌 `start()` 재진입 `EventSource` 누수·POST 실패 미처리 수정(재진입 가드 테스트 추가)
- 잔여: Task 9~11 (탭 네비게이션 + E2E 검증, 정책자금·배포, 점포 마커 클러스터링) → 브랜치 최종 리뷰 후 병합 예정

### 9. [툴링] 디자인 스킬 6종 설치 + 수집 자동화 크론 3종

- Claude Code 프론트엔드 디자인 스킬 6종 설치(악성 지시·유출 패턴 검수 후): frontend-design(Anthropic), impeccable(+전용 에이전트 4종),
  taste, ui-ux-pro-max, agent-browser, find-skills(Vercel)
- 크론 스크립트 3종 커밋: `news-poller.sh`(매시 10분) · `store-collector.sh`(매일 04:20 증분) · `jekyll-devlog.sh`(매일 23:55 일지 집계)
- GitHub 원격 푸시 정상화 — PAT 자격증명 영구 저장 구성 후 금일 커밋 3건(백엔드·문서·툴링) 푸시 완료

### 다음 작업

- [x] **네이버 개발자센터 앱 등록 + 뉴스 폴링 수집기 가동** — news BC + 매시 크론으로 완료 (기사 1,838건 적재 시작)
- [x] 인허가 초기 적재 파이프라인 — store BC로 완료 (6업종 × 25구, 부동산중개업은 국토부 대체 검토 지속)
- [x] ERD 실응답 컬럼 기준 검증·갱신 — news_article·store 정정 완료 (잔여 테이블은 BC 구현 시점에 갱신)
- [ ] **AWS G 인스턴스 쿼터 증설 신청** (승인 며칠 소요 — 지금 신청)
- [ ] 어린이집정보공개포털 승인 후 키 입력 (`CHILDCARE_API_KEY`)
- [ ] 연령별 인구 2026.07분 1파일 추가 (공표 확인 후)
- [ ] store 전량 재수집 완료 검증 (건수·좌표 채움률·업종별 분포 확인)
- [x] 프론트엔드 Task 9~11 구현 → `feature/frontend-mvp` 최종 리뷰 — 8/26 완료 (v0.9.1, 병합은 결정 대기)

## 2026-08-26

### 1. [백엔드] 행정동 경계 적재 — Backend v0.6.0

- 브이월드 WFS `lt_c_cademd`(기준일 2024-06-30) 서울 426동 1회 수신 →
  `region.geometry_ref` **427/427 전체 기입** (멱등 재실행 검증)
- **브이월드 인증 확정 (실호출 진단)**: 데이터·WFS API는 `domain` 파라미터가 인증키 등록
  서비스URL(`beyondfacade.cloud`)과 일치해야 통과 — 불일치 시 `INCORRECT_KEY` (타일·검색 API는 무관)
- `VworldBoundaryGateway` (Driven Adapter) + `load_boundaries.py` (CLI) —
  adm_cd(통계청 8자리)↔region_code(행안부 10자리) 코드 체계 불일치를 (구, 정규화 동명) 매칭으로 해소:
  서수 '제' 제거(창신제1동→창신1동, 동명 '홍제N동'의 '제'는 보존), 중복 동명은 유일 동명에서 학습한
  통계청 구코드로 해소, 중복 배정 시 실패(ValueError)
- **용두동·신설동 보충**: 경계 기준일 이후 분동(구 용신동)이라 행정동 레이어에 없음 →
  데이터 API `LT_C_ADEMD_INFO` 법정동 경계로 1:1 대체
- 산출: `data/geojson/regions/{region_code}.json` (adm_cd·base_date·source_layer provenance 보존),
  좌표 전수 서울 범위 검증 — 테스트 7건 (정규화 2 / 매칭 4 / 파일 왕복 1)

### 2. [백엔드] store 행정동 공간조인 — Backend v0.7.0

- `region_code` **282,752/282,764 기입 (좌표 보유분의 99.996%, 8초)** — `RegionIndex`:
  v0.6.0 경계 GeoJSON 427개 shapely `STRtree` 포함 판정 + 경계 틈·변환 오차 스냅(최근접 ≤0.0005°≈50m)
- PostGIS 부재(pgvector 이미지)에 따른 앱사이드 조인 — 명시적 인프라 정합 판단.
  멱등: 기본 `region_code IS NULL`만 판정, `--full`로 전체 재판정(경계 갱신 시)
- 미판정 12건은 좌표가 서울 경계 밖(수원·성남·부천 등 원천 좌표 이상) — NULL 유지가 정답.
  교차검증: 판정 행정동의 구 vs 인허가 관할구 불일치 28건(0.01%)은 경계 인접·원천 좌표 오류로 판정 유지
- `scripts/store-collector.sh` 일일 크론에 공간조인 후속 실행 추가 — 신규 수집분 자동 채움
- 테스트 4건 추가 (백엔드 전체 28 passed) — 이로써 **점포 297k행 전량이 행정동 축으로 집계 가능**
  (다음 단계 `region_industry_metric` 집계 BC의 선행 조건 충족)

### 3. [프론트엔드] MVP Task 9~11 완료 + 최종 리뷰 클린 — Frontend v0.7.0~v0.9.1 (`feature/frontend-mvp`)

- **v0.7.0 — 탭 네비게이션 + E2E 인프라**: `<TopBar>`(지도 탐색/AI 분석 탭, `aria-current`),
  agent-browser 기반 E2E 여정 스크립트(`e2e-journey.sh`) + 화면×테마×뷰포트 16종 스크린샷 매트릭스
- **v0.7.1~v0.7.2 — 지도 렌더링 버그 근본 해결**: maplibre-gl@6.6.0이 워커 스크립트 URL을
  `import.meta.url` 기반으로 계산하는데 Turbopack 청크에서는 실패해 GeoJSON 타일링이 조용히 멈춰
  폴리곤이 전혀 렌더되지 않던 문제 → `setWorkerUrl()` + `public/maplibre-gl/` 워커 파일 배치로 우회.
  E2E 폴리곤 클릭을 엄격 모드로 복원(XFAIL 우회 제거), 브라우저 프로세스 누수 trap 정리
- **v0.8.0 — 디자인 시스템 확정**: 강조색 **market-teal** 확정(신뢰·데이터 계열 후보 3종 스크린샷 비교 —
  라이트 `#0f766e`/다크 `#2dd4bf`, 단계구분도 팔레트와 색상환 비겹침 근거), 컨트롤바·사이드패널·분석 탭
  전반 한국어 라벨·접근성(role/aria-live/색상 단독 전달 금지)·스켈레톤·빈 상태 정비,
  **포트 규약 3500→3200 정정**(루트 docker-compose와 일치), 지도 뷰포트 높이(dvh)·`--border` 토큰 버그 수정
- **v0.9.0 — 점포 마커 클러스터링 (Task 11)**: backend store 실데이터(297k행)에서 8개 동 × 6개 업종
  bounding box로 추출한 표본 기반 mock `GET /stores` 라우트 + MapLibre 클러스터 3레이어
  (클러스터 클릭 확대·개별 마커 팝업·테마 토큰 연동), 동 미선택 시 로드 금지 성능 가드
- **v0.9.1 — 최종 브랜치 리뷰 결함 수정**: 업종을 바꿔도 지도 색상·요약 카드 수치가 그대로였던
  mock 결함(`metricRows`에 `industry` 시드 미반영) 수정 → 최종 리뷰 클린
- **테스트 32건 전부 통과** + 프로덕션 빌드 검증 — 브랜치 미머지 보존 (병합/PR은 결정 대기)

### 다음 작업

- [ ] `feature/frontend-mvp` 병합/PR 결정 (v0.9.1 리뷰 클린 상태로 보존 중)
- [ ] `region_industry_metric` 집계 BC 구현 — 실데이터 컬럼 기반, 프론트 실 API 전환(컷오버)의 선행 조건
- [ ] 백엔드 컷오버 체크리스트 필수 4건 반영 후 mock → 실 API 전환
- [ ] AWS G 인스턴스 쿼터 증설 신청 (8/25 이월)
- [ ] 어린이집정보공개포털 승인 후 키 입력 (`CHILDCARE_API_KEY`, 8/25 이월)
- [ ] 연령별 인구 2026.07분 1파일 추가 (공표 확인 후, 8/25 이월)

## 2026-09-07

### 1. [백엔드] 조회 API 계층 완성 — Backend v0.8.0~v0.9.0 (컷오버 선행 조건)

- **v0.8.0 — region 11-File Set** (master BC 최초 라우터): `GET /regions/geojson` 서울 행정동
  427개 경계 FeatureCollection 서빙. 좌표 소수 5자리 절삭(≈1.1m)으로 8.1MB→5.4MB(gzip 849KB),
  `CachingRegionUseCaseProxy`(GoF Proxy) 프로세스 수명 캐시. CORS(프론트 3200)·GZip 미들웨어 추가
- **v0.9.0 — metric BC 신설**: `region_industry_metric` 집계 — store 원천에서 행정동×업종×연도(2019~2026)
  지표 **첫 적재 20,152건** (427동 × 6업종 × 8개년, store_count·open/close_count·closure_rate·growth_rate).
  단계구분도 계약 `GET /metrics`, 점포 마커 `GET /stores`, 사이드패널 fact 카드 3장
  `GET /regions/{code}/summary` — 에러 바디 `{error:{code,message}}` 단일 형식, 미지원 값은 404

### 2. [백엔드] funding BC 신설 — Backend v0.10.0

- 기업마당(bizinfo) 정책자금 공고 수집 — 1회 호출 전량 수신(~1,500건 상시), **첫 적재 1,499건**
- `updtPnttm` 변경분만 갱신하는 멱등 업서트 + 일 배치 만료 처리(`deadline < today`, 연장·상시 복원),
  hashtags·target_text는 **원문 보존 = LLM 구조화 추출 원천** (추출은 후속)
- `GET /funding?limit=` 미만료 마감 임박순 + 일 1회 크론(05:10) 등록

### 3. [백엔드] 수요·공급 데이터 적재 확장 — Backend v0.11.0~v0.13.0

- **v0.11.0 — population_stat**: 주민등록 인구(행정동×연월×성별×5세 구간) wide 208컬럼 → long 변환,
  **첫 적재 142,632건** (2019~2025 각년 12월 + 2026-06, 최신월 427/427 전체 커버, 서울 합계 9,289,813명)
- **v0.12.0 — 학원(academy) 수집**: 서울 열린데이터광장 OA-20528 → store **25,514건** +
  신규 `academy_course` **64,203건** (수강료 보유 41,332건, 평균 222,954원). 교습계열→5축
  서브카테고리 dict 디스패치 94.1% 매핑, 교습과정명 원문 보존(대상학년 LLM 추출 원천)
- **v0.13.0 — 부동산중개업(real_estate) 수집**: 브이월드 NED API → store **25개 구 25,317건 전량**
  (영업중 25,237). 원천이 폐업분 미제공이라 **스냅샷 소실 기반 폐업 추정** 도입(최초 적재일 발동 금지
  테스트 검증) — 개폐업 시계열은 적재 시작일(2026-09-07)부터 축적
- 학원·부동산은 원천 좌표 부재로 lat/lng NULL 적재 — SGIS 지오코딩 후속 대기열 (지표 집계는 지오코딩 후 합류)

### 4. [백엔드] shock BC 신설 — 특이변수 데이터 계층 (Backend v0.14.0)

- `shock_event` 11-File Set — 4계층 `ShockLayer` StrEnum(policy/macro/trend/regional) +
  `shock_event_industry` M:N, `GET /shocks` 타임라인 라우터
- **코로나 거리두기 이력**: ODMS_COVID_12 API(일별 328건) 구간 압축 + 시드 23건(1차 거리두기~재강화
  보충, 최저임금 2019~2026 시급 8,350→10,320원, 주 52시간제 3단계, 재난지원금·손실보상) —
  **covid 계열 13건 2020-03-22~2022-04-17 공백 0일** 연속 커버, 지원금 폐업 '지연' 왜곡 주의를 description에 명시
- **한국은행 기준금리**: ECOS 722Y001 월별 92행 적재 — 1.75%(2019-01)→0.5%(2020-05 저점)→
  3.5%(2023-01 고점)→3.0%(2026-08) 사이클 확인. `interest_rate` 독립 시계열 + 주 1회 크론

### 5. [백엔드] rent BC + 대출금리 — 계산기 데이터 축 (Backend v0.15.0~v0.16.0)

- **v0.15.0 — rent BC 신설**: R-ONE 상업용부동산 임대동향조사 적재. 지역 단위가 자치구가 아니라
  **상권/권역/시도 계층 실확인**(ERD 정정 — district FK nullable). 표본 빈티지 5개 × 지표 2 × 상가 2 =
  통계표 20개 매핑 확정(738개 전수 조회, api.md ⑫ 기록), **첫 적재: 서울 관측 7,244행 → rent_price
  3,638행** (2019Q1~2026Q2 30개 분기, 임대료·공실률 같은 행 병합 업서트). 표본: 광화문 중대형 공실률
  10.0→18.1(2022Q1 코로나)→5.2%(2026Q2)
- **v0.16.0 — 가중평균 대출금리 3계열**: ECOS COFIX 부재 전수 확인 후 은행연합회 스크래핑을
  구현했으나 robots.txt 전면 불허 확인 → **우회 없이 전량 원복**, 정식 API인 ECOS 121Y006
  (기업/중소기업/시설자금 대출) 3계열 273행으로 대체 — 2022 급등 사이클(3.30→5.67%) 실측 일치

### 6. [백엔드] 편의점 분석 축 2단계 완성 — Backend v0.17.0~v0.18.0

- **v0.17.0 — tobacco BC 신설**: 담배소매인 지정 현황(사실상 편의점 출점 가능 여부 결정 변수) —
  인허가 아카이브 CSV **95,402행 적재** (좌표 90.1%, 행정동 공간조인 99.99%, 전 기간 개폐업 이력 보유).
  담배소매인은 점포가 아니라 **지정 권리**라 store와 분리(별도 보조 테이블)
- **v0.18.0 — convenience BC 신설**: 소진공 상가정보 sdsc2 × 행정동 427회 호출로 편의점 현행 스냅샷
  **첫 적재 9,395건** (427/427 전 커버, 좌표·FK 100% 채움). 브랜드 분포: GS25 30.3% · CU 28.1% ·
  세븐일레븐 26.7% · 이마트24 6.5%. `first_seen/last_seen` 관측 필드로 소실=폐점 추정 후보를 후속
  분석에 위임 + 주 1회 크론(월 05:40). **백엔드 전체 테스트 135건 중 134 passed**

### 7. [백엔드] 운영 정비 — 도커 이미지 갱신 + CLAUDE.md Part V (Backend v0.15.1)

- 13일 전 구버전으로 돌던 `beyondfacade-api` 컨테이너를 v0.15.0 코드로 재빌드·재기동 —
  `/regions/geojson` 427 features 등 실검증 통과, `BoundaryFileReader` 경로가 컨테이너 마운트와
  일치함을 실확인
- CLAUDE.md **Part V(프론트엔드 구조 규칙) 성문화** — Feature-Sliced 구조, mock API 계약,
  토큰 기반 스타일·다크모드, TanStack Query, MapLibre WebGL 브리징, Vitest·TDD (실코드 관행 기반)

### 8. [프론트엔드] 실경계·실 API 컷오버 + 범례 — Frontend v0.10.0~v0.12.0 (`feature/frontend-mvp`)

- **v0.10.0**: mock 사각형 8개 → 백엔드 산출 **서울 행정동 427개 실경계 GeoJSON**으로 교체
  (코로플레스가 서울 전역에 칠해짐)
- **v0.10.1**: 단계구분도 색상을 연속 보간 → **이산 7클래스**로 교체 — sequential은 YlOrRd 7클래스 +
  분위수 경계(동 색 대비 최대화), diverging은 RdBu 0 중심 대칭(성장률 부호 = 색 부호)
- **v0.12.0 — 실 API 컷오버**: `NEXT_PUBLIC_API_BASE`로 지도 탭을 백엔드 v0.9.0 실 API에 연결
  (geojson 427·metrics 427행·summary 카드·stores 역삼1동 카페 705행 — curl+브라우저 실검증).
  AI 분석 탭만 mock 유지(RAG 백엔드 미구현). 컷오버 필수 결함 3건 수정(지도 에러 배너·SSE
  JSON.parse 무가드·React key 중복) + **단계구분도 범례** 추가 — `makeMetricColorScale`이 페인트
  색과 범례 구간의 단일 원천(`{colorOf, classes}`). vitest 39건·`tsc --noEmit` 통과

### 9. [설계] RAG + 단일 에이전트 스펙·구현 계획 확정 (AI 분석 탭 실구현 준비)

- **설계 스펙** (`docs/superpowers/specs/2026-09-07-rag-agent-design.md`): RAG 검색 계층
  `apps/rag` BC(v0.19.0, `rag_chunk` 1536차원 벡터 + Recall@5 평가 하네스) → 에이전트 루프
  `apps/agent` BC(v0.20.0, 도구 7종 = 기존 UseCase 래핑, **Port = Tool 원칙**) → 프론트 전환
  (FE v0.13.0, SSE 계약 기존 그대로) → 두뇌 모델 평가(로컬 먼저, Gemini 다음)
- **임베딩 혼용 구도 실측 확정**: 색인은 qwen3-embedding-4b fp16, 쿼리는 Q4 — 교차 런타임 검색
  실측 **top-1 100% / top-5 85%**로 Q4 쿼리 기준선 검증 (lifetutorial의 로컬+Gemini 1536차원
  이중 어댑터 패턴 이식). 평가 코퍼스로 정책자금 공고 200건 추출
- **구현 계획** (`docs/superpowers/plans/2026-09-07-rag-agent.md`): **14태스크 로드맵** —
  rag BC(Task 1~7) → agent BC(Task 8~11) → 프론트 전환(Task 12) → 모델 비교 평가(Task 13~14)

### 다음 작업

- [ ] **RAG+에이전트 구현 착수** — Task 1(rag_chunk 스키마 + HNSW 인덱스, BE v0.19.0)부터 14태스크 순차 진행
- [ ] SGIS 지오코딩 — 학원·부동산중개 lat/lng NULL 대기열 해소 후 지표 집계 합류
- [x] `feature/frontend-mvp` 병합/PR 결정 (v0.12.0 컷오버 완료 상태로 보존 중) — 9/15 main 병합 완료
- [ ] docker-compose frontend 포트 매핑 `3200:3000` 불일치 정리 (포스트MVP 이연)
- [ ] AWS G 인스턴스 쿼터 증설 신청 (8/25 이월)
- [x] 어린이집정보공개포털 승인 후 키 입력 (`CHILDCARE_API_KEY`, 8/25 이월) — 9/15 승인(cpmsapi030)·키 인증 통과. 개발계정은 스펙 샘플만 반환 → **운영계정 신청 후 실데이터 수집** (후속)
- [ ] 연령별 인구 2026.07분 1파일 추가 (공표 확인 후, 8/25 이월)

## 2026-09-15

### 1. [백엔드] rag BC 신설 — 색인·검색·Recall@5 평가 하네스 (Backend v0.19.0)

9/7 확정한 14태스크 로드맵의 **Task 1~7(rag BC 전체) 완주** — RAG 검색 계층 Phase 1 완료.

- **`rag_chunk` 테이블** — `vector(1536)` + HNSW 인덱스, source_type/source_id 복합 인덱스,
  region_code FK(nullable)
- **`EmbeddingPort` + 어댑터 3종** (전부 1536차원 규격 통일): Ollama Q4(색인 겸 검색 고정),
  fp16(로컬 GPU, 지연 로딩), Gemini(온라인, 429 재시도) — **혼용 구도를 코드로 강제**
  (색인 임베더는 provider 선택, 검색(query) 임베더는 Ollama Q4 고정)
- 청크 빌더(funding/news 순수 함수) + 소스 게이트웨이 — cross-BC 접근은 게이트웨이 파일 안에만 국한
- `SqlAlchemyRagRepository` — chunk_id 업서트 + 코사인 유사도 검색, 만료 공고 기본 제외
  (`exclude_expired_funding=True`, non-funding이 join에서 드롭되지 않게 outerjoin 조건 구성)
- 색인/검색 UseCase 분리(ISP) + `build_rag_index.py` CLI + 크론(매일 05:50, **provider=fp16 명시** —
  크론이 조용히 다른 모델로 색인해 혼용 구도가 깨지는 사고 방지)
- **초기 색인 6,157건** (funding 1,761 + news 4,396) — Q4(ollama)로 수행.
  fp16 전량 재색인은 GPU 점유(다른 상주 모델 13GB대, 여유 VRAM 2.4~2.6GB)로 보류
- **Recall@5 평가 하네스** (`evaluate_rag.py`): 순수 함수 `recall_at_k`·`mrr` + provider별 실행·JSON 저장.
  **평가셋 후보 생성기** (`generate_evalset.py`): 색인 funding 청크 결정적 표본 50건 → gemma3:12b로
  자연어 질문 생성(candidate 50행, 약 54초). 시운전(candidate 기준 "(참고)" 수치):
  **ollama Recall@5 0.900 / MRR 0.782**. fp16은 GPU 제약으로 스킵, gemini는 쿼터 보존으로 미실행
- candidate → confirmed 승격은 사용자 검수 몫(후속). 테스트: recall_at_k·mrr 4케이스 등 TDD 전 과정 통과

### 2. [프론트엔드] v0.12.0 main 병합 — `feature/frontend-mvp` 통합 완료

- 9/7 컷오버 완료 상태로 보존하던 브랜치를 main에 병합(c1f41d2) — **20커밋 · 75파일 · 9,270라인**,
  충돌 0건. 원격 push까지 완료, 워크트리 제거로 프론트 소스는 `frontend/` 단일 위치로 일원화
- 병합 후 vitest 전건 통과, 백엔드와 동시 기동해 지도 탭 실 API 연동 정상 동작 실검증

### 3. [문서] 일정 압축 반영 — 마감 10/27 → 10/8 (10주 → 7주)

- `brainstorming.md` MVP 주차표 압축(5~10주 → 5/6/7주), `agent-architecture.md` §3 구축 순서
  7주 재배치 + §4-1 AWS 이전 전 로컬 개발 시한 9월 하순으로 조정, 본 개발일지 일정 표기 정합화
- 공개 사이트(지킬) 스프린트 로드맵·칸반을 실제 진행 상황(RAG 조기 완료 등)으로 동기화,
  기술 스택 표기를 Flutter → **웹(Next.js)** 으로 전면 교체(실구현과 문서 일치화)

### 4. [문서] 어린이집정보공개포털 승인 — api.md ⑬ 갱신

- 8/25 신청한 개발계정 **9/15 승인** (승인 API: cpmsapi030 어린이집 일반현황) —
  `CHILDCARE_API_KEY` 기입, 실호출 인증 통과, 응답 스키마 **62필드 실확인**
  (정원 crcapat·현원 crchcnt·좌표·반별/연령별/보육교직원 카운트)
- 단, 개발계정 키는 스펙 샘플(전 필드 더미 순번)만 반환 — **실데이터 수집 전 운영계정 재승인 필수** (후속)

### 5. [문서] 프로젝트 산출물 구조 문서 신설

- `docs/프로젝트_산출물_구조.md` — milestone·WBS부터 서버 구성, 타당성 검토(실데이터 기반 ERD 원칙,
  임베딩 fp16/Q4 혼용 실측), 백엔드·프론트·AI 스택까지 프로젝트 전체 산출물을 한 문서로 집약

### 다음 작업

- [ ] **agent BC 착수 (Task 8~11, BE v0.20.0)** — 도구 7종 = 기존 UseCase 래핑, Port = Tool 원칙 — 9/16 Task 8~10 완료, Task 11 남음
- [ ] RAG 평가셋 candidate 50건 검수 → confirmed 승격 (본지표 산출 전제)
- [ ] fp16 전량 재색인 + fp16 Recall@5 측정 — GPU 여유 시 `--full --provider fp16` 수동 실행
- [ ] 어린이집 운영계정 신청 → cpmsapi030 실데이터 수집
- [ ] SGIS 지오코딩 — 학원·부동산중개 lat/lng NULL 대기열 (9/7 이월)
- [ ] docker-compose frontend 포트 매핑 `3200:3000` 불일치 정리 (포스트MVP 이연)
- [ ] AWS G 인스턴스 쿼터 증설 신청 (8/25 이월)
- [ ] 연령별 인구 2026.07분 1파일 추가 (공표 확인 후, 8/25 이월)

## 2026-09-16

9/15 rag BC(Task 1~7)에 이어 **agent BC Task 8~10 구현** — 5커밋 · 신규/수정 약 1,850라인.
BE 버전(v0.20.0)은 라우터·SSE까지 붙는 Task 11 완료 시점에 확정·기록 예정.

### 1. [백엔드] LLMGatewayPort + gemma3·Gemini 어댑터 (Task 8)

- `apps/agent` BC 골격 + `LLMGatewayPort`(`chat` 단일 메서드) — `LLMToolSpec`·`LLMToolCall`·`LLMUsage`·
  `LLMTurn`을 **프로바이더 중립 계약**으로 정의해 도구 레지스트리·에이전트 루프가 이 포트 위에서 동작
- **OllamaLLMAdapter**: `/api/chat` + tools를 function 스펙으로 변환, `tool_calls` 파싱,
  토큰 사용량(`prompt_eval_count`/`eval_count`) → `LLMUsage`
- **GeminiLLMAdapter**: system_instruction 분리·role 매핑·functionResponse 변환을 순수 함수로 분리,
  요청 간 **최소 4초 간격** + 429 지수 백오프(재시도 예산 30초, 임베딩 어댑터와 동일 관행)
- 테스트 5건 (Ollama 3 + Gemini 변환 함수 2, 실호출 없음)

### 2. [백엔드] 도구 레지스트리 7종 + 월세 vs 매입 계산기 (Task 9)

- `RegionFactsPort` 5메서드(metrics/summary/population/shocks/latest_rates) — 구현체
  `RegionFactsGateway`가 metric·master·shock BC를 **어댑터 레이어에서만** 조회(app 레이어는 포트만 import)
- **도구 7종을 if/elif 없이 리스트 registry로 조립** — market(get_region_metrics·get_region_summary·
  get_population) / shock(search_shocks·search_news) / funding(search_funding·compare_rent_vs_buy)
- `compare_rent_vs_buy` 순수 계산기: 연금리 생략 시 시설자금대출(`loan_facility`) 최신값 자동 주입,
  결과에 **금융 규제 경계 고지(assumptions)** 항상 포함
- 리뷰 수정(b1c3b2e): 금리 미적재 시 KeyError로 도구가 죽던 문제 → `{"error": ...}` JSON 반환으로
  우아하게 실패. 테스트 7건 통과

### 3. [백엔드] 단일 에이전트 루프 — SSE 이벤트 계약 (Task 10)

- `AgentEvent` 엔티티(프론트 `types.ts` 미러) + `AnalysisUseCase` 입력 포트 + `AnalysisInteractor`
  (제너레이터) — `agent_status → tool_call → report_delta → report_done` 순서 계약으로 스트리밍
- SYSTEM_PROMPT **응답 규칙 4종**(외국인 변수·지원금 왜곡·금융 규제 경계·신뢰 등급 표기) +
  `[SECTION:*]` 마커 5종, `split_report_sections` 파서(누락 섹션은 "분석 데이터가 부족합니다." 폴백)
- **루프는 죽지 않는다**: 인자 스키마 위반은 재프롬프트 1회 후 스킵, 도구 예외는 `{"error"}` 되먹임,
  **12턴 초과 시 최종 리포트 강제**, 전 chat 호출 usage를 `last_usage`에 합산(Task 11이 영속화)
- 리뷰 수정(46f567c) 4건: ① citations를 프론트 계약 `{title, url, grade}` 3키로 정규화(등급별 제목 테이블)
  ② cite 콜백 예외 가드 — 인용 실패해도 리포트 스트림 끝까지 방출 ③ 재프롬프트 이력 순서 — 유효 호출 먼저
  실행 후 위반 호출만 재시도(dangling tool_call 제거) ④ Gemini 어댑터가 `tool_name` 키를 읽도록 크로스태스크 갭 수정
- 테스트 16건 통과 (`test_agent_loop.py` 11 + `test_agent_llm_adapters.py` 5)

### 다음 작업

- [ ] **Task 11 — agent 영속화 + 라우터 + SSE 엔드포인트** (BE v0.20.0 확정, 버전 로그 기록)
- [ ] Task 12 — 프론트 AI 분석 탭 mock → 실 SSE 전환 (FE v0.13.0)
- [ ] Task 13~14 — 두뇌 모델 비교 평가 (gemma3 로컬 → Gemini)
- [ ] RAG 평가셋 candidate 50건 검수 → confirmed 승격 (9/15 이월)
- [ ] fp16 전량 재색인 + fp16 Recall@5 측정 — GPU 여유 시 (9/15 이월)
- [ ] 어린이집 운영계정 신청 → cpmsapi030 실데이터 수집 (9/15 이월)
- [ ] SGIS 지오코딩 — 학원·부동산중개 lat/lng NULL 대기열 (9/7 이월)
- [ ] docker-compose frontend 포트 매핑 `3200:3000` 불일치 정리 (포스트MVP 이연)
- [ ] AWS G 인스턴스 쿼터 증설 신청 (8/25 이월)
- [ ] 연령별 인구 2026.07분 1파일 추가 (공표 확인 후, 8/25 이월)

## 2026-09-17

어린이집 실데이터 수집부터 어린이집·편의점 지도 연결까지 완료하고, **서울 상권 아틀라스** 방향으로
랜딩·지도 탐색·AI 분석 화면을 정리했다. 실DB 기준 최종 ERD(21개 테이블)도 확정했다.
Backend **v0.20.0**, Frontend **v0.13.0~v0.14.0**.

### 1. [백엔드] 어린이집 수집·이력 저장 — childcare BC 신설 (Backend v0.20.0)

- **운영계정으로 cpmsapi030 실데이터 수집 완료** — 자치구 25회 호출로 서울 어린이집 **3,940곳** 적재,
  실패 구 0. 기존 개발계정 샘플 반환 문제를 해소하고 매주 월요일 05:30 수집 크론 등록
- 시설 정보 `childcare_center`와 기준일별 정원·현원·입소대기 `childcare_center_stat`를 분리.
  현황을 덮어쓰지 않아 이후 가동률 추이를 비교할 수 있고, first/last_seen으로 관측 이력을 보존
- 첫 스냅샷: 정원 **191,788명**, 현원 **130,019명**, 서울 가동률 **67.8%**.
  행정동 연결 **3,912곳**, **426/427개 동** 커버. 좌표 누락 7곳과 자치구 불일치·경계 밖 21곳은
  행정동을 임의로 채우지 않음
- 입소대기·상태 공란은 NULL 보존. 대표자명은 수집하지 않고, 등록 자치구 밖을 가리키는 좌표는
  공간조인에서 제외. API가 HTTP 200으로 반환하는 인증 오류도 본문의 `errcode`로 검출

### 2. [백엔드] 어린이집·편의점 조회 API와 점포수 지표 연결 (Backend v0.20.0)

- **어린이집 API** — 행정동별 시설 마커와 최신 정원·현원·입소대기·가동률 요약 제공.
  현행 시설은 **자치구별 최신 관측일**로 판정해 한 구의 수집 실패가 다른 구의 시설 표시를 바꾸지 않음
- **편의점 API** — 행정동별 점포 마커와 브랜드별 점포 수·기준연월 제공.
  현행 점포는 **행정동별 최신 관측일**로 판정. 실서버 확인: 역삼1동 **149곳**,
  GS25 54·세븐일레븐 49·CU 34·이마트24 7·미니스톱 2·기타 3
- **점포수 지표 합류** — 전체 지표 **21,005건** 재집계. 2026년 어린이집 **3,912곳/426개 동**,
  편의점 **9,395곳/427개 동**을 단계구분도와 요약 카드에서 조회 가능
- 스냅샷에는 개폐업 이력이 없으므로 **개업 수·폐업 수·폐업률·성장률은 NULL**로 유지.
  관측하지 않은 2019~2025년 값도 만들지 않음. 입소대기 합은 중복 신청을 포함하는 수치로 표시
- 백엔드 버전 로그 기준 최종 테스트 **213건 중 212건 통과**.
  기존 `test_store_ingest` 실DB 커서 테스트 실패 1건은 남아 있으며, 이번 작업으로 해결된 것으로 기록하지 않음

### 3. [프론트엔드] 어린이집·편의점 지도 마커와 현황 패널 (Frontend v0.13.0)

- **업종별 마커 전략(Strategy)** 도입 — 기존 점포 마커를 `RegionMarkers`로 일반화하고,
  업종별 조회 함수·캐시 키·팝업 구성을 분리. 카페 등 기존 업종의 지도 동작은 유지
- 어린이집 팝업에 유형·상태·정원·현원·가동률·입소대기를 표시하고, 사이드패널에 시설 수·합산 현황 제공.
  미공개 값은 `미공개`/`상태 미상`으로 구분. **청운효자동 4곳·가동률 62.1%·입소대기 108건** 실검증
- 편의점 팝업에 상호·브랜드·주소를, 사이드패널에 브랜드 분포와 원천 기준연월을 표시.
  역삼1동 **149곳 클러스터 → 개별 점포 팝업**까지 브라우저로 확인
- mock API도 실 API 계약에 맞춰 정리하고, 목록과 요약의 합산 규칙·404·표시 포맷·마커 전략 테스트 추가

### 4. [프론트엔드] Remote-SSH 지도 요청 오류 수정 (Frontend v0.13.1)

- 포트 포워딩으로 접속한 브라우저가 `127.0.0.1:8201`을 개발 서버가 아닌 사용자 PC로 해석해
  지도 데이터를 받지 못하던 원인 확인
- Next.js의 **`/api/backend/*` → 서버 전용 `BACKEND_ORIGIN/*` 프록시** 추가.
  브라우저는 프론트엔드와 같은 origin으로 요청하고, 백엔드 주소는 서버에서 처리
- health·행정동 GeoJSON·지표의 200 응답과 404 오류 본문 전달을 확인.
  프록시 설정이 없을 때의 기존 mock 동작을 보존하고, 해당 시점 테스트 **68건** 통과

### 5. [디자인·프론트엔드] 서울 상권 아틀라스 랜딩과 세 화면 톤 통일 (Frontend v0.14.0)

- **랜딩 `/` 신설** — “서울의 변화 속에서, 내 가게의 자리를 찾다.”를 중심으로
  상권 탐색 CTA·기능 소개·이용 순서를 구성. 아이보리 바탕과 청록색, 큰 제목과 여백으로 서비스의 인상을 정리
- **Blender 도시 모형·위치 핀 제작** — 편집 가능한 `.blend`와 재현 스크립트를 함께 제공.
  웹에서는 투명 WebP **2장, 총 74,590 bytes(약 75KB)**와 CSS 모션만 사용하며 실시간 3D 런타임은 추가하지 않음.
  서울을 표현한 개념 모형임을 표기하고 모바일·reduced-motion에서는 장식 모션 정지
- **지도 `/map` 분리** — 기존 `/?region=…&industry=…` 링크는 쿼리를 보존해 이동.
  지도 링크의 자동 prefetch를 끄고, 랜딩에서 지도 모듈·지도 API를 로드하지 않도록 분리
- **지도 탐색** — 제목·필터·지도 프레임·지역 브리프의 위계를 정리.
  **AI 분석** — 입력·진행 상황·문서형 리포트를 같은 톤으로 구성.
  공통 헤더·색상 토큰·다크 테마를 통일하고 모바일에서는 패널을 세로 배치. 지도·분석에는 3D 효과를 추가하지 않음
- **기존 데이터 동작 유지** — 지도 렌더링·데이터 색상 스케일·필터·SSE 계약 보존.
  AI 분석은 기존 **모의 API(`/api/mock`)**를 사용하며, 실제 분석 백엔드 연결은 후속 작업
- **서브에이전트 구현·독립 검토** — 지도와 AI 화면을 나눠 구현하고 공통 UI를 통합.
  검토에서 보조 텍스트 대비를 **5.12:1**로 개선하고, 부분 리포트 수신 후 오류가 나면 내용은 유지하며
  상태를 **`작성 중단`**으로 표시하도록 수정
- 최종 **Vitest 25파일·77건**, TypeScript 검사, 프로덕션 빌드 통과.
  랜딩 1440/1024/390/320px, 지도·완성 리포트 데스크톱/390/320px, 다크 모드와 모션 감소 상태 확인.
  **지도 선택 → 지역·업종 전달 → 분석 제출 → 리포트 5개 섹션·참고 자료 4건** 흐름을 검증
- v0.14.0은 `codex/seoul-atlas-landing` 브랜치에서 구현·검증을 마친 상태이며, 배포 완료를 의미하지 않음

### 6. [개발 환경·문서] 최종 ERD·인수인계 문서와 변경 기록 정리

- **최종 ERD 작성 (`docs/erd.md` §6)** — 운영 DB `information_schema`를 실제로 조회해 **21개 테이블** 기준 Mermaid ERD 작성.
  DB FK 제약은 실선, 애플리케이션 레벨 참조(`rag_chunk` 다형 참조·지표 배치 집계·금리↔임대료 계산 조인)는 점선으로 구분
  - 적재 현황: store **348,792** · population_stat **142,632** · tobacco_retailer **95,402** · region_industry_metric **21,005** ·
    convenience_store **9,395** · rag_chunk **6,645** · childcare_center **3,940** 등
  - 초안(MVP 15개 테이블) 대비: `rag_chunk` 추가, `sales_estimate`·`funding_program_industry` 미구현,
    지표 테이블 PK를 (region_code, industry_id, year) 복합키로 바꾼 점 등을 정리
  - §13 연결 원칙 점검: `funding_program`은 DB FK가 없어 업종 연결 테이블 구현이 필요하고, `shock_event_region`은 적재 0건
- **API 문서 갱신 (`docs/api.md`)** — 어린이집 운영계정 승인·`CHILDCARE_API_KEY` 교체(종로구 실데이터 58건 확인)와
  수집기 실적재 완료(3,940건) 표시
- **인수인계 문서 `docs/HANDOFF.md` 작성** — 현재 상태(지도 실 API 연결, AI 분석 탭 mock, 수집 크론 일정, 개발 서버 구성)와
  남은 작업을 우선순위별로 정리. Task 11~14는 GPU 16GB 중 13.4GB를 다른 프로젝트 시연 모델이 점유하고 있어 **보류**,
  Task 11은 **BE v0.21.0**으로 버전을 다시 배정
- 백엔드 도커 이미지를 **v0.20.0으로 재빌드**해 `beyondfacade-api`(8200) 재기동
- `.gitignore`의 데이터 제외 범위를 루트 `/data/`로 한정해 디자인 스킬의 참조 데이터가 함께 제외되던 문제 수정.
  UI 스타일·색상·타이포그래피 등 참조 자료를 저장소에서 추적
- 랜딩 설계·구현 계획과 Blender 자산 재현 문서를 작성하고, 프론트엔드 버전 로그를 v0.14.0까지 갱신

### 다음 작업

- [x] **Task 11 — agent 영속화·라우터·SSE 엔드포인트** 구현 (**BE v0.21.0** — 기존 계획의 v0.20.0은
  오늘 childcare 기능에 사용). GPU를 점유한 시연 모델이 내려간 뒤 `ollama ps`로 확인하고 재개 — 9/21 완료
- [ ] `funding_program_industry`(지원사업↔업종) 구현 — 최종 ERD 연결 원칙 점검에서 확인된 미연결 테이블 해소
- [x] Task 12 — AI 분석 화면을 mock에서 실 SSE로 전환 (후속 프론트엔드 버전으로 기록) — 9/21 완료(FE v0.14.0, analysis-api 브랜치)
- [ ] Task 13~14 — 두뇌 모델 비교 평가 (gemma3 로컬 → Gemini) — 9/21 Task 13 러너 완료, Task 14 실행 대기
- [ ] RAG 평가셋 candidate 50건 검수 → confirmed 승격, GPU 여유 시 fp16 전량 재색인·Recall@5 측정 — 9/22 fp16 재색인 완료(BE v0.22.1), 검수는 대기
- [ ] 서울 상권 아틀라스 변경 검토 후 병합·배포
- [x] SGIS 지오코딩 — 학원·부동산중개 좌표 누락 대기열 해소 — 9/22 완료(BE v0.22.0)
- [ ] docker-compose frontend 포트 매핑 정리·AWS G 인스턴스 쿼터 증설·연령별 인구 2026.07분 확보

## 2026-09-21

9/17에 GPU 점유로 보류했던 **Task 11~13**을 `feature/analysis-api` 워크트리(main에서 분기)에서 재개했다.
agent BC를 HTTP/SSE 엔드포인트와 영속화로 마감하고, 프론트엔드 AI 분석 탭을 실 백엔드 SSE로 전환했으며,
두뇌 모델 비교 평가 러너를 준비했다. Backend **v0.21.0**, Frontend **v0.14.0**(analysis-api 브랜치 기준).

### 1. [백엔드] agent BC SSE 분석 API — Task 11 마감 (Backend v0.21.0)

- **`POST /analysis` · `GET /analysis/{id}/events` · `GET /analysis/myself`** 3개 엔드포인트 신설.
  myself로 라우터→유스케이스→인터랙터 배선을 먼저 확인하고, POST로 analysis_id(UUID)를 발급한 뒤
  SSE 프레임(`event: {type}` + `data:`)을 이벤트 순서대로 스트림
- Composition Root `analysis_dependencies` — 모델 레지스트리 **`gemma3 | gemini`**를 Factory Method로 분기.
  요청마다 AnalysisInteractor 인스턴스를 새로 만들어 토큰 사용량(`last_usage`) 가변 상태를 요청 간 격리
- **gemma4:12b 배선** — 현행 `gemma3:12b`는 Ollama tools capability가 없어(`does not support tools`)
  API 키 이름은 `gemma3`로 유지하고 실제 모델만 동일 패밀리 **`gemma4:12b`**로 교체
- **영속화** — 스트림 완료 시 `analysis_report` 1행 + `llm_usage` 1행 저장(마이그레이션 `a1b2c3d4e5f6`).
  `report_done.report_id`를 analysis_id와 같게 두어 mock 계약과 대칭. 진행 중 id는 프로세스 수명 `_PENDING`에 보관
- 라우터 테스트 **4건**(Fake UseCase) — myself 200·POST UUID·SSE 프레임 순서·미지 id 404 본문
- 스모크(8299, 역삼1동 카페): **약 23초**, input **14,377** / output **719** 토큰, DB 1+1행 저장 확인
- T8 LLM 어댑터(Ollama·Gemini)·T9 도구 7종·T10 단일 에이전트 루프는 선행 커밋이며,
  이번 버전에서 HTTP/SSE·영속화에 연결되어 마감

### 2. [프론트엔드] AI 분석 탭 실 SSE 전환 — Task 12 (Frontend v0.14.0)

- `ANALYSIS_API_BASE=/api/mock` 상수와 TODO 제거. 분석 POST·EventSource가 `config.apiBase`
  (`NEXT_PUBLIC_API_BASE=/api/backend`)를 따르므로 **코드 수정 없이 env만으로** mock↔실 API 전환
- 백엔드 계약이 mock과 동일해 훅 로직은 무변경. 테스트는 "mock 고정" 계약을 "config.apiBase를 따른다"로 반전
- **버전 번호 충돌 주의** — `codex/seoul-atlas-landing` 브랜치의 아틀라스 랜딩도 **Frontend v0.14.0**(9/17)으로
  기록되어 있어, 두 브랜치 병합 시 한쪽 번호를 재배정해야 함

### 3. [백엔드] 모델 비교 평가 러너 — Task 13

- `run_agent_eval --model gemma3|gemini` CLI. **시나리오 10건** — 업종 기본 6건(역삼 카페·잠원 헬스장·
  삼성 노래방·가산 PC방·청운효자 미용실·청담 당구장), 부분 데이터 2건(편의점·어린이집 — 폐업률·성장률이
  없으므로 "지어내기 금지" 기대), 규칙 2건(대림3동 "외국인 많은 동네" 질문 → 차별 금지,
  역삼 부동산 "대출 어디서" 질문 → 은행 추천 금지)
- 자동 채점 순수 함수 3종 — tool_call 호출·스킵 수, 금지 키워드 적중(은행명+권유어, 외국인 비하),
  리포트 **5섹션 완성률**("분석 데이터가 부족합니다"만 있으면 미완성). 단위 테스트 **4건**
- 결과는 `data/eval/results/agent_{model}_{ts}.jsonl`에 리포트 전문 포함 저장(수동 검토용).
  Gemini는 무료 티어 요청 간격 4초. 키워드 채점은 부정문·맥락을 판별하지 못하므로 최종 위반 판정은 수동 병기
- 평가 실행(Task 14)은 아직 하지 않음 — 결과 파일 없음

### 다음 작업

- [x] **Task 14 — 평가 실행** gemma4(로컬) → Gemini 순으로 시나리오 10건 실행, 비교표 작성 — 9/22 완료(BE v0.21.1)
- [ ] `feature/analysis-api` ↔ `codex/seoul-atlas-landing` 병합 순서 결정, Frontend v0.14.0 번호 충돌 해소 — 9/22 PR #1 생성, 머지 대기
- [ ] `docs/api.md`에 `/analysis` 엔드포인트 3종 반영 (오늘 미갱신)
- [ ] `funding_program_industry` 구현·RAG 평가셋 검수·SGIS 지오코딩 등 9/17 잔여 항목 유지 — SGIS 지오코딩은 9/22 완료(BE v0.22.0)

## 2026-09-22

`feature/analysis-api` 워크트리에서 Task 14 두뇌 비교 평가를 마치고, 9/17부터 이월된 **SGIS 지오코딩**과
**RAG fp16 전량 재색인**을 GPU가 비는 틈에 처리했다. 프론트엔드는 어린이집·편의점 스냅샷 업종의 표시 규칙과
포스트MVP 잔여 UX를 정리했다. Backend **v0.21.1~v0.22.1**, Frontend **v0.14.1~v0.14.4**(analysis-api 브랜치 기준, PR #1).

### 1. [백엔드] 두뇌 비교 평가 결과 — Task 14 마감 (Backend v0.21.1)

- **Gemini 기본 모델 교체** `gemini-2.0-flash` → `gemini-2.5-flash`. 2.0은 폐기되어 404를 반환했고,
  3.6-flash는 `thought_signature`를 요구해 현 어댑터로는 보류
- **시나리오 10건 × gemma4:12b(로컬) vs gemini-2.5-flash** 실행, 비교표 `data/eval/results/agent_compare.md` 작성
  (원본 jsonl 2건 force-add)
  - 리포트 5섹션 완성률 **50% vs 90%**, 평균 소요 **39.9s vs 17.4s**, 평균 토큰(입+출) **10,997 vs 7,570**,
    평균 도구 호출 3.4 vs 5.0, 도구 성공률 양쪽 100%
  - 자동 규칙 위반 감지(외국인 비하·특정 은행 추천) **0/10 양쪽**. 키워드 근사라 최종 판정은 `report_md` 수동 검토 병기
  - gemma4는 잠원 헬스장·청운효자 미용실·편의점 부분 데이터 3건에서 0/5, Gemini는 청담 당구장 1건만 0/5(6초 만에 종료)
- 두뇌 채택은 **A Gemini 단독 / B 로컬 단독 / C 혼합(데모는 Gemini, 야간 배치·폴백은 로컬)** 세 안으로 정리.
  Composition Root 레지스트리로 C안이 이미 가능하며, 최종 결정은 팀 몫으로 남김

### 2. [백엔드] SGIS 지오코딩 파이프라인 — 학원·부동산중개 좌표 누락 해소 (Backend v0.22.0~v0.22.1)

- `store`에 **`road_address` / `jibun_address`** 컬럼 추가(마이그레이션 `b2c3d4e5f6a7`).
  학원 게이트웨이는 `ROAD_NM_ADDR`, 중개 게이트웨이는 `rdnmadr`/`mnnmadr`를 적재
- **`SgisGeocodingGateway`** — 액세스 토큰 4시간 캐시, UTM-K(EPSG:5179) → WGS84 변환.
  `GeocodeStoresInteractor` + CLI `geocode_stores [--limit N] [--industry …]`로 lat/lng NULL 대기열만 처리.
  입력·출력 포트(`geocode_stores_use_case`·`geocoding_port`·`store_geocode_port`) 신설, 테스트 3파일 추가
- **업서트 시 원천 좌표가 NULL이면 기존 지오코딩·공간조인 결과 보존** — 학원 재수집 때 좌표가 다시 사라지던 문제 차단
- 운영 보강 2건 — 좌표를 **200행마다 flush**해 장시간 실행 중 중단돼도 진행분 유지,
  미매칭만 남은 대기열에서 `geocoded==0`이면 **exit 2**로 종료해 크론 무한루프 방지.
  `store-collector.sh` 크론에 지오코딩 단계 합류
- **전량 지오코딩 완료** — 학원 **25,504** · 중개 **25,299** 좌표 확보, 행정동 배정 25,504·25,281,
  `region_industry_metric` **3,408·3,416행** 합류. 미매칭 잔여 학원 4·중개 2
- **`GET /stores` 500 수정(v0.22.1)** — `Store` 엔티티에 추가한 주소 필드가 `StoreDto(**asdict)`에 없어 TypeError.
  DTO와 응답 스키마에 동일 필드를 추가해 복구
- 선행 조건: `SGIS_SERVICE_ID` / `SGIS_SECURITY_KEY`가 `.env`에 없으면 CLI가 즉시 실패.
  순서는 수집(주소 채움) → geocode_stores → assign_regions → build_metrics

### 3. [백엔드] RAG fp16 전량 재색인 (Backend v0.22.1)

- GPU 점유 모델이 내려간 것을 확인하고 **7,505건 전부 `qwen3-embedding-4b-fp16`**으로 재색인(343.8초).
  Q4·fp16 혼용 상태 해소
- 참고 평가: candidate 50건 기준 **Recall@5 0.900 / MRR 0.791** (`data/eval/results/rag_fp16_20260922_122721.json`).
  confirmed가 0건이라 본지표는 아직 산출하지 않음 — 평가셋 검수는 사용자 작업으로 유지

### 4. [프론트엔드] 어린이집·편의점 스냅샷 업종 표시 규칙과 딥링크 (Frontend v0.14.1~v0.14.3)

- **v0.14.1** — 스냅샷 원천이라 폐업률·성장률이 NULL인 업종은 지표 버튼을 점포수만 노출하고,
  URL의 폐업률/성장률 지표는 `store_count`로 보정. 사이드패널 카드 숨김 + 안내 문구, 지도 빈 지표 배너를 점포수 기준으로 구분
- **v0.14.3** — 위 숨김을 철회. 지표 버튼과 사이드패널 카드 3종을 모두 다시 표시하고 값이 없으면 **"데이터 없음"**,
  스냅샷 원천 안내 문구만 유지 (`map-state` 순수 함수 31줄 → 단순화, 테스트 갱신)
- **v0.14.2** — 딥링크 `?region=` 진입·선택 시 GeoJSON 행정동 bbox로 **`fitBounds`**.
  순수 함수 `bboxOfRegion` + 단위 테스트로 고정

### 5. [프론트엔드] 포스트MVP 잔여 UX 정리 (Frontend v0.14.4)

- **스트림 에러 시 에이전트 슬롯 stale 수정** — SSE `onerror`·JSON 파싱 실패 때 `running` → `error`로 전이(훅 테스트 추가)
- **테마 새로고침 리셋 수정** — `localStorage(metabole-theme)` 저장 + layout 부트 스크립트로 첫 렌더부터 다크 유지
- Pretendard **CDN → 셀프호스트**(`pretendard` 패키지 CSS import), AnalysisForm 업종 입력을 `INDUSTRIES` select로 교체
- `readAccentColor`를 `shared/lib/accent-color.ts`로 승격(map-view export 제거),
  maplibre 워커 벤더링을 `scripts/vendor-maplibre-worker.sh` + `postinstall`로 자동화

### 6. [문서·인프라] HANDOFF 갱신과 PR #1

- **`docs/HANDOFF.md` 재작성**(9/22 기준, 69줄) — Task 11~14 완료 표시, 데이터 계층·UX·배포·정리 항목을 체크리스트로 재정렬.
  편의점 폐업률을 담배소매인 데이터로 대체하지 않기로 한 결정을 "재검토 불필요"로 명시
- rag-agent 설계·플랜 문서에 실제 버전(BE v0.21+/FE v0.14+) 주석. `docs/api.md`는 오늘도 미갱신(`/analysis` 3종·`/stores` 주소 필드)
- docker-compose 프론트 포트 `3200:3200` + Dockerfile `EXPOSE 3200` 정합.
  `test_latest_source_updated_at_returns_cursor`는 미래 커서 시각으로 실DB 오염 회피
- `feature/analysis-api` 푸시 + **PR #1** 생성. main 머지는 리뷰 후, `codex/seoul-atlas-landing`은 그 뒤 리베이스

### 다음 작업

- [x] **PR #1 리뷰 → main 머지**, 이어서 `codex/seoul-atlas-landing` 리베이스와 Frontend v0.14.0 번호 재배정 — 9/23 T0-2 병합으로 해소(FE v0.15.0~v0.17.0 재번호, main 73cc401 푸시)
- [ ] 두뇌 채택 **A/B/C** 팀 결정 → Composition Root 기본 모델 확정
- [ ] RAG 평가셋 candidate 50건 검수 → confirmed 승격 후 Recall@5 본지표 산출
- [ ] `docs/api.md`에 `/analysis` 3종·`/stores` 주소 필드 반영
- [ ] Vercel 앱 프로젝트 신설(`NEXT_PUBLIC_API_BASE` + 백엔드 터널) — 현재 CLI 계정에 Metabole 프로젝트 없음
- [ ] `funding_program_industry` 구현·어린이집 폐업률 산출 방식·연령별 인구 2026.07분·AWS G 쿼터 등 이월 항목 유지

## 2026-09-23

서울시 상권분석서비스 공개 CSV를 **commerce·neighborhood 두 BC**로 적재하고(약 1,000만 행), 그 위에
**동네 유형 6종·시간대 어긋남** 파생 계층과 조회 API를 세운 뒤, 방향을 **채팅 관문 전환**(로드맵 T0~T5)으로
재구성했다. T0 브랜치 합치기 → T1 관문(intent BC) → T2 무대(유형 단계구분도·패널 서사)까지 하루에 마감하고
main에 머지했으며, T3 계획(finance BC) 설계서로 끝냈다. Backend **v0.23.0~v0.32.0**, Frontend **v0.15.1~v0.21.0**.
설계서 8건(`docs/superpowers/specs/2026-09-23-*.md`)·로드맵 1건·ERD §6 갱신.

### 1. [백엔드] commerce BC — 상권분석서비스 업종 실적 적재 (Backend v0.23.0~v0.24.0)

- **v0.23.0 — `apps/commerce/` 신설.** 추정매출(OA-22175)·점포(OA-22172) 행정동 계열 로컬 CSV(공공누리 1유형, API 0회).
  `region_commerce_sales` **343,167행** · `region_commerce_store` **704,470행**, 20분기(2021Q1~2025Q4) 결측 없음.
  CP949, `기준_년분기_코드` 5자리 문자열 보존, 원천 8자리 행정동 코드 ↔ `region` 10자리 앞 8자리 1:1(충돌 0건).
  원천에만 있는 옛 행정동 3개(용신동·일원2동·상일동)는 버리지 않고 `region_code` NULL로 적재(0.63%)
- `industry_id`를 사실 테이블에 박지 않고 `industry_source_code`(seoul_commercial 12행 시드)로 조인 —
  cafe·gym 매핑이 바뀌어도 70만 행 재적재가 없다. 마이그레이션 `c7a4f2e19b35`, 테스트 6건
- **v0.24.0 — 매출 분해 47컬럼을 1NF long 테이블로.** `region_commerce_sales_breakdown`(dim_type × dim_key 23구간)
  **7,892,841행 / 13분 07초**, 부모와 복합 FK. 원천 헤더 오타(`시간대_건수~06_매출_건수`) 때문에 이름이 아니라
  **순서 기반 매핑**, 어긋나면 즉시 ValueError. 게이트웨이는 Iterator, 40,000행 청크 업서트로 상주 메모리 353MB
- **축별 총합 검증** — weekpart·dow·hour는 총액의 완전 분할(괴리 최대 5원), **gender·age는 금액 89.2%·건수 95.9%만
  덮는다**(인구속성 미확인 거래 누락) → 두 축은 절대금액이 아니라 구성비로만 쓴다는 제약을 기록
- 교차검증 문서 `commerce-crossvalidation.md` — 상권분석 `점포_수`는 총 점포수가 아니라는 발견, cafe에 패스트푸드·분식,
  hair_salon에 네일·피부를 더해야 우리 인허가 모집단과 맞는다는 판정(→ v0.26.0에서 매핑 12 → 16행 반영)

### 2. [백엔드] neighborhood BC — 동네 맥락 7종 적재 (Backend v0.25.0)

- **`apps/neighborhood/` 신설, 테이블 8개.** 유동인구·직장/상주인구·가구/아파트·주거 평균·집객시설·지출·상권 변화 +
  서울 평균 baseline. 업종 축이 없는 "분기×동" 데이터라 commerce와 BC를 갈랐다(어휘가 다르고, 합치면 10테이블로
  §12 컨텍스트 단위가 무너진다). 설계서 `neighborhood-bc-design.md`
- **첫 실적재 1,051,204행 / 1분 15초**, 22분기(20211~20262) 연속. 직장·상주 인구는 값 컬럼 21개가 동일해 한 테이블
  (`population_type`), 서울 평균은 분기에만 종속이라 **2NF 분리** 후 FK로 노드화, `change_name`은 근거를 남긴 역정규화
- **실데이터 함정 3건을 테스트로 고정** — 지출 CSV는 `음식`이 `기타` 뒤에 와서 순서 매핑이면 통째로 뒤바뀜(이름 매핑으로
  전환), 집객시설 `total`은 19종 합이 아니다(총량 커버리지 **48.4%**, 명동 542 대 151) → 나란히 놓지 말 것,
  `철도_역_수`는 NULL 100%. 직장인구는 425개 동 중 **11개 결측**. 테스트 19건

### 3. [설계] 동네 유형 분류 규칙·지출 정의·파생 지표 설계서

- `neighborhood-typology.md`(566줄) — 유형 6종(주거·먹자/나들이·업무·대학가·생활중심·혼합) 규칙과 상식 검증.
  임계값은 상수가 아니라 매 배치 분포에서 재계산, 판정 창은 **최근 4분기 이동평균**(분기 단독 불변 75.1% → 81.6%)
- `spending-definition.md` — 유입·유출 지수는 정의상 성립하지 않아 **폐기**, 지출 항목 구성비만 조건부 사용
- `region-profile-design.md` — `region_profile_quarter`·`region_industry_hour_gap_quarter` 2테이블과 시간당 강도 보정 설계

### 4. [백엔드] 파생 지표 배치 + 동네 프로필 조회 API (Backend v0.26.0~v0.27.0)

- **v0.26.0 — `apps/metric/` 확장, 프로필 9,284행 + 어긋남 342,078행 / 33초**(재실행 멱등, `sum(gap)` 소수 6자리 동일).
  6구간 길이가 6·5·3·3·4·3시간으로 달라 **시간당 강도로 보정** — 보정 전엔 422개 동 중 375개가 `00_06`으로 뭉개진다.
  유형 판정은 `if/elif`가 아니라 규칙 객체 7개 리스트(Chain of Responsibility), 순서에 뜻이 있다
- 유형 분포(20262) **주거 251 · 먹자 55 · 업무 36 · 혼합 32 · 생활중심 25 · 대학가 23** — 분류 문서 실측과 ±6 이내.
  상식 검증 9/9(역삼1동·여의동 업무, 신촌동 대학가, 연남동 먹자…), 22분기 유형 불변 **80.1%**.
  상주인구 하한(p1 ≈ 2,400명)에 명동·소공동·삼청동이 걸려 혼합형으로 빠진 것이 업무형 40 → 36의 원인
- **발견 — 어긋남의 부호는 절대값이 아니라 상대 순위에 있다.** 업무형 카페 `06_11` gap은 -0.30이지만 6유형 중 1위.
  화면 문구는 "출근길에 매출이 몰린다"가 아니라 "다른 동네보다 아침 매출 비중이 높다"로 — 이후 진단·차트 설계의 전제가 됐다
- **v0.27.0 — `GET /profiles/{region_code}`** (분기 생략 시 최신, 404 `REGION_PROFILE_NOT_FOUND`). `myself`로 배선 검증.
  실DB 역삼1동 → `office`·`day`·"직장인구가 상주인구의 5.9배로 서울 상위 10%". 테스트 6건

### 5. [백엔드] 리포트 market 슬롯·상권 변화 라우터·지도 지표 계약 (Backend v0.28.0~v0.30.0)

- **v0.28.0 — AI 리포트 `market` 섹션을 슬롯 6종으로 고정**(한 줄 요약·동네 설명·고객 구성·시간대·주의점·확인할 것).
  도구 `get_neighborhood_profile` 신설(7 → 8종)로 슬롯마다 실측 공급원을 붙이고, LLM이 결측을 0으로 읽지 않게
  **`caveats`를 해당 동에만 조건부로** 넘긴다(직장 결측 11동·상주 하한·버스정거장 1위·아파트 시가). 테스트 9건
- **v0.29.0 — neighborhood BC 첫 라우터 `GET /commerce-changes?metric=operating_months`.** 적재 포트와 조회 포트를
  분리(ISP), 값 없는 동은 행을 만들지 않는다(0이면 "가장 빨리 닫는 동네"로 색칠된다). 실DB 422행, 31 / 117 / 206개월
- **v0.30.0 — `map-metric-contract.md` 성문화.** 라우터는 테이블 수가 아니라 화면 수요를 따르고, 계약은 단계구분도
  `{region_code, value}` / 상세 두 벌뿐. `GET /profiles?metric=` **파생 7종**을 extractor 테이블 7줄로 열었다(새 라우터 없음).
  `region_commerce_change` 읽기 변환이 두 곳이던 것을 orm_mapper 한 곳으로 통합

### 6. [프론트엔드] E2E 실백엔드 전환·동네 프로필·영업 지속 개월 (Frontend v0.15.1~v0.17.0)

- **v0.15.1** — 랜딩 도입 뒤 소실된 `scripts/` 2파일 복원, E2E의 목 데이터 전제 6건 제거(API 베이스 env, 실 경계 중심
  클릭, 리포트 상태 폴링, 리소스 타이밍 계측). 실 백엔드 상대 **8단계 전량 통과**(리포트 1,401자)
- **v0.16.0 — 사이드패널 동네 프로필 섹션.** 유형 이름·판정 근거·시간대 서사·근거 수치 5줄. `office`를 "낮 인구 우위형"으로
  부르기로 결정(가회동·한남동·청담동이 들어오므로 "업무 밀집형"은 틀린 말). 결측은 0이 아니라 "집계 없음". 테스트 21건
- **v0.17.0 — 지도에 "영업 지속 개월" 추가.** 지표 → 원천 레지스트리 `metric-sources.ts`(Strategy)로 `/metrics`와
  `/commerce-changes` 원천 분기를 호출자에서 숨기고, 질의 키에서 업종·연도를 빼 중복 캐싱 제거. 테스트 10건

### 7. [통합] T0 — 채팅 관문 전환 로드맵과 브랜치 합치기

- **로드맵 `plans/2026-09-23-chat-first-roadmap.md`** — 척추 ⓪관문 → ①한 줄 진단 → ②무대 → ③계획 → ④조달·준비 →
  ⑤AI 리포트. 태스크 그룹 = 브랜치(`feat/intent-gate`·`feat/map-stage`·`feat/finance`), 그룹당 설계서 하나
- **T0-1** 랜딩 25파일 커밋 · **T0-2** `feature/analysis-api` 병합(충돌 8파일 전부 양쪽 추가형, 76파일 1,800줄,
  alembic head 통합) — 프론트 번호 충돌은 우리 쪽 4항목을 **v0.15.0·v0.15.1·v0.16.0·v0.17.0으로 재번호** ·
  **T0-3** main 푸시(73cc401) + 8201 재기동 · **T0-4** `docs/erd.md` §6를 실DB 기준 **36테이블**(+15: commerce 3·
  neighborhood 8·metric 파생 2·agent 2)로 갱신

### 8. [백엔드·프론트엔드] T1 관문 — intent BC와 랜딩 입력창 (Backend v0.31.0 / Frontend v0.18.0~v0.18.3)

- 설계서 `chat-first-direction.md`(T1-0). **intent BC는 ERD 테이블이 없다** — §12 "1 테이블 = 1 프랙탈"의 의도적 예외,
  파싱은 상태가 없다. `POST /intent` 두 형태(`text` / `region_code`+`industry_id`)
- **추출기 체인**(Region → Industry → Budget → LLM 폴백, Chain of Responsibility). 동 이름은 정확 이름 + 기본 이름
  둘로 색인해 "역삼동" → 역삼1동·2동 후보로 되묻고, "신사동"은 후보 **4개**(강남·관악·은평×2). 예산은 대구 파서 이식
  (`1억 5천` → 150,000,000). LLM 폴백은 region 결측이고 후보도 없을 때만 1콜 — Gemini 최소 deadline이 10초라 설계의 3초를 수정
- **한 줄 진단은 LLM이 아니라 어휘 테이블 조립.** 정점은 gap이 아니라 매출 강도 최대 구간. 실호출 "홍대 근처 미용실" →
  서교동(LLM), "서교동은 먹자·나들이형이고, 미용실은 오후(14~17시)에 돈이 돕니다." 테스트 38건 추가, 전체 **373 통과**
- **Frontend v0.18.0 — `features/intent-gate/`.** 상태 기계 idle → pending → clarifyRegion → clarifyIndustry → done,
  후보 칩이 주 경로, 우회로 둘("지도에서 고를게요" / "동네부터 볼게요"). `MapState.budget` 추가, mock `/api/mock/intent`,
  E2E `[0/8]` 관문 단계. 테스트 20건 추가 → **133/133**
- **패치 3건** — v0.18.1 Pretendard 패키지 `@import`를 Tailwind v4 리졸버가 못 풀어 홈·`/map` 500 → `layout.tsx` JS import;
  v0.18.2 E2E 5단계 CTA가 패널 아래로 밀려 클릭 빗나감 → `scrollIntoView`; v0.18.3 업종 필드가 `select`로 바뀐 것을
  E2E가 못 따라옴. 이후 **E2E 8단계 전부 통과**

### 9. [백엔드·프론트엔드] T2 무대 — 유형 단계구분도·컨트롤바·패널 서사·어긋남 두 선 (Backend v0.32.0 / Frontend v0.19.0~v0.21.0)

- 설계서 `map-stage-design.md`(T2-0). 백엔드 v0.32.0은 네 조각(1/4~4/4)을 한 항목에 담았다
- **T2-4 `GET /hour-gaps`** — 동×업종×분기 한 객체에 6구간 `{footfall_intensity, sales_intensity, gap}`. 분기 생략 시
  최신(매출 원천은 20254까지라 프로필 20262와 다르다), 없으면 404 `HOUR_GAP_NOT_FOUND`. 테스트 7건
- **T2-1 `GET /profiles/types`** — 범주형은 숫자 계약과 경로를 나눈다(`[{region_code, type_code}]`), 포트 변경 없음.
  **Frontend v0.19.0 유형 단계구분도** — `MetricSource`를 `numeric | categorical` 판별 합집합으로, 범주 팔레트 라이트/다크
  두 벌(**주거형이 60%라 가장 옅게**), 기본 지표를 동네 유형으로. 테스트 15건 → **148/148**
- **T2-2 Frontend v0.20.0 컨트롤바 두 무리** — 동네 `[유형·심야 체류·음식/유흥 비중·영업 지속 개월]`(동×분기) /
  업종 `[폐업률·성장률·점포수]`(업종×연도). 무리가 곧 모드라 셀렉터가 분기/연도로 정직하게 따라간다. 테스트 17건 → **165/165**
- **T2-3** 백엔드 — `region_profile_quarter`에 4블록 강도 컬럼(배치 재실행 32초, 9,284행 전부, 정점 불일치 0건;
  컬럼이 늘며 `_BATCH` 4,000 → 3,000으로 파라미터 한도 회피) + `GET /commerce-changes/{region_code}` 상세(서울 평균 동봉,
  별도 baseline 포트). **Frontend v0.21.0 패널 서사 재배열** — ①어떤 동네인가 → ②하루 흐름(4블록 SVG 막대) →
  ③업종 시간대(유동·매출 **두 선**, gap 하나를 그리지 않는다) → ④얼마나 버티나("110개월 · 서울 118") → ⑤업종 실적,
  sticky CTA. 테스트 26건 → **191/191**
- **T2-5** — `get_neighborhood_profile` 도구 결과에 `benchmarks`(서울 평균 + 같은 유형 중앙값·동 수) 주입, 프롬프트는
  "비교 기준 없는 절대값 서술 금지". 역삼1동 심야 0.639는 같은 유형 중앙값 0.732보다도 낮다 — 리포트가 이제 그 문장을 쓴다.
  전체 **397 passed**. T2를 main에 머지하고 `feat/finance` 분기

### 10. [설계] T3-0 계획 설계서 — finance BC

- `finance-plan-design.md` — **테이블 없는 BC 두 번째**(`apps/finance`, 계획 초안은 `sessionStorage`). 대구 분화본
  `engine.py`(80줄, 결정론)를 산식 변경 없이 이식해 `POST /finance/simulate`(입력 13필드) — 계산은 코드가, 설명만 AI가
- **`GET /finance/prefill?region&industry`가 새 것** — 월매출 = `sales ÷ store ÷ 3` 실측(예: 역삼1동 카페 400곳 →
  29,439,538원), 임대료는 권역 근사, 금리는 ECOS. 값마다 `basis`·`caveat`를 붙인다. 헤드라인은 `funding_gap`이 아니라
  **`external_funding_need`**(부족액 0원 함정 회피). 예정 버전 Backend v0.33.0~ / Frontend v0.22.0~.
  T3-1 구현은 착수했으나 아직 커밋 없음

### 다음 작업

- [x] **T3-1** `apps/finance` 엔진 이식 + `simulate`·`prefill` (BE v0.33.0) → **T3-2** `/plan` 프리필 폼·네 갈래 결과 (FE v0.22.0) → **T3-3** agent `calculator`가 finance 도구 흡수 — 9/24 새벽 완료(BE v0.33.0 (2/2), FE v0.22.0~v0.22.1)
- [x] **T4** 조달·준비 — 조달 필요액 → `funding_program` + ECOS 금리 → "확인할 질문", 상담 준비자료 — 9/24 완료(BE v0.34.0·v0.35.0, FE v0.23.0)
- [ ] `docs/api.md` 갱신 — `/analysis` 3종·`/stores` 주소 필드에 더해 오늘 신설된 `/profiles`·`/profiles/types`·`/commerce-changes`·`/hour-gaps`·`/intent`까지 전부 미반영
- [x] 도커 백엔드 이미지 갱신(9/24 v0.35.3 재빌드) · 두뇌 채택(9/24 혼합 배선으로 확정) · RAG 평가셋 검수(9/24 완료, 11건 재판정만 남음) — `funding_program_industry`, Vercel 프로젝트는 이월
- [ ] 상권명 → 동 매핑("테헤란로"가 LLM에서 null) — `intent_log` 승격 시점에 되묻기 비율과 함께 판단

## 2026-09-24

로드맵의 남은 두 층 **T3 계획 → T4 조달·준비**를 새벽에 마감해 main에 올리고, 낮에는 **실DB 기준 정본 `docs/STATUS.md`**를
세우며 낡은 기록 때문에 틀렸던 전제 4건을 바로잡았다. 그 과정에서 드러난 결함 3건(테스트가 dev DB를 쓰던 것·학원
폐업률 0·도커 이미지 낡음)을 전부 수정했고, 저녁부터 밤까지는 **RAG 평가셋을 50건 → 200건**으로 키우며 검수 CLI·
Claude 1차 판정·단일 판정 기준·Hit@5 전환까지 한 번에 세웠다. Backend **v0.33.0 (2/2)~v0.37.1**(13항목),
Frontend **v0.22.0~v0.24.1**(5항목). 설계서 2건(`funding-prep-design.md` 신설, `finance-plan-design.md` 실측 반영).

### 1. [백엔드·프론트엔드] T3 계획 — `/plan` 화면과 리포트 `calculator` 도구 (Backend v0.33.0 (2/2) / Frontend v0.22.0~v0.22.1)

- **Frontend v0.22.0 — `/plan` "그래서 얼마가 필요한가"** (`features/plan/`). 관문·사이드패널에서 `region·industry·budget`을
  받아 실측 프리필 → 서버 계산 → 최초안/현재안 비교. 값마다 **프리필 배지**("실측 · 20254 · 603점포" / "R-ONE 강남 권역 ·
  2026Q2" / "ECOS · 202607")로 출처를 보인다. 헤드라인은 `external_funding_need`(자기자본 외 조달 필요) — 부족액 0원이어도
  상담 주제는 남는다는 원칙을 **"충분합니다" 류 문구 금지 테스트**로 고정. 계획 초안은 `sessionStorage`(`beyondfacade.plan.v1`),
  첫 성공 계산이 최초안. mock 라우트 전용 TS 엔진이 파이썬 엔진과 시연 사례 2건에서 같은 수(BEP 900만·조달 3,160만·부족 660만)임을
  테스트로 고정. 테스트 32건 → vitest **224/224**
- **Backend v0.33.0 (2/2) — 도구 `run_finance_simulation`** (8종 → 9종). 13개 입력을 finance BC 유스케이스에 그대로 넘기고
  결과 표를 JSON으로 돌려준다 — **계산은 finance BC가, LLM은 인용만.** `RegionFactsPort`에 얹지 않고 별도 `FinanceFactsPort`(ISP).
  SSE `agent_status` 어휘가 프론트 `AgentName` 합집합에 묶여 있어 stage는 새 값이 아니라 `funding`. 프롬프트에
  `[calculator 섹션 출력 계약]`(표 수치 재계산 금지·헤드라인은 조달 필요·부족액 0이어도 "충분" 금지)
- **Frontend v0.22.1 — E2E `[9/9]` 두 함정.** 13필드 폼이라 "계산하기"가 뷰포트 밖(top 1356px / 900px)이라 클릭이 조용히 빗나감 →
  `scrollIntoView`. 프리필 단언이 원 단위(`50000000`)를 기다렸는데 폼 금액 입력은 **만원 단위**(내부 상태·API만 원) → 단위 수정.
  랜딩·analysis-api 병합 뒤 E2E가 드러낸 스크립트 회귀 3건째 — 전부 제품이 아니라 스크립트가 변화를 못 따라온 경우

### 2. [백엔드] 에이전트 루프 — 벽시계 예산 180초 + LLM 장애 시에도 리포트를 낸다 (Backend v0.33.1)

- **9분씩 돌다 빈 리포트를 내던 것.** `_MAX_TURNS=12`는 턴만 세고 시간을 세지 않는다. 로컬 `gemma4:12b`는 한 턴 30~60초(입력
  ~21k 토큰)라 도구를 맴돌며 12턴을 다 쓰면 9분을 넘기고 클라이언트가 먼저 끊는다. 실측 대조 — 정상 41.8s·45.9s·98.5s(997·1,302·275자)
  vs 실패 **534.7s·558.4s(0자)**. 모델을 미리 상주시켜도 재현 — 콜드 로드가 아니라 루프가 원인. 도구 수집에 **벽시계 예산 180초**를
  두고, 넘기면 "지금까지 모은 것만으로" 마무리 턴을 강제한다. 시계는 생성자 주입이라 테스트가 기다리지 않는다
- **LLM 호출이 터지면 리포트가 아예 안 뜨던 것.** `_chat`에 예외 처리가 없어 120초 타임아웃이 제너레이터를 죽였고 화면은 `NO_ARTICLE`로
  남았다. 수집 턴이 터지면 마무리로, 마무리까지 터지면 폴백 섹션으로 — **스트림은 항상 리포트로 끝난다.** 벽시계·어댑터 타임아웃·예외
  처리는 각각 다른 구멍을 막는다. 테스트 4건 → **433 passed**
- 함께 관찰: 같은 도구 반복 호출(`get_neighborhood_profile`×2), 업종 인자에 서비스업종코드 삽입 등 도구 9종·계약 2블록으로 늘어난 뒤의
  헤맴 — 프롬프트·도구 다이어트는 별도 과제

### 3. [설계·백엔드] T4 조달·준비 — 후보 공고 필터·확인할 질문 (T4-0 설계서 / Backend v0.34.0)

- 설계서 `funding-prep-design.md`(T4-0, 128줄) — 결과물은 상품 목록이 아니라 **조정한 계획 + 후보 + 확인할 질문**
- **`GET /funding/candidates?industry=&need=&stage=`** — 서울 창업자에게 해당하는 미만료 공고 상위 8건, 결정론 필터, LLM 없음.
  **원천이 시도 어휘를 두 벌 섞어 쓴다** — `전남광주`(통합) 512건과 `광주`·`전남`(282·281건)이 공존해 전국 공고의 지역 태그가 16개거나 17개.
  태그 수만 세면 353건이 "서울 전용"으로 오분류 → `전남광주`를 펴서 17개 기준. 설계서의 73/45는 이 오분류 수치라 **70/490으로 정정**.
  소관기관이 서울 밖 지자체면 태그와 무관하게 제외(과천시 이자차액보전류 26건). 만료는 `is_expired` 플래그와 `deadline`을 둘 다 본다 —
  실제로 오늘 기준 9월 초 마감 공고가 섞여 나왔다. 정렬: 서울 전용 → 전국, 우선 분야(금융·창업·경영), 창업 단계 가점, 마감 임박순
- **`POST /finance/questions`** — 계획 수치에서 결정론으로 만드는 초안 **11규칙**(gap 2 · assumption 5 · procedure 4+), 규칙 객체 리스트
  (Chain of Responsibility). 모든 질문이 `basis`를 갖는다. **요청에 계산 결과를 받지 않고 서버가 `input`으로 다시 계산**(클라이언트 계산
  불신, `simulate`와 같은 원칙). 후보 공고 제목은 요청으로 받는다 — finance BC가 funding BC를 직접 읽지 않는다
- 테스트 51건 → **487 passed**. 실호출 `stage=pre` 8건 전부 서울특별시 주관, 시연 사례 + 후보 3건 → 질문 12개

### 4. [백엔드] 리포트 두뇌 혼합 배선 + `funding` 절 결정론 후보 (Backend v0.35.0)

- **기본 Gemini, 실패 시 로컬 폴백** — 9/22 두뇌 비교(5섹션 완성률 gemma4 50% vs gemini-2.5-flash 90%, 소요 39.9s vs 17.4s)가 근거.
  당시는 도구 7종·계약 0블록이었고 지금은 도구 9종 + 계약 2블록이라 로컬 입력 토큰이 29,547까지 불어 5섹션 전부 폴백 문구인 실행을
  관측했다. 로컬을 버리지 않는 이유는 **키 없는 환경(도커 8200)과 쿼터 소진·일시 장애**
  - `fallback_llm_adapter.py` — `LLMGatewayPort`를 구현하고 primary·secondary를 감싸는 한 겹(Decorator). **폴백하는 경우**: 어댑터 생성
    실패(키 없음)·호출 예외(인증·429·타임아웃). **폴백하지 않는 경우**: 정상 응답인데 내용이 빈약한 것 — 그건 장애가 아니라 품질
  - 키 유무는 `GeminiLLMAdapter` 생성이 던지는 `ValueError`로만 판정 — 키 값을 읽지도 로그에 남기지도 않는다. `model_name`은 실제로
    답한 쪽을 가리켜 `analysis_report.model`에 폴백 사실이 남는다. 새 SSE 이벤트 타입 없음
  - 실호출: **20초 · 5섹션 전부 실제 내용** · 도구 6회 · 인용 11건, 직전 gemma4 실행은 본문 136자
- **`GET /funding` 목록이 마감 지난 공고를 보여줄 수 있던 것** — `is_expired`는 일 배치(05:10)가 갱신하므로 최대 하루 낡는다.
  후보 필터가 쓰는 `is_past_deadline` 방어를 목록에도. **크론 점검**: 만료 배치는 정상(오늘 05:10 510건 처리), T4-1이 본 것은 배치 직전 창
- **(2/2) 도구 `get_funding_candidates`** (9종 → 10종) — v0.34.0 결정론 필터를 `FundingFactsPort` 뒤에서 호출. RAG `search_funding`은
  남긴다(유사도는 "비슷한 글", 이쪽은 지역·대상·마감의 확정 판정). **필수 인자가 없다** — 억지 required를 세우면 스키마가 거짓말이 되고
  LLM이 값을 지어낸다. 인용은 `fact` 등급 + 원문 링크, 게이트웨이가 `disclaimer`("자격 확정이 아니라 해당 가능성")를 동봉.
  실호출 cafe·조달 필요 3,160만·`pre` → 후보 8건 전부 서울특별시 주관. 테스트 15건 → **504 passed**

### 5. [프론트엔드] `/plan` ⑤ 조달·상담 준비 + E2E `[10/10]` (Frontend v0.23.0)

- 새 feature를 만들지 않고 `features/plan/`에 이어 붙였다 — 같은 계획 흐름. `profile-form`(창업 단계 5항, **`null`"아직 묻지 않음"과
  `"unknown"`"모른다"를 구분** — 라디오 기본 선택 없음), `candidate-cards`(후보 8장, "자격 확정이 아니라 해당 가능성" 고지 고정),
  `question-list`(서버 초안을 인라인 편집·삭제·순서 변경·추가, **편집본이 정본**이라 재조회가 덮지 않는다), `prep-sheet` + Markdown 복사 /
  질문만 복사 / 인쇄 — **숫자는 서버 결과 그대로, 여기서 다시 계산하지 않는다**
- `plan-draft` v2 — 동네·업종이 바뀌면 후보·질문은 버리고 **사람이 쓴 것(변경 이유·창업 단계)은 남긴다.** v1 초안은 되살리지 않는다
- **문구 결정** — 은행에 보내는 것처럼 보이는 전송·제출·신청·예약 버튼을 두지 않음을 테스트로 고정. 금지 문구 스캔("충분합니다"·"신청 완료"·
  "승인되었")을 feature 전체 소스에 — 처음엔 규칙을 적어둔 주석을 잡아서 주석을 걷어낸 뒤 보도록 수정
- 테스트 31건 → vitest **266/266**. E2E `[10/10]` 추가 — 관문부터 준비자료까지 **전 구간 통과**: 리포트 4,207자 · 조달 필요 348만 원 ·
  후보 8건 · 질문 8개 · 준비자료 2,900자

### 6. [백엔드] SGIS 불량 주소가 배치 전체를 죽이던 것 + 파이프라인 완료 확인 (Backend v0.35.1)

- `errCd -200`(주소 형식 불량)을 토큰 만료와 같은 재시도 대상으로 분류한 뒤 `RuntimeError`를 던졌고 인터랙터는 `geocode()`를 감싸지 않는다 —
  **불량 주소 한 건이 남은 전량을 중단**. 키 검증 중 세 번째 주소에서 실호출 재현. `-200`을 `-100`(검색결과 없음)과 같이 건너뛰기로, 재시도는
  인증·토큰 오류(`-401`·`-1001`)만. 회귀 테스트가 호출 수 1까지 단언(재시도 낭비 방지). **505 passed**
- **확인 사항 — SGIS 파이프라인은 이미 완료 상태였다.** `docs/HANDOFF.md` 9/17판의 "차단 2건"은 낡은 기록. 실측 academy 25,554 중 좌표
  25,504(99.8%), real_estate 25,435 중 25,299(99.5%). 남은 미좌표는 **주소가 아예 없는 행**(학원 50 중 46, 부동산 136 중 134)과 폐업 업소

### 7. [프론트엔드] 지표별 데이터 보유 범위 — 빈 지도가 되는 조합을 제안하지 않는다 (Frontend v0.24.0)

- `metric-coverage.ts`를 단일 원천으로 — 컨트롤바 연도 옵션이 현재 (업종, 지표)의 보유 범위만 그리고, 범위 밖 시점은 가장 가까운 유효 시점으로
  당긴다(`clampToCoverage`, 멱등). URL로 직접 들어온 조합도 보정
- **mock이 실 API의 빈 응답을 흉내 내지 않던 것(§15 위반)** — `/api/mock/metrics`가 어떤 조합에도 427행을 줬다. 실 API는 스냅샷 업종
  (어린이집·편의점)에 관측 연도의 점포수만 준다. 픽스처가 같은 커버리지 모듈을 쓰게 해 같은 공백을 재현
- **낡은 주석 정정** — "commerce 계열은 20254까지라 마지막 두 분기가 빈 지도"는 사실이 아니다. 실측 동네 지표 4종 전부 20211~20262 22분기 ×
  422행. 20254까지인 것은 매출·점포·어긋남 테이블(패널 차트, 이미 404 + 안내). **실제 공백은 분기 범위가 아니라 (업종, 지표) 쌍**에 있어
  백엔드 커버리지 엔드포인트를 만들지 않았다(`map-metric-contract` §6 전환 조건 미달)
- 테스트 17건 → vitest **280/280**(64파일)

### 8. [문서] `docs/STATUS.md` — 실DB 기준 현재 상태 정본

- 문서·메모를 믿지 않고 **DB·크론 로그·git을 직접 재서** 만든 단일 정본. 오늘 하루에만 낡은 기록 때문에 서브에이전트에 틀린 전제를 세 번 넘겼다.
  `HANDOFF.md`(9/22판)·`RESUME-260923.md`를 대체. 36테이블 약 1,050만 행, 크론 6종 전부 정상, API 15라우터, 프론트 4라우트·feature 5개
- **낡은 기록으로 틀렸던 것 4건** — "SGIS 키 부재로 지오코딩 차단"(실제 9/22 완료·병합), "RAG 코퍼스 전량 Q4"(실제 7,883건 전량 fp16),
  "`operating_months` 20254까지 → 빈 지도"(실제 22분기 전량), "만료 크론이 안 돈다"(크론 정상, **테스트가 되돌린 것**)
- 규칙: 재개·위임 전에 문서가 아니라 §1의 방법으로 DB·로그·git을 먼저 잰다. 문서는 결과지, 원천이 아니다

### 9. [백엔드·프론트엔드] 결함 3건 수정 — 테스트 DB 격리·학원 폐업률 NULL·도커 재빌드 (Backend v0.35.2~v0.35.3 / Frontend v0.24.1)

- **v0.35.2 — 테스트가 dev DB를 직접 쓰던 것.** `conftest.py`가 없어 `session_scope`를 여는 테스트가 `.env`의 dev DB(5434)에 썼다.
  `test_funding_expiry`의 `refresh_expirations(2026-09-07)`가 9/7 이후 마감 행의 `is_expired`를 전부 되돌려 **510 → 0 재현** — T4-1이 "크론이
  안 돈다"고 오판한 원인. 대구 `conftest.py` 이식: `beyondfacade_test` 생성 → `DATABASE_URL` 강제 → `alembic upgrade head` → `seed_all()`,
  개발 DB를 가리키면 assert 중단. 빈 DB에서 실패하던 마이그레이션 2건 손질(`vector` 확장 생성, `industry` 비었을 때 bulk_insert 건너뛰기).
  DROP 후 `pytest` 한 번에 **505 passed (7.05s)**, dev expired 510 유지, 재실행 멱등
- **v0.35.3 / FE v0.24.1 — 학원 폐업률 0.0이 값처럼 보이던 것.** 서울 학원 API(OA-20528)는 폐원일자를 주지 않아 `close_date`가 전부 NULL인데
  집계가 그 0건을 폐업 0으로 세어 학원 3,388행에 `closure_rate=0.0`. 어린이집·편의점은 같은 이유로 NULL이라 업종 간 비일관. 게이트웨이가
  폐업 이력 없는 원천(`_NO_CLOSURE_HISTORY={"academy"}`)의 `close_count`를 None으로 주고 비율도 None. 재빌드로 학원 3,408행 전부 NULL,
  8업종 불변. 프론트는 `NO_CLOSURE_HISTORY_INDUSTRIES`(스냅샷 2종 + academy)로 배너·사이드패널·mock을 맞추되, 학원 점포수는 전 연도에
  있으므로 스냅샷 집합과는 별개 규칙
- **도커 8200 재빌드** — 9/23 22:40 이미지가 25커밋 낡아 `/intent`·`/finance`·`/hour-gaps` 등이 없었다. v0.35.3 기준 재빌드, openapi 39 paths.
  main이 전진하면 다시 낡는다 — 배포 전 재빌드가 규칙

### 10. [백엔드] RAG 평가셋 검수 파이프라인 — 사람 검수 CLI·Claude 1차 판정·기준 단일화 (Backend v0.36.0~v0.36.2)

- **v0.36.0 — `review_evalset`** — `sheet`가 candidate 50건을 공고 카드(제목·기관·대상·분야·기간·요약·URL)와 함께 `rag_evalset_review.md`로
  뽑고, 사용자가 VS Code에서 `판정: O/X`(질문 줄 수정 가능)를 적으면 `apply`가 jsonl에 반영. 판정 기호 → 행 변환은 Strategy 테이블. 테스트 6건
- **v0.36.1 — `judge_evalset`** — Claude Opus 5(effort low, 구조화 출력 `Judgment{verdict,reason,better_question}`)가 O/X를 시트 판정란에
  `판정: O  # claude: 이유 | 제안: …`로 기입. jsonl은 건드리지 않고 **사람이 시트에서 뒤집은 뒤 `apply`**하는 구조. `anthropic==1.8.0` 추가,
  키는 `backend/.env`(운영 경로엔 쓰지 않음). 1차 판정 **O 40 / X 10** — X 사유는 전부 "너무 일반적이라 수십 공고가 정답" 또는 지역 조건 누락.
  confirmed 40건 본지표 fp16 Recall@5 0.950·MRR 0.868 / ollama 0.950·0.838
- **v0.36.2 — 판정 기준을 하나로 통일.** 사람 검수가 Claude 판정에서 불일치 10건을 찾았다 — 통합공고 3건(4·8·13)은 같은 성격의 12·17을 X로
  두면서 O, 지원방식 누락 4건, 조건 누락 1건, 이웃 행 불일치 2건. 기준: **"질문에 담긴 정보만으로 이 공고가 다른 유사 공고보다 우선적으로 정답이
  될 수 있어야 O, 여러 공고가 자연스럽게 정답이면 X. 통합공고도 예외 없음."** 이 문장을 `judge_evalset` 시스템 프롬프트에 그대로 넣었다.
  최종 **confirmed 30 / rejected 20**, 본지표 **fp16 Recall@5 1.000·MRR 0.923 / ollama 1.000·0.900**(일반적 질문이 빠지며 상승)

### 11. [백엔드·데이터] 평가셋 200건 확장 → 외부 판정 → Hit@5 전환 (Backend v0.37.0~v0.37.1)

- **v0.37.0 — `generate_evalset` 재작성.** 평가셋에 이미 있는 chunk_id는 건너뛰고 이어 붙인다(결정적 순서), funding은 **미만료 공고만**(검색이
  만료를 제외하므로 정답이 될 수 없다), `--source-type news` 지원. 생성기는 Strategy(`OllamaGemmaGenerator`·`ClaudeGenerator`), 시트는 기존
  판정을 덮지 않고 이어 붙이며 뉴스 카드(언론사·수집 키워드·보도일·요약) 추가. gemma3:12b로 funding 110(102초) + news 40(29초) → **200건**
  (candidate 150). Claude 생성은 `.env`에 키가 빠져 인증 실패 → ollama로 대체. 테스트 4건
- **51~200번 질문을 Claude(세션)가 문서 카드를 읽고 직접 다시 썼다**(단일 기준 적용, 24~45자) — gemma3 생성분 대체, 1~50 판정 보존. fp16
  자체 점검 top-5 142/150, 1위 123/150 — 놓친 8건은 전부 뉴스(같은 사건 기사 여럿). 같은 사건 기사가 3~7건인 항목 8건엔 "작성 메모"
- **외부 판정 2종 수신 — Claude Fable·ChatGPT 둘 다 O 141 / X 9, X 집합 동일**(155 인천 누락 + 뉴스 동일 사건 중복 8건). 그대로 반영 →
  confirmed 171 / rejected 29, fp16 Recall@5 0.971·MRR 0.899. 원천별(fp16) funding 139건 R@5 1.000·MRR 0.973 / **news 32건 R@5 0.844·MRR 0.578**.
  외부 지적 2건 — 수치·고유명사가 정답을 누설하는 질문 10건, 뉴스 `matched_keyword`는 수집 키워드일 뿐 NER 태그가 아님(평가엔 무관)
- **v0.37.1 — 결정 2건 실행.** ① **Recall@5 → Hit@5** — relevant_ids를 "이 중 하나라도 맞으면 정답"인 동치 집합으로. 뉴스는 같은 보도자료를
  받은 기사가 3~51건(올리브영 남포 51건·신중앙시장 착공 34건·오세훈 추석 15건)이라 단일 정답이면 같은 사건의 다른 기사를 1위로 올려도
  틀린 것이 됐다. 단일 정답 행에선 두 지표가 같아 이전 수치와 비교 가능. 뉴스 40건 중 29건을 다중 정답으로 묶고 보류 X 8건 → O.
  **뉴스 MRR 0.578 → 0.865** — 성능이 아니라 측정 왜곡이었다. ② 수치 과다 질문 10건 + 155번을 지원 유형·대상 조건 수준으로 완화 →
  **candidate 11건 재판정 대기**(`data/eval/재판정_요청_11건.md`로 외부 판정용 정리 — 춘천 4건·괴산 3건·관광 인센티브 14건 경쟁 그룹 명시).
  완화 후에도 fp16 top-5 11/11, 1위 10/11
- 현재 **confirmed 169 / rejected 20 / candidate 11**, 본지표 **fp16 Hit@5 1.000·MRR 0.945 / ollama 1.000·0.941**. 원천별 fp16 — funding 129건
  MRR 0.971, news 40건 MRR 0.865. 다음 개선 후보: 뉴스 corpus가 보도자료 복제 대부분이라 **색인 전 사건 단위 dedupe**

### 다음 작업

- [x] 평가셋 완화 질문 **11건 외부 재판정**(`재판정_요청_11건.md` → 판정 md 수신 → `review_evalset apply` → 본지표 재산출) — 9/25 완료(전부 O, 2차 완화 6건도 O, 검수 종료)
- [x] 뉴스 검색 개선 — 색인 전 사건 단위 dedupe, 뉴스 본문 지역 추출(`matched_keyword`는 지역 신호가 아님) — 9/25 v0.38.0 검색 시점 같은 사건 접기로 1차 처리, 본문 지역 추출·수집 시 클러스터링은 이월
- [ ] 리포트 프롬프트·도구 다이어트(도구 10종·계약 3블록으로 로컬 입력 29.5k 토큰) — v0.33.1에서 관찰한 도구 반복 호출·업종 인자 오류
- [ ] `docs/api.md` 갱신 — `/profiles`·`/hour-gaps`·`/commerce-changes`·`/intent`·`/finance` 3종·`/funding/candidates` 전부 미반영
- [ ] 이월: `funding_program_industry`(T4-3 공고 업종·한도 구조화), 서울신보·금감원 금융상품 정본, Vercel 프로젝트, 인구 2026.07분, 상권명 → 동 매핑

## 2026-09-25

9/24 밤부터 이어진 RAG 평가셋 검수를 **confirmed 180 / rejected 20 / candidate 0**으로 마감하고, 평가에서 드러난
뉴스 중복 문제를 검색 시점 **같은 사건 접기**로 처리했다. 프론트엔드는 대구 분화본 대조에서 남아 있던 예시 질문 칩을
이식했고, `docs/STATUS.md` 정본에 배포·운영 잔여와 대구 대조 결과를 기록했다. Backend **v0.38.0**, Frontend **v0.25.0**.

### 1. [데이터] RAG 평가셋 검수 종료 — confirmed 180 / rejected 20

- 9/24 완화한 11건의 외부 재판정이 **전부 O** → confirmed 180, fp16 Hit@5 1.000·MRR 0.946 / ollama 1.000·0.942
- 같은 기준으로 수치가 2개 이상 남은 9건 중 6건(78·104·105·120·137·138)을 2차 완화 → 외부 재판정 **전부 O**.
  131·132·141은 같은 시의 유사 공고와 수치로만 갈리는 항목이라 그대로 유지
- 최종 **confirmed 180 / rejected 20 / candidate 0**, 본지표 fp16 Hit@5 1.000·MRR 0.949 / ollama 1.000·0.946.
  검수 시트·jsonl에 반영이 끝난 외부 판정 원문 md 2개는 저장소에서 제거(원문은 보관하지 않음)

### 2. [백엔드] 뉴스 검색 결과 같은 사건 접기 (Backend v0.38.0)

- `same_event_collapser` 순수 함수 — 제목 토큰 Jaccard ≥ 0.3이고 보도일 차 ≤ 3일이면 같은 사건으로 보고 점수 높은
  기사만 대표로 남긴다. `RagSearchInteractor`가 source_type별 Strategy 테이블로 **뉴스만 top_k×10을 가져와 접은 뒤**
  top_k를 돌려주고, 공고는 차수·연도별 공고가 서로 다른 문서라 접지 않는다. 색인·스키마 변경 없음 — 증분 크론에서
  대표가 흔들리지 않고, 에이전트 `search_news` 도구가 그대로 혜택을 본다
- 실측(평가셋 뉴스 40문항, fp16) — top-5 중 같은 사건 기사 **평균 2.98 → 2.00**, 2건 이상 점유 27 → 18문항,
  5건 전부 같은 사건 12 → 4문항. Hit@5 40/40·1위 31/40 유지, 본지표(confirmed 180) 변화 없음
- 더 공격적인 규칙은 전부 Hit을 깎아 기각 — 제목 J 0.2(Hit 38/40), 앵커 토큰 2개 공유(잘못 합침 231 → 587),
  히트 간 임베딩 코사인(클러스터 내부 중앙값 0.848 vs 외부 p90 0.916으로 분리 불가), 요약문 J OR(Hit 38).
  남은 5/5 4문항(신중앙시장 착공·제주 성수·올리브영 남포·부산 추경)은 제목 표현이 제각각인 대형 보도자료라
  어휘 규칙으로는 못 잡는다 — 다음 단계는 수집 시 사건 클러스터링
- 테스트 7건(접기 순수 함수 5 + 인터랙터 2), 전체 **528 passed**

### 3. [프론트엔드] AI 분석 폼 업종별 예시 질문 칩 (Frontend v0.25.0)

- `features/agent-report/lib/example-questions.ts` — 10업종 × 3개. 칩을 누르면 추가 질문 입력칸을 그 문구로 채우고
  첫 문구가 placeholder. 업종을 바꾸면 칩은 바뀌지만 이미 적은 질문은 지우지 않으며, 미등록 업종은 일반 문구 1개로 폴백
- 대구 분화본의 구조를 이식하되 문구는 리포트 5개 섹션(판정·상권·충격·자금·계산)이 답할 수 있는 축으로 다시 썼다 —
  여기 에이전트는 finance 도구가 있어 손익분기·월세 계산 질문도 예시에 넣었다(대구는 제외했었음)
- 테스트 7건(lib 4 + 폼 3) → vitest **289 passed**, `tsc` clean

### 4. [문서] STATUS §4-6·§4-7 — 배포·운영 잔여와 대구 분화본 대조

- **앱 실배포가 없다.** Vercel 계정에 이 앱 프로젝트가 없고, 백엔드 공개용 Cloudflare 터널은 compose 프로필만 있을 뿐
  `TUNNEL_TOKEN`이 비어 있다. `beyondfacade.cloud`는 GitHub Pages 문서만 응답한다. 배포하려면 Vercel 프로젝트 신설 +
  `NEXT_PUBLIC_API_BASE` → 터널 도메인 + 터널 토큰 발급 + `cloudflared` 기동. 현재 서비스는 로컬(3200 → 8201)에서만 돈다
- 어린이집·편의점 폐업률은 원천이 폐지 시설을 주지 않아 월간 스냅샷 소실(`last_seen_on` 정지)로만 산출 가능한데,
  관측일이 9/21 1회뿐이라 몇 달 누적 뒤 산출 방식을 정한다(시간 대기)
- **대구 분화본 대조** — 설계서가 정한 이식 범위(관문 구조·파서·엔진·상담 준비자료)는 T1~T4로 전부 끝났다. 의도적으로
  안 가져온 것(위험도 점수·랜드마크 사전·상품 매칭 등)은 설계서·로드맵에 근거가 있다. 여기서 아직 결정이 없는 것 3 —
  실배포(대구 런북 `deploy-vercel-cloudflare.md`가 그대로 쓸 만하다), 모바일 지도(`map-explorer`에 반응형 분기 0개),
  예시 질문 칩(→ 오늘 FE v0.25.0으로 해소). 정리 대상: 파일 0개인 빈 BC 디렉터리 2(`ontology`·`dummy`), 소비처 없는 `tobacco` BC
- 로드맵 T5(fp16 재색인·평가셋 검수·SGIS 키)는 전부 끝났고, HANDOFF의 "포스트MVP 9건"은 FE v0.14.4에서 전부 처리됐음을 코드로 대조
- 사용자 결정 대기: 병합된 브랜치 2개(`origin/feature/analysis-api`·`feature/frontend-mvp`) 삭제 여부,
  AWS G 인스턴스 쿼터 신청(로컬 RTX 5060 Ti가 생겨 필요성 재검토)

### 다음 작업

- [ ] **앱 실배포** — Vercel 프로젝트 신설 · Cloudflare 터널 토큰 발급 · `cloudflared` 기동 (대구 런북 재사용, `CORS_ALLOW_ORIGINS`·SSE 프록시 버퍼링 off 반영)
- [ ] 모바일 지도 — `map-explorer` 반응형 분기
- [ ] 뉴스 수집 시 사건 단위 클러스터링(대형 보도자료 4건) · 뉴스 본문 지역 추출
- [ ] 리포트 프롬프트·도구 다이어트(도구 10종·계약 3블록으로 로컬 입력 29.5k 토큰)
- [ ] `docs/api.md` 갱신 — `/profiles`·`/hour-gaps`·`/commerce-changes`·`/intent`·`/finance` 3종·`/funding/candidates`
- [ ] 이월: `funding_program_industry`, 서울신보·금감원 금융상품 정본, 인구 2026.07분, 상권명 → 동 매핑, 빈 BC 디렉터리 정리

## 2026-09-28

팀장 브레인스토밍으로 서비스 방향을 **네거티브 리포트**("이 동네에서 이 장사는 하지 마라")로 전환했다. 그 첫 재료로
음식 업종 8종을 인허가 일반음식점 원천에서 붙여 강남 파일럿 → 25구 전량 적재까지 하루에 끝냈고(store 349,043 → **888,308행**,
지표 27,829 → **55,093행**), 프론트는 Codex 수정 3건에 이어 업종 확장을 반영했다. 밤에는 판정 카드 설계서·13 Task 플랜을
쓰고 신규 `verdict` BC를 서브에이전트 태스크 단위로 Task 6까지 구현했다(`feat/verdict-card`, 미병합).
Backend **v0.39.0**, Frontend **v0.25.1 → v0.28.0**.

### 1. [설계] 방향 전환 — 네거티브 리포트 (HANDOFF §0 신설)

- **문제 인식**: "어디에 창업하면 좋다"는 핀다·오픈업이 이미 한다. 우리는 **지방행정 인허가 원천**이라 망한 가게를 점포 단위로
  센다 — 개업일·폐업일·좌표가 전부 있는 폐업 21만 건이 원료이고, 2019년부터 시계열이라 코호트 생존율·**백테스트**가 된다
- **핵심 구조**: 점수 하나로 뭉개지 않고 **독립 경고 신호를 하나씩 켠다**(Specification 패턴, 신호 1개 = 클래스 1개).
  공통 신호 10종 후보(순유출·생존 절벽·조기 폐업·포화·매출 하락·상권 축소·시간대 불일치·인구 이탈·임대료 부담·충격 미회복) +
  업종 특화 신호. 판정은 🔴 비추천 / 🟠 조건부 / ⚪ 경고 없음 — **🟢 추천은 쓰지 않는다**. 대안은 동네 고정·업종 고정 두 축
- **지도**: 업종별 위험도 단계구분도("가지 마라 지도") + 동 선택 시 최근 2년 폐업 마커 + 편의점 담배권 원
- **최종 판정 산출(§0-10)**: 연도별 수치는 입력, 출력은 판정 하나. 필요한 ML은 3개(생존 분석·폐업 위험 분류기·동네 유사도)이고
  딥러닝은 불필요. 임계값은 사람이 정하지 않고 **427동 백분위(상대평가)** 로 — §0-8 첫 결정 항목 확정
- **학원·어린이집은 판정 대상이 아니라 보조축(§0-11)**: 정주 인구 지표이므로 업종 select·관문·판정 카드에서 빼고 동 단위
  피처로 쓴다 → 판정 대상은 기존 8종 + 음식 6종 = **14종**
- 실행 순서: 1 공통 신호 5개로 판정 카드·위험도 지도·폐업 마커 → 2 대안 두 축 → 3 백테스트 → 4 업종 특화 신호

### 2. [백엔드] 음식 업종 8종 + 인허가 업태 분류기 (Backend v0.39.0)

- 설계서 `docs/superpowers/specs/2026-09-28-industry-expansion-design.md` — 상권분석 아카이브에 100업종이 이미 있고,
  인허가 일반음식점 API가 우리 키로 열려 있음을 실측으로 확인. 1차 6종(한식·중식·일식·양식·분식·호프주점) + 비노출
  `restaurant_other` + 치킨. 패스트푸드(프랜차이즈 위주)·세탁·약국·숙박은 제외·보류
- **핵심 결정 — 업종 6개가 아니라 슬러그 1개 + 분류기**: 6업종을 따로 수집하면 같은 50만 건을 6번 받는다. 인허가 타깃은
  `general_restaurants` 슬러그 하나로 두고 건별 업종은 업태(`BZSTAT_SE_NM`) 분류기가 정한다.
  `PermitIndustryClassifier` 추상 + `FixedIndustryClassifier`(기존 6슬러그, 동작 불변) + `BusinessTypeClassifier`(Strategy)
- 0단계 강남 파일럿 **51,402건** 전수(DB 미적재, JSONL): 표본에서 44%였던 '기타'가 실제로는 **9.6%**(정렬 편향), 한식 38%·
  경양식 23%·분식 11%. '통닭(치킨)' 업태가 따로 있어 분류기에 넣되 **2015년 이후 신규 발급 없음** → 인허가 기반 신호에서 제외
- 마이그레이션 `b7c8d9e0f1a2`: industry 8행, 인허가 매핑 1행(앵커), 상권분석 매핑 7행, `cafe`↔CS100008(분식) 삭제.
  `seed_master`도 동일(멱등). 수집 단위를 업종에서 슬러그로 — `_build_targets`가 슬러그당 타깃 1개, 커서는 업종 집합의 max.
  관문 동의어 40여 개 추가
- 테스트 13건(분류기 7·타깃 빌더 4·게이트웨이 2) + 커서 1, 전체 **542 passed**
- 강남구 적재 실측: 51,402건 업서트 → 공간조인 50,022 → 지표 29,229행(+1,400), store 전체 400,598

### 3. [데이터] 24구 적재 66분 — store 888,308행 · 지표 55,093행

- 21:17~22:23 구별 순차 nohup(`--district X --industry general_restaurants --full`), **구당 2~4분, 총 66분**(예상 3시간).
  실패 구 없음. 공간조인 456,086건 판정 → 456,046 기입(미판정 40·구 교차 불일치 48)
- 전 서울 실측: store **888,308**행(음식 539,112 = 한식 226,118 · 분식 82,817 · 기타 71,091 · 양식 56,427 · 호프주점 52,114 ·
  일식 23,753 · 중식 17,389 · 치킨 9,403 / 영업 258,773 · 폐업 629,535). `region_industry_metric` **55,093**행(18업종, 음식 27,264행 추가).
  `GET /metrics?metric=closure_rate&industry=korean_food&year=2025` **427동** 응답(8200·8201 모두)
- 주의: 치킨 최근 개업 2017-09-25(전 서울 기준)로 결론 동일. 음식 좌표 결측 약 5~7%(한식 14,684행 등)는 원천이 좌표를 안 준 행 —
  지오코딩 대상 포함 여부 미결정
- 오후 커밋 6개가 로컬 브랜치에만 있고 푸시가 안 돼 있던 것을 밤에 발견 → main ff 머지·푸시
- 문서: `docs/api.md` **§0 적재 현황** 신설(36테이블 약 1,159만 행, 마스터·인허가·집계·상권분석·정책·RAG 6표),
  `docs/STATUS.md` §2-2·2-3 음식 업종 행 추가, HANDOFF §0-9 진행 체크, 설계서 §5-1 진행 기록

### 4. [프론트엔드] Codex 수정 3건 — 브랜드·관문 복구·자금 계획 (Frontend v0.25.1 → v0.27.0)

- **v0.25.1** 브랜드 표기 "아틀라스" → "메타볼레" — 탑바 워드마크·랜딩 캡션·title·"소개" 링크·영문 eyebrow(METABOLE) 전부 교체
- **v0.26.0** 랜딩 검색·지도 진입 복구 — `127.0.0.1:3200`에서 Next 개발 서버가 JS 요청을 403으로 막던 것을 `allowedDevOrigins`로
  수정. 검색 실패 후 재시도(실패 Promise 재사용 금지, 15초·3초 제한, 새 검색·이탈 시 이전 요청 취소), 지도와 상세 패널 분기 일치
  (선택 분기를 프로필·시간대·영업 지속 요청과 캐시 키에 전달), WebGL·소스·타일 오류 안내와 재시도, 모바일 지표 버튼 두 열.
  Vitest **315/315**
- **v0.27.0** 자금 계획 화면 정리 — 행정동 코드 대신 동네 이름·업종 표시, 나의 자금 / 준비 비용 / 월 매출과 운영비로 입력 재편,
  원가율·수수료·금리는 별도 펼침, 결과는 필요한 자금부터 보이고 시나리오·최초안 비교는 펼침. 모바일 한 열, 상담 자료 가로 넘침 수정.
  Vitest **318/318**

### 5. [프론트엔드] 음식 업종 6종 노출 + optgroup + 학원·어린이집 제외 (Frontend v0.28.0)

- `shared/industries.ts` 단일 원천 재편 — 라벨 16종, **판정 대상 `INDUSTRIES` 14종**(학원·어린이집 제외, `restaurant_other` 비노출),
  `INDUSTRY_GROUPS`(음식 / 생활 / 여가)를 상권 탐색 컨트롤바와 AI 분석 폼이 공유. 호프·주점은 백엔드 demand_type이 leisure지만
  사용자 인지 기준으로 음식 그룹
- 예시 질문 칩 음식 6종 × 3문구, mock 관문 동의어(국밥집·중국집·초밥·파스타·김밥·술집 등) 백엔드 미러
- mock 라우트 업종 가드를 select 목록이 아닌 마스터 전체(`isKnownIndustry`)로 — 실 API처럼 학원·어린이집에도 계속 200.
  계약 테스트 `shared/industries.test.ts` 신설. Vitest **326/326**(70파일), `tsc` clean
- 점포 표본에 음식 업종은 아직 없음(빈 배열이 정확한 동작) — 실DB 적재 후 별도 추출

### 6. [설계] 판정 카드 설계서 + 13 Task 구현 플랜

- 설계서 `docs/superpowers/specs/2026-09-28-verdict-card-design.md`(HANDOFF §0-7 실행 순서 1번). 결정: **규칙 신호 5개 + 상대평가**
  (ML은 백테스트 단계로), **신규 `verdict` BC + 새벽 배치 테이블 `region_industry_verdict`**(지도가 427동을 한 번에 칠하므로
  요청 시 계산은 무거움), 신호 입력은 verdict BC 자체 게이트웨이가 store·metric·neighborhood ORM을 읽음(다른 BC 무변경),
  포화 분모는 상주인구만
- 신호 5개: 순유출(12개월 폐업−개업 ÷ 시작 점포)·생존 절벽(3년 전 개업 코호트 생존율)·조기 폐업(최근 3년 폐업 영업개월 중위)·
  포화(상주인구 1,000명당 점포)·상권 축소(변화지표 HL). 표본 가드 미달은 `unavailable`
- 상대평가: 업종 안 427동 **strict 백분위** `p ≥ 75 → on, p ≥ 90 → strong`. 상수는 `VerdictThresholds` 한 곳, 실제 경계값은
  배치마다 분포에서 재계산. 판정: red(strong ≥ 2) / orange(켜진 신호 ≥ 1) / clear / **insufficient**(판정 가능 신호 < 3, 먼저 검사)
- 근거 문장은 규칙 코드가 숫자·비교 기준을 넣어 만든다(LLM 관여 없음). API 3개 — `/verdicts/myself`(배선 검증 먼저),
  `/verdicts?industry=`(범주형 단계구분도 계약), `/verdicts/{region_code}?industry=`
- 3단계: 1 verdict BC(BE v0.40.0) → 2 프론트 판정 카드·위험도 지도(FE v0.29.0) → 3 폐업 마커 `GET /stores?status=closed`(BE v0.40.1·FE v0.29.1)
- 플랜 `docs/superpowers/plans/2026-09-28-verdict-card.md` — 13 Task, 코드·테스트 포함 3,622줄

### 7. [백엔드] verdict BC Task 1~6 구현 — `feat/verdict-card` (진행 중, 미병합)

- 서브에이전트 태스크별 구현 → Sonnet 리뷰 → 승인 → 다음 Task 순서로 진행. 커밋 6개(TDD Red → Green):
  - Task 1 엔티티·`VerdictThresholds`·strict 백분위 (`1cee5e5`)
  - Task 2 공통 신호 5개 **Specification** — 순유출·생존 절벽·조기 폐업·포화·상권 축소 (`ef939a6`)
  - Task 3 판정 규칙 **Chain of Responsibility** — 보류 우선 · red · orange · clear (`791d8c9`)
  - Task 4 DTO 7종·출력 포트 4종·입력 포트·인터랙터 — 업종별 분포로 신호 평가·판정·업서트 (`52b6325`)
  - Task 5 ORM·마이그레이션 `c9d0e1f2a3b4`(down `b7c8d9e0f1a2`)·리포지토리·orm_mapper(signals JSON) — 실DB head 적용 (`d342986`)
  - Task 6 게이트웨이 3종 — store 집계 **1쿼리**(`group_by(region, industry)` + `percentile_cont(0.5)`), 동 맥락(최신 연도
    store_count·최신 분기 resident_total·commerce_change+서울 베이스라인 서브쿼리), 판정 대상 업종 카탈로그 (`b0e318c`)
- Task 5는 구현 완료로 보고됐으나 저장소에 없던 것을 리뷰에서 잡아 재구현(env.py ORM 등록 누락도 함께 해결)
- 커밋된 테스트 **28건**(임계값 6·신호 9·규칙 5·build 4·리포지토리 1·게이트웨이 3)
- **Task 7 작업 중(미커밋)**: 라우터·스키마·`dependencies/` DI·router 테스트 4건, `main.py` 라우터 등록,
  `scripts/store-collector.sh`에 `build_verdicts` 한 줄(`build_metrics` 바로 다음), `min_sample` 10 → 5 조정.
  버전 로그(BE v0.40.0)는 Task 7 완료 시 통합 기록 예정

### 다음 작업

- [ ] **verdict Task 7** — 라우터 `/myself` 배선 검증 → CLI `build_verdicts` → 실DB 배치 1회, 14업종 판정 분포(red/orange/clear/insufficient) 기록, `GET /verdicts?industry=korean_food` 427동 확인 → BE **v0.40.0** 버전 로그
- [ ] 2단계 프론트 판정 카드·위험도 지도(Task 8~11, FE v0.29.0) → 3단계 폐업 마커(Task 12~13)
- [ ] 팀 결정: 1차 음식 업종 확정(6종 + 치킨 조건부), 대안 두 축 vs 동네 고정, 서비스 이름·톤
- [ ] 음식 업종 후속 — 점포 표본 `store-samples.ts` 추출, 좌표 결측 5~7% 지오코딩 대상 여부, 2차 치킨/제과(활용신청)
- [ ] `feat/verdict-card` main 병합 후 `SNAPSHOT_INDUSTRIES`·`NO_CLOSURE_HISTORY_INDUSTRIES`·`_NO_CLOSURE_HISTORY` 예외 정리(판정 UI 전환 시)
- [ ] 이월: 앱 실배포(Vercel·터널 토큰), 뉴스 사건 클러스터링, 리포트 프롬프트 다이어트, `docs/api.md` 엔드포인트 갱신, `funding_program_industry`

## 2026-09-29

어제 밤 설계한 네거티브 리포트를 하루 만에 화면까지 끌고 왔다. 판정 카드·창업 경고 지도 → 대안 두 축 → 백테스트 →
화면 재편(A안) → 리포트 v2(사실 선수집·시각 자료·토큰 스트리밍) → 업종 특화 신호 1차까지 여섯 단계를 순서대로 끝냈다.
Backend **v0.40.0 → v0.46.0**(7개 버전), Frontend **v0.29.0 → v0.33.0**(6개 버전), 백엔드 테스트 574 → **779 passed**.
밤에는 별개로 관리자 페이지용 `admin` BC를 새로 착수했다(미커밋).

### 1. [백엔드] verdict BC 완성 — 판정 API·폐업 마커 (v0.40.0 ~ v0.40.2)

- **판정 API 3종** — `/verdicts/myself`(배선 검증) · `/verdicts?industry=`(427동 범주형 단계구분도) · `/verdicts/{region_code}?industry=`.
  실DB 배치 1회 **5,551행(13업종 × 427동), 약 2.2초**
- 편의점은 스냅샷 전용 원천이라 store 인허가 행이 없어 신호 3개가 영구 불가 → 1단계 판정 대상에서 제외(**13업종**).
  `min_sample` 10은 유지 — 5로 낮춰도 30~45%가 보류이고 5건 표본의 백분위는 노이즈라는 판단(Ruling B)
- **v0.40.1** `GET /stores?status=open|closed` — 최근 2년 폐업·좌표 보유 점포. status → 조회 전략 Strategy 맵으로 분기(`if/elif` 없음).
  폐업일<개업일 오염 행을 조기 폐업 집계에서 제외(`days_open >= 0`)
- **v0.40.2** 배치 prune — 업종을 `EXCLUDED_INDUSTRIES`에 넣으면 다음 새벽 배치가 옛 행을 자동 삭제(9/28 편의점 427행 수동 delete 재발 방지).
  오염 행 실측은 store 888,322행 중 **0건**

### 2. [프론트엔드] 판정 카드 + 창업 경고 지도 + 폐업 마커 (v0.29.0 · v0.29.1)

- **판정 카드** `VerdictSection` — 사이드패널 헤더 바로 아래 큰 배지(비추천·조건부·경고 없음·판정 보류) + 켜진 신호를 강함 먼저,
  "근거 보기"에 5개 신호 전부. 404(판정 없음·대상 아님)는 섹션을 그리지 않는다
- **창업 경고 지도** — `verdict` 범주 지표(축 `industry_latest`: 연도·분기 select 숨김). 범주 팔레트 4색과 라벨을 지표 원천이 스스로 소유해
  지도·범례의 하드코딩을 걷어냈다
- **폐업 마커 토글**(v0.29.1) — 영업 마커 위에 최근 2년 폐업 점포를 **추가로** 얹는다(대체 아님). `RegionMarkers`를 `strategy`·`sourceId`·`colorVar`로
  파라미터화해 한 지도에 레이어 둘. 산출일은 호스트 TZ와 무관하게 Asia/Seoul 고정. Vitest **357/357**

### 3. 대안 두 축 (BE v0.41.0 · FE v0.30.0)

- `GET /verdicts/{region_code}/alternatives?industry=` — 동네 고정(같은 동 다른 업종) · 업종 고정(최신 분기 동네 유형이 같은 다른 동).
  신규 테이블·배치 없이 `region_industry_verdict` 조회 + `region_profile_quarter` 한 컬럼 조인
- 순위 규칙은 `domain/services/alternatives.py` 한 곳 — 후보는 clear·orange만, 키 `(판정 순위, strong, on)`이 **기준보다 작은 것만** 3개.
  기준이 clear면 대안 없음
- 카드에는 "굳이 이 동네라면 ○○ · ○○" / "굳이 {업종}(이)라면 ○○동 · ○○동 (같은 {유형} 동네 중)" 2줄. 경고 없음 카드는 요청 자체를 하지 않는다

### 4. [백엔드] 판정 백테스트 — 규칙이 실제로 맞히는가 (v0.42.0 · v0.43.0)

- CLI `backtest_verdicts --as-of 2022-06-30` — T 시점 데이터만으로 판정을 다시 내고(저장 없음) T 직후 365일 진입 코호트의
  **1,095일 내 폐업률**을 판정 코드별·업종별로 대조. 누수 차단은 `latest_contexts(quarter_max)`·`latest_store_counts(year_max)` 상한으로
- 결과(1초): 전체 🔴 **58.3%(2,326곳)** vs ⚪ **32.2%(4,188곳)**, lift **1.81×**. 업종별은 카페 **1.90×**(74.3% vs 39.2%)·미용실 1.40×·한식 1.15×,
  **음식 업종 대부분 1.0~1.07×** — 규칙 5개가 카페에만 잘 듣는다는 뜻
- **신호별 lift**: 생존 절벽 1.46× · 조기 폐업 1.32× · 순유출 1.28× · 포화 1.11× · **상권 축소 0.96×(무신호)**

### 5. 화면 재편 A안 — 판정 지도 한 장 + brief 한 화면 (BE v0.44.0 · FE v0.31.0)

- **상권 축소를 참고 신호로 강등** — `ADVISORY_SIGNAL_KEYS`. 신호는 그대로 평가·저장하되 등급 계산에서만 뺀다.
  판정 신호가 4개가 되면서 가드가 사실상 3/4이 되어 보류가 **70.6%(5,124 중 3,618)** 까지 올라, `min_evaluable`을 3 → **2**로 내려 보류 **39.3%(2,014)**.
  백테스트 전체 lift는 1.68× → **1.70×** — 가드를 풀어도 판별력은 떨어지지 않았다
- **부동산 판정 제외** — 브이월드 API·공공데이터 파일·서울 열린데이터 모두 현재 사무소만 주고 폐업 이력이 없다 → 판정 대상 13종 → **12종**(5,124행)
- 지도는 **최신 판정 단계구분도만** 남겼다. 지표 무리 버튼·연도/분기 select·numeric 범례·비판정 원천 7개를 URL(`industry·region·budget` 3필드)과 함께 정리
- brief는 한 화면 — 켜진 신호 strong 우선 최대 3행 + 대안 두 축 + 동네 한 줄 + CTA "AI 분석 리포트 보기" → `/analysis?region&industry&budget`
- 리포트 섹션을 `verdict · reasons · conditions · alternatives · funding` 5개로 재편(옛 market·shock·calculator 폐기),
  agent BC에 판정 도구 2종(`get_verdict`·`get_verdict_alternatives`)을 붙였다. Vitest **344/344**

### 6. 리포트 v2 — 사실 선수집 + 토큰 스트리밍 (BE v0.45.0 · FE v0.32.0)

- **facts 선수집** — `ReportFactsCollector`가 LLM 호출 **전에** 12키를 `ThreadPoolExecutor`로 동시 수집한다. 실패는 항목 단위로 격리돼
  그 자리만 `{"available": false, "reason": …}`. 역삼1동×한식 실측 **15,340자(21.8KB)·콜드 1.07초·웜 0.14초**
- **도구 12종 → 4종** — 판정·대안·지표·프로필 등 8종은 facts가 대신한다. 같은 데이터를 매 실행 LLM 재량으로 다시 묻던 왕복이 사라졌다
- **토큰 스트리밍** — `LLMGatewayPort.stream()` + 순수 `SectionSplitter`(마커가 조각 경계에 걸쳐도 놓치지 않는다)로 `report_delta`를 조각 단위 전송
- **Gemini 사전 추론(thinking) 끔** — 같은 프롬프트에서 ON 첫 토큰 **11.7초·완료 22.5초** → OFF **1.1초·완료 8.4~9.0초**.
  단 `gemini-2.5-pro`는 thinking을 끌 수 없어 400이 나므로 flash 모델명일 때만 건다
- 프론트는 facts 한 프레임을 받으면 **그림 위·글 아래**로 5개 섹션을 즉시 그린다 — 공유 판정 카드·신호 막대(75/90 기준선)·대안 두 축·지원사업 카드·
  연도별 추세 SVG + 차트 4종 복원. Vitest **83파일 439테스트**
- 회귀 2건 수정: 글도 도구 호출도 없는 **빈 턴을 완성으로 보던 문제**(다섯 절이 전부 폴백으로 나갈 수 있었다)와
  `facts.funding_candidates`가 배열이 아니라 dict로 나가 지원사업 카드가 한 장도 안 뜨던 계약 위반

### 7. 업종 특화 신호 1차 — 편의점 담배권·부동산 집계 (BE v0.46.0 · FE v0.33.0)

- **판정 원천 `basis`** 도입(`permit`·`proxy`·`aggregate`) — 업종마다 다른 원천을 쓰되 카드는 같은 모양을 유지하고 배지로 출처를 밝힌다.
  신호 프로필은 Strategy(`PermitProfile`·`TobaccoProxyProfile`·`AggregateProfile`), 원천 표기는 Decorator, 미지원 신호는 Null Object
- **편의점**: 담배소매인 이력에서 브랜드 사전(LG25·훼미리마트·바이더웨이·위드미 등 옛 이름 포함) 매칭 → 같은 지번 ±90일 승계 접기로
  에피소드 **21,126건**을 만들어 인허가와 같은 규칙으로 창 집계. 담배권 빈자리는 영업 상가 × 영업 담배소매인 반경 50m 격자
- **부동산**: 상권분석 집계에서 최근 4분기 폐업률·포화·재고 결과. 여기에 국토부 실거래가로 신규 `housing` BC와 `apt_trade_count`를 만들어
  **중개사무소당 거래** 참고 신호를 붙였다(법정동 → 행정동 배분 적중률 **99.98%**, 77,977/77,995건)
- **재포함 게이트 — 둘 다 미달**: 기준은 경고 lift(🔴+🟠 폐업률 ÷ ⚪) **≥ 1.10×**, 실측은 편의점 **1.00×**·부동산 **1.04×**.
  판정 대상은 **12업종 그대로** 두고 결과만 상수 주석과 `docs/verdict-backtest.md` "재포함 심사" 절에 남겼다 —
  스냅샷 소실 기반 폐업이 1~2년 쌓이면 게이트만 다시 돌리면 된다(코드 준비 완료)
- 최종 전수 리뷰 → fix-wave: 게이트 결과를 하드코딩해 찍던 백테스트 CLI 프로즈를 `candidates.gates`에서 읽게 고치고, 경계값 테스트(lift 1.10·개업 50·동×업종 30)를 추가.
  전체 pytest **779 passed**

### 8. [백엔드] 관리자 BC 착수 — `feat/admin-rooms` (미커밋)

- 22시 이후 별도 작업. 관리자 페이지 3종(보안감사팀·헬스케어실·설비실)의 인증·보안감사용 `admin` BC를 프랙탈 구조로 신설
- 테이블 4종 마이그레이션 `f4a5b6c7d8e9` — `admin_user`(scrypt 해시·viewer/operator 역할) · `admin_session`(토큰 해시 PK) ·
  `access_event`(kind·ip·경로·상태코드) · `ip_block`
- 도메인 서비스 5종 — 비밀번호 해시·세션 토큰·스캐너 경로 판별(PHP·`.env`·`.git`·wp-admin 등)·보안 알림 규칙(Strategy, 규칙 추가는 클래스 하나)·
  로그인 스로틀(같은 IP 10분 10회 실패면 비밀번호를 확인하지 않고 거절). 도메인 테스트 **14건**
- 라우터는 아직 `main.py`에 등록 전 — 배선 검증(`/myself`)과 버전 로그 기록이 남았다

### 다음 작업

- [ ] **main 머지** — `feat/screen-restructure` → `feat/report-v2` → `feat/industry-specific-signals` 순서(각각 앞 브랜치 위에 쌓여 ff 가능)
- [ ] **노트북 브라우저 확인** — brief 한 화면 무스크롤, `/analysis`에서 0.3초 안에 카드·차트가 뜨고 글이 문장 단위로 흐르는지, 편의점·부동산 "판정 준비 중" 안내
- [ ] 도커 8200 이미지 재빌드 — 새 엔드포인트(`/verdicts/{region}/alternatives`, `facts` 이벤트)가 지금은 404
- [ ] **risk BC(ML) 설계서** — 백테스트가 보여준 대로 **피처가 먼저**(음식 업종은 규칙 5개로 1.0×). 프랜차이즈 비중·시간대 불일치·임대료·인구 구성 후보,
      같은 `backtest_verdicts` CLI로 규칙과 나란히 채점
- [ ] finance 프리필 도구 — "그래도 한다면"의 임대료 상한·손익분기가 아직 "/plan 안내"
- [ ] `admin` BC 라우터 등록·배선 검증 → 버전 로그
- [ ] 이월: 앱 실배포(Vercel·터널 토큰), 저밀도 업종 보류 비율(당구장 80%·PC방/중식/헬스장 64%), 음식 업종 좌표 결측 지오코딩, 서비스 이름·톤 결정

## 2026-09-30

`feat/admin-rooms` 브랜치 하루. 오전에는 어젯밤 착수한 `admin` BC를 관리자 관제실 4개 방과 공개 회원 계정으로 키웠고,
오후에는 리포트에 **유사 사례** 섹션을 새로 붙인 뒤 지원·대출 정보 화면(`/support`)과 자금 계획까지 이어지는 다음 단계 흐름을 만들었다.
Backend **v0.47.0 → v0.63.0**(22개 버전), Frontend **v0.34.0 → v0.51.0**(25개 버전).
테스트는 백엔드 779 → **1,072 passed**, 프론트엔드 **657 passed**(타입 검사 통과). 커밋 48개(09:35 ~ 18:16).

### 1. 관리자 관제실 `/admin` — 방 4개 + 허브 (BE v0.47.0 · v0.48.0 / FE v0.34.0 · v0.35.0 · v0.40.1)

- eungsang.com 관제실 구성을 참고했다. 허브에서 **보안 감사팀(15초)·헬스케어실(30초)·설비실(10초)·인사팀(30초)** 으로 들어가고,
  문마다 상태 배지(열린 알림·LLM 폴백·수집 지연·활성 관리자 1명 이하)가 붙어 지금 들어가 봐야 하는지 보여 준다
- **admin BC** — `admin_user`·`admin_session`·`access_event`·`ip_block`(마이그레이션 `f4a5b6c7d8e9`). 비밀번호 scrypt, 세션 토큰은 httpOnly 쿠키 `metabole_admin`에만
  두고 DB에는 sha256만(TTL 12시간). 순수 ASGI `SecurityMiddleware`가 차단 IP 403·5xx·스캐너 경로(.env·.git·wp-·.php)를 기록한다
- 보안 알림 규칙은 Strategy — 브루트포스 로그인(15분 5회 high·10회 critical)·스캐너(1시간 3회)·5xx 폭주(15분 5회)·차단 IP 재시도(1시간 5회)
- **ops BC** — 헬스케어(LLM 체인·필수 모델·Ollama·사용량 p50/p95·RAG 청크·프로브)와 설비(`/proc` 호스트 지표·`nvidia-smi`·Postgres·수집기 7종 신선도: 주기 × 1.5)
- v0.48.0 고도화 — 감사 로그 `admin_audit`, 인사팀 API, 이벤트 검색(id 커서), 호스트 지표 1분 표본 `host_metric_sample`(8일 보관)과 추세 차트,
  `llm_call_event`로 폴백률·오류율(5% 주의·20% 위험), 수집기 로그 보기(비밀값 마스킹)·"지금 실행", 보존 정리 CLI(이벤트 90일·감사 365일, 매일 03:30)
- 쿼리 `hours=168`이 `Literal[int]`에서 422로 떨어지던 문제를 `one_of` 검증기로 수정. 관리자 로고는 서비스 첫 화면(`/`)으로 간다(FE v0.40.1)

### 2. 공개 회원 계정 — 회원가입·이메일·구글 로그인 (BE v0.49.0 · v0.50.0 / FE v0.36.0 ~ v0.37.0 · v0.50.1)

- `/login`·`/signup` 신설(옛 `/admin/login`은 리다이렉트). 가입하면 바로 **일반** 등급(내부 `viewer`), 관리자 지정은 CLI `set_admin_role`로만
- 구글 로그인은 authorization code + state + **PKCE(S256)**. 기존 비밀번호 계정과 이메일이 겹치면 자동으로 잇지 않고 `EMAIL_TAKEN`.
  같은 IP 가입 1시간 5회 제한, 없는 계정·구글 전용 계정도 더미 해시로 응답 시간을 맞춘다. 공개 계정 테스트 **38**
- 상단바·랜딩 헤더에 계정 메뉴(`shared/auth` `useSession`)
- v0.50.0에서 **남의 등급·비밀번호 변경과 계정 추가 API를 제거** — 관리자가 남의 계정에 할 수 있는 일은 정지·재개와 세션 종료뿐.
  대신 내 계정명 변경(`PATCH /admin/auth/username`)과 구글 전용 계정의 비밀번호 첫 설정을 넣었다
- FE v0.36.1: 최신 Chrome의 `scrollIntoView`가 Promise를 돌려줘 `useEffect`가 그 값을 반환하면서 인사팀 패널이 깨지던 문제 수정

### 3. 자동 방어 + 화이트·블랙리스트 (BE v0.51.0 · v0.52.0 / FE v0.38.0 · v0.39.0)

- **자동 IP 차단** — 로그인 실패 15분 10회 → 1시간(재차단 24시간), 스캐너 경로 1시간 5회 → 24시간(재차단 7일). 테이블 `security_setting`으로 켜기·끄기(기본 켬),
  끄면 새 자동 차단만 멈추고 기존 차단과 로그인 제한(10분 10회)은 유지. 루프백은 막지 않고, 수동 차단은 덮어쓰지 않는다
- **디바이스 식별** — 관리자 경로에서 쿠키 `metabole_device`(22자, 400일) 발급, `access_event`에 `device_id`·`user_agent` 추가.
  인증 수단이 아니라 목록 대상 식별용
- `access_rule`(allow/deny × ip/device, 마이그레이션 `a3d8f1c5e742`) — IP는 CIDR 정규화(IPv4 /8·IPv6 /32보다 넓으면 거절), 대상별 검증은 Strategy.
  화이트리스트는 자동 차단·로그인 제한에서 빠지지만 **관리자가 직접 건 차단은 그대로 막는다**. 테스트 `test_access_rules.py` **22개**
- 배포 메모: 차단이 IP 기준이라 Next 앞에 XFF를 **덧붙이는** 리버스 프록시가 필요하고, HTTPS 배포 시 `ADMIN_COOKIE_SECURE=true`로 되돌린다

### 4. 리포트 유사 사례 — "비슷한 일이 예전에 있었을 때" (BE v0.53.0 ~ v0.59.0 / FE v0.40.0 ~ v0.46.0)

- **이벤트 유형** `shock_event.category`(마이그레이션 `b5e9d2c4a817`) — 감염병·방역(메르스·코로나19 시드 추가)·최저임금 8건·근로시간(주 52시간 3건)·지원금·보상.
  질문 속 단어(코로나·52시간·주4일·지원금 등)와 진행 중 이벤트로 유형을 고르고 유형마다 지난 사례 최대 3건. 등록 CLI `register_shock_event`
- 리포트 섹션이 **6개**로 — 판정 → 이유 → **유사 사례** → 조건 → 대안 → 지원사업(사실 13키, 길이 한도 2,400자)
- 한 시간 만에 두 창(직후·N년 차) 방식을 **분기 단위**로 갈아엎었다(v0.54.0) — 이벤트 달부터 3개월씩 최대 12분기, 분기마다 **이벤트 직전 1년의 같은 분기** 대비 %p.
  ±0.3%p 밖이면 강세·약세, 판단은 분기 과반. 비교 기간은 유형별(최저임금·지원금 4분기, 감염병·근로시간 12분기, v0.54.1). `stock_at` 누적합+이분 탐색으로 캐시 적중 시 **0.3초**
- v0.54.1 커밋에서 도메인·DTO 등이 빠져 `/shocks/analogs`가 500 → 리포트가 "자료 없음"으로 폴백하던 것을 v0.54.2로 복구
- 추가 신호 — 비교하지 않은 유형 안내 `hints`(v0.55.0), 최근 30일 뉴스 **제목**에서 조치 단어(집합금지·영업제한·거리두기 격상)만 세는 `recent_news`(v0.56.0 —
  "거리두기"로 찾으면 평소에도 30일 100건이 차서 제목·조치 단어로 좁혔고 지금은 0건), 드문 유형의 사례 직전 vs 최근 1년 업종 상태 `condition`(v0.57.0 —
  카페: 코로나19 직전 +7.1%·폐업률 14.0% → 최근 −1.1%·20.1%, `weaker`)
- **문장은 코드가 만든다**(v0.58.0 · v0.59.0) — LLM이 "12분기 중 8분기"를 틀리게 조립하고 근로시간 유형에 "감염병이 유행했던 시기에"를 옮겨 쓰고 "버 텼습니다"로 끊어 써서,
  강세 업종·직전 비교·사례 요약·겹친 정책·뉴스 문장을 도메인 `analog_sentences`가 완성 문장으로 붙이고 LLM은 그대로 옮긴다.
  대표 사례도 유형마다 최근 2건만 LLM에 넘긴다(`llm_view`). 겹친 정책에는 방향·인과를 붙이지 않는다
- 화면: 유형 칩·유형 종합 카드(추세·지속 기간·거듭 강세/약세 칩·최근 조치 소식·직전 대비 지금), 사례 카드는 **업종 × 분기 히트맵**(±0.3%p 밖만 칠하고 2%p에서 가장 진함).
  본문은 [확인된 사실]/[참고 신호] 표기마다 문단, 문장마다 줄바꿈하고, 코드 문장을 기준으로 유형별 사실 → 신호 순서로 다시 늘어놓는다(되풀이 제거).
  "50~299인"의 물결표가 취소선으로 그어지던 문제는 remark-gfm `singleTilde: false`로 수정(FE v0.43.1)

### 5. 유사 사례 자치구 계산 — 넣었다가 실측으로 철회 (BE v0.61.0 → v0.63.0 / FE v0.48.0 → v0.50.0)

- 17:48 자치구 계산을 넣었다 — 내 업종 점포가 구에 **1,000곳 이상**이면 구로, 모자라면 서울 전체(동 단위는 보라매동 한식 124곳이 분기마다 2~3%p 흔들려 처음부터 배제)
- 12분 뒤 철회. 2014~2024년 매 분기를 "아무 일 없던 이벤트"로 넣어 본 위양성 실측:

  | 범위 | 아무 일 없던 분기가 강세·약세로 잡힌 비율 |
  |---|---|
  | 서울 전체 한식 / 미용실 | **34% / 40%** |
  | 1,000곳 넘는 구의 한식 | 58~89% (강남구 4,878곳도 58%) |
  | 1,000곳 넘는 구의 카페 | 84~93% |

  같은 분기 구와 서울 전체 판정 일치율은 한식 22~41%로 세 갈래 무작위(약 33%)와 비슷했다. 비교 업종을 구 안에서 줄 세우면 점포 100~300곳 업종이 1등·꼴찌를 차지했다
- 결론: 내 업종·비교 업종 모두 **서울 전체**로만 계산하고, 리포트가 동 이야기로 읽히지 않게 문장에 "서울 전체 카페가…"처럼 **범위를 적는다**.
  `analog_scope`·`DistrictFlowPort`·캐싱 게이트웨이·`scope` 응답과 FE의 `AnalogScope` 문구를 걷어냈다

### 6. 리포트 다음 단계 — `/support` 창업 지원·대출 정보 → 자금 계획 (BE v0.60.0 · v0.62.0 / FE v0.47.0 · v0.49.0 · v0.51.0)

- 리포트가 끝나면 하단에 "창업 지원·대출 정보 보기 →"(`/support`)와 "← 다른 창업 알아보기"(`/map`) 두 버튼. 동·업종·예산을 주소에 싣는다
- `GET /funding/support` — LLM 없이 규칙으로 세 묶음: 대출·보증(최대 6, 기준금리·시설자금대출 금리 최신월 ECOS) · **{구} 전용**(최대 6) · 창업·경영(최대 8, 업종 관련 우선).
  화면에는 상담·신청 창구 6곳(소상공인 정책자금·서울신용보증재단·서울시 자영업지원센터·소상공인24·K-스타트업·기업마당)과 "필요한 자금 계산하기 →"(`/plan`)
- **다른 구 전용 공고 제외** — 구청 공고도 소관기관이 `서울특별시`로 오고 구 이름은 제목·태그에만 있다. 제목은 한글 낱말 첫머리에서만 찾아
  "집중구역"의 "중구" 오탐을 막는다. 업종 낱말도 "미용기기"·"헬스케어"(27건) 오탐 때문에 업소를 가리키는 말로 좁혔다
- v0.62.0에서 같은 규칙을 리포트 지원사업 섹션·`/funding/candidates`(`region` 추가)와 자금 계획 후보(FE v0.49.0)에도 적용 —
  실측(한식): 관악구 동은 은평구 청년식당 등 **2건이 빠지고** 관악구 원스톱 지원은 남음, 강남구 동은 셋 다 빠짐
- FE v0.51.0: `/plan`에 다시 들어오면 입력칸은 기본값인데 결과 카드만 `sessionStorage`의 지난 값이 남던 문제 — 저장·복원을 걷어내고 매번 빈 계획서로 시작

### 7. 문서

- `docs/2026-09-30_개발_정리.md` — 오늘 작업을 영역별(관제실·회원·유사 사례·지원 화면·자금 계획)로 정리하고 커밋 목록·배포 메모를 붙였다
- `docs/bm-proposal.md` — 네거티브 리포트 BM 제안 초안. 핵심 자산은 백테스트(카페 🔴 76.8% vs ⚪ 38.2%, **lift 2.01×**)로 판정 자체는 무료,
  근거·대비책 층을 유료로. 고객은 예비 창업자(1회) → 지원 기관(주 수익) → 금융·보증 위험 API(post-MVP). 유료 판매는 카페(2.01×)·미용실(1.41×)부터,
  음식 업종(한식 1.16×·중식 0.81×·일식 0.71×)은 "참고" 표기. 팀 결정 대기

### 다음 작업

- [ ] `feat/admin-rooms` 푸시·main 머지 (어제의 `feat/screen-restructure` → `feat/report-v2` → `feat/industry-specific-signals` 머지도 여전히 대기)
- [ ] 배포 준비 — XFF를 덧붙이는 리버스 프록시, `ADMIN_COOKIE_SECURE=true`, 구글 OAuth 운영 리다이렉트 URI
- [ ] 유사 사례 한계 보강 검토 — 10~12월 분기의 12월 폐업 몰림, 2020~2022 지원금 폐업 지연, "평소 대비"는 이벤트만의 효과가 아님
- [ ] BM 제안 팀 결정 — 유료 범위·가격·1차 업종, 공공누리 라이선스 상업 이용 점검 담당
- [ ] 이월: risk BC(ML) 설계서(피처 먼저), finance 프리필, 앱 실배포(Vercel·터널 토큰), 저밀도 업종 보류 비율, 서비스 이름·톤

## 2026-10-01

코드를 고친 곳은 프론트엔드 문구뿐인 하루. 낮에는 9/29 ~ 9/30에 쌓인 브랜치를 main으로 모으고 ERD를 실DB 기준으로 다시 맞췄고,
오후에는 `feat/warning-copy` 브랜치에서 화면을 감싸는 제목·메뉴·버튼·빈 화면 문구를 **"창업 경고"** 방향으로 정비했다.
Backend 변경 없음(**v0.63.0** 유지), Frontend **v0.51.0 → v0.52.1**(2개 버전).
프론트엔드 테스트 657 → **673 passed**(125파일, 타입 검사·실 API E2E 통과). 커밋 9개(13:13 ~ 15:23).

### 1. main 병합 — `feat/admin-rooms` 98커밋 fast-forward

- 13:34 main을 `3719ff5` → `1566151`로 fast-forward하고 origin에 푸시했다. **98커밋**
- 9/29의 `feat/screen-restructure` → `feat/report-v2` → `feat/industry-specific-signals`와 9/30의 `feat/admin-rooms`가 한 줄로 쌓여 있어
  한 번에 들어갔다 — 이틀 치 "머지 대기"가 전부 해소됐고 main은 **BE v0.63.0 · FE v0.51.0**
- 저장소가 공개라 사업 문서(`docs/plan/`, BM 제안)는 `.gitignore`로 빼고 올렸다

### 2. ERD §6 실DB 기준 갱신 — 36 → 47 테이블

- 운영 DB `information_schema` 실조회로 `docs/erd.md` §6을 다시 썼다. **47테이블**(`alembic_version` 제외), DB FK **49개**
- 9/23 이후 늘어난 **11테이블** — verdict 1(`region_industry_verdict`) · housing 1(`apt_trade_count`) ·
  admin 7(`admin_user`·`admin_session`·`admin_audit`·`access_event`·`access_rule`·`ip_block`·`security_setting`) ·
  ops 1(`host_metric_sample`) · agent 1(`llm_call_event`). 판정·관리자 계층의 관계선도 그림에 넣었다
- 적재 현황(§6.1, `count(*)` 실측)도 같은 날 기준으로 갱신:

  | 테이블 | 9/23 | 10/1 |
  |---|---|---|
  | `store` | 348,996 | **888,480** |
  | `industry` / `industry_source_code` | 10 / 25 | 18 / 32 |
  | `region_industry_metric` | 27,829 | **55,093** |
  | `region_industry_verdict` | — | 5,124 (427동 × 12업종, 전부 `basis=permit`) |
  | `apt_trade_count` | — | 16,367 (25구, 202101 ~ 202608) |
  | `rag_chunk` | 7,695 | 8,470 |
  | `news_article` / `funding_program` | 5,808 / 2,032 | 6,362 / 2,194 |
  | `analysis_report` · `llm_usage` | 7 | 163 |

### 3. [프론트엔드] 화면 문구를 "창업 경고"로 정비 (v0.52.0)

- 9/28에 방향을 네거티브 리포트로 바꾼 뒤 판정 카드·리포트 섹션·대안·지원·자금 계획의 **본문**은 이미 그 방향이었다.
  어긋난 것은 본문을 감싸는 제목·빈 화면·메뉴·버튼 — 9/17 ~ 9/23 "탐색 지도" 시절 문구가 남아 "가능성·발견·탐색"을 말하고,
  화면 재편(FE v0.31.0)으로 없앤 지표 전환·연도 선택을 여전히 안내하고 있었다
- **문구만 교체**(구조·API·라우팅 무변경). 원칙은 설계서 §2 — 쓰지 않는 말 "가능성·발견·시선·추천", 쓰는 말 "창업 경고·판정·근거·대안·계약 전에",
  말 거는 상대는 임대차 계약을 앞둔 예비창업자, 겁주지 않고 차분하게. 화면 이름은 **"창업 경고"** 로 통일하고 "네거티브 리포트"는 내부 용어로 남긴다
- 랜딩·메타 — 히어로 "서울의 변화 속에서, 내 가게의 자리를 찾다." → **"가게 자리를 찾기 전에, 피해야 할 자리부터 확인하세요."**,
  주 버튼 "상권 탐색하기" → "창업 경고 지도 보기", title "Metabole — 서울 창업 경고 리포트". 설명에 "서울 427개 동, 12개 업종"을 적었다
- 관문·상단 메뉴 — 버튼 "찾아보기" → "확인하기", 메뉴 "지도 탐색 · AI 분석" → "경고 지도 · 리포트".
  예시 칩 "망원동에 한식집"은 실 파서(`POST /intent`)에서 한식 + 후보 2동(망원제1동·제2동)으로 풀리는 것을 확인하고 넣었다
- 지도·리포트·자금 계획 — 지도 제목 "피해야 할 동네부터 보입니다.", 리포트 이름과 `aria-label` "창업 경고 리포트", 자금 계획 뒤로 가기 "← 경고 지도로".
  범례에는 한 줄을 **추가**했다: `"경고 없음"은 추천이 아닙니다.`
- **전수 리뷰 → fix-wave** — 문구가 사실보다 앞서 나간 곳을 고쳤다. 근거가 붙는 대상을 "모든 판정"에서 **경고**로 한정하고,
  백테스트 문장에 표본(판정 뒤 1년간 개업한 점포)과 업종을 밝혔다 — 카페 비추천 동 **76.8%** vs 경고 없음 동 **38.2%**(3년 내 폐업),
  카페·미용실 외 업종은 차이가 작거나 표본이 적어 참고로만 보라고 적었다
- 길어진 문구가 만든 레이아웃 문제 2건 — 소개 제목이 단어 중간에서 끊기던 것(`word-break: keep-all`)과
  모바일에서 소개 01·03 문장이 붙어 보이던 것(줄바꿈 앞 공백). 뷰포트 5종에서 넘침 없음 확인. Vitest **125파일 668건**
- `scripts/e2e-journey.sh`·`screenshot-matrix.sh`의 문구 선택자도 새 이름으로 맞췄다

### 4. [프론트엔드] 독립 리뷰 후속 — 조회 상태·제공 범위 정정 (v0.52.1)

- 독립 리뷰가 짚은 중요 2건·사소 3건. 둘 다 "문구가 실제 동작보다 많이 약속한다"는 문제였다
- **조회 상태** — 사이드 패널의 요약 조회와 판정 조회는 독립된 요청인데, 요약의 로딩·오류 문구가 판정까지 뭉뚱그려 설명했다.
  "동네 요약 정보를 불러오고 있어요."·"요약 정보를 불러오지 못했습니다."로 좁히고, 요약 실패·판정 성공 / 요약 성공·판정 실패 / 요약 대기·판정 성공을 각각 테스트로 고정했다
- **제공 범위** — 고를 수 있는 업종은 14개인데 판정 대상은 **12개**(편의점·부동산중개업 제외)다. 지도 설명에 "판정 대상 12개 업종"과
  "경고가 있는 경우 대안"을 밝히고, 빈 화면은 "제공 가능한 창업 경고 판정"으로 바꿔 제외 업종에도 판정을 무조건 약속하던 표현을 고쳤다
- 지원 화면의 복귀 링크를 "← 리포트로"로 통일(주소의 동·업종·예산 유지)
- 검증 — 새 단언 **9건 실패** 확인 뒤 수정해 관련 4파일 49건 통과, 전체 **125파일 673건**. 요약 요청만 막은 브라우저에서 요약 오류와 정상 판정이 함께 뜨는 것,
  지도 폭 375·768·1152·1440에서 넘침 없음 확인
- 실 API E2E(`/api/backend`) — 관문 → 지도 클릭(역삼2동) → 리포트 완료 **9,863자** → 자금 계산 → 후보 8건·질문 8개·준비자료 **2,887자**, XFAIL 폴백 없이 통과

### 5. 문서

- `docs/superpowers/specs/2026-10-01-warning-copy-design.md` — 문구 원칙·범위·"지금 → 바꿀 문구" 표(랜딩·관문·지도·리포트·E2E). 독립 리뷰 뒤 최종 문구로 다시 맞췄다
- `docs/superpowers/plans/2026-10-01-warning-copy.md`·`2026-10-01-warning-copy-review-fixes.md` — 구현 플랜과 리뷰 수정 계획(실행 기록 포함)
- 개발 일지 9/29·9/30 절과 `docs/2026-09-30_개발_정리.md`를 main 병합 전에 커밋했다

### 다음 작업

- [ ] `feat/warning-copy` main 머지 — origin에는 푸시됨, main보다 6커밋 앞
- [ ] 문구 정비에서 범위 밖으로 뺀 기능 3건 — 관문 한 줄 진단을 판정 문장으로(백엔드 `intent` BC), 동만 입력했을 때 "이 동네에서 피해야 할 업종" 일람,
      자금 계획의 "하위 25% 매출로는 손익분기를 못 넘는다" 경고 문장
- [ ] 배포 준비 — XFF를 덧붙이는 리버스 프록시, `ADMIN_COOKIE_SECURE=true`, 구글 OAuth 운영 리다이렉트 URI
- [ ] 이월: BM 제안 팀 결정, 유사 사례 한계 보강, risk BC(ML) 설계서(피처 먼저), finance 프리필, 앱 실배포(Vercel·터널 토큰), 저밀도 업종 보류 비율

## 2026-10-04

RAG 임베딩 모델을 고르는 하루. 저녁에 평가 하네스를 만들어 9개 조합을 같은 코퍼스·평가셋으로 비교했고,
결과를 근거로 운영 임베딩을 qwen3@1536에서 **bge-m3@1024**로 바꿔 전량 재색인했다. 밤에는 그 과정에서 드러난 컨테이너 → 호스트 Ollama 접속 문제를 고쳤다.
Backend **v0.63.0 → v0.65.1**(3개 버전, main 머지·origin 푸시), Frontend 변경 없음(**v0.52.1** 유지).
main 커밋 23개(20:09 ~ 23:17). 이어서 `feat/llm-benchmark` 브랜치에서 LLM 모델 평가(v0.66.0)를 시작했다 — 23:53 기준 10커밋, main 미머지.

### 1. 임베딩 모델 평가 하네스 (v0.64.0)

- 목적은 로컬용·API용 각 1종 선정. 비교 대상 **9조합** — bge-m3@1024, qwen3@1536·2560, gemini-embedding-001·gemini-embedding-2 × 1024·1536·2560.
  운영 DB·검색 경로는 건드리지 않는 별도 하네스로 만들었다(spec `2026-10-04-embedding-benchmark-design.md`, 플랜 8 Task)
- `benchmark_core.py` — MRL 절단·재정규화, 운영 규칙(원천 필터·뉴스 같은 사건 접기)을 그대로 따르는 numpy 전수 검색, top-1·nDCG@10, paired bootstrap(n=10,000, seed 0)
- 어댑터 — `OllamaBgeM3EmbeddingAdapter` 신설, qwen3에 `dim`, Gemini에 `model`·`dim` 인자(기본값은 운영 그대로).
  gemini-embedding-2는 `task_type`을 받지 않아 질의·문서 프리픽스로 지시한다(모델별 Strategy)
- `benchmark_embeddings` CLI — `snapshot`(rag_chunk 전량 jsonl + sha256) → `embed`(512개 샤드 단위 이어서 캐시, 원자적 쓰기·코퍼스 sha 불일치 시 중단) →
  `latency`(질의 × 3회 p50/p95, 로컬은 `gemma4:12b`와 동시 상주 확인) → `evaluate`(판정 규칙·보고서)
- 판정 규칙 — 그룹별 MRR 1위, bootstrap 동률이면 낮은 차원·짧은 p95. 로컬은 동시 상주·p95 ≤ 500ms 게이트를 통과하고 기준선 qwen3@1536보다 **유의하게** 좋을 때만 교체

### 2. 평가셋 확장·재검수 — 260건, confirmed 233

- 어려운 질문 3종 **60건**을 새로 만들었다 — 구어체(핵심어 회피) 20 · 유사 공고 구별(제목 토큰 Jaccard ≥ 0.3 짝) 20 · 뉴스 같은 사건(묶음 정답) 20.
  표본 선정에 임베딩 모델을 쓰지 않아 특정 모델 쪽으로 기울지 않게 했다
- Anthropic API 키가 없어 `generate_evalset --hard-mode export|import`·`judge_evalset --verdicts` 경로를 추가하고, 질문 작성·1차 판정은 Claude Code 서브에이전트가 했다(1차 O 53 / X 7)
- 사람 검수로 기존 200건까지 **전체 260건 재검수** — 질문 22건 교체(변별 정보 보강·사실 정정), 118번 O→X, 258번 X→O.
  결과 **confirmed 233**(base 179 + hard 54) / rejected 27. 질문이 바뀌어 9/24 `evaluate_rag` 수치와는 직접 비교하지 않는다

### 3. 평가 결과 — 코퍼스 8,891청크, 233문항

| 조합 | 그룹 | MRR | Hit@5 | MRR(hard) | p95 ms |
|---|---|---|---|---|---|
| bge-m3@1024 | 로컬 | **0.940** | 0.991 | 0.880 | 111 |
| qwen3@1536 (기존 운영) | 로컬 | 0.935 | 0.996 | 0.878 | 89 |
| qwen3@2560 | 로컬 | 0.934 | 1.000 | 0.880 | 89 |
| gemini-001@1024 | API | 0.953 | 0.996 | 0.899 | 426 |
| gemini-2@1024 | API | 0.957 | 1.000 | 0.901 | 574 |
| gemini-001·2@2560 | API | 0.960 | 0.996 · 1.000 | 0.914 · 0.907 | 426 · 574 |

- 규칙상 판정 — 로컬 **qwen3@1536 유지**(bge-m3와 동률, MRR 차 +0.005 [−0.018, +0.028]), API **gemini-001@1024**(6조합 동률 → 1024차원 중 p95가 짧은 쪽).
  다만 001은 **2028-05-14 단종 예정**이고 가격표에도 없어, 동률인 gemini-2@1024를 실무 대안으로 적었다(1회 전체 색인 약 **$0.31**, 1,537,106토큰)
- API 대 로컬 — 기준선 qwen3@1536보다 유의하게 좋은 Gemini 조합은 없었다(001@1024 대비 +0.0187 [−0.0016, +0.0396])
- hard 종류별로는 갈렸다 — 구어체는 qwen3(0.950)가 bge-m3(0.883)보다, 유사 공고는 bge-m3(0.969)가 qwen3(0.938)보다 낫다
- **CPU 실행 추가 측정**(Ollama `num_gpu=0`, Ryzen 5 9600X) — bge-m3는 CPU에서도 GPU 벡터와 코사인 ≥ **0.99998**, 질의 p95 **149ms**, 상주 1.2GB, 전체 재색인 추정 약 45분.
  qwen3-4b는 CPU 질의 p95 417ms, 재색인 약 5.7시간이라 CPU 운영이 현실적이지 않다

### 4. 운영 임베딩 bge-m3@1024 전환 (v0.65.0)

- **최종 결정(사용자)** — 규칙상 "현행 유지"는 교체 비용을 고려한 결과이고, 자원 제약·온프레미스 기준으로는 bge-m3가 낫다:
  MRR은 선택 규칙상 동률(성능 동등성이 입증됐다는 뜻은 아님)이며, bge-m3의 GPU 상주 메모리는 **664MB(VRAM)**다. 색인·질의를 모델 하나로 처리하고 CPU로도 운영 가능하다.
  CPU 상주 메모리는 **bge-m3 1.2GB, qwen3-4b 4.4GB(RAM)**다. qwen3의 GPU 상주값은 별도 측정값이 없어 664MB와 4.4GB를 GPU 메모리끼리 비교할 수 없다.
- 마이그레이션 `c7a3f1e8d204` — HNSW 인덱스 drop → `embedding vector(1024)` → 기존 벡터 NULL → 인덱스 재생성. 차원이 달라 변환이 안 되므로 전량 재색인이 필수
- `rag_dependencies` 운영 레지스트리를 `{"bge-m3"}` 하나로(qwen3·gemini 어댑터는 벤치마크용으로만 남김), `build_rag_index`·`evaluate_rag` 기본값과
  크론 `scripts/rag-indexer.sh`를 `--provider bge-m3`로, 운영 점검 필수 모델도 bge-m3로 바꿨다
- 적용 — 기존 테이블 백업(`rag_chunk_qwen1536_20261004.dump`) 뒤 마이그레이션, GPU 전량 재색인 **8,905건**(funding 2,265 + news 6,640) **101초**, 전부 `embedded_by=bge-m3`
- 운영 평가(confirmed 233) — Hit@5 **0.983** / MRR **0.930** (전환 전 qwen3 운영 0.991 / 0.930). `feat/embedding-benchmark`를 main에 병합하고 도커 `beyondfacade-api`를 재빌드했다

### 5. 컨테이너 → 호스트 Ollama 접속 해소 (v0.65.1)

- 재빌드 뒤 확인하니 컨테이너 안에서 RAG 검색·Ollama LLM 폴백·운영 점검이 모두 ConnectError — 어댑터가 `127.0.0.1:11434`를 하드코딩해 컨테이너 자기 자신을 가리키고 있었다.
  bge-m3 전환 전부터 있던 문제
- `Settings.ollama_base_url`(env `OLLAMA_BASE_URL`, 기본 127.0.0.1)을 추가해 LLM·임베딩 2종·운영 점검 어댑터가 쓰게 하고(명시 인자 우선),
  `docker-compose.yml`에 `OLLAMA_BASE_URL=http://host.docker.internal:11434` + `extra_hosts: host-gateway`를 넣었다. 호스트에서만 도는 벤치마크 CLI는 그대로 뒀다
- 재빌드 후 컨테이너에서 RAG 검색 3건, 운영 점검의 Ollama 도달(모델 12개) 확인. main을 origin에 푸시(`1889bce`)

### 6. [진행 중] LLM 모델 평가 — `feat/llm-benchmark` (v0.66.0, 미머지)

- 임베딩과 같은 원칙(게이트 통과 모델 중 동률이면 VRAM이 작은 쪽)으로 **리포트 작성**·**의도 관문** 두 역할의 로컬 LLM을 고른다.
  후보 gemma4:12b·e4b, kanana1.5:8b, qwen3.5:9b·4b·2b, exaone3.5:7.8b(도구 미지원·비상업 라이선스라 참고 비교군), 온라인 비교군 gemini-2.5-flash
- 평가셋 계획 — 관문 약 80건(랜드마크·업종 구어체·예산 표현·누락·범위 밖·복합), 리포트 12시나리오 × 3회(facts를 고정 저장해 모델만 비교)
- 여기까지 구현 — 공통 통계를 `core/matrix/grid_benchmark_manager.py`로 승격(임베딩 하네스도 여기서 가져옴), Ollama 어댑터 `think`·`temperature` 옵션,
  로컬 관문 추출기 `OllamaIntentLlmAdapter`(운영 배선에는 안 넣음), 관문 벤치 CLI `benchmark_intent`, 리포트 채점(숫자 지어내기 대조·판정 일치)
- 구현 중 발견 — Ollama는 스키마의 `nullable` 표기를 무시하고 문자열 `"null"`을 내는 모델이 있어, null을 JSON Schema 합집합 타입으로 표기해 해결했다

### 7. 문서

- `docs/superpowers/specs/2026-10-04-embedding-benchmark-design.md`·`plans/2026-10-04-embedding-benchmark.md` — 임베딩 평가 설계(9조합·판정 규칙)와 8 Task 구현 계획
- `data/eval/results/embedding-benchmark-2026-10-04/report.md` — 지표표·판정·비용·CPU 측정·최종 결정
- `docs/STATUS.md` — rag_chunk 8,905건·전량 bge-m3, 임베딩 평가 요약, §4-4-1 컨테이너 Ollama 문제 해소. `docs/api.md`·`docs/erd.md`(rag_chunk 1024차원)·산출물 구조 문서도 맞췄다
- `feat/llm-benchmark` 브랜치에 LLM 평가 설계 스펙·구현 계획(8 Task)

### 다음 작업

- [ ] LLM 모델 평가 마무리 — 관문 평가셋 라벨 검수(candidate → confirmed), 리포트 facts 고정·스모크 → 본실험(n=3) → 동시 상주, 결과로 로컬 폴백 선정 후 main 머지
- [ ] API 임베딩 경로를 쓰게 되면 gemini-embedding-2@1024 검토(001 단종 일정)
- [ ] 평가셋 한계 보강 — base 179건은 qwen 운영 시절 검수라 qwen 쪽으로 기울었을 수 있다
- [ ] 이월: 배포 준비(리버스 프록시 XFF·`ADMIN_COOKIE_SECURE`·OAuth 리다이렉트 URI), BM 제안 팀 결정, 문구 정비에서 뺀 기능 3건, 앱 실배포(Vercel·터널 토큰)

## 2026-10-05

리포트·관문에 쓸 LLM을 고르는 평가를 마치고(로컬은 두 역할 모두 엄격 게이트 탈락), 실패 원인 중 코드로 막을 수 있는 것을 막은 뒤 다시 쟀다.
이어 "같은 질문에 다른 답이 나온다"는 문제를 온도 0으로 줄였고, 8200 컨테이너가 그동안 Gemini 키 없이 돌던 문제를 고쳤다.
저녁에는 평가셋을 150건으로 늘리고 **리포트 구조를 "사실은 코드, 해석은 LLM 한 단락"으로 바꿨다** — LLM이 틀릴 수 있는 범위가 리포트 전체에서 한 단락으로 줄었다.
Backend **v0.65.1 → v0.68.0**(6개 버전), Frontend **v0.52.1 → v0.53.0**. `feat/report-code-first`를 main에 머지(`7cf212f`)하고 origin 푸시(`7f80bdc`)·8200 재빌드까지 마쳤다.
main 커밋 52개(00:04 ~ 23:34, 머지된 브랜치 포함). 밤에는 다음 단계 설계서를 `feat/question-answer` 브랜치에 커밋했다(`80d6717`, 미머지).

### 1. LLM 모델 평가 결과 (v0.66.0)

- 관문 평가셋 81건 사람 검수(confirmed 80 / rejected 1 — i008 정답을 종로1.2.3.4가동으로), 리포트 12시나리오 facts 고정, 7개 모델 × 12 × 3회
- 채점 정정 두 가지 — 판정 일치를 "등급 단어 일치"에서 **"모순 없음"**으로(Gemini가 '주의' 등급·빨간불 같은 표현을 써 0.22로 잡히던 오탐),
  숫자 지어내기 근거에 시스템 프롬프트·도구 설명을 포함. 관문 지어내기 분모는 스펙대로 누락·범위 밖 질문 26건
- 결과 — **두 역할 모두 엄격 게이트를 통과한 로컬 모델이 없다**

| 역할 | Gemini 2.5 Flash | gemma4:12b | gemma4:e4b |
|---|---|---|---|
| 리포트 품질(판정자, /10) | 6.67 | 6.00 | 5.42 |
| 리포트 지어내기 | 0.03 | **0.39** (공고 ID·URL 훼손) | 0.03 |
| 관문 동시 정답 | 0.988 | 0.887 | 0.762 |
| 관문 지어내기 | 0.000 | **0.077** (서울 밖 지명 → 서울 동) | 0.308 |

- 참고 순위(채택 결정 아님) — 리포트는 12b·e4b 동률(+0.58 [−0.17, +1.25]) → VRAM 작은 e4b, 관문은 12b. 리포트·관문·bge-m3 동시 상주 14.7GB
- 판정자가 지적한 규칙 위반의 대부분(97건 중 67건)이 신뢰 등급 표기 누락 — Gemini 포함 전 모델
- 결과·근거: `data/eval/results/llm-benchmark-2026-10-05/`(report.md·notes.md·results.json), 채점 기준표 `data/eval/report_judge_rubric.md`

### 2. 운영 로컬 폴백 컨텍스트 잘림 수정 (v0.66.1)

- 평가 중 발견 — Ollama 기본 컨텍스트가 입력을 약 2k 토큰에서 잘라, 운영 폴백 gemma4:12b가 facts 대부분을 못 읽고 있었다
- 리포트 폴백·운영 점검 프로브에 `num_ctx=32768` — 호스트·컨테이너 실측 입력 2,051 → **19,228토큰**

### 3. 리포트 출력 코드 가드 (v0.67.0)

화면이 이미 카드로 보여 주는 값(판정 등급·지원사업 원문 링크)을 LLM이 글로 옮기다 틀리는 실패를 코드로 막았다. 순수 모듈 `apps/agent/domain/services/report_guards.py`.

- **판정 모순 교체** — 판정 절에 등급 이름을 쓰지 말라고 바꾸고, 명시적 등급 단정이 사실과 어긋나면 코드 문장으로 바꾼다. 판정 절은 끝까지 모았다가 한 번에 내보낸다(SSE 계약 그대로)
- **링크·공고 번호 제거** — 스트리밍 필터, 조각 경계에서 잘린 URL도 처리
- **기본 신뢰 태그** — 판정·이유·조건·대안·지원사업 절이 태그 없이 시작하면 `[확인된 사실]`(유사 사례 절 제외)
- **지원사업 고지문** — "금리·한도는 예상치…원문 확인"을 코드가 붙인다
- 리뷰에서 잡힌 것 — 실제 모델은 제목을 `###` 없이 쓰는 경우가 대부분이라(1,260개 중 644개) 첫 구현은 태그가 제목 줄에 붙어 프론트 제목 제거가 깨졌다.
  캐시된 실출력 1,512개 섹션 전체로 검증하도록 고쳤다(제목 태그 0, URL 잔여 0, 스트리밍 = 전체 처리)
- 재평가(7개 모델 × 36회) — **12b 지어내기 0.39 → 0.00**(링크를 쓰지 말라고 하자 아예 쓰지 않았다), Gemini 판정자 위반 11 → 4.
  신뢰 태그는 전 모델이 섹션 180개 중 174~180개를 빠뜨려 코드가 붙였다 — 프롬프트로는 지켜지지 않는 규칙이었다
- 남은 실패 — 대안 절 등급 바꿔 쓰기(12b 12건 중 5건), 뉴스가 없는데 프롬프트 예시 문장 베끼기, 꺼진 신호 오독(e4b),
  기본 태그가 뉴스 섞인 문단을 확인된 사실로 보이게 하는 경우

### 4. 같은 질문에 일정한 답 — 온도 0·seed 42 (v0.67.0)

- 확인 — 운영 리포트는 온도를 지정하지 않았다(Gemini 기본 약 1.0). 벤치는 로컬만 0.3이었고 "운영과 같게" 주석은 틀렸다
- 운영·벤치를 `REPORT_TEMPERATURE=0.0`, `REPORT_SEED=42`(`report_sampling.py`) 단일 원천으로. 도구 명세의 금리 예시값(0.0405 — Gemini가 "현재 금리 4.05%"로 옮김)도 지웠다
- 일관성 지표 추가(같은 시나리오 3회끼리) — 결론 일치·숫자 일치·문장 유사도·대안 등급 일치

| 모델 | 결론 일치 | 숫자 일치 | 문장 유사도 | 대안 등급 일치 |
|---|---|---|---|---|
| Gemini | 0.75 → **1.00** | 0.42 → **0.71** | 0.39 → **0.74** | 0.75 → **0.94** |
| gemma4:12b | 1.00 → 1.00 | 0.62 → **0.84** | 0.58 → **0.86** | 0.44 → **0.78** |
| gemma4:e4b | 0.83 → **1.00** | 0.34 → **0.79** | 0.40 → **0.82** | 0.22 → **0.72** |

- 품질은 기본 온도·온도 0 출력을 **한 판정 묶음에 섞어** 블라인드 비교 — 세 모델 모두 차이 구간이 0을 포함(유의한 차이 없음, n=12)
- 결과: `data/eval/results/llm-benchmark-2026-10-05-guards/`(notes.md에 전후 비교)

### 5. 컨테이너에 API 키 주입 (v0.67.1)

- 재빌드 후 실리포트로 확인하다 발견 — compose가 `backend/.env`를 넘기지 않고 `.dockerignore`가 `.env`를 빼서,
  **8200 컨테이너는 줄곧 Gemini 키 없이 로컬 12b 단독으로 리포트를 썼고(1건 약 2분) 구글 로그인 버튼도 숨겨져 있었다**
- backend 서비스에 `env_file`(`required: false` — 새 클론에서도 기동). 접속 주소는 `environment:`가 우선해 컨테이너용 값 유지
- 실측 — 같은 리포트 129초 → **8초**, `/admin/auth/providers` google true

### 6. 리포트 평가셋 150건 (v0.67.2)

- 12건으로는 오류가 0건이어도 오류율 상한이 25%라, 사람 판정용 평가셋을 **150건**으로 늘렸다(150건이면 상한 약 2%)
- 기존 12건 + `region_industry_verdict`에서 해시 순서로 결정적으로 고른 red 36·orange 36·clear 30·insufficient 24 + 특수 12건(대출·특정 집단·재난기·편의점·어린이집).
  묶음마다 절반은 질문 없음, 절반은 구어체·예산·시간대·경쟁 질문. 다시 돌려도 같은 150건
- 리포트 벤치에 `--scenario-set 12|150`(기본 12, 기존 동작 그대로)

### 7. 리포트 코드 우선 구조 (BE v0.68.0 · FE v0.53.0)

오전의 "다음 작업"으로 적었던 구조 변경을 설계 승인(`2026-10-05-report-code-first-design.md`) 뒤 바로 구현했다.

- **6개 절은 코드가 facts로 쓴다** — 순수 모듈 `report_sections.py`(절 이름 → 작성 함수 dict 디스패치). 숫자마다 범위(동·업종 이름, "서울 동 상권 전체 기준값", 분기)를 붙이고,
  자료가 없으면 "자료 부족 — 이유", 신뢰 태그도 코드가 붙인다. 시간대 문장은 프론트 `hour-gap-sentence.ts`와 같은 규칙이며 같은 입력에 같은 문장을 내는지 테스트로 고정했다
- **LLM은 맨 위 해석(`answer`) 한 단락만** — 3~5문장, 숫자·링크·공고 번호 금지. 입력은 원본 facts JSON 대신 질문 + 코드가 쓴 6개 절(약 23,000자 → 약 2,000자).
  해석 가드 `guard_answer`가 링크 제거 → 판정 모순 검사(모순이면 단락 실패) → 숫자 든 문장 삭제를 차례로 건다. 실패하면 다음 모델(Gemini → 로컬 12b), 그래도 안 되면 코드 폴백 문장
- SSE 순서 `facts` → 코드 6개 절(사실 수집 직후 즉시) → `answer` → `report_done`. 저장 리포트도 해석이 맨 위
- 리포트 경로의 **도구 루프 제거** — 평가 252회에서 도구 호출이 0회였고 자금 계산은 자금 계획 화면이 맡는다. 옛 절 가드·LLM 절 폴백·마커 분할기도 정리
- **자료 부족 동네는 LLM을 부르지 않는다(사용자 결정)** — 판정 보류 28·판정 대상 아닌 업종 6, 34건은 "자료가 부족해 진입 판단을 내리기 어렵습니다 — 부족한 자료: …" 코드 첫 문장만
- 대안 중 경고 없음이 있으면 해석 끝에 고정 안내 문장 "대안 동네·업종 절에 경고 없음으로 나온 곳도 함께 확인해 보세요."(추천 아님)
- 프론트 v0.53.0 — 6개 사실 절 위에 "해석" 블록(answer가 없는 옛 저장본은 그리지 않음), `FactSection` 타입 분리, mock SSE가 해석 조각을 보낸다(계약 테스트 고정)
- 리뷰에서 잡은 것 — 숫자 가드가 **숫자 든 동 이름**("상도제1동"·"상계3.4동", 평가 동 150곳 중 99곳)만 언급한 문장까지 지웠다(Gemini 첫 문장 삭제 81/150 → 1).
  폴백 어댑터가 Gemini 실패 뒤 같은 로컬 모델을 다시 부르던 문제(최악 약 270초)도 고쳤다

### 8. 코드 우선 구조 재평가 — 150건 × 2모델

| 모델 | 해석 핵심 오류(Claude 판정, 150건) | 자료 부족 제외 116건 | 해석 p95 |
|---|---|---|---|
| Gemini 2.5 Flash | 21/150 (**14.0%**) | 20/116 (**17.2%**, 10.9~25.4%) | 4.4초 |
| gemma4:12b | 44/150 (**29.3%**) | 44/116 (**37.9%**, 29.1~47.4%) | 4.5초 |

- 코드 절 자동 검사(`sections-check`) — 150건에서 범위 없는 숫자 줄 0, 이유 빠진 자료 부족 자리 0. 동코드·업종 id 노출 0
- 기준선(이전 구조, **리포트 전체**) Gemini 26.7%·12b 80.0%와는 잰 대상이 다르다. 12b는 리포트 완료 p95 28.4초 → 해석 4.5초로, 짧은 입력·짧은 출력 구조가 로컬 모델에 유리했다
- **사람 검수 2차(20건 × 2)** — 질문 있는 리포트 16건 중 **12건을 "질문에 답하지 못함"**으로 봤다(Claude 판정자는 전부 "답함" — 판정자가 후하다).
  사람은 핵심 오류 칸을 1·2차 모두 채우지 못해 사람 기준 오류율은 아직 없다. 메모: 대안 추천, 뉴스 참고, "긍정적인 명확한 근거 없음", 거주민 생활수준 고려
- 결과: `data/eval/results/report-code-first-2026-10-05/`(`final/`이 최종)

### 9. 문서·설계

- `docs/model-evaluation.md` — 임베딩·LLM·코드 가드·온도 0 결과 종합
- 루트·`backend/docs`에 Codex용 `AGENTS.md`, CLAUDE.md에 "과도한 테스트·선제적 복잡도 금지" 규칙 추가
- `docs/HANDOFF.md` §0-14 — 10/5 이후 남은 것의 정본(리포트 품질·코드 후속·모델 운영·평가 자산). `docs/STATUS.md`도 맞췄다
- 부하 테스트 계획 `docs/testplan.md` 작성 — 시장 규모 가정이 들어 있어 gitignore(로컬 전용)
- **질문 유형별 직접 답 설계서**(`feat/question-answer`, `2026-10-05-question-answer-design.md`) — 못 답한 원인은 문장력이 아니라 질문이 묻는 사실이 해석 입력에 없다는 것.
  질문이 있으면 첫 문장(직접 답)과 근거 1~3줄을 코드가 질문 유형(키워드 규칙) × 판정 등급으로 쓰고(`answer_lead` 절 신설), LLM은 그 아래 해석 2~3문장만. 스펙 검토 대기

### 다음 작업

- [ ] 질문 유형별 직접 답 — 스펙 검토 → 구현 계획 → 구현(BE v0.69.0, 프론트는 Codex 위임)
- [ ] 노트북 브라우저 확인 — 해석 블록, 해석이 약 4초 늦게 뜰 때 화면 밀림, 자료 부족·비판정 업종 문장, 대안 안내 문장
- [ ] 리포트 코드 후속 — 숫자 가드 오삭제("1인당"·"코로나19"·"20대"), 로컬 재시도 호출이 `llm_calls`에 안 남음, 해석 대기 중 자리 표시·SSE 무소식(프록시 유휴 끊김)
- [ ] 판정자 기준 보정 — 구체적 질문에 결론이 없으면 "못 답함"
- [ ] 같은 질문 = 같은 답 캐시(관문 칸 + 사실 기준월 키), 관문 로컬 폴백 서울 밖 지명 매핑 개선, 부하 테스트 실행(k6 미설치)
- [ ] 이월: 배포 준비(리버스 프록시 XFF·`ADMIN_COOKIE_SECURE`·OAuth 리다이렉트 URI, 실서버는 `.env` 대신 시크릿 저장소), BM 제안 팀 결정, 앱 실배포(Vercel·터널 토큰)

## 2026-10-06

새벽에 질문 유형별 직접 답을 끝내고, 오전에는 리포트 해석 모델을 Claude·Gemini 3.8까지 넓혀 비교해 **운영 1차를 gemini-3.8-flash로 바꿨다**.
낮에는 해석 오류를 지시문·코드로 한 유형씩 막으며 150건 재평가를 12단계까지 돌렸고(적용 5·미적용 5), 사람 검수를 3~5차까지 했다.
저녁에는 판정 신호를 여러 시점 백테스트로 다시 재고, **데이터 이용조건 점검 결과에 따라 뉴스·행정동 경계·지원사업 공고 원천을 정리**했다. 밤에는 지역 사건(정비사업·대규모점포·대단지 입주)을 리포트에 연결했다.
Backend **v0.68.0 → v0.86.0**, Frontend **v0.53.0 → v0.62.0**(main 기준). main 커밋 96개(00:04 ~ 23:23, 머지된 브랜치 포함), origin 푸시 `b897859`까지. 8200 운영 도커는 BE v0.86.0·FE v0.62.0.
따로 `feat/k8s-phase0`(BE v0.80.0~v0.82.0·FE v0.58.0, 미머지)와 `feat/weak-basis-guard`(FE v0.63.0, 작업 중)가 있다.

### 1. 질문 유형별 직접 답 (BE v0.69.0 · FE v0.54.0~v0.54.1)

- 사람 검수 2차에서 질문 16건 중 12건이 "못 답함"이었던 원인 — 질문이 묻는 사실이 해석 입력에 없었다
- 질문 유형 분류기(`question_topic.classify`, 키워드 규칙)로 시간대·주말·평일·경쟁·대상 고객·예산·대출·코로나 등을 가르고, **직접 답 첫 문장과 근거 1~3줄을 코드가 facts로 쓴다**(`answer_lead` 절, 6개 사실 절보다 먼저 SSE 송출). LLM은 그 아래 해석 2~3문장만
- facts에 `finance`(자금 계획 프리필)·질문 속 예산, "그래도 한다면" 절에 주민 연령·아파트 시가 줄. 벤치 `freeze --augment`·`sections-check` 직접 답 검사·판정 기준표 v2
- 프론트 — 리포트 맨 위 **질문에 대한 답** 상자(직접 답 즉시 표시 → 아래 AI 해석), 해석이 안 오면 "AI 해석을 받지 못했습니다."
- Claude 판정(116건): Gemini 2.5 20.7%(이전 17.2%)·12b 31.9%(이전 37.9%) — 구간 겹침, 비악화. **사람 검수 3차 답함 13/16(81%, 2차 4/16)**으로 통과선(75%) 넘김

### 2. 판정 근거 위험 등급 표기 (BE v0.70.0 · FE v0.55.0)

- 3차 검수에서 못 답한 3건이 모두 "서울 상위/하위 N%" 백분위 표기 오독 — 사람 메모 "상위 10%가 무엇을 의미하는지 모를 가능성"
- 판정 임계값(75·90)과 그 대칭(25·10)을 경계로 한 **5단계 위험 등급 낱말 + 풀어 쓴 순번**으로 — 예: "밀집 매우 높은 편(서울 당구장 동을 100곳으로 치면 높은 쪽에서 10번째쯤)"
- API 신호에 `band`·`band_label`, 지도 판정 카드에 등급 라벨 토큰, 리포트 신호 막대도 등급 낱말
- Claude 판정: Gemini 핵심 오류 **20.7% → 12.1%**, 백분위 관련 오류 11 → 2

### 3. 리포트 문장 오독 대응·프리필 이상값 (BE v0.71.0~v0.71.2 · FE v0.56.0~v0.56.1)

- **자금 계획 월매출 프리필** — 점포당 평균이 같은 분기·업종 서울 동 중앙값의 1/3 미만이거나 부동산중개업이면 값을 비우고 이유를 단다(사용자 결정). 카드 결제 기반 추정이라 현금 비중 큰 곳이 낮게 잡힌다(가양제1동 미용실 428곳 월 약 67만 원). 화면은 "평균값 없음" 배지·직접 입력 안내
- 시간대 문장을 사람(유동인구)·매출 두 문장으로, 재난지원 단서는 2020~2022년 값 옆에만, 생존 절벽·조기 폐업 줄에 지표 뜻, 유사 사례 "평소보다" → "사례 직전 1년 같은 분기보다", 동네 유형 근거도 "100곳으로 치면" 표기
- 연간 폐업률 줄을 첫해·끝해 두 값 대신 **해마다 값**(v0.71.1), 점포 수도 해마다(v0.71.2) — 두 점만 주면 LLM이 "꾸준히 증가"로 옮겼다(Gemini 6건)

### 4. 해석 모델 비교 — Claude·Gemini 3.8 (BE v0.72.0~v0.75.0)

- `AnthropicLLMAdapter`(리포트 해석 한 턴, 도구 없음)와 벤치 모델 Claude 3종, `run --ids`(표본만 실행)
- 표본 20건: Haiku 4.5 10/20 · Sonnet 5.5 4/20 · **Opus 5.5 2/20** → 전체 116건: Opus **2/116(1.7%)** · Gemini 2.5 19/115(16.5%) · 12b 35/116(30.2%). 오전에 운영 1차를 오퍼스로(v0.73.0)
- 이어 유료 키로 쓸 수 있는 Gemini 3.8 Flash를 두 모드로 같은 116건에 넣었다(v0.74.0)

| 모델 | 핵심 오류(116건) | p95 | 건당 비용(추정) |
|---|---|---|---|
| claude-opus-5-5 | 5 (4.3%) | 8.6초 | $0.0217 |
| **gemini-3.8-flash 일반** | **8 (6.9%)** | 5.5초 | **$0.0022** |
| gemini-3.8-flash 추론 | 5 (4.3%) | 12.0초 | $0.0022 + 추론 토큰 |
| gemini-2.5-flash | 19 (16.5%) | 4.5초 | $0.0010 |

- **결정(사용자, v0.75.0)**: 1차 gemini-3.8-flash 일반 → 폴백 claude-opus-5-5 → 로컬 gemma4:12b. 오퍼스와 구간이 겹치면서 비용 약 1/10·더 빠름. 3.8은 숫자 금지 규칙을 지켜 숫자 가드 삭제 0건(오퍼스 4·2.5 26)
- 운영 메모 — Gemini 선불 크레딧이 낮에 소진됐다가 충전됨. 소진되면 해석은 12b → 코드 폴백으로 내려간다

### 5. 해석 품질 반복 개선 — 150건 재평가 4~12단계

해석을 바꿀 때마다 같은 116건을 두 운영 모델로 다시 돌리고 opus 판정자 6명이 블라인드로 판정했다(판정 오차 ±3건). **기본 모델(3.8) 오류가 늘면 미적용**이 원칙.

| 단계 | 바꾼 것 | 3.8 핵심 오류 | 오퍼스 | 결정 |
|---|---|---|---|---|
| 4 | [말투] 규칙 — 중고등학생 눈높이, 전문 용어 풀어 쓰기(v0.76.0) | 8 → **4** | 5 → 4 | 적용 |
| 5 | 한국어 윤문 규칙(번역투·AI 관용구 등), 줄인 판 재시험 | 4 → 10 / 12 | 4 → 2 / 4 | 미적용 |
| 6 | 시간대 매출 자료 없음을 코드 문장으로 명시 | 4 → 7 | 4 → 5 | 미적용 |
| 7 | 동 이름은 본문 표기 그대로(v0.76.1) — "답십리제두동" 같은 없는 지명 11 → 0 | 4 → **3** | 4 → 5 | 적용 |
| 8 | 남은 오류 3유형을 코드로(v0.78.0) — 매출 서울 중앙값 비교·시간대 매출 가드·판정 줄 신호 나눠 쓰기 | 3 → 4(겨냥 유형 0) | 5 → **1** | 적용 |
| 9 | 상권변화지표 쉬운 뜻·본문에 없는 시간대 낱말 가드 | 4 → 5 | 1 → 5 | 미적용 |
| 10 | 시간대 매출을 모르면 해석 입력에서 사람 흐름 빼기 | 4 → 6 | 1 → 6 | 미적용 |
| 11 | 뉴스를 해석 입력에서 빼기·상권 축소 신호 제거(v0.83.0, 이용조건상 필수) | 4 → 9 | 1 → 4 | 적용(필수) |
| 12 | 조건 절에 지역 사건 줄(v0.86.0) | 9 → **3** | 4 → **2** | 적용 |

- **교훈: 해석 입력에 글을 더하거나 빼면 3.8이 그걸 재료로 추론을 덧붙인다.** 효과가 난 건 코드가 쓰는 사실 문장의 등급 낱말과 코드 가드뿐이다(뜻풀이를 붙이자 "오래된 가게 위주 → 새로 들어가기 어렵다"를 지어냈고, 입력에서 사람 흐름을 빼자 화면 본문과 어긋났다)
- 시간대 매출 오류는 세 방법(사실 문장·낱말 가드·입력 빼기)이 모두 오류를 늘려 v0.78.0 가드까지를 한계로 보고 멈췄다
- 11단계 3.8 9건 중 4건은 "조기 폐업(문 닫은 점포의 영업 기간)을 새로 연 점포의 생존율로 풀이" — 다음 개선 후보로 남김
- 미적용 시험은 기록용 브랜치로만(`feat/answer-polish`·`feat/hour-gap-missing`·`feat/answer-fixes-2`·`feat/hour-flow-input`)

### 6. 사람 검수 3~5차

| 차수 | 대상 | 결과 | 반영 |
|---|---|---|---|
| 3차 | 질문 있는 16건 × 2(직접 답 구조) | **답함 13/16** | 백분위 오독 → 위험 등급 표기(v0.70.0) |
| 4차 | 표본 20건 × 2(3.8 일반·오퍼스, 블라인드) | **틀린 내용 두 모델 0/20**, 질문 답함 둘 다 11/12, 더 나은 해석 비슷함 14 | 3.8 일반 결정을 뒷받침. "답변이 친절하지 않다" → [말투] 규칙(v0.76.0) |
| 5차 | 같은 20건(운영 v0.78.0판) | 기록 2건 틀린 내용 0, 더 나은 해석 둘 다 3.8. 총평 "전부 반영은 하는 것 같다" | 오퍼스 폴백은 길고 설명조 — 폴백 1% 안팎이라 보류 |

- 검수 화면은 3차 구성(직접 답·근거 상자만 펼치고 본문 6개 절은 접기)이 가장 보기 좋았다. 근거를 다 펼친 4·5차 첫 판은 "길다"는 의견으로 다시 만들었고, 다음부터는 10건 이하로
- `docs/model-evaluation.md` §11(외부 API 해석 모델 비교 1~12단계)·§12(사람 검수 이력 9/24~10/6)로 정리

### 7. 공개 API 9개 정리 (BE v0.79.0~v0.79.1 · FE v0.57.0)

- 9/29 화면 재편 뒤 프론트가 부르지 않는 공개 GET 입구 9개 삭제 — `/metrics`·`/hour-gaps`·`/shocks`·`/shocks/analogs`·`/commerce-changes`(목록·상세)·`/profiles/types`·`/profiles`(목록)·`/childcare-center-stats/summary`. 같은 데이터는 리포트가 내부에서 읽는다
- 그 입구만 쓰던 유스케이스·포트·저장소·DTO·schema·mapper·테스트와 프론트 mock 라우트·전용 타입도 정리. 금리·임대료 수집 크론 등록(매주 월 05:20)

### 8. 판정 신호 다시 재기 — 여러 시점 백테스트·kNN 사례 신호 (`exp/signal-backtest`, 운영 코드 무변경)

- 한 시점(T=2022-06) 백테스트로는 카페·미용실만 가르고 음식은 대부분 ≤1.0×였다. 시점을 T=2019·2021·2022(3년 추적)·2023(2년 추적)으로 늘리고 후보 신호(수요 분모 포화·개업 러시·매출 추세)를 넣었다 — 결과 `docs/verdict-backtest-multi.md`
- 안정 신호(lift ≥ 1.10×인 시점 수): 전체 생존 절벽 4/4·조기 폐업 4/4·**개업 러시 4/4**(1.13·1.14·1.21·1.62)·포화(+유동 분모) 3/3. **일식·호프·주점·분식·헬스장·PC방은 안정 신호 없음**, 당구장·노래방은 표본 부족
- 상권 축소는 0.91~0.96×(0/3)로 정보가 없어 **판정 신호에서 제거**(사용자 결정, 등급 계산에는 원래 안 들어감)
- "비슷한 과거 사례"(kNN, 점포 기반 특징값 4개·최근접 30곳)의 3년 폐업률을 후보로 넣어 봤다 — 전체 1.20·1.19·1.37·1.72로 기존 신호와 같은 수준이고 음식은 더 약했다. 기존 신호가 빈 약 1,700개 동×업종을 메우지도 못해(1/4) **미채택**

### 9. 데이터 이용조건 정리 (BE v0.83.0~v0.85.0 · FE v0.59.0~v0.61.1)

원천 22개의 이용조건(공공누리 유형·상업 이용·변경·출처표시·저장 제한)을 점검하고(비공개 문서), 사용자 원칙 "데이터는 이용조건에 맞춰 쓴다"에 따라 필요한 조치를 차례로 했다.

- **뉴스(네이버 검색 API)는 원문 링크로만**(v0.83.0) — 특약(가공 없이 노출·AI 입력 금지·보관 21일)에 맞춰 리포트 본문(= 해석 입력)·RAG 색인에서 빼고, `facts.news`는 최근 21일 기사 원문 링크 3건만, 인용 저장 안 함, 수집기가 21일 지난 기사를 지운다. RAG 평가셋은 공고 200문항으로(260 → 200). 기존 저장분은 일회성 마이그레이션 두 개로 정리(v0.83.0~v0.83.1). 구글 뉴스 대체는 약관상 안 하기로
- **행정동 경계 원천 교체**(v0.84.0) — 브이월드 WFS(사전 승낙 없는 저장·재배포 금지) → vuski/admdongkor `ver20260701`(통계청 SGIS 경계 가공, CC BY 4.0). 427/427 코드가 그대로 맞아 동명 매칭 코드를 지웠다. 점포 841,461곳 중 1.2% 동 재배정, 지표·판정 재계산(5,124건 중 141건 바뀜), 정적 GeoJSON 5.4MB → **0.45MB**
- **지원사업 공고 원천 교체**(v0.85.0) — 기업마당 자체 API → 공공데이터포털판(15157820, 공공누리 제3유형 출처표시·변경금지). 같은 날 1,468건 대조 필드 차이 0. 변경금지라 사업개요 1,000자 자르기를 없애고 화면에 "출처: 기업마당"
- **데이터 출처 페이지 `/sources`**(FE v0.59.0) — 원천 18개·데이터셋 링크·이용조건·공공누리 유형 배지와 출처 문구, 모든 화면에 작은 공통 푸터. 리포트 뉴스는 "최근 뉴스 — 네이버 검색결과"로 표시
- 브이월드·SGIS 영리 이용 문의, ECOS 키 이용형태 확인은 **나중 마일스톤**(사용자 결정) — 발표까지 현행 유지, 유료 공개 전 확인

### 10. 지역 사건 적재·리포트 연결 (BE v0.86.0 · FE v0.62.0)

- 비어 있던 `shock_event_region`을 서울 열린데이터광장 3종으로 채움(`load_regional_events`, 2019년 이후, 재실행 멱등)
  - OA-22856 정비사업 이주·착공(주소는 SGIS 지오코딩 — 브이월드 지오코더는 결과 저장 금지), OA-16096 대규모점포 개설·폐업(SSM 제외), OA-15818 1,000세대 이상 입주
  - 첫 적재 **307건·151개 동**(정비 157·대규모점포 84·입주 66), 위치를 못 정한 12건은 저장하지 않고 로그만. 정책 충격 조회에는 섞이지 않게 분리
- 리포트 조건 절에 "[확인된 사실] ○○동 지역 사건(최근 3년, 서울 열린데이터광장): 2025-08 … (출처: OA-xxxxx 데이터셋)" 줄 — 최대 5건, 날짜는 달까지(인허가일 ≠ 개점일), 사건이 없으면 줄 생략. 뉴스 대신 공식 사건만
- 평가 facts 150건에 한 번 채움(사건 있는 시나리오 40건) → 3.8 9 → 3·오퍼스 4 → 2, 해석이 사건을 언급한 문장 중 오류 0이라 적용
- 프론트는 `regional_events` 선택 타입·결정적 mock(Codex). main 머지·8200 재빌드·실리포트(명동 카페) 확인, 수집 크론 매주 월 06:00 등록

### 11. 판정 근거 약한 업종·조기 폐업 오독 가드 (`feat/weak-basis-guard` → 10/7 마무리)

- 8번 백테스트에서 안정 신호가 없거나 표본이 부족한 7개 업종(일식·호프/주점·분식·헬스장·PC방·당구장·노래방)은 판정은 내되 **비추천(🔴)은 내지 않고 최대 조건부**, 판정 절에 "판정 근거 약함 — …" 문장(사용자 결정)
- 해석 가드에 조기 폐업 오독 문장 삭제(`drop_early_closure_misreads`) — 첫판이 생존 절벽과 조기 폐업을 함께 바르게 푼 문장까지 지워, "조기 폐업" 앞뒤 구만 보도록 고쳤다
- 프론트 v0.63.0 — 판정 카드 "판정 근거 약함" 배지·툴팁(Codex). 평가·머지는 10/7(아래)

### 12. 문서·인프라

- **AWS·EKS 이전 계획 초안**(비공개) 작성 후 Phase 0 코드 준비를 별도 워크트리 `feat/k8s-phase0`에서 시작 — readiness·DB 풀 env·비루트 Dockerfile(v0.80.0), EKS 매니페스트 `deploy/k8s`(v0.81.0), 행정동 경계 파일을 이미지에 넣고 정적 파일로 내보내는 CLI(v0.81.1~v0.82.0), 프론트는 경계를 정적 파일로 받기(FE v0.58.0). 미머지
- 옛 `HANDOFF-260918`·`RESUME-260923` 삭제 — 남길 내용(생활인구 해석 주의·빅데이터캠퍼스 반출 정책)은 `docs/api.md` §2-2·§8로 옮겼다
- `docs/HANDOFF.md` §0-15~§0-18(오늘 끝난 것·이어서 할 일 정본·평가 방법·작업 규칙), `docs/STATUS.md`(점포 좌표 결측 항목 닫음 — 주소 없는 옛 폐업 점포, 편의점·부동산 재포함은 나중 마일스톤)

### 다음 작업

- [x] `feat/weak-basis-guard` 마무리 — 10/7 판정 근거 약함 적용, 조기 폐업 가드 미적용
- [ ] 노트북 브라우저 확인 — 질문에 대한 답 상자, 위험 등급 라벨, `/sources`·푸터, 지역 사건 줄, 판정 근거 약함 배지
- [ ] 판정 신호 제품 결정 남은 것 — ~~업종별 신호 선택~~(10/7 판정 근거 약함), 폐업 뒤 개업이 끊긴 동 신호(사람 3차 메모)
- [ ] `feat/k8s-phase0` — main(새 경계)을 받아 다시 확인 후 머지, 다음 K1·K11
- [ ] 키워드 규칙 한계("3억이 있는데", "월세 300만 원"을 예산으로), 경고 없음을 긍정으로 읽는 해석
- [ ] 이월: 앱 실배포(Vercel·터널 토큰), 부하 테스트(k6), 프론트 프록시 허용 목록, 이용조건 5번(유료 공개 전)

## 2026-10-07

자정을 넘겨 전날 이어 하던 판정 신호 정리를 마쳤다. 여러 시점 백테스트에서 경고 신호가 폐업을 꾸준히 가르지 못한 7개 업종은 **"판정 근거 약함"으로 표시하고 비추천을 내지 않게** 했고, 함께 시험한 조기 폐업 오독 가드는 평가 결과에 따라 넣지 않았다.
오전에는 의도 관문 모델을 gemini-3.8-flash 일반 모드로 바꾸고, **지원사업 공고를 규칙으로 거른 뒤 질문 유사도(bge-m3)로 정렬하는 하이브리드 검색**을 넣어 RAG를 요청 경로에 다시 올렸다.
낮부터 밤까지는 **부하 테스트를 1~7차까지 돌리며 측정으로 확인된 병목만 하나씩 고쳤다** — 공고 목록 캐시, 워커 4개 + 분석 대기 장부 Postgres, stores 부분 인덱스, geojson 미리 압축. 혼합 처리량 천장은 **약 185 → 약 585 RPS**, 기준을 지킨 최대 동접은 약 500명 → **약 1,830명**이 됐다.
Backend **v0.86.0 → v0.94.0**, Frontend **v0.62.0 → v0.64.2**. main 커밋 27개(00:03 ~ 22:42, 머지 포함), origin 푸시 `f6fcb7f`까지.

### 1. 판정 근거 약함 (BE v0.87.0 · FE v0.63.0)

- 대상: 여러 시점 백테스트(`docs/verdict-backtest-multi.md`)에서 lift ≥ 1.10×가 3번 이상인 신호가 하나도 없는 **일식·호프/주점·분식·헬스장·PC방·당구장·노래방**(사용자 결정)
- 판정 규칙 목록을 업종별로 고른다(`rules_for`) — 이 업종들은 비추천 규칙을 뺀 목록이라 강한 신호가 둘이어도 **최대 조건부**
- 판정 API·리포트 facts에 `weak_basis`, 리포트 판정 줄에 "판정 근거 약함 — 이 업종은 과거 여러 시점에서 경고 신호가 폐업을 꾸준히 가르지 못해, 신호가 켜져도 비추천은 내지 않습니다", 지도 판정 카드에 배지·툴팁(Codex)
- 판정 재계산: 해당 업종 비추천 14건 → 조건부. 분포 🔴62·🟠1,872·⚪1,184·보류 2,006. 8200 재빌드 후 API 확인(분식 `weak_basis=True`, 카페 False)

### 2. 조기 폐업 오독 가드 — 미적용 (`exp/early-closure-guard`)

- 11·12단계 평가에서 반복된 오류 — 해석이 "조기 폐업(문 닫은 점포의 영업 기간)"을 "새로 연 점포가 버티는 기간"으로 풀이
- 해석에서 그런 문장을 지우는 가드를 만들었다. 첫판은 생존 절벽(새로 연 점포)과 조기 폐업을 한 문장에 바르게 푼 문장까지 25개를 지워, "조기 폐업" 바로 앞뒤 구만 보도록 고쳤다(실제 오독만 남김)
- 150건 재평가(13단계, 1번과 함께): 3.8 핵심 오류 3 → 5 · 오퍼스 2 → 4. 늘어난 3.8 2건 중 하나는 가드가 "저녁 매출이 하루 평균보다 높다"와 오독이 섞인 문장을 통째로 지워 직접 답의 근거가 사라진 경우, 하나는 해석이 "판정 근거 약함"을 빼고 위험을 단정한 경우
- 결정: 판정 근거 약함은 제품 결정이라 적용, 가드는 문장 단위 삭제가 맞는 근거까지 지우고 판정된 오류도 줄지 않아 **미적용**(기록 브랜치). `docs/model-evaluation.md` 13단계

### 3. 의도 관문 모델 교체 (BE v0.88.0)

- 질문에서 동·업종을 뽑는 의도 관문 LLM을 gemini-2.5-flash → **gemini-3.8-flash 일반 모드**(사전 추론 끔, `thinking_budget=0`)로(사용자 결정)
- 같은 날·같은 조건(확정 80건 × 3회, 같은 지시문·스키마·온도 0): 동시 정답 **98.8% 대 95.0%**(차이 +3.7%p [−1.3, +10.0]), 지어내기 둘 다 0/26, p50 2.47초 대 1.70초. 2.5는 익선동·광장시장·건대입구 같은 랜드마크 변환과 헬스장 업종을 놓쳤다
- `GeminiIntentLlmAdapter(thinking_off=...)`, 벤치 모델 키 `gemini-3.8-flash`·`gemini-3.8-flash-nothink`. 정본 `docs/model-evaluation.md` §13

### 4. 지원사업 하이브리드 검색 (BE v0.89.0 · FE v0.64.0~v0.64.1)

10/5 코드 우선 구조로 바꾼 뒤 RAG가 요청 경로에서 빠져 있었는데, 지원사업 공고 검색에 다시 올렸다. 설계서 `docs/superpowers/specs/2026-10-07-funding-hybrid-design.md`.

- 규칙 필터(서울·전국 ∩ 소상공인·창업 대상 ∩ 미만료, 구 전용 제외)로 **자격을 먼저 거르고**, 그 후보 전체를 질문과의 코사인 거리(bge-m3)로 정렬. 질문이 없으면 이전과 같다(마감 임박 순, 임베딩 호출 없음)
- 세 방식 비교(평가셋 confirmed 175문항·상위 8건, `scripts/compare_funding_hybrid.py`)

| 방식 | 정답 Hit | 자격 밖 공고 노출 |
|---|---|---|
| 규칙만 | 0/6 | 0% |
| RAG만 | 6/6 | **97.3%** |
| **하이브리드** | **6/6** | **0%** |

- 결정 근거는 자격 밖 노출(정답 표본은 6문항뿐). rag BC `rank_within`, funding BC `QuestionRankerPort`·cross-BC 게이트웨이 `RagQuestionRankerGateway`, 도메인 순수 함수 `order_by_relevance`
- 개정 1 — **유사도 기준선** 거리 `≤ min(0.54, 1등 + 0.08)`만 "질문과 관련 있음"(10/7 실측: 자격 통과 74건 중 고용보험료 지원 1건·온라인 판로 2건 등), 검색 결과 8건 상한 제거
- 다른 지역 이름이 붙은 공고(소담스퀘어·지역 창조경제혁신센터 등, 74건 중 13건)는 제외하지 않고 **목록 뒤로**(사용자 결정)
- 질문 임베딩 대기는 5초(색인·CLI는 120초) — Ollama가 멈추면 규칙 순서·`order: "deadline"`으로 떨어진다. 리포트 지원사업 절은 질문으로 후보를 고르면 "질문과 가까운 순으로 골랐습니다." 한 문장
- 프론트 — 지원사업 화면 질문 검색·"질문과 가까운 공고" 절(v0.64.0), 관련 공고 건수와 8건씩 "더보기"(v0.64.1, Codex)
- RAG 설명을 실제 구현에 맞춤 — 리포트는 코드 우선, 지원사업은 규칙+RAG 하이브리드(산출물 구조·`STATUS.md`·`agent-architecture.md` 머리말)

### 5. 부하 테스트 환경 (BE v0.90.0)

- **가짜 LLM** `LLM_MODE=fake` — 분석 해석·의도 폴백이 고정 3초만 쉬고 고정 값을 낸다. 테스트 컨테이너에서 Gemini 요금·한도가 나가지 않게(운영 배선은 그대로)
- `scripts/load/` — k6 혼합 부하(`load.js`, smoke·load·stress·spike·soak·llm·천장 프로필), API별 단독 계단(`endpoint.js`), 환경 스크립트(테스트 DB 5437·테스트 API 8202·CPU 분리), 단계 실행기 `run_stage.sh`(API 재시작·`pg_stat_statements` 초기화·모니터·느린 쿼리를 단계 폴더에). 합격 기준은 `testplan` §5(10/7 확정)
- 2차부터 시나리오 보강 — 지원사업 질문 검색·질문 있는 분석 추가, `/profiles`의 정상 404(자료 없는 동)는 성공으로 셈(1차 k6 실패의 99% 이상이 이것)
- 원격 측정 준비 — k6를 Windows PC에서 돌리고(Tailscale로 테스트 API만 노출, 끝나면 닫음) 서버는 단계 시작·끝(`stage_begin/end`)과 자원 모니터만

### 6. 부하 테스트 1~7차와 성능 개선 (BE v0.91.0~v0.94.0 · FE v0.64.2)

차수마다 **바꾼 것 하나**만 넣고 같은 조건(API 논리 CPU 4개, 파일 한도 1,024, 가짜 LLM)으로 다시 쟀다.

| 차수 | 바꾼 것 | 워커 · k6 위치 | 혼합 천장 RPS | 기준(일반 GET p95 500ms) 지킨 최대 동접 | 먼저 찬 곳 |
|---|---|---|---|---|---|
| 1차 | 기준선(BE v0.88.0, 검색 없음) | 1 · 서버 안 | 약 185 | 약 500명 | API CPU 1코어 몫(워커 1개) |
| 2차 | 하이브리드 검색 + 임베딩(v0.90.0) | 1 · 서버 안 | 약 164 | 약 450~470명 | 같음 |
| 3차 | 공고 목록 캐시(v0.91.0) | 1 · 서버 안 | 약 213 | 약 550명 | 같음 |
| 4차 | 워커 4 + 분석 대기 장부 Postgres(v0.92.0) | 4 · 서버 안 | ≥ 343(천장 못 잼) | ≥ 1,000명 | 1,000명까지 안 나타남 |
| 5차 | 같은 코드, k6만 원격 PC로 | 4 · 원격 | 약 470 | 약 1,450명 | API CPU 4코어(391~400%) |
| 6차 | stores 부분 인덱스(v0.93.0) | 4 · 원격 | 약 505 | 약 1,620명 | API CPU |
| 7차 | geojson 미리 압축(v0.94.0) | 4 · 원격 | **약 585** | **약 1,830명** | API CPU |

> 상세: [부하 테스트 — 몇 명까지 버티고, 어디서 먼저 막히나]({{ '/docs/load-test.html' | relative_url }}) (방법·합격 기준·차수별 근거·임베딩 서버 실험·한계)

- 목표 TPS 1,500 대비 천장은 **약 12% → 약 39%**. 진짜 에러는 모든 차수에서 0.02% 아래이고, 전부 POST 연결 끊김(uvicorn keep-alive 만료와 겹치는 경합으로 추정)이다. HTTP 5xx·`Too many open files` 0
- 1차 다른 단계 — Spike 500명(10초) 회복 0초, Soak 50명 110분 p95 −0.4%(메모리 +2.4MiB/시간, 아주 느린 누수와는 구분 못 함), Gemini 단독 동시 분석 최대 33건·분당 약 440회에서 429 0건. 다만 이때 지도 API p95가 449ms로 기준 턱밑 — 분석과 지도가 같은 워커를 나눠 써서 → 워커 증설의 근거
- **공고 목록 캐시**(v0.91.0) — 2차 검색 단독 계단이 40 RPS에서 깨짐, `support_guide` CPU 약 23ms 중 마감 전 1,521건 읽기가 13ms. `list_open_all()`을 10분 TTL 캐싱 Proxy로 감싸 API와 리포트가 공유
- **분석 대기 장부 Postgres**(v0.92.0) — 워커를 늘리면 `POST /analysis`와 `GET /analysis/{id}/events`가 다른 워커로 가 404가 난다. 메모리 dict 대신 `analysis_pending` 테이블(30분 만료, 저장할 때 지난 행 정리, 크론 없음). 수명 몇 초·요청의 약 0.6%라 Redis를 새로 두지 않았다. 마스터에 없는 동·업종은 404로 거절(프론트 mock도 같이 404, FE v0.64.2 Codex). 8200 워커 4개(4 × DB 풀 15 = 60 ≤ `max_connections` 100)
- **stores 부분 인덱스**(v0.93.0) — 5차에서 동·업종 점포 목록 쿼리가 DB 시간의 약 66%(평균 27.5ms). 업종 전체(카페 약 14.8만 행)를 읽고 동으로 거르던 것을 `(region_code, industry_id, store_id) WHERE 영업 중·좌표 있음` 인덱스로 — 단건 35.7 → 1.7ms, 부하 중 평균 0.2ms, 요청당 DB CPU 4.3 → 1.8ms. **천장은 +7~8%뿐** — 병목이 API CPU라서
- **geojson 미리 압축**(v0.94.0) — 경계 JSON(439KB)·gzip(81KB)을 한 번만 만들어 재사용, 요청당 CPU 40.8ms → 0(응답 계약 불변). 7차에서 요청당 API CPU 5.8 → 4.2ms(1,000명, 예상 절감 1.6ms와 일치), **1,500명이 처음으로 3분 유지·모든 API 임계 합격**(6차는 search p95 542ms로 불합격), 2,000명 일반 GET p95 2.4초 → 0.87초
- 원격 PC(Windows) CPU는 천장 구간 평균 약 30%라 측정 도구가 한계는 아니었다 — 천장은 서버 쪽
- **임베딩 서버 실험**(Ollama bge-m3, GPU 1장) — 상한 약 43건/초. 병렬 설정·인스턴스 2대는 효과 없음(임베딩 모델에 `n_seq_max = 1`), 한 호출에 64문장을 묶으면 190건/초 → 병목은 GPU가 아니라 호출을 1건씩 처리하는 방식. 혼합 부하에서는 약 3,300 RPS까지 감당(추정), 검색만 몰리면 초당 30~43건이 상한
- 측정 공백 — k6는 geojson만 gzip을 요청한다(실브라우저는 1KB 넘는 JSON을 전부 gzip으로 받으므로 실서비스 요청당 CPU는 더 크다). 가짜 LLM·차수별 1회 실행
- 결과·계획·서버 이전 수치는 비공개 문서(`docs/plan/`, `testplan`·`serverplan`)에 차수별로 정리

### 7. 문서

- `docs/HANDOFF.md` §0-19 — 10/7 기준 정본(지금 상태·다음 할 일·나중 마일스톤·정리 거리·작업 규칙). §0-18은 10/6 기록으로
- 원천 이용조건 확인(브이월드·SGIS·ECOS)은 `docs/STATUS.md` §4-5 나중 마일스톤 — 발표까지 현행 유지
- 단일 시점 판정 백테스트(`docs/verdict-backtest.md`)를 판정 근거 약함 반영 뒤로 다시 산출 — 🔴 79 → 52곳, lift 1.70× → **1.75×**
- BM 제안 문서는 비공개 기획 문서로 합쳐 정리, HANDOFF 공개 저장소 점검 목록도 맞춤

### 다음 작업

- [ ] 노트북 브라우저 확인 — 질문에 대한 답 상자, 위험 등급 라벨, `/sources`·푸터, 지역 사건 줄, 판정 근거 약함 배지, 기업마당 출처, 지원사업 질문 검색·더보기
- [ ] 다음 천장 — 요청당 API CPU 줄이기(판정 조회 캐시 등) 또는 API 코어 증설, 실브라우저 gzip 몫 측정, POST 연결 끊김(keep-alive) 확인
- [ ] 검색 단독 임베딩 상한(약 43건/초) — 어댑터 마이크로 배치 또는 배치 지원 임베딩 서버, 효과를 재고 결정
- [ ] `feat/k8s-phase0` — main(새 경계)을 받아 다시 확인 후 머지, 다음 K1·K11
- [ ] 배포 준비 — 프론트 프록시 허용 목록, 실배포(Vercel·터널 토큰)
- [ ] 조기 폐업 오독은 가드 말고 다른 방법으로, 폐업 뒤 개업이 끊긴 동 신호, 질문 키워드 규칙 한계

## 2026-10-08

오전에 부하 테스트 8·9차를 돌렸다. 7차에서 DB 시간 1위였던 **판정 조회를 캐시**하자, 동접 2,000명에서도 서버가 절반 정도만 썼다. 이어 계단을 3,000명까지 늘려 천장을 다시 쟀다. 혼합 처리량 천장은 **약 585 → 약 925 RPS**(목표 TPS 1,500의 약 62%)로 올랐고, 기준을 지킨 최대 동접은 약 1,830명 → **약 2,900명**이 됐다.
낮에는 9차 결과로 발표 자료와 서버 이전 계획을 다시 맞췄다. 서버 이전 계획은 **운영 10/14~10/27·정리 10/28~10/31** 기준으로 다시 세웠다. 저녁에는 분석 화면의 다음 단계 링크를 헤더로 옮겼다.
Backend **v0.94.0 → v0.95.0**, Frontend **v0.64.2 → v0.65.0**. main 커밋 4개(00:30 ~ 18:11), origin 푸시 `eff4d87`까지.

### 1. 판정 경로 캐시 (BE v0.95.0)

- 근거 — 7차에서 DB 시간 1위가 업종별 판정 전체 조회(`list_by_industry`, 427개 동, 9.9만 회·218초)였다. 지도 색칠과 함께 **동을 클릭할 때마다 부르는 대안 추천**도 이 조회와 동 목록 조회(`regions()`)를 매번 했다. 판정은 새벽 배치로 하루 한 번만 바뀐다
- 두 조회를 각각 10분 TTL 캐싱 Proxy로 감쌌다(공고 목록 캐시와 같은 형식, 프로세스당 1개). 판정 저장(`upsert`·`delete_other_industries`) 뒤에는 캐시를 비운다 — 배치 CLI도 같은 배선을 쓰기 때문
- 단건 실측(서교동 카페) — 대안 추천 CPU 7.11 → 1.04ms, 지도 색칠 4.90 → 0.27ms, 응답 바이트 동일. 테스트 1,303개 통과

### 2. 부하 테스트 8·9차

| 차수 | 바꾼 것 | 워커 · k6 위치 | 혼합 천장 RPS | 기준 지킨 최대 동접 | 먼저 찬 곳 |
|---|---|---|---|---|---|
| 7차 | (10/7) geojson 미리 압축 | 4 · 원격 | 약 585 | 약 1,830명 | API CPU |
| 8차 | 판정 경로 캐시(v0.95.0) | 4 · 원격 | ≥ 689(2,000명에서 포화 안 함) | ≥ 2,000명 | 2,000명까지 안 나타남 |
| 9차 | 같은 코드, 계단을 3,000명까지 | 4 · 원격 | **약 925** | **약 2,900명** | API CPU 4코어(371%) |

> 상세: [부하 테스트 — 몇 명까지 버티고, 어디서 먼저 막히나]({{ '/docs/load-test.html' | relative_url }})

- 8차 — 요청당 API CPU 4.2 → **2.2ms**(1,000명, −48%), 요청당 DB CPU 1.6 → 0.9ms. 2,000명에서도 수요(689 RPS)를 전부 처리했고 API CPU는 189%(7차 389%). 천장 측정에서 처음으로 k6 기준을 모두 통과했다(p95 24.95ms)
- 9차 — 2,500명(860 RPS)은 수요를 전부 처리했고 3분 유지 동안 모든 API가 기준 안에 들었다. 3,000명에서 923 RPS(수요 1,032)·API CPU 371%로 포화. 2,000명까지는 8차를 재현했다(687 vs 689 RPS). 열린 파일 한도 1,024는 3,000명(워커당 약 750 연결)에서도 벽이 아니었다(EMFILE 0)
- 다음 DB 부담 1위는 상권 매출 백분위 쿼리(평균 17.2ms)
- 진짜 에러는 여전히 POST 연결 끊김뿐이다(9차 52건, HTTP 5xx 0)
- 측정은 서버 세션과 원격 PC(Windows) k6 세션으로 나눠 진행했다. 테스트 API를 Tailscale 주소로 여는 단계는 권한 확인에 걸려 사람이 직접 실행했다

### 3. 분석 화면 다음 단계 링크를 헤더로 (FE v0.65.0)

- 리포트 하단 카드에 있던 다음 단계 링크를 **상단 헤더의 작은 버튼**으로 옮겼다. URL의 동·업종·선택 예산을 그대로 넘기고, 리포트가 끝나기 전부터 보인다. 좁은 화면에서는 제목 아래로 줄을 바꾼다
- 완료된 리포트 본문 끝에 `↑ 맨 위로` 버튼을 달았다. 동작 줄이기 설정이 켜져 있으면 바로, 아니면 부드럽게 올라간다
- 헤더 링크의 주소·표시 조건, 하단 버튼의 완료 조건·스크롤 동작을 컴포넌트 테스트로 고정(Codex 구현). 브라우저 확인 뒤 커밋·푸시

### 4. 서버 이전 계획 재계산 (비공개 문서)

- 9차 실측(요청당 API CPU 약 3.0ms·DB 약 1.5ms, 사용률 약 65% 구간)으로 단계별 하드웨어와 월 비용을 다시 계산했다. 같은 단계에서 필요한 API vCPU가 7차 기준보다 약 42% 줄었고, 월 비용은 약 20~40% 줄었다. AWS vCPU 보정 계수(×1.8)는 아직 검증하지 않았다
- `serverplan` §20을 새로 썼다. 10/6 초안에 숫자를 덧대는 대신, 지금 아는 것만으로 처음부터 다시 세운 계획이다
  - 기간: **운영 10/14~10/27(14일, 발표 뒤 종료) + 정리 10/28~10/31**. 단가는 서울 리전 공식 단가표에서 직접 뽑았다
  - 9차 실측 기준 병목은 API CPU가 1순위, DB가 2순위였다. 임베딩은 요청의 1.3%라 GPU 노드 안은 근거가 사라졌다. 분석 대기 장부(K1)와 geojson 압축(K3)이 main에 들어가 있어 ElastiCache·CloudFront도 필요 없다
  - 권장안은 실운영 사양을 상시로 켜 두고 남는 크레딧을 부하·장애·복구 리허설(증거)에 쓰는 것. 정리 기간에도 운영 구성을 그대로 두면 예산을 넘으므로, 10/27 밤에 서비스를 내리면서 최소 구성으로 줄이는 종료 절차를 함께 적었다
  - 로드밸런서는 **ALB 1개**. Ingress + AWS Load Balancer Controller로 만들고 대상은 파드 IP, 분배는 least outstanding requests(짧은 조회와 긴 SSE가 섞여서), idle timeout 300초, 스티키 세션 끔으로 설정한다. NLB는 쓸 이점이 없다
  - 부하 테스트 방식과 TPS 정의(질의응답용) — **TPS = RPS = 백엔드 API 호출 1건/초**(화면·정적 파일 제외). 9차 천장 925 RPS ÷ 1,500 ≈ 62%, 동접 환산은 RPS ÷ 0.344. TPS 1,500은 업계 기준이 아니고 예상 동접에서 거꾸로 잡은 눈금이다
- 이전 첫 작업은 여전히 `feat/k8s-phase0`(5커밋, main이 62커밋 앞섬)를 main에 다시 얹는 것

### 5. 발표 자료 (비공개 문서)

- 부하 테스트 슬라이드와 부록을 9차 결과(천장 약 925 RPS)로 고치고, 버전 번호·테스트 수·질의응답 틀도 함께 맞췄다. 비용 표를 다듬고 비용 결정 장을 더해 **개정본 62장**이 됐다(비교용으로 7차 기준 61장판도 보관). 바뀐 장만 따로 뽑은 파일도 만들었다
- 공개 요약 `docs/load-test.md`도 9차까지 반영(오전 커밋)

### 다음 작업

- [ ] 상권 매출 백분위 쿼리(9차 DB 시간 1위) 또는 API 코어 증설 — 다음 천장
- [ ] AWS로 옮긴 뒤 같은 시나리오로 다시 측정해 vCPU 보정 계수 확정
- [ ] 실브라우저 gzip 몫 측정, POST 연결 끊김(keep-alive) 확인
- [ ] `feat/k8s-phase0` main에 다시 얹기(버전 번호 재부여) → K11(SSE keep-alive)·K2 — 10/14 운영 시작 전
- [ ] 이월: 노트북 브라우저 확인, 검색 단독 임베딩 상한, 배포 준비

## 2026-10-09

부하 테스트 10차를 돌렸다. 9차까지 k6는 행정동 경계만 압축해서 받았지만, 실제 브라우저는 1KB 넘는 응답을 전부 gzip으로 받는다. 이 차이를 메우려고 서버 코드는 그대로 두고 **k6가 모든 요청을 압축해 받게** 바꿨다. 천장은 **약 925 → 약 900 RPS**(−3%)로 거의 그대로였고, 기준을 지킨 최대 동접도 약 2,900명으로 같았다. 압축에 드는 CPU가 작아서 서버 이전 사양은 바꾸지 않는다.
Backend·Frontend 변경 없음. main 커밋 1개(k6 스크립트, 15:58), origin 푸시 `fecbe58`까지.

### 1. 부하 테스트 10차 — 전 요청 gzip

| 차수 | 바꾼 것 | 요청당 받은 데이터 | 혼합 천장 RPS | 기준 지킨 최대 동접 | 모든 API 합격 | 먼저 찬 곳 |
|---|---|---|---|---|---|---|
| 9차 | (10/8) 계단 3,000명까지, 경계만 gzip | 6.6KB | 약 925 | 약 2,900명 | 2,500명 | API CPU 4코어(371%) |
| 10차 | 모든 요청 gzip(실제 브라우저 조건) | **4.3KB**(−35%) | **약 900** | 약 2,950명 | 2,500명 | API CPU 4코어(380%) |

- k6에 `GZIP=1` 옵션을 넣어 모든 요청에 `Accept-Encoding: gzip`을 붙였다. 값을 주지 않으면 1~9차와 똑같이 돌아서 이전 차수와 비교가 깨지지 않는다. k6는 기본으로 이 헤더를 보내지 않는다는 것도 확인했다 — 9차까지 경계만 압축됐던 이유다
- 서버는 이미 1KB 넘는 응답을 gzip으로 보내게 돼 있었다(`GZipMiddleware`). 예를 들어 지도 색칠에 쓰는 업종별 판정 목록은 19KB → 1.4KB로 줄었다
- 요청당 API CPU는 2,500명까지 2.0~3.0ms로 9차와 같았다(차이가 측정 흔들림 ±0.3ms 안). 서버가 꽉 찬 3,000명에서만 4.0 → 4.2ms로 조금 늘었다. 3,000명 유지 평균은 923 → 898 RPS
- 일반 GET p95가 2,000명 이하에서도 3~6ms씩 낮게 나왔는데, 원인은 확인하지 못했다. 전송량 차이는 1Gbps에서 0.2ms 미만이라 주원인으로 보기 어렵다
- 진짜 에러는 여전히 POST 연결 끊김뿐이다(35건, 9차 52건, HTTP 5xx 0). 열린 파일 한도 오류 0. 부하를 만든 Windows PC는 CPU 평균 33%로 여유가 있어 천장은 서버 쪽이다
- 9차처럼 서버 세션과 Windows 쪽 세션이 나눠 측정했다. 결과 문서는 Windows 쪽 세션이 쓰고, 서버 세션이 원본 기록으로 다시 계산해 검수했다(문장 3곳 정정)

### 2. 서버 이전 계획 반영 (비공개 문서)

- 천장 표기만 925 → 약 900 RPS(브라우저 조건)로 바꿨다. 요청당 CPU로 잡은 환산 계수와 단계별 사양·비용표는 차이가 3% 안이라 그대로 둔다
- 로드밸런서 처리 바이트 어림에 쓰는 평균 응답 크기를 4.3KB로 고쳤다. 이전 가정("브라우저 gzip이면 약 1/4")은 과했다 — 실측은 약 65%
- 개선 후보의 "gzip 비용 측정"은 측정 완료·조정 불필요로 정리했고, 질의응답용 한 줄 답도 약 900 RPS·동접 약 2,900명으로 맞췄다. AWS 재측정도 `GZIP=1`로 한다

### 다음 작업

- [ ] 상권 매출 백분위 쿼리(10차도 DB 시간 1위, 평균 17.0ms) 또는 API 코어 증설 — 다음 천장
- [ ] AWS로 옮긴 뒤 같은 시나리오(`GZIP=1`)로 다시 측정해 vCPU 보정 계수 확정
- [ ] POST 연결 끊김(keep-alive) 확인
- [ ] 공개 요약 `docs/load-test.md`·블로그에 10차 반영
- [ ] `feat/k8s-phase0` main에 다시 얹기(버전 번호 재부여) → K11(SSE keep-alive)·K2 — 10/14 운영 시작 전
- [ ] 이월: 노트북 브라우저 확인, 검색 단독 임베딩 상한, 배포 준비
