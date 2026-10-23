# 서울 업종별 점포당 매출 중앙값 사전 계산 — 설계

> 2026-10-23 · 근거: `docs/serverplan.md` §21-10(11-1)·§21-12(11-3) 부하 측정 · 12차 부하 테스트 전에 적용

## 1. 문제 (측정으로 확인)

재무 계획 프리필(`GET /finance/prefill`)이 **요청마다** 서울 전체 동의 점포당 매출 중앙값을 다시 계산한다
(`RevenueFactsGateway.latest_quarterly_sales_per_store` — 427개 동 집계 후 `percentile_cont`).

- 11-1(DB large): DB 시간의 **약 92%**가 이 쿼리 하나, 평균 103~159ms → DB CPU 포화가 천장(약 685 RPS)을 정했다.
- 11-3(DB xlarge): 업종 코드 수가 다른 세 변형 합계 **약 93만 ms — 2위 쿼리(7만 ms)의 13배**. 다음 병목 예상이 DB(약 1,850 RPS).

그런데 이 값은 **업종 × 분기에만 달려 있다** — 12업종 × 최신 분기, 실제로 서로 다른 값은 12개뿐이다.
원천(`region_commerce_sales`·`region_commerce_store`)은 정적 아카이브를 손으로 다시 적재할 때(`load_commerce`)만 바뀐다.

## 2. 목표 / 비목표

- 목표: 프리필의 서울 중앙값을 **미리 계산한 표에서 한 줄로 읽는다.** 응답 값은 지금과 같다(같은 업종·분기면 같은 숫자).
- 비목표: 동 하나의 매출을 읽는 앞부분 쿼리(가볍다)·프리필의 다른 값·화면은 건드리지 않는다. 메모리 캐시(TTL)도 두지 않는다.

## 3. 설계

### 3-1. 표 `industry_sales_median_quarter` (집계 계층 — metric BC)

| 컬럼 | 형 | 설명 |
|---|---|---|
| `industry_id` | varchar, PK, FK → `industry` | 우리 업종 |
| `year_quarter` | varchar(5), PK | 원천 분기 코드(예: `20254`) |
| `median_quarterly_sales_per_store` | double | 동마다 낸 (매출 합 ÷ 점포 합)의 서울 중앙값 — 분기 합 단위(지금 게이트웨이와 같음) |
| `region_count` | int | 중앙값에 들어간 동 수(검수용) |

- **집계 계층의 의도적 역정규화**(docs/erd.md 원칙 — 집계 계층에만 허용, 근거 명시): 원천에서 언제든 다시 만들 수 있는 파생 값을 저장한다. 근거는 §1의 부하 측정.
- ERD 연결: `industry ||--o{ industry_sales_median_quarter` (고립 테이블 아님).
- 계산식은 지금 게이트웨이와 **같다** — 업종에 붙은 원천 코드(`industry_source_code`, `seoul_commercial`) 전부를 합쳐, 동(`region_code`)별 `sum(sales_amount) / sum(store_count)`(`having sum(store_count) > 0`, 매출·점포 NULL 제외, 같은 동·코드·분기로 조인)의 `percentile_cont(0.5)`.
- **모든 분기**를 계산한다(개발 DB: 매핑된 16업종 × 20분기 = 320행) — 동마다 "최신 분기"가 다를 수 있어 그 분기로 바로 찾게.

### 3-2. 파일 (라우터 없음 — 읽는 쪽은 재무 게이트웨이뿐)

metric BC에 `industry_sales_median`: orm · input port(use case: `build`) · output port(repository: `rebuild`) · interactor · repository · dependencies · CLI `build_sales_median`.
엔티티·DTO·ORM 매퍼는 두지 않는다 — 앱 안에서 이 행을 객체로 읽는 곳이 없다(재무 게이트웨이는 지금 상권·마스터 ORM을 읽듯 이 ORM을 직접 읽는다).
계산은 **repository의 `rebuild()` 한 메서드**가 한 트랜잭션에서 `DELETE` 후 `INSERT … SELECT` 한 문장으로 한다(지우고 다시 넣어 매핑에서 빠진 조합도 남지 않는다)(원천을 파이썬으로 끌어오지 않는다 — 427동×분기 집계라 DB 안에서 끝내는 게 빠르다). interactor는 `rebuild()`를 부르고 처리 행 수를 돌려줄 뿐이다. 마이그레이션의 채우기 SQL은 같은 식을 복사해 둔다(마이그레이션은 앱 코드를 import하지 않는다).

### 3-3. 채우는 시점 — 두 곳

1. **마이그레이션**(`migrations/versions/…`): 표 생성 + **같은 SQL로 즉시 채우기**(`INSERT … SELECT`). 운영은 Argo의 배포 전 단계(db-migrate Job)가 돌리므로 배포와 함께 값이 생긴다.
2. **매일 새벽 store-collector 체인**: `… && build_metrics && build_sales_median && build_verdicts` — 새 CLI `apps.metric.adapter.inbound.cli.build_sales_median`(재실행 멱등, 수 초). 원천을 손으로 다시 적재해도 다음 새벽에 맞춰지고, 업종-원천 코드 매핑이 바뀌어도 따라간다.

### 3-4. 읽기 (finance BC)

- `RevenueFactsGateway`의 `percentile_cont` 블록을 `industry_sales_median_quarter`의 (업종, 그 동의 최신 분기) 한 줄 조회로 바꾼다. 포트·DTO(`RevenueBasis.seoul_median_quarterly_sales_per_store`)·인터랙터는 그대로.
- 행이 없으면 지금처럼 `None` — 이상값 판정(`implausible_revenue_reason`)만 건너뛰고 화면엔 서울 중앙값이 안 나온다(지금 원천이 비었을 때와 같은 동작).

## 4. 테스트 (TDD — 동작만 고정)

1. 집계: 원천 표본(동 3개, 코드 2개 업종 포함, NULL·점포 0 행 포함)으로 `build` → 업종·분기별 중앙값이 손 계산과 같다. 재실행해도 행 수 같음(멱등).
2. 읽기: 표에 값이 있으면 게이트웨이 `RevenueBasis.seoul_median…`이 그 값, 없으면 `None`.
3. 기존 프리필 테스트(`tests/test_finance_prefill.py`) 전부 그대로 통과.

## 5. 배포·검증

- 배포 전 로컬(8200 DB): 마이그레이션 → **12업종 × 최신 분기의 새 값 = 지금 실시간 계산 값**(소수점까지) 비교.
- 운영: 푸시(= 운영 배포) → db-migrate 성공 → 같은 비교를 API 파드에서 한 번 → `/finance/prefill` 몇 조합 응답이 배포 전과 같은지.
- 느린 쿼리: 12차 `pg_top`에서 `percentile_cont`가 사라졌는지.

## 6. 12차 부하 테스트와의 관계

12차 전에 넣는다(10/23 결정). 이 변경은 **DB CPU**에, GPU는 **임베딩 성공률**에 작용하고 둘 다 따로 측정되므로(RDS CPU·`pg_top` / k6 임베딩 체크·Ollama·GPU 기록) 한 번의 측정에서 효과를 나눠 읽는다. 12차 계획서(`docs/plan/부하테스트12차.md`) 구성 표에 반영한다.
