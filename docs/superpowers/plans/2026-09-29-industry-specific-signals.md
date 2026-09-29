# 업종 특화 신호 (편의점 담배권 이력 · 부동산 집계 판정) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 판정에서 빠진 편의점·부동산을 원천을 바꿔 다시 판정한다 — 편의점은 담배소매인 인허가 이력(+ 담배권 빈자리 참고 신호), 부동산은 서울시 상권분석 동×분기 집계(+ "집계 기반" 표시). 백테스트 게이트를 통과한 업종만 판정 대상에 다시 넣는다.

**Architecture:** verdict BC 안에 **업종별 원천 Strategy**를 둔다. 도메인 `SignalProfile`(어떤 신호를 어떤 원천 표기로 돌리나 + `basis`)과 출력 포트 `IndustrySignalDataPort`(창 집계·점포수·진입 결과) 한 쌍(`IndustrySource`)을 업종 id로 등록하고, 인터랙터는 `dict.get(industry_id, 기본 인허가 원천)`으로 찾기만 한다. 편의점 원천은 담배소매인을 브랜드 사전으로 골라 같은 지번 ±90일 승계를 접은 "에피소드"로 기존 창 집계를 그대로 재현하고, 부동산 원천은 `region_commerce_store`(CS200033)로 폐업률·포화를 만든다. 판정 행에 `basis`(permit·proxy·aggregate) 컬럼을 더해 API·카드 배지까지 싣는다. 백테스트 CLI에 `--candidates` 재포함 심사 절과 게이트 판정을 붙인다.

**Tech Stack:** FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL · pytest(`beyondfacade_test` DB) · Python 3.14 / Next.js App Router · TanStack Query · Vitest (프론트는 Codex 구현)

**Spec:** `docs/superpowers/specs/2026-09-29-industry-specific-signals-design.md` (이하 "설계서"). 선행: `docs/superpowers/specs/2026-09-28-verdict-card-design.md` (이하 "판정 카드 설계서")

## Global Constraints

- **버전**: 백엔드 **v0.46.0**, 프론트 **v0.33.0** (현재 BE v0.45.0 · FE v0.32.0). 백엔드 첫 코드 태스크(Task 3)가 `backend/docs/backend_ver_log.md` 맨 위에 `## [v0.46.0] - 2026-09-29` 항목을 만들고, 이후 백엔드 태스크는 **같은 항목**의 `### Added`/`### Changed`에 한 줄씩 덧붙인다. 프론트는 Task 14가 `frontend/docs/frontend_ver_log.md`에 `## [v0.33.0] - 2026-09-29`를 만들고 Task 15가 덧붙인다. 새 버전 번호를 따로 만들지 않는다.
- **브랜드 사전** (설계서 §5-1, 도메인 상수 `BRAND_PATTERNS`, 대문자화한 상호에 `re.search`, 첫 일치가 이긴다):
  - `GS25`: `GS\s*25` · `지에스\s*25` · `LG\s*25` · `엘지\s*25`
  - `CU`: `(?<![A-Z])CU(?![A-Z])` · `씨유` · `훼미리\s*마트` · `패밀리\s*마트` · `FAMILY\s*MART` · `비지에프`
  - `세븐일레븐`: `세븐\s*-?\s*일레븐` · `7\s*-?\s*ELEVEN` · `(?<!\d)7-11(?!\d)` · `바이더웨이` · `BUY\s*THE\s*WAY` · `코리아세븐`
  - `이마트24`: `이마트\s*24` · `EMART\s*24` · `위드미` · `WITH\s*ME`
  - `미니스톱`: `미니스톱` · `MINI\s*STOP`
  - `기타 체인`: `365\s*플러스` · `홈플러스\s*365` · `스토리웨이` · `씨스페이스` · `C-?\s*SPACE` · `로그인\s*25`
  - 넣지 않는 것: 맨 `세븐`, 맨 `로그인`, `GS리테일`·`지에스리테일`(GS수퍼 혼재). convenience BC의 `extract_brand`는 건드리지 않는다.
- **승계 접기**: 같은 지번주소(공백 정규화)에서 **이미 닫힌** 에피소드의 폐업일 ±`SUCCESSION_GAP_DAYS = 90`일 안에 개업한 레코드는 그 에피소드에 잇는다. 영업 중 에피소드에는 잇지 않는다. `MIN_VALID_DATE = date(1990, 1, 1)` 이전 개업·동 미배정 레코드는 버린다.
- **담배권 빈자리**: 반경 `TOBACCO_GAP_RADIUS_M = 50.0`(도메인 상수, `apps/verdict/domain/services/tobacco_gap.py`), 후보 자리 가드 `VerdictThresholds.min_gap_candidates = 30`, 신호 키 `tobacco_gap`, **참고 신호**(`ADVISORY_SIGNAL_KEYS`).
- **임계값**: 기존 그대로 — 백분위 on 75 / strong 90, `min_sample = 10`, `min_population = 1000`, `min_evaluable = 2`. 이번 계획에서 바꾸지 않는다.
- **판정 원천 값**: `BASIS_PERMIT = "permit"` · `BASIS_PROXY = "proxy"` · `BASIS_AGGREGATE = "aggregate"`. 테이블 `region_industry_verdict.basis` `String(12) NOT NULL server_default 'permit'`, 마이그레이션 revision **`d0e1f2a3b4c5`**, down_revision **`c9d0e1f2a3b4`**(현재 head).
- **신호 키**: `SIGNAL_KEYS`(공통 5개, 불변) · `SPECIFIC_SIGNAL_KEYS = ("closure_rate", "tobacco_gap")` · `ALL_SIGNAL_KEYS = SIGNAL_KEYS + SPECIFIC_SIGNAL_KEYS` · `ADVISORY_SIGNAL_KEYS = {"shrinking", "tobacco_gap"}`. 실거래가 태스크(Task 10·11)를 하면 `"trade_per_office"`를 `SPECIFIC_SIGNAL_KEYS`·`ADVISORY_SIGNAL_KEYS`에 덧붙인다. 신호 `source` 새 값: `tobacco`(담배소매인) · `commerce`(상권분석 집계) · (Task 11을 하면) `molit`(국토부 실거래가).
- **원천 코드**: 상권분석 `industry_source_code.source_system = 'seoul_commercial'` — 부동산 `real_estate ↔ CS200033`, 편의점 `convenience_store ↔ CS300002`(이미 적재, 마이그레이션 `c7a4f2e19b35`). 테이블 `region_commerce_store`(PK `adstrd_code`·`service_industry_code`·`year_quarter`, 컬럼 `region_code`·`store_count`·`open_store_count`·`close_store_count`), `tobacco_retailer`(`retailer_id`·`name`·`region_code`·`designated_date`·`permit_date`·`close_date`·`cancel_date`·`jibun_address`·`lat`·`lng`·`status_code`).
- **부동산 신호**: `closure_rate`(최근 4분기 폐업 합 ÷ 4분기 전 점포수) + `saturation`(아카이브 점포수). 순유출은 쓰지 않는다(아카이브 개업 수가 2024Q1부터 0, 설계서 §2-3). 생존 절벽·조기 폐업은 `UnsupportedSignal`(사유 `"집계 원천 — 개별 점포 개업·폐업일이 없어 산출하지 않음"`).
- **재포함 게이트** (설계서 §8): 경고 lift = (🔴+🟠 폐업 ÷ 🔴+🟠 개업) ÷ (⚪ 폐업 ÷ ⚪ 개업) **≥ 1.10**. 표본 — `proxy`·`permit`: 경고·⚪ 각 개업 **≥ 50**, `aggregate`: 경고·⚪ 각 동×업종 **≥ 30**. 시점 T = **2022-06-30**, entry 365일, horizon 1,095일. 통과 → 백엔드 `EXCLUDED_INDUSTRIES`·프론트 `VERDICT_EXCLUDED_INDUSTRIES`에서 제거. 미달 → 유지하고 기록.
- **실거래가 파일럿 게이트**: `RTMSDataSvcAptTrade` 호출이 HTTP 200 + `resultCode ∈ {"00","000"}` + `totalCount > 0`일 때만 Task 10·11을 한다. 아니면 두 태스크는 건너뛰고 HANDOFF에 "외부 대기"로 적는다.
- `domain/`·`app/use_cases/`에서 FastAPI·SQLAlchemy import 금지. 다른 BC ORM 접근은 `adapter/outbound/gateways/`에서만. 업종·원천·상태로 분기하는 `if/elif` 금지 — 레지스트리(dict)·Strategy·Decorator·Null Object로(CLAUDE.md §5).
- 오류 바디 `{error:{code,message}}`, 제외 업종은 404 `INDUSTRY_NOT_FOUND`(불변).
- 테스트 제목은 한국어 서술문(파이썬 식별자에 이모지 금지). 백엔드: `cd backend && .venv/bin/python -m pytest tests/<file> -q` (기존 694 collected 전부 통과 유지). 프론트: `cd frontend && npx vitest run <path>` + `npx tsc --noEmit`.
- 개발 DB 쓰기는 Task 3(마이그레이션 적용)·Task 10(마이그레이션·실거래 적재, 조건부)·Task 16(판정 배치)에서만. 나머지 실DB 단계(Task 7·8 스모크, Task 12 백테스트, Task 13 분석)는 읽기만. 스크래치 스크립트는 커밋하지 않는다.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. 브랜치 `feat/industry-specific-signals` 그대로, 푸시하지 않는다.
- **프론트 태스크(14·15)는 Codex가 구현한다** — 컨트롤러가 `codex exec --cd frontend "<태스크 본문>"`으로 넘긴다.

---

## File Structure

**백엔드 — `backend/apps/verdict/`**

| 파일 | 책임 | 태스크 |
|---|---|---|
| 수정 `domain/entities/region_industry_verdict_entity.py` | `BASIS_*`, `RegionIndustryVerdict.basis`, `SPECIFIC_SIGNAL_KEYS`·`ALL_SIGNAL_KEYS`, `ADVISORY_SIGNAL_KEYS`+`tobacco_gap`, `EXCLUDED_INDUSTRIES`(게이트 결과) | 3·5·12 |
| 신규 `domain/services/convenience_history.py` | `BRAND_PATTERNS`·`brand_of`·`RetailerRecord`·`Episode`·`address_key`·`fold_successions` | 4 |
| 신규 `domain/services/tobacco_gap.py` | `TOBACCO_GAP_RADIUS_M`·`GeoPoint`·`blocked_counts` | 4 |
| 수정 `domain/services/signals.py` | `SignalInput.gap_*`, `SourcedSignal`·`UnsupportedSignal`·`ClosureRateSignal`·`TobaccoGapSignal` | 5 |
| 신규 `domain/services/profiles.py` | `SignalProfile`·`PermitProfile`·`TobaccoProxyProfile`·`AggregateProfile` | 5 |
| 수정 `domain/services/thresholds.py` | `min_gap_candidates = 30` | 5 |
| 수정 `domain/services/backtest.py` | 버킷 범위 표(`_SCOPES_OF_BASIS`), `ALL_SIGNAL_KEYS` 정렬, `quarter_of`·`shift_quarter`, `GatePolicy`·`GATE_POLICIES`·`GateResult`·`reinclusion_gate` | 6·8·9 |
| 수정 `app/dtos/region_industry_verdict_dto.py` | `RegionIndustryVerdictDto.basis`, `StoreSignalStat.gap_*`, `BacktestReportDto.industry_basis`·`gates`, `BacktestGateDto` | 3·5·6·9 |
| 수정 `app/ports/output/region_industry_verdict_port.py` | `IndustrySignalDataPort`, `IndustryCatalogPort.named_industries` | 6 |
| 수정 `app/ports/input/region_industry_verdict_use_case.py` | `backtest(..., industry_ids=None)` | 6 |
| 신규 `app/use_cases/industry_source.py` | `IndustrySource`·`PermitSignalData` | 6 |
| 수정 `app/use_cases/region_industry_verdict_interactor.py` | 원천 레지스트리, 원천별 1회 로드, basis, 백테스트 원천별 결과·게이트 | 3·6·9 |
| 수정 `adapter/outbound/orms/region_industry_verdict_orm.py`·`orm_mappers/…`·`inbound/api/schemas/…`·`inbound/mappers/…` | `basis` 왕복 | 3 |
| 수정 `adapter/outbound/gateways/industry_catalog_gateway.py` | `named_industries` | 6 |
| 신규 `adapter/outbound/gateways/tobacco_convenience_gateway.py` | `stats_from_episodes`·`TobaccoConvenienceSignalData` | 7 |
| 신규 `adapter/outbound/gateways/commerce_aggregate_gateway.py` | `CommerceAggregateSignalData` | 8 |
| 수정 `adapter/inbound/cli/backtest_verdicts.py` | `--candidates`, 심사 절, † 표기, 새 신호 칸 | 9 |
| 신규 `adapter/inbound/cli/real_estate_survivor_backcast.py` | 생존자 역산 표 (분석) | 13 |
| 수정 `dependencies/region_industry_verdict_dependencies.py` | `sources` 등록 | 7·8·11 |
| 신규 `backend/migrations/versions/d0e1f2a3b4c5_region_industry_verdict_basis.py` | `basis` 컬럼 | 3 |

**백엔드 — 조건부(실거래가 파일럿 통과 시)**: 신규 BC `backend/apps/housing/`(`apt_trade_count` 수집 전용 보조 테이블 — tobacco·rent 선례, 라우터 없음), 마이그레이션 `e1f2a3b4c5d6_apt_trade_count.py`, verdict `domain/services/legal_dong.py`·`adapter/outbound/gateways/apt_trade_gateway.py`·`TradeEnrichedSignalData`·`TradePerOfficeSignal` (Task 10·11).

**테스트 — `backend/tests/`**: 신규 `test_verdict_convenience_history.py`(4) · `test_verdict_profiles.py`(5) · `test_verdict_sources.py`(6) · `test_verdict_tobacco_source.py`(7) · `test_verdict_commerce_source.py`(8) · `test_verdict_backtest_cli.py`(9) · `test_verdict_survivor_backcast.py`(13), 수정 `test_verdict_repository.py`·`test_verdict_router.py`(3) · `test_verdict_build.py`·`test_verdict_backtest.py`·`test_verdict_alternatives.py`·`test_verdict_gateways.py`(6·8·9·12) · `test_verdict_thresholds.py`(12).

**프론트 — Codex**: `src/shared/api/types.ts` · `src/shared/verdict.ts`(+test) · `src/app/api/mock/fixtures.ts` · `src/app/api/mock/verdicts/[regionCode]/route.test.ts` · `src/shared/ui/verdict-card.tsx`(+test) · `src/features/map-explorer/components/verdict-section.tsx`(+test) · `src/features/map-explorer/components/side-panel.tsx`(+test).

**문서**: `docs/api.md`(1·2) · `docs/HANDOFF.md`(1·2·12·13·16) · 설계서 §17 진행 기록(매 조사·실측 태스크) · `docs/verdict-backtest.md`(12, 생성물) · `docs/STATUS.md`(16) · `docs/erd.md`(10, 조건부).

---

## 0단계 — 조사 (코드 없음)

### Task 1: LOCALDATA 부동산중개업 원천 재확인 (I)

설계서 §12. **조사·기록만**. 수집기·코드를 만들지 않는다.

**Files:**
- Modify: `docs/api.md` (188행 근처 "⚠️ 부동산중개업은 행안부 통합 목록에서 미확인" 줄 바로 아래에 날짜 붙은 하위 항목 추가)
- Modify: `docs/HANDOFF.md` §0-12 A (업종 특화 신호 항목 아래 하위 항목)
- Modify: `docs/superpowers/specs/2026-09-29-industry-specific-signals-design.md` §17 진행 기록 표에 1행

**Interfaces:**
- Consumes: 없음
- Produces: 문서 기록 한 줄 — "폐업일 있는 부동산중개업 원천: 있음(데이터셋 ID·컬럼) / 없음(확인한 곳 목록)". 이후 태스크는 이 결과에 의존하지 않는다(있어도 후속 과제).

- [ ] **Step 1: 행안부 인허가 목록에서 찾는다**

WebFetch(또는 `curl -sL`)로 아래를 열고 "중개"·"부동산"을 찾는다.
- `https://www.data.go.kr/tcs/eds/selectCoreDataView.do?coreDataInsttCode=1741000&coreDataSn=6` (국가중점데이터 — 행안부 인허가 212개 세부)
- `https://www.data.go.kr/tcs/dss/selectDataSetList.do?dType=API&keyword=%EB%B6%80%EB%8F%99%EC%82%B0%EC%A4%91%EA%B0%9C%EC%97%85` (API 검색 "부동산중개업")
- `https://www.data.go.kr/tcs/dss/selectDataSetList.do?dType=FILE&keyword=%EB%B6%80%EB%8F%99%EC%82%B0%EC%A4%91%EA%B0%9C%EC%97%85` (파일 검색)

기록할 것: 결과 데이터셋 제목·ID·제공기관, 상세 페이지 "항목(컬럼)"에 `폐업일자`·`영업상태`·`인허가일자`가 있는지.

- [ ] **Step 2: LOCALDATA 파일 목록과 서울 열린데이터를 본다**

- `https://www.localdata.go.kr/devcenter/dataDown.do?menuNo=20001` — 업종 목록에 "부동산중개업"(또는 "중개업")이 있는지.
- `https://data.seoul.go.kr/dataList/datasetList.do?searchValue=%EB%B6%80%EB%8F%99%EC%82%B0%20%EC%A4%91%EA%B0%9C` — 서울시 부동산 중개업 데이터셋의 컬럼 명세에 폐업일·상태구분이 있는지.

- [ ] **Step 3: 후보가 API로 열려 있으면 1회 호출로 컬럼을 확인한다**

후보가 data.go.kr 1741000 계열이면 기존 인허가 게이트웨이와 같은 모양이다. 슬러그는 상세 페이지의 엔드포인트에서 읽는다(추측 금지).
```bash
cd backend && PYTHONPATH=. .venv/bin/python - <<'EOF'
import httpx
from core.matrix.grid_keymaker_secret_manager import get_settings
SLUG = "<상세 페이지에 적힌 슬러그>"
r = httpx.get(f"https://apis.data.go.kr/1741000/{SLUG}/info",
              params={"serviceKey": get_settings().data_go_kr_api_key, "pageNo": 1, "numOfRows": 3, "returnType": "json"}, timeout=30)
print(r.status_code); print(r.text[:1500])
EOF
```
Expected: 200이면 응답의 날짜 컬럼 이름을 적는다. 403·"SERVICE_KEY_IS_NOT_REGISTERED"면 "활용신청 필요"로 적는다. 후보가 없으면 이 단계는 건너뛴다.

- [ ] **Step 4: 기록한다**

`docs/api.md` 188행 아래(들여쓰기 한 단계 더):
```markdown
      - 재확인(2026-09-29, 업종 특화 신호 설계서 §12): <있음 — 제목(ID), 폐업일 컬럼명, 호출 결과 | 없음 — 행안부 1741000 목록·data.go.kr API/파일 검색·LOCALDATA 파일 목록·서울 열린데이터 모두 부동산중개업 폐업일 원천 없음>. brainstorming.md:196의 "LOCALDATA 부동산중개업 개폐업 일자"는 <정정 | 확인>.
```
HANDOFF §0-12 A "업종 특화 신호" 항목 아래:
```markdown
  - [x] LOCALDATA 부동산중개업 재확인(9/29) — <결과 한 줄>. <있으면: "후속: 수집기 → 부동산을 permit 원천으로 옮겨 코호트 신호 복구">
```
설계서 §17 표에 `| 2026-09-29 | Task 1 LOCALDATA 재확인 | <결과 한 줄> |`.

- [ ] **Step 5: 커밋**

```bash
git add docs/api.md docs/HANDOFF.md docs/superpowers/specs/2026-09-29-industry-specific-signals-design.md
git commit -m "docs: LOCALDATA 부동산중개업 원천 재확인 결과 기록

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 국토부 실거래가 API 파일럿 (G 게이트)

설계서 §11-1·2. **결과가 Task 10·11의 실행 여부를 정한다.**

**Files:**
- Modify: `docs/api.md` (§3-2 ⑤ 활용신청 목록의 "국토부 상업업무용 부동산 매매 실거래가" 줄 아래 하위 항목)
- Modify: `docs/HANDOFF.md` §0-12 A 업종 특화 신호 항목 아래
- Modify: 설계서 §17 진행 기록

**Interfaces:**
- Produces: 판정 `G_PILOT = PASS | FAIL`. PASS = 아파트 매매(`RTMSDataSvcAptTrade`) 응답이 HTTP 200 + `resultCode ∈ {"00","000"}` + `totalCount > 0`. Task 10·11의 시작 조건.

- [ ] **Step 1: 세 서비스를 한 번씩 부른다 (강남구 2024-06)**

```bash
cd backend && PYTHONPATH=. .venv/bin/python - <<'EOF'
import re
import httpx
from core.matrix.grid_keymaker_secret_manager import get_settings
KEY = get_settings().data_go_kr_api_key
SERVICES = {
    "아파트 매매": "RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
    "아파트 전월세": "RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
    "상업업무용 매매": "RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade",
}
for label, path in SERVICES.items():
    r = httpx.get(f"https://apis.data.go.kr/1613000/{path}",
                  params={"serviceKey": KEY, "LAWD_CD": "11680", "DEAL_YMD": "202406", "pageNo": 1, "numOfRows": 10}, timeout=30)
    code = re.search(r"<resultCode>(.*?)</resultCode>", r.text)
    total = re.search(r"<totalCount>(\d+)</totalCount>", r.text)
    umd = re.findall(r"<umdNm>(.*?)</umdNm>", r.text)[:3]
    print(label, r.status_code, code and code.group(1), total and total.group(1), umd, r.text[:200].replace("\n", " "))
EOF
```
Expected: 줄 3개. 아파트 매매가 `200 000 <수백> ['역삼동', ...]` 모양이면 PASS. `403`·`SERVICE_KEY_IS_NOT_REGISTERED_ERROR`·`resultCode` 없음이면 FAIL.

- [ ] **Step 2: 기록한다**

`docs/api.md` 해당 줄 아래:
```markdown
    - 파일럿(2026-09-29, 업종 특화 신호 §11): 아파트 매매 <HTTP·resultCode·totalCount> · 아파트 전월세 <…> · 상업업무용 매매 <…>. 응답 법정동 필드 `umdNm`.
```
HANDOFF §0-12 A 업종 특화 신호 아래:
- PASS: `  - [ ] 실거래가(아파트 매매 건수) 참고 신호 — 파일럿 통과(9/29), Task 10·11 진행`
- FAIL: `  - [ ] **외부 대기** 국토부 실거래가 — 아파트 매매 <상태>. data.go.kr에서 "국토교통부_아파트 매매 실거래가 자료" 활용신청 후 Task 10·11 재개(계획서 2026-09-29-industry-specific-signals)`

설계서 §17: `| 2026-09-29 | Task 2 실거래가 파일럿 | PASS/FAIL — <세 줄 요약> |`.

- [ ] **Step 3: 커밋**

```bash
git add docs/api.md docs/HANDOFF.md docs/superpowers/specs/2026-09-29-industry-specific-signals-design.md
git commit -m "docs: 국토부 실거래가 파일럿 호출 결과 기록

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## 1단계 — 백엔드 원천 Strategy (BE v0.46.0)

### Task 3: 판정 행 `basis` 컬럼 — 엔티티·DTO·테이블·API

설계서 §9. 기존 행은 전부 인허가 원천이라 기본값 `permit`이 참값이다.

**Files:**
- Modify: `backend/apps/verdict/domain/entities/region_industry_verdict_entity.py`
- Modify: `backend/apps/verdict/app/dtos/region_industry_verdict_dto.py`
- Modify: `backend/apps/verdict/app/use_cases/region_industry_verdict_interactor.py` (`_to_dto`)
- Modify: `backend/apps/verdict/adapter/outbound/orms/region_industry_verdict_orm.py`
- Modify: `backend/apps/verdict/adapter/outbound/orm_mappers/region_industry_verdict_orm_mapper.py`
- Modify: `backend/apps/verdict/adapter/inbound/api/schemas/region_industry_verdict_schema.py`
- Modify: `backend/apps/verdict/adapter/inbound/mappers/region_industry_verdict_mapper.py`
- Create: `backend/migrations/versions/d0e1f2a3b4c5_region_industry_verdict_basis.py`
- Modify: `backend/docs/backend_ver_log.md`
- Test: `backend/tests/test_verdict_repository.py`, `backend/tests/test_verdict_router.py`

**Interfaces:**
- Produces: 상수 `BASIS_PERMIT = "permit"`, `BASIS_PROXY = "proxy"`, `BASIS_AGGREGATE = "aggregate"` (entity 모듈). `RegionIndustryVerdict(..., computed_at, basis: str = BASIS_PERMIT)` — **마지막 필드, 기본값**. `RegionIndustryVerdictDto(..., computed_at, basis: str = BASIS_PERMIT)`. API 단건 응답 `basis: str`.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_verdict_repository.py` — 상단 import에 `from dataclasses import replace` 추가, 파일 끝에:
```python
def test_basis가_왕복되고_지정하지_않으면_permit이다():
    codes = _two_region_codes()
    repo = SqlAlchemyRegionIndustryVerdictRepository()
    try:
        repo.upsert([replace(_verdict(codes[0], "orange"), basis="aggregate"), _verdict(codes[1], "clear")])
        assert repo.find(codes[0], _INDUSTRY).basis == "aggregate"
        assert repo.find(codes[1], _INDUSTRY).basis == "permit"
    finally:
        _cleanup(codes)
```
`backend/tests/test_verdict_router.py` 파일 끝에:
```python
def test_단건은_판정_원천_basis를_싣는다():
    body = _client().get("/verdicts/1168064000?industry=korean_food").json()
    assert body["basis"] == "permit"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_repository.py tests/test_verdict_router.py -q`
Expected: FAIL 2건 — `TypeError: ... unexpected keyword argument 'basis'`(replace) 와 `KeyError: 'basis'`.

- [ ] **Step 3: 엔티티·DTO**

`region_industry_verdict_entity.py` — `VERDICT_INSUFFICIENT` 정의 바로 아래에:
```python
# 판정 원천 — 판정 한 행이 어떤 원천에서 나왔나 (업종 특화 신호 설계서 §9). 카드 배지·백테스트 합산 범위가 이 값을 본다.
BASIS_PERMIT = "permit"  # 인허가 개별 점포 이력 (store)
BASIS_PROXY = "proxy"  # 대리 원천의 개별 이력 (편의점 = 담배소매인)
BASIS_AGGREGATE = "aggregate"  # 동×분기 집계 (부동산 = 서울시 상권분석)
```
`RegionIndustryVerdict`의 `computed_at` 다음 줄에:
```python
    basis: str = BASIS_PERMIT  # permit | proxy | aggregate
```
`region_industry_verdict_dto.py` — 상단에 `from apps.verdict.domain.entities.region_industry_verdict_entity import BASIS_PERMIT`, `RegionIndustryVerdictDto`의 `computed_at` 다음 줄에:
```python
    basis: str = BASIS_PERMIT
```
`region_industry_verdict_interactor.py`의 모듈 함수 `_to_dto` 반환에 `basis=entity.basis,` 추가.

- [ ] **Step 4: ORM·매퍼·스키마**

`region_industry_verdict_orm.py` — `computed_at` 다음 줄:
```python
    basis: Mapped[str] = mapped_column(String(12), server_default="permit")  # permit | proxy | aggregate (설계서 §9)
```
`region_industry_verdict_orm_mapper.py` — `to_orm`에 `basis=entity.basis,`, `to_entity`에 `basis=orm.basis,`.
`region_industry_verdict_schema.py` — `RegionIndustryVerdictResponse`의 `computed_at` 다음 줄:
```python
    basis: str  # permit | proxy | aggregate — 카드 배지 (업종 특화 신호 설계서 §9-3)
```
`region_industry_verdict_mapper.py` — `to_response`에 `basis=dto.basis,`.

- [ ] **Step 5: 마이그레이션**

Create `backend/migrations/versions/d0e1f2a3b4c5_region_industry_verdict_basis.py`:
```python
"""판정 원천 컬럼 region_industry_verdict.basis

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-29 12:00:00.000000

설계서 `docs/superpowers/specs/2026-09-29-industry-specific-signals-design.md` §9-1.
permit(인허가) · proxy(담배소매인 대리) · aggregate(상권분석 집계). 기존 행은 전부 인허가 원천이라 기본값이 참값이다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "region_industry_verdict",
        sa.Column("basis", sa.String(length=12), nullable=False, server_default="permit"),
    )


def downgrade() -> None:
    op.drop_column("region_industry_verdict", "basis")
```

- [ ] **Step 6: 통과 확인 + verdict 전체 회귀**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_repository.py tests/test_verdict_router.py -q && .venv/bin/python -m pytest tests -q -k verdict`
Expected: PASS (conftest가 테스트 DB를 head까지 올린다).

- [ ] **Step 7: 개발 DB에 마이그레이션 적용**

Run: `cd backend && .venv/bin/alembic upgrade head && .venv/bin/alembic current`
Expected: `d0e1f2a3b4c5 (head)`. 기존 5,124행은 `basis='permit'`. (도커 8200 이미지는 옛 코드라 새 컬럼을 무시한다 — 동작 불변.)

- [ ] **Step 8: 버전 로그 항목 생성**

`backend/docs/backend_ver_log.md`의 `# Backend Version Log` 바로 아래에:
```markdown
## [v0.46.0] - 2026-09-29

### Added
- **판정 원천 `basis`** (업종 특화 신호 설계서 §9) — `region_industry_verdict.basis`(`permit`·`proxy`·`aggregate`, 기본 `permit`) 컬럼·마이그레이션 `d0e1f2a3b4c5`, 엔티티·DTO·단건 API 응답 `basis`.

### Changed
```

- [ ] **Step 9: 커밋**

```bash
git add backend/apps/verdict backend/migrations/versions/d0e1f2a3b4c5_region_industry_verdict_basis.py backend/tests/test_verdict_repository.py backend/tests/test_verdict_router.py backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 판정 행 basis(판정 원천) 컬럼·API

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 편의점 이력 도메인 — 브랜드 사전 · 승계 접기 · 담배권 빈자리 격자

설계서 §5-1·§5-2·§6-1. 순수 파이썬(프레임워크 import 없음).

**Files:**
- Create: `backend/apps/verdict/domain/services/convenience_history.py`
- Create: `backend/apps/verdict/domain/services/tobacco_gap.py`
- Test: `backend/tests/test_verdict_convenience_history.py`
- Modify: `backend/docs/backend_ver_log.md` (v0.46.0 Added에 한 줄)

**Interfaces:**
- Produces:
  - `convenience_history`: `MIN_VALID_DATE: date`, `SUCCESSION_GAP_DAYS: int = 90`, `BRAND_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...]`, `brand_of(name: str) -> str | None`, `RetailerRecord(retailer_id: str, name: str, region_code: str | None, open_date: date | None, close_date: date | None, address_key: str | None)`(frozen), `Episode(region_code: str, open_date: date, close_date: date | None, record_count: int = 1)`(frozen), `address_key(jibun_address: str | None) -> str | None`, `fold_successions(records: Iterable[RetailerRecord], gap_days: int = SUCCESSION_GAP_DAYS) -> list[Episode]`
  - `tobacco_gap`: `TOBACCO_GAP_RADIUS_M: float = 50.0`, `GeoPoint(region_code: str | None, lat: float, lng: float)`(frozen), `blocked_counts(candidates: Iterable[GeoPoint], retailers: Iterable[GeoPoint], radius_m: float = TOBACCO_GAP_RADIUS_M) -> dict[str, tuple[int, int]]` — 동별 `(후보 수, 막힌 수)`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `backend/tests/test_verdict_convenience_history.py`:
```python
"""편의점 이력 도메인 — 브랜드 사전(옛 이름·CU 경계), 승계 접기, 담배권 빈자리 격자 (업종 특화 신호 설계서 §5·§6)."""

from datetime import date

import pytest

from apps.verdict.domain.services.convenience_history import (
    Episode,
    RetailerRecord,
    address_key,
    brand_of,
    fold_successions,
)
from apps.verdict.domain.services.tobacco_gap import TOBACCO_GAP_RADIUS_M, GeoPoint, blocked_counts


@pytest.mark.parametrize("name, brand", [
    ("GS25 종각점", "GS25"), ("지에스25 세운점", "GS25"), ("LG25종로교남점", "GS25"), ("엘지25 장위점", "GS25"),
    ("CU 광진웰츠점", "CU"), ("씨유(CU) 청계센트럴점", "CU"), ("훼미리마트 서소문점", "CU"),
    ("(주)비지에프리테일 휘경센터점", "CU"),
    ("(주)코리아세븐 종각점", "세븐일레븐"), ("바이더웨이 옥수점", "세븐일레븐"), ("7-ELEVEN 명륜성대점", "세븐일레븐"),
    ("위드미군자점", "이마트24"), ("이마트24 성동대로점", "이마트24"),
    ("한국미니스톱(주) M안국역점", "미니스톱"),
    ("365플러스 동대문역점", "기타 체인"), ("로그인25노원점", "기타 체인"),
])
def test_편의점_브랜드와_옛_이름을_찾는다(name, brand):
    assert brand_of(name) == brand


@pytest.mark.parametrize("name", [
    "CUBE마트", "SCU상사", "세븐마트", "행복슈퍼", "(주)지에스리테일 GS수퍼 종로명륜점", "로그인 PC", "17-11번지 담배",
])
def test_편의점이_아닌_상호는_None이다(name):
    assert brand_of(name) is None


def _r(rid, open_, close=None, addr="서울특별시 강남구 역삼동 1", region="1168064000"):
    return RetailerRecord(rid, "GS25", region, open_, close, addr)


def test_폐업_전후_90일_안_같은_지번_새_지정은_한_에피소드로_잇는다():
    episodes = fold_successions([_r("a", date(2015, 1, 1), date(2020, 3, 1)), _r("b", date(2020, 2, 20))])
    assert episodes == [Episode("1168064000", date(2015, 1, 1), None, 2)]


def test_90일을_넘기면_따로_센다():
    episodes = fold_successions([_r("a", date(2015, 1, 1), date(2020, 3, 1)), _r("b", date(2020, 7, 1))])
    assert len(episodes) == 2


def test_영업_중인_자리에_새_지정이_오면_잇지_않는다():
    # 대형 건물 안 동시 영업 점포를 합치지 않는다
    episodes = fold_successions([_r("a", date(2015, 1, 1)), _r("b", date(2016, 1, 1))])
    assert len(episodes) == 2


def test_승계가_여러_번이면_한_줄로_이어진다():
    episodes = fold_successions([
        _r("a", date(2010, 1, 1), date(2013, 1, 1)),
        _r("b", date(2013, 1, 15), date(2018, 5, 1)),
        _r("c", date(2018, 5, 1), date(2024, 1, 1)),
    ])
    assert episodes == [Episode("1168064000", date(2010, 1, 1), date(2024, 1, 1), 3)]


def test_주소가_없거나_다르면_잇지_않는다():
    episodes = fold_successions([
        _r("a", date(2015, 1, 1), date(2020, 3, 1), addr=None),
        _r("b", date(2020, 3, 2), addr=None),
        _r("c", date(2020, 3, 2), addr="서울특별시 강남구 역삼동 2"),
    ])
    assert len(episodes) == 3


def test_동이_없거나_1990년_이전_개업은_버린다():
    episodes = fold_successions([_r("a", date(1900, 1, 1)), _r("b", date(2015, 1, 1), region=None), _r("c", date(2015, 1, 1))])
    assert episodes == [Episode("1168064000", date(2015, 1, 1), None, 1)]


def test_지번주소_공백을_정규화한다():
    assert address_key(" 서울특별시  강남구 역삼동 1 ") == "서울특별시 강남구 역삼동 1"
    assert address_key("   ") is None
    assert address_key(None) is None


_M = 1 / 111_320  # 위도 1m


def test_반경_50m_안에_소매인이_있으면_막힌_자리다():
    retailers = [GeoPoint(None, 37.5, 127.0)]
    candidates = [
        GeoPoint("r1", 37.5, 127.0),
        GeoPoint("r1", 37.5 + 40 * _M, 127.0),
        GeoPoint("r1", 37.5 + 60 * _M, 127.0),
        GeoPoint("r2", 37.6, 127.0),
        GeoPoint(None, 37.5, 127.0),  # 동 없는 후보는 버린다
    ]
    assert blocked_counts(candidates, retailers) == {"r1": (3, 2), "r2": (1, 0)}


def test_반경은_인자로_바꿀_수_있고_기본은_50m다():
    assert TOBACCO_GAP_RADIUS_M == 50.0
    assert blocked_counts([GeoPoint("r1", 37.5 + 60 * _M, 127.0)], [GeoPoint(None, 37.5, 127.0)], radius_m=100.0) == {"r1": (1, 1)}
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_convenience_history.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.verdict.domain.services.convenience_history'`

- [ ] **Step 3: `convenience_history.py` 구현**

```python
"""편의점 개폐업 이력 — 담배소매인 인허가를 편의점 개폐업의 대리 원천으로 읽는다 (업종 특화 신호 설계서 §5).
순수 파이썬. 브랜드 사전(옛 이름 포함)으로 편의점 행만 고르고, 같은 자리 양도·양수는 한 에피소드로 접는다."""

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date

MIN_VALID_DATE = date(1990, 1, 1)  # 원천에 1900-01-01 쓰레기값이 있다
# 같은 지번에서 폐업 ±90일 안 새 지정 = 승계. 실측(9/29) 편의점 폐업 15,573건 중 2,482건(16%)
SUCCESSION_GAP_DAYS = 90

# 브랜드 사전 (CLAUDE.md §5 — if/elif 대신 순서 있는 매핑, 첫 일치가 이긴다). 대문자화한 상호에 re.search.
# 옛 이름: LG25·엘지25 → GS25, 훼미리마트·패밀리마트 → CU, 바이더웨이·코리아세븐 → 세븐일레븐, 위드미 → 이마트24.
# 'CU'는 영문자 경계 필수(CUBE·SCU). 맨 '세븐'·맨 '로그인'·'GS리테일'(GS수퍼 혼재)은 넣지 않는다.
BRAND_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (brand, re.compile("|".join(patterns)))
    for brand, patterns in (
        ("GS25", (r"GS\s*25", r"지에스\s*25", r"LG\s*25", r"엘지\s*25")),
        ("CU", (r"(?<![A-Z])CU(?![A-Z])", r"씨유", r"훼미리\s*마트", r"패밀리\s*마트", r"FAMILY\s*MART", r"비지에프")),
        ("세븐일레븐", (r"세븐\s*-?\s*일레븐", r"7\s*-?\s*ELEVEN", r"(?<!\d)7-11(?!\d)", r"바이더웨이",
                   r"BUY\s*THE\s*WAY", r"코리아세븐")),
        ("이마트24", (r"이마트\s*24", r"EMART\s*24", r"위드미", r"WITH\s*ME")),
        ("미니스톱", (r"미니스톱", r"MINI\s*STOP")),
        ("기타 체인", (r"365\s*플러스", r"홈플러스\s*365", r"스토리웨이", r"씨스페이스", r"C-?\s*SPACE", r"로그인\s*25")),
    )
)


def brand_of(name: str) -> str | None:
    """편의점 브랜드 — 사전에 없으면 None(편의점이 아니거나 개인 편의점: 판정 원천에서 뺀다)."""
    text = name.upper()
    return next((brand for brand, pattern in BRAND_PATTERNS if pattern.search(text)), None)


@dataclass(frozen=True)
class RetailerRecord:
    retailer_id: str
    name: str
    region_code: str | None
    open_date: date | None  # 지정일자 또는 인허가일자 (둘 다 있으면 실측 전부 같다)
    close_date: date | None  # 폐업일자 또는 인허가취소일자
    address_key: str | None  # 지번주소 공백 정규화 — 승계 판단 단위


@dataclass(frozen=True)
class Episode:
    """한 자리의 편의점 영업 한 토막 — 승계로 이어진 레코드 여러 개가 하나가 된다."""

    region_code: str
    open_date: date
    close_date: date | None
    record_count: int = 1


def address_key(jibun_address: str | None) -> str | None:
    if jibun_address is None or not jibun_address.strip():
        return None
    return " ".join(jibun_address.split())


def fold_successions(records: Iterable[RetailerRecord], gap_days: int = SUCCESSION_GAP_DAYS) -> list[Episode]:
    """레코드 → 에피소드. 같은 지번에서 이미 닫힌 에피소드의 폐업일 ±gap_days 안에 개업하면 그 에피소드에 잇는다.
    영업 중인 에피소드에는 잇지 않는다(대형 건물 동시 영업). 주소 없는 레코드는 혼자 에피소드."""
    usable = [r for r in records if r.region_code and r.open_date and r.open_date >= MIN_VALID_DATE]
    by_address: dict[str, list[RetailerRecord]] = {}
    episodes: list[Episode] = []
    for record in usable:
        if record.address_key is None:
            episodes.append(_start(record))
        else:
            by_address.setdefault(record.address_key, []).append(record)
    for group in by_address.values():
        episodes.extend(_fold_group(sorted(group, key=lambda r: (r.open_date, r.retailer_id)), gap_days))
    return episodes


def _start(record: RetailerRecord) -> Episode:
    return Episode(record.region_code, record.open_date, record.close_date)


def _fold_group(records: list[RetailerRecord], gap_days: int) -> list[Episode]:
    episodes: list[Episode] = []
    for record in records:
        nearest = min(
            (
                (abs((record.open_date - e.close_date).days), n)
                for n, e in enumerate(episodes)
                if e.close_date is not None and abs((record.open_date - e.close_date).days) <= gap_days
            ),
            default=None,
        )
        if nearest is None:
            episodes.append(_start(record))
            continue
        e = episodes[nearest[1]]
        close = None if record.close_date is None else max(e.close_date, record.close_date)
        episodes[nearest[1]] = replace(e, close_date=close, record_count=e.record_count + 1)
    return episodes
```

- [ ] **Step 4: `tobacco_gap.py` 구현**

```python
"""담배권 빈자리 — 상가 자리 중 영업 중인 담배소매인 반경 안에 든 비율 (업종 특화 신호 설계서 §6). 순수 파이썬 격자 근접 판정."""

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

# 반경 50m — 소매인 간격 실측(9/29): 100m 안 이웃 73%라 100m 제한 구는 드물고, 100m로 재면 동 중위 95%가 막혀
# 변별력이 없다(설계서 §2-2·§3). 구별 조례 반영은 후속 — 바꿀 때는 이 상수 한 곳.
TOBACCO_GAP_RADIUS_M = 50.0

_M_PER_DEG_LAT = 111_320.0
_M_PER_DEG_LNG = 111_320.0 * math.cos(math.radians(37.55))  # 서울 기준 등장방형 근사


@dataclass(frozen=True)
class GeoPoint:
    region_code: str | None
    lat: float
    lng: float


def _xy(point: GeoPoint) -> tuple[float, float]:
    return point.lat * _M_PER_DEG_LAT, point.lng * _M_PER_DEG_LNG


def blocked_counts(
    candidates: Iterable[GeoPoint], retailers: Iterable[GeoPoint], radius_m: float = TOBACCO_GAP_RADIUS_M
) -> dict[str, tuple[int, int]]:
    """동별 (후보 자리 수, 반경 안에 소매인이 하나라도 있는 자리 수). 격자 한 칸 = 반경이라 이웃 9칸만 본다."""
    grid: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)
    for retailer in retailers:
        x, y = _xy(retailer)
        grid[(int(x // radius_m), int(y // radius_m))].append((x, y))
    totals: dict[str, list[int]] = {}
    for candidate in candidates:
        if candidate.region_code is None:
            continue
        x, y = _xy(candidate)
        cx, cy = int(x // radius_m), int(y // radius_m)
        near = any(
            math.hypot(x - rx, y - ry) <= radius_m
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for rx, ry in grid.get((cx + dx, cy + dy), ())
        )
        cell = totals.setdefault(candidate.region_code, [0, 0])
        cell[0] += 1
        cell[1] += near
    return {region: (total, blocked) for region, (total, blocked) in totals.items()}
```

- [ ] **Step 5: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_convenience_history.py -q`
Expected: PASS (33 passed 안팎 — parametrize 포함)

- [ ] **Step 6: 버전 로그 한 줄 + 커밋**

v0.46.0 `### Added`에:
```markdown
- **편의점 이력 도메인** (설계서 §5·§6) — `domain/services/convenience_history.py`(브랜드 사전: 옛 이름 LG25·훼미리마트·바이더웨이·위드미 포함, 'CU' 영문자 경계 / 같은 지번 ±90일 승계 접기, 영업 중 에피소드에는 잇지 않음), `domain/services/tobacco_gap.py`(반경 50m 격자 근접 판정 `blocked_counts`).
```
```bash
git add backend/apps/verdict/domain/services/convenience_history.py backend/apps/verdict/domain/services/tobacco_gap.py backend/tests/test_verdict_convenience_history.py backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 편의점 이력 도메인 — 브랜드 사전·승계 접기·담배권 빈자리 격자

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 신호 프로필 Strategy — Decorator·Null Object·폐업률·담배권 빈자리

설계서 §4·§6·§7-1·§9-2. 순수 도메인.

**Files:**
- Modify: `backend/apps/verdict/domain/entities/region_industry_verdict_entity.py` (신호 키 상수)
- Modify: `backend/apps/verdict/domain/services/thresholds.py` (`min_gap_candidates`)
- Modify: `backend/apps/verdict/domain/services/signals.py`
- Create: `backend/apps/verdict/domain/services/profiles.py`
- Modify: `backend/apps/verdict/app/dtos/region_industry_verdict_dto.py` (`StoreSignalStat.gap_*`)
- Test: `backend/tests/test_verdict_profiles.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 3 `BASIS_*`, Task 4 `TOBACCO_GAP_RADIUS_M`
- Produces:
  - entity: `SPECIFIC_SIGNAL_KEYS = ("closure_rate", "tobacco_gap")`, `ALL_SIGNAL_KEYS = SIGNAL_KEYS + SPECIFIC_SIGNAL_KEYS`, `ADVISORY_SIGNAL_KEYS = frozenset({"shrinking", "tobacco_gap"})`
  - `VerdictThresholds.min_gap_candidates: int = 30`
  - `SignalInput`에 기본값 필드 `gap_candidates: int = 0`, `gap_blocked: int = 0` (마지막)
  - `StoreSignalStat`에 기본값 필드 `gap_candidates: int = 0`, `gap_blocked: int = 0` (마지막)
  - signals: `SourcedSignal(inner: Signal, source: str)`, `UnsupportedSignal(key: str, source: str, reason: str)`, `ClosureRateSignal`(key `closure_rate`, source `commerce`), `TobaccoGapSignal`(key `tobacco_gap`, source `tobacco`)
  - profiles: `SignalProfile(ABC)`(속성 `basis: str`, 메서드 `signals() -> tuple[Signal, ...]`), `PermitProfile(signals: Sequence[Signal] = SIGNALS)`, `TobaccoProxyProfile()`, `AggregateProfile()`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `backend/tests/test_verdict_profiles.py`:
```python
"""신호 프로필 — 원천별 신호 목록·원천 표기·미지원 신호·폐업률·담배권 빈자리 (업종 특화 신호 설계서 §4·§6·§7)."""

import pytest

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    ADVISORY_SIGNAL_KEYS,
    ALL_SIGNAL_KEYS,
    LEVEL_OFF,
    LEVEL_STRONG,
    LEVEL_UNAVAILABLE,
    SIGNAL_KEYS,
    SignalResult,
)
from apps.verdict.domain.services.profiles import AggregateProfile, PermitProfile, TobaccoProxyProfile
from apps.verdict.domain.services.rules import on_count, strong_count
from apps.verdict.domain.services.signals import ClosureRateSignal, SignalInput, TobaccoGapSignal
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS as T


def _input(**overrides) -> SignalInput:
    base = dict(
        region_code="1168064000", industry_id="convenience_store", industry_name="편의점",
        start_store_count=100, opened_12m=28, closed_12m=41,
        cohort_size=37, cohort_survived=14,
        closed_3y_count=60, closed_3y_median_months=19.0,
        latest_store_count=94, resident_total=10_000,
        change_code="HL", change_name="상권축소", change_quarter="20262",
        closed_months=20.0, seoul_closed_months=27.0,
        gap_candidates=200, gap_blocked=150,
    )
    base.update(overrides)
    return SignalInput(**base)


def test_신호_키_상수와_빈자리_가드():
    assert ALL_SIGNAL_KEYS == SIGNAL_KEYS + ("closure_rate", "tobacco_gap")
    assert T.min_gap_candidates == 30


def test_인허가_프로필은_공통_신호_5개_그대로다():
    profile = PermitProfile()
    assert profile.basis == "permit"
    assert tuple(s.key for s in profile.signals()) == SIGNAL_KEYS


def test_편의점_프로필은_공통_5개에_담배권_빈자리를_더하고_원천을_담배소매인으로_표기한다():
    profile = TobaccoProxyProfile()
    assert profile.basis == "proxy"
    assert tuple(s.key for s in profile.signals()) == SIGNAL_KEYS + ("tobacco_gap",)
    results = {s.key: s.evaluate(_input(), T, [0.0, 0.5]) for s in profile.signals()}
    assert results["net_outflow"].source == "tobacco"
    assert results["net_outflow"].value == pytest.approx(0.13)
    assert results["saturation"].source == "tobacco"
    assert results["shrinking"].source == "neighborhood"
    assert results["tobacco_gap"].source == "tobacco"


def test_부동산_프로필은_폐업률과_포화만_계산하고_코호트_신호는_집계_사유로_미판정이다():
    profile = AggregateProfile()
    assert profile.basis == "aggregate"
    assert tuple(s.key for s in profile.signals()) == (
        "closure_rate", "survival_cliff", "early_closure", "saturation", "shrinking",
    )
    results = {s.key: s.evaluate(_input(), T, [0.1]) for s in profile.signals()}
    for key in ("survival_cliff", "early_closure"):
        assert results[key].level == LEVEL_UNAVAILABLE
        assert results[key].evidence == "집계 원천 — 개별 점포 개업·폐업일이 없어 산출하지 않음"
        assert results[key].source == "commerce"
    assert results["closure_rate"].source == "commerce"
    assert results["saturation"].source == "commerce"
    unsupported = [s for s in profile.signals() if s.key in ("survival_cliff", "early_closure")]
    assert all(s.raw_value(_input(), T) is None for s in unsupported)  # 분포에도 안 들어간다


def test_폐업률은_4분기_폐업을_시작_점포로_나누고_가드는_10이다():
    signal = ClosureRateSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(0.41)
    assert signal.raw_value(_input(start_store_count=9), T) is None
    result = signal.evaluate(_input(), T, [0.1, 0.2, 0.3, 0.4])
    assert result.level == LEVEL_STRONG
    assert "지난 4분기 폐업 41곳" in result.evidence and "서울시 상권분석 집계" in result.evidence
    assert "표본 부족" in signal.evaluate(_input(start_store_count=9), T, [0.1]).evidence


def test_담배권_빈자리는_막힌_자리_비율이고_후보_30곳_미만이면_미판정이다():
    signal = TobaccoGapSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(0.75)
    thin = signal.evaluate(_input(gap_candidates=29, gap_blocked=29), T, [0.5])
    assert thin.level == LEVEL_UNAVAILABLE and "29곳" in thin.evidence
    ok = signal.evaluate(_input(), T, [0.5, 0.6])
    assert "50m" in ok.evidence and "200곳" in ok.evidence and "75%" in ok.evidence


def test_담배권_빈자리는_참고_신호라_등급_계산에서_빠진다():
    assert "tobacco_gap" in ADVISORY_SIGNAL_KEYS and "shrinking" in ADVISORY_SIGNAL_KEYS
    results = [
        SignalResult("tobacco_gap", LEVEL_STRONG, 0.9, 99.0, "근거", "tobacco"),
        SignalResult("net_outflow", LEVEL_OFF, 0.0, 10.0, "근거", "tobacco"),
    ]
    assert strong_count(results) == 0 and on_count(results) == 0
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_profiles.py -q`
Expected: FAIL — `ImportError: cannot import name 'ALL_SIGNAL_KEYS'`

- [ ] **Step 3: 상수·임계값·DTO**

`region_industry_verdict_entity.py` — `SIGNAL_KEYS` 정의 아래에 추가하고 `ADVISORY_SIGNAL_KEYS`를 교체:
```python
# 업종 특화 신호 — 특정 원천 프로필에만 있다 (업종 특화 신호 설계서 §9-2). 백테스트 정렬·표 칸은 ALL_SIGNAL_KEYS 순서.
# signals 튜플은 "항상 5개"가 아니라 프로필이 정한 개수·순서다: 인허가 5 · 편의점 6 · 부동산 5.
SPECIFIC_SIGNAL_KEYS: tuple[str, ...] = ("closure_rate", "tobacco_gap")
ALL_SIGNAL_KEYS: tuple[str, ...] = SIGNAL_KEYS + SPECIFIC_SIGNAL_KEYS

# 참고 신호 — 평가·저장은 하되 strong_count/on_count/evaluable_count(등급 계산)에서는 뺀다.
# 상권 축소는 백테스트 lift 0.96×(무신호, 판정 카드 설계서 §7). 담배권 빈자리는 폐업 위험이 아니라 진입 가능성을 잰다(업종 특화 신호 설계서 §6-2).
ADVISORY_SIGNAL_KEYS: frozenset[str] = frozenset({"shrinking", "tobacco_gap"})
```
`thresholds.py` `VerdictThresholds`의 `min_evaluable` 아래:
```python
    min_gap_candidates: int = 30  # 담배권 빈자리 후보 자리 가드 — 비율 표본이라 점포 가드보다 크게 (업종 특화 신호 설계서 §6-1)
```
`region_industry_verdict_dto.py` `StoreSignalStat`의 `closed_3y_median_months` 아래:
```python
    # 담배권 빈자리 (편의점 원천만 채운다, 업종 특화 신호 설계서 §6) — 다른 원천은 0 → 가드가 unavailable로 만든다
    gap_candidates: int = 0
    gap_blocked: int = 0
```

- [ ] **Step 4: `signals.py` 확장**

상단 import 교체·추가:
```python
from dataclasses import dataclass, replace
...
from apps.verdict.domain.services.tobacco_gap import TOBACCO_GAP_RADIUS_M
```
`SignalInput`의 마지막 필드(`seoul_closed_months`) 아래:
```python
    # 담배권 빈자리 (편의점 원천) — 기본값 0이면 TobaccoGapSignal 가드가 unavailable로 만든다
    gap_candidates: int = 0
    gap_blocked: int = 0
```
`ShrinkingSignal` 클래스 뒤, `SIGNALS` 튜플 앞에:
```python
class ClosureRateSignal(Signal):
    """집계 원천 폐업률 — 개업 수가 끊긴 원천(부동산 아카이브 2024Q1~)에서 순유출 대신 쓴다 (업종 특화 신호 설계서 §7-1)."""

    key = "closure_rate"
    source = "commerce"

    def raw_value(self, i, t):
        if i.start_store_count < t.min_sample:
            return None
        return i.closed_12m / i.start_store_count

    def worse(self, value):
        return value

    def evidence(self, i, value, percentile):
        return (
            f"지난 4분기 폐업 {i.closed_12m:,}곳 (4분기 전 점포 {i.start_store_count:,}곳의 {value * 100:.0f}%, "
            f"서울 {i.industry_name} 상위 {_top(percentile)}%, 서울시 상권분석 집계)"
        )

    def unavailable_reason(self, i, t):
        return f"표본 부족 — 4분기 전 점포 {i.start_store_count}곳 ({t.min_sample}곳 미만)"


class TobaccoGapSignal(Signal):
    """담배권 빈자리 — 상가 자리 중 영업 중인 담배소매인 반경 안 비율, 높을수록 나쁨. 참고 신호 (설계서 §6)."""

    key = "tobacco_gap"
    source = "tobacco"

    def raw_value(self, i, t):
        if i.gap_candidates < t.min_gap_candidates:
            return None
        return i.gap_blocked / i.gap_candidates

    def worse(self, value):
        return value

    def evidence(self, i, value, percentile):
        return (
            f"이 동 상가 자리 {i.gap_candidates:,}곳 중 {value * 100:.0f}%가 영업 중인 담배소매인 "
            f"{TOBACCO_GAP_RADIUS_M:.0f}m 안 — 새 담배소매인 지정이 어렵다 (서울 상위 {_top(percentile)}%)"
        )

    def unavailable_reason(self, i, t):
        return f"상가 좌표 표본 부족 — {i.gap_candidates}곳 ({t.min_gap_candidates}곳 미만)"


class SourcedSignal(Signal):
    """Decorator — 같은 계산을 다른 원천 데이터로 돌릴 때 source 표기만 바꾼다 (업종 특화 신호 설계서 §4)."""

    def __init__(self, inner: Signal, source: str) -> None:
        self._inner = inner
        self.key = inner.key
        self.source = source

    def raw_value(self, i, t):
        return self._inner.raw_value(i, t)

    def worse(self, value):
        return self._inner.worse(value)

    def evidence(self, i, value, percentile):
        return self._inner.evidence(i, value, percentile)

    def unavailable_reason(self, i, t):
        return self._inner.unavailable_reason(i, t)

    def evaluate(self, i, t, distribution):
        return replace(self._inner.evaluate(i, t, distribution), source=self.source)


class UnsupportedSignal(Signal):
    """Null Object — 원천이 이 신호의 재료를 주지 않는다. 표본 부족과 다른 사유 문장으로 항상 unavailable (설계서 §7-1)."""

    def __init__(self, key: str, source: str, reason: str) -> None:
        self.key = key
        self.source = source
        self._reason = reason

    def raw_value(self, i, t):
        return None

    def worse(self, value):
        return value

    def evidence(self, i, value, percentile):
        return self._reason

    def unavailable_reason(self, i, t):
        return self._reason
```
`SIGNALS` 튜플은 그대로(공통 5개).

- [ ] **Step 5: `profiles.py` 생성**

```python
"""신호 프로필 — 업종의 원천에 따라 어떤 신호를 어떤 원천 표기로 돌리는가 (Strategy, 업종 특화 신호 설계서 §4).
인터랙터는 업종 id로 프로필을 찾기만 하고 업종을 분기하지 않는다."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    BASIS_AGGREGATE,
    BASIS_PERMIT,
    BASIS_PROXY,
)
from apps.verdict.domain.services.signals import (
    SIGNALS,
    ClosureRateSignal,
    EarlyClosureSignal,
    NetOutflowSignal,
    SaturationSignal,
    ShrinkingSignal,
    Signal,
    SourcedSignal,
    SurvivalCliffSignal,
    TobaccoGapSignal,
    UnsupportedSignal,
)

_TOBACCO = "tobacco"
_COMMERCE = "commerce"
_NO_STORE_HISTORY = "집계 원천 — 개별 점포 개업·폐업일이 없어 산출하지 않음"


class SignalProfile(ABC):
    basis: str

    @abstractmethod
    def signals(self) -> tuple[Signal, ...]:
        """표시·저장 순서대로의 신호 목록."""


class PermitProfile(SignalProfile):
    """인허가 개별 이력 — 공통 신호 5개 그대로 (판정 카드 설계서 §3)."""

    basis = BASIS_PERMIT

    def __init__(self, signals: Sequence[Signal] = SIGNALS) -> None:
        self._signals = tuple(signals)

    def signals(self) -> tuple[Signal, ...]:
        return self._signals


class TobaccoProxyProfile(SignalProfile):
    """편의점 — 담배소매인 이력으로 공통 신호를 돌리고 담배권 빈자리(참고)를 더한다 (설계서 §5·§6)."""

    basis = BASIS_PROXY

    def signals(self) -> tuple[Signal, ...]:
        return (
            SourcedSignal(NetOutflowSignal(), _TOBACCO),
            SourcedSignal(SurvivalCliffSignal(), _TOBACCO),
            SourcedSignal(EarlyClosureSignal(), _TOBACCO),
            SourcedSignal(SaturationSignal(), _TOBACCO),
            ShrinkingSignal(),
            TobaccoGapSignal(),
        )


class AggregateProfile(SignalProfile):
    """부동산 — 동×분기 집계로 폐업률·포화만. 코호트 신호는 원천상 불가 (설계서 §7)."""

    basis = BASIS_AGGREGATE

    def signals(self) -> tuple[Signal, ...]:
        return (
            ClosureRateSignal(),
            UnsupportedSignal(SurvivalCliffSignal.key, _COMMERCE, _NO_STORE_HISTORY),
            UnsupportedSignal(EarlyClosureSignal.key, _COMMERCE, _NO_STORE_HISTORY),
            SourcedSignal(SaturationSignal(), _COMMERCE),
            ShrinkingSignal(),
        )
```

- [ ] **Step 6: 통과 확인 + 회귀**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_profiles.py -q && .venv/bin/python -m pytest tests -q -k verdict`
Expected: PASS. (`test_verdict_thresholds.py::test_기본_임계값_상수`는 새 필드가 기본값이라 그대로 통과. `test_신호_키_순서와_제외_업종`의 `SIGNAL_KEYS` 5개도 불변.)

- [ ] **Step 7: 버전 로그 + 커밋**

v0.46.0 `### Added`:
```markdown
- **신호 프로필 Strategy** (설계서 §4) — `domain/services/profiles.py`: `PermitProfile`(공통 5) · `TobaccoProxyProfile`(공통 5 원천 표기 `tobacco` + 담배권 빈자리) · `AggregateProfile`(폐업률 · 코호트 2종 미지원 · 포화 `commerce` · 상권 축소). 신호: `SourcedSignal`(Decorator) · `UnsupportedSignal`(Null Object) · `ClosureRateSignal` · `TobaccoGapSignal`. 상수 `SPECIFIC_SIGNAL_KEYS`·`ALL_SIGNAL_KEYS`, `min_gap_candidates = 30`.
```
v0.46.0 `### Changed`:
```markdown
- `ADVISORY_SIGNAL_KEYS`에 `tobacco_gap` 추가(진입 가능성 신호 — 등급 계산 제외).
```
```bash
git add backend/apps/verdict/domain backend/apps/verdict/app/dtos/region_industry_verdict_dto.py backend/tests/test_verdict_profiles.py backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 신호 프로필 Strategy — 원천 표기 Decorator·미지원 Null Object·폐업률·담배권 빈자리

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 인터랙터 원천 레지스트리 — 업종별 원천·프로필·basis

설계서 §4·§7-3. 인터랙터가 `sources.get(industry_id, 기본 인허가 원천)`으로 찾고, 원천마다 한 번만 읽는다. 백테스트는 원천별 결과를 모으고 집계 원천은 "전체" 합산에서 뺀다.

**Files:**
- Modify: `backend/apps/verdict/app/ports/output/region_industry_verdict_port.py`
- Create: `backend/apps/verdict/app/use_cases/industry_source.py`
- Modify: `backend/apps/verdict/app/use_cases/region_industry_verdict_interactor.py`
- Modify: `backend/apps/verdict/app/ports/input/region_industry_verdict_use_case.py`
- Modify: `backend/apps/verdict/app/dtos/region_industry_verdict_dto.py` (`BacktestReportDto.industry_basis`)
- Modify: `backend/apps/verdict/domain/services/backtest.py` (버킷 범위 표·`ALL_SIGNAL_KEYS` 정렬)
- Modify: `backend/apps/verdict/adapter/outbound/gateways/industry_catalog_gateway.py`
- Test: Create `backend/tests/test_verdict_sources.py`; Modify `backend/tests/test_verdict_build.py`, `backend/tests/test_verdict_backtest.py`, `backend/tests/test_verdict_alternatives.py` (Fake 카탈로그에 `named_industries`), `backend/tests/test_verdict_gateways.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 5 `SignalProfile`·`PermitProfile`·`TobaccoProxyProfile`·`AggregateProfile`, `StoreSignalStat.gap_*`, Task 3 `BASIS_*`
- Produces:
  - `IndustrySignalDataPort(ABC)`: `signal_stats(today: date) -> list[StoreSignalStat]`, `store_counts(year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]`, `entrant_outcomes(as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]`
  - `IndustryCatalogPort.named_industries(industry_ids: Iterable[str]) -> list[JudgedIndustry]` (abstract)
  - `IndustrySource(profile: SignalProfile, data: IndustrySignalDataPort)` — `@dataclass(frozen=True, eq=False)`(원천 객체 동일성으로 해시)
  - `PermitSignalData(store_stats: StoreSignalStatsPort, region_context: RegionContextPort, entrant_outcomes: EntrantOutcomePort)`
  - `RegionIndustryVerdictInteractor(..., thresholds=..., signals=SIGNALS, sources: Mapping[str, IndustrySource] | None = None)`
  - `compute(today, quarter_max=None, year_max=None, industries: Sequence[JudgedIndustry] | None = None)`
  - `backtest(as_of, entry_days=365, horizon_days=1095, industry_ids: Sequence[str] | None = None)`
  - `BacktestReportDto.industry_basis: tuple[tuple[str, str], ...] = ()` (마지막 필드)

- [ ] **Step 1: 실패하는 테스트 작성**

Create `backend/tests/test_verdict_sources.py`:
```python
"""업종별 원천 레지스트리 — 인터랙터가 업종마다 등록된 원천·프로필로 판정하고 basis를 싣는다 (업종 특화 신호 설계서 §4)."""

from datetime import date

import pytest

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    EntrantOutcome,
    JudgedIndustry,
    LatestStoreCount,
    RegionContext,
    StoreSignalStat,
)
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    EntrantOutcomePort,
    IndustryCatalogPort,
    IndustrySignalDataPort,
    RegionCatalogPort,
    RegionContextPort,
    RegionIndustryVerdictRepositoryPort,
    StoreSignalStatsPort,
)
from apps.verdict.app.use_cases.industry_source import IndustrySource
from apps.verdict.app.use_cases.region_industry_verdict_interactor import RegionIndustryVerdictInteractor
from apps.verdict.domain.services.profiles import AggregateProfile, TobaccoProxyProfile

_REGIONS = [f"r{i:02d}" for i in range(20)]
_NAMES = {"korean_food": "한식", "convenience_store": "편의점", "real_estate": "부동산중개업"}


def _stat(region, industry, closed_12m, gap=(0, 0)):
    return StoreSignalStat(
        region, industry, start_store_count=100, opened_12m=10, closed_12m=closed_12m, cohort_size=0,
        cohort_survived=0, closed_3y_count=0, closed_3y_median_months=None, gap_candidates=gap[0], gap_blocked=gap[1],
    )


class FakeRepository(RegionIndustryVerdictRepositoryPort):
    def upsert(self, verdicts):
        return len(verdicts)

    def list_by_industry(self, industry_id):
        return []

    def list_by_region(self, region_code):
        return []

    def find(self, region_code, industry_id):
        return None

    def delete_other_industries(self, keep_industry_ids):
        return 0


class FakeStoreStats(StoreSignalStatsPort):
    """인허가 원천 — 편의점 행도 일부러 돌려준다(편의점 판정에 쓰이면 안 된다)."""

    def signal_stats(self, today):
        return [_stat(r, "korean_food", 10 + i) for i, r in enumerate(_REGIONS)] + [
            _stat(r, "convenience_store", 90) for r in _REGIONS
        ]


class FakeContext(RegionContextPort):
    def latest_contexts(self, quarter_max=None):
        return [RegionContext(r, 10_000, "HH", "정체", "20262", 25.0, 27.0) for r in _REGIONS]

    def latest_store_counts(self, year_max=None):
        return [LatestStoreCount(r, "korean_food", 90) for r in _REGIONS]


class FakeData(IndustrySignalDataPort):
    def __init__(self, industry_id):
        self.industry_id = industry_id
        self.calls = []

    def signal_stats(self, today):
        self.calls.append(("stats", today))
        return [_stat(r, self.industry_id, 10 + i, gap=(100, 50 + i)) for i, r in enumerate(_REGIONS)]

    def store_counts(self, year_max, quarter_max):
        self.calls.append(("counts", year_max, quarter_max))
        return [LatestStoreCount(r, self.industry_id, 20 + i) for i, r in enumerate(_REGIONS)]

    def entrant_outcomes(self, as_of, entry_days, horizon_days):
        self.calls.append(("outcomes", as_of))
        return [EntrantOutcome(r, self.industry_id, opened=100, closed_within=i) for i, r in enumerate(_REGIONS)]


class FakeCatalog(IndustryCatalogPort):
    def __init__(self, judged):
        self.judged = judged

    def judged_industries(self):
        return list(self.judged)

    def named_industries(self, industry_ids):
        return [JudgedIndustry(i, _NAMES[i]) for i in industry_ids]


class FakeOutcomes(EntrantOutcomePort):
    """인허가 원천 결과 — 부동산 행(999)도 섞는다(집계 원천 업종에 쓰이면 안 된다)."""

    def entrant_outcomes(self, as_of, entry_days, horizon_days):
        return [EntrantOutcome(r, "korean_food", 10, 3) for r in _REGIONS] + [
            EntrantOutcome(r, "real_estate", 999, 999) for r in _REGIONS
        ]


class FakeRegions(RegionCatalogPort):
    def regions(self):
        return []


def _interactor(judged, sources):
    return RegionIndustryVerdictInteractor(
        repository=FakeRepository(), store_stats=FakeStoreStats(), region_context=FakeContext(),
        industry_catalog=FakeCatalog(judged), region_catalog=FakeRegions(), entrant_outcomes=FakeOutcomes(),
        sources=sources,
    )


def test_등록된_업종은_자기_원천과_프로필로_판정하고_basis를_싣는다():
    data = FakeData("convenience_store")
    interactor = _interactor(
        [JudgedIndustry("korean_food", "한식"), JudgedIndustry("convenience_store", "편의점")],
        {"convenience_store": IndustrySource(TobaccoProxyProfile(), data)},
    )
    verdicts = {(v.region_code, v.industry_id): v for v in interactor.compute(date(2026, 9, 29))}
    conv = verdicts[("r19", "convenience_store")]
    assert conv.basis == "proxy"
    assert [s.key for s in conv.signals] == [
        "net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking", "tobacco_gap",
    ]
    assert conv.signals[0].source == "tobacco"
    assert conv.signals[0].value == pytest.approx((29 - 10) / 100)  # 인허가 원천의 편의점 행(90)이 아니라 원천 데이터 값
    assert conv.signals[5].value == pytest.approx(69 / 100)
    korean = verdicts[("r19", "korean_food")]
    assert korean.basis == "permit" and korean.signals[0].source == "store"


def test_원천은_업종이_여럿이어도_한_번만_읽는다():
    data = FakeData("convenience_store")
    interactor = _interactor(
        [JudgedIndustry("convenience_store", "편의점"), JudgedIndustry("convenience_store", "편의점")],
        {"convenience_store": IndustrySource(TobaccoProxyProfile(), data)},
    )
    interactor.compute(date(2026, 9, 29))
    assert data.calls == [("stats", date(2026, 9, 29)), ("counts", None, None)]


def test_집계_원천_백테스트는_상한을_넘기고_전체_합산에서_빠진다():
    data = FakeData("real_estate")
    interactor = _interactor([JudgedIndustry("korean_food", "한식")], {"real_estate": IndustrySource(AggregateProfile(), data)})
    report = interactor.backtest(date(2022, 6, 30), industry_ids=["real_estate"])
    assert ("counts", 2021, "20221") in data.calls and ("outcomes", date(2022, 6, 30)) in data.calls
    assert report.industry_basis == (("real_estate", "aggregate"),)
    assert all(b.industry_id == "real_estate" for b in report.buckets)  # 전체(None) 버킷 없음
    assert sum(b.opened for b in report.buckets) == 100 * 20  # 인허가 원천의 부동산 결과(999)는 버린다
    assert {b.signal_key for b in report.signal_buckets} <= {"closure_rate", "saturation", "shrinking"}


def test_등록되지_않은_업종은_기존_인허가_원천을_쓰고_전체_합산에_들어간다():
    report = _interactor([JudgedIndustry("korean_food", "한식")], {}).backtest(date(2022, 6, 30))
    assert report.industry_basis == (("korean_food", "permit"),)
    assert any(b.industry_id is None for b in report.buckets)
```
`backend/tests/test_verdict_gateways.py` 끝에:
```python
def test_이름_조회는_판정_제외_업종도_돌려준다():
    named = IndustryCatalogGateway().named_industries(["real_estate", "convenience_store"])
    assert [(i.industry_id, i.name) for i in named] == [("convenience_store", "편의점"), ("real_estate", "부동산중개업")]
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_sources.py tests/test_verdict_gateways.py -q`
Expected: FAIL — `ImportError: cannot import name 'IndustrySignalDataPort'`

- [ ] **Step 3: 포트 추가**

`region_industry_verdict_port.py` — import에 `from collections.abc import Iterable`(이미 있음 확인), 파일 끝에:
```python
class IndustrySignalDataPort(ABC):
    """한 업종군의 개폐업 원천 — 창 집계·점포수·진입 결과가 같은 원천에서 함께 나온다(원천을 바꾸면 셋이 같이 바뀐다,
    업종 특화 신호 설계서 §4). 인허가 원천은 PermitSignalData가 기존 포트 3개를 묶어 이 모양으로 만든다."""

    @abstractmethod
    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        """동×업종별 12개월 개폐업·코호트·최근 3년 폐업(원천이 못 주는 항목은 0/None)."""

    @abstractmethod
    def store_counts(self, year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]:
        """포화 분자 — 동×업종 점포수. 상한이 None이면 최신 (백테스트는 상한을 준다)."""

    @abstractmethod
    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        """백테스트 결과 라벨 — 진입 코호트, 또는 집계 원천이면 재고 결과(설계서 §7-3)."""
```
`IndustryCatalogPort`에 메서드 추가:
```python
    @abstractmethod
    def named_industries(self, industry_ids: Iterable[str]) -> list[JudgedIndustry]:
        """제외 여부와 무관하게 주어진 업종의 이름 — 재포함 심사 백테스트용 (업종 특화 신호 설계서 §8)."""
```

- [ ] **Step 4: `industry_source.py` 생성**

```python
"""업종별 판정 원천 — 신호 프로필(도메인 Strategy)과 데이터 포트를 한 쌍으로 묶는다 (업종 특화 신호 설계서 §4)."""

from dataclasses import dataclass
from datetime import date

from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome, LatestStoreCount, StoreSignalStat
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    EntrantOutcomePort,
    IndustrySignalDataPort,
    RegionContextPort,
    StoreSignalStatsPort,
)
from apps.verdict.domain.services.profiles import SignalProfile


@dataclass(frozen=True, eq=False)  # 원천 객체 동일성으로 해시 — 인터랙터가 원천마다 한 번만 읽는 캐시 키
class IndustrySource:
    profile: SignalProfile
    data: IndustrySignalDataPort


class PermitSignalData(IndustrySignalDataPort):
    """Adapter — 기존 인허가 포트 3개를 원천 포트 하나로 묶는다(등록 안 된 업종의 기본 원천)."""

    def __init__(
        self, store_stats: StoreSignalStatsPort, region_context: RegionContextPort, entrant_outcomes: EntrantOutcomePort
    ) -> None:
        self._store_stats = store_stats
        self._region_context = region_context
        self._entrant_outcomes = entrant_outcomes

    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        return self._store_stats.signal_stats(today)

    def store_counts(self, year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]:
        return self._region_context.latest_store_counts(year_max)  # 연말 스냅샷 원천이라 연도 상한만 본다

    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        return self._entrant_outcomes.entrant_outcomes(as_of, entry_days, horizon_days)
```

- [ ] **Step 5: 백테스트 버킷 범위 표**

`domain/services/backtest.py` — import의 `SIGNAL_KEYS`를 `ALL_SIGNAL_KEYS, BASIS_AGGREGATE, BASIS_PERMIT, BASIS_PROXY`로 바꾸고, `VERDICT_ORDER` 아래에:
```python
def _pooled(industry_id: str) -> tuple[str | None, ...]:
    return (None, industry_id)


def _own(industry_id: str) -> tuple[str | None, ...]:
    return (industry_id,)


# 버킷 범위 — 전체(None) 합산에 넣을지는 판정 원천이 정한다. 집계 기반은 결과 단위(점포수 대비 폐업)가 달라
# 진입 코호트와 합산하지 않는다 (업종 특화 신호 설계서 §7-3). 표 조회라 분기 없음.
_SCOPES_OF_BASIS = {BASIS_PERMIT: _pooled, BASIS_PROXY: _pooled, BASIS_AGGREGATE: _own}
```
`summarize`와 `summarize_signals`의 `for industry in (None, v.industry_id):` 두 곳을 `for industry in _SCOPES_OF_BASIS[v.basis](v.industry_id):`로, `summarize_signals`의 정렬 키 `SIGNAL_KEYS.index(k[1])`를 `ALL_SIGNAL_KEYS.index(k[1])`로 바꾼다.
`region_industry_verdict_dto.py` `BacktestReportDto`의 `signal_buckets` 아래:
```python
    industry_basis: tuple[tuple[str, str], ...] = ()  # (industry_id, basis) — 표의 † 표기·심사 절 원천 칸
```

- [ ] **Step 6: 인터랙터**

`region_industry_verdict_interactor.py`:
- import 추가: `from collections.abc import Mapping, Sequence`, DTO에 `EntrantOutcome`, `from apps.verdict.app.use_cases.industry_source import IndustrySource, PermitSignalData`, `from apps.verdict.domain.services.profiles import PermitProfile, SignalProfile`.
- `_EMPTY_STAT`에 `gap_candidates=0, gap_blocked=0,` 추가.
- `__init__` 시그니처 끝에 `sources: Mapping[str, IndustrySource] | None = None,`를 더하고 본문 끝에:
```python
        # 등록 안 된 업종의 원천 = 기존 인허가 포트 3개 (업종 특화 신호 설계서 §4). 업종별 교체는 sources로만.
        self._default_source = IndustrySource(
            PermitProfile(self._signals), PermitSignalData(store_stats, region_context, entrant_outcomes)
        )
        self._sources = dict(sources or {})
```
- `compute`와 `backtest`를 교체:
```python
    def compute(
        self, today: date, quarter_max: str | None = None, year_max: int | None = None,
        industries: Sequence[JudgedIndustry] | None = None,
    ) -> list[RegionIndustryVerdict]:
        """판정 대상(또는 주어진) 업종 × 전 행정동 판정 (저장 없음). 업종마다 등록된 원천·프로필을 쓴다(업종 특화 신호 설계서 §4).
        상한은 백테스트가 T 시점 이후 값을 못 보게 막는다 (판정 카드 설계서 §13)."""
        targets = self._industry_catalog.judged_industries() if industries is None else list(industries)
        contexts = self._region_context.latest_contexts(quarter_max)
        computed_at = datetime.now(timezone.utc)
        loaded: dict[IndustrySource, tuple[dict, dict]] = {}
        verdicts: list[RegionIndustryVerdict] = []
        for industry in targets:
            source = self._source_of(industry.industry_id)
            if source not in loaded:  # 원천마다 한 번만 읽는다 (인허가 원천은 store 전량 group_by 1회)
                loaded[source] = self._load(source, today, quarter_max, year_max)
            stats, counts = loaded[source]
            inputs = [self._input(ctx, industry, stats, counts) for ctx in contexts]
            verdicts.extend(self._judge_industry(inputs, computed_at, source.profile))
        return verdicts

    def backtest(
        self, as_of: date, entry_days: int = 365, horizon_days: int = 1095, industry_ids: Sequence[str] | None = None
    ) -> BacktestReportDto:
        quarter_max, year_max = quarter_before(as_of), as_of.year - 1
        industries = (
            self._industry_catalog.judged_industries() if industry_ids is None
            else self._industry_catalog.named_industries(industry_ids)
        )
        verdicts = self.compute(as_of, quarter_max=quarter_max, year_max=year_max, industries=industries)
        outcomes = self._outcomes(industries, as_of, entry_days, horizon_days)
        names = {i.industry_id: i.name for i in industries}
        return BacktestReportDto(
            as_of=as_of, quarter_max=quarter_max, year_max=year_max, entry_days=entry_days, horizon_days=horizon_days,
            buckets=tuple(
                BacktestBucketDto(b.industry_id, names.get(b.industry_id), b.verdict_code, b.pairs, b.opened, b.closed)
                for b in summarize(verdicts, outcomes)
            ),
            signal_buckets=tuple(
                BacktestSignalBucketDto(b.industry_id, names.get(b.industry_id), b.signal_key, b.fired, b.pairs, b.opened, b.closed)
                for b in summarize_signals(verdicts, outcomes)
            ),
            industry_basis=tuple((i.industry_id, self._source_of(i.industry_id).profile.basis) for i in industries),
        )
```
- `# --- 내부 ---` 아래에 추가:
```python
    def _source_of(self, industry_id: str) -> IndustrySource:
        return self._sources.get(industry_id, self._default_source)

    @staticmethod
    def _load(source: IndustrySource, today: date, quarter_max: str | None, year_max: int | None) -> tuple[dict, dict]:
        stats = {(s.region_code, s.industry_id): s for s in source.data.signal_stats(today)}
        counts = {(c.region_code, c.industry_id): c.store_count for c in source.data.store_counts(year_max, quarter_max)}
        return stats, counts

    def _outcomes(
        self, industries: Sequence[JudgedIndustry], as_of: date, entry_days: int, horizon_days: int
    ) -> list[EntrantOutcome]:
        """원천마다 한 번 읽고 그 원천이 맡은 업종의 결과만 남긴다 (인허가 원천의 부동산 행 등은 버린다)."""
        members: dict[IndustrySource, set[str]] = {}
        for industry in industries:
            members.setdefault(self._source_of(industry.industry_id), set()).add(industry.industry_id)
        return [
            outcome
            for source, ids in members.items()
            for outcome in source.data.entrant_outcomes(as_of, entry_days, horizon_days)
            if outcome.industry_id in ids
        ]
```
- `_judge_industry` 시그니처를 `(self, inputs: list[SignalInput], computed_at: datetime, profile: SignalProfile)`로 바꾸고, 본문의 `for signal in self._signals:`를 `for signal in profile.signals():`로, `RegionIndustryVerdict(...)` 생성에 `basis=profile.basis,`를 더한다.

`region_industry_verdict_use_case.py`의 `backtest` 시그니처를 `backtest(self, as_of: date, entry_days: int = 365, horizon_days: int = 1095, industry_ids: Sequence[str] | None = None)`로(`from collections.abc import Sequence`), 독스트링 끝에 "industry_ids를 주면 제외 여부와 무관하게 그 업종만 심사한다(업종 특화 신호 설계서 §8)." 추가. `build` 독스트링의 "판정 대상 12업종"은 "판정 대상 업종"으로.

- [ ] **Step 7: 카탈로그 게이트웨이 + 기존 Fake 3곳**

`industry_catalog_gateway.py` — import에 `from collections.abc import Iterable`, 클래스에:
```python
    def named_industries(self, industry_ids: Iterable[str]) -> list[JudgedIndustry]:
        ids = list(industry_ids)
        with session_scope() as session:
            rows = session.execute(
                select(IndustryOrm.industry_id, IndustryOrm.name)
                .where(IndustryOrm.industry_id.in_(ids))
                .order_by(IndustryOrm.industry_id)
            ).all()
        return [JudgedIndustry(industry_id, name) for industry_id, name in rows]
```
`tests/test_verdict_build.py`·`tests/test_verdict_backtest.py`·`tests/test_verdict_alternatives.py`의 `class FakeCatalog(IndustryCatalogPort):`에 각각 추가:
```python
    def named_industries(self, industry_ids):
        wanted = set(industry_ids)
        return [i for i in self.judged_industries() if i.industry_id in wanted]
```

- [ ] **Step 8: 통과 확인 + verdict 회귀**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_sources.py tests/test_verdict_gateways.py -q && .venv/bin/python -m pytest tests -q -k "verdict or agent"`
Expected: PASS. 특히 `test_verdict_backtest.py::test_백테스트는_상한을_넘겨_T시점_판정을_내고_결과와_조인한다`의 `ctx.calls == [("contexts", "20221"), ("counts", 2021)]`가 그대로 통과(동 맥락을 먼저, 인허가 원천의 점포수를 뒤에 읽는다).

- [ ] **Step 9: 버전 로그 + 커밋**

v0.46.0 `### Added`:
```markdown
- **업종별 원천 레지스트리** (설계서 §4) — `IndustrySignalDataPort`(창 집계·점포수·진입 결과), `IndustrySource(profile, data)`, `PermitSignalData`(기존 인허가 포트 3개 Adapter), `IndustryCatalogPort.named_industries`. 인터랙터 `sources=`로 업종별 원천 등록 — 등록 안 된 업종은 기존 인허가 원천.
```
v0.46.0 `### Changed`:
```markdown
- 인터랙터 `compute(..., industries=)`·`backtest(..., industry_ids=)` — 원천마다 1회 로드, 판정 행에 프로필 `basis`, 백테스트 결과는 원천별로 읽어 그 원천 업종만 남긴다. 집계 기반 업종은 백테스트 "전체" 합산에서 뺀다(`_SCOPES_OF_BASIS`). `BacktestReportDto.industry_basis`.
```
```bash
git add backend/apps/verdict backend/tests/test_verdict_sources.py backend/tests/test_verdict_build.py backend/tests/test_verdict_backtest.py backend/tests/test_verdict_alternatives.py backend/tests/test_verdict_gateways.py backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 판정 인터랙터 업종별 원천 레지스트리·basis·백테스트 원천별 결과

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 7: 담배소매인 편의점 원천 게이트웨이 (A 데이터)

설계서 §5-3·§5-4·§6-1. 담배소매인 전량을 한 번 읽어 편의점 에피소드와 빈자리 재료를 만든다. 창 집계는 `StoreSignalStatsGateway`의 SQL과 같은 규칙을 파이썬으로.

**Files:**
- Create: `backend/apps/verdict/adapter/outbound/gateways/tobacco_convenience_gateway.py`
- Modify: `backend/apps/verdict/dependencies/region_industry_verdict_dependencies.py`
- Test: `backend/tests/test_verdict_tobacco_source.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 4 `brand_of`·`RetailerRecord`·`Episode`·`address_key`·`fold_successions`·`GeoPoint`·`blocked_counts`·`TOBACCO_GAP_RADIUS_M`, Task 6 `IndustrySignalDataPort`·`IndustrySource`, Task 5 `TobaccoProxyProfile`·`StoreSignalStat.gap_*`
- Produces:
  - `stats_from_episodes(episodes: Iterable[Episode], today: date, industry_id: str) -> list[StoreSignalStat]` (순수, 모듈 공개 함수)
  - `TobaccoConvenienceSignalData(industry_id: str = "convenience_store", radius_m: float = TOBACCO_GAP_RADIUS_M)` — `IndustrySignalDataPort` 구현. 생성자는 DB에 닿지 않는다(`cached_property`로 지연 로드 — 라우터 요청마다 유스케이스를 새로 만든다).
  - 의존성: `sources={"convenience_store": IndustrySource(TobaccoProxyProfile(), TobaccoConvenienceSignalData())}`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `backend/tests/test_verdict_tobacco_source.py`:
```python
"""담배소매인 편의점 원천 — 창 집계 순수 함수(인허가 SQL과 같은 규칙) + DB 게이트웨이(승계·기준일·빈자리·점포수·진입 결과).
업종 특화 신호 설계서 §5·§6."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.tobacco.adapter.outbound.orms.tobacco_retailer_orm import TobaccoRetailerOrm
from apps.verdict.adapter.outbound.gateways.tobacco_convenience_gateway import (
    TobaccoConvenienceSignalData,
    stats_from_episodes,
)
from apps.verdict.domain.services.convenience_history import Episode
from core.matrix.grid_oracle_database_manager import session_scope

_TODAY = date(2099, 6, 30)
_PREFIX = "test-tbcsrc-"


def _e(open_days: int, close_days: int | None = None) -> Episode:
    d = lambda n: _TODAY - timedelta(days=n)  # noqa: E731
    return Episode("r1", d(open_days), None if close_days is None else d(close_days))


def test_창_집계는_인허가_SQL과_같은_규칙이다():
    # test_verdict_gateways.py::test_store_집계_12개월_코호트_중위개월과 같은 8행·같은 기대값
    episodes = [_e(800), _e(800, 100), _e(100), _e(1195), _e(1195, 795), _e(1195, 95), _e(2000, 200), _e(100, 200)]
    (stat,) = stats_from_episodes(episodes, _TODAY, "convenience_store")
    assert stat.industry_id == "convenience_store"
    assert (stat.start_store_count, stat.opened_12m, stat.closed_12m) == (5, 2, 4)
    assert (stat.cohort_size, stat.cohort_survived) == (3, 2)
    assert stat.closed_3y_count == 4
    assert stat.closed_3y_median_months == pytest.approx(900 / 30.4375, rel=1e-3)


def _region() -> str:
    with session_scope() as session:
        return session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)).scalar_one()


def _retailer(n, region, name, open_, close=None, jibun=None, lat=None, lng=None):
    return TobaccoRetailerOrm(
        retailer_id=f"{_PREFIX}{n}", name=name, district_code=region[:5], region_code=region,
        status_code="0" if close is None else "2", status_name="시험", designated_date=open_, permit_date=open_,
        close_date=close, cancel_date=None, lat=lat, lng=lng, road_address=None, jibun_address=jibun,
        source_updated_at=datetime(2099, 1, 1),
    )


def _store(n, region, lat, lng):
    return StoreOrm(
        store_id=f"{_PREFIX}{n}", name=f"빈자리시험{n}", industry_id="cafe", district_code=region[:5],
        region_code=region, subcategory_id=None, open_date=date(2090, 1, 1), close_date=None, status_code="01",
        status_name="영업", lat=lat, lng=lng, road_address=None, jibun_address=None,
        source_updated_at=datetime(2099, 1, 1),
    )


def test_담배소매인_원천은_편의점만_승계를_접어_원천_최신일_기준으로_센다():
    region = _region()
    addr = "서울특별시 시험구 시험동 1"
    retailers = [
        _retailer(1, region, "GS25 시험1점", date(2097, 1, 1), date(2098, 12, 1), jibun=addr),
        _retailer(2, region, "CU 시험1점", date(2098, 12, 20), jibun=addr),  # 19일 뒤 같은 지번 → 승계
        _retailer(3, region, "세븐일레븐 시험2점", date(2098, 10, 1), jibun="서울특별시 시험구 시험동 2"),
        _retailer(4, region, "행복슈퍼", date(2090, 1, 1), jibun="서울특별시 시험구 시험동 3", lat=37.5, lng=127.0),  # 편의점 아님
        _retailer(5, region, "이마트24 시험4점", date(2095, 1, 1), date(2099, 3, 1), jibun="서울특별시 시험구 시험동 4"),
        _retailer(6, region, "미니스톱 시험6점", date(2098, 4, 15), jibun="서울특별시 시험구 시험동 6"),
    ]
    stores = [_store(1, region, 37.5001, 127.0), _store(2, region, 37.51, 127.0)]  # 11m · 1.1km
    try:
        with session_scope() as session:
            session.add_all(retailers + stores)
        data = TobaccoConvenienceSignalData()
        # 원천 최신 날짜 2099-03-01(5번 폐업) < 요청일 → 기준일 2099-03-01, 12개월 창 (2098-03-01, 2099-03-01]
        stat = next(s for s in data.signal_stats(_TODAY) if s.region_code == region)
        assert stat.start_store_count == 2  # 승계 에피소드(1+2) · 5번
        assert stat.opened_12m == 2  # 3번 · 6번(기준일 고정이라 창 안). 2번은 승계라 개업이 아니다
        assert stat.closed_12m == 1  # 5번. 1번 폐업은 승계라 폐업이 아니다
        assert (stat.gap_candidates, stat.gap_blocked) == (2, 1)  # 상가 1은 행복슈퍼 11m 안
        assert {c.region_code: c.store_count for c in data.store_counts(None, None)}[region] == 3  # 승계·3번·6번
        assert {c.region_code: c.store_count for c in data.store_counts(2098, None)}[region] == 4  # 2098-12-31엔 5번도
        outcome = next(o for o in data.entrant_outcomes(date(2098, 1, 1), 365, 1095) if o.region_code == region)
        assert (outcome.opened, outcome.closed_within) == (2, 0)  # 3번·6번. 승계(2번)는 진입이 아니다
    finally:
        with session_scope() as session:
            session.execute(delete(TobaccoRetailerOrm).where(TobaccoRetailerOrm.retailer_id.like(f"{_PREFIX}%")))
            session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_PREFIX}%")))
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_tobacco_source.py -q`
Expected: FAIL — `ModuleNotFoundError: ...tobacco_convenience_gateway`

- [ ] **Step 3: 게이트웨이 구현**

Create `backend/apps/verdict/adapter/outbound/gateways/tobacco_convenience_gateway.py`:
```python
"""Driven Adapter — 편의점 개폐업 대리 원천: 담배소매인 인허가 중 편의점 상호 (업종 특화 신호 설계서 §5·§6).
창 집계는 StoreSignalStatsGateway의 SQL과 한 줄씩 대응한다 — 원천만 다르고 신호 정의는 같다.
cross-BC 접근(tobacco·store ORM)은 이 파일 안에서만. 원천이 정적 아카이브라 기준일 = min(요청일, 원천 최신 날짜)."""

import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import replace
from datetime import date, timedelta
from functools import cached_property

from sqlalchemy import or_, select

from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.tobacco.adapter.outbound.orms.tobacco_retailer_orm import TobaccoRetailerOrm
from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome, LatestStoreCount, StoreSignalStat
from apps.verdict.app.ports.output.region_industry_verdict_port import IndustrySignalDataPort
from apps.verdict.domain.services.convenience_history import (
    Episode,
    RetailerRecord,
    address_key,
    brand_of,
    fold_successions,
)
from apps.verdict.domain.services.tobacco_gap import TOBACCO_GAP_RADIUS_M, GeoPoint, blocked_counts
from core.matrix.grid_oracle_database_manager import session_scope

_DAYS_PER_MONTH = 30.4375
_THREE_YEARS_DAYS = 3 * 365
_EXPIRED_TEMPORARY = "4"  # 임시소매기간만료 — 폐업일 없이 끝난 임시 지정. 빈자리 계산에서 뺀다


def _active(open_date: date, close_date: date | None, at: date) -> bool:
    return open_date <= at and (close_date is None or close_date > at)


def stats_from_episodes(episodes: Iterable[Episode], today: date, industry_id: str) -> list[StoreSignalStat]:
    """동별 창 집계 — StoreSignalStatsGateway.signal_stats와 같은 규칙 (판정 카드 설계서 §3-1).
    12개월 전 영업 / 12개월 개·폐업 / [today−4y, today−3y) 코호트·3년 생존 / 최근 3년 폐업 영업개월 중위(폐업일<개업일 제외)."""
    since_12m = today - timedelta(days=365)
    cohort_to = today - timedelta(days=3 * 365)
    cohort_from = today - timedelta(days=4 * 365)
    acc: dict[str, dict] = defaultdict(
        lambda: {"start": 0, "opened": 0, "closed": 0, "cohort": 0, "survived": 0, "months": []}
    )
    for e in episodes:
        a = acc[e.region_code]
        days_open = None if e.close_date is None else (e.close_date - e.open_date).days
        in_cohort = cohort_from <= e.open_date < cohort_to
        a["start"] += e.open_date <= since_12m and (e.close_date is None or e.close_date > since_12m)
        a["opened"] += since_12m < e.open_date <= today
        a["closed"] += e.close_date is not None and since_12m < e.close_date <= today
        a["cohort"] += in_cohort
        a["survived"] += in_cohort and (days_open is None or days_open >= _THREE_YEARS_DAYS)
        if e.close_date is not None and cohort_to <= e.close_date <= today and days_open >= 0:
            a["months"].append(days_open / _DAYS_PER_MONTH)
    return [
        StoreSignalStat(
            region, industry_id, a["start"], a["opened"], a["closed"], a["cohort"], a["survived"],
            len(a["months"]), statistics.median(a["months"]) if a["months"] else None,
        )
        for region, a in sorted(acc.items())
    ]


class TobaccoConvenienceSignalData(IndustrySignalDataPort):
    def __init__(self, industry_id: str = "convenience_store", radius_m: float = TOBACCO_GAP_RADIUS_M) -> None:
        self._industry_id = industry_id
        self._radius_m = radius_m

    @cached_property
    def _rows(self) -> list:
        T = TobaccoRetailerOrm
        with session_scope() as session:
            return session.execute(
                select(
                    T.retailer_id, T.name, T.region_code, T.designated_date, T.permit_date, T.close_date,
                    T.cancel_date, T.jibun_address, T.lat, T.lng, T.status_code,
                )
            ).all()

    @cached_property
    def _records(self) -> list[RetailerRecord]:
        return [
            RetailerRecord(
                r.retailer_id, r.name, r.region_code, r.designated_date or r.permit_date,
                r.close_date or r.cancel_date, address_key(r.jibun_address),
            )
            for r in self._rows
        ]

    @cached_property
    def _latest(self) -> date:
        """원천 최신 날짜 — 정적 아카이브(2026-08 확보)라 오늘보다 앞선다 (설계서 §5-3)."""
        return max(d for r in self._records for d in (r.open_date, r.close_date) if d is not None)

    @cached_property
    def _episodes(self) -> list[Episode]:
        return fold_successions(r for r in self._records if brand_of(r.name) is not None)

    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        anchor = min(today, self._latest)
        stats = {s.region_code: s for s in stats_from_episodes(self._episodes, anchor, self._industry_id)}
        gaps = self._gaps(anchor)
        empty = StoreSignalStat("", self._industry_id, 0, 0, 0, 0, 0, 0, None)
        return [
            replace(
                stats.get(region, replace(empty, region_code=region)),
                gap_candidates=gaps.get(region, (0, 0))[0],
                gap_blocked=gaps.get(region, (0, 0))[1],
            )
            for region in sorted(stats.keys() | gaps.keys())
        ]

    def store_counts(self, year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]:
        """기준일에 영업 중인 에피소드 수 — 배치는 원천 최신 날짜, 백테스트는 year_max년 말 (설계서 §5-3)."""
        at = self._latest if year_max is None else date(year_max, 12, 31)
        counts = Counter(e.region_code for e in self._episodes if _active(e.open_date, e.close_date, at))
        return [LatestStoreCount(region, self._industry_id, n) for region, n in sorted(counts.items())]

    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        acc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        entry_end = as_of + timedelta(days=entry_days)
        for e in self._episodes:
            if as_of <= e.open_date < entry_end:
                cell = acc[e.region_code]
                cell[0] += 1
                cell[1] += e.close_date is not None and 0 <= (e.close_date - e.open_date).days <= horizon_days
        return [EntrantOutcome(region, self._industry_id, opened, closed) for region, (opened, closed) in sorted(acc.items())]

    def _gaps(self, anchor: date) -> dict[str, tuple[int, int]]:
        """담배권 빈자리 재료 (설계서 §6-1) — 후보 = 기준일 영업 상가(업종 무관), 소매인 = 기준일 영업 담배소매인(편의점 여부 무관)."""
        retailers = [
            GeoPoint(row.region_code, row.lat, row.lng)
            for row, record in zip(self._rows, self._records)
            if row.lat is not None and row.lng is not None and row.status_code != _EXPIRED_TEMPORARY
            and record.open_date is not None and _active(record.open_date, record.close_date, anchor)
        ]
        with session_scope() as session:
            candidates = [
                GeoPoint(region, lat, lng)
                for region, lat, lng in session.execute(
                    select(StoreOrm.region_code, StoreOrm.lat, StoreOrm.lng).where(
                        StoreOrm.region_code.is_not(None), StoreOrm.lat.is_not(None), StoreOrm.lng.is_not(None),
                        StoreOrm.open_date <= anchor,
                        or_(StoreOrm.close_date.is_(None), StoreOrm.close_date > anchor),
                    )
                ).all()
            ]
        return blocked_counts(candidates, retailers, self._radius_m)
```

- [ ] **Step 4: 의존성 등록**

`region_industry_verdict_dependencies.py`에 import:
```python
from apps.verdict.adapter.outbound.gateways.tobacco_convenience_gateway import TobaccoConvenienceSignalData
from apps.verdict.app.use_cases.industry_source import IndustrySource
from apps.verdict.domain.services.profiles import TobaccoProxyProfile
```
`RegionIndustryVerdictInteractor(...)` 인자 끝에:
```python
        # 업종별 원천 (업종 특화 신호 설계서 §4) — 판정 대상 여부는 EXCLUDED_INDUSTRIES가 따로 정한다
        sources={
            "convenience_store": IndustrySource(TobaccoProxyProfile(), TobaccoConvenienceSignalData()),
        },
```

- [ ] **Step 5: 통과 확인 + 회귀**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_tobacco_source.py -q && .venv/bin/python -m pytest tests -q -k "verdict or agent"`
Expected: PASS (`test_myself_배선_200`이 실제 DI로 생성자를 부른다 — 생성자가 DB에 닿지 않아야 통과).

- [ ] **Step 6: 개발 DB 스모크 (읽기만)**

아래 파이썬을 `cd backend && time PYTHONPATH=. .venv/bin/python -c '<코드>'` 또는 임시 파일(스크래치 디렉터리, 커밋 금지)로 실행한다:
```python
from datetime import date
from apps.verdict.adapter.outbound.gateways.tobacco_convenience_gateway import TobaccoConvenienceSignalData
d = TobaccoConvenienceSignalData()
s = d.signal_stats(date.today())
print("동", len(s), "기준일", d._latest, "12개월전영업", sum(x.start_store_count for x in s),
      "개업", sum(x.opened_12m for x in s), "폐업", sum(x.closed_12m for x in s),
      "빈자리후보", sum(x.gap_candidates for x in s), "막힘", sum(x.gap_blocked for x in s))
print("영업중", sum(c.store_count for c in d.store_counts(None, None)), "에피소드", len(d._episodes))
```
Expected(설계서 §2 사전 조사, ±5%): 동 427 안팎, 기준일 2026-08-21, 12개월 전 영업 약 7,900, 개업 약 370, 폐업 약 520, 빈자리 후보 약 25만·막힘 약 65%, 영업중 약 7,600, 에피소드 약 20,900, 소요 10초 이내. 크게 다르면 멈추고 보고한다.

- [ ] **Step 7: 버전 로그 + 커밋**

v0.46.0 `### Added`:
```markdown
- **담배소매인 편의점 원천** (설계서 §5·§6) — `TobaccoConvenienceSignalData`: 브랜드 사전 매칭 → 승계 접기 에피소드로 창 집계(`stats_from_episodes`, 인허가 SQL과 같은 규칙), 기준일 = min(요청일, 원천 최신 2026-08-21), 점포수·진입 결과, 담배권 빈자리(영업 상가 × 영업 담배소매인 50m). 의존성에 `convenience_store` 등록(판정 대상 편입은 게이트 후).
```
```bash
git add backend/apps/verdict backend/tests/test_verdict_tobacco_source.py backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 담배소매인 편의점 원천 — 에피소드 창 집계·기준일 고정·담배권 빈자리

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 상권분석 집계 원천 게이트웨이 (E 데이터 — 부동산)

설계서 §7-1·§7-3. `region_commerce_store`의 CS200033으로 폐업률 재료·점포수·재고 결과를 만든다.

**Files:**
- Modify: `backend/apps/verdict/domain/services/backtest.py` (`quarter_of`·`shift_quarter`)
- Create: `backend/apps/verdict/adapter/outbound/gateways/commerce_aggregate_gateway.py`
- Modify: `backend/apps/verdict/dependencies/region_industry_verdict_dependencies.py`
- Test: `backend/tests/test_verdict_backtest.py` (분기 보조 함수), Create `backend/tests/test_verdict_commerce_source.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 6 `IndustrySignalDataPort`·`IndustrySource`, Task 5 `AggregateProfile`, 기존 `quarter_before(as_of) -> str`
- Produces:
  - `quarter_of(d: date) -> str` (`date(2022,6,30)` → `"20222"`), `shift_quarter(year_quarter: str, n: int) -> str` (`("20254", -4)` → `"20244"`)
  - `CommerceAggregateSignalData(industry_ids: Iterable[str])` — `IndustrySignalDataPort` 구현:
    - `signal_stats(today)`: `q_last` = 원천 분기 중 `quarter_before(today)` 이하 최신, `q0 = shift_quarter(q_last, -4)`. `start_store_count` = q0 점포수 합, `closed_12m`·`opened_12m` = (q0, q_last] 폐업·개업 합. 코호트 필드 0·None.
    - `store_counts(year_max, quarter_max)`: `quarter_max` 이하 최신 분기 점포수 합(None이면 최신). `year_max`는 쓰지 않는다.
    - `entrant_outcomes(as_of, entry_days, horizon_days)`: `opened` = `quarter_of(as_of)` 점포수, `closed_within` = (그 분기, `quarter_of(as_of + horizon_days)`] 폐업 합. `entry_days`는 쓰지 않는다.
  - 의존성: `"real_estate": IndustrySource(AggregateProfile(), CommerceAggregateSignalData(("real_estate",)))`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_verdict_backtest.py` — import에 `quarter_of, shift_quarter` 추가(기존 `quarter_before` 옆), `test_직전_분기_라벨` 아래에:
```python
def test_분기_보조_함수():
    assert quarter_of(date(2022, 6, 30)) == "20222"
    assert quarter_of(date(2022, 7, 1)) == "20223"
    assert shift_quarter("20254", -4) == "20244"
    assert shift_quarter("20221", -1) == "20214"
    assert shift_quarter("20214", 1) == "20221"
```
Create `backend/tests/test_verdict_commerce_source.py`:
```python
"""상권분석 집계 원천 — 4분기 창·동 합산·점포수 상한·재고 결과 (업종 특화 신호 설계서 §7, 실 DB)."""

from datetime import date

from sqlalchemy import delete, select

from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.verdict.adapter.outbound.gateways.commerce_aggregate_gateway import CommerceAggregateSignalData
from core.matrix.grid_oracle_database_manager import session_scope

_ADSTRD = ("T9700001", "T9700002")
_CODE = "CS200033"  # real_estate ↔ seoul_commercial (마이그레이션 c7a4f2e19b35 시드)


def _region() -> str:
    with session_scope() as session:
        return session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)).scalar_one()


def _row(adstrd, region, quarter, store, opened=0, closed=0):
    return RegionCommerceStoreOrm(
        adstrd_code=adstrd, service_industry_code=_CODE, year_quarter=quarter, region_code=region,
        store_count=store, similar_industry_store_count=None, open_rate=None, open_store_count=opened,
        close_rate=None, close_store_count=closed, franchise_store_count=None,
    )


def test_집계_원천은_최근_4분기_폐업과_4분기_전_점포수를_동별로_합한다():
    region = _region()
    rows = [
        _row(_ADSTRD[0], region, "20973", 100, opened=3, closed=5),
        _row(_ADSTRD[0], region, "20974", 102, opened=6, closed=4),
        _row(_ADSTRD[0], region, "20981", 101, opened=1, closed=3),
        _row(_ADSTRD[0], region, "20982", 99, opened=2, closed=2),
        _row(_ADSTRD[0], region, "20983", 90, opened=0, closed=6),
        _row(_ADSTRD[0], region, "20984", 80, opened=0, closed=9),  # 기준 분기 뒤 — 창 밖
        _row(_ADSTRD[1], region, "20973", 10),  # 같은 동의 두 번째 상권코드
        _row(_ADSTRD[1], region, "20983", 10, closed=1),
    ]
    try:
        with session_scope() as session:
            session.add_all(rows)
        data = CommerceAggregateSignalData(("real_estate",))
        # today 2098-12-31 → 직전 분기 20983 → 창 (20973, 20983]
        stat = next(s for s in data.signal_stats(date(2098, 12, 31)) if s.region_code == region)
        assert stat.industry_id == "real_estate"
        assert stat.start_store_count == 110  # 20973: 100 + 10
        assert stat.closed_12m == 4 + 3 + 2 + 6 + 1
        assert stat.opened_12m == 6 + 1 + 2 + 0
        assert (stat.cohort_size, stat.closed_3y_count, stat.closed_3y_median_months) == (0, 0, None)
        count = lambda quarter_max: next(  # noqa: E731
            c.store_count for c in data.store_counts(None, quarter_max) if c.region_code == region
        )
        assert count(None) == 80  # 최신 20984
        assert count("20982") == 99
        outcome = next(o for o in data.entrant_outcomes(date(2097, 9, 30), 365, 365) if o.region_code == region)
        assert (outcome.opened, outcome.closed_within) == (110, 4 + 3 + 2 + 6 + 1)  # 노출 20973, 폐업 20974~20983
    finally:
        with session_scope() as session:
            session.execute(delete(RegionCommerceStoreOrm).where(RegionCommerceStoreOrm.adstrd_code.in_(_ADSTRD)))
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_backtest.py tests/test_verdict_commerce_source.py -q`
Expected: FAIL — `ImportError: cannot import name 'quarter_of'`

- [ ] **Step 3: 분기 보조 함수**

`domain/services/backtest.py`의 `quarter_before` 아래:
```python
def quarter_of(d: date) -> str:
    """d가 속한 분기 라벨('20222')."""
    return f"{d.year}{(d.month - 1) // 3 + 1}"


def shift_quarter(year_quarter: str, n: int) -> str:
    """분기 라벨을 n분기 옮긴다 — shift_quarter('20254', -4) == '20244'."""
    index = int(year_quarter[:4]) * 4 + int(year_quarter[4]) - 1 + n
    return f"{index // 4}{index % 4 + 1}"
```

- [ ] **Step 4: 게이트웨이 구현**

Create `backend/apps/verdict/adapter/outbound/gateways/commerce_aggregate_gateway.py`:
```python
"""Driven Adapter — 집계 원천: 서울시 상권분석 동×분기 점포·폐업 수 (업종 특화 신호 설계서 §7). 개별 점포 이력이 없는 업종(부동산).
업종 ↔ 서비스업종 코드는 industry_source_code(source_system='seoul_commercial'), 코드·상권코드가 여럿이면 동 단위로 합한다.
cross-BC 접근(commerce·master ORM)은 이 파일 안에서만."""

from collections.abc import Iterable
from datetime import date, timedelta
from functools import cached_property

from sqlalchemy import func, select

from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm
from apps.master.adapter.outbound.orms.industry_source_code_orm import IndustrySourceCodeOrm
from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome, LatestStoreCount, StoreSignalStat
from apps.verdict.app.ports.output.region_industry_verdict_port import IndustrySignalDataPort
from apps.verdict.domain.services.backtest import quarter_before, quarter_of, shift_quarter
from core.matrix.grid_oracle_database_manager import session_scope

_SOURCE_SYSTEM = "seoul_commercial"
_WINDOW_QUARTERS = 4  # 폐업률 창 — 12개월 창과 같은 길이

S = RegionCommerceStoreOrm


class CommerceAggregateSignalData(IndustrySignalDataPort):
    def __init__(self, industry_ids: Iterable[str]) -> None:
        self._industry_ids = tuple(industry_ids)

    @cached_property
    def _industry_of_code(self) -> dict[str, str]:
        with session_scope() as session:
            rows = session.execute(
                select(IndustrySourceCodeOrm.code, IndustrySourceCodeOrm.industry_id).where(
                    IndustrySourceCodeOrm.source_system == _SOURCE_SYSTEM,
                    IndustrySourceCodeOrm.industry_id.in_(self._industry_ids),
                )
            ).all()
        return dict(rows)

    @cached_property
    def _quarters(self) -> list[str]:
        with session_scope() as session:
            return list(
                session.execute(
                    select(S.year_quarter).where(S.service_industry_code.in_(self._industry_of_code))
                    .distinct().order_by(S.year_quarter)
                ).scalars()
            )

    def _latest_at_or_before(self, quarter: str | None) -> str | None:
        eligible = [q for q in self._quarters if quarter is None or q <= quarter]
        return eligible[-1] if eligible else None

    def _between(self, after: str, upto: str) -> list[str]:
        return [q for q in self._quarters if after < q <= upto]

    def _sum(self, column, quarters: list[str]) -> dict[tuple[str, str], int]:
        """(동, 업종)별 column 합 — 주어진 분기들. 동 미배정 행은 뺀다."""
        if not quarters:
            return {}
        with session_scope() as session:
            rows = session.execute(
                select(S.region_code, S.service_industry_code, func.coalesce(func.sum(column), 0))
                .where(
                    S.region_code.is_not(None),
                    S.service_industry_code.in_(self._industry_of_code),
                    S.year_quarter.in_(quarters),
                )
                .group_by(S.region_code, S.service_industry_code)
            ).all()
        acc: dict[tuple[str, str], int] = {}
        for region, code, total in rows:
            key = (region, self._industry_of_code[code])
            acc[key] = acc.get(key, 0) + int(total)
        return acc

    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        """폐업률 재료 — (q0, q_last] 폐업·개업 합과 q0 점포수 (설계서 §7-1). 코호트 항목은 원천에 없어 0."""
        last = self._latest_at_or_before(quarter_before(today))
        if last is None:
            return []
        first = shift_quarter(last, -_WINDOW_QUARTERS)
        window = self._between(first, last)
        start = self._sum(S.store_count, [first])
        closed = self._sum(S.close_store_count, window)
        opened = self._sum(S.open_store_count, window)
        return [
            StoreSignalStat(region, industry, start.get((region, industry), 0), opened.get((region, industry), 0),
                            closed.get((region, industry), 0), 0, 0, 0, None)
            for region, industry in sorted(start.keys() | closed.keys())
        ]

    def store_counts(self, year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]:
        """포화 분자 — quarter_max 이하 최신 분기 점포수. 분기 원천이라 연도 상한(year_max)보다 촘촘한 quarter_max만 본다."""
        at = self._latest_at_or_before(quarter_max)
        if at is None:
            return []
        return [LatestStoreCount(r, i, n) for (r, i), n in sorted(self._sum(S.store_count, [at]).items())]

    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        """재고 결과 (설계서 §7-3) — opened = as_of 분기 점포수, closed_within = 다음 분기 ~ as_of+horizon 분기 폐업 합.
        개별 개업일이 없어 진입 코호트를 만들 수 없다 — entry_days는 쓰지 않는다."""
        exposure_quarter = quarter_of(as_of)
        horizon_quarter = quarter_of(as_of + timedelta(days=horizon_days))
        exposure = self._sum(S.store_count, [exposure_quarter])
        closed = self._sum(S.close_store_count, self._between(exposure_quarter, horizon_quarter))
        return [EntrantOutcome(r, i, n, closed.get((r, i), 0)) for (r, i), n in sorted(exposure.items())]
```

- [ ] **Step 5: 의존성 등록**

`region_industry_verdict_dependencies.py` import에 `from apps.verdict.adapter.outbound.gateways.commerce_aggregate_gateway import CommerceAggregateSignalData`와 `AggregateProfile`(profiles에서 `TobaccoProxyProfile` 옆) 추가, `sources`에:
```python
            "real_estate": IndustrySource(AggregateProfile(), CommerceAggregateSignalData(("real_estate",))),
```

- [ ] **Step 6: 통과 확인 + 회귀**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_backtest.py tests/test_verdict_commerce_source.py -q && .venv/bin/python -m pytest tests -q -k verdict`
Expected: PASS

- [ ] **Step 7: 개발 DB 스모크 (읽기만)**

Task 7 Step 6과 같은 방식으로 실행:
```python
from datetime import date
from apps.verdict.adapter.outbound.gateways.commerce_aggregate_gateway import CommerceAggregateSignalData
d = CommerceAggregateSignalData(("real_estate",))
s = d.signal_stats(date.today())
print("동", len(s), "시작점포", sum(x.start_store_count for x in s), "4분기폐업", sum(x.closed_12m for x in s),
      "개업", sum(x.opened_12m for x in s), "폐업0동", sum(1 for x in s if x.closed_12m == 0))
print("점포수(최신)", sum(c.store_count for c in d.store_counts(None, None)))
t = d.signal_stats(date(2022, 6, 30))
print("T=2022-06-30 폐업", sum(x.closed_12m for x in t), "시작점포", sum(x.start_store_count for x in t))
```
Expected(설계서 §2-3): 동 422 · 시작 점포 40,129(20244) · 4분기 폐업 2,985(20251~20254) · 개업 150 · 점포수(20254) 37,169 · T 시점 시작 점포(20211) 약 42,000·폐업(20212~20221) 수천. "폐업0동" 값은 Task 12 기록(설계서 §15 리스크)에 옮긴다.

- [ ] **Step 8: 버전 로그 + 커밋**

v0.46.0 `### Added`:
```markdown
- **상권분석 집계 원천** (설계서 §7) — `CommerceAggregateSignalData`: `region_commerce_store`(업종 ↔ `seoul_commercial` 코드)에서 최근 4분기 폐업·4분기 전 점포수(폐업률 재료), 분기 상한 점포수(포화), 재고 결과(T 분기 점포수 대비 이후 폐업). `quarter_of`·`shift_quarter`. 의존성에 `real_estate` 등록(판정 대상 편입은 게이트 후).
```
```bash
git add backend/apps/verdict backend/tests/test_verdict_backtest.py backend/tests/test_verdict_commerce_source.py backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 상권분석 집계 원천 — 부동산 폐업률·포화·재고 결과

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: 재포함 게이트 · 백테스트 CLI 심사 절

설계서 §8. 게이트는 도메인 순수 함수, CLI는 `--candidates`로 제외 업종을 따로 심사해 같은 문서에 절을 붙인다.

**Files:**
- Modify: `backend/apps/verdict/domain/services/backtest.py` (`GatePolicy`·`GATE_POLICIES`·`GateResult`·`reinclusion_gate`)
- Modify: `backend/apps/verdict/app/dtos/region_industry_verdict_dto.py` (`BacktestGateDto`, `BacktestReportDto.gates`)
- Modify: `backend/apps/verdict/app/use_cases/region_industry_verdict_interactor.py` (`backtest`가 게이트 계산)
- Modify: `backend/apps/verdict/adapter/inbound/cli/backtest_verdicts.py`
- Test: `backend/tests/test_verdict_backtest.py`, Create `backend/tests/test_verdict_backtest_cli.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 6 `summarize`·`BacktestReportDto.industry_basis`·`_source_of`, Task 3 `BASIS_*`
- Produces:
  - `GatePolicy(min_lift: float, min_opened: int, min_pairs: int)`(frozen), `GATE_POLICIES: dict[str, GatePolicy]` = `{permit: (1.10, 50, 0), proxy: (1.10, 50, 0), aggregate: (1.10, 0, 30)}`
  - `GateResult(industry_id, passed: bool, warn_lift: float | None, warn_opened, clear_opened, warn_pairs, clear_pairs, reason: str)` — `reason`은 `"통과"` 또는 `"미달 — …"`
  - `reinclusion_gate(buckets: Iterable[OutcomeBucket], industry_id: str, policy: GatePolicy) -> GateResult`
  - `BacktestGateDto(industry_id, industry_name, basis, passed, warn_lift, warn_opened, clear_opened, warn_pairs, clear_pairs, reason)`, `BacktestReportDto.gates: tuple[BacktestGateDto, ...] = ()`
  - `render_markdown(report, today, candidates: BacktestReportDto | None = None) -> str`, CLI `--candidates convenience_store,real_estate`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_verdict_backtest.py` — `from apps.verdict.domain.services.backtest import ...`에 `GATE_POLICIES, OutcomeBucket, reinclusion_gate` 추가, `import pytest`가 없으면 추가, 파일 끝에:
```python
def _b(industry, code, pairs, opened, closed):
    return OutcomeBucket(industry, code, pairs, opened, closed)


def test_게이트는_경고_lift_1_10과_표본을_모두_넘어야_통과한다():
    buckets = [
        _b("convenience_store", "red", 3, 20, 8),
        _b("convenience_store", "orange", 100, 400, 80),
        _b("convenience_store", "clear", 80, 200, 30),
        _b("convenience_store", "insufficient", 50, 60, 30),  # 보류는 게이트에 안 들어간다
        _b(None, "clear", 1, 1, 1),
    ]
    gate = reinclusion_gate(buckets, "convenience_store", GATE_POLICIES["proxy"])
    assert gate.passed and gate.reason == "통과"
    assert gate.warn_lift == pytest.approx((88 / 420) / (30 / 200))
    assert (gate.warn_opened, gate.clear_opened, gate.warn_pairs, gate.clear_pairs) == (420, 200, 103, 80)


def test_게이트_경고_lift가_1_10_미만이면_미달이다():
    gate = reinclusion_gate([_b("x", "orange", 100, 400, 60), _b("x", "clear", 80, 200, 30)], "x", GATE_POLICIES["proxy"])
    assert not gate.passed and "경고 lift 1.00×" in gate.reason


def test_게이트_대리_원천은_개업_50곳_미만이면_미달이다():
    gate = reinclusion_gate([_b("x", "orange", 10, 49, 20), _b("x", "clear", 10, 200, 20)], "x", GATE_POLICIES["proxy"])
    assert not gate.passed and "개업" in gate.reason


def test_게이트_집계_원천은_동_30곳_미만이면_미달이다():
    gate = reinclusion_gate(
        [_b("x", "orange", 29, 5000, 900), _b("x", "clear", 200, 20000, 2000)], "x", GATE_POLICIES["aggregate"]
    )
    assert not gate.passed and "동×업종" in gate.reason


def test_게이트_경고_없음_판정이_없으면_lift를_못_내고_미달이다():
    gate = reinclusion_gate([_b("x", "orange", 50, 500, 50)], "x", GATE_POLICIES["proxy"])
    assert not gate.passed and gate.warn_lift is None and "계산 불가" in gate.reason
```
Create `backend/tests/test_verdict_backtest_cli.py`:
```python
"""백테스트 CLI 렌더 — 재포함 심사 절·원천 표기·† (업종 특화 신호 설계서 §7-3·§8)."""

from datetime import date

from apps.verdict.adapter.inbound.cli.backtest_verdicts import render_markdown
from apps.verdict.app.dtos.region_industry_verdict_dto import BacktestBucketDto, BacktestGateDto, BacktestReportDto


def _report(industry, name, basis, gates=()):
    buckets = (
        BacktestBucketDto(industry, name, "orange", 100, 400, 80),
        BacktestBucketDto(industry, name, "clear", 80, 200, 30),
    )
    return BacktestReportDto(
        as_of=date(2022, 6, 30), quarter_max="20221", year_max=2021, entry_days=365, horizon_days=1095,
        buckets=buckets, signal_buckets=(), industry_basis=((industry, basis),), gates=gates,
    )


def test_심사_절은_원천과_경고_lift와_게이트_결과를_찍는다():
    gate = BacktestGateDto("convenience_store", "편의점", "proxy", True, 1.4, 400, 200, 100, 80, "통과")
    text = render_markdown(
        _report("korean_food", "한식", "permit"), date(2026, 9, 29), _report("convenience_store", "편의점", "proxy", (gate,))
    )
    assert "## 재포함 심사" in text
    assert "| 편의점 | 담배소매인 이력 |" in text and "| 1.40× | 통과 |" in text


def test_심사_대상이_없으면_심사_절이_없다():
    assert "## 재포함 심사" not in render_markdown(_report("korean_food", "한식", "permit"), date(2026, 9, 29))


def test_집계_기반_업종은_업종표에_칼표를_단다():
    text = render_markdown(_report("real_estate", "부동산중개업", "aggregate"), date(2026, 9, 29))
    assert "| 부동산중개업 † |" in text
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_backtest.py tests/test_verdict_backtest_cli.py -q`
Expected: FAIL — `ImportError: cannot import name 'GATE_POLICIES'`

- [ ] **Step 3: 게이트 (도메인)**

`domain/services/backtest.py` 파일 끝에:
```python
@dataclass(frozen=True)
class GatePolicy:
    min_lift: float  # 경고(🔴+🟠) 폐업률 ÷ ⚪ 폐업률 하한
    min_opened: int  # 경고·⚪ 각각의 개업(또는 집계 노출) 하한
    min_pairs: int  # 경고·⚪ 각각의 동×업종 하한


# 재포함 게이트 (업종 특화 신호 설계서 §8). 1.10 = 작동한다고 본 카페 1.36·미용실 1.16과 못 가른 나머지(≤1.08) 사이.
# 대리 원천은 개업 50곳(폐업률 15%에서 표준오차 약 5%p), 집계 원천은 결과 단위가 동이라 동 30곳.
GATE_POLICIES: dict[str, GatePolicy] = {
    BASIS_PERMIT: GatePolicy(min_lift=1.10, min_opened=50, min_pairs=0),
    BASIS_PROXY: GatePolicy(min_lift=1.10, min_opened=50, min_pairs=0),
    BASIS_AGGREGATE: GatePolicy(min_lift=1.10, min_opened=0, min_pairs=30),
}

_WARN_CODES = frozenset({"red", "orange"})


@dataclass(frozen=True)
class GateResult:
    industry_id: str
    passed: bool
    warn_lift: float | None
    warn_opened: int
    clear_opened: int
    warn_pairs: int
    clear_pairs: int
    reason: str  # "통과" 또는 "미달 — …"


def _fmt_lift(lift: float | None) -> str:
    return "계산 불가" if lift is None else f"{lift:.2f}×"


def reinclusion_gate(buckets: Iterable[OutcomeBucket], industry_id: str, policy: GatePolicy) -> GateResult:
    """업종 버킷으로 재포함 게이트를 판정한다. 보류(insufficient)는 넣지 않는다."""
    own = [b for b in buckets if b.industry_id == industry_id]
    warn = [b for b in own if b.verdict_code in _WARN_CODES]
    clear = [b for b in own if b.verdict_code == "clear"]
    w_pairs, w_opened, w_closed = sum(b.pairs for b in warn), sum(b.opened for b in warn), sum(b.closed for b in warn)
    c_pairs, c_opened, c_closed = sum(b.pairs for b in clear), sum(b.opened for b in clear), sum(b.closed for b in clear)
    lift = None if not (w_opened and c_opened and c_closed) else (w_closed / w_opened) / (c_closed / c_opened)
    failures = [
        message
        for failed, message in (
            (min(w_pairs, c_pairs) < policy.min_pairs,
             f"동×업종 경고 {w_pairs}·경고 없음 {c_pairs} < {policy.min_pairs}"),
            (min(w_opened, c_opened) < policy.min_opened,
             f"개업 경고 {w_opened:,}·경고 없음 {c_opened:,} < {policy.min_opened}"),
            (lift is None or lift < policy.min_lift,
             f"경고 lift {_fmt_lift(lift)} < {policy.min_lift:.2f}×"),
        )
        if failed
    ]
    reason = "통과" if not failures else "미달 — " + "; ".join(failures)
    return GateResult(industry_id, not failures, lift, w_opened, c_opened, w_pairs, c_pairs, reason)
```

- [ ] **Step 4: DTO·인터랙터**

`region_industry_verdict_dto.py` — `BacktestReportDto` **앞에**:
```python
@dataclass(frozen=True)
class BacktestGateDto:
    """재포함 게이트 결과 (업종 특화 신호 설계서 §8)."""

    industry_id: str
    industry_name: str | None
    basis: str
    passed: bool
    warn_lift: float | None
    warn_opened: int
    clear_opened: int
    warn_pairs: int
    clear_pairs: int
    reason: str
```
`BacktestReportDto`의 `industry_basis` 아래에 `gates: tuple[BacktestGateDto, ...] = ()`.
인터랙터 — import에 `BacktestGateDto`, backtest 모듈에서 `GATE_POLICIES, reinclusion_gate`. `backtest`의 `names = ...` 줄부터 `return` 끝까지를:
```python
        names = {i.industry_id: i.name for i in industries}
        basis_of = {i.industry_id: self._source_of(i.industry_id).profile.basis for i in industries}
        buckets = summarize(verdicts, outcomes)
        return BacktestReportDto(
            as_of=as_of, quarter_max=quarter_max, year_max=year_max, entry_days=entry_days, horizon_days=horizon_days,
            buckets=tuple(
                BacktestBucketDto(b.industry_id, names.get(b.industry_id), b.verdict_code, b.pairs, b.opened, b.closed)
                for b in buckets
            ),
            signal_buckets=tuple(
                BacktestSignalBucketDto(b.industry_id, names.get(b.industry_id), b.signal_key, b.fired, b.pairs, b.opened, b.closed)
                for b in summarize_signals(verdicts, outcomes)
            ),
            industry_basis=tuple(basis_of.items()),
            gates=tuple(
                BacktestGateDto(g.industry_id, names.get(g.industry_id), basis_of[g.industry_id], g.passed, g.warn_lift,
                                g.warn_opened, g.clear_opened, g.warn_pairs, g.clear_pairs, g.reason)
                for g in (reinclusion_gate(buckets, i, GATE_POLICIES[basis_of[i]]) for i in basis_of)
            ),
        )
```

- [ ] **Step 5: CLI**

`backtest_verdicts.py`:
- import: `SIGNAL_KEYS` → `ALL_SIGNAL_KEYS`, DTO import에 `BacktestGateDto`는 불필요(타입만 쓰면 생략 가능).
- `_SIGNAL_LABEL`에 `"closure_rate": "폐업률", "tobacco_gap": "담배권 빈자리"` 추가. 새 상수:
```python
_BASIS_LABEL = {"permit": "인허가", "proxy": "담배소매인 이력", "aggregate": "상권분석 집계 †"}
_NAME_SUFFIX = {"aggregate": " †"}  # 집계 기반 — 개업 대신 점포수, 3년 폐업 대신 이후 12분기 폐업 (설계서 §7-3)
```
- 헬퍼 추가(`render_markdown` 위):
```python
def _industry_name(report: BacktestReportDto, industry: str) -> str:
    basis = dict(report.industry_basis).get(industry, "permit")
    name = next((b.industry_name for b in report.buckets if b.industry_id == industry and b.industry_name), industry)
    return name + _NAME_SUFFIX.get(basis, "")


def _signal_lines(report: BacktestReportDto, industries: list[str | None]) -> list[str]:
    lines = [
        "| 업종 | " + " | ".join(_SIGNAL_LABEL[k] for k in ALL_SIGNAL_KEYS) + " |",
        "|---|" + "---:|" * len(ALL_SIGNAL_KEYS),
    ]
    for industry in industries:
        cells = [_signal_cell(report.signal_buckets, industry, key) for key in ALL_SIGNAL_KEYS]
        name = "전체" if industry is None else _industry_name(report, industry)
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return lines


def _candidate_lines(report: BacktestReportDto) -> list[str]:
    lines = [
        "", "## 재포함 심사 — 업종 특화 원천 (업종 특화 신호 설계서 §8)", "",
        "> 게이트: 경고(🔴+🟠) 폐업률 ÷ ⚪ 폐업률 ≥ 1.10×. 표본 — 담배소매인 이력은 경고·⚪ 개업 각 50곳 이상, "
        "상권분석 집계는 경고·⚪ 동 각 30곳 이상. 판정 대상 여부와 무관하게 이 업종들만 다시 판정했다.",
        "> † 집계 기반: 괄호 안은 개업 수가 아니라 T 분기 점포수, 폐업은 이후 12분기 폐업 수.",
        "",
        "| 업종 | 원천 | 🔴 폐업률 (개업) | 🟠 폐업률 (개업) | ⚪ 폐업률 (개업) | 보류 (개업) | 경고 lift | 게이트 |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for gate in report.gates:
        cells = {b.verdict_code: b for b in report.buckets if b.industry_id == gate.industry_id}
        cell = lambda code: f"{_pct(cells[code].rate)} ({cells[code].opened:,})" if code in cells else "—"  # noqa: E731
        lift = "—" if gate.warn_lift is None else f"{gate.warn_lift:.2f}×"
        lines.append(
            f"| {gate.industry_name or gate.industry_id} | {_BASIS_LABEL[gate.basis]} | {cell('red')} | {cell('orange')} "
            f"| {cell('clear')} | {cell('insufficient')} | {lift} | {gate.reason} |"
        )
    lines += ["", "### 심사 업종 신호별 lift", "", *_signal_lines(report, [g.industry_id for g in report.gates])]
    return lines
```
- `render_markdown(report, today, candidates: BacktestReportDto | None = None)`:
  - 업종별 표 루프의 `name = next(b.industry_name for b in cells.values()) or industry`를 `name = _industry_name(report, industry)`로.
  - 신호별 lift 절의 헤더 2줄과 업종 루프(`lines += ["| 업종 | " ...`부터 루프 안 `lines.append(f"| {name} | " ...)`까지)를 `lines += _signal_lines(report, [None, *industries])`로.
  - "읽는 법"의 부동산 줄(`"- 부동산은 원천(부동산중개업 인허가)에 폐업일이 ..."`)을 교체:
    `"- 편의점·부동산은 업종 특화 원천(담배소매인 이력·상권분석 집계)으로 판정한다. † 표시 업종은 집계 기반이라 개업 대신 T 분기 점포수, 3년 내 폐업 대신 이후 12분기 폐업 수를 세며 전체 합산에 넣지 않는다. 헬스장은 원천 확인 결과 정상(연 3% 폐업이 실제)이라 그대로 둔다.",`
  - `return` 직전에 `lines += _candidate_lines(candidates) if candidates is not None else []`.
- `main()`:
```python
    parser.add_argument(
        "--candidates", type=lambda s: [x for x in s.split(",") if x], default=None,
        help="판정 제외 업종을 따로 심사 (예: convenience_store,real_estate) — 업종 특화 신호 설계서 §8",
    )
```
그리고 `report = get_region_industry_verdict_use_case().backtest(args.as_of)`와 `text = render_markdown(report, today)` 두 줄을:
```python
    use_case = get_region_industry_verdict_use_case()
    report = use_case.backtest(args.as_of)
    candidates = use_case.backtest(args.as_of, industry_ids=args.candidates) if args.candidates else None
    text = render_markdown(report, today, candidates)
```

- [ ] **Step 6: 통과 확인 + 전체 회귀**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_backtest.py tests/test_verdict_backtest_cli.py -q && .venv/bin/python -m pytest tests -q`
Expected: PASS, 전체 스위트 실패 0.

- [ ] **Step 7: 버전 로그 + 커밋**

v0.46.0 `### Added`:
```markdown
- **재포함 게이트** (설계서 §8) — `reinclusion_gate`(경고 lift = (🔴+🟠) 폐업률 ÷ ⚪ ≥ 1.10×, 표본: 대리 원천 개업 각 50·집계 원천 동 각 30), `BacktestReportDto.gates`. CLI `backtest_verdicts --candidates convenience_store,real_estate` → "재포함 심사" 절(원천·판정별 폐업률·경고 lift·게이트)과 심사 업종 신호별 lift. 업종표의 집계 기반 업종 † 표기, 신호 칸에 폐업률·담배권 빈자리.
```
```bash
git add backend/apps/verdict backend/tests/test_verdict_backtest.py backend/tests/test_verdict_backtest_cli.py backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 재포함 게이트·백테스트 CLI 심사 절

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## 2단계 — 실거래가 참고 신호 (조건부: Task 2 = PASS)

> **Task 10·11 시작 조건: Task 2 파일럿 PASS** (아파트 매매 HTTP 200 + `resultCode ∈ {"00","000"}` + `totalCount > 0`). FAIL이면 두 태스크를 건너뛰고 Task 12로 간다 — Task 2가 이미 HANDOFF에 "외부 대기"를 적었다. 이 경우 `trade_per_office` 키는 어디에도 추가하지 않는다(프론트 Task 14도 마찬가지).

### Task 10: 아파트 매매 건수 수집 — `housing` BC · `apt_trade_count` 보조 테이블 (G1)

설계서 §11-3. tobacco·rent와 같은 "수집 전용 보조 테이블" — 엔티티·ORM·게이트웨이·CLI만, 라우터 없음. 범위는 아파트 매매 **건수**만, 자치구×법정동×월, 2021-01부터.

**Files:**
- Create: `backend/apps/housing/__init__.py`, `backend/apps/housing/domain/__init__.py`, `backend/apps/housing/domain/entities/__init__.py`, `backend/apps/housing/adapter/__init__.py`, `backend/apps/housing/adapter/inbound/__init__.py`, `backend/apps/housing/adapter/inbound/cli/__init__.py`, `backend/apps/housing/adapter/outbound/__init__.py`, `backend/apps/housing/adapter/outbound/orms/__init__.py`, `backend/apps/housing/adapter/outbound/gateways/__init__.py` (전부 빈 파일)
- Create: `backend/apps/housing/domain/entities/apt_trade_count_entity.py`
- Create: `backend/apps/housing/adapter/outbound/orms/apt_trade_count_orm.py`
- Create: `backend/apps/housing/adapter/outbound/gateways/molit_apt_trade_gateway.py`
- Create: `backend/apps/housing/adapter/inbound/cli/load_apt_trade_counts.py`
- Create: `backend/migrations/versions/e1f2a3b4c5d6_apt_trade_count.py`
- Modify: `backend/migrations/env.py` (ORM import 한 줄 — `tobacco_retailer_orm` import 아래)
- Modify: `docs/erd.md` (보조 테이블 목록·mermaid에 `district ||--o{ apt_trade_count`)
- Test: `backend/tests/test_housing_apt_trade.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Produces:
  - `AptTradeCount(district_code: str, legal_dong: str, deal_ym: str, trade_count: int)`(frozen) — `deal_ym`은 `"YYYYMM"`
  - 테이블 `apt_trade_count`: PK(`district_code` FK district, `legal_dong` String(40), `deal_ym` String(6)), `trade_count` int, `collected_at` DateTime(tz)
  - `count_by_legal_dong(xml_text: str) -> tuple[Counter[str], int]` (응답 XML → 법정동별 건수, totalCount). 정상 코드가 아니면 `MolitApiError`
  - `month_range(start: str, end: str) -> list[str]` (`"202111"`, `"202202"` → `["202111","202112","202201","202202"]`)
  - CLI `python -m apps.housing.adapter.inbound.cli.load_apt_trade_counts --from 202101 [--to YYYYMM] [--refresh]`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `backend/tests/test_housing_apt_trade.py`:
```python
"""아파트 매매 건수 수집 — 응답 파싱·월 범위·멱등 업서트 (업종 특화 신호 설계서 §11)."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from apps.housing.adapter.inbound.cli.load_apt_trade_counts import month_range, upsert_counts
from apps.housing.adapter.outbound.gateways.molit_apt_trade_gateway import MolitApiError, count_by_legal_dong
from apps.housing.adapter.outbound.orms.apt_trade_count_orm import AptTradeCountOrm
from apps.housing.domain.entities.apt_trade_count_entity import AptTradeCount
from core.matrix.grid_oracle_database_manager import session_scope

_OK = """<?xml version="1.0" encoding="UTF-8"?><response><header><resultCode>000</resultCode><resultMsg>OK</resultMsg></header>
<body><items><item><umdNm>역삼동</umdNm></item><item><umdNm> 역삼동 </umdNm></item><item><umdNm>대치동</umdNm></item></items>
<numOfRows>1000</numOfRows><pageNo>1</pageNo><totalCount>3</totalCount></body></response>"""

_BAD = """<OpenAPI_ServiceResponse><cmmMsgHeader><errMsg>SERVICE ERROR</errMsg>
<returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg><returnReasonCode>30</returnReasonCode></cmmMsgHeader></OpenAPI_ServiceResponse>"""


def test_응답을_법정동별_건수로_센다():
    counts, total = count_by_legal_dong(_OK)
    assert counts == {"역삼동": 2, "대치동": 1} and total == 3


def test_정상_코드가_아니면_예외다():
    with pytest.raises(MolitApiError):
        count_by_legal_dong(_BAD)


def test_월_범위는_양끝을_포함한다():
    assert month_range("202111", "202202") == ["202111", "202112", "202201", "202202"]


def test_업서트는_멱등이다():
    rows = [AptTradeCount("11680", "시험동", "209901", 5), AptTradeCount("11680", "시험동2", "209901", 1)]
    try:
        assert upsert_counts(rows, datetime(2099, 1, 1, tzinfo=timezone.utc)) == 2
        assert upsert_counts([AptTradeCount("11680", "시험동", "209901", 7)], datetime(2099, 1, 2, tzinfo=timezone.utc)) == 1
        with session_scope() as session:
            got = dict(session.execute(
                select(AptTradeCountOrm.legal_dong, AptTradeCountOrm.trade_count).where(AptTradeCountOrm.deal_ym == "209901")
            ).all())
        assert got == {"시험동": 7, "시험동2": 1}
    finally:
        with session_scope() as session:
            session.execute(delete(AptTradeCountOrm).where(AptTradeCountOrm.deal_ym == "209901"))
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_housing_apt_trade.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.housing'`

- [ ] **Step 3: 엔티티·ORM·마이그레이션**

`apt_trade_count_entity.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AptTradeCount:
    """아파트 매매 신고 건수 — 자치구×법정동×월 (국토부 RTMSDataSvcAptTrade, 업종 특화 신호 설계서 §11).
    법정동은 원천 umdNm 원문. 행정동 배분은 verdict BC가 한다(store 지번주소 분포, 근사)."""

    district_code: str  # 시군구 5자리 = LAWD_CD
    legal_dong: str  # 법정동명 (umdNm)
    deal_ym: str  # "YYYYMM"
    trade_count: int
```
`apt_trade_count_orm.py`:
```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장 (tobacco 전례)
import apps.master.adapter.outbound.orms.district_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class AptTradeCountOrm(OrmBase):
    """아파트 매매 건수 — 수집 전용 보조 테이블 (erd.md 보조 테이블, 업종 특화 신호 설계서 §11).
    §13 연결 원칙: district FK로 마스터 허브에 연결. 법정동은 원천 문자열이라 FK 없음(행정동 배분은 verdict BC)."""

    __tablename__ = "apt_trade_count"

    district_code: Mapped[str] = mapped_column(ForeignKey("district.district_code"), primary_key=True)
    legal_dong: Mapped[str] = mapped_column(String(40), primary_key=True)
    deal_ym: Mapped[str] = mapped_column(String(6), primary_key=True)
    trade_count: Mapped[int]
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```
`migrations/versions/e1f2a3b4c5d6_apt_trade_count.py`:
```python
"""아파트 매매 건수 보조 테이블 apt_trade_count

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-29 18:00:00.000000

업종 특화 신호 설계서 §11-3. 자치구×법정동×월 건수만.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "apt_trade_count",
        sa.Column("district_code", sa.String(), sa.ForeignKey("district.district_code"), primary_key=True),
        sa.Column("legal_dong", sa.String(length=40), primary_key=True),
        sa.Column("deal_ym", sa.String(length=6), primary_key=True),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("apt_trade_count")
```
`migrations/env.py`에 `import apps.housing.adapter.outbound.orms.apt_trade_count_orm  # noqa: F401`.

- [ ] **Step 4: 게이트웨이**

`molit_apt_trade_gateway.py`:
```python
"""국토부 아파트 매매 실거래가 Driven Adapter — apis.data.go.kr/1613000/RTMSDataSvcAptTrade (파일럿 9/29, 설계서 §11).
LAWD_CD(시군구 5자리) × DEAL_YMD(월) 반복 호출, numOfRows 1000 페이지. 최근 1~2개월은 신고기한(30일) 탓에 미완결."""

import time
import xml.etree.ElementTree as ET
from collections import Counter

import httpx

from core.matrix.grid_keymaker_secret_manager import get_settings

_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
_PAGE_SIZE = 1000
_OK_CODES = frozenset({"00", "000"})


class MolitApiError(RuntimeError):
    """정상 코드가 아닌 응답 — 활용신청 미승인(SERVICE_KEY_IS_NOT_REGISTERED_ERROR)·트래픽 초과 등."""


def count_by_legal_dong(xml_text: str) -> tuple[Counter[str], int]:
    root = ET.fromstring(xml_text)
    code = (root.findtext("header/resultCode") or "").strip()
    if code not in _OK_CODES:
        reason = root.findtext(".//returnAuthMsg") or root.findtext("header/resultMsg") or "응답 코드 없음"
        raise MolitApiError(f"{code or '-'}: {reason.strip()}")
    counts = Counter((item.findtext("umdNm") or "").strip() for item in root.iter("item"))
    counts.pop("", None)
    return counts, int(root.findtext("body/totalCount") or 0)


class MolitAptTradeGateway:
    def month_counts(self, district_code: str, deal_ym: str) -> Counter[str]:
        """한 구·한 달의 법정동별 매매 건수 (페이지 전부)."""
        counts: Counter[str] = Counter()
        page = 1
        with httpx.Client(timeout=30) as client:
            while True:
                response = client.get(_URL, params={
                    "serviceKey": get_settings().data_go_kr_api_key, "LAWD_CD": district_code,
                    "DEAL_YMD": deal_ym, "pageNo": page, "numOfRows": _PAGE_SIZE,
                })
                response.raise_for_status()
                page_counts, total = count_by_legal_dong(response.text)
                counts.update(page_counts)
                if page * _PAGE_SIZE >= total:
                    return counts
                page += 1
                time.sleep(0.2)
```

- [ ] **Step 5: CLI**

`load_apt_trade_counts.py`:
```python
"""아파트 매매 건수 적재 러너 (Driving Adapter, CLI) — 업종 특화 신호 설계서 §11.

- 25개 구 × 월(--from ~ --to, 기본 --to = 지난달). 이미 적재된 (구, 월)은 건너뛴다(--refresh로 다시).
- 멱등: PK (district_code, legal_dong, deal_ym) INSERT … ON CONFLICT DO UPDATE.
- 일일 호출 한도에 걸리면 MolitApiError로 멈춘다 — 다음 날 같은 명령을 다시 실행하면 이어서 받는다.

실행: python -m apps.housing.adapter.inbound.cli.load_apt_trade_counts --from 202101
"""

import argparse
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from apps.housing.adapter.outbound.gateways.molit_apt_trade_gateway import MolitAptTradeGateway
from apps.housing.adapter.outbound.orms.apt_trade_count_orm import AptTradeCountOrm
from apps.housing.domain.entities.apt_trade_count_entity import AptTradeCount
from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from core.matrix.grid_oracle_database_manager import session_scope


def month_range(start: str, end: str) -> list[str]:
    first = int(start[:4]) * 12 + int(start[4:]) - 1
    last = int(end[:4]) * 12 + int(end[4:]) - 1
    return [f"{m // 12}{m % 12 + 1:02d}" for m in range(first, last + 1)]


def upsert_counts(rows: list[AptTradeCount], collected_at: datetime) -> int:
    if not rows:
        return 0
    statement = insert(AptTradeCountOrm).values([
        {"district_code": r.district_code, "legal_dong": r.legal_dong, "deal_ym": r.deal_ym,
         "trade_count": r.trade_count, "collected_at": collected_at}
        for r in rows
    ])
    with session_scope() as session:
        session.execute(statement.on_conflict_do_update(
            index_elements=["district_code", "legal_dong", "deal_ym"],
            set_={"trade_count": statement.excluded.trade_count, "collected_at": statement.excluded.collected_at},
        ))
    return len(rows)


def _last_month(today: date) -> str:
    return f"{today.year - 1}12" if today.month == 1 else f"{today.year}{today.month - 1:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="아파트 매매 건수 적재 (설계서 §11)")
    parser.add_argument("--from", dest="start", default="202101")
    parser.add_argument("--to", dest="end", default=_last_month(date.today()))
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    gateway = MolitAptTradeGateway()
    with session_scope() as session:
        districts = session.execute(select(DistrictOrm.district_code).order_by(DistrictOrm.district_code)).scalars().all()
        done = set(session.execute(select(AptTradeCountOrm.district_code, AptTradeCountOrm.deal_ym).distinct()).all())
    total = 0
    for deal_ym in month_range(args.start, args.end):
        for district in districts:
            if not args.refresh and (district, deal_ym) in done:
                continue
            counts = gateway.month_counts(district, deal_ym)
            total += upsert_counts(
                [AptTradeCount(district, dong, deal_ym, n) for dong, n in counts.items()], datetime.now(timezone.utc)
            )
        print(f"{deal_ym} 적재 누적 {total}행")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_housing_apt_trade.py -q && .venv/bin/python -m pytest tests -q`
Expected: PASS (conftest가 테스트 DB를 `e1f2a3b4c5d6`까지 올린다).

- [ ] **Step 7: 개발 DB 마이그레이션 + 적재**

Run: `cd backend && .venv/bin/alembic upgrade head && .venv/bin/python -m apps.housing.adapter.inbound.cli.load_apt_trade_counts --from 202101`
Expected: `e1f2a3b4c5d6 (head)`, 월별 누적 행수 출력. 25구 × 약 68개월 ≈ 1,700회 호출. 한도에 걸려 `MolitApiError`로 멈추면 적재된 범위를 기록하고 다음 날 같은 명령으로 이어 받는다 — **백테스트(T=2022-06-30)에 필요한 2021-05~2022-04와 배치에 필요한 최근 12개월이 먼저 필요하다**: 한도가 빠듯하면 `--from 202105 --to 202204`를 먼저, 이어서 `--from <오늘-14개월>`을 돈다. 확인: `select min(deal_ym), max(deal_ym), sum(trade_count) from apt_trade_count`.

- [ ] **Step 8: erd.md · 버전 로그 · 커밋**

`docs/erd.md` 보조 테이블 절(tobacco_retailer 설명 근처)에:
```markdown
- `apt_trade_count` — **보조 테이블 추가** (2026-09-29, 업종 특화 신호 §11). 국토부 아파트 매매 건수, 자치구×법정동×월. district FK로 허브 연결, 법정동은 원천 문자열(행정동 배분은 verdict BC 근사). 수집 전용(라우터 없음).
```
두 mermaid 블록의 tobacco_retailer 관계 줄 아래에 `    district ||--o{ apt_trade_count : "아파트 매매 건수(보조 테이블)"`.
v0.46.0 `### Added`:
```markdown
- **아파트 매매 건수 수집** (설계서 §11, 파일럿 통과) — 신규 `housing` BC(엔티티·ORM·게이트웨이·CLI, 라우터 없음), 보조 테이블 `apt_trade_count`(자치구×법정동×월, 마이그레이션 `e1f2a3b4c5d6`), `load_apt_trade_counts --from 202101`(적재된 구·월 건너뜀, 멱등 업서트).
```
```bash
git add backend/apps/housing backend/migrations backend/tests/test_housing_apt_trade.py docs/erd.md backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 아파트 매매 건수 수집 — housing BC·apt_trade_count

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: 중개사무소당 거래 참고 신호 `trade_per_office` (G2)

설계서 §11-3. 법정동 건수를 store 지번주소 분포로 행정동에 배분하고, 부동산 집계 원천에 Decorator로 얹는다. **참고 신호**(등급 계산 제외).

**Files:**
- Create: `backend/apps/verdict/domain/services/legal_dong.py`
- Modify: `backend/apps/verdict/domain/services/signals.py` (`TradePerOfficeSignal`, `SignalInput.trade_12m`)
- Modify: `backend/apps/verdict/domain/services/profiles.py` (`AggregateProfile` 끝에 추가)
- Modify: `backend/apps/verdict/domain/entities/region_industry_verdict_entity.py` (키 2곳)
- Modify: `backend/apps/verdict/app/dtos/region_industry_verdict_dto.py` (`StoreSignalStat.trade_12m`)
- Modify: `backend/apps/verdict/app/ports/output/region_industry_verdict_port.py` (`TradeCountsPort`)
- Modify: `backend/apps/verdict/app/use_cases/industry_source.py` (`TradeEnrichedSignalData`)
- Modify: `backend/apps/verdict/app/use_cases/region_industry_verdict_interactor.py` (`_EMPTY_STAT`에 `trade_12m=None`)
- Create: `backend/apps/verdict/adapter/outbound/gateways/apt_trade_gateway.py`
- Modify: `backend/apps/verdict/dependencies/region_industry_verdict_dependencies.py`
- Modify: `backend/apps/verdict/adapter/inbound/cli/backtest_verdicts.py` (`_SIGNAL_LABEL["trade_per_office"] = "사무소당 거래"`)
- Test: Create `backend/tests/test_verdict_trade_signal.py`; Modify `backend/tests/test_verdict_profiles.py`
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 10 `apt_trade_count`, Task 8 `CommerceAggregateSignalData`, Task 5 `AggregateProfile`
- Produces:
  - `legal_dong_of(jibun_address: str | None) -> str | None` (`"서울특별시 강남구 역삼동 123-4"` → `"역삼동"`, `"서울특별시 중구 을지로3가 5"` → `"을지로3가"`)
  - `allocate(trades: Mapping[tuple[str, str], int], weights: Mapping[tuple[str, str], Mapping[str, int]]) -> dict[str, float]` — (구, 법정동) 건수를 그 법정동 상가의 행정동 분포 비율로 나눠 행정동별 합
  - `month_window(today: date, months: int = 12, lag: int = 2) -> tuple[str, str]` — `(date(2026,9,29))` → `("202508", "202607")`
  - `TradeCountsPort.trades_by_region(month_from: str, month_to: str) -> dict[str, float]`
  - `TradeEnrichedSignalData(inner: IndustrySignalDataPort, trades: TradeCountsPort)` — Decorator: `signal_stats(today)`가 inner 결과에 `trade_12m`(행정동 배분 12개월 합)을 채운다. 나머지 두 메서드는 위임.
  - `TradePerOfficeSignal`(key `trade_per_office`, source `molit`): 값 = `trade_12m ÷ latest_store_count`, 낮을수록 나쁨(`worse = -value`), `latest_store_count < min_sample` 또는 `trade_12m is None`이면 unavailable.
  - `SPECIFIC_SIGNAL_KEYS += ("trade_per_office",)`, `ADVISORY_SIGNAL_KEYS += {"trade_per_office"}`, `AggregateProfile.signals()` 끝에 `TradePerOfficeSignal()`.

- [ ] **Step 1: 실패하는 테스트 작성**

Create `backend/tests/test_verdict_trade_signal.py`:
```python
"""중개사무소당 거래 참고 신호 — 법정동 배분·월 창·Decorator·신호 값 (업종 특화 신호 설계서 §11)."""

from datetime import date

import pytest

from apps.verdict.app.dtos.region_industry_verdict_dto import StoreSignalStat
from apps.verdict.app.ports.output.region_industry_verdict_port import IndustrySignalDataPort, TradeCountsPort
from apps.verdict.app.use_cases.industry_source import TradeEnrichedSignalData
from apps.verdict.domain.entities.region_industry_verdict_entity import ADVISORY_SIGNAL_KEYS, LEVEL_UNAVAILABLE
from apps.verdict.domain.services.legal_dong import allocate, legal_dong_of, month_window
from apps.verdict.domain.services.signals import SignalInput, TradePerOfficeSignal
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS as T


@pytest.mark.parametrize("address, dong", [
    ("서울특별시 강남구 역삼동 123-4", "역삼동"),
    ("서울특별시 중구 을지로3가 5", "을지로3가"),
    ("서울시 종로구 종로1가 1", "종로1가"),
    ("경기도 성남시 분당구 정자동 1", None),
    (None, None),
])
def test_지번주소에서_법정동을_읽는다(address, dong):
    assert legal_dong_of(address) == dong


def test_법정동_건수를_상가_분포_비율로_행정동에_나눈다():
    trades = {("11680", "역삼동"): 100, ("11680", "없는동"): 7}
    weights = {("11680", "역삼동"): {"1168064000": 3, "1168065000": 1}}
    assert allocate(trades, weights) == {"1168064000": 75.0, "1168065000": 25.0}  # 배분 못 한 7건은 버린다


def test_월_창은_기준월_2개월_전까지_12개월이다():
    assert month_window(date(2026, 9, 29)) == ("202508", "202607")
    assert month_window(date(2022, 6, 30)) == ("202105", "202204")


class _Inner(IndustrySignalDataPort):
    def signal_stats(self, today):
        return [StoreSignalStat("r1", "real_estate", 100, 0, 5, 0, 0, 0, None)]

    def store_counts(self, year_max, quarter_max):
        return ["counts"]

    def entrant_outcomes(self, as_of, entry_days, horizon_days):
        return ["outcomes"]


class _Trades(TradeCountsPort):
    def __init__(self):
        self.args = None

    def trades_by_region(self, month_from, month_to):
        self.args = (month_from, month_to)
        return {"r1": 240.0}


def test_거래_Decorator는_집계_원천에_12개월_거래를_얹고_나머지는_위임한다():
    trades = _Trades()
    data = TradeEnrichedSignalData(_Inner(), trades)
    (stat,) = data.signal_stats(date(2022, 6, 30))
    assert stat.trade_12m == 240.0 and trades.args == ("202105", "202204")
    assert data.store_counts(None, None) == ["counts"]
    assert data.entrant_outcomes(date(2022, 6, 30), 365, 1095) == ["outcomes"]


def _input(**overrides) -> SignalInput:
    base = dict(
        region_code="r1", industry_id="real_estate", industry_name="부동산중개업",
        start_store_count=100, opened_12m=0, closed_12m=5, cohort_size=0, cohort_survived=0,
        closed_3y_count=0, closed_3y_median_months=None, latest_store_count=80, resident_total=10_000,
        change_code="HH", change_name="정체", change_quarter="20262", closed_months=25.0, seoul_closed_months=27.0,
        trade_12m=240.0,
    )
    base.update(overrides)
    return SignalInput(**base)


def test_사무소당_거래는_낮을수록_나쁘고_참고_신호다():
    signal = TradePerOfficeSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(3.0)
    assert signal.worse(3.0) == -3.0
    assert signal.evaluate(_input(trade_12m=None), T, [1.0]).level == LEVEL_UNAVAILABLE
    assert signal.evaluate(_input(latest_store_count=9), T, [1.0]).level == LEVEL_UNAVAILABLE
    assert "사무소당 3.0건" in signal.evaluate(_input(), T, [-5.0, -1.0]).evidence
    assert "trade_per_office" in ADVISORY_SIGNAL_KEYS
```
`backend/tests/test_verdict_profiles.py`의 `test_부동산_프로필은_…`에서 기대 키 튜플 끝에 `"trade_per_office"`를 더하고, `test_신호_키_상수와_빈자리_가드`의 기대값을 `SIGNAL_KEYS + ("closure_rate", "tobacco_gap", "trade_per_office")`로 바꾼다.

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_trade_signal.py tests/test_verdict_profiles.py -q`
Expected: FAIL — `ModuleNotFoundError: ...legal_dong` 및 프로필 키 불일치

- [ ] **Step 3: 도메인 — `legal_dong.py`**

```python
"""법정동 → 행정동 배분 (업종 특화 신호 설계서 §11-3). 순수 파이썬 — 근사: 같은 법정동 상가의 행정동 분포 비율로 나눈다."""

import re
from collections.abc import Mapping
from datetime import date

_LEGAL_DONG = re.compile(r"^서울(?:특별)?시\s+\S+구\s+(\S+?(?:동|가))(?:\s|$)")


def legal_dong_of(jibun_address: str | None) -> str | None:
    match = _LEGAL_DONG.match(jibun_address.strip()) if jibun_address else None
    return match.group(1) if match else None


def allocate(
    trades: Mapping[tuple[str, str], int], weights: Mapping[tuple[str, str], Mapping[str, int]]
) -> dict[str, float]:
    """(구, 법정동) 건수를 그 법정동 상가의 행정동 분포 비율로 나눈다. 분포가 없는 법정동은 버린다."""
    result: dict[str, float] = {}
    for key, count in trades.items():
        shares = weights.get(key, {})
        total = sum(shares.values())
        for region, weight in shares.items():
            result[region] = result.get(region, 0.0) + count * weight / total
    return result


def month_window(today: date, months: int = 12, lag: int = 2) -> tuple[str, str]:
    """기준월 lag개월 전까지 months개월 — 신고기한(30일) 탓에 최근 월은 미완결 (api.md 국토부 실거래가)."""
    last = today.year * 12 + today.month - 1 - lag
    first = last - months + 1
    return f"{first // 12}{first % 12 + 1:02d}", f"{last // 12}{last % 12 + 1:02d}"
```

- [ ] **Step 4: 신호·키·프로필·DTO**

`signals.py` — `SignalInput`의 `gap_blocked` 아래 `trade_12m: float | None = None  # 행정동 배분 아파트 매매 12개월 합 (부동산 원천)`, 클래스 추가(`SIGNALS` 앞):
```python
class TradePerOfficeSignal(Signal):
    """중개사무소당 아파트 매매 — 낮을수록 나쁨. 법정동 배분이 근사라 참고 신호 (업종 특화 신호 설계서 §11)."""

    key = "trade_per_office"
    source = "molit"

    def raw_value(self, i, t):
        if i.trade_12m is None or i.latest_store_count is None or i.latest_store_count < t.min_sample:
            return None
        return i.trade_12m / i.latest_store_count

    def worse(self, value):
        return -value

    def evidence(self, i, value, percentile):
        return (
            f"지난 12개월 아파트 매매 {i.trade_12m:,.0f}건 ÷ 중개사무소 {i.latest_store_count}곳 = 사무소당 {value:.1f}건 "
            f"(서울 {i.industry_name} 하위 {_top(percentile)}%, 국토부 실거래가)"
        )

    def unavailable_reason(self, i, t):
        return "실거래 배분 없음 또는 중개사무소 10곳 미만"
```
entity: `SPECIFIC_SIGNAL_KEYS = ("closure_rate", "tobacco_gap", "trade_per_office")`, `ADVISORY_SIGNAL_KEYS = frozenset({"shrinking", "tobacco_gap", "trade_per_office"})`.
profiles: import `TradePerOfficeSignal`, `AggregateProfile.signals()` 튜플 끝에 `TradePerOfficeSignal(),`.
DTO `StoreSignalStat`의 `gap_blocked` 아래 `trade_12m: float | None = None`. 인터랙터 `_EMPTY_STAT`에 `trade_12m=None,`.

- [ ] **Step 5: 포트·Decorator·게이트웨이·의존성**

포트 파일 끝:
```python
class TradeCountsPort(ABC):
    @abstractmethod
    def trades_by_region(self, month_from: str, month_to: str) -> dict[str, float]:
        """[month_from, month_to] 아파트 매매 건수를 행정동으로 배분한 합 (업종 특화 신호 설계서 §11)."""
```
`industry_source.py`에 (import `replace`, `TradeCountsPort`, `month_window`):
```python
class TradeEnrichedSignalData(IndustrySignalDataPort):
    """Decorator — 원천 집계에 행정동 배분 아파트 매매 12개월 합(trade_12m)을 얹는다. 나머지는 위임 (설계서 §11)."""

    def __init__(self, inner: IndustrySignalDataPort, trades: TradeCountsPort) -> None:
        self._inner = inner
        self._trades = trades

    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        by_region = self._trades.trades_by_region(*month_window(today))
        return [replace(s, trade_12m=by_region.get(s.region_code)) for s in self._inner.signal_stats(today)]

    def store_counts(self, year_max: int | None, quarter_max: str | None) -> list[LatestStoreCount]:
        return self._inner.store_counts(year_max, quarter_max)

    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        return self._inner.entrant_outcomes(as_of, entry_days, horizon_days)
```
Create `adapter/outbound/gateways/apt_trade_gateway.py`:
```python
"""Driven Adapter — 아파트 매매 건수(housing BC)를 행정동으로 배분 (업종 특화 신호 설계서 §11).
가중치 = store 전 업종 점포의 (구, 법정동) → 행정동 분포. cross-BC 접근은 이 파일 안에서만."""

from collections import defaultdict
from functools import cached_property

from sqlalchemy import func, select

from apps.housing.adapter.outbound.orms.apt_trade_count_orm import AptTradeCountOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.verdict.app.ports.output.region_industry_verdict_port import TradeCountsPort
from apps.verdict.domain.services.legal_dong import allocate, legal_dong_of
from core.matrix.grid_oracle_database_manager import session_scope


class AptTradeGateway(TradeCountsPort):
    @cached_property
    def _weights(self) -> dict[tuple[str, str], dict[str, int]]:
        with session_scope() as session:
            rows = session.execute(
                select(StoreOrm.district_code, StoreOrm.jibun_address, StoreOrm.region_code)
                .where(StoreOrm.region_code.is_not(None), StoreOrm.jibun_address.is_not(None))
            ).all()
        weights: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for district, address, region in rows:
            dong = legal_dong_of(address)
            if dong is not None:
                weights[(district, dong)][region] += 1
        return weights

    def trades_by_region(self, month_from: str, month_to: str) -> dict[str, float]:
        A = AptTradeCountOrm
        with session_scope() as session:
            rows = session.execute(
                select(A.district_code, A.legal_dong, func.sum(A.trade_count))
                .where(A.deal_ym >= month_from, A.deal_ym <= month_to)
                .group_by(A.district_code, A.legal_dong)
            ).all()
        return allocate({(d, dong): int(n) for d, dong, n in rows}, self._weights)
```
의존성의 `real_estate` 등록을:
```python
            "real_estate": IndustrySource(
                AggregateProfile(), TradeEnrichedSignalData(CommerceAggregateSignalData(("real_estate",)), AptTradeGateway())
            ),
```
(import `TradeEnrichedSignalData`, `AptTradeGateway`). CLI `_SIGNAL_LABEL`에 `"trade_per_office": "사무소당 거래"`.

- [ ] **Step 6: 통과 확인 + 회귀 + 배분 적중률 스모크**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_trade_signal.py tests/test_verdict_profiles.py -q && .venv/bin/python -m pytest tests -q`
Expected: PASS
스모크(읽기만): `AptTradeGateway().trades_by_region(*month_window(date.today()))`의 합 ÷ 같은 창 `apt_trade_count` 합 = 배분 적중률. **90% 미만이면** `legal_dong_of` 정규식이 놓치는 법정동 이름(예: 로·길 끝)을 `select legal_dong ... except` 식으로 뽑아 보고하고 멈춘다.

- [ ] **Step 7: 버전 로그 + 커밋**

v0.46.0 `### Added`:
```markdown
- **중개사무소당 거래 참고 신호** (설계서 §11) — `TradePerOfficeSignal`(`trade_per_office`, source `molit`, 낮을수록 나쁨, 참고 신호), `legal_dong_of`·`allocate`(store 지번주소 분포로 법정동 → 행정동 배분)·`month_window`(기준월 2개월 전까지 12개월), `TradeCountsPort`·`AptTradeGateway`, 집계 원천 Decorator `TradeEnrichedSignalData`. `AggregateProfile` 끝에 추가.
```
```bash
git add backend/apps/verdict backend/tests/test_verdict_trade_signal.py backend/tests/test_verdict_profiles.py backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 중개사무소당 아파트 매매 참고 신호

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## 3단계 — 실DB 판정 · 게이트 · 분석

### Task 12: 실DB 백테스트 · 재포함 게이트 판정 · 제외 목록 반영

설계서 §8·§15·§17. 게이트 결과에 따라 **분기가 있는 유일한 태스크**다 — 통과한 업종만 `EXCLUDED_INDUSTRIES`에서 뺀다.

**Files:**
- Modify(생성물): `docs/verdict-backtest.md`
- Modify(조건부): `backend/apps/verdict/domain/entities/region_industry_verdict_entity.py` (`EXCLUDED_INDUSTRIES` + 주석), `backend/tests/test_verdict_thresholds.py`, `backend/tests/test_verdict_gateways.py`, `backend/apps/verdict/adapter/inbound/cli/build_verdicts.py`(출력 문구), `backend/apps/verdict/app/ports/input/region_industry_verdict_use_case.py`(독스트링), `scripts/store-collector.sh`(echo 문구)
- Modify: 설계서 §17, `docs/HANDOFF.md` §0-12 A
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Consumes: Task 9 CLI `--candidates`, Task 7·8 원천
- Produces: **게이트 결과 기록**(편의점·부동산 각각 통과/미달, 경고 lift, 표본) — Task 14·15(프론트 `VERDICT_EXCLUDED_INDUSTRIES`·안내 문구)와 Task 16이 이 기록을 읽는다. 기록 위치: 설계서 §17 표와 HANDOFF §0-12 A.

- [ ] **Step 1: 심사 백테스트 실행 (DB 읽기만)**

Run: `cd backend && .venv/bin/python -m apps.verdict.adapter.inbound.cli.backtest_verdicts --as-of 2022-06-30 --candidates convenience_store,real_estate --out ../docs/verdict-backtest.md`
Expected: `저장: ../docs/verdict-backtest.md`와 표 출력. "재포함 심사" 절에 편의점·부동산중개업 두 줄, 게이트 칸이 `통과` 또는 `미달 — …`. 기존 12업종 표는 9/29 값(전체 lift 1.70×, `docs/verdict-backtest.md` 커밋본)과 거의 같아야 한다(그 뒤 수집된 store 행 탓에 ±0.03× 안쪽). 크게 다르면 Task 6 회귀를 의심하고 멈춘다.

- [ ] **Step 2: 원천 검증 두 가지를 재서 기록한다 (DB 읽기만)**

(a) 브랜드 사전 검증 — 동별 에피소드 폐업 수(2021~2025) vs 상권분석 CS300002 폐업 수의 순위 상관. 스크래치에서 실행(커밋 금지):
```python
from sqlalchemy import func, select
from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm as S
from apps.verdict.adapter.outbound.gateways.tobacco_convenience_gateway import TobaccoConvenienceSignalData
from core.matrix.grid_oracle_database_manager import session_scope

def rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i]); r = [0] * len(xs)
    for k, i in enumerate(order): r[i] = k
    return r

def spearman(a, b):
    ra, rb = rank(a), rank(b); n = len(a); ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return cov / (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5

tob = {}
for e in TobaccoConvenienceSignalData()._episodes:
    if e.close_date and 2021 <= e.close_date.year <= 2025:
        tob[e.region_code] = tob.get(e.region_code, 0) + 1
with session_scope() as s:
    arch = dict(s.execute(select(S.region_code, func.sum(S.close_store_count))
                .where(S.service_industry_code == "CS300002", S.region_code.is_not(None)).group_by(S.region_code)).all())
keys = sorted(set(tob) & set(arch))
print("동", len(keys), "rho", round(spearman([tob[k] for k in keys], [int(arch[k]) for k in keys]), 3))
```
(b) 부동산 "폐업0동" 비율 — Task 8 Step 7 출력값(최신 4분기 폐업 합이 0인 동 ÷ 422).
기록 기준: (a) ρ < 0.6이면 설계서 §15대로 "브랜드 사전 재검토 후속"을 HANDOFF에 적는다. (b) 30% 초과면 "부동산 아카이브 원천 점검 후속"을 적는다. 둘 다 이 태스크의 게이트 판정은 바꾸지 않는다.

- [ ] **Step 3: 게이트 결과에 따라 제외 목록을 고친다**

각 업종에 대해 Step 1 "게이트" 칸을 본다.

- **통과한 업종**: `EXCLUDED_INDUSTRIES`에서 뺀다. 예) 둘 다 통과:
```python
EXCLUDED_INDUSTRIES: frozenset[str] = frozenset({"academy", "childcare", "restaurant_other", "chicken"})
```
  편의점만 통과면 `{"academy", "childcare", "restaurant_other", "chicken", "real_estate"}`, 부동산만 통과면 `{..., "convenience_store"}`. 상수 위 주석에서 뺀 업종 설명을 "편의점 — 담배소매인 이력(proxy)으로 재포함(9/29 게이트 통과, 경고 lift N.NN×)" / "부동산 — 상권분석 집계(aggregate)로 재포함(…)"으로 바꾼다.
  - `tests/test_verdict_thresholds.py::test_신호_키_순서와_제외_업종`의 기대 집합을 같은 집합으로.
  - `tests/test_verdict_gateways.py::test_판정_대상_업종은_제외_6종을_뺀_12종` — 함수 이름의 숫자와 `assert len(ids) == 12`를 새 개수로(18 − 제외 개수: 둘 다 통과 14, 하나 통과 13).
  - `build_verdicts.py` 출력 문구·모듈 독스트링의 "12업종", `region_industry_verdict_use_case.py` 독스트링, `scripts/store-collector.sh`의 `판정 배치 (region_industry_verdict, 12업종 × 427동)`를 새 개수로.
- **미달한 업종**: 코드를 바꾸지 않는다. 상수 주석에 "(9/29 재포함 게이트 미달 — 경고 lift N.NN×, docs/verdict-backtest.md 재포함 심사 절)"만 덧붙인다.

Run: `cd backend && .venv/bin/python -m pytest tests -q`
Expected: PASS

- [ ] **Step 4: 백테스트 재생성 (포함된 업종이 본표에 들어가도록)**

하나라도 통과했으면 Step 1 명령을 **같은 인자로** 다시 실행한다(심사 절은 두 업종을 계속 보여준다). 본표 업종별 행에 편입 업종이 보이고, 부동산은 `부동산중개업 †`로 전체 합산에서 빠졌는지 확인한다.

- [ ] **Step 5: 기록**

설계서 §17 표에 행 추가:
```markdown
| 2026-09-29 | Task 12 재포함 게이트 (T=2022-06-30) | 편의점: <통과/미달> — 경고 lift <x.xx×>, 경고 개업 <n>·⚪ 개업 <n>, 🔴 <rate(opened)>. 부동산: <통과/미달> — 경고 lift <x.xx×>, 경고 동 <n>·⚪ 동 <n>. 신호별 lift: 담배권 빈자리 <x.xx×>, 폐업률 <x.xx×>(+ 사무소당 거래 <x.xx×>). 원천 검증: 편의점 에피소드 폐업 vs CS300002 ρ <0.xx>, 부동산 폐업0동 <n>/422. 결과: EXCLUDED_INDUSTRIES = <집합>. |
```
HANDOFF §0-12 A "업종 특화 신호" 항목 아래에 같은 요약 한 줄과, 미달 업종이 있으면 "프론트 안내 문구: <사유>" 한 줄(Task 15가 그대로 쓴다):
- 편의점 미달 사유 문구: `"담배소매인 이력으로 만든 판정이 백테스트 기준(경고 lift 1.10배)을 넘지 못했습니다"`
- 부동산 미달 사유 문구: `"상권분석 집계로 만든 판정이 백테스트 기준(경고 lift 1.10배)을 넘지 못했습니다"`

- [ ] **Step 6: 버전 로그 + 커밋**

v0.46.0 `### Changed`에 통과 여부에 맞춰:
```markdown
- **판정 대상 재포함 (9/29 게이트)** — <편의점(담배소매인 이력, 경고 lift x.xx×)·부동산(상권분석 집계, x.xx×)>을 `EXCLUDED_INDUSTRIES`에서 뺐다 → 판정 대상 <N>업종. <미달 업종과 lift는 제외 유지>. `docs/verdict-backtest.md` 재생성(재포함 심사 절).
```
```bash
git add docs/verdict-backtest.md docs/HANDOFF.md docs/superpowers/specs/2026-09-29-industry-specific-signals-design.md backend/apps/verdict backend/tests scripts/store-collector.sh backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 재포함 게이트 실측 — 편의점·부동산 판정 대상 결정

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: 부동산 생존자 역산 분석 (F)

설계서 §10. 분석 CLI와 문서 기록만. 신호로 만들지 않는다.

**Files:**
- Create: `backend/apps/verdict/adapter/inbound/cli/real_estate_survivor_backcast.py`
- Test: Create `backend/tests/test_verdict_survivor_backcast.py`
- Modify: 설계서 §17, `docs/HANDOFF.md` §0-12 A
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Produces: `survivor_rows(survivors: Mapping[int, int], archive_opens: Mapping[int, int], years: Sequence[int]) -> list[tuple[int, int, int, float | None]]` (연도, 생존 사무소, 아카이브 개업, 비율 — 아카이브 0이면 None), `ratio_quantiles(ratios: Sequence[float]) -> tuple[float, float, float]` (p10·중위·p90, 인덱스 `int(p*(n-1))`), `render(rows, dong_quantiles, over_one, dong_count) -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
"""부동산 생존자 역산 — 연도별 비율·동 분포 (업종 특화 신호 설계서 §10)."""

from apps.verdict.adapter.inbound.cli.real_estate_survivor_backcast import ratio_quantiles, render, survivor_rows


def test_연도별_비율은_생존_사무소를_아카이브_개업으로_나누고_0이면_None이다():
    rows = survivor_rows({2021: 1500, 2024: 1550}, {2021: 5000, 2024: 0}, [2021, 2024])
    assert rows == [(2021, 1500, 5000, 0.3), (2024, 1550, 0, None)]


def test_분위수는_정렬한_값의_인덱스로_뽑는다():
    assert ratio_quantiles([0.5, 0.1, 0.3, 0.9, 0.7]) == (0.1, 0.5, 0.7)


def test_표는_연도와_비율을_찍는다():
    text = render([(2021, 1500, 5000, 0.3), (2024, 1550, 0, None)], (0.1, 0.3, 0.6), 4, 420)
    assert "| 2021 | 1,500 | 5,000 | 30.0% |" in text and "| 2024 | 1,550 | 0 | — |" in text
    assert "비율 > 1인 동 4/420" in text
```
`ratio_quantiles([0.1,0.3,0.5,0.7,0.9])`: n=5 → p10 idx int(0.4)=0 → 0.1, p50 idx int(2.0)=2 → 0.5, p90 idx int(3.6)=3 → 0.7 ✓.

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_survivor_backcast.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
"""부동산 생존자 역산 — 현재 영업 사무소의 등록 연도별 수 ÷ 상권분석 아카이브 같은 연도 개업 수 (업종 특화 신호 설계서 §10).
분석 전용(읽기만). 비율 ≈ 그 연도 개업의 현재 생존율 × (스냅샷 포착률 ÷ 아카이브 포착률). 2024~는 아카이브 개업 단절(설계서 §2-3).

    cd backend && .venv/bin/python -m apps.verdict.adapter.inbound.cli.real_estate_survivor_backcast
"""

from collections.abc import Mapping, Sequence

from sqlalchemy import extract, func, select

from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm as S
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_oracle_database_manager import session_scope

_YEARS = (2021, 2022, 2023, 2024, 2025)
_DONG_YEARS = (2021, 2022, 2023)  # 아카이브 개업이 살아 있는 연도만 동 분포에
_CODE = "CS200033"


def survivor_rows(
    survivors: Mapping[int, int], archive_opens: Mapping[int, int], years: Sequence[int]
) -> list[tuple[int, int, int, float | None]]:
    return [
        (y, survivors.get(y, 0), archive_opens.get(y, 0),
         None if not archive_opens.get(y) else survivors.get(y, 0) / archive_opens[y])
        for y in years
    ]


def ratio_quantiles(ratios: Sequence[float]) -> tuple[float, float, float]:
    ordered = sorted(ratios)
    pick = lambda p: ordered[int(p * (len(ordered) - 1))]  # noqa: E731
    return pick(0.1), pick(0.5), pick(0.9)


def render(rows, dong_quantiles: tuple[float, float, float], over_one: int, dong_count: int) -> str:
    lines = [
        "| 등록 연도 | 현재 영업 사무소 | 아카이브 개업 | 비율 |", "|---:|---:|---:|---:|",
        *[f"| {y} | {s:,} | {a:,} | {'—' if r is None else f'{r * 100:.1f}%'} |" for y, s, a, r in rows],
        "",
        f"동 단위(2021~2023 합산) 비율 p10 {dong_quantiles[0]:.2f} · 중위 {dong_quantiles[1]:.2f} · p90 {dong_quantiles[2]:.2f}, "
        f"비율 > 1인 동 {over_one}/{dong_count}",
    ]
    return "\n".join(lines)


def main() -> None:
    year = extract("year", StoreOrm.open_date)
    live = (StoreOrm.industry_id == "real_estate", StoreOrm.close_date.is_(None), StoreOrm.region_code.is_not(None))
    archive_year = func.substr(S.year_quarter, 1, 4)
    with session_scope() as session:
        survivors = {int(y): n for y, n in session.execute(
            select(year, func.count()).where(*live, year.in_(_YEARS)).group_by(year)).all()}
        archive = {int(y): int(n) for y, n in session.execute(
            select(archive_year, func.sum(S.open_store_count)).where(S.service_industry_code == _CODE)
            .group_by(archive_year)).all()}
        dong_live = dict(session.execute(
            select(StoreOrm.region_code, func.count()).where(*live, year.in_(_DONG_YEARS)).group_by(StoreOrm.region_code)).all())
        dong_arch = dict(session.execute(
            select(S.region_code, func.sum(S.open_store_count))
            .where(S.service_industry_code == _CODE, S.region_code.is_not(None), archive_year.in_([str(y) for y in _DONG_YEARS]))
            .group_by(S.region_code)).all())
    ratios = [dong_live.get(r, 0) / int(n) for r, n in dong_arch.items() if n]
    print(render(survivor_rows(survivors, archive, _YEARS), ratio_quantiles(ratios), sum(1 for x in ratios if x > 1), len(ratios)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인 후 실행 (DB 읽기만)**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_survivor_backcast.py -q && .venv/bin/python -m apps.verdict.adapter.inbound.cli.real_estate_survivor_backcast`
Expected: 테스트 PASS. 표 5행 — 사전 조사로는 2021 1,512/5,269(약 29%) · 2022 1,556/4,501 · 2023 1,513/4,307 · 2024 1,538/222(비율 폭주) · 2025 1,912/150.

- [ ] **Step 5: 기록 + 커밋**

설계서 §17 표에 `| 2026-09-29 | Task 13 생존자 역산 | <표 요약: 연도별 비율, 동 분위수, 비율>1 동 수>. 해석: <예) 2021~2023 비율 약 30~35%는 "5년 생존율 × 포착률 차"로 분리 불가 — 신호 채택 보류 / 2024~ 폭주는 아카이브 개업 단절 확인> |`. HANDOFF §0-12 A 업종 특화 신호 아래 `  - [x] 부동산 생존자 역산(9/29) — <한 줄>. 신호 채택은 보류(팀 판단)`.
v0.46.0 `### Added`: `- 분석 CLI \`real_estate_survivor_backcast\` (설계서 §10) — 현재 영업 부동산 사무소 등록 연도별 수 ÷ 아카이브 개업 수, 동 분포. 기록만(신호 아님).`
```bash
git add backend/apps/verdict/adapter/inbound/cli/real_estate_survivor_backcast.py backend/tests/test_verdict_survivor_backcast.py docs/HANDOFF.md docs/superpowers/specs/2026-09-29-industry-specific-signals-design.md backend/docs/backend_ver_log.md
git commit -m "backend v0.46.0: 부동산 생존자 역산 분석 CLI·기록

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## 4단계 — 프론트 (FE v0.33.0, 구현: Codex)

> 두 태스크 모두 **구현: Codex (`codex exec --cd frontend`)**. 컨트롤러는 태스크 본문 전체와 함께 **Task 12 게이트 결과**(설계서 §17 해당 행, HANDOFF §0-12 A의 안내 문구 줄)와 **Task 2 파일럿 결과**(PASS/FAIL)를 붙여 넘긴다. 아래 "게이트 결과에 따라"로 적힌 곳은 그 값으로 채운다.
> 프론트 규칙: CLAUDE.md Part V — feature 간 import 금지, 색은 토큰만, 타입 단일 원천 `@/shared/api/types.ts`, mock은 실 API 미러, 테스트는 co-located `*.test.ts(x)`·한국어 제목.

### Task 14: 판정 타입·어휘·mock 미러 — basis·새 신호 키·원천 (FE)

**구현: Codex (`codex exec --cd frontend`)**

설계서 §9-3·§13. 백엔드 계약(Task 3·5·11·12)을 타입과 mock에 옮긴다.

**Files:**
- Modify: `frontend/src/shared/api/types.ts` (판정 카드 절, 384~406행 근처)
- Modify: `frontend/src/shared/verdict.ts`, `frontend/src/shared/verdict.test.ts`
- Modify: `frontend/src/app/api/mock/fixtures.ts` (판정 카드 mock 절, 770~830행 근처)
- Modify: `frontend/src/app/api/mock/verdicts/[regionCode]/route.test.ts`
- Modify: `frontend/docs/frontend_ver_log.md`

**Interfaces:**
- Consumes: 백엔드 단건 응답 `basis: "permit" | "proxy" | "aggregate"`, 신호 키 `closure_rate`·`tobacco_gap`(+ Task 2 PASS면 `trade_per_office`), 원천 `tobacco`·`commerce`(+ PASS면 `molit`). 프로필별 신호 순서: permit `[net_outflow, survival_cliff, early_closure, saturation, shrinking]` · proxy `[… 5개, tobacco_gap]` · aggregate `[closure_rate, survival_cliff, early_closure, saturation, shrinking(, trade_per_office)]`. aggregate의 `survival_cliff`·`early_closure`는 항상 `unavailable`, evidence `"집계 원천 — 개별 점포 개업·폐업일이 없어 산출하지 않음"`.
- Produces (Task 15가 쓴다):
  - `types.ts`: `VerdictSignalKey`(+`"closure_rate" | "tobacco_gap"`, PASS면 `| "trade_per_office"`), `VerdictSignalSource = "store" | "metric" | "neighborhood" | "tobacco" | "commerce"`(PASS면 `| "molit"`), `VerdictSignal.source: VerdictSignalSource`, `VerdictBasis = "permit" | "proxy" | "aggregate"`, `RegionIndustryVerdict.basis: VerdictBasis`
  - `shared/verdict.ts`: `SIGNAL_LABELS`에 `closure_rate: "폐업률"`, `tobacco_gap: "담배권 빈자리"`(PASS면 `trade_per_office: "사무소당 거래"`); `ADVISORY_SIGNAL_KEYS = new Set(["shrinking", "tobacco_gap"])`(PASS면 + `"trade_per_office"`); `VERDICT_BASIS_BADGE: Record<VerdictBasis, { label: string; description: string } | null>`; `VERDICT_EXCLUDED_INDUSTRIES`(게이트 결과에 따라); `verdictExclusionNotice(industryId: string): string`

- [ ] **Step 1: 실패하는 테스트 작성**

`src/shared/verdict.test.ts`:
- 기존 `it("신호 5개 라벨", …)`을 다음으로 교체:
```ts
it("신호 라벨은 공통 5개 뒤에 업종 특화 신호를 둔다", () => {
  expect(Object.keys(SIGNAL_LABELS)).toEqual([
    "net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking", "closure_rate", "tobacco_gap",
    // Task 2 PASS면 여기에 "trade_per_office"
  ]);
  expect(signalLabel("net_outflow")).toBe("순유출");
  expect(signalLabel("closure_rate")).toBe("폐업률");
  expect(signalLabel("tobacco_gap")).toBe("담배권 빈자리");
  expect(signalLabel("unknown")).toBe("unknown");
});

it("담배권 빈자리는 상권 축소처럼 참고 신호다", () => {
  expect(ADVISORY_SIGNAL_KEYS.has("tobacco_gap")).toBe(true);
  expect(ADVISORY_SIGNAL_KEYS.has("shrinking")).toBe(true);
});

it("판정 원천 배지는 인허가에는 없고 대리·집계 원천에만 있다", () => {
  expect(VERDICT_BASIS_BADGE.permit).toBeNull();
  expect(VERDICT_BASIS_BADGE.proxy?.label).toBe("담배소매인 이력 기준");
  expect(VERDICT_BASIS_BADGE.aggregate?.label).toBe("집계 기반 판정");
});

it("판정 제외 업종 안내 문구는 업종별 사유를 붙이고 모르는 업종은 기본 문구다", () => {
  expect(verdictExclusionNotice("academy")).toBe("판정 준비 중인 업종 — 아직 판정을 제공하지 않습니다");
});
```
- 기존 `it("판정 대상 업종 판별", …)`과 `it("폐업 이력이 없는 부동산은 판정 대상에서 제외한다", …)`를 **게이트 결과에 따라** 교체:
  - 통과한 업종: `expect(isVerdictIndustry("<id>")).toBe(true);`
  - 미달한 업종: `expect(isVerdictIndustry("<id>")).toBe(false);`와 `expect(verdictExclusionNotice("<id>")).toBe("판정 준비 중인 업종 — <HANDOFF의 사유 문구>");`
  - 공통: `expect(isVerdictIndustry("korean_food")).toBe(true); expect(isVerdictIndustry("academy")).toBe(false);`
- import 줄에 `ADVISORY_SIGNAL_KEYS, VERDICT_BASIS_BADGE, verdictExclusionNotice` 추가.

`src/app/api/mock/verdicts/[regionCode]/route.test.ts` 끝에:
```ts
it("단건은 판정 원천 basis를 싣는다 — 인허가 업종은 permit", async () => {
  const v = await (await call("1168064000")).json();
  expect(v.basis).toBe("permit");
});
```
그리고 **게이트 결과에 따라** 업종마다 하나:
- 편의점 통과:
```ts
it("편의점 단건은 담배소매인 원천(proxy)과 담배권 빈자리 참고 신호를 싣는다", async () => {
  const v = await (await call("1168064000", "?industry=convenience_store")).json();
  expect(v.basis).toBe("proxy");
  expect(v.signals.map((s: { key: string }) => s.key)).toEqual([
    "net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking", "tobacco_gap",
  ]);
  expect(v.signals[0].source).toBe("tobacco");
});
```
- 부동산 통과:
```ts
it("부동산 단건은 집계 원천(aggregate)이고 생존 절벽·조기 폐업은 집계 사유로 미판정이다", async () => {
  const v = await (await call("1168064000", "?industry=real_estate")).json();
  expect(v.basis).toBe("aggregate");
  expect(v.signals.map((s: { key: string }) => s.key)).toEqual([
    "closure_rate", "survival_cliff", "early_closure", "saturation", "shrinking",
    // Task 2 PASS면 "trade_per_office"
  ]);
  expect(v.signals[1]).toMatchObject({ level: "unavailable", evidence: "집계 원천 — 개별 점포 개업·폐업일이 없어 산출하지 않음", source: "commerce" });
});
```
- 미달한 업종:
```ts
it("<업종>은 판정 대상이 아니라 404 INDUSTRY_NOT_FOUND", async () => {
  const res = await call("1168064000", "?industry=<id>");
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run src/shared/verdict.test.ts src/app/api/mock/verdicts`
Expected: FAIL — `SIGNAL_LABELS` 키 불일치, `VERDICT_BASIS_BADGE` 미정의, `basis` undefined.

- [ ] **Step 3: 타입**

`src/shared/api/types.ts` 판정 카드 절:
```ts
export type VerdictSignalKey =
  | "net_outflow" | "survival_cliff" | "early_closure" | "saturation" | "shrinking"
  | "closure_rate" | "tobacco_gap"; // 업종 특화 — 부동산 폐업률·편의점 담배권 빈자리 (Task 2 PASS면 | "trade_per_office")
export type VerdictSignalSource = "store" | "metric" | "neighborhood" | "tobacco" | "commerce"; // PASS면 | "molit"
/** 판정 원천 — permit 인허가 개별 이력 · proxy 담배소매인 대리 이력(편의점) · aggregate 상권분석 동×분기 집계(부동산). */
export type VerdictBasis = "permit" | "proxy" | "aggregate";
```
`VerdictSignal.source`를 `VerdictSignalSource`로. `RegionIndustryVerdict`에 `basis: VerdictBasis;` 추가, `signals` 주석을 `// 프로필이 정한 개수·순서 — 인허가 5 · 편의점 6 · 부동산 5`로.

- [ ] **Step 4: `shared/verdict.ts`**

- `SIGNAL_LABELS`에 `closure_rate: "폐업률", tobacco_gap: "담배권 빈자리",`(PASS면 `trade_per_office: "사무소당 거래",`).
- `ADVISORY_SIGNAL_KEYS`를 `new Set(["shrinking", "tobacco_gap"])`(PASS면 + `"trade_per_office"`), 주석 "백엔드 `ADVISORY_SIGNAL_KEYS` 미러 — 상권 축소(무신호)·담배권 빈자리(진입 가능성) 등은 평가·표시만".
- 추가:
```ts
/** 판정 원천 배지 — 인허가는 배지 없음. 문구는 설계서 §7-2. */
export const VERDICT_BASIS_BADGE: Record<VerdictBasis, { label: string; description: string } | null> = {
  permit: null,
  proxy: {
    label: "담배소매인 이력 기준",
    description: "편의점 개폐업을 담배소매인 지정·폐업 이력으로 대신 셉니다 — 원천 기준 2026-08",
  },
  aggregate: {
    label: "집계 기반 판정",
    description: "개별 점포의 개업·폐업일이 아니라 서울시 상권분석 동×분기 집계로 판정 — 생존 절벽·조기 폐업은 산출하지 않습니다",
  },
};

/** 판정 제외 업종의 사유 (Task 12 게이트 결과 — 미달 업종만 남긴다). */
const VERDICT_EXCLUSION_REASONS: Record<string, string> = {
  // 게이트 결과에 따라: 미달 업종마다 HANDOFF §0-12 A의 사유 문구를 그대로. 예)
  // convenience_store: "담배소매인 이력으로 만든 판정이 백테스트 기준(경고 lift 1.10배)을 넘지 못했습니다",
};

export function verdictExclusionNotice(industryId: string): string {
  return `판정 준비 중인 업종 — ${VERDICT_EXCLUSION_REASONS[industryId] ?? "아직 판정을 제공하지 않습니다"}`;
}
```
- `VERDICT_EXCLUDED_INDUSTRIES`를 게이트 결과에 따라: 둘 다 통과 → `new Set<string>()`, 하나 미달 → 그 업종만. 위 주석도 결과에 맞게("편의점·부동산은 9/29 업종 특화 원천으로 재포함 — 미달 업종만 남긴다").
- import에 `VerdictBasis`.

- [ ] **Step 5: mock 픽스처**

`src/app/api/mock/fixtures.ts` 판정 카드 절:
```ts
// 업종별 판정 원천 — 백엔드 dependencies의 sources 미러 (업종 특화 신호 설계서 §4). 판정 대상 여부는 isVerdictIndustry가 정한다.
const BASIS_BY_INDUSTRY: Partial<Record<string, VerdictBasis>> = { convenience_store: "proxy", real_estate: "aggregate" };
// 백엔드 profiles.py 미러 — 원천별 신호 순서
const SIGNAL_KEYS_BY_BASIS: Record<VerdictBasis, VerdictSignalKey[]> = {
  permit: ["net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking"],
  proxy: ["net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking", "tobacco_gap"],
  aggregate: ["closure_rate", "survival_cliff", "early_closure", "saturation", "shrinking"], // PASS면 + "trade_per_office"
};
// 원천 표기 교체 (SourcedSignal 미러) — 없는 키는 SIGNAL_SOURCE 기본값
const SOURCE_BY_BASIS: Record<VerdictBasis, Partial<Record<VerdictSignalKey, VerdictSignalSource>>> = {
  permit: {},
  proxy: { net_outflow: "tobacco", survival_cliff: "tobacco", early_closure: "tobacco", saturation: "tobacco" },
  aggregate: { survival_cliff: "commerce", early_closure: "commerce", saturation: "commerce" },
};
// 원천이 재료를 주지 않는 신호 (UnsupportedSignal 미러)
const UNSUPPORTED_BY_BASIS: Record<VerdictBasis, ReadonlySet<VerdictSignalKey>> = {
  permit: new Set(), proxy: new Set(), aggregate: new Set(["survival_cliff", "early_closure"]),
};
const UNSUPPORTED_EVIDENCE = "집계 원천 — 개별 점포 개업·폐업일이 없어 산출하지 않음";
```
- 기존 `SIGNAL_KEYS` 상수는 지우고(위 표가 대신), `SIGNAL_SOURCE`에 `closure_rate: "commerce", tobacco_gap: "tobacco"`(PASS면 `trade_per_office: "molit"`)를 더해 `Record<VerdictSignalKey, VerdictSignalSource>`를 채운다.
- `signalOf(key, regionCode, industryId, basis: VerdictBasis)`: 맨 앞에서 `UNSUPPORTED_BY_BASIS[basis].has(key)`면 `{ key, level: "unavailable", value: null, percentile: null, evidence: UNSUPPORTED_EVIDENCE, source }`를 돌려준다. `source = SOURCE_BY_BASIS[basis][key] ?? SIGNAL_SOURCE[key]`. 해시 시드 `hashSeed("verdict", key, regionCode, industryId)`는 **바꾸지 않는다**(기존 계약 테스트 값 유지). `EVIDENCE`에 추가:
  - `closure_rate: \`지난 4분기 폐업 ${5 + Math.floor(u * 30)}곳 (4분기 전 점포 ${60 + Math.floor(u * 100)}곳의 ${Math.round(u * 8)}%, 서울 ${name} 상위 ${top}%, 서울시 상권분석 집계)\``
  - `tobacco_gap: \`이 동 상가 자리 ${300 + Math.floor(u * 900)}곳 중 ${50 + Math.round(u * 30)}%가 영업 중인 담배소매인 50m 안 — 새 담배소매인 지정이 어렵다 (서울 상위 ${top}%)\``
  - (PASS면) `trade_per_office: \`지난 12개월 아파트 매매 ${100 + Math.floor(u * 400)}건 ÷ 중개사무소 ${40 + Math.floor(u * 60)}곳 = 사무소당 ${(1 + u * 6).toFixed(1)}건 (서울 ${name} 하위 ${top}%, 국토부 실거래가)\``
- `verdictOf(regionCode, industryId)`: `const basis = BASIS_BY_INDUSTRY[industryId] ?? "permit"; const signals = SIGNAL_KEYS_BY_BASIS[basis].map((key) => signalOf(key, regionCode, industryId, basis));` 반환 객체에 `basis` 추가. `judgeOf`는 그대로(참고 신호 제외·보류 우선 규칙이 백엔드와 같다).
- 이 파일의 다른 `SIGNAL_KEYS` 사용처가 있으면 `SIGNAL_KEYS_BY_BASIS.permit`으로 바꾼다.

- [ ] **Step 6: 통과 확인 + 전체**

Run: `cd frontend && npx vitest run src/shared/verdict.test.ts src/app/api/mock && npx vitest run && npx tsc --noEmit`
Expected: 전부 PASS, 타입 오류 0. `verdict-card.tsx`의 `SOURCE_LABEL: Record<VerdictSignal["source"], string>`이 새 원천 때문에 tsc 오류를 내면 **이 태스크에서는** 두 키(`tobacco: "담배소매인"`, `commerce: "상권분석 집계"`, PASS면 `molit: "국토부 실거래가"`)만 추가해 막는다(표시 변경은 Task 15).

- [ ] **Step 7: 버전 로그 + 커밋**

`frontend/docs/frontend_ver_log.md`의 머리말 인용 블록 아래, 기존 `## [v0.32.0]` 위에:
```markdown
## [v0.33.0] - 2026-09-29

### Added
- **판정 원천 계약** (업종 특화 신호 설계서 §9-3) — `VerdictBasis`(`permit`·`proxy`·`aggregate`), `RegionIndustryVerdict.basis`, 신호 키 `closure_rate`·`tobacco_gap`, 원천 `tobacco`·`commerce`. `shared/verdict.ts`: 라벨(폐업률·담배권 빈자리), `VERDICT_BASIS_BADGE`, `verdictExclusionNotice`. mock은 업종별 원천·신호 목록·미지원 신호를 백엔드 프로필대로 미러(Codex).

### Changed
- `ADVISORY_SIGNAL_KEYS`에 `tobacco_gap`. `VERDICT_EXCLUDED_INDUSTRIES` = <게이트 결과 집합>(9/29 재포함 게이트).
```
```bash
git add frontend/src/shared frontend/src/app/api/mock frontend/docs/frontend_ver_log.md
git commit -m "frontend v0.33.0: 판정 원천 basis·업종 특화 신호 계약·mock 미러 (Codex)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: 판정 카드 원천 배지 · brief 제외 업종 안내 한 줄 · 편의점 분기 레지스트리 (FE)

**구현: Codex (`codex exec --cd frontend`)**

설계서 §7-2·§13. Task 14의 어휘로 화면을 바꾼다.

**Files:**
- Modify: `frontend/src/shared/ui/verdict-card.tsx`, `frontend/src/shared/ui/verdict-card.test.tsx`
- Modify: `frontend/src/features/map-explorer/components/verdict-section.tsx`, `frontend/src/features/map-explorer/components/verdict-section.test.tsx`
- Modify: `frontend/src/features/map-explorer/components/side-panel.tsx`, `frontend/src/features/map-explorer/components/side-panel.test.tsx`
- Modify: `frontend/docs/frontend_ver_log.md`

**Interfaces:**
- Consumes: Task 14 `VERDICT_BASIS_BADGE`, `verdictExclusionNotice`, `ADVISORY_SIGNAL_KEYS`, `VerdictSignalSource`, `isVerdictIndustry`
- Produces: 화면 동작 —
  - `VerdictCard`: `VERDICT_BASIS_BADGE[verdict.basis]`가 있으면 판정 배지 줄(`role="status"` div) 안 qualifier 뒤에 `<span title={description}>{label}</span>`(테두리 `--border`, 글자 `--text-secondary`, 10px). 원천 태그 `SOURCE_LABEL`에 `tobacco: "담배소매인"`, `commerce: "상권분석 집계"`(PASS면 `molit: "국토부 실거래가"`). 참고 줄은 **켜진(on·strong) 참고 신호 전부**를 `참고: {evidence}` 한 줄씩(`verdict.signals` 순서).
  - `VerdictSection`: `isVerdictIndustry(industry)`가 false이고 `INDUSTRIES`에 있는 업종이면 `null` 대신 `<p className="mt-3 text-xs text-[var(--text-secondary)]">{verdictExclusionNotice(industry)}</p>` (요청은 여전히 보내지 않는다). 학원·어린이집처럼 `INDUSTRIES`에 없는 업종은 지금처럼 `null`.
  - `SidePanel`: `industry === "convenience_store"` 분기를 **본문 레지스트리**로 교체 — `const BRIEF_BODIES: Partial<Record<string, ComponentType<{ regionCode: string; industry: string }>>> = { convenience_store: ConvenienceBrief }`, 기본은 `DefaultBrief`(= `VerdictSection` + `NeighborhoodLine`, 현행 그대로). `ConvenienceBrief` = `VerdictSection` + `ConvenienceSummarySection`(현행 편의점 본문에서 하드코딩 문구 "판정은 담배권 특화 신호 단계에서 제공"만 빼고 `VerdictSection`을 앞에). 편의점 판정이 제외면 `VerdictSection`이 안내 한 줄을, 포함이면 카드를 그린다.

- [ ] **Step 1: 실패하는 테스트 작성**

`src/shared/ui/verdict-card.test.tsx` 끝에:
```tsx
const signal = (over: Partial<VerdictSignal>): VerdictSignal => ({
  key: "net_outflow", level: "off", value: 0, percentile: 10, evidence: "근거", source: "store", ...over,
});
const base = { region_code: "1", industry_id: "real_estate", verdict_code: "orange" as const, strong_count: 0, on_count: 1, computed_at: "2026-09-29T04:30:00+09:00" };

it("집계 기반 판정은 배지와 설명 툴팁을 단다", () => {
  render(<VerdictCard industryLabel="부동산중개업" verdict={{ ...base, basis: "aggregate", signals: [signal({ key: "closure_rate", level: "on", source: "commerce", evidence: "지난 4분기 폐업 18곳" })] }} />);
  const badge = screen.getByText("집계 기반 판정");
  expect(badge).toHaveAttribute("title", expect.stringContaining("서울시 상권분석"));
  expect(screen.getByText("상권분석 집계")).toBeInTheDocument(); // 원천 태그
});

it("인허가 판정은 원천 배지가 없다", () => {
  render(<VerdictCard industryLabel="한식" verdict={{ ...base, industry_id: "korean_food", basis: "permit", signals: [] }} />);
  expect(screen.queryByText("집계 기반 판정")).toBeNull();
  expect(screen.queryByText("담배소매인 이력 기준")).toBeNull();
});

it("켜진 참고 신호가 둘이면 참고 줄도 둘이다", () => {
  render(<VerdictCard industryLabel="편의점" verdict={{ ...base, industry_id: "convenience_store", verdict_code: "clear", on_count: 0, basis: "proxy", signals: [
    signal({ key: "shrinking", level: "on", source: "neighborhood", evidence: "상권축소 근거" }),
    signal({ key: "tobacco_gap", level: "strong", source: "tobacco", evidence: "담배권 근거" }),
  ] }} />);
  expect(screen.getByText("참고: 상권축소 근거")).toBeInTheDocument();
  expect(screen.getByText("참고: 담배권 근거")).toBeInTheDocument();
  expect(screen.getByText("담배소매인 이력 기준")).toBeInTheDocument();
});
```
(import에 `VerdictSignal` 타입. 기존 첫 테스트의 verdict 객체에 `basis: "permit"`을 더한다 — 타입이 필수로 바뀌었다.)

`verdict-section.test.tsx` 끝에(기존 파일의 렌더 헬퍼·mock 방식을 따른다):
- 제외 업종이 남아 있으면: `it("판정 제외 업종은 카드 대신 준비 중 안내 한 줄을 보여주고 요청하지 않는다", …)` — `<VerdictSection regionCode="1168064000" industry="<제외 업종>" />` 렌더 → `screen.getByText(verdictExclusionNotice("<제외 업종>"))` 존재, `fetchVerdict` mock 호출 0회.
- 둘 다 통과했으면 대신: `it("판정 대상이 아닌 select 밖 업종(학원)은 아무것도 그리지 않는다", …)` — `industry="academy"` → `container`가 비어 있고 `fetchVerdict` 호출 0회.

`side-panel.test.tsx`의 `it("편의점은 현황 한 줄과 특화 신호 안내만 본문에 보여준다", …)`를 게이트 결과에 따라 교체:
- 편의점 미달:
```tsx
it("편의점은 판정 준비 중 안내와 현황 한 줄을 보여준다", async () => {
  renderPanel({ industry: "convenience_store" });
  expect(await screen.findByText("편의점 149곳 · 기준 2026년 6월")).toBeInTheDocument();
  expect(screen.getByText(verdictExclusionNotice("convenience_store"))).toBeInTheDocument();
  expect(screen.queryByText("판정은 담배권 특화 신호 단계에서 제공")).toBeNull();
  expect(screen.queryByRole("region", { name: "창업 경고 판정" })).toBeNull();
  expect(screen.queryByRole("checkbox")).toBeNull();
});
```
- 편의점 통과:
```tsx
it("편의점은 판정 카드와 현황 한 줄을 함께 보여준다", async () => {
  renderPanel({ industry: "convenience_store" });
  expect(await screen.findByRole("region", { name: "창업 경고 판정" })).toBeInTheDocument();
  expect(await screen.findByText("편의점 149곳 · 기준 2026년 6월")).toBeInTheDocument();
  expect(screen.queryByText("판정은 담배권 특화 신호 단계에서 제공")).toBeNull();
});
```
  (이 파일은 `../api`를 목으로 가므로 `fetchVerdict`가 편의점에 대해 `basis: "proxy"` 판정을 돌려주게 목을 맞춘다.)
- `it("부동산은 판정 없이 동네 한 줄과 CTA를 표시한다", …)`도 같은 방식: 미달이면 안내 한 줄 `verdictExclusionNotice("real_estate")`를 추가로 기대, 통과면 판정 카드(`region "창업 경고 판정"`)와 배지 "집계 기반 판정"을 기대하도록 제목·단언을 바꾼다.

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run src/shared/ui/verdict-card.test.tsx src/features/map-explorer/components/verdict-section.test.tsx src/features/map-explorer/components/side-panel.test.tsx`
Expected: FAIL — 배지·안내 문구 없음, 참고 줄 1개.

- [ ] **Step 3: 구현**

`verdict-card.tsx`:
```tsx
const SOURCE_LABEL: Record<VerdictSignalSource, string> = {
  store: "인허가",
  metric: "지표",
  neighborhood: "상권분석",
  tobacco: "담배소매인",
  commerce: "상권분석 집계",
  // Task 2 PASS면 molit: "국토부 실거래가",
};
```
본문:
```tsx
  const advisories = verdict.signals.filter((s) => ADVISORY_SIGNAL_KEYS.has(s.key) && (s.level === "on" || s.level === "strong"));
  const basisBadge = VERDICT_BASIS_BADGE[verdict.basis];
```
배지 줄(`role="status"` div) 안 qualifier span 뒤:
```tsx
        {basisBadge && (
          <span title={basisBadge.description} className="rounded border border-[var(--border)] px-1 text-[10px] text-[var(--text-secondary)]">
            {basisBadge.label}
          </span>
        )}
```
참고 줄 `{advisory && <p …>참고: {advisory.evidence}</p>}`를:
```tsx
      {advisories.map((s) => (
        <p key={s.key} className="text-xs text-[var(--text-secondary)]">참고: {s.evidence}</p>
      ))}
```
`verdict-section.tsx`의 `if (!isVerdictIndustry(industry)) return null;`을:
```tsx
  if (!isVerdictIndustry(industry)) {
    // select 업종인데 판정 제외면 안내 한 줄(설계서 §13), select 밖 업종(학원·어린이집)은 아무것도 그리지 않는다
    return (INDUSTRIES as readonly string[]).includes(industry)
      ? <p className="mt-3 text-xs text-[var(--text-secondary)]">{verdictExclusionNotice(industry)}</p>
      : null;
  }
```
(import `INDUSTRIES`는 `@/shared/industries`, `verdictExclusionNotice`는 `@/shared/verdict`. 훅 호출 순서 규칙상 `useVerdict` 호출은 이 분기보다 **위**에 그대로 둔다 — 지금 구조 유지.)
`side-panel.tsx`:
```tsx
type BriefBody = ComponentType<{ regionCode: string; industry: string }>;

function DefaultBrief({ regionCode, industry }: { regionCode: string; industry: string }) {
  return (
    <>
      <VerdictSection regionCode={regionCode} industry={industry} />
      <NeighborhoodLine regionCode={regionCode} />
    </>
  );
}

function ConvenienceBrief({ regionCode, industry }: { regionCode: string; industry: string }) {
  return (
    <>
      <VerdictSection regionCode={regionCode} industry={industry} />
      <ConvenienceSummarySection regionCode={regionCode} />
    </>
  );
}

/** 업종별 brief 본문 — 조건 분기 대신 레지스트리 (CLAUDE.md §5). 없는 업종은 DefaultBrief. */
const BRIEF_BODIES: Partial<Record<string, BriefBody>> = { convenience_store: ConvenienceBrief };
```
본문의 `{industry === "convenience_store" ? (…) : (…)}` 블록을:
```tsx
          {(() => {
            const Body = BRIEF_BODIES[industry] ?? DefaultBrief;
            return <Body regionCode={regionCode} industry={industry} />;
          })()}
```
(또는 컴포넌트 상단에서 `const Body = BRIEF_BODIES[industry] ?? DefaultBrief;`를 만들고 `<Body … />` — 가독성 좋은 쪽. `import type { ComponentType } from "react"`.)

- [ ] **Step 4: 통과 확인 + 전체**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 전부 PASS, 타입 오류 0. 리포트 화면(`agent-report/components/report-visuals.tsx`)의 `VerdictCard`도 같은 배지를 받는다 — `report-visuals.test.tsx` 픽스처에 `basis`가 없어 타입 오류가 나면 `basis: "permit"`을 채운다.

- [ ] **Step 5: 버전 로그 + 커밋**

v0.33.0 `### Added`에:
```markdown
- **판정 원천 배지·안내** (설계서 §7-2·§13) — `VerdictCard`에 원천 배지("집계 기반 판정"·"담배소매인 이력 기준", 설명 툴팁), 원천 태그 담배소매인·상권분석 집계, 켜진 참고 신호 전부를 "참고:" 줄로. brief: 판정 제외 select 업종은 카드 대신 "판정 준비 중인 업종 — {사유}" 한 줄.
```
`### Changed`에:
```markdown
- 사이드패널 편의점 분기를 업종별 본문 레지스트리(`BRIEF_BODIES`)로 교체, 하드코딩 문구 "판정은 담배권 특화 신호 단계에서 제공" 제거(Codex).
```
```bash
git add frontend/src frontend/docs/frontend_ver_log.md
git commit -m "frontend v0.33.0: 판정 원천 배지·제외 업종 안내 한 줄·brief 본문 레지스트리 (Codex)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## 5단계 — 마무리

### Task 16: 실DB 판정 배치 · API 확인 · 문서 정리

**Files:**
- Modify: `docs/HANDOFF.md` (§0-7 4번, §0-11, §0-12 A)
- Modify: `docs/STATUS.md` (§2-2 인허가·점포 절 끝 또는 판정 관련 줄)
- Modify: 설계서 §17
- Modify: `backend/docs/backend_ver_log.md`, `frontend/docs/frontend_ver_log.md` (빠진 줄 확인만)

**Interfaces:**
- Consumes: 전 태스크

- [ ] **Step 1: 전체 테스트**

Run: `cd backend && .venv/bin/python -m pytest tests -q` 그리고 `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 둘 다 실패 0. 백엔드 수는 694 + 이번 신규분.

- [ ] **Step 2: 개발 DB 판정 배치**

Run: `cd backend && .venv/bin/alembic current && time .venv/bin/python -m apps.verdict.adapter.inbound.cli.build_verdicts`
Expected: head(`d0e1f2a3b4c5`, 실거래가 진행 시 `e1f2a3b4c5d6`), `판정 업서트: <427 × 판정 대상 수>건`, 소요 20초 이내(담배권 빈자리 계산 포함).
분포 확인(읽기만):
```sql
select industry_id, basis, verdict_code, count(*) from region_industry_verdict group by 1, 2, 3 order by 1, 3;
```
편입 업종이 있으면 그 업종의 `basis`가 `proxy`/`aggregate`이고 나머지는 전부 `permit`인지, 보류 비율이 설계서 §2-1 예상(편의점 약 22%)과 크게 다르지 않은지 본다.

- [ ] **Step 3: API 스팟 체크 (새 코드로 8201에 잠깐 띄운다)**

```bash
cd backend && (.venv/bin/uvicorn main:app --port 8201 > /tmp/verdict-8201.log 2>&1 &) && sleep 4
curl -s "http://localhost:8201/verdicts/1168064000?industry=korean_food" | python3 -c "import json,sys; v=json.load(sys.stdin); print(v['basis'], [s['key'] for s in v['signals']])"
curl -s "http://localhost:8201/verdicts/1168064000?industry=convenience_store" | head -c 400; echo
curl -s "http://localhost:8201/verdicts/1168064000?industry=real_estate" | head -c 400; echo
pkill -f "uvicorn main:app --port 8201"
```
Expected: 한식 `permit [net_outflow, …, shrinking]`. 편입 업종은 200 + `basis` + 프로필 신호 목록(편의점 6개·부동산 5개/6개). 제외 유지 업종은 404 `{"error":{"code":"INDUSTRY_NOT_FOUND",…}}`. (포트 8201은 백엔드 범위 8200~8299 안의 임시 포트 — 도커 8200은 건드리지 않는다.)

- [ ] **Step 4: 문서**

- `docs/HANDOFF.md` §0-7 4번 → `4. 업종 특화 신호 — ✅ 1차 완료(9/29, BE v0.46.0 · FE v0.33.0): 편의점 담배소매인 이력·담배권 빈자리(참고), 부동산 상권분석 집계 판정. 재포함 게이트 결과 <요약>`.
- §0-11 "편의점은 … 재포함한다"·"부동산도 … 제외" 두 줄 → 게이트 결과대로 "판정 대상 = <N>종" 갱신.
- §0-12 A "업종 특화 신호" 항목 `[ ]` → `[x]`(1차), 하위에 남은 후속: 담배권 빈자리 등급 승격(lift 확인 후 팀), 구별 담배 거리 조례, 담배소매인 아카이브 갱신 절차(파일 재확보 → `load_tobacco_retailer`), 프랜차이즈 잠식 신호(§0-9, 미착수), 실거래가(PASS면 "전월세·상업용 추가 검토", FAIL이면 "외부 대기"). "제외 업종(부동산·편의점) brief 안내 한 줄·편의점 분기 레지스트리 복귀" 항목 → `[x]`(FE v0.33.0).
- `docs/STATUS.md` §2-2에 한 줄: `판정 원천(9/29, BE v0.46.0): region_industry_verdict.basis — permit/proxy(편의점 = 담배소매인 에피소드 약 20,900개, 기준일 2026-08-21)/aggregate(부동산 = 상권분석 CS200033, 개업 수 2024Q1~ 단절). 판정 대상 <N>종.`
- 설계서 §17에 `| 2026-09-29 | Task 16 실DB 배치 | <업서트 건수·소요·업종별 basis·판정 분포 요약>, API 스팟 체크 결과 |`.
- 두 버전 로그에서 이번 태스크들의 줄이 빠짐없이 들어갔는지 확인(없으면 추가).

- [ ] **Step 5: 커밋**

```bash
git add docs/HANDOFF.md docs/STATUS.md docs/superpowers/specs/2026-09-29-industry-specific-signals-design.md backend/docs/backend_ver_log.md frontend/docs/frontend_ver_log.md
git commit -m "docs: 업종 특화 신호 1차 완료 — 실DB 배치·API 확인·HANDOFF/STATUS 갱신

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Self-Review

**1. 설계서 대응**

| 설계서 | 태스크 |
|---|---|
| §2 사전 조사 | 실측 재확인은 Task 7·8 스모크, Task 12 원천 검증 |
| §3 결정 — 원천 Strategy | Task 5(프로필)·6(레지스트리) |
| §4 구조 | Task 5·6·7·8 |
| §5 편의점(브랜드·승계·창 집계·기준일) | Task 4·7 |
| §6 담배권 빈자리(정의·50m·참고) | Task 4(격자)·5(신호·참고)·7(재료) |
| §7 부동산(폐업률·포화·미지원·재고 결과·† 합산 제외) | Task 5·6·8·9 |
| §8 재포함 게이트 | Task 9(함수·CLI)·12(실측·반영) |
| §9 basis 컬럼·키·API | Task 3·5 |
| §10 생존자 역산 | Task 13 |
| §11 실거래가 파일럿·조건부 구현 | Task 2·10·11 |
| §12 LOCALDATA 재확인 | Task 1 |
| §13 프론트 | Task 14·15 |
| §14 테스트 | 각 태스크 Step 1 |
| §15 리스크 — 브랜드 사전 ρ·폐업0동 | Task 12 Step 2 |
| §17 진행 기록 | Task 1·2·12·13·16 |

빈 곳 없음. 설계서 §15의 "대안 목록에 집계 기반 판정이 섞임"은 동작 변경 없이 두는 리스크라 태스크가 없다(의도).

**2. 자리표시자 점검** — "TBD·나중에·적절히" 없음. 게이트 결과에 따라 달라지는 곳(Task 12 Step 3, Task 14·15의 제외 목록·안내 문구·테스트 기대값)은 결과 두 갈래의 코드를 모두 적었고, 채울 값의 출처(설계서 §17·HANDOFF 줄)를 지정했다. Task 1·2의 기록 문구는 조사 결과 자리를 `<…>`로 둔 템플릿이며 무엇을 적을지 항목이 정해져 있다.

**3. 이름·타입 일관성**
- `IndustrySignalDataPort.signal_stats(today)` / `store_counts(year_max, quarter_max)` / `entrant_outcomes(as_of, entry_days, horizon_days)` — Task 6 정의, Task 7·8·11 구현, Task 6 테스트 Fake와 같은 순서.
- `IndustrySource(profile, data)` — Task 6 정의, Task 7·8·11 의존성에서 같은 인자 순서.
- `StoreSignalStat`·`SignalInput`의 `gap_candidates`·`gap_blocked`(Task 5), `trade_12m`(Task 11) — 모두 기본값 필드라 기존 위치 인자 생성자(테스트 포함)가 깨지지 않는다. 인터랙터 `_EMPTY_STAT`에 Task 6이 `gap_*`, Task 11이 `trade_12m`을 더한다.
- `RegionIndustryVerdict.basis`·`RegionIndustryVerdictDto.basis` 기본값 `BASIS_PERMIT` — Task 3. `summarize`의 `_SCOPES_OF_BASIS[v.basis]`(Task 6)는 기본값 덕에 기존 백테스트 테스트의 `_v()` 판정도 받는다.
- `BacktestReportDto.industry_basis`(Task 6)·`gates`(Task 9) — 둘 다 기본값 `()`, 기존 생성 코드 호환. CLI 테스트는 둘을 키워드로 준다.
- 신호 키: `SIGNAL_KEYS`(5, 불변) · `SPECIFIC_SIGNAL_KEYS`/`ALL_SIGNAL_KEYS`(Task 5, Task 11이 `trade_per_office` 추가) — 백테스트 정렬(Task 6)·CLI 칸(Task 9)·`_SIGNAL_LABEL`(Task 9·11)·프론트 `SIGNAL_LABELS`(Task 14)가 같은 순서.
- `IndustryCatalogPort.named_industries` — Task 6에서 추상 메서드로 추가하고 같은 태스크에서 기존 Fake 3곳(`test_verdict_build`·`test_verdict_backtest`·`test_verdict_alternatives`)을 고친다. 새 Fake(`test_verdict_sources`)도 구현.
- `quarter_of`·`shift_quarter`는 Task 8에서 만들고 Task 8 게이트웨이가 처음 쓴다. `month_window`(Task 11)는 월 단위라 별개.
- 원천 표기 `source`: `store`·`metric`·`neighborhood`(기존) + `tobacco`·`commerce`(Task 5) + `molit`(Task 11, 조건부) — 프론트 `VerdictSignalSource`·`SOURCE_LABEL`(Task 14·15)이 같은 집합.
