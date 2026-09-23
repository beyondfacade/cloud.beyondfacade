---
layout: post
title: 개발 일지
permalink: /docs/devlog.html
date: 2026-09-22
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

- [ ] **PR #1 리뷰 → main 머지**, 이어서 `codex/seoul-atlas-landing` 리베이스와 Frontend v0.14.0 번호 재배정
- [ ] 두뇌 채택 **A/B/C** 팀 결정 → Composition Root 기본 모델 확정
- [ ] RAG 평가셋 candidate 50건 검수 → confirmed 승격 후 Recall@5 본지표 산출
- [ ] `docs/api.md`에 `/analysis` 3종·`/stores` 주소 필드 반영
- [ ] Vercel 앱 프로젝트 신설(`NEXT_PUBLIC_API_BASE` + 백엔드 터널) — 현재 CLI 계정에 Metabole 프로젝트 없음
- [ ] `funding_program_industry` 구현·어린이집 폐업률 산출 방식·연령별 인구 2026.07분·AWS G 쿼터 등 이월 항목 유지
