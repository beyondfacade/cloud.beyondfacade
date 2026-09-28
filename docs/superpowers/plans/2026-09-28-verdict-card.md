# 판정 카드 (Verdict Card) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 동×업종마다 공통 경고 신호 5개를 상대평가로 켜서 🔴/🟠/⚪/보류 판정 한 행을 새벽 배치로 만들고, 사이드패널 판정 카드·업종별 위험도 지도·최근 2년 폐업 마커로 보여준다.

**Architecture:** 신규 `verdict` BC(프랙탈 11파일)가 store·metric·neighborhood ORM을 자체 게이트웨이로 읽어 `region_industry_verdict` 테이블을 업서트하고 `GET /verdicts` 두 경로로 노출한다. 신호 = Specification 클래스 1개씩(`domain/services/signals.py`), 판정 = Chain of Responsibility(`rules.py`), 임계값은 백분위 상수 두 개만 두고 경계값은 배치마다 분포에서 재계산한다(`typology.py` 선례). 프론트는 `METRIC_SOURCES`에 범주 지표 `verdict` 1줄, 사이드패널 최상단 `VerdictSection`, 점포 API `status=closed` 확장으로 폐업 마커를 얹는다.

**Tech Stack:** FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL(percentile_cont) · pytest(`beyondfacade_test` DB) / Next.js App Router · TanStack Query · MapLibre · Vitest

**Spec:** `docs/superpowers/specs/2026-09-28-verdict-card-design.md` (이하 "설계서")

## Global Constraints

- 판정 대상 = 마스터 18업종 − `academy`·`childcare`·`restaurant_other`·`chicken`·`convenience_store` = **13종**(Task 7 Ruling A: 편의점은 스냅샷 전용 원천이라 신호 3개 영구 불가 → 특화 신호 단계까지 제외). 도메인 상수 `EXCLUDED_INDUSTRIES`가 유일한 원천. 프론트 `INDUSTRIES`(select)는 여전히 14종이고, 판정 관련 코드만 `VERDICT_EXCLUDED_INDUSTRIES = {"convenience_store"}`로 편의점을 뺀다.
- 신호 레벨: 백분위 `p ≥ 75` → `on`, `p ≥ 90` → `strong`. 백분위는 strict("값보다 작은 동의 비율") (설계서 §3-2).
- 판정: 판정 가능 신호 < 3 → `insufficient`(먼저 검사) / strong ≥ 2 → `red` / on·strong ≥ 1 → `orange` / 그 외 `clear`. 🟢 없음 (설계서 §3-3).
- 표본 가드: 시작 점포·코호트·폐업 건수 < 10, 상주인구 < 1,000 → `unavailable` (설계서 §3-1).
- 포화 분모는 `region_profile_quarter.resident_total`(상주인구만) (설계서 §2).
- 오류 바디 `{error:{code,message}}`, 미지원 값은 404 (`INDUSTRY_NOT_FOUND`·`VERDICT_NOT_FOUND`·`STORE_STATUS_NOT_FOUND`). `code`는 SCREAMING_SNAKE, `message`는 한국어.
- `domain/`·`app/use_cases/`에서 FastAPI·SQLAlchemy import 금지. 다른 BC 접근은 `adapter/outbound/gateways/`에서만.
- 프론트 색은 토큰만(`--danger`·`--warn`·`--text-secondary`·`--border`). 지도 팔레트는 `lib/verdict-palette.ts`에 데이터 시각화 팔레트로 주석 선언.
- mock은 실 API 미러: 경로·파라미터·응답 타입 동일, 타입은 `@/shared/api/types.ts` 한 곳. `Math.random` 금지.
- 테스트 제목은 한국어 서술문. 백엔드 테스트 실행: `cd backend && .venv/bin/python -m pytest tests/<file> -q`. 프론트: `cd frontend && npx vitest run <path>`.
- 단계 끝마다 `backend/docs/backend_ver_log.md` / `frontend/docs/frontend_ver_log.md` 기록 후 커밋. 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- 버전: 1단계 BE v0.40.0 · 2단계 FE v0.29.0 · 3단계 BE v0.40.1 + FE v0.29.1.

---

## File Structure

**1단계 — backend (신규 `backend/apps/verdict/`)**

| 파일 | 책임 |
|---|---|
| `domain/entities/region_industry_verdict_entity.py` | `SignalResult`·`RegionIndustryVerdict` dataclass, 코드 상수, `SIGNAL_KEYS`, `EXCLUDED_INDUSTRIES` |
| `domain/errors.py` | `IndustryNotFoundError` |
| `domain/services/thresholds.py` | `VerdictThresholds`(상수 5개), `percentile_rank`, `level_of` |
| `domain/services/signals.py` | `SignalInput`, `Signal(ABC)`, 신호 5개 클래스, `SIGNALS` 튜플 |
| `domain/services/rules.py` | `VerdictRule(ABC)` 4개, `judge`, `strong_count`, `on_count` |
| `app/dtos/region_industry_verdict_dto.py` | 응답 DTO 3종 + 게이트웨이 출력 DTO 4종 |
| `app/ports/input/region_industry_verdict_use_case.py` | `RegionIndustryVerdictUseCase` |
| `app/ports/output/region_industry_verdict_port.py` | Repository·StoreSignalStats·RegionContext·IndustryCatalog 4포트 |
| `app/use_cases/region_industry_verdict_interactor.py` | `build(today)`·`list_verdict_values`·`find`·`myself` |
| `adapter/outbound/orms/region_industry_verdict_orm.py` | 테이블 `region_industry_verdict` |
| `adapter/outbound/orm_mappers/region_industry_verdict_orm_mapper.py` | entity ↔ ORM (signals ↔ JSON) |
| `adapter/outbound/repositories/region_industry_verdict_repository.py` | upsert·list_by_industry·find |
| `adapter/outbound/gateways/store_signal_stats_gateway.py` | store ORM 집계 1쿼리 |
| `adapter/outbound/gateways/region_context_gateway.py` | region_profile·commerce_change·baseline·metric·region ORM |
| `adapter/outbound/gateways/industry_catalog_gateway.py` | industry ORM − 제외 4종 |
| `adapter/inbound/api/schemas/region_industry_verdict_schema.py` | pydantic 응답 3종 |
| `adapter/inbound/mappers/region_industry_verdict_mapper.py` | dto → schema |
| `adapter/inbound/api/v1/region_industry_verdict_router.py` | `/verdicts/myself`·`/verdicts`·`/verdicts/{region_code}` |
| `adapter/inbound/cli/build_verdicts.py` | 배치 진입점 |
| `dependencies/region_industry_verdict_dependencies.py` | Composition Root |
| `backend/migrations/versions/c9d0e1f2a3b4_region_industry_verdict.py` | 테이블 생성 |
| 수정: `backend/migrations/env.py`, `backend/main.py`, `scripts/store-collector.sh` | ORM 등록·라우터 등록·크론 한 줄 |

**2단계 — frontend**

| 파일 | 책임 |
|---|---|
| 수정 `src/shared/api/types.ts` | `VerdictCode`·`VerdictSignal`·`RegionIndustryVerdict`·`VerdictRow`, `CategoricalMetricKey`·`MapMetricKey`·`MetricAxis` 확장 |
| 신규 `src/shared/verdict.ts` | 판정 코드 순서·라벨·신호 라벨 (공통 어휘) |
| 신규 `src/features/map-explorer/lib/verdict-palette.ts` | 4범주 지도 팔레트(라이트/다크) |
| 수정 `src/features/map-explorer/api.ts` | `fetchVerdictMetrics`·`fetchVerdict` |
| 수정 `src/features/map-explorer/lib/metric-sources.ts` | `CategoricalMetricSource`에 `palette`·`order`·`labelOf`, `verdict` 엔트리 |
| 수정 `src/features/map-explorer/lib/map-state.ts` | 그룹 `verdict`(axis `industry_latest`), 라벨, `year` 미직렬화 |
| 수정 `control-bar.tsx`·`map-view.tsx`·`map-legend.tsx` | `industry_latest` 축, 범주 팔레트·라벨을 source에서 읽기 |
| 신규 `hooks/use-verdict.ts`, `components/verdict-section.tsx` | 카드 |
| 수정 `components/side-panel.tsx` | 헤더 직후 `VerdictSection` |
| 신규 `src/app/api/mock/verdicts/route.ts`, `verdicts/[regionCode]/route.ts`, 수정 `fixtures.ts` | mock 미러 |

**3단계 — 폐업 마커**

| 파일 | 책임 |
|---|---|
| 수정 backend `store` BC: `app/ports/output/store_port.py`, `adapter/outbound/repositories/store_repository.py`, `app/ports/input/store_use_case.py`, `app/use_cases/store_interactor.py`, `domain/errors.py`, `adapter/inbound/api/v1/store_router.py`, `adapter/inbound/api/schemas/store_schema.py`, `adapter/inbound/mappers/store_mapper.py` | `status=open|closed`, `close_date` |
| 수정 frontend `types.ts`(`Store.close_date`), `api.ts`(`fetchStores` status), `marker-strategies.ts`(`CLOSED_STORE_STRATEGY`), `region-markers.tsx`(전략·소스·색 파라미터화), `map-view.tsx`·`map-page.tsx`·`side-panel.tsx`(토글·건수), mock `stores/route.ts`·`fixtures.ts` | 폐업 레이어 |

---

## 1단계 — 백엔드 verdict BC (BE v0.40.0)

### Task 1: 엔티티·임계값·백분위

**Files:**
- Create: `backend/apps/verdict/__init__.py`, `backend/apps/verdict/domain/__init__.py`, `backend/apps/verdict/domain/entities/__init__.py`, `backend/apps/verdict/domain/services/__init__.py` (전부 빈 파일)
- Create: `backend/apps/verdict/domain/entities/region_industry_verdict_entity.py`
- Create: `backend/apps/verdict/domain/errors.py`
- Create: `backend/apps/verdict/domain/services/thresholds.py`
- Test: `backend/tests/test_verdict_thresholds.py`

**Interfaces:**
- Produces: `SignalResult(key, level, value, percentile, evidence, source)`, `RegionIndustryVerdict(region_code, industry_id, verdict_code, strong_count, on_count, signals, computed_at)`, 상수 `LEVEL_*`·`VERDICT_*`·`SIGNAL_KEYS`·`EXCLUDED_INDUSTRIES`, `VerdictThresholds`, `DEFAULT_THRESHOLDS`, `percentile_rank(value, distribution) -> float`, `level_of(percentile, thresholds) -> str`, `IndustryNotFoundError`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# backend/tests/test_verdict_thresholds.py
"""판정 임계값 — 백분위는 strict, 75/90 경계, 상수는 dataclass 한 곳."""

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    EXCLUDED_INDUSTRIES,
    LEVEL_OFF,
    LEVEL_ON,
    LEVEL_STRONG,
    SIGNAL_KEYS,
)
from apps.verdict.domain.services.thresholds import (
    DEFAULT_THRESHOLDS,
    VerdictThresholds,
    level_of,
    percentile_rank,
)


def test_백분위는_값보다_작은_동의_비율이다_strict():
    distribution = [1.0, 2.0, 3.0, 4.0]
    assert percentile_rank(3.0, distribution) == 50.0  # 1,2 두 개가 작다
    assert percentile_rank(0.5, distribution) == 0.0
    assert percentile_rank(9.0, distribution) == 100.0


def test_동률이_많은_이진값은_전부_켜지지_않는다():
    distribution = [1.0] * 10
    assert percentile_rank(1.0, distribution) == 0.0


def test_빈_분포는_0이다():
    assert percentile_rank(5.0, []) == 0.0


def test_레벨_경계_75_90():
    t = DEFAULT_THRESHOLDS
    assert level_of(74.9, t) == LEVEL_OFF
    assert level_of(75.0, t) == LEVEL_ON
    assert level_of(89.9, t) == LEVEL_ON
    assert level_of(90.0, t) == LEVEL_STRONG


def test_기본_임계값_상수():
    assert DEFAULT_THRESHOLDS == VerdictThresholds(
        on_percentile=75.0, strong_percentile=90.0, min_sample=10, min_population=1000, min_evaluable=3
    )


def test_신호_키_순서와_제외_업종():
    assert SIGNAL_KEYS == ("net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking")
    assert EXCLUDED_INDUSTRIES == frozenset({"academy", "childcare", "restaurant_other", "chicken"})
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_thresholds.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.verdict'`

- [ ] **Step 3: 엔티티·오류·임계값 구현**

```python
# backend/apps/verdict/domain/entities/region_industry_verdict_entity.py
"""verdict BC 엔티티 — 동×업종 판정 1행 (설계서 §4-2). 순수 파이썬, 프레임워크 import 없음."""

from dataclasses import dataclass
from datetime import datetime

# 신호 순서 = signals_json 순서 = 카드 표시 순서 (설계서 §3-1)
SIGNAL_KEYS: tuple[str, ...] = ("net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking")

LEVEL_OFF = "off"
LEVEL_ON = "on"
LEVEL_STRONG = "strong"
LEVEL_UNAVAILABLE = "unavailable"

VERDICT_RED = "red"
VERDICT_ORANGE = "orange"
VERDICT_CLEAR = "clear"
VERDICT_INSUFFICIENT = "insufficient"

# 판정 대상에서 빼는 업종 — 학원·어린이집(HANDOFF §0-11 보조축), 기타(비노출), 치킨(2017-09 이후 신규 인허가 없음).
# 프론트 `shared/industries.ts`의 INDUSTRIES 14종과 같은 집합이어야 한다.
EXCLUDED_INDUSTRIES: frozenset[str] = frozenset({"academy", "childcare", "restaurant_other", "chicken"})


@dataclass(frozen=True)
class SignalResult:
    key: str  # SIGNAL_KEYS 중 하나
    level: str  # off | on | strong | unavailable
    value: float | None  # 원값. unavailable이면 None
    percentile: float | None  # 나쁜 방향 백분위 0~100. 이진 신호·unavailable은 None
    evidence: str  # 근거 한 문장 (설계서 §3-4)
    source: str  # store | metric | neighborhood


@dataclass(frozen=True)
class RegionIndustryVerdict:
    region_code: str
    industry_id: str
    verdict_code: str  # red | orange | clear | insufficient
    strong_count: int
    on_count: int  # on + strong
    signals: tuple[SignalResult, ...]  # 항상 5개, SIGNAL_KEYS 순서
    computed_at: datetime
```

```python
# backend/apps/verdict/domain/errors.py
"""verdict BC 도메인 예외 — 라우터가 잡아 404 에러 바디로 변환한다."""


class IndustryNotFoundError(Exception):
    """판정 대상 업종이 아니다 (마스터 미등록이거나 EXCLUDED_INDUSTRIES)."""
```

```python
# backend/apps/verdict/domain/services/thresholds.py
"""판정 임계값 — 상수는 백분위 두 개와 표본 가드뿐이고, 실제 경계값(예: 한식 순유출 75백분위 = 0.083)은
배치마다 그 분포에서 다시 나온다. 어디에도 절대값을 하드코딩하지 않는다 (설계서 §3-2, typology.py 원칙)."""

from collections.abc import Sequence
from dataclasses import dataclass

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_OFF,
    LEVEL_ON,
    LEVEL_STRONG,
)


@dataclass(frozen=True)
class VerdictThresholds:
    on_percentile: float = 75.0
    strong_percentile: float = 90.0
    min_sample: int = 10  # 순유출 시작 점포·코호트·폐업 건수 가드
    min_population: int = 1000  # 포화 분모(상주인구) 가드
    min_evaluable: int = 3  # 판정 가능한 신호가 이보다 적으면 보류


DEFAULT_THRESHOLDS = VerdictThresholds()


def percentile_rank(value: float, distribution: Sequence[float]) -> float:
    """value보다 작은 값의 비율 × 100 (strict). 동률이 많아도 전부 켜지지 않는다."""
    if not distribution:
        return 0.0
    below = sum(1 for other in distribution if other < value)
    return below / len(distribution) * 100.0


def level_of(percentile: float, thresholds: VerdictThresholds) -> str:
    """백분위 → 레벨. 순서 비교라 조건문이 맞다 (타입·상태 분기가 아니다)."""
    if percentile >= thresholds.strong_percentile:
        return LEVEL_STRONG
    if percentile >= thresholds.on_percentile:
        return LEVEL_ON
    return LEVEL_OFF
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_thresholds.py -q`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/apps/verdict backend/tests/test_verdict_thresholds.py
git commit -m "verdict: 엔티티·임계값·strict 백분위 (설계서 §3-2, §4-2)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

### Task 2: 신호 5개 (Specification)

**Files:**
- Create: `backend/apps/verdict/domain/services/signals.py`
- Test: `backend/tests/test_verdict_signals.py`

**Interfaces:**
- Consumes: Task 1의 `SignalResult`, `LEVEL_*`, `VerdictThresholds`, `percentile_rank`, `level_of`
- Produces: `SignalInput` dataclass, `Signal(ABC)` with `key`·`source`·`raw_value(i, t)`·`worse(value)`·`evidence(i, value, percentile)`·`unavailable_reason(i, t)`·`evaluate(i, t, distribution) -> SignalResult`, 클래스 `NetOutflowSignal`·`SurvivalCliffSignal`·`EarlyClosureSignal`·`SaturationSignal`·`ShrinkingSignal`, 튜플 `SIGNALS`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# backend/tests/test_verdict_signals.py
"""신호 5개 — 값·가드·나쁜 방향·근거 문장 (설계서 §3-1, §3-4)."""

import pytest

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_OFF,
    LEVEL_ON,
    LEVEL_STRONG,
    LEVEL_UNAVAILABLE,
    SIGNAL_KEYS,
)
from apps.verdict.domain.services.signals import (
    SIGNALS,
    EarlyClosureSignal,
    NetOutflowSignal,
    SaturationSignal,
    ShrinkingSignal,
    SignalInput,
    SurvivalCliffSignal,
)
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS as T


def _input(**overrides) -> SignalInput:
    base = dict(
        region_code="1168064000", industry_id="korean_food", industry_name="한식",
        start_store_count=100, opened_12m=28, closed_12m=41,
        cohort_size=37, cohort_survived=14,
        closed_3y_count=60, closed_3y_median_months=19.0,
        latest_store_count=94, resident_total=10_000,
        change_code="HL", change_name="상권축소", change_quarter="20262",
        closed_months=20.0, seoul_closed_months=27.0,
    )
    base.update(overrides)
    return SignalInput(**base)


def test_신호_순서와_키가_엔티티_상수와_같다():
    assert tuple(s.key for s in SIGNALS) == SIGNAL_KEYS


def test_순유출은_폐업에서_개업을_빼_시작_점포수로_나눈다():
    signal = NetOutflowSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(0.13)
    assert signal.worse(0.13) == 0.13  # 높을수록 나쁨


def test_순유출_시작_점포_10_미만이면_미판정():
    result = NetOutflowSignal().evaluate(_input(start_store_count=9), T, [0.1, 0.2])
    assert result.level == LEVEL_UNAVAILABLE
    assert result.value is None and result.percentile is None
    assert "표본 부족" in result.evidence and "9곳" in result.evidence


def test_생존율은_낮을수록_나쁘다_부호_반전():
    signal = SurvivalCliffSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(14 / 37)
    assert signal.worse(0.38) == -0.38


def test_생존_코호트_10_미만이면_미판정():
    assert SurvivalCliffSignal().raw_value(_input(cohort_size=9), T) is None


def test_조기폐업은_중위_개월이_낮을수록_나쁘다():
    signal = EarlyClosureSignal()
    assert signal.raw_value(_input(), T) == 19.0
    assert signal.worse(19.0) == -19.0
    assert signal.raw_value(_input(closed_3y_count=9), T) is None
    assert signal.raw_value(_input(closed_3y_median_months=None), T) is None


def test_포화는_상주인구_천명당_점포수():
    signal = SaturationSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(9.4)
    assert signal.raw_value(_input(resident_total=999), T) is None
    assert signal.raw_value(_input(resident_total=None), T) is None
    assert signal.raw_value(_input(latest_store_count=None), T) is None


def test_백분위로_레벨이_정해지고_근거_문장에_숫자와_비교_기준이_들어간다():
    distribution = [float(i) / 100 for i in range(20)]  # 0.00 ~ 0.19
    result = NetOutflowSignal().evaluate(_input(), T, distribution)  # 0.13 → 13개가 작다 → 65
    assert result.level == LEVEL_OFF
    assert result.percentile == 65.0
    assert "폐업 41곳" in result.evidence and "개업 28곳" in result.evidence
    assert "서울 한식 상위 35%" in result.evidence
    strong = NetOutflowSignal().evaluate(_input(closed_12m=60), T, distribution)  # 0.32 → 100
    assert strong.level == LEVEL_STRONG


def test_상권축소는_이진이고_서울보다_빨리_닫히면_strong():
    signal = ShrinkingSignal()
    assert signal.evaluate(_input(), T, []).level == LEVEL_STRONG  # HL + 20 < 27
    assert signal.evaluate(_input(closed_months=30.0), T, []).level == LEVEL_ON
    assert signal.evaluate(_input(change_code="HH", change_name="정체"), T, []).level == LEVEL_OFF
    missing = signal.evaluate(_input(change_code=None, change_name=None, change_quarter=None), T, [])
    assert missing.level == LEVEL_UNAVAILABLE
    on = signal.evaluate(_input(closed_months=None), T, [])
    assert on.level == LEVEL_ON and on.percentile is None
    assert "2026년 2분기" in on.evidence and "동 전체 기준" in on.evidence
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_signals.py -q`
Expected: FAIL — `ModuleNotFoundError: ... signals`

- [ ] **Step 3: 신호 구현**

```python
# backend/apps/verdict/domain/services/signals.py
"""신호 5개 — Specification 패턴 (CLAUDE.md §5). 신호 하나 = 클래스 하나, 새 신호는 클래스 추가로 끝난다.
값·가드·나쁜 방향·근거 문장은 신호가 스스로 안다. 백분위 분포는 인터랙터가 업종별로 넘긴다 (설계서 §3)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_OFF,
    LEVEL_ON,
    LEVEL_STRONG,
    LEVEL_UNAVAILABLE,
    SignalResult,
)
from apps.verdict.domain.services.thresholds import VerdictThresholds, level_of, percentile_rank

_SHRINKING_CODE = "HL"  # 서울시 상권변화지표 '상권축소'


@dataclass(frozen=True)
class SignalInput:
    """동×업종 하나의 신호 입력 — 게이트웨이 출력을 인터랙터가 합쳐 만든다."""

    region_code: str
    industry_id: str
    industry_name: str
    # store 집계 (StoreSignalStatsPort)
    start_store_count: int  # 12개월 전 시점 영업중
    opened_12m: int
    closed_12m: int
    cohort_size: int  # 3~4년 전 개업
    cohort_survived: int  # 그중 3년 생존
    closed_3y_count: int
    closed_3y_median_months: float | None
    # 동 맥락 (RegionContextPort)
    latest_store_count: int | None  # region_industry_metric 최신 연도
    resident_total: int | None  # region_profile_quarter 최신 분기
    change_code: str | None  # HH | HL | LH | LL
    change_name: str | None
    change_quarter: str | None  # '20262'
    closed_months: float | None
    seoul_closed_months: float | None


def _top(percentile: float) -> int:
    """'서울 상위 N%' 표기 — 백분위 65 → 상위 35%. 0%는 말이 안 되니 최소 1."""
    return max(1, round(100 - percentile))


def _quarter_label(year_quarter: str | None) -> str:
    return f"{year_quarter[:4]}년 {year_quarter[4]}분기" if year_quarter else "분기 미상"


class Signal(ABC):
    key: str
    source: str

    @abstractmethod
    def raw_value(self, i: SignalInput, t: VerdictThresholds) -> float | None:
        """신호 원값. 표본 가드 미달이면 None (→ unavailable)."""

    @abstractmethod
    def worse(self, value: float) -> float:
        """나쁜 방향이 커지도록 부호를 맞춘 값 — 백분위는 이 값으로 낸다."""

    @abstractmethod
    def evidence(self, i: SignalInput, value: float, percentile: float) -> str:
        """근거 한 문장 — 숫자와 비교 기준을 반드시 넣는다 (설계서 §3-4)."""

    @abstractmethod
    def unavailable_reason(self, i: SignalInput, t: VerdictThresholds) -> str:
        """미판정 사유 문장."""

    def evaluate(self, i: SignalInput, t: VerdictThresholds, distribution: Sequence[float]) -> SignalResult:
        value = self.raw_value(i, t)
        if value is None:
            return SignalResult(self.key, LEVEL_UNAVAILABLE, None, None, self.unavailable_reason(i, t), self.source)
        percentile = percentile_rank(self.worse(value), distribution)
        return SignalResult(
            self.key, level_of(percentile, t), value, round(percentile, 1),
            self.evidence(i, value, percentile), self.source,
        )


class NetOutflowSignal(Signal):
    key = "net_outflow"
    source = "store"

    def raw_value(self, i, t):
        if i.start_store_count < t.min_sample:
            return None
        return (i.closed_12m - i.opened_12m) / i.start_store_count

    def worse(self, value):
        return value

    def evidence(self, i, value, percentile):
        return (
            f"지난 12개월 폐업 {i.closed_12m}곳, 개업 {i.opened_12m}곳 "
            f"(순유출률 {value * 100:+.0f}%, 서울 {i.industry_name} 상위 {_top(percentile)}%)"
        )

    def unavailable_reason(self, i, t):
        return f"표본 부족 — 12개월 전 영업 점포 {i.start_store_count}곳 ({t.min_sample}곳 미만)"


class SurvivalCliffSignal(Signal):
    key = "survival_cliff"
    source = "store"

    def raw_value(self, i, t):
        if i.cohort_size < t.min_sample:
            return None
        return i.cohort_survived / i.cohort_size

    def worse(self, value):
        return -value  # 낮을수록 나쁨

    def evidence(self, i, value, percentile):
        return (
            f"3년 전 개업한 {i.industry_name} {i.cohort_size}곳 중 {i.cohort_survived}곳만 남음 "
            f"(생존율 {value * 100:.0f}%, 서울 {i.industry_name} 하위 {_top(percentile)}%)"
        )

    def unavailable_reason(self, i, t):
        return f"표본 부족 — 3년 전 개업 코호트 {i.cohort_size}곳 ({t.min_sample}곳 미만)"


class EarlyClosureSignal(Signal):
    key = "early_closure"
    source = "store"

    def raw_value(self, i, t):
        if i.closed_3y_count < t.min_sample or i.closed_3y_median_months is None:
            return None
        return i.closed_3y_median_months

    def worse(self, value):
        return -value  # 짧을수록 나쁨

    def evidence(self, i, value, percentile):
        return (
            f"최근 3년 폐업 {i.industry_name}의 영업 기간 중위 {value:.0f}개월 "
            f"(서울 {i.industry_name} 하위 {_top(percentile)}%)"
        )

    def unavailable_reason(self, i, t):
        return f"표본 부족 — 최근 3년 폐업 {i.closed_3y_count}곳 ({t.min_sample}곳 미만)"


class SaturationSignal(Signal):
    key = "saturation"
    source = "metric"

    def raw_value(self, i, t):
        if i.resident_total is None or i.resident_total < t.min_population or i.latest_store_count is None:
            return None
        return i.latest_store_count / (i.resident_total / 1000)

    def worse(self, value):
        return value

    def evidence(self, i, value, percentile):
        return f"상주인구 1,000명당 {i.industry_name} {value:.1f}곳 (서울 상위 {_top(percentile)}%)"

    def unavailable_reason(self, i, t):
        if i.latest_store_count is None:
            return "최신 연도 점포수 지표 없음"
        return f"상주인구 {i.resident_total or 0:,}명 ({t.min_population:,}명 미만이거나 프로필 없음)"


class ShrinkingSignal(Signal):
    """동 단위 이진 신호 — 백분위를 쓰지 않으므로 evaluate를 통째로 재정의한다."""

    key = "shrinking"
    source = "neighborhood"

    def raw_value(self, i, t):
        if i.change_code is None:
            return None
        return 1.0 if i.change_code == _SHRINKING_CODE else 0.0

    def worse(self, value):
        return value

    def evidence(self, i, value, percentile):
        return f"서울시 상권변화지표 '{i.change_name}' ({_quarter_label(i.change_quarter)}, 동 전체 기준)"

    def unavailable_reason(self, i, t):
        return "상권변화지표 없음 (해당 동·분기 행 없음)"

    def evaluate(self, i, t, distribution):
        value = self.raw_value(i, t)
        if value is None:
            return SignalResult(self.key, LEVEL_UNAVAILABLE, None, None, self.unavailable_reason(i, t), self.source)
        level = LEVEL_OFF
        if value == 1.0:
            faster_than_seoul = (
                i.closed_months is not None and i.seoul_closed_months is not None
                and i.closed_months < i.seoul_closed_months
            )
            level = LEVEL_STRONG if faster_than_seoul else LEVEL_ON
        return SignalResult(self.key, level, value, None, self.evidence(i, value, 0.0), self.source)


SIGNALS: tuple[Signal, ...] = (
    NetOutflowSignal(),
    SurvivalCliffSignal(),
    EarlyClosureSignal(),
    SaturationSignal(),
    ShrinkingSignal(),
)
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_signals.py tests/test_verdict_thresholds.py -q`
Expected: 15 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/apps/verdict/domain/services/signals.py backend/tests/test_verdict_signals.py
git commit -m "verdict: 공통 신호 5개 Specification — 순유출·생존 절벽·조기 폐업·포화·상권 축소 (설계서 §3-1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

### Task 3: 판정 규칙 (Chain of Responsibility)

**Files:**
- Create: `backend/apps/verdict/domain/services/rules.py`
- Test: `backend/tests/test_verdict_rules.py`

**Interfaces:**
- Consumes: Task 1 `SignalResult`, `LEVEL_*`, `VERDICT_*`, `VerdictThresholds`
- Produces: `judge(results, t) -> str`, `strong_count(results) -> int`, `on_count(results) -> int`, `evaluable_count(results) -> int`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# backend/tests/test_verdict_rules.py
"""판정 규칙 — 보류 우선, red/orange/clear (설계서 §3-3)."""

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_OFF,
    LEVEL_ON,
    LEVEL_STRONG,
    LEVEL_UNAVAILABLE,
    VERDICT_CLEAR,
    VERDICT_INSUFFICIENT,
    VERDICT_ORANGE,
    VERDICT_RED,
    SignalResult,
)
from apps.verdict.domain.services.rules import judge, on_count, strong_count
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS as T


def _results(*levels: str) -> tuple[SignalResult, ...]:
    return tuple(
        SignalResult(key=f"s{i}", level=lv, value=None, percentile=None, evidence="", source="store")
        for i, lv in enumerate(levels)
    )


def test_강한_신호_2개면_red():
    assert judge(_results(LEVEL_STRONG, LEVEL_STRONG, LEVEL_OFF, LEVEL_OFF, LEVEL_OFF), T) == VERDICT_RED


def test_켜진_신호_1개면_orange_강한_1개도_orange():
    assert judge(_results(LEVEL_ON, LEVEL_OFF, LEVEL_OFF, LEVEL_OFF, LEVEL_OFF), T) == VERDICT_ORANGE
    assert judge(_results(LEVEL_STRONG, LEVEL_ON, LEVEL_OFF, LEVEL_OFF, LEVEL_OFF), T) == VERDICT_ORANGE


def test_켜진_신호_없으면_clear():
    assert judge(_results(LEVEL_OFF, LEVEL_OFF, LEVEL_OFF, LEVEL_OFF, LEVEL_UNAVAILABLE), T) == VERDICT_CLEAR


def test_판정_가능_신호_3개_미만이면_강한_신호가_2개여도_보류():
    levels = (LEVEL_STRONG, LEVEL_STRONG, LEVEL_UNAVAILABLE, LEVEL_UNAVAILABLE, LEVEL_UNAVAILABLE)
    assert judge(_results(*levels), T) == VERDICT_INSUFFICIENT


def test_카운트():
    r = _results(LEVEL_STRONG, LEVEL_ON, LEVEL_OFF, LEVEL_UNAVAILABLE, LEVEL_STRONG)
    assert strong_count(r) == 2
    assert on_count(r) == 3  # on + strong
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_rules.py -q`
Expected: FAIL — `ModuleNotFoundError: ... rules`

- [ ] **Step 3: 규칙 구현**

```python
# backend/apps/verdict/domain/services/rules.py
"""판정 규칙 — 결정 목록 (Chain of Responsibility, CLAUDE.md §5). 첫 일치가 이긴다.
보류를 먼저 검사한다: 표본 부족 동을 ⚪로 오해하지 않기 위해 (설계서 §3-3)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_ON,
    LEVEL_STRONG,
    LEVEL_UNAVAILABLE,
    VERDICT_CLEAR,
    VERDICT_INSUFFICIENT,
    VERDICT_ORANGE,
    VERDICT_RED,
    SignalResult,
)
from apps.verdict.domain.services.thresholds import VerdictThresholds


def strong_count(results: Sequence[SignalResult]) -> int:
    return sum(1 for r in results if r.level == LEVEL_STRONG)


def on_count(results: Sequence[SignalResult]) -> int:
    return sum(1 for r in results if r.level in (LEVEL_ON, LEVEL_STRONG))


def evaluable_count(results: Sequence[SignalResult]) -> int:
    return sum(1 for r in results if r.level != LEVEL_UNAVAILABLE)


class VerdictRule(ABC):
    @abstractmethod
    def judge(self, results: Sequence[SignalResult], t: VerdictThresholds) -> str | None:
        """판정되면 코드, 아니면 None을 반환해 다음 규칙에 넘긴다."""


class InsufficientRule(VerdictRule):
    def judge(self, results, t):
        return VERDICT_INSUFFICIENT if evaluable_count(results) < t.min_evaluable else None


class RedRule(VerdictRule):
    def judge(self, results, t):
        return VERDICT_RED if strong_count(results) >= 2 else None


class OrangeRule(VerdictRule):
    def judge(self, results, t):
        return VERDICT_ORANGE if on_count(results) >= 1 else None


class ClearRule(VerdictRule):
    def judge(self, results, t):
        return VERDICT_CLEAR


RULES: tuple[VerdictRule, ...] = (InsufficientRule(), RedRule(), OrangeRule(), ClearRule())


def judge(results: Sequence[SignalResult], t: VerdictThresholds) -> str:
    for rule in RULES:
        verdict = rule.judge(results, t)
        if verdict is not None:
            return verdict
    raise AssertionError("ClearRule은 항상 판정한다")
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_rules.py -q`
Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/apps/verdict/domain/services/rules.py backend/tests/test_verdict_rules.py
git commit -m "verdict: 판정 규칙 — 보류 우선·red·orange·clear (설계서 §3-3)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

### Task 4: DTO·포트·인터랙터 (Fake 포트로 build 검증)

**Files:**
- Create: `backend/apps/verdict/app/__init__.py`, `app/dtos/__init__.py`, `app/ports/__init__.py`, `app/ports/input/__init__.py`, `app/ports/output/__init__.py`, `app/use_cases/__init__.py` (빈 파일)
- Create: `backend/apps/verdict/app/dtos/region_industry_verdict_dto.py`
- Create: `backend/apps/verdict/app/ports/output/region_industry_verdict_port.py`
- Create: `backend/apps/verdict/app/ports/input/region_industry_verdict_use_case.py`
- Create: `backend/apps/verdict/app/use_cases/region_industry_verdict_interactor.py`
- Test: `backend/tests/test_verdict_build.py`

**Interfaces:**
- Consumes: Task 1~3 전부
- Produces:
  - DTO: `SignalResultDto`, `RegionIndustryVerdictDto`, `VerdictValueDto(region_code, value)`, `StoreSignalStat`, `RegionContext`, `LatestStoreCount`, `JudgedIndustry(industry_id, name)`
  - 포트: `RegionIndustryVerdictRepositoryPort.upsert(list) -> int / list_by_industry(industry_id) -> list[RegionIndustryVerdict] / find(region_code, industry_id) -> RegionIndustryVerdict | None`, `StoreSignalStatsPort.signal_stats(today: date) -> list[StoreSignalStat]`, `RegionContextPort.latest_contexts() -> list[RegionContext] / latest_store_counts() -> list[LatestStoreCount]`, `IndustryCatalogPort.judged_industries() -> list[JudgedIndustry]`
  - 유스케이스: `RegionIndustryVerdictUseCase.myself() / build(today) -> int / list_verdict_values(industry_id) -> list[VerdictValueDto] / find(region_code, industry_id) -> RegionIndustryVerdictDto | None`
  - `RegionIndustryVerdictInteractor(repository, store_stats, region_context, industry_catalog, thresholds=DEFAULT_THRESHOLDS, signals=SIGNALS)`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# backend/tests/test_verdict_build.py
"""판정 배치 — Fake 포트로 업종별 상대평가·업서트·조회 검증 (설계서 §4-4)."""

from datetime import date

import pytest

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    JudgedIndustry,
    LatestStoreCount,
    RegionContext,
    StoreSignalStat,
)
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    IndustryCatalogPort,
    RegionContextPort,
    RegionIndustryVerdictRepositoryPort,
    StoreSignalStatsPort,
)
from apps.verdict.app.use_cases.region_industry_verdict_interactor import (
    RegionIndustryVerdictInteractor,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import (
    SIGNAL_KEYS,
    VERDICT_INSUFFICIENT,
    RegionIndustryVerdict,
)
from apps.verdict.domain.errors import IndustryNotFoundError


class FakeRepository(RegionIndustryVerdictRepositoryPort):
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], RegionIndustryVerdict] = {}

    def upsert(self, verdicts):
        for v in verdicts:
            self.rows[(v.region_code, v.industry_id)] = v
        return len(verdicts)

    def list_by_industry(self, industry_id):
        return sorted((v for v in self.rows.values() if v.industry_id == industry_id), key=lambda v: v.region_code)

    def find(self, region_code, industry_id):
        return self.rows.get((region_code, industry_id))


class FakeStoreStats(StoreSignalStatsPort):
    def __init__(self, stats):
        self.stats = stats

    def signal_stats(self, today):
        return self.stats


class FakeContext(RegionContextPort):
    def __init__(self, contexts, counts):
        self.contexts, self.counts = contexts, counts

    def latest_contexts(self):
        return self.contexts

    def latest_store_counts(self):
        return self.counts


class FakeCatalog(IndustryCatalogPort):
    def judged_industries(self):
        return [JudgedIndustry("korean_food", "한식")]


def _stat(region: str, closed_12m: int) -> StoreSignalStat:
    return StoreSignalStat(
        region_code=region, industry_id="korean_food", start_store_count=100, opened_12m=10,
        closed_12m=closed_12m, cohort_size=40, cohort_survived=20, closed_3y_count=30, closed_3y_median_months=24.0,
    )


def _context(region: str, change_code: str | None = "HH") -> RegionContext:
    return RegionContext(
        region_code=region, resident_total=10_000, change_code=change_code,
        change_name=None if change_code is None else "정체", change_quarter="20262",
        closed_months=25.0, seoul_closed_months=27.0,
    )


def _interactor(stats, contexts, counts):
    repo = FakeRepository()
    return repo, RegionIndustryVerdictInteractor(
        repository=repo, store_stats=FakeStoreStats(stats),
        region_context=FakeContext(contexts, counts), industry_catalog=FakeCatalog(),
    )


def test_동_20개를_업종_안에서_상대평가해_상위_동만_켠다():
    regions = [f"11680{i:05d}" for i in range(20)]
    stats = [_stat(r, closed_12m=10 + i) for i, r in enumerate(regions)]  # 순유출률 0.00 ~ 0.19
    contexts = [_context(r) for r in regions]
    counts = [LatestStoreCount(r, "korean_food", 90) for r in regions]
    repo, interactor = _interactor(stats, contexts, counts)

    assert interactor.build(date(2026, 9, 28)) == 20

    worst = repo.find(regions[19], "korean_food")
    best = repo.find(regions[0], "korean_food")
    assert [s.key for s in worst.signals] == list(SIGNAL_KEYS)
    assert worst.signals[0].level == "strong"  # 19개보다 크다 → 95
    assert best.signals[0].level == "off"
    # 포화는 전 동 동일값 → 백분위 0 → off, 상권축소는 HH → off
    assert worst.signals[3].level == "off" and worst.signals[4].level == "off"
    assert worst.verdict_code == "orange"  # strong 1개


def test_집계가_없는_동은_표본_부족으로_보류된다():
    regions = ["1168000001", "1168000002", "1168000003"]
    repo, interactor = _interactor([], [_context(r, change_code=None) for r in regions], [])
    interactor.build(date(2026, 9, 28))
    v = repo.find(regions[0], "korean_food")
    assert v.verdict_code == VERDICT_INSUFFICIENT
    assert all(s.level == "unavailable" for s in v.signals)


def test_조회는_판정_대상_업종만_받는다():
    repo, interactor = _interactor([], [_context("1168000001")], [])
    interactor.build(date(2026, 9, 28))
    assert [v.value for v in interactor.list_verdict_values("korean_food")] == [VERDICT_INSUFFICIENT]
    assert interactor.find("1168000001", "korean_food").region_code == "1168000001"
    assert interactor.find("0000000000", "korean_food") is None
    with pytest.raises(IndustryNotFoundError):
        interactor.list_verdict_values("academy")
    with pytest.raises(IndustryNotFoundError):
        interactor.find("1168000001", "chicken")


def test_myself는_하드코딩_행을_돌려준다():
    _, interactor = _interactor([], [], [])
    me = interactor.myself()
    assert me.region_code == "myself" and len(me.signals) == 5
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_build.py -q`
Expected: FAIL — `ModuleNotFoundError: ... app.dtos`

- [ ] **Step 3: DTO·포트·유스케이스·인터랙터 구현**

```python
# backend/apps/verdict/app/dtos/region_industry_verdict_dto.py
"""verdict BC DTO — 응답용 3종 + 게이트웨이 출력 4종. 프레임워크 타입 없음."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SignalResultDto:
    key: str
    level: str
    value: float | None
    percentile: float | None
    evidence: str
    source: str


@dataclass(frozen=True)
class RegionIndustryVerdictDto:
    region_code: str
    industry_id: str
    verdict_code: str
    strong_count: int
    on_count: int
    signals: tuple[SignalResultDto, ...]
    computed_at: datetime


@dataclass(frozen=True)
class VerdictValueDto:
    """단계구분도 응답 단위 — {region_code, value: verdict_code} (범주 계약)."""

    region_code: str
    value: str


@dataclass(frozen=True)
class StoreSignalStat:
    """store 원천 집계 (동×업종). 없는 조합은 인터랙터가 0으로 채운다 → 표본 가드가 unavailable로 만든다."""

    region_code: str
    industry_id: str
    start_store_count: int
    opened_12m: int
    closed_12m: int
    cohort_size: int
    cohort_survived: int
    closed_3y_count: int
    closed_3y_median_months: float | None


@dataclass(frozen=True)
class RegionContext:
    """동 단위 맥락 — 전 행정동 1행씩 (프로필·변화지표가 없으면 None)."""

    region_code: str
    resident_total: int | None
    change_code: str | None
    change_name: str | None
    change_quarter: str | None
    closed_months: float | None
    seoul_closed_months: float | None


@dataclass(frozen=True)
class LatestStoreCount:
    region_code: str
    industry_id: str
    store_count: int


@dataclass(frozen=True)
class JudgedIndustry:
    industry_id: str
    name: str
```

```python
# backend/apps/verdict/app/ports/output/region_industry_verdict_port.py
"""Driven Ports — verdict가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from datetime import date

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    JudgedIndustry,
    LatestStoreCount,
    RegionContext,
    StoreSignalStat,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import RegionIndustryVerdict


class RegionIndustryVerdictRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, verdicts: list[RegionIndustryVerdict]) -> int:
        """(region_code, industry_id) 기준 업서트 — 처리 건수 반환."""

    @abstractmethod
    def list_by_industry(self, industry_id: str) -> list[RegionIndustryVerdict]:
        """해당 업종의 전 행정동 판정을 region_code 순으로."""

    @abstractmethod
    def find(self, region_code: str, industry_id: str) -> RegionIndustryVerdict | None:
        """복합키 단건 — 없으면 None."""


class StoreSignalStatsPort(ABC):
    @abstractmethod
    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        """store 원천에서 동×업종별 12개월 개폐업·3년 코호트·최근 3년 폐업 중위개월 (region_code 보유분만)."""


class RegionContextPort(ABC):
    @abstractmethod
    def latest_contexts(self) -> list[RegionContext]:
        """전 행정동 1행씩 — 최신 분기 상주인구·상권변화지표·서울 베이스라인."""

    @abstractmethod
    def latest_store_counts(self) -> list[LatestStoreCount]:
        """region_industry_metric 최신 연도의 동×업종 점포수."""


class IndustryCatalogPort(ABC):
    @abstractmethod
    def judged_industries(self) -> list[JudgedIndustry]:
        """판정 대상 업종 — industry 마스터 − EXCLUDED_INDUSTRIES."""
```

```python
# backend/apps/verdict/app/ports/input/region_industry_verdict_use_case.py
"""Driving Port — region_industry_verdict UseCase 인터페이스."""

from abc import ABC, abstractmethod
from datetime import date

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    RegionIndustryVerdictDto,
    VerdictValueDto,
)


class RegionIndustryVerdictUseCase(ABC):
    @abstractmethod
    def myself(self) -> RegionIndustryVerdictDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def build(self, today: date) -> int:
        """판정 대상 14업종 × 전 행정동 판정을 재계산·업서트하고 처리 건수를 반환한다 (멱등)."""

    @abstractmethod
    def list_verdict_values(self, industry_id: str) -> list[VerdictValueDto]:
        """단계구분도용 — 판정 대상이 아니면 IndustryNotFoundError."""

    @abstractmethod
    def find(self, region_code: str, industry_id: str) -> RegionIndustryVerdictDto | None:
        """카드용 단건 — 없으면 None. 판정 대상이 아니면 IndustryNotFoundError."""
```

```python
# backend/apps/verdict/app/use_cases/region_industry_verdict_interactor.py
"""Application Service — 얇은 조율: 게이트웨이 3종 → 업종별 분포 → 신호 평가 → 판정 → 업서트."""

from collections.abc import Sequence
from dataclasses import asdict
from datetime import date, datetime, timezone

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    JudgedIndustry,
    LatestStoreCount,
    RegionContext,
    RegionIndustryVerdictDto,
    SignalResultDto,
    StoreSignalStat,
    VerdictValueDto,
)
from apps.verdict.app.ports.input.region_industry_verdict_use_case import (
    RegionIndustryVerdictUseCase,
)
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    IndustryCatalogPort,
    RegionContextPort,
    RegionIndustryVerdictRepositoryPort,
    StoreSignalStatsPort,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_OFF,
    LEVEL_STRONG,
    LEVEL_UNAVAILABLE,
    VERDICT_ORANGE,
    RegionIndustryVerdict,
    SignalResult,
)
from apps.verdict.domain.errors import IndustryNotFoundError
from apps.verdict.domain.services.rules import judge, on_count, strong_count
from apps.verdict.domain.services.signals import SIGNALS, Signal, SignalInput
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS, VerdictThresholds

_EMPTY_STAT = dict(
    start_store_count=0, opened_12m=0, closed_12m=0, cohort_size=0, cohort_survived=0,
    closed_3y_count=0, closed_3y_median_months=None,
)


class RegionIndustryVerdictInteractor(RegionIndustryVerdictUseCase):
    def __init__(
        self,
        repository: RegionIndustryVerdictRepositoryPort,
        store_stats: StoreSignalStatsPort,
        region_context: RegionContextPort,
        industry_catalog: IndustryCatalogPort,
        thresholds: VerdictThresholds = DEFAULT_THRESHOLDS,
        signals: Sequence[Signal] = SIGNALS,
    ) -> None:
        self._repository = repository
        self._store_stats = store_stats
        self._region_context = region_context
        self._industry_catalog = industry_catalog
        self._thresholds = thresholds
        self._signals = tuple(signals)

    def myself(self) -> RegionIndustryVerdictDto:
        signals = tuple(
            SignalResultDto(key=s.key, level=LEVEL_STRONG if i == 0 else LEVEL_OFF, value=0.13 if i == 0 else 0.0,
                            percentile=95.0 if i == 0 else 10.0, evidence="배선 검증", source=s.source)
            for i, s in enumerate(self._signals)
        )
        return RegionIndustryVerdictDto(
            region_code="myself", industry_id="korean_food", verdict_code=VERDICT_ORANGE,
            strong_count=1, on_count=1, signals=signals, computed_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
        )

    def build(self, today: date) -> int:
        industries = self._industry_catalog.judged_industries()
        stats = {(s.region_code, s.industry_id): s for s in self._store_stats.signal_stats(today)}
        counts = {(c.region_code, c.industry_id): c.store_count for c in self._region_context.latest_store_counts()}
        contexts = self._region_context.latest_contexts()
        computed_at = datetime.now(timezone.utc)
        verdicts: list[RegionIndustryVerdict] = []
        for industry in industries:
            inputs = [self._input(ctx, industry, stats, counts) for ctx in contexts]
            verdicts.extend(self._judge_industry(inputs, computed_at))
        return self._repository.upsert(verdicts)

    def list_verdict_values(self, industry_id: str) -> list[VerdictValueDto]:
        self._require_judged(industry_id)
        return [VerdictValueDto(v.region_code, v.verdict_code) for v in self._repository.list_by_industry(industry_id)]

    def find(self, region_code: str, industry_id: str) -> RegionIndustryVerdictDto | None:
        self._require_judged(industry_id)
        entity = self._repository.find(region_code, industry_id)
        return None if entity is None else _to_dto(entity)

    # --- 내부 ---

    def _require_judged(self, industry_id: str) -> None:
        if industry_id not in {i.industry_id for i in self._industry_catalog.judged_industries()}:
            raise IndustryNotFoundError(industry_id)

    @staticmethod
    def _input(ctx: RegionContext, industry: JudgedIndustry, stats, counts) -> SignalInput:
        stat = stats.get((ctx.region_code, industry.industry_id))
        stat_fields = {k: getattr(stat, k) for k in _EMPTY_STAT} if stat else dict(_EMPTY_STAT)
        return SignalInput(
            region_code=ctx.region_code, industry_id=industry.industry_id, industry_name=industry.name,
            latest_store_count=counts.get((ctx.region_code, industry.industry_id)),
            resident_total=ctx.resident_total, change_code=ctx.change_code, change_name=ctx.change_name,
            change_quarter=ctx.change_quarter, closed_months=ctx.closed_months,
            seoul_closed_months=ctx.seoul_closed_months, **stat_fields,
        )

    def _judge_industry(self, inputs: list[SignalInput], computed_at: datetime) -> list[RegionIndustryVerdict]:
        t = self._thresholds
        results: dict[str, list[SignalResult]] = {i.region_code: [] for i in inputs}
        for signal in self._signals:
            # 업종 안에서 가드를 통과한 동만 분포에 넣는다 (설계서 §3-2)
            distribution = [signal.worse(v) for i in inputs if (v := signal.raw_value(i, t)) is not None]
            for i in inputs:
                results[i.region_code].append(signal.evaluate(i, t, distribution))
        verdicts = []
        for i in inputs:
            r = tuple(results[i.region_code])
            verdicts.append(RegionIndustryVerdict(
                region_code=i.region_code, industry_id=i.industry_id, verdict_code=judge(r, t),
                strong_count=strong_count(r), on_count=on_count(r), signals=r, computed_at=computed_at,
            ))
        return verdicts


def _to_dto(entity: RegionIndustryVerdict) -> RegionIndustryVerdictDto:
    return RegionIndustryVerdictDto(
        region_code=entity.region_code, industry_id=entity.industry_id, verdict_code=entity.verdict_code,
        strong_count=entity.strong_count, on_count=entity.on_count,
        signals=tuple(SignalResultDto(**asdict(s)) for s in entity.signals), computed_at=entity.computed_at,
    )
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_build.py -q`
Expected: 4 passed (`LEVEL_UNAVAILABLE` 미사용 경고가 있으면 import에서 제거)

- [ ] **Step 5: 커밋**

```bash
git add backend/apps/verdict/app backend/tests/test_verdict_build.py
git commit -m "verdict: DTO·포트 4종·인터랙터 — 업종별 분포로 신호 평가·판정·업서트 (설계서 §4-4)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

### Task 5: ORM·마이그레이션·리포지토리

**Files:**
- Create: `backend/apps/verdict/adapter/__init__.py`, `adapter/outbound/__init__.py`, `adapter/outbound/orms/__init__.py`, `adapter/outbound/orm_mappers/__init__.py`, `adapter/outbound/repositories/__init__.py`, `adapter/outbound/gateways/__init__.py` (빈 파일)
- Create: `backend/apps/verdict/adapter/outbound/orms/region_industry_verdict_orm.py`
- Create: `backend/apps/verdict/adapter/outbound/orm_mappers/region_industry_verdict_orm_mapper.py`
- Create: `backend/apps/verdict/adapter/outbound/repositories/region_industry_verdict_repository.py`
- Create: `backend/migrations/versions/c9d0e1f2a3b4_region_industry_verdict.py`
- Modify: `backend/migrations/env.py:44` (ORM import 한 줄 추가)
- Test: `backend/tests/test_verdict_repository.py`

**Interfaces:**
- Consumes: Task 1 `RegionIndustryVerdict`·`SignalResult`, Task 4 `RegionIndustryVerdictRepositoryPort`
- Produces: `RegionIndustryVerdictOrm`, `to_orm(entity)`, `to_entity(orm)`, `SqlAlchemyRegionIndustryVerdictRepository`

- [ ] **Step 1: 실패하는 테스트 작성** (테스트 DB — `conftest.py`가 alembic head까지 올린다)

```python
# backend/tests/test_verdict_repository.py
"""판정 리포지토리 — 업서트 멱등·signals JSON 왕복·업종별 목록 (실 DB, beyondfacade_test)."""

from datetime import datetime, timezone

from sqlalchemy import delete, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.verdict.adapter.outbound.orms.region_industry_verdict_orm import RegionIndustryVerdictOrm
from apps.verdict.adapter.outbound.repositories.region_industry_verdict_repository import (
    SqlAlchemyRegionIndustryVerdictRepository,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import (
    RegionIndustryVerdict,
    SignalResult,
)
from core.matrix.grid_oracle_database_manager import session_scope

_INDUSTRY = "korean_food"


def _two_region_codes() -> list[str]:
    with session_scope() as session:
        return session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(2)).scalars().all()


def _verdict(region_code: str, code: str) -> RegionIndustryVerdict:
    signals = tuple(
        SignalResult(key=k, level="on" if k == "net_outflow" else "off", value=0.1, percentile=80.0,
                     evidence=f"{k} 근거 — 한글 포함", source="store")
        for k in ("net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking")
    )
    return RegionIndustryVerdict(region_code, _INDUSTRY, code, 0, 1, signals, datetime(2026, 9, 28, 4, 30, tzinfo=timezone.utc))


def _cleanup(region_codes: list[str]) -> None:
    with session_scope() as session:
        session.execute(delete(RegionIndustryVerdictOrm).where(RegionIndustryVerdictOrm.region_code.in_(region_codes)))


def test_업서트는_멱등이고_signals가_JSON으로_왕복된다():
    codes = _two_region_codes()
    repo = SqlAlchemyRegionIndustryVerdictRepository()
    try:
        assert repo.upsert([_verdict(codes[0], "orange"), _verdict(codes[1], "clear")]) == 2
        assert repo.upsert([_verdict(codes[0], "red")]) == 1  # 같은 키 → 덮어씀
        found = repo.find(codes[0], _INDUSTRY)
        assert found.verdict_code == "red"
        assert [s.key for s in found.signals][0] == "net_outflow"
        assert found.signals[0].evidence == "net_outflow 근거 — 한글 포함"
        assert found.signals[0].level == "on"
        assert repo.find("0000000000", _INDUSTRY) is None
        listed = repo.list_by_industry(_INDUSTRY)
        assert [v.region_code for v in listed if v.region_code in codes] == sorted(codes)
    finally:
        _cleanup(codes)
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_repository.py -q`
Expected: FAIL — `ModuleNotFoundError: ... orms.region_industry_verdict_orm`

- [ ] **Step 3: ORM·마이그레이션·매퍼·리포지토리 구현**

```python
# backend/apps/verdict/adapter/outbound/orms/region_industry_verdict_orm.py
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionIndustryVerdictOrm(OrmBase):
    """행정동×업종 판정 1행 — 새벽 배치 재생성 (설계서 §4-3).
    signals_json은 카드가 통째로 읽고 질의 축이 아니라 열로 풀지 않는다(명시적 역정규화)."""

    __tablename__ = "region_industry_verdict"
    __table_args__ = (
        # 단계구분도 조회(GET /verdicts?industry=)가 업종으로 전 행정동을 훑는다
        Index("ix_region_industry_verdict_industry", "industry_id"),
    )

    region_code: Mapped[str] = mapped_column(ForeignKey("region.region_code"), primary_key=True)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industry.industry_id"), primary_key=True)
    verdict_code: Mapped[str] = mapped_column(String(12))  # red | orange | clear | insufficient
    strong_count: Mapped[int] = mapped_column(SmallInteger)
    on_count: Mapped[int] = mapped_column(SmallInteger)
    signals_json: Mapped[str] = mapped_column(Text)  # SignalResult 5개 JSON 배열
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

```python
# backend/migrations/versions/c9d0e1f2a3b4_region_industry_verdict.py
"""판정 테이블 region_industry_verdict

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-09-29 00:00:00.000000

설계서 `docs/superpowers/specs/2026-09-28-verdict-card-design.md` §4-3.
동×업종당 1행(판정 코드·켜진 개수·신호 JSON·산출 시각). 새벽 배치 `build_verdicts`가 재생성한다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "region_industry_verdict",
        sa.Column("region_code", sa.String(), sa.ForeignKey("region.region_code"), primary_key=True),
        sa.Column("industry_id", sa.String(), sa.ForeignKey("industry.industry_id"), primary_key=True),
        sa.Column("verdict_code", sa.String(length=12), nullable=False),
        sa.Column("strong_count", sa.SmallInteger(), nullable=False),
        sa.Column("on_count", sa.SmallInteger(), nullable=False),
        sa.Column("signals_json", sa.Text(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_region_industry_verdict_industry", "region_industry_verdict", ["industry_id"])


def downgrade() -> None:
    op.drop_index("ix_region_industry_verdict_industry", table_name="region_industry_verdict")
    op.drop_table("region_industry_verdict")
```

`backend/migrations/env.py` 44행 뒤에 한 줄 추가:

```python
import apps.verdict.adapter.outbound.orms.region_industry_verdict_orm  # noqa: F401
```

```python
# backend/apps/verdict/adapter/outbound/orm_mappers/region_industry_verdict_orm_mapper.py
"""Outbound Boundary Gate — entity ↔ ORM 변환 (signals 튜플 ↔ JSON 문자열)."""

import json
from dataclasses import asdict

from apps.verdict.adapter.outbound.orms.region_industry_verdict_orm import RegionIndustryVerdictOrm
from apps.verdict.domain.entities.region_industry_verdict_entity import (
    RegionIndustryVerdict,
    SignalResult,
)


def to_orm(entity: RegionIndustryVerdict) -> RegionIndustryVerdictOrm:
    return RegionIndustryVerdictOrm(
        region_code=entity.region_code,
        industry_id=entity.industry_id,
        verdict_code=entity.verdict_code,
        strong_count=entity.strong_count,
        on_count=entity.on_count,
        signals_json=json.dumps([asdict(s) for s in entity.signals], ensure_ascii=False),
        computed_at=entity.computed_at,
    )


def to_entity(orm: RegionIndustryVerdictOrm) -> RegionIndustryVerdict:
    return RegionIndustryVerdict(
        region_code=orm.region_code,
        industry_id=orm.industry_id,
        verdict_code=orm.verdict_code,
        strong_count=orm.strong_count,
        on_count=orm.on_count,
        signals=tuple(SignalResult(**item) for item in json.loads(orm.signals_json)),
        computed_at=orm.computed_at,
    )
```

```python
# backend/apps/verdict/adapter/outbound/repositories/region_industry_verdict_repository.py
from sqlalchemy import select

from apps.verdict.adapter.outbound.orm_mappers.region_industry_verdict_orm_mapper import (
    to_entity,
    to_orm,
)
from apps.verdict.adapter.outbound.orms.region_industry_verdict_orm import RegionIndustryVerdictOrm
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    RegionIndustryVerdictRepositoryPort,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import RegionIndustryVerdict
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyRegionIndustryVerdictRepository(RegionIndustryVerdictRepositoryPort):
    def upsert(self, verdicts: list[RegionIndustryVerdict]) -> int:
        if not verdicts:
            return 0
        with session_scope() as session:
            for verdict in verdicts:
                session.merge(to_orm(verdict))
        return len(verdicts)

    def list_by_industry(self, industry_id: str) -> list[RegionIndustryVerdict]:
        with session_scope() as session:
            rows = session.execute(
                select(RegionIndustryVerdictOrm)
                .where(RegionIndustryVerdictOrm.industry_id == industry_id)
                .order_by(RegionIndustryVerdictOrm.region_code)
            ).scalars().all()
            return [to_entity(row) for row in rows]

    def find(self, region_code: str, industry_id: str) -> RegionIndustryVerdict | None:
        with session_scope() as session:
            orm = session.get(RegionIndustryVerdictOrm, (region_code, industry_id))
            return None if orm is None else to_entity(orm)
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_repository.py -q`
Expected: 1 passed (conftest가 테스트 DB에 `c9d0e1f2a3b4`를 적용한다)

- [ ] **Step 5: 개발 DB에도 마이그레이션 적용**

Run: `cd backend && .venv/bin/alembic upgrade head && .venv/bin/alembic current`
Expected: `c9d0e1f2a3b4 (head)`

- [ ] **Step 6: 커밋**

```bash
git add backend/apps/verdict/adapter backend/migrations backend/tests/test_verdict_repository.py
git commit -m "verdict: ORM·마이그레이션 c9d0e1f2a3b4·리포지토리 — region_industry_verdict (설계서 §4-3)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

### Task 6: 게이트웨이 3개 (store 집계 · 동 맥락 · 업종 카탈로그)

**Files:**
- Create: `backend/apps/verdict/adapter/outbound/gateways/store_signal_stats_gateway.py`
- Create: `backend/apps/verdict/adapter/outbound/gateways/region_context_gateway.py`
- Create: `backend/apps/verdict/adapter/outbound/gateways/industry_catalog_gateway.py`
- Test: `backend/tests/test_verdict_gateways.py`

**Interfaces:**
- Consumes: Task 4 포트 3종·DTO, 다른 BC ORM: `apps.store...StoreOrm`, `apps.metric...RegionIndustryMetricOrm`, `apps.metric.adapter.outbound.orms.region_profile_quarter_orm.RegionProfileQuarterOrm`, `apps.neighborhood...RegionCommerceChangeOrm`, `SeoulCommerceChangeBaselineOrm`, `apps.master...RegionOrm`, `IndustryOrm`
- Produces: `StoreSignalStatsGateway`, `RegionContextGateway`, `IndustryCatalogGateway`

- [ ] **Step 1: 실패하는 테스트 작성** (실 DB, `test_metric_store_stats.py`와 같은 방식 — 미래 연도 시험행)

```python
# backend/tests/test_verdict_gateways.py
"""판정 게이트웨이 — store 집계 SQL(12개월·코호트·중위개월 경계)과 업종 카탈로그 제외 (실 DB)."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.verdict.adapter.outbound.gateways.industry_catalog_gateway import IndustryCatalogGateway
from apps.verdict.adapter.outbound.gateways.region_context_gateway import RegionContextGateway
from apps.verdict.adapter.outbound.gateways.store_signal_stats_gateway import StoreSignalStatsGateway
from apps.verdict.domain.entities.region_industry_verdict_entity import EXCLUDED_INDUSTRIES
from core.matrix.grid_oracle_database_manager import session_scope

_PREFIX = "test-verdictstats-"
_TODAY = date(2099, 6, 30)  # 실적재보다 뒤 — 시험 행만 이 창에 잡힌다
_INDUSTRY = "korean_food"


def _region_code() -> str:
    with session_scope() as session:
        return session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)).scalar_one()


def _store(n: int, region: str, open_date: date, close_date: date | None) -> StoreOrm:
    return StoreOrm(
        store_id=f"{_PREFIX}{n}", name=f"판정시험{n}", industry_id=_INDUSTRY, district_code=region[:5],
        region_code=region, subcategory_id=None, open_date=open_date, close_date=close_date,
        status_code="01", status_name="영업" if close_date is None else "폐업",
        lat=None, lng=None, road_address=None, jibun_address=None, source_updated_at=datetime(2099, 1, 1),
    )


def test_store_집계_12개월_코호트_중위개월():
    region = _region_code()
    d = lambda days: _TODAY - timedelta(days=days)  # noqa: E731
    # 개업/폐업일은 전부 today(2099-06-30) 기준 N일 전. 창: 12개월 = 365일, 코호트 = [1460, 1095)일 전 개업, 3년 = 1095일
    rows = [
        _store(1, region, d(800), None),      # 12개월 전 영업 → start. 폐업 없음
        _store(2, region, d(800), d(100)),    # start · closed_12m · closed_3y (영업 700일)
        _store(3, region, d(100), None),      # opened_12m
        _store(4, region, d(1195), None),     # 코호트 · 생존 · start
        _store(5, region, d(1195), d(795)),   # 코호트 · 400일 만에 폐업 → 미생존 · closed_3y (start 아님: 12개월 전 이미 폐업)
        _store(6, region, d(1195), d(95)),    # 코호트 · 1100일 뒤 폐업 → 생존(≥1095) · start · closed_12m · closed_3y
        _store(7, region, d(2000), d(200)),   # start · closed_12m · closed_3y (영업 1800일)
    ]
    try:
        with session_scope() as session:
            session.add_all(rows)
        stat = next(s for s in StoreSignalStatsGateway().signal_stats(_TODAY)
                    if s.region_code == region and s.industry_id == _INDUSTRY)
        # 실적재 행은 2099 창에 안 잡힌다(개업·폐업일이 전부 과거) — 시험 행만 센다
        assert stat.start_store_count == 5  # 1, 2, 4, 6, 7 (5는 12개월 전 이미 폐업, 3은 그 뒤 개업)
        assert stat.opened_12m == 1  # 3
        assert stat.closed_12m == 3  # 2, 6, 7
        assert stat.cohort_size == 3 and stat.cohort_survived == 2  # 4·5·6 중 4·6
        assert stat.closed_3y_count == 4  # 2, 5, 6, 7
        # 영업일수 700·400·1100·1800 → 중위 900일 ≈ 29.6개월
        assert stat.closed_3y_median_months == pytest.approx(900 / 30.4375, rel=1e-3)
    finally:
        with session_scope() as session:
            session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_PREFIX}%")))


def test_동_맥락은_전_행정동을_한_행씩_준다():
    contexts = RegionContextGateway().latest_contexts()
    codes = [c.region_code for c in contexts]
    assert len(codes) == len(set(codes)) >= 400
    counts = RegionContextGateway().latest_store_counts()
    assert all(c.store_count >= 0 for c in counts)


def test_판정_대상_업종은_제외_4종을_뺀_14종():
    judged = IndustryCatalogGateway().judged_industries()
    ids = {i.industry_id for i in judged}
    assert len(ids) == 14
    assert ids.isdisjoint(EXCLUDED_INDUSTRIES)
    assert next(i.name for i in judged if i.industry_id == "korean_food") == "한식"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_gateways.py -q`
Expected: FAIL — `ModuleNotFoundError: ... gateways.industry_catalog_gateway`

- [ ] **Step 3: 게이트웨이 구현**

```python
# backend/apps/verdict/adapter/outbound/gateways/store_signal_stats_gateway.py
"""Driven Adapter — store 원천을 한 번의 group_by로 세 집계 (cross-BC 접근은 어댑터 레이어에서만).
창(12개월·3년·4년)은 today 기준 일수로 잡는다 — 월 단위 산술의 2/29 문제를 피한다."""

from datetime import date, timedelta

from sqlalchemy import and_, func, or_, select

from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.verdict.app.dtos.region_industry_verdict_dto import StoreSignalStat
from apps.verdict.app.ports.output.region_industry_verdict_port import StoreSignalStatsPort
from core.matrix.grid_oracle_database_manager import session_scope

_DAYS_PER_MONTH = 30.4375
_THREE_YEARS_DAYS = 3 * 365


class StoreSignalStatsGateway(StoreSignalStatsPort):
    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        since_12m = today - timedelta(days=365)
        cohort_to = today - timedelta(days=3 * 365)  # 코호트 = [today−4y, today−3y)
        cohort_from = today - timedelta(days=4 * 365)
        since_3y = cohort_to

        days_open = StoreOrm.close_date - StoreOrm.open_date  # PostgreSQL: date − date = 일수(int)
        in_cohort = and_(StoreOrm.open_date >= cohort_from, StoreOrm.open_date < cohort_to)
        closed_3y = and_(StoreOrm.close_date.is_not(None), StoreOrm.close_date >= since_3y, StoreOrm.close_date <= today)

        with session_scope() as session:
            rows = session.execute(
                select(
                    StoreOrm.region_code,
                    StoreOrm.industry_id,
                    # 12개월 전 시점 영업중: 그 전에 개업 & (미폐업 or 그 뒤 폐업)
                    func.count().filter(
                        StoreOrm.open_date <= since_12m,
                        or_(StoreOrm.close_date.is_(None), StoreOrm.close_date > since_12m),
                    ),
                    func.count().filter(StoreOrm.open_date > since_12m, StoreOrm.open_date <= today),
                    func.count().filter(StoreOrm.close_date > since_12m, StoreOrm.close_date <= today),
                    func.count().filter(in_cohort),
                    func.count().filter(in_cohort, or_(StoreOrm.close_date.is_(None), days_open >= _THREE_YEARS_DAYS)),
                    func.count().filter(closed_3y),
                    func.percentile_cont(0.5).within_group(days_open / _DAYS_PER_MONTH).filter(closed_3y),
                )
                .where(StoreOrm.region_code.is_not(None), StoreOrm.open_date.is_not(None))
                .group_by(StoreOrm.region_code, StoreOrm.industry_id)
            ).all()
        return [
            StoreSignalStat(
                region_code=region_code, industry_id=industry_id, start_store_count=start, opened_12m=opened,
                closed_12m=closed, cohort_size=cohort, cohort_survived=survived, closed_3y_count=closed_3y_count,
                closed_3y_median_months=None if median is None else float(median),
            )
            for region_code, industry_id, start, opened, closed, cohort, survived, closed_3y_count, median in rows
        ]
```

```python
# backend/apps/verdict/adapter/outbound/gateways/region_context_gateway.py
"""Driven Adapter — 동 맥락: 최신 분기 상주인구(region_profile_quarter), 최신 분기 상권변화지표(+서울 베이스라인),
최신 연도 점포수(region_industry_metric). 전 행정동(region 마스터) 1행씩 돌려주고 없는 값은 None."""

from sqlalchemy import and_, func, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.metric.adapter.outbound.orms.region_industry_metric_orm import RegionIndustryMetricOrm
from apps.metric.adapter.outbound.orms.region_profile_quarter_orm import RegionProfileQuarterOrm
from apps.neighborhood.adapter.outbound.orms.region_commerce_change_orm import RegionCommerceChangeOrm
from apps.neighborhood.adapter.outbound.orms.seoul_commerce_change_baseline_orm import (
    SeoulCommerceChangeBaselineOrm,
)
from apps.verdict.app.dtos.region_industry_verdict_dto import LatestStoreCount, RegionContext
from apps.verdict.app.ports.output.region_industry_verdict_port import RegionContextPort
from core.matrix.grid_oracle_database_manager import session_scope


class RegionContextGateway(RegionContextPort):
    def latest_contexts(self) -> list[RegionContext]:
        P, C, B = RegionProfileQuarterOrm, RegionCommerceChangeOrm, SeoulCommerceChangeBaselineOrm
        with session_scope() as session:
            latest_profile = (
                select(P.region_code, func.max(P.year_quarter).label("yq")).group_by(P.region_code).subquery()
            )
            residents = dict(
                session.execute(
                    select(P.region_code, P.resident_total).join(
                        latest_profile, and_(P.region_code == latest_profile.c.region_code, P.year_quarter == latest_profile.c.yq)
                    )
                ).all()
            )
            latest_change = (
                select(C.region_code, func.max(C.year_quarter).label("yq"))
                .where(C.region_code.is_not(None))
                .group_by(C.region_code)
                .subquery()
            )
            change_rows = session.execute(
                select(C.region_code, C.year_quarter, C.change_code, C.change_name, C.closed_months, B.seoul_closed_months)
                .join(latest_change, and_(C.region_code == latest_change.c.region_code, C.year_quarter == latest_change.c.yq))
                .join(B, B.year_quarter == C.year_quarter, isouter=True)
                .order_by(C.region_code, C.adstrd_code)
            ).all()
            changes = {}
            for row in change_rows:
                changes.setdefault(row.region_code, row)  # 한 동에 상권코드가 여럿이면 첫 행(adstrd_code 순)
            region_codes = session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code)).scalars().all()
        contexts = []
        for code in region_codes:
            change = changes.get(code)
            contexts.append(RegionContext(
                region_code=code,
                resident_total=residents.get(code),
                change_code=change.change_code if change else None,
                change_name=change.change_name if change else None,
                change_quarter=change.year_quarter if change else None,
                closed_months=change.closed_months if change else None,
                seoul_closed_months=change.seoul_closed_months if change else None,
            ))
        return contexts

    def latest_store_counts(self) -> list[LatestStoreCount]:
        M = RegionIndustryMetricOrm
        with session_scope() as session:
            latest_year = session.execute(select(func.max(M.year))).scalar_one()
            rows = session.execute(
                select(M.region_code, M.industry_id, M.store_count).where(M.year == latest_year)
            ).all()
        return [LatestStoreCount(r, i, n) for r, i, n in rows]
```

```python
# backend/apps/verdict/adapter/outbound/gateways/industry_catalog_gateway.py
"""Driven Adapter — industry 마스터에서 판정 대상 업종만 (EXCLUDED_INDUSTRIES 제외)."""

from sqlalchemy import select

from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.verdict.app.dtos.region_industry_verdict_dto import JudgedIndustry
from apps.verdict.app.ports.output.region_industry_verdict_port import IndustryCatalogPort
from apps.verdict.domain.entities.region_industry_verdict_entity import EXCLUDED_INDUSTRIES
from core.matrix.grid_oracle_database_manager import session_scope


class IndustryCatalogGateway(IndustryCatalogPort):
    def judged_industries(self) -> list[JudgedIndustry]:
        with session_scope() as session:
            rows = session.execute(
                select(IndustryOrm.industry_id, IndustryOrm.name)
                .where(IndustryOrm.industry_id.not_in(EXCLUDED_INDUSTRIES))
                .order_by(IndustryOrm.industry_id)
            ).all()
        return [JudgedIndustry(industry_id, name) for industry_id, name in rows]
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_gateways.py -q`
Expected: 3 passed. `percentile_cont(...).within_group(...).filter(...)`가 SQLAlchemy 버전에서 `FILTER` 절을 못 만들면 `func.percentile_cont(0.5).within_group(...)` 대신 `case((closed_3y, days_open / _DAYS_PER_MONTH), else_=None)`를 within_group 안에 넣는다 — NULL은 ordered-set 집계에서 무시된다.

- [ ] **Step 5: 커밋**

```bash
git add backend/apps/verdict/adapter/outbound/gateways backend/tests/test_verdict_gateways.py
git commit -m "verdict: 게이트웨이 3종 — store 집계 1쿼리(percentile_cont)·동 맥락·판정 대상 업종 (설계서 §4-4)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

### Task 7: 라우터·스키마·매퍼·DI·CLI·크론 + 실DB 배치 1회 + 버전 로그

**Files:**
- Create: `backend/apps/verdict/adapter/inbound/__init__.py`, `adapter/inbound/api/__init__.py`, `adapter/inbound/api/v1/__init__.py`, `adapter/inbound/api/schemas/__init__.py`, `adapter/inbound/mappers/__init__.py`, `adapter/inbound/cli/__init__.py`, `dependencies/__init__.py` (빈 파일)
- Create: `backend/apps/verdict/adapter/inbound/api/schemas/region_industry_verdict_schema.py`
- Create: `backend/apps/verdict/adapter/inbound/mappers/region_industry_verdict_mapper.py`
- Create: `backend/apps/verdict/dependencies/region_industry_verdict_dependencies.py`
- Create: `backend/apps/verdict/adapter/inbound/api/v1/region_industry_verdict_router.py`
- Create: `backend/apps/verdict/adapter/inbound/cli/build_verdicts.py`
- Modify: `backend/main.py` (import + `app.include_router(verdict_router)`)
- Modify: `scripts/store-collector.sh:25` 뒤 두 줄
- Modify: `backend/docs/backend_ver_log.md`, `docs/superpowers/specs/2026-09-28-verdict-card-design.md`(§11 진행 기록 추가), `docs/HANDOFF.md` §0-7
- Test: `backend/tests/test_verdict_router.py`

**Interfaces:**
- Consumes: Task 4 유스케이스·DTO, Task 5 리포지토리, Task 6 게이트웨이
- Produces: `GET /verdicts/myself`, `GET /verdicts?industry=`, `GET /verdicts/{region_code}?industry=`, `get_region_industry_verdict_use_case()`, CLI `python -m apps.verdict.adapter.inbound.cli.build_verdicts`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# backend/tests/test_verdict_router.py
"""verdict 라우터 — 배선(myself) · 목록(범주 계약) · 단건 · 404 두 종류 (Fake 유스케이스)."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    RegionIndustryVerdictDto,
    SignalResultDto,
    VerdictValueDto,
)
from apps.verdict.app.ports.input.region_industry_verdict_use_case import RegionIndustryVerdictUseCase
from apps.verdict.dependencies.region_industry_verdict_dependencies import get_region_industry_verdict_use_case
from apps.verdict.domain.errors import IndustryNotFoundError
from main import app

_DTO = RegionIndustryVerdictDto(
    region_code="1168064000", industry_id="korean_food", verdict_code="red", strong_count=2, on_count=3,
    signals=tuple(
        SignalResultDto(key=k, level="strong", value=0.2, percentile=95.0, evidence="근거", source="store")
        for k in ("net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking")
    ),
    computed_at=datetime(2026, 9, 29, 4, 30, tzinfo=timezone.utc),
)


class FakeUseCase(RegionIndustryVerdictUseCase):
    def myself(self):
        return _DTO

    def build(self, today):
        return 0

    def list_verdict_values(self, industry_id):
        if industry_id != "korean_food":
            raise IndustryNotFoundError(industry_id)
        return [VerdictValueDto("1168064000", "red"), VerdictValueDto("1168065000", "clear")]

    def find(self, region_code, industry_id):
        if industry_id != "korean_food":
            raise IndustryNotFoundError(industry_id)
        return _DTO if region_code == "1168064000" else None


def _client() -> TestClient:
    app.dependency_overrides[get_region_industry_verdict_use_case] = lambda: FakeUseCase()
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.pop(get_region_industry_verdict_use_case, None)


def test_myself_배선_200():
    app.dependency_overrides.pop(get_region_industry_verdict_use_case, None)  # 실제 DI로 배선 검증
    body = TestClient(app).get("/verdicts/myself").json()
    assert body["region_code"] == "myself" and len(body["signals"]) == 5


def test_목록은_region_code와_value_쌍이다():
    res = _client().get("/verdicts?industry=korean_food")
    assert res.status_code == 200
    assert res.json() == [{"region_code": "1168064000", "value": "red"}, {"region_code": "1168065000", "value": "clear"}]


def test_판정_대상이_아닌_업종은_404_INDUSTRY_NOT_FOUND():
    res = _client().get("/verdicts?industry=academy")
    assert res.status_code == 404 and res.json()["error"]["code"] == "INDUSTRY_NOT_FOUND"
    res = _client().get("/verdicts/1168064000?industry=chicken")
    assert res.status_code == 404 and res.json()["error"]["code"] == "INDUSTRY_NOT_FOUND"


def test_단건은_신호_5개를_담고_없으면_404_VERDICT_NOT_FOUND():
    res = _client().get("/verdicts/1168064000?industry=korean_food")
    assert res.status_code == 200
    body = res.json()
    assert body["verdict_code"] == "red" and body["signals"][0]["key"] == "net_outflow"
    assert body["signals"][0]["percentile"] == 95.0
    missing = _client().get("/verdicts/0000000000?industry=korean_food")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "VERDICT_NOT_FOUND"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_router.py -q`
Expected: FAIL — `ModuleNotFoundError: ... dependencies`

- [ ] **Step 3: 스키마·매퍼·DI·라우터·CLI 구현 + 등록**

```python
# backend/apps/verdict/adapter/inbound/api/schemas/region_industry_verdict_schema.py
from datetime import datetime

from pydantic import BaseModel


class SignalResultResponse(BaseModel):
    key: str
    level: str
    value: float | None
    percentile: float | None
    evidence: str
    source: str


class RegionIndustryVerdictResponse(BaseModel):
    region_code: str
    industry_id: str
    verdict_code: str
    strong_count: int
    on_count: int
    signals: list[SignalResultResponse]
    computed_at: datetime


class VerdictValueResponse(BaseModel):
    """단계구분도 응답 단위 — {region_code, value: verdict_code}. 동네 유형과 같은 범주 계약 (프론트엔드 계약)."""

    region_code: str
    value: str
```

```python
# backend/apps/verdict/adapter/inbound/mappers/region_industry_verdict_mapper.py
"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.verdict.adapter.inbound.api.schemas.region_industry_verdict_schema import (
    RegionIndustryVerdictResponse,
    SignalResultResponse,
    VerdictValueResponse,
)
from apps.verdict.app.dtos.region_industry_verdict_dto import RegionIndustryVerdictDto, VerdictValueDto


def to_response(dto: RegionIndustryVerdictDto) -> RegionIndustryVerdictResponse:
    return RegionIndustryVerdictResponse(
        region_code=dto.region_code, industry_id=dto.industry_id, verdict_code=dto.verdict_code,
        strong_count=dto.strong_count, on_count=dto.on_count,
        signals=[SignalResultResponse(**asdict(s)) for s in dto.signals], computed_at=dto.computed_at,
    )


def to_value_response(dto: VerdictValueDto) -> VerdictValueResponse:
    return VerdictValueResponse(**asdict(dto))
```

```python
# backend/apps/verdict/dependencies/region_industry_verdict_dependencies.py
"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.verdict.adapter.outbound.gateways.industry_catalog_gateway import IndustryCatalogGateway
from apps.verdict.adapter.outbound.gateways.region_context_gateway import RegionContextGateway
from apps.verdict.adapter.outbound.gateways.store_signal_stats_gateway import StoreSignalStatsGateway
from apps.verdict.adapter.outbound.repositories.region_industry_verdict_repository import (
    SqlAlchemyRegionIndustryVerdictRepository,
)
from apps.verdict.app.ports.input.region_industry_verdict_use_case import RegionIndustryVerdictUseCase
from apps.verdict.app.use_cases.region_industry_verdict_interactor import RegionIndustryVerdictInteractor


def get_region_industry_verdict_use_case() -> RegionIndustryVerdictUseCase:
    return RegionIndustryVerdictInteractor(
        repository=SqlAlchemyRegionIndustryVerdictRepository(),
        store_stats=StoreSignalStatsGateway(),
        region_context=RegionContextGateway(),
        industry_catalog=IndustryCatalogGateway(),
    )
```

```python
# backend/apps/verdict/adapter/inbound/api/v1/region_industry_verdict_router.py
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.verdict.adapter.inbound.api.schemas.region_industry_verdict_schema import (
    RegionIndustryVerdictResponse,
    VerdictValueResponse,
)
from apps.verdict.adapter.inbound.mappers.region_industry_verdict_mapper import to_response, to_value_response
from apps.verdict.app.ports.input.region_industry_verdict_use_case import RegionIndustryVerdictUseCase
from apps.verdict.dependencies.region_industry_verdict_dependencies import get_region_industry_verdict_use_case
from apps.verdict.domain.errors import IndustryNotFoundError

router = APIRouter(prefix="/verdicts", tags=["verdicts"])


def _not_found(code: str, message: str) -> JSONResponse:
    """에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)."""
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})


@router.get("/myself", response_model=RegionIndustryVerdictResponse)
def myself(use_case: RegionIndustryVerdictUseCase = Depends(get_region_industry_verdict_use_case)):
    return to_response(use_case.myself())


@router.get("", response_model=list[VerdictValueResponse])
def list_verdict_values(
    industry: str,
    use_case: RegionIndustryVerdictUseCase = Depends(get_region_industry_verdict_use_case),
) -> list[VerdictValueResponse] | JSONResponse:
    try:
        values = use_case.list_verdict_values(industry)
    except IndustryNotFoundError:
        return _not_found("INDUSTRY_NOT_FOUND", f"판정 대상 업종이 아닙니다: {industry}")
    return [to_value_response(v) for v in values]


# `/{region_code}`는 ""·/myself 뒤에 선언한다 — 앞에 두면 "myself"를 동 코드로 먹는다.
@router.get("/{region_code}", response_model=RegionIndustryVerdictResponse)
def find_verdict(
    region_code: str,
    industry: str,
    use_case: RegionIndustryVerdictUseCase = Depends(get_region_industry_verdict_use_case),
) -> RegionIndustryVerdictResponse | JSONResponse:
    try:
        dto = use_case.find(region_code, industry)
    except IndustryNotFoundError:
        return _not_found("INDUSTRY_NOT_FOUND", f"판정 대상 업종이 아닙니다: {industry}")
    if dto is None:
        return _not_found("VERDICT_NOT_FOUND", f"판정이 없습니다: {region_code} × {industry}")
    return to_response(dto)
```

```python
# backend/apps/verdict/adapter/inbound/cli/build_verdicts.py
"""판정 배치 — 매일 04:20 store-collector.sh에서 build_metrics 바로 뒤에 실행 (설계서 §4-4).

    cd backend && .venv/bin/python -m apps.verdict.adapter.inbound.cli.build_verdicts
"""

from datetime import date

from apps.verdict.dependencies.region_industry_verdict_dependencies import get_region_industry_verdict_use_case


def main() -> None:
    processed = get_region_industry_verdict_use_case().build(date.today())
    print(f"판정 업서트: {processed}건 (판정 대상 14업종 × 행정동)")


if __name__ == "__main__":
    main()
```

`backend/main.py` — import 블록 끝(35행 `store_router` 다음)에 추가하고 `app.include_router(store_router)` 다음 줄에 등록:

```python
from apps.verdict.adapter.inbound.api.v1.region_industry_verdict_router import (
    router as verdict_router,
)
```
```python
app.include_router(verdict_router)
```

`scripts/store-collector.sh` — `build_metrics` 줄(25행) 바로 뒤:

```bash
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 판정 배치 (region_industry_verdict, 14업종 × 427동)"
  .venv/bin/python -m apps.verdict.adapter.inbound.cli.build_verdicts
```

- [ ] **Step 4: 통과 확인 + 전체 회귀**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verdict_router.py -q && .venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: 4 passed, 이어서 전체 `542 + 24 passed` 이상(기존 542 유지)

- [ ] **Step 5: 실DB 배치 1회 실행하고 분포를 기록한다**

Run:
```bash
cd backend && time .venv/bin/python -m apps.verdict.adapter.inbound.cli.build_verdicts
.venv/bin/python - <<'EOF'
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
load_dotenv("/home/kimchungsik/projects/cloud.beyondfacade/backend/.env")
url = next(v for k, v in os.environ.items() if "DATABASE" in k and "://" in v)
with create_engine(url).connect() as c:
    print("총 행:", c.execute(text("select count(*) from region_industry_verdict")).scalar())
    for r in c.execute(text("""
        select industry_id,
               sum(case when verdict_code='red' then 1 else 0 end) red,
               sum(case when verdict_code='orange' then 1 else 0 end) orange,
               sum(case when verdict_code='clear' then 1 else 0 end) clear,
               sum(case when verdict_code='insufficient' then 1 else 0 end) insufficient
        from region_industry_verdict group by industry_id order by red desc""")):
        print(r)
EOF
curl -s "http://127.0.0.1:8201/verdicts?industry=korean_food" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("한식 동 수:", len(d))'
curl -s "http://127.0.0.1:8201/verdicts/1168064000?industry=korean_food" | head -c 600
```
Expected: 총 행 5,978(= 14 × 427), 한식 427동, 역삼1동 카드 JSON. **insufficient 비율이 어느 업종에서든 30%를 넘으면** 설계서 §9대로 `VerdictThresholds.min_sample`을 5로 낮춰 재실행하고 그 사실을 §11에 적는다(상수는 한 곳). 8201이 코드를 새로 안 읽으면(uvicorn --reload 아님) 재시작 없이 넘어가고 8299로 임시 기동해 확인: `.venv/bin/uvicorn main:app --port 8299` (검증 후 종료).

- [ ] **Step 6: 문서 3곳**

`backend/docs/backend_ver_log.md` 맨 위 `# Backend Version Log` 아래에:

```markdown
## [v0.40.0] - 2026-09-29

### Added
- **verdict BC** — 동×업종 판정 카드 원천. 공통 경고 신호 5개(순유출·생존 절벽·조기 폐업·포화·상권 축소)를
  업종 안 427동 백분위로 상대평가(75 켜짐·90 강함)해 🔴 red(강함 2+)/🟠 orange(켜짐 1+)/⚪ clear/보류 insufficient(판정 가능 신호 3 미만).
  신호 = Specification 클래스(`domain/services/signals.py`), 판정 = Chain of Responsibility(`rules.py`), 임계값은 `thresholds.py` 한 곳.
- 테이블 `region_industry_verdict`(마이그레이션 `c9d0e1f2a3b4`), 배치 `build_verdicts`(크론 `store-collector.sh` 마지막),
  API `GET /verdicts/myself`·`GET /verdicts?industry=`(범주 계약)·`GET /verdicts/{region_code}?industry=`.
- 판정 대상 14업종 = 마스터 18 − 학원·어린이집·기타·치킨(`EXCLUDED_INDUSTRIES`).

### Validation
- 신규 테스트 24 (임계값 6·신호 9·규칙 5·배치 4·리포지토리 1·게이트웨이 3·라우터 4), 전체 N passed.
- 실DB 배치 1회: 5,978행, 소요 S초. 업종별 red/orange/clear/insufficient 분포는 설계서 §11.
```
(N·S와 분포는 Step 5 실측으로 채운다.)

설계서 끝에 `## 11. 진행 기록` 표를 추가하고 1단계 행(일시·배치 소요·업종별 분포·insufficient 최대 비율·min_sample 조정 여부)을 적는다. `docs/HANDOFF.md` §0-7 1번 줄 끝에 `— 1단계 BE v0.40.0 완료(9/29), 2·3단계는 플랜 참조` 를 덧붙인다.

- [ ] **Step 7: 커밋·푸시**

```bash
git add backend/apps/verdict backend/main.py backend/tests/test_verdict_router.py scripts/store-collector.sh backend/docs/backend_ver_log.md docs/superpowers/specs/2026-09-28-verdict-card-design.md docs/HANDOFF.md
git commit -m "backend v0.40.0: verdict BC — 공통 신호 5개 상대평가 판정, region_industry_verdict 배치·API (설계서 1단계)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git push origin main
```

---

## 2단계 — 프론트 판정 카드·위험도 지도 (FE v0.29.0)

### Task 8: 타입·공통 어휘·지도 팔레트

**Files:**
- Modify: `frontend/src/shared/api/types.ts:9-45` (지표 키 유니온·축) + 파일 끝(verdict 타입)
- Create: `frontend/src/shared/verdict.ts`
- Create: `frontend/src/features/map-explorer/lib/verdict-palette.ts`
- Test: `frontend/src/shared/verdict.test.ts`, `frontend/src/features/map-explorer/lib/verdict-palette.test.ts`

**Interfaces:**
- Produces (types.ts): `VerdictCode = "red" | "orange" | "clear" | "insufficient"`, `VerdictSignalLevel`, `VerdictSignalKey`, `VerdictSignal`, `RegionIndustryVerdict`, `VerdictRow {region_code, value: VerdictCode}`; `CategoricalMetricKey = "neighborhood_type" | "verdict"`, `MapMetricKey = MetricKey | RegionMetricKey | "verdict"`, `MetricAxis = "industry_year" | "region_quarter" | "industry_latest"`
- Produces (shared/verdict.ts): `VERDICT_CODES` (순서 red→orange→clear→insufficient), `verdictLabel(code) -> {name, qualifier}`, `SIGNAL_LABELS: Record<VerdictSignalKey, string>`, `signalLabel(key)`
- Produces (verdict-palette.ts): `verdictPalette(theme: MapTheme) -> Record<VerdictCode, string>`

- [ ] **Step 1: 실패하는 테스트 작성**

```ts
// frontend/src/shared/verdict.test.ts
import { expect, it } from "vitest";
import { SIGNAL_LABELS, VERDICT_CODES, signalLabel, verdictLabel } from "./verdict";

it("판정 코드 순서는 빨강→주황→경고 없음→보류다 (범례 순서)", () => {
  expect(VERDICT_CODES).toEqual(["red", "orange", "clear", "insufficient"]);
});

it("판정 라벨은 이름과 괄호 설명을 갖고, 🟢 추천은 없다", () => {
  expect(verdictLabel("red")).toEqual({ name: "비추천", qualifier: "강한 경고 신호 2개 이상" });
  expect(verdictLabel("orange").name).toBe("조건부");
  expect(verdictLabel("clear").name).toBe("경고 없음");
  expect(verdictLabel("insufficient").name).toBe("판정 보류");
  expect(Object.values(VERDICT_CODES)).not.toContain("green");
});

it("알 수 없는 코드는 원문을 이름으로 돌려준다", () => {
  expect(verdictLabel("weird").name).toBe("weird");
});

it("신호 5개 라벨", () => {
  expect(Object.keys(SIGNAL_LABELS)).toEqual(["net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking"]);
  expect(signalLabel("net_outflow")).toBe("순유출");
  expect(signalLabel("unknown")).toBe("unknown");
});
```

```ts
// frontend/src/features/map-explorer/lib/verdict-palette.test.ts
import { expect, it } from "vitest";
import { relativeLuminance } from "./neighborhood-palette";
import { verdictPalette } from "./verdict-palette";

it("라이트·다크 둘 다 4범주 색을 갖는다", () => {
  for (const theme of ["light", "dark"] as const) {
    expect(Object.keys(verdictPalette(theme)).sort()).toEqual(["clear", "insufficient", "orange", "red"]);
  }
});

it("경고 없음·보류가 가장 옅다 — 빨강·주황이 지도에서 튀어야 한다", () => {
  const light = verdictPalette("light");
  expect(relativeLuminance(light.clear)).toBeGreaterThan(relativeLuminance(light.red));
  expect(relativeLuminance(light.clear)).toBeGreaterThan(relativeLuminance(light.orange));
  const dark = verdictPalette("dark");
  expect(relativeLuminance(dark.clear)).toBeLessThan(relativeLuminance(dark.red));
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run src/shared/verdict.test.ts src/features/map-explorer/lib/verdict-palette.test.ts`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

`frontend/src/shared/api/types.ts` — 다음 세 줄을 바꾼다:

```ts
/** 범주 계약({region_code, type_code})으로 오는 지표. 숫자 계약과 경로가 다르다 (map-metric-contract §5).
 *  verdict는 API가 {region_code, value}로 주지만 api.ts가 type_code로 옮겨 같은 범주 파이프라인을 탄다. */
export type CategoricalMetricKey = "neighborhood_type" | "verdict";

/** 지도 단계구분도가 그릴 수 있는 전체 지표. 원천은 넷으로 갈리지만 호출하는 쪽은 METRIC_SOURCES 한 곳만 안다. */
export type MapMetricKey = MetricKey | RegionMetricKey | "verdict";

/** 지표의 축 — 셀렉터가 이 값을 정직하게 따라간다. industry_latest는 업종만 묻고 시점은 "배치 최신"이라 연도·분기 select를 숨긴다. */
export type MetricAxis = "industry_year" | "region_quarter" | "industry_latest";
```

파일 끝에 추가:

```ts
// ---------------------------------------------------------------------------
// 판정 카드 (GET /verdicts, GET /verdicts/{region_code}) — 설계서 2026-09-28-verdict-card-design §4-5
// ---------------------------------------------------------------------------

export type VerdictCode = "red" | "orange" | "clear" | "insufficient";
export type VerdictSignalLevel = "off" | "on" | "strong" | "unavailable";
export type VerdictSignalKey = "net_outflow" | "survival_cliff" | "early_closure" | "saturation" | "shrinking";

export interface VerdictSignal {
  key: VerdictSignalKey;
  level: VerdictSignalLevel;
  value: number | null;
  percentile: number | null; // 나쁜 방향 백분위 0~100. 이진 신호·미판정은 null
  evidence: string; // 백엔드가 만든 근거 한 문장 — 화면은 그대로 띄운다
  source: "store" | "metric" | "neighborhood";
}

export interface RegionIndustryVerdict {
  region_code: string;
  industry_id: string;
  verdict_code: VerdictCode;
  strong_count: number;
  on_count: number;
  signals: VerdictSignal[]; // 항상 5개, 고정 순서
  computed_at: string;
}

/** 위험도 단계구분도 행 (GET /verdicts?industry=). 범주 계약이지만 필드명은 value다. */
export interface VerdictRow {
  region_code: string;
  value: VerdictCode;
}
```

```ts
// frontend/src/shared/verdict.ts
/** 판정 코드·신호 키의 표기 어휘. 코드는 API 계약 값이라 영문 유지, 화면엔 라벨만.
 *  판정은 백엔드 verdict 배치가 하고 여기는 사람이 읽는 말로 옮기기만 한다. 🟢 추천은 없다(HANDOFF §0-2).
 *  지도 범례·사이드패널 카드가 함께 쓰므로 shared에 둔다. */
import type { VerdictCode, VerdictSignalKey } from "@/shared/api/types";

export const VERDICT_CODES = ["red", "orange", "clear", "insufficient"] as const satisfies readonly VerdictCode[];

export interface VerdictLabel {
  name: string;
  qualifier: string;
}

const LABELS: Record<VerdictCode, VerdictLabel> = {
  red: { name: "비추천", qualifier: "강한 경고 신호 2개 이상" },
  orange: { name: "조건부", qualifier: "경고 신호 1개 이상" },
  clear: { name: "경고 없음", qualifier: "켜진 신호 없음" },
  insufficient: { name: "판정 보류", qualifier: "표본 부족 — 판정 가능한 신호 3개 미만" },
};

export function verdictLabel(code: string): VerdictLabel {
  return LABELS[code as VerdictCode] ?? { name: code, qualifier: "분류 없음" };
}

export const SIGNAL_LABELS: Record<VerdictSignalKey, string> = {
  net_outflow: "순유출",
  survival_cliff: "생존 절벽",
  early_closure: "조기 폐업",
  saturation: "포화",
  shrinking: "상권 축소",
};

export function signalLabel(key: string): string {
  return SIGNAL_LABELS[key as VerdictSignalKey] ?? key;
}

/** 판정 대상에서 빠진 select 업종 — 편의점은 스냅샷 전용 원천이라 백엔드 verdict가 없다(1단계 Ruling A, 특화 신호 단계까지).
 *  백엔드 `EXCLUDED_INDUSTRIES` 중 프론트 `INDUSTRIES`(14)에 남아 있는 것만 여기 둔다. */
export const VERDICT_EXCLUDED_INDUSTRIES: ReadonlySet<string> = new Set(["convenience_store"]);

export function isVerdictIndustry(industryId: string): boolean {
  return (INDUSTRIES as readonly string[]).includes(industryId) && !VERDICT_EXCLUDED_INDUSTRIES.has(industryId);
}
```
(`import { INDUSTRIES } from "@/shared/industries";` 를 파일 상단에 추가. `shared/verdict.test.ts`에 케이스 하나: `isVerdictIndustry("korean_food")` true, `"convenience_store"` false, `"academy"` false.)

```ts
// frontend/src/features/map-explorer/lib/verdict-palette.ts
/** 판정 4범주의 지도 팔레트 — 데이터 시각화 전용 상수. tokens.css의 UI 토큰과 분리된 별도 체계다
 *  (neighborhood-palette.ts와 같은 원칙). 카드·배지의 색은 토큰(--danger·--warn)을 쓰고, 여기 값은 WebGL fill에만 간다.
 *  원칙 — 경고 없음·보류가 가장 옅고(배경에 가깝게) 빨강·주황이 튄다. 옅음은 명도로 정의한다. */
import type { VerdictCode } from "@/shared/api/types";
import type { MapTheme } from "./neighborhood-palette";

const LIGHT: Record<VerdictCode, string> = {
  red: "#c8102e",
  orange: "#e8862a",
  clear: "#dcdad3", // 가장 옅은 회베이지
  insufficient: "#ecebe7", // 보류 — clear보다 더 옅게, 빗금 대신 명도로 구분
};

const DARK: Record<VerdictCode, string> = {
  red: "#ff5a6a",
  orange: "#ffa64d",
  clear: "#3a3f4b", // 밤 타일에 가장 가깝다
  insufficient: "#2c303a",
};

export function verdictPalette(theme: MapTheme): Record<VerdictCode, string> {
  return theme === "dark" ? DARK : LIGHT;
}
```

- [ ] **Step 4: 통과 확인 + 타입 체크**

Run: `cd frontend && npx vitest run src/shared/verdict.test.ts src/features/map-explorer/lib/verdict-palette.test.ts && npx tsc --noEmit`
Expected: 6 passed. tsc는 `METRIC_LABELS: Record<MapMetricKey, string>`·`METRIC_SOURCES: Record<MapMetricKey, ...>`에 `verdict`가 없어 **실패한다** — Task 10에서 채운다. 이 Task에서는 vitest만 통과하면 된다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/shared/api/types.ts frontend/src/shared/verdict.ts frontend/src/shared/verdict.test.ts frontend/src/features/map-explorer/lib/verdict-palette.ts frontend/src/features/map-explorer/lib/verdict-palette.test.ts
git commit -m "frontend: 판정 타입·공통 어휘·지도 팔레트 (설계서 §5)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

### Task 9: mock 미러 — /api/mock/verdicts 두 라우트 + 픽스처

**Files:**
- Modify: `frontend/src/app/api/mock/fixtures.ts` (끝에 verdict 픽스처)
- Create: `frontend/src/app/api/mock/verdicts/route.ts`, `frontend/src/app/api/mock/verdicts/[regionCode]/route.ts`
- Test: `frontend/src/app/api/mock/verdicts/route.test.ts`, `frontend/src/app/api/mock/verdicts/[regionCode]/route.test.ts`

**Interfaces:**
- Consumes: Task 8 타입, `fixtures.ts`의 `hashSeed`·`unitFrom`·`REGIONS`·`SEOUL_REGIONS_GEOJSON`, `@/shared/industries`의 `INDUSTRIES`·`INDUSTRY_LABELS`
- Produces: `verdictOf(regionCode, industryId): RegionIndustryVerdict`, `verdictRows(industryId): VerdictRow[]`

- [ ] **Step 1: 실패하는 테스트 작성**

```ts
// frontend/src/app/api/mock/verdicts/route.test.ts
import { expect, it } from "vitest";
import { GET } from "./route";

function call(query: string) {
  return GET(new Request(`http://test/api/mock/verdicts${query}`));
}

it("판정 대상 업종은 200과 region_code·value(판정 코드) 쌍 목록을 준다", async () => {
  const res = await call("?industry=korean_food");
  expect(res.status).toBe(200);
  const rows = await res.json();
  expect(rows.length).toBeGreaterThan(400);
  expect(Object.keys(rows[0]).sort()).toEqual(["region_code", "value"]);
  const codes = new Set(rows.map((r: { value: string }) => r.value));
  expect([...codes].sort()).toEqual(["clear", "insufficient", "orange", "red"]); // 네 판정이 전부 나와야 지도 범례·QA가 가능하다
});

it("학원·어린이집·치킨·편의점·미등록 업종은 404 INDUSTRY_NOT_FOUND (실 API 미러)", async () => {
  for (const industry of ["academy", "childcare", "chicken", "restaurant_other", "convenience_store", "unknown"]) {
    const res = await call(`?industry=${industry}`);
    expect(res.status, industry).toBe(404);
    expect((await res.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
  }
});

it("업종이 다르면 같은 동의 판정이 달라질 수 있다 (해시 기반 결정적)", async () => {
  const a = await (await call("?industry=korean_food")).json();
  const b = await (await call("?industry=cafe")).json();
  expect(a).not.toEqual(b);
  expect(a).toEqual(await (await call("?industry=korean_food")).json());
});
```

```ts
// frontend/src/app/api/mock/verdicts/[regionCode]/route.test.ts
import { expect, it } from "vitest";
import { GET } from "./route";

function call(regionCode: string, query = "?industry=korean_food") {
  return GET(new Request(`http://test/api/mock/verdicts/${regionCode}${query}`), {
    params: Promise.resolve({ regionCode }),
  });
}

it("단건은 신호 5개를 고정 순서로 담고 켜진 개수가 신호와 맞는다", async () => {
  const res = await call("1168064000");
  expect(res.status).toBe(200);
  const v = await res.json();
  expect(v.signals.map((s: { key: string }) => s.key)).toEqual(["net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking"]);
  const strong = v.signals.filter((s: { level: string }) => s.level === "strong").length;
  const on = v.signals.filter((s: { level: string }) => s.level === "on" || s.level === "strong").length;
  expect(v.strong_count).toBe(strong);
  expect(v.on_count).toBe(on);
  for (const s of v.signals) expect(s.evidence.length).toBeGreaterThan(5);
});

it("목록 라우트와 같은 판정 코드를 준다 (두 계약의 원천이 하나)", async () => {
  const { GET: list } = await import("../route");
  const rows = await (await list(new Request("http://test/api/mock/verdicts?industry=korean_food"))).json();
  const row = rows.find((r: { region_code: string }) => r.region_code === "1168064000");
  expect((await (await call("1168064000")).json()).verdict_code).toBe(row.value);
});

it("모르는 동은 404 VERDICT_NOT_FOUND, 판정 대상이 아닌 업종은 404 INDUSTRY_NOT_FOUND", async () => {
  const missing = await call("0000000000");
  expect(missing.status).toBe(404);
  expect((await missing.json()).error.code).toBe("VERDICT_NOT_FOUND");
  const academy = await call("1168064000", "?industry=academy");
  expect((await academy.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run src/app/api/mock/verdicts`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 픽스처·라우트 구현**

`frontend/src/app/api/mock/fixtures.ts` — import 줄에 타입 추가 후 파일 끝에:

```ts
import type { RegionIndustryVerdict, VerdictCode, VerdictRow, VerdictSignal, VerdictSignalKey } from "@/shared/api/types";
import { INDUSTRY_LABELS, type IndustryId } from "@/shared/industries";
import { isVerdictIndustry } from "@/shared/verdict";
```

```ts
// ---------------------------------------------------------------------------
// 판정 카드 mock — 설계서 2026-09-28-verdict-card-design §3. 판정 규칙은 백엔드 rules.py를 그대로 옮긴 것
// (보류 우선 → strong 2+ red → on 1+ orange → clear). 값·근거는 해시 기반 결정적.
// ---------------------------------------------------------------------------

const SIGNAL_KEYS: VerdictSignalKey[] = ["net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking"];
const SIGNAL_SOURCE: Record<VerdictSignalKey, VerdictSignal["source"]> = {
  net_outflow: "store", survival_cliff: "store", early_closure: "store", saturation: "metric", shrinking: "neighborhood",
};

/** 판정 대상 여부 — 실 API의 EXCLUDED_INDUSTRIES 미러 = 프론트 INDUSTRIES 14종 − 편의점(shared/verdict.ts 단일 원천). */
export function isJudgedIndustry(industryId: string): industryId is IndustryId {
  return isVerdictIndustry(industryId);
}

function signalOf(key: VerdictSignalKey, regionCode: string, industryId: string): VerdictSignal {
  const u = unitFrom(hashSeed("verdict", key, regionCode, industryId));
  const name = INDUSTRY_LABELS[industryId as IndustryId] ?? industryId;
  const source = SIGNAL_SOURCE[key];
  // 하위 8%는 미판정(표본 부족), 나머지 92%를 0~100 백분위로 펼친다 — strong(≥90)·red가 실제로 나온다 (Task 9 리뷰에서 잡은 플랜 결함 수정)
  if (u < 0.08) {
    return { key, level: "unavailable", value: null, percentile: null, evidence: `표본 부족 — 3년 전 개업 코호트 ${Math.floor(u * 100)}곳 (10곳 미만)`, source };
  }
  const percentile = Math.round(((u - 0.08) / 0.92) * 1000) / 10; // 0.0 ~ 100.0
  const level = percentile >= 90 ? "strong" : percentile >= 75 ? "on" : "off";
  const top = Math.max(1, Math.round(100 - percentile));
  const EVIDENCE: Record<VerdictSignalKey, string> = {
    net_outflow: `지난 12개월 폐업 ${20 + Math.floor(u * 30)}곳, 개업 ${15 + Math.floor(u * 10)}곳 (순유출률 +${Math.round(u * 20)}%, 서울 ${name} 상위 ${top}%)`,
    survival_cliff: `3년 전 개업한 ${name} 40곳 중 ${40 - Math.floor(u * 25)}곳만 남음 (생존율 ${100 - Math.round(u * 62)}%, 서울 ${name} 하위 ${top}%)`,
    early_closure: `최근 3년 폐업 ${name}의 영업 기간 중위 ${36 - Math.round(u * 20)}개월 (서울 ${name} 하위 ${top}%)`,
    saturation: `상주인구 1,000명당 ${name} ${(2 + u * 9).toFixed(1)}곳 (서울 상위 ${top}%)`,
    shrinking: `서울시 상권변화지표 '${u >= 0.75 ? "상권축소" : "정체"}' (2026년 2분기, 동 전체 기준)`,
  };
  const value = key === "shrinking" ? (u >= 0.75 ? 1 : 0) : Math.round(u * 100) / 100;
  return { key, level, value, percentile: key === "shrinking" ? null : percentile, evidence: EVIDENCE[key], source };
}

function judgeOf(signals: VerdictSignal[]): VerdictCode {
  const evaluable = signals.filter((s) => s.level !== "unavailable").length;
  const strong = signals.filter((s) => s.level === "strong").length;
  const on = signals.filter((s) => s.level === "on" || s.level === "strong").length;
  if (evaluable < 3) return "insufficient";
  if (strong >= 2) return "red";
  if (on >= 1) return "orange";
  return "clear";
}

export function verdictOf(regionCode: string, industryId: string): RegionIndustryVerdict {
  const signals = SIGNAL_KEYS.map((key) => signalOf(key, regionCode, industryId));
  return {
    region_code: regionCode,
    industry_id: industryId,
    verdict_code: judgeOf(signals),
    strong_count: signals.filter((s) => s.level === "strong").length,
    on_count: signals.filter((s) => s.level === "on" || s.level === "strong").length,
    signals,
    computed_at: "2026-09-29T04:30:00+09:00",
  };
}

export function verdictRows(industryId: string): VerdictRow[] {
  return REGIONS.map(({ region_code }) => ({ region_code, value: verdictOf(region_code, industryId).verdict_code }));
}
```

(기존 31행 `import { INDUSTRY_LABELS, type IndustryId } …`는 그대로 두고 `isVerdictIndustry` import 한 줄과 types import만 추가한다 — 중복 import 금지.)

```ts
// frontend/src/app/api/mock/verdicts/route.ts
import { isJudgedIndustry, verdictRows } from "../fixtures";

/** 위험도 단계구분도 — 범주 계약이지만 필드명은 value(실 API 미러). 판정 대상 14종 외는 404. */
export async function GET(request: Request) {
  const industry = new URL(request.url).searchParams.get("industry") ?? "";
  if (!isJudgedIndustry(industry)) {
    return Response.json(
      { error: { code: "INDUSTRY_NOT_FOUND", message: `판정 대상 업종이 아닙니다: ${industry}` } },
      { status: 404 },
    );
  }
  return Response.json(verdictRows(industry));
}
```

```ts
// frontend/src/app/api/mock/verdicts/[regionCode]/route.ts
import { SEOUL_REGIONS_GEOJSON, isJudgedIndustry, verdictOf } from "../../fixtures";

export async function GET(request: Request, { params }: { params: Promise<{ regionCode: string }> }) {
  const { regionCode } = await params;
  const industry = new URL(request.url).searchParams.get("industry") ?? "";
  if (!isJudgedIndustry(industry)) {
    return Response.json(
      { error: { code: "INDUSTRY_NOT_FOUND", message: `판정 대상 업종이 아닙니다: ${industry}` } },
      { status: 404 },
    );
  }
  const known = SEOUL_REGIONS_GEOJSON.features.some((f) => f.properties?.region_code === regionCode);
  if (!known) {
    return Response.json(
      { error: { code: "VERDICT_NOT_FOUND", message: `판정이 없습니다: ${regionCode} × ${industry}` } },
      { status: 404 },
    );
  }
  return Response.json(verdictOf(regionCode, industry));
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npx vitest run src/app/api/mock`
Expected: 신규 6 passed, 기존 mock 계약 테스트 전부 통과

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/app/api/mock
git commit -m "frontend mock: /verdicts 목록·단건 미러 + 결정적 판정 픽스처 + 계약 테스트 (설계서 §5, CLAUDE.md §15)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

### Task 10: 위험도 지도 — API 함수·지표 원천·축 `industry_latest`·범주 팔레트 일반화

**Files:**
- Modify: `frontend/src/features/map-explorer/api.ts` (함수 2개 추가)
- Modify: `frontend/src/features/map-explorer/lib/metric-sources.ts` (`CategoricalMetricSource`에 `palette`·`order`·`labelOf`, `verdict` 엔트리)
- Modify: `frontend/src/features/map-explorer/lib/map-state.ts` (그룹·라벨·직렬화)
- Modify: `frontend/src/features/map-explorer/components/control-bar.tsx:26,93-125` (시점 select 분기)
- Modify: `frontend/src/features/map-explorer/components/map-view.tsx:85-89,349-357` (범주 스케일·안내)
- Modify: `frontend/src/features/map-explorer/components/map-legend.tsx:61-78` (범주 라벨을 source에서)
- Test: `frontend/src/features/map-explorer/lib/map-state.test.ts`, `metric-sources.test.ts`(신규), `components/control-bar.test.tsx`

**Interfaces:**
- Consumes: Task 8 타입·`verdictPalette`·`VERDICT_CODES`·`verdictLabel`; 기존 `neighborhoodPalette`·`NEIGHBORHOOD_TYPES`·`neighborhoodTypeLabel`
- Produces: `fetchVerdictMetrics(industry): Promise<CategoryRow[]>`, `fetchVerdict(regionCode, industry): Promise<RegionIndustryVerdict>`, `CategoricalMetricSource.palette(theme)`·`.order`·`.labelOf(code)`, `METRIC_GROUPS[2] = {key:"verdict", axis:"industry_latest", metrics:["verdict"]}`, `METRIC_LABELS.verdict = "창업 경고"`

- [ ] **Step 1: 실패하는 테스트 작성**

`map-state.test.ts` 끝에 추가:

```ts
it("verdict 지표는 industry_latest 축의 세 번째 무리에 있고 라벨은 '창업 경고'다", () => {
  const group = metricGroupOf("verdict");
  expect(group.key).toBe("verdict");
  expect(group.axis).toBe("industry_latest");
  expect(METRICS).toContain("verdict");
});

it("industry_latest 축에서는 year를 직렬화하지 않고, 파싱하면 기본 연도로 돌아온다", () => {
  const s = { industry: "korean_food", metric: "verdict" as const, year: 2021, year_quarter: null, region: "1168064000", budget: null };
  const params = new URLSearchParams(serializeMapState(s));
  expect(params.get("year")).toBeNull();
  expect(params.get("metric")).toBe("verdict");
  expect(parseMapState(params)).toEqual({ ...s, year: 2026 });
});
```

```ts
// frontend/src/features/map-explorer/lib/metric-sources.test.ts
import { expect, it } from "vitest";
import { METRICS, METRIC_GROUPS, metricGroupOf } from "./map-state";
import { METRIC_SOURCES } from "./metric-sources";

it("모든 지표가 원천을 갖고, 원천의 축은 무리의 축과 같다", () => {
  for (const metric of METRICS) {
    expect(METRIC_SOURCES[metric].axis, metric).toBe(metricGroupOf(metric).axis);
  }
  expect(METRIC_GROUPS.map((g) => g.axis)).toEqual(["region_quarter", "industry_year", "industry_latest"]);
});

it("범주 원천은 팔레트·순서·라벨을 스스로 안다 — 지도·범례가 동네 유형을 하드코딩하지 않는다", () => {
  for (const metric of ["neighborhood_type", "verdict"] as const) {
    const source = METRIC_SOURCES[metric];
    if (source.kind !== "categorical") throw new Error(`${metric}는 범주 원천이어야 한다`);
    expect(source.order.length).toBeGreaterThan(0);
    for (const code of source.order) {
      expect(source.palette("light")[code], `${metric}/${code} light`).toMatch(/^#/);
      expect(source.palette("dark")[code], `${metric}/${code} dark`).toMatch(/^#/);
      expect(source.labelOf(code).name.length).toBeGreaterThan(0);
    }
  }
  const verdict = METRIC_SOURCES.verdict;
  if (verdict.kind !== "categorical") throw new Error();
  expect(verdict.order).toEqual(["red", "orange", "clear", "insufficient"]);
  expect(verdict.queryKey({ industry: "korean_food", year: 2026, yearQuarter: null })).toEqual(["verdicts", "korean_food"]);
});
```

`control-bar.test.tsx` 끝에 추가 (기존 `renderBar` 헬퍼 사용):

```ts
it("창업 경고 지표에서는 연도·분기 셀렉터가 모두 숨고 업종 select는 살아 있다", () => {
  renderBar({ metric: "verdict", industry: "korean_food" });
  expect(screen.queryByRole("combobox", { name: /연도/ })).toBeNull();
  expect(screen.queryByRole("combobox", { name: /분기/ })).toBeNull();
  expect(screen.getByRole("combobox", { name: /업종/ })).toBeInTheDocument();
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run src/features/map-explorer/lib src/features/map-explorer/components/control-bar.test.tsx`
Expected: FAIL — `verdict`가 무리에 없음 / metric-sources 모듈 타입 오류

- [ ] **Step 3: 구현**

`api.ts` — import에 `RegionIndustryVerdict`, `VerdictRow` 추가, 파일 끝에:

```ts
/** 위험도 단계구분도 — 실 API는 {region_code, value}로 주지만 범주 파이프라인(type_code)으로 옮긴다 (작은 ACL). 시점 파라미터 없음(배치 최신). */
export function fetchVerdictMetrics(industry: string): Promise<CategoryRow[]> {
  const params = new URLSearchParams({ industry });
  return apiGet<VerdictRow[]>(`/verdicts?${params.toString()}`).then((rows) =>
    rows.map(({ region_code, value }) => ({ region_code, type_code: value })),
  );
}

/** 판정 카드 단건 — 판정 대상이 아니면 INDUSTRY_NOT_FOUND, 배치 전·모르는 동이면 VERDICT_NOT_FOUND. */
export function fetchVerdict(regionCode: string, industry: string): Promise<RegionIndustryVerdict> {
  const params = new URLSearchParams({ industry });
  return apiGet<RegionIndustryVerdict>(`/verdicts/${regionCode}?${params.toString()}`);
}
```

`metric-sources.ts` — import와 `CategoricalMetricSource`, `METRIC_SOURCES`를 바꾼다:

```ts
import { NEIGHBORHOOD_TYPES, neighborhoodTypeLabel } from "@/shared/neighborhood";
import { VERDICT_CODES, verdictLabel } from "@/shared/verdict";
import { fetchCommerceChangeMetrics, fetchMetrics, fetchProfileMetrics, fetchProfileTypes, fetchVerdictMetrics } from "../api";
import type { ColorScheme } from "./metric-color";
import { neighborhoodPalette, type MapTheme } from "./neighborhood-palette";
import { verdictPalette } from "./verdict-palette";

/** 범주 지표 — {region_code, type_code}. 팔레트·키 순서·라벨을 원천이 스스로 안다 (지도·범례는 이 셋만 읽는다).
 *  한 타입에 value/category를 섞어 한쪽을 null로 두지 않는다 — 판별 합집합으로 나눈다. */
export interface CategoricalMetricSource {
  kind: "categorical";
  axis: MetricAxis;
  queryKey: (query: MetricQuery) => unknown[];
  fetch: (query: MetricQuery) => Promise<CategoryRow[]>;
  palette: (theme: MapTheme) => Record<string, string>;
  order: readonly string[];
  labelOf: (code: string) => { name: string; qualifier: string };
}
```

`METRIC_SOURCES`의 `neighborhood_type` 엔트리에 세 필드를 더하고 `verdict`를 추가:

```ts
  neighborhood_type: {
    kind: "categorical",
    axis: "region_quarter",
    queryKey: ({ yearQuarter }) => ["profile-types", yearQuarter],
    fetch: ({ yearQuarter }) => fetchProfileTypes(yearQuarter ?? undefined),
    palette: neighborhoodPalette,
    order: NEIGHBORHOOD_TYPES,
    labelOf: neighborhoodTypeLabel,
  },
  // 판정 — 업종만 묻고 시점은 배치 최신. year·yearQuarter를 키에 넣으면 같은 응답을 중복 캐싱한다.
  verdict: {
    kind: "categorical",
    axis: "industry_latest",
    queryKey: ({ industry }) => ["verdicts", industry],
    fetch: ({ industry }) => fetchVerdictMetrics(industry),
    palette: verdictPalette,
    order: VERDICT_CODES,
    labelOf: verdictLabel,
  },
```

`map-state.ts`:

```ts
export const METRIC_GROUPS = [
  { key: "region", label: "동네", axis: "region_quarter", metrics: ["neighborhood_type", "night_index", "fnb_share", "operating_months"] },
  { key: "industry", label: "업종", axis: "industry_year", metrics: ["closure_rate", "growth_rate", "store_count"] },
  // 판정 — 연도·분기가 없다(배치 최신). 첫 화면은 여전히 동네 유형(DEFAULT_STATE); 관문이 verdict로 내려놓는 건 후속.
  { key: "verdict", label: "판정", axis: "industry_latest", metrics: ["verdict"] },
] as const satisfies readonly { key: string; label: string; axis: MetricAxis; metrics: readonly MapMetricKey[] }[];
```

`METRIC_LABELS`에 `verdict: "창업 경고",` 추가. `serializeMapState`의 `params.set("year", ...)`를 다음으로:

```ts
  // industry_latest 축은 시점이 없다 — year를 실으면 URL이 "2021년 판정"처럼 읽힌다.
  if (metricGroupOf(state.metric).axis !== "industry_latest") {
    params.set("year", String(state.year));
  }
```

`control-bar.tsx` 26행 아래에 `const latestAxis = group.axis === "industry_latest";` 를 두고, 93~125행의 시점 셀렉터 블록을:

```tsx
      {latestAxis ? null : regionAxis ? (
        <label className={`${styles.yearField} flex flex-col gap-2`}>
          {/* 분기 select — 기존 코드 그대로 */}
        </label>
      ) : (
        <label className={`${styles.yearField} flex flex-col gap-2`}>
          {/* 연도 select — 기존 코드 그대로 */}
        </label>
      )}
```

`metric-coverage.ts` — 편의점×verdict는 백엔드가 404를 주므로 조회 자체를 막고 안내한다. 파일 끝에:

```ts
/** 판정 지표가 없는 업종 — 편의점(스냅샷 원천, 1단계 판정 제외). `map-view`가 fetch를 끄고 안내 문구를 띄운다. */
export function isVerdictMissingForIndustry(metric: MapMetricKey, industry: string): boolean {
  return metric === "verdict" && !isVerdictIndustry(industry);
}
```
(`import { isVerdictIndustry } from "@/shared/verdict";`.) `metric-coverage.test.ts`에 케이스: `("verdict","convenience_store")` true, `("verdict","cafe")` false, `("closure_rate","convenience_store")` false.

`map-view.tsx` — rows 쿼리의 `enabled`에 `&& !isVerdictMissingForIndustry(metric, industry)`를 더하고(기존 enabled 조건이 없으면 `enabled: !isVerdictMissingForIndustry(metric, industry)`), 빈 지도 안내 블록의 조건을 `noData || verdictMissing`으로 넓혀 `verdictMissing`일 때 문구 "편의점은 아직 판정 대상이 아닙니다 — 담배권 특화 신호가 붙으면 열립니다." 를 보여준다(`const verdictMissing = isVerdictMissingForIndustry(metric, industry);`).

`map-view.tsx` 85~89행의 범주 스케일:

```ts
    if (source.kind === "categorical") {
      const codes = (data as CategoryRow[]).map((row) => row.type_code);
      return { kind: "categorical" as const, ...makeCategoryColorScale(codes, source.palette(theme), source.order) };
    }
```
(`NEIGHBORHOOD_TYPES`·`neighborhoodPalette` import는 map-view에서 제거한다 — 더 이상 쓰지 않는다.) 349~357행의 빈 지도 안내 삼항에 `industry_latest` 분기 하나를 넣는다:

```tsx
            : source.axis === "industry_latest"
              ? "이 업종의 판정이 아직 없습니다. 새벽 배치 후 다시 확인해 주세요."
```
(`region_quarter` 분기 앞에.)

`map-legend.tsx` 61~78행 `CategoryRows`가 `neighborhoodTypeLabel` 대신 원천의 `labelOf`를 받는다:

```tsx
function CategoryRows({ classes, labelOf }: { classes: CategoryColorClass[]; labelOf: (code: string) => { name: string; qualifier: string } }) {
  return (
    <>
      {classes.map(({ color, code }) => {
        const label = labelOf(code);
        return (
          <li key={code} className="flex items-center gap-2 text-[11px] leading-none text-[var(--text-secondary)]">
            <span aria-hidden className="h-3 w-3 shrink-0 rounded-[2px]" style={{ backgroundColor: color }} />
            <span className="text-[var(--text-primary)]">{label.name}</span>
            <span>({label.qualifier})</span>
          </li>
        );
      })}
    </>
  );
}
```
호출부(91행): `const source = METRIC_SOURCES[metric];` 를 `MapLegend` 첫 줄에 두고 `<CategoryRows classes={scale.classes} labelOf={source.kind === "categorical" ? source.labelOf : (code) => ({ name: code, qualifier: "" })} />`. `neighborhoodTypeLabel` import는 제거, `METRIC_SOURCES` import 추가.

- [ ] **Step 4: 통과 확인 + 전체**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: tsc 통과, 전체 통과(기존 326 + 신규). `metric-coverage.test.ts`가 `METRICS` 전부를 `industry_year`/`region_quarter`로 가정해 깨지면 `industry_latest`를 "연도를 쓰지 않는 축"으로 같은 기대(`availableYears === YEARS`)에 넣는다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/features/map-explorer frontend/src/shared
git commit -m "frontend: 창업 경고 지도 — verdict 범주 지표, industry_latest 축(연도 select 숨김), 범주 팔레트·라벨을 원천이 소유 (설계서 §5-2)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

### Task 11: 판정 카드 — 훅·`VerdictSection`·사이드패널 삽입 + 버전 로그

**Files:**
- Create: `frontend/src/features/map-explorer/hooks/use-verdict.ts`
- Create: `frontend/src/features/map-explorer/components/verdict-section.tsx`
- Modify: `frontend/src/features/map-explorer/components/side-panel.tsx:108-115` (`regionCode &&` 블록 첫 줄)
- Modify: `frontend/docs/frontend_ver_log.md`, 설계서 §11
- Test: `frontend/src/features/map-explorer/components/verdict-section.test.tsx`

**Interfaces:**
- Consumes: Task 10 `fetchVerdict`, Task 8 `verdictLabel`·`signalLabel`, `ApiError`(`@/shared/api/client`), `industryLabel`
- Produces: `useVerdict(regionCode, industry)`, `VerdictSection({ regionCode, industry })`

- [ ] **Step 1: 실패하는 테스트 작성**

```tsx
// frontend/src/features/map-explorer/components/verdict-section.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { RegionIndustryVerdict, VerdictSignal } from "@/shared/api/types";
import { ApiError } from "@/shared/api/client";
import * as api from "../api";
import { VerdictSection } from "./verdict-section";

const signal = (key: VerdictSignal["key"], level: VerdictSignal["level"], evidence: string): VerdictSignal => ({
  key, level, value: 0.1, percentile: level === "unavailable" ? null : 80, evidence, source: "store",
});

function verdict(code: RegionIndustryVerdict["verdict_code"], signals: VerdictSignal[]): RegionIndustryVerdict {
  return {
    region_code: "1168064000", industry_id: "korean_food", verdict_code: code,
    strong_count: signals.filter((s) => s.level === "strong").length,
    on_count: signals.filter((s) => s.level === "on" || s.level === "strong").length,
    signals, computed_at: "2026-09-29T04:30:00+09:00",
  };
}

const FIVE = [
  signal("net_outflow", "on", "순유출 근거"),
  signal("survival_cliff", "strong", "생존 근거"),
  signal("early_closure", "off", "조기폐업 근거"),
  signal("saturation", "unavailable", "표본 부족 — 상주인구 900명"),
  signal("shrinking", "strong", "상권축소 근거"),
];

function renderSection() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <VerdictSection regionCode="1168064000" industry="korean_food" />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

it("판정 배지와 켜진 신호를 강함 먼저 보여주고, 근거 보기를 펼치면 5개 전부 나온다", async () => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("red", FIVE));
  renderSection();
  expect(await screen.findByRole("status", { name: /비추천/ })).toBeInTheDocument();
  const fired = screen.getAllByTestId("fired-signal").map((el) => el.textContent);
  expect(fired[0]).toContain("생존 절벽");
  expect(fired[1]).toContain("상권 축소");
  expect(fired[2]).toContain("순유출");
  expect(fired).toHaveLength(3);
  expect(screen.queryByText("표본 부족 — 상주인구 900명")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /근거 보기/ }));
  expect(screen.getByText("표본 부족 — 상주인구 900명")).toBeInTheDocument();
  expect(screen.getAllByTestId("all-signal")).toHaveLength(5);
});

it("경고 없음·보류 판정은 켜진 신호 목록 대신 한 줄 설명을 보여준다", async () => {
  vi.spyOn(api, "fetchVerdict").mockResolvedValue(verdict("insufficient", FIVE.map((s) => ({ ...s, level: "unavailable" }))));
  renderSection();
  expect(await screen.findByRole("status", { name: /판정 보류/ })).toBeInTheDocument();
  expect(screen.queryAllByTestId("fired-signal")).toHaveLength(0);
  expect(screen.getByText(/표본 부족/)).toBeInTheDocument();
});

it("판정 제외 업종(편의점)은 요청 없이 섹션을 그리지 않는다", () => {
  const spy = vi.spyOn(api, "fetchVerdict");
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const { container } = render(
    <QueryClientProvider client={client}>
      <VerdictSection regionCode="1168064000" industry="convenience_store" />
    </QueryClientProvider>,
  );
  expect(container.querySelector("section")).toBeNull();
  expect(spy).not.toHaveBeenCalled();
});

it("판정이 없는 조합(404)은 섹션을 그리지 않는다", async () => {
  vi.spyOn(api, "fetchVerdict").mockRejectedValue(new ApiError("VERDICT_NOT_FOUND", "판정이 없습니다"));
  const { container } = renderSection();
  await new Promise((r) => setTimeout(r, 0));
  expect(container.querySelector("section")).toBeNull();
});

it("그 외 오류는 한 줄 안내를 보여준다", async () => {
  vi.spyOn(api, "fetchVerdict").mockRejectedValue(new Error("network"));
  renderSection();
  expect(await screen.findByRole("alert")).toHaveTextContent("판정을 불러오지 못했습니다");
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run src/features/map-explorer/components/verdict-section.test.tsx`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 훅·컴포넌트 구현, 사이드패널 삽입**

```ts
// frontend/src/features/map-explorer/hooks/use-verdict.ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/client";
import { isVerdictIndustry } from "@/shared/verdict";
import { fetchVerdict } from "../api";

/** 판정 카드 조회 — 404(판정 없음·대상 아님)는 재시도하지 않는다. queryKey는 ["verdict", 동, 업종]. */
export function useVerdict(regionCode: string, industry: string) {
  return useQuery({
    queryKey: ["verdict", regionCode, industry],
    queryFn: () => fetchVerdict(regionCode, industry),
    // 편의점처럼 판정 대상이 아닌 업종은 요청하지 않는다(백엔드 404) — 카드는 isPending이 아니라 idle이 되어 그리지 않는다
    enabled: isVerdictIndustry(industry),
    retry: (count, error) => !(error instanceof ApiError) && count < 1,
  });
}
```

```tsx
// frontend/src/features/map-explorer/components/verdict-section.tsx
"use client";

import { useState } from "react";
import type { VerdictCode, VerdictSignal } from "@/shared/api/types";
import { ApiError } from "@/shared/api/client";
import { industryLabel } from "@/shared/industries";
import { signalLabel, verdictLabel } from "@/shared/verdict";
import { useVerdict } from "../hooks/use-verdict";

/** 판정 → 배지 색 토큰. 🔴 --danger · 🟠 --warn · ⚪ 보조 텍스트 · 보류 테두리색 (조건 분기 대신 테이블). */
const BADGE_TOKEN: Record<VerdictCode, string> = {
  red: "var(--danger)",
  orange: "var(--warn)",
  clear: "var(--text-secondary)",
  insufficient: "var(--border)",
};

const LEVEL_LABEL: Record<VerdictSignal["level"], string> = {
  strong: "강함",
  on: "켜짐",
  off: "꺼짐",
  unavailable: "미판정",
};

/** 켜진 신호만, strong 먼저. 백엔드 순서(SIGNAL_KEYS)는 같은 레벨 안에서 유지된다(안정 정렬). */
function firedSignals(signals: VerdictSignal[]): VerdictSignal[] {
  const rank: Record<VerdictSignal["level"], number> = { strong: 0, on: 1, off: 2, unavailable: 3 };
  return signals.filter((s) => s.level === "strong" || s.level === "on").sort((a, b) => rank[a.level] - rank[b.level]);
}

/** 404(판정 없음·판정 대상 아님)는 카드를 그리지 않는다 — 학원·어린이집·배치 전 조합의 정상 동작. */
function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && (error.code === "VERDICT_NOT_FOUND" || error.code === "INDUSTRY_NOT_FOUND");
}

interface VerdictSectionProps {
  regionCode: string;
  industry: string;
}

export function VerdictSection({ regionCode, industry }: VerdictSectionProps) {
  const query = useVerdict(regionCode, industry);
  const [open, setOpen] = useState(false);

  if (!isVerdictIndustry(industry)) return null; // 편의점 등 판정 제외 업종 — 요청도 카드도 없음
  if (query.isPending) {
    return <div className="mt-4 h-16 rounded-lg bg-[var(--bg-raised)]" aria-hidden />;
  }
  if (query.isError) {
    if (isNotFound(query.error)) return null;
    return (
      <p role="alert" className="mt-4 text-xs text-[var(--danger)]">
        판정을 불러오지 못했습니다.
      </p>
    );
  }

  const verdict = query.data;
  const label = verdictLabel(verdict.verdict_code);
  const fired = firedSignals(verdict.signals);
  const color = BADGE_TOKEN[verdict.verdict_code];

  return (
    <section className="mt-4 flex flex-col gap-3" aria-label="창업 경고 판정">
      <div
        role="status"
        aria-label={`${industryLabel(industry)} 판정: ${label.name}`}
        className="flex items-baseline gap-2 rounded-lg border px-3 py-2"
        style={{ borderColor: color }}
      >
        <span className="text-lg font-semibold" style={{ color }}>{label.name}</span>
        <span className="text-xs text-[var(--text-secondary)]">{label.qualifier}</span>
      </div>

      {fired.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {fired.map((s) => (
            <li key={s.key} data-testid="fired-signal" className="text-sm leading-snug">
              <span className="font-medium text-[var(--text-primary)]">{signalLabel(s.key)}</span>
              <span className="ml-1 text-[11px]" style={{ color: s.level === "strong" ? "var(--danger)" : "var(--warn)" }}>
                {LEVEL_LABEL[s.level]}
              </span>
              <p className="text-[var(--text-secondary)]">{s.evidence}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-[var(--text-secondary)]">
          {verdict.verdict_code === "insufficient"
            ? "표본 부족으로 판정을 보류했습니다. 아래 근거에서 어떤 신호가 빠졌는지 볼 수 있습니다."
            : "서울 같은 업종 동네와 비교해 켜진 경고 신호가 없습니다."}
        </p>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="self-start text-xs text-[var(--accent)] underline-offset-2 hover:underline"
      >
        {open ? "근거 접기" : "근거 보기"}
      </button>
      {open && (
        <ul className="flex flex-col gap-1.5 border-t border-[var(--border)] pt-2 text-xs">
          {verdict.signals.map((s) => (
            <li key={s.key} data-testid="all-signal" className="flex flex-col">
              <span>
                <span className="text-[var(--text-primary)]">{signalLabel(s.key)}</span>
                <span className="ml-1 text-[var(--text-secondary)]">
                  · {LEVEL_LABEL[s.level]}
                  {s.percentile !== null && <span className="tabular-nums"> · 서울 상위 {Math.max(1, Math.round(100 - s.percentile))}%</span>}
                </span>
              </span>
              <span className="text-[var(--text-secondary)]">{s.evidence}</span>
            </li>
          ))}
          <li className="text-[10px] text-[var(--text-secondary)]">
            상대평가 — 같은 업종의 서울 행정동 분포에서 상위 25%면 켜짐, 상위 10%면 강함. 산출 {verdict.computed_at.slice(0, 10)}
          </li>
        </ul>
      )}
    </section>
  );
}
```

`side-panel.tsx` — import 추가 `import { VerdictSection } from "./verdict-section";` 후 108행 `{regionCode && (` 블록의 첫 자식으로:

```tsx
          <VerdictSection regionCode={regionCode} industry={industry} />
```
(`NeighborhoodProfileSection` 바로 위.)

- [ ] **Step 4: 통과 확인 + 전체 + 실 화면**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 전부 통과. 이어서 실 API로 확인 (3200 dev 서버는 `/api/backend` → 8201):

```bash
curl -s "http://127.0.0.1:3200/api/backend/verdicts/1168064000?industry=korean_food" | head -c 300
curl -s "http://127.0.0.1:3200/map?region=1168064000&industry=korean_food" | grep -o '창업 경고 판정\|비추천\|조건부\|경고 없음\|판정 보류' | sort | uniq -c
```
Expected: JSON 카드, SSR 출력에 `창업 경고 판정` 라벨(클라이언트 훅이라 판정 문구는 하이드레이션 후 — 노트북 브라우저에서 역삼1동 한식 카드가 헤더 바로 아래 뜨는지 확인).

- [ ] **Step 5: 버전 로그·설계서 §11**

`frontend/docs/frontend_ver_log.md` 맨 위 헤더 아래에:

```markdown
## [v0.29.0] - 2026-09-29

### Added
- **판정 카드** — 사이드패널 헤더 바로 아래 `VerdictSection`. 큰 판정 배지(비추천·조건부·경고 없음·판정 보류) + 켜진 신호를
  강함 먼저 나열(백엔드 근거 문장 그대로) + "근거 보기" 펼침에 5개 신호 전부. 404(판정 없음·대상 아님)는 섹션을 그리지 않는다.
  관문 → `/map?region&industry`이므로 이 카드가 첫 화면(HANDOFF §0-4).
- **창업 경고 지도** — 세 번째 지표 무리 `판정`(축 `industry_latest`: 연도·분기 select 숨김, URL에 year 미직렬화).
  범주 팔레트 4색 `lib/verdict-palette.ts`, 범례 라벨은 `shared/verdict.ts`.
- mock `/api/mock/verdicts`·`/verdicts/[regionCode]` + 결정적 픽스처 + 계약 테스트.

### Changed
- 범주 지표 원천(`CategoricalMetricSource`)이 팔레트·키 순서·라벨을 스스로 갖는다 — 지도·범례의 동네 유형 하드코딩 제거.

### Validation
- Vitest **N/N**, `tsc --noEmit`. 실 API 역삼1동 한식 카드 확인.
```

설계서 §11 진행 기록에 2단계 행 추가.

- [ ] **Step 6: 커밋·푸시**

```bash
git add frontend docs/superpowers/specs/2026-09-28-verdict-card-design.md
git commit -m "frontend v0.29.0: 판정 카드 + 창업 경고 지도 — VerdictSection, verdict 범주 지표, industry_latest 축 (설계서 2단계)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git push origin main
```

---

## 3단계 — 폐업 마커 (BE v0.40.1 · FE v0.29.1)

### Task 12: 백엔드 — `GET /stores?status=open|closed` + `close_date`

**Files:**
- Modify: `backend/apps/store/domain/errors.py` (`StoreStatusNotFoundError` 추가)
- Modify: `backend/apps/store/app/ports/output/store_port.py:26-27` (`list_closed_since` 추가)
- Modify: `backend/apps/store/adapter/outbound/repositories/store_repository.py:91-108` 뒤 (`list_closed_since` 구현)
- Modify: `backend/apps/store/app/ports/input/store_use_case.py:21-25` (`list_stores` 추가)
- Modify: `backend/apps/store/app/use_cases/store_interactor.py:59-65` (`list_stores` + Strategy 맵)
- Modify: `backend/apps/store/adapter/inbound/api/schemas/store_schema.py:24-32` (`close_date`)
- Modify: `backend/apps/store/adapter/inbound/mappers/store_mapper.py:16-24` (`close_date`)
- Modify: `backend/apps/store/adapter/inbound/api/v1/store_router.py:26-44` (`status` 파라미터·404)
- Modify: `backend/tests/test_store_list_open.py` (`FakeRepository.list_closed_since` + 케이스 2개)
- Test: `backend/tests/test_store_list_closed_repository.py` (신규, 실 DB)
- Modify: `backend/docs/backend_ver_log.md`

**Interfaces:**
- Produces: `StoreRepositoryPort.list_closed_since(region_code, industry_id, since: date) -> list[Store]`, `StoreUseCase.list_stores(region_code, industry_id, status: str) -> list[StoreDto]`, `StoreStatusNotFoundError`, `StoreMarkerResponse.close_date: date | None`, `GET /stores?region&industry&status=` (기본 `open`, 미지원 → 404 `STORE_STATUS_NOT_FOUND`)

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_store_list_open.py` — `FakeRepository`에 메서드 추가:

```python
    def list_closed_since(self, region_code: str, industry_id: str, since):
        return [
            s
            for s in self._stores
            if s.region_code == region_code
            and s.industry_id == industry_id
            and s.close_date is not None
            and s.close_date >= since
            and s.lat is not None
            and s.lng is not None
        ]
```

같은 파일의 기존 `test_stores_endpoint_returns_marker_contract`는 응답에 `close_date`가 생기므로 기대 JSON에 `"close_date": None,` 한 줄을 추가한다(`"open_date"` 다음). 파일 끝에 케이스 2개 — 파일의 기존 헬퍼 `_store(store_id, open_date)`·`_client(stores)`를 그대로 쓴다:

```python
from datetime import timedelta
from dataclasses import replace


def test_status_closed는_최근_폐업_점포를_close_date와_함께_준다():
    closed = replace(_store("c1"), close_date=date.today() - timedelta(days=30), status_name="폐업")
    client = _client([_store("s1"), closed])
    res = client.get("/stores?region=1168064000&industry=cafe&status=closed")
    assert res.status_code == 200
    body = res.json()
    assert [s["store_id"] for s in body] == ["c1"]
    assert body[0]["close_date"] == closed.close_date.isoformat()
    assert body[0]["status_name"] == "폐업"
    # 기본값(open)에는 폐업 점포가 없고 close_date는 null
    default = client.get("/stores?region=1168064000&industry=cafe").json()
    assert [s["store_id"] for s in default] == ["s1"]
    assert default[0]["close_date"] is None


def test_미지원_status는_404_STORE_STATUS_NOT_FOUND():
    res = _client([_store("s1")]).get("/stores?region=1168064000&industry=cafe&status=bogus")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "STORE_STATUS_NOT_FOUND"
```
(`Store`는 frozen dataclass가 아니면 `replace` 대신 `_store` 호출 뒤 필드를 바꾼다. import 두 줄은 파일 상단 import 블록에 합친다.)

```python
# backend/tests/test_store_list_closed_repository.py
"""폐업 점포 조회 리포지토리 — since 경계·좌표 없는 행 제외 (실 DB)."""

from datetime import date, datetime, timedelta

from sqlalchemy import delete, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.store.adapter.outbound.repositories.store_repository import SqlAlchemyStoreRepository
from core.matrix.grid_oracle_database_manager import session_scope

_PREFIX = "test-closed-"
_TODAY = date(2099, 6, 30)


def _region_code() -> str:
    with session_scope() as session:
        return session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)).scalar_one()


def _store(n: int, region: str, close_date: date | None, lat: float | None = 37.5) -> StoreOrm:
    return StoreOrm(
        store_id=f"{_PREFIX}{n}", name=f"폐업시험{n}", industry_id="cafe", district_code=region[:5], region_code=region,
        subcategory_id=None, open_date=date(2095, 1, 1), close_date=close_date, status_code="03",
        status_name="폐업" if close_date else "영업", lat=lat, lng=None if lat is None else 127.0,
        road_address=None, jibun_address=None, source_updated_at=datetime(2099, 1, 1),
    )


def test_since_이후_폐업_좌표_보유_행만():
    region = _region_code()
    since = _TODAY - timedelta(days=730)
    rows = [
        _store(1, region, since),                      # 경계 포함
        _store(2, region, since - timedelta(days=1)),  # 경계 밖
        _store(3, region, _TODAY, lat=None),           # 좌표 없음 → 제외
        _store(4, region, None),                       # 영업 중 → 제외
    ]
    try:
        with session_scope() as session:
            session.add_all(rows)
        found = SqlAlchemyStoreRepository().list_closed_since(region, "cafe", since)
        assert [s.store_id for s in found if s.store_id.startswith(_PREFIX)] == [f"{_PREFIX}1"]
    finally:
        with session_scope() as session:
            session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_PREFIX}%")))
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_store_list_open.py tests/test_store_list_closed_repository.py -q`
Expected: FAIL — `list_closed_since` 없음 / `TypeError: Can't instantiate abstract class` (포트 추가 전엔 Fake가 먼저 깨지지 않으니 구현 순서대로 진행)

- [ ] **Step 3: 구현**

`domain/errors.py` 끝에:

```python
class StoreStatusNotFoundError(Exception):
    """지원하지 않는 status 값 (open | closed)."""
```

`store_port.py` `StoreRepositoryPort.list_open` 아래에:

```python
    @abstractmethod
    def list_closed_since(self, region_code: str, industry_id: str, since: date) -> list[Store]:
        """해당 행정동×업종의 폐업 점포(close_date ≥ since)·좌표 보유 목록 — 폐업 마커용."""
```
(`from datetime import date` import 추가.)

`store_repository.py` `list_open` 아래에:

```python
    def list_closed_since(self, region_code: str, industry_id: str, since: date) -> list[Store]:
        with session_scope() as session:
            rows = (
                session.execute(
                    select(StoreOrm)
                    .where(
                        StoreOrm.region_code == region_code,
                        StoreOrm.industry_id == industry_id,
                        StoreOrm.close_date.is_not(None),
                        StoreOrm.close_date >= since,
                        StoreOrm.lat.is_not(None),
                        StoreOrm.lng.is_not(None),
                    )
                    .order_by(StoreOrm.close_date.desc(), StoreOrm.store_id)
                )
                .scalars()
                .all()
            )
            return [to_entity(row) for row in rows]
```

`store_use_case.py` `list_open_stores` 아래에:

```python
    @abstractmethod
    def list_stores(self, region_code: str, industry_id: str, status: str) -> list[StoreDto]:
        """지도 마커용 — status=open은 list_open_stores와 같고, closed는 최근 2년 폐업 점포.

        미등록 업종은 IndustryNotFoundError, 미지원 status는 StoreStatusNotFoundError.
        """
```

`store_interactor.py` — 모듈 상단에 Strategy 테이블(if/else 금지), `list_open_stores` 아래에 `list_stores`:

```python
from datetime import date, timedelta
from apps.store.domain.errors import IndustryNotFoundError, StoreStatusNotFoundError

_CLOSED_WINDOW_DAYS = 730  # 최근 2년 (설계서 §6-1)

# status → 조회 전략. 새 상태는 항목 추가로 끝난다.
_LISTERS: dict[str, Callable[[StoreRepositoryPort, str, str], list[Store]]] = {
    "open": lambda repo, region, industry: repo.list_open(region, industry),
    "closed": lambda repo, region, industry: repo.list_closed_since(
        region, industry, date.today() - timedelta(days=_CLOSED_WINDOW_DAYS)
    ),
}
```

```python
    def list_stores(self, region_code: str, industry_id: str, status: str) -> list[StoreDto]:
        lister = _LISTERS.get(status)
        if lister is None:
            raise StoreStatusNotFoundError(status)
        if not self._industry_catalog.exists(industry_id):
            raise IndustryNotFoundError(industry_id)
        return [StoreDto(**asdict(store)) for store in lister(self._repository, region_code, industry_id)]
```
(`from collections.abc import Callable`, `Store` 엔티티 import가 없으면 추가.)

`store_schema.py` `StoreMarkerResponse`에 `close_date: date | None = None` 추가, docstring을 "좌표 보유 점포. status=open은 영업 중(close_date null), closed는 최근 2년 폐업"으로.
`store_mapper.py` `to_marker_response`에 `close_date=dto.close_date,` 추가.

`store_router.py` `list_open_stores`를:

```python
@router.get("", response_model=list[StoreMarkerResponse])
def list_stores(
    region: str,
    industry: str,
    status: str = "open",
    use_case: StoreUseCase = Depends(get_store_use_case),
) -> list[StoreMarkerResponse] | JSONResponse:
    try:
        stores = use_case.list_stores(region, industry, status)
    except StoreStatusNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "STORE_STATUS_NOT_FOUND", "message": f"지원하지 않는 status: {status} (open | closed)"}},
        )
    except IndustryNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "INDUSTRY_NOT_FOUND", "message": f"지원하지 않는 industry: {industry}"}},
        )
    return [to_marker_response(store) for store in stores]
```

- [ ] **Step 4: 통과 확인 + 전체 회귀**

Run: `cd backend && .venv/bin/python -m pytest tests/test_store_list_open.py tests/test_store_list_closed_repository.py -q && .venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: 전부 통과. 실 API: `curl -s "http://127.0.0.1:8201/stores?region=1168064000&industry=korean_food&status=closed" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(len(d), d[0] if d else None)'` → 역삼1동 한식 2년 폐업 건수·첫 행에 `close_date`. **1,000 초과면** 설계서 §9대로 §11에 기록하고 상한 도입 여부를 사용자에게 묻는다.

- [ ] **Step 5: 버전 로그·커밋**

`backend/docs/backend_ver_log.md`에 `## [v0.40.1] - 2026-09-29` / `### Added` — `GET /stores?status=open|closed`(기본 open, closed = 최근 2년 폐업·좌표 보유), `StoreMarkerResponse.close_date`. 미지원 status 404 `STORE_STATUS_NOT_FOUND`. 리포지토리 `list_closed_since`, 인터랙터 Strategy 맵. / `### Validation` — 신규 테스트 3, 전체 N passed, 역삼1동 한식 폐업 K건.

```bash
git add backend
git commit -m "backend v0.40.1: GET /stores?status=closed — 최근 2년 폐업 점포 마커 + close_date (설계서 §6-1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

### Task 13: 프론트 — 폐업 마커 전략·레이어 파라미터화·토글·건수 + 버전 로그

**Files:**
- Modify: `frontend/src/shared/api/types.ts` (`Store.close_date: string | null`)
- Modify: `frontend/src/features/map-explorer/api.ts:37-40` (`fetchStores` status)
- Modify: `frontend/src/app/api/mock/stores/route.ts`, `fixtures.ts:109-120` (`storesOf` status)
- Modify: `frontend/src/features/map-explorer/components/marker-strategies.ts` (`CLOSED_STORE_STRATEGY` export)
- Modify: `frontend/src/features/map-explorer/components/region-markers.tsx` (전략·소스 id·색 토큰 props)
- Modify: `frontend/src/features/map-explorer/components/map-view.tsx` (`showClosed` prop → 두 번째 `RegionMarkers`)
- Modify: `frontend/src/features/map-explorer/components/map-page.tsx` (`showClosed` 상태)
- Modify: `frontend/src/features/map-explorer/components/side-panel.tsx` (토글 + 건수 한 줄)
- Modify: `frontend/docs/frontend_ver_log.md`, 설계서 §11, `docs/HANDOFF.md` §0-7
- Test: `src/app/api/mock/stores/route.test.ts`, `components/marker-strategies.test.ts`, `components/side-panel.test.tsx`

**Interfaces:**
- Consumes: Task 12 API 계약
- Produces: `fetchStores(regionCode, industry, status: "open" | "closed" = "open")`, `CLOSED_STORE_STRATEGY: MarkerStrategy<Store>`, `RegionMarkers` props `strategy?`·`sourceId?`·`colorVar?`, `MapView` prop `showClosed: boolean`, `SidePanel` props `showClosed`·`onToggleClosed`

- [ ] **Step 1: 실패하는 테스트 작성**

`src/app/api/mock/stores/route.test.ts` 끝에:

```ts
it("status=closed는 폐업 점포만 close_date와 함께 주고, 기본값은 close_date가 null이다", async () => {
  const closed = await (await GET(new Request("http://test/api/mock/stores?region=1168052100&industry=cafe&status=closed"))).json();
  expect(closed.length).toBeGreaterThan(0);
  for (const s of closed) {
    expect(s.status_name).toBe("폐업");
    expect(s.close_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  }
  const open = await (await GET(new Request("http://test/api/mock/stores?region=1168052100&industry=cafe"))).json();
  for (const s of open) expect(s.close_date).toBeNull();
});

it("미지원 status는 404 STORE_STATUS_NOT_FOUND", async () => {
  const res = await GET(new Request("http://test/api/mock/stores?region=1168052100&industry=cafe&status=bogus"));
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("STORE_STATUS_NOT_FOUND");
});
```

`components/marker-strategies.test.ts` 끝에:

```ts
it("폐업 전략은 stores-closed 키로 조회하고 팝업에 폐업일과 영업 개월을 쓴다", () => {
  expect(CLOSED_STORE_STRATEGY.queryKey("1168064000", "korean_food")).toEqual(["stores-closed", "1168064000", "korean_food"]);
  const popup = CLOSED_STORE_STRATEGY.buildPopup({
    store_id: "x", name: "문닫은집", lat: 37.5, lng: 127.0, status_name: "폐업", open_date: "2023-01-10", close_date: "2025-01-10",
  });
  expect(popup.textContent).toContain("폐업일 2025-01-10");
  expect(popup.textContent).toContain("영업 24개월");
});
```
(파일 상단 import에 `CLOSED_STORE_STRATEGY` 추가.)

`components/side-panel.test.tsx` 끝에 (파일의 기존 렌더 헬퍼·QueryClient 구성을 재사용):

```tsx
it("폐업 점포 토글을 켜면 최근 2년 폐업 건수를 한 줄로 보여준다", async () => {
  vi.spyOn(api, "fetchStores").mockResolvedValue([
    { store_id: "c1", name: "a", lat: 37.5, lng: 127, status_name: "폐업", open_date: "2023-01-01", close_date: "2025-01-01" },
    { store_id: "c2", name: "b", lat: 37.5, lng: 127, status_name: "폐업", open_date: "2023-02-01", close_date: "2025-02-01" },
  ]);
  const onToggle = vi.fn();
  renderPanel({ regionCode: "1168064000", industry: "korean_food", showClosed: true, onToggleClosed: onToggle });
  expect(await screen.findByText(/최근 2년 한식 2곳 폐업/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("checkbox", { name: /최근 2년 폐업 점포 보기/ }));
  expect(onToggle).toHaveBeenCalledWith(false);
});
```
(`renderPanel`이 없으면 기존 테스트의 `render(<QueryClientProvider ...><SidePanel .../></QueryClientProvider>)` 구문을 헬퍼로 뽑아 props를 받게 한다. `vi.spyOn(api, ...)`의 `api`는 `import * as api from "../api"`.)

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run src/app/api/mock/stores src/features/map-explorer/components/marker-strategies.test.ts src/features/map-explorer/components/side-panel.test.tsx`
Expected: FAIL — `CLOSED_STORE_STRATEGY` 없음 / status 미지원 / 토글 없음

- [ ] **Step 3: 구현**

`types.ts` `Store`에 `close_date: string | null; // status=open이면 null` 추가.

`api.ts`:

```ts
export type StoreStatus = "open" | "closed";

/** 점포 마커 — status=closed는 최근 2년 폐업(백엔드 창). 기본 open은 기존 계약 그대로. */
export function fetchStores(regionCode: string, industry: string, status: StoreStatus = "open"): Promise<Store[]> {
  const params = new URLSearchParams({ region: regionCode, industry, status });
  return apiGet<Store[]>(`/stores?${params.toString()}`);
}
```

`fixtures.ts` `storesOf`를 status 인자로:

```ts
const OPEN_STATUSES = new Set(["영업", "영업중"]);

/** 결정적 폐업일 — 개업일 + (해시 % 36 + 3)개월. 표본에 폐업일 컬럼이 없어 여기서 만든다. */
function closeDateOf(sample: StoreSample): string {
  const months = (hashSeed("close", sample.store_id) % 36) + 3;
  const d = new Date(sample.open_date);
  d.setMonth(d.getMonth() + months);
  return d.toISOString().slice(0, 10);
}

export function storesOf(regionCode: string, industryId: string, status: "open" | "closed" = "open"): Store[] {
  const samples = (STORE_SAMPLES[regionCode] ?? []).filter((s) => s.industry_id === industryId);
  const picked = status === "closed" ? samples.filter((s) => !OPEN_STATUSES.has(s.status_name)) : samples;
  return picked.map(({ store_id, name, lat, lng, status_name, open_date }) => ({
    store_id, name, lat, lng, status_name, open_date,
    close_date: status === "closed" ? closeDateOf({ store_id, name, lat, lng, status_name, open_date, industry_id: industryId }) : null,
  }));
}
```

`mock/stores/route.ts` — `industry` 가드 뒤에:

```ts
  const status = searchParams.get("status") ?? "open";
  if (status !== "open" && status !== "closed") {
    return Response.json(
      { error: { code: "STORE_STATUS_NOT_FOUND", message: `지원하지 않는 status: ${status} (open | closed)` } },
      { status: 404 },
    );
  }
  return Response.json(storesOf(region, industry, status));
```

`marker-strategies.ts` — `STORE_STRATEGY` 아래에:

```ts
function monthsBetween(from: string, to: string): number {
  const a = new Date(from), b = new Date(to);
  return Math.max(0, (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth()));
}

/** 최근 2년 폐업 점포 — 영업 마커 위에 얹는 별도 레이어(--danger). 팝업은 언제 열고 얼마나 버텼는지. */
export const CLOSED_STORE_STRATEGY: MarkerStrategy<Store> = {
  queryKey: (regionCode, industry) => ["stores-closed", regionCode, industry],
  fetch: (regionCode, industry) => fetchStores(regionCode, industry, "closed"),
  buildPopup: (store) =>
    popupContent([
      { text: store.name, bold: true },
      { text: `개업일 ${store.open_date} · 폐업일 ${store.close_date ?? "-"}`, color: "var(--text-secondary)" },
      {
        text: store.close_date && store.open_date ? `영업 ${monthsBetween(store.open_date, store.close_date)}개월` : store.status_name,
        color: "var(--danger)",
        bold: true,
      },
    ]),
};
```

`region-markers.tsx` — 소스·레이어 id를 props에서 파생하고 색 토큰을 받는다:

```tsx
interface RegionMarkersProps {
  mapRef: RefObject<MapLibreGLMap | null>;
  ready: boolean;
  regionCode: string | null | undefined;
  industry: string;
  /** 기본은 업종별 전략(markerStrategyOf). 폐업 레이어는 CLOSED_STORE_STRATEGY를 넘긴다. */
  strategy?: MarkerStrategy<MarkerPoint>;
  /** 한 지도에 레이어를 둘 얹으려면 소스 id가 달라야 한다. */
  sourceId?: string;
  /** 마커·클러스터 색 토큰. WebGL은 var()를 모르므로 계산값을 읽어 넘긴다. */
  colorVar?: string;
}

export function RegionMarkers({
  mapRef, ready, regionCode, industry, strategy: strategyProp, sourceId = "markers", colorVar = "--accent",
}: RegionMarkersProps) {
  const strategy = strategyProp ?? markerStrategyOf(industry);
  const ids = {
    source: sourceId,
    cluster: `${sourceId}-clusters`,
    count: `${sourceId}-cluster-count`,
    point: `${sourceId}-unclustered`,
  };
  const color = () => (colorVar === "--accent" ? readAccentColor() : readCssVar(colorVar, "#c8102e"));
  // 이하 기존 본문에서 MARKERS_SOURCE_ID → ids.source, CLUSTER_LAYER_ID → ids.cluster,
  // CLUSTER_COUNT_LAYER_ID → ids.count, UNCLUSTERED_LAYER_ID → ids.point, readAccentColor() → color() 로 치환.
  // applyThemeColors(map)도 (map, ids, color) 를 받게 바꾼다. 상수 4개는 삭제.
```

`map-view.tsx` — `MapViewProps`에 `showClosed: boolean;` 추가, 렌더 끝 `<RegionMarkers .../>` 아래에:

```tsx
      <RegionMarkers
        mapRef={mapRef}
        ready={ready}
        regionCode={showClosed ? regionCode : null}
        industry={industry}
        strategy={CLOSED_STORE_STRATEGY}
        sourceId="closed-markers"
        colorVar="--danger"
      />
```
(`import { CLOSED_STORE_STRATEGY } from "./marker-strategies";`. `regionCode`를 null로 넘기면 기존 성능 가드가 소스를 비운다 — 토글 꺼짐 = 로드 안 함.)

`map-page.tsx` — `const [showClosed, setShowClosed] = useState(false);` 를 두고 `<MapView showClosed={showClosed} .../>`, `<SidePanel showClosed={showClosed} onToggleClosed={setShowClosed} .../>`. URL·localStorage에 넣지 않는다(설계서 §6-2).

`side-panel.tsx` — props에 `showClosed?: boolean; onToggleClosed?: (next: boolean) => void;` 추가. `VerdictSection` 바로 아래에:

```tsx
          <ClosedStoresToggle regionCode={regionCode} industry={industry} checked={showClosed ?? false} onChange={onToggleClosed ?? (() => {})} />
```

같은 파일 하단에 컴포넌트 추가:

```tsx
function ClosedStoresToggle({ regionCode, industry, checked, onChange }: {
  regionCode: string; industry: string; checked: boolean; onChange: (next: boolean) => void;
}) {
  const closed = useQuery({
    queryKey: CLOSED_STORE_STRATEGY.queryKey(regionCode, industry),
    queryFn: () => CLOSED_STORE_STRATEGY.fetch(regionCode, industry),
    enabled: checked,
  });
  return (
    <div className="mt-2 flex flex-col gap-1 text-xs">
      <label className="flex items-center gap-2 text-[var(--text-secondary)]">
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
        최근 2년 폐업 점포 보기
      </label>
      {checked && closed.data && (
        <p className="text-[var(--text-primary)]">
          이 동에서 최근 2년 {industryLabel(industry)} <span className="tabular-nums">{closed.data.length}</span>곳 폐업
        </p>
      )}
    </div>
  );
}
```
(`import { CLOSED_STORE_STRATEGY } from "./marker-strategies";` — 같은 queryKey라 `RegionMarkers`와 요청이 한 번으로 합쳐진다.)

- [ ] **Step 4: 통과 확인 + 전체 + 실 화면**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: 전부 통과. 기존 `map-view.test.tsx`가 `MapView`를 `showClosed` 없이 렌더하면 prop을 `showClosed={false}`로 넘겨 고친다. 노트북 브라우저에서 `/map?region=1168064000&industry=korean_food` → 토글 켜기 → 빨간 마커·"최근 2년 한식 N곳 폐업" 확인.

- [ ] **Step 5: 문서·커밋·푸시**

`frontend/docs/frontend_ver_log.md`에 `## [v0.29.1] - 2026-09-29` / `### Added` — 폐업 마커 토글(기본 꺼짐, URL 미포함), `CLOSED_STORE_STRATEGY`(`--danger`, 팝업 폐업일·영업 개월), 건수 한 줄, mock `status`. / `### Changed` — `RegionMarkers`가 전략·소스 id·색 토큰을 props로 받아 레이어를 둘 얹을 수 있음. / `### Validation` — Vitest N/N, tsc, 실 화면 역삼1동 한식.
설계서 §11에 3단계 행. `docs/HANDOFF.md` §0-7 1번을 `✅ 전부 완료(9/29, BE v0.40.1 · FE v0.29.1)`로.

```bash
git add frontend docs
git commit -m "frontend v0.29.1: 최근 2년 폐업 마커 — CLOSED_STORE_STRATEGY·레이어 파라미터화·토글·건수 (설계서 3단계)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git push origin main
```

---

## Self-Review

**Spec coverage** — §3 신호·상대평가·판정·근거 → Task 1~4. §4-1 파일 구성·§4-2 엔티티 → Task 1·4. §4-3 테이블 → Task 5. §4-4 배치·크론·게이트웨이 → Task 6·7. §4-5 API → Task 7. §5-1 카드 → Task 11. §5-2 지도(축·팔레트·범례·딥링크) → Task 8·10. §6-1 백엔드 status → Task 12. §6-2 토글·전략·건수 → Task 13. §7 3단계 커밋·버전 → Task 7·11·13. §8 테스트 목록 → 각 Task Step 1. §9 insufficient 30%·폐업 1,000 초과 대응 → Task 7 Step 5·Task 12 Step 4. mock 미러(§5·§6) → Task 9·13. `EXCLUDED_INDUSTRIES` = 프론트 14종 → Task 1·9(`isJudgedIndustry`).

**Type consistency** — `SignalResult(key, level, value, percentile, evidence, source)` 6필드가 엔티티·DTO·ORM JSON·pydantic·TS `VerdictSignal`에서 같다. 목록 계약 `{region_code, value}`는 백엔드 `VerdictValueResponse`·TS `VerdictRow`이고 프론트 `fetchVerdictMetrics`가 `type_code`로 옮긴다. `CategoricalMetricSource.palette/order/labelOf`는 Task 10 정의·map-view·map-legend 소비가 일치. `fetchStores(regionCode, industry, status)` 시그니처는 Task 13 api·전략·mock에서 동일. `RegionMarkers` 신규 props 이름(`strategy`·`sourceId`·`colorVar`)은 map-view 호출부와 동일.

**Placeholder scan** — Task 7 Step 6·Task 12 Step 5·Task 13 Step 5의 N·S·K는 실측으로 채우는 자리이며 값이 아니라 절차가 명시돼 있다. 그 외 TBD·"적절히"·"비슷하게" 없음.

**Scope** — 단일 플랜 13 Task, 3단계 커밋 경계. 대안 두 축·백테스트·업종 특화 신호는 설계서 §10대로 제외.
