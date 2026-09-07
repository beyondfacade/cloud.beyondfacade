# CLAUDE.md — Master

> **이 파일은 마스터 문서입니다.**
> `backend/docs/CLAUDE.md` 와 `frontend/docs/CLAUDE.md` 는 이 파일의 심볼릭 링크입니다.
> 이 파일을 수정하면 두 링크 모두 자동으로 동일 내용을 반영합니다.

---

## [Shared] Part I — AI Coding Behavior

This project is built on Hexagonal + Clean Architecture + DDD as a **fractal structure for AI-harness engineering**.
Each Bounded Context is the unit of AI delegation: self-contained, port-bounded, and TDD-verified.
The architecture is not a stack of patterns — it is one rule repeated at every scale.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## [Shared] Part II — GoF Design Patterns

### 5. GoF Patterns (Gang of Four)

**`if/else` = the caller knows the branching → caller must change when behavior changes.**
**GoF pattern = the object knows its own branching → OCP achieved naturally.**

Telling AI "use Strategy here" compresses 10 lines of `if/elif/else` intent into one word.
Prefer `@abstractmethod` and polymorphism over any conditional that dispatches on type or state.

### Conditional → Pattern Mapping

| Bad code (conditional) | GoF Pattern | Category |
|---|---|---|
| `if type == "A": ... elif type == "B":` | **Strategy** | Behavioral |
| `if state == "PENDING": ... elif state == "PAID":` | **State** | Behavioral |
| `if format == "JSON": ... elif format == "XML":` | **Factory / Abstract Factory** | Creational |
| `if a: do_a(); if b: do_b();` | **Chain of Responsibility** | Behavioral |
| `if event == "click": ... elif event == "hover":` | **Observer / Command** | Behavioral |
| `for item in list: item.do()` | **Iterator + Visitor** | Behavioral |
| `obj = ClassA() if x else ClassB()` | **Factory Method** | Creational |
| `if cache: return cache; else: fetch()` | **Proxy** | Structural |
| `obj.a(); obj.b(); obj.c();` fixed order | **Template Method** | Behavioral |
| `if A and B and C: do()` complex condition | **Specification** | Behavioral |
| `result = step1(step2(step3(x)))` nested calls | **Decorator** | Structural |
| `global_var = None; if not global_var: init()` | **Singleton** | Creational |
| `try: ... except TypeA: ... except TypeB:` | **Command + Handler** | Behavioral |
| `if legacy_api: adapt(); else: use_new()` | **Adapter** | Structural |
| `obj1.notify(obj2); obj1.notify(obj3);` manual propagation | **Observer** | Behavioral |
| `if flag: do_extra()` feature toggle | **Decorator** | Structural |
| `if subsystem_a: ...; if subsystem_b: ...` | **Facade** | Structural |
| `copy = deepcopy(obj)` manual copy | **Prototype** | Creational |
| `for`-loop directly traversing a tree | **Composite + Iterator** | Structural + Behavioral |
| `if obj_type == "remote": ... elif "local":` | **Bridge** | Structural |

### GoF 23 Pattern Reference

```
Creational (5)
├── Singleton       ← global variable + if None check
├── Factory Method  ← if/else object creation
├── Abstract Factory← platform-specific if/else
├── Builder         ← telescoping constructor (too many __init__ args)
└── Prototype       ← manual deepcopy

Structural (7)
├── Adapter         ← if legacy / new API
├── Bridge          ← if remote / local
├── Composite       ← tree traversed directly with for
├── Decorator       ← nested function calls, flag-toggled features
├── Facade          ← complex subsystem if-chain
├── Flyweight       ← repeated object creation for identical data
└── Proxy           ← if cache / if auth / if lazy-load

Behavioral (11)
├── Chain of Responsibility ← if a: do_a; if b: do_b
├── Command         ← direct method call with no undo/queue
├── Iterator        ← direct for-loop over internals
├── Mediator        ← objects holding direct references to each other
├── Memento         ← state saved manually in dict/list
├── Observer        ← manual notify calls listed in sequence
├── State           ← if state == "X": elif state == "Y":
├── Strategy        ← if type == "A": elif type == "B":
├── Template Method ← fixed-order procedural calls
├── Visitor         ← for + if isinstance() dispatch
└── Interpreter     ← string parsing with if/elif chains
```

**Rules:**
- Replace any `if/elif` that dispatches on **type or state** with Strategy or State.
- Replace any object creation `if/else` with Factory Method or Abstract Factory.
- Replace any `for + if isinstance()` with Visitor.
- Use `@abstractmethod` to enforce contracts. Never check `isinstance` in business logic.
- When AI is asked to implement branching logic, default to the pattern — not the conditional.

---

## [Backend] Part III — Backend Architecture

### 6. Why Fractal

Every domain module has the same internal shape:

```
Order domain                Payment domain
├── Domain                  ├── Domain       ← same pattern
│   (Entity, VO, Event)     │
├── Application             ├── Application
│   (UseCase, Port)         │
├── Adapter (in / out)      ├── Adapter
└── Infrastructure          └── Infrastructure
```

Once you know the shape of one domain, you know the shape of all of them.

**Why this matters:**
- Each Bounded Context is fully understandable within a single context window — the unit of AI delegation.
- One dependency rule applies everywhere: business logic never depends on infrastructure.
- Every collaboration point crosses a Port — typed, named, independently testable.
- When AI makes a mistake, the damage is contained within the Bounded Context.

```
Humans define:                AI implements:
├── Bounded Context           ├── UseCase
├── Ports (interfaces)        ├── Adapter
├── Domain rules (invariants) ├── Repository
├── TDD scenarios             └── DTO / Mapper
└── AOP policies
```

### 7. Hexagonal Architecture (Alistair Cockburn)

**The application is the center. The world outside is a plugin.**

The application must not know who is calling it or what it is calling. All external actors — UI, database, message broker, CLI, test — are equal.

**Port** — an interface defined by the application, in the application's language.
- Driving Port (inbound): how the outside world triggers the application. e.g. `OrderUseCase`, `PaymentCommandPort`
- Driven Port (outbound): what the application needs from the outside world. e.g. `OrderRepository`, `PaymentGateway`

**Adapter** — a concrete implementation that connects one Port to one external technology.
- Driving Adapter (inbound): REST Controller, gRPC Handler, CLI Runner, Test Driver.
- Driven Adapter (outbound): JPA Repository, Kafka Producer, SMTP Client, In-Memory Fake.

**Rules:**
- Business logic imports Ports, never Adapters. Adapters import nothing from the domain.
- Swap any Adapter without touching any other layer.
- A test is just another Driving Adapter — the application cannot tell the difference.
- One Port, many possible Adapters. One Adapter, exactly one Port.

### 8. SOLID (Uncle Bob)

**Write code that is easy to change, not just code that works.**

- **S** — One class, one reason to change. If you need "and" to describe it, split it.
- **O** — Add new behavior by adding new code, not by editing existing code.
- **L** — A subtype must honor every contract the base type promises. If overriding changes expected behavior, inheritance is wrong.
- **I** — Prefer many small, role-specific interfaces over one large general-purpose one.
- **D** — Business logic must not import concrete infrastructure. Dependencies point inward only.

### 9. Clean Architecture (Uncle Bob)

**Dependencies must point inward. Inner layers know nothing about outer layers.**

```
Frameworks & Drivers  →  Interface Adapters  →  Use Cases  →  Entities
     (outermost)                                              (innermost)
```

- **Entities**: pure domain logic. No external dependencies.
- **Use Cases**: orchestrate entities. Must not depend on UI, DB, or transport.
- **Interface Adapters**: convert between domain format and external format. Controllers, Presenters, Gateways.
- **Frameworks & Drivers**: all infrastructure detail lives here. Swappable without touching inner layers.

**Rules:**
- Don't pass framework types (ORM models, HTTP request objects) into use cases.
- Define interfaces in the inner layer; implement them in the outer layer.
- Only the composition root (main / IoC container) is allowed to wire everything together.

### 10. DDD + TDD + AOP

```
┌─────────────────────────────────────────────┐
│  DDD  "What to build" — domain model        │
│  ┌───────────────────────────────────────┐  │
│  │  TDD  "How to build it" — practice   │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │  AOP  "Where to put extras"     │  │  │
│  │  │       cross-cutting concerns    │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

| | DDD | TDD | AOP |
|---|---|---|---|
| **Purpose** | Domain modeling | Quality assurance | Concern separation |
| **Stage** | Design | Development | Implementation / Runtime |
| **Core value** | Business alignment | Testability | Modularity |

**DDD — Domain-Driven Design (Eric Evans)**

- Use the same terms in code and conversation. If the term drifts, the model drifts.
- Identify the **Core Domain** — invest here. Generic subdomains can be built simply or outsourced.
- **Bounded Context**: one consistent model per boundary. Use an ACL at the seam to prevent external models from polluting yours.
- **Entity**: identity-based. Mutate state only from inside.
- **Value Object**: attribute-based, immutable. Replace rather than mutate.
- **Aggregate**: one Root is the only entry point. Enforce invariants inside. Reference other Aggregates by ID only.
- **Repository**: one per Aggregate Root. Interface in domain layer; implementation in infrastructure.
- **Application Service**: thin orchestrator only — load, call domain, save, publish. No business rules here.
- If logic spans entities and doesn't fit in one, extract a **Domain Service**.

**TDD — Test-Driven Development (Kent Beck)**

- **Red → Green → Refactor.** Never write production code without a failing test.
- Red: smallest failing test. One behavior, one assertion. Confirm it fails for the right reason.
- Green: minimum code to pass. Fake it if needed. Do not refactor yet.
- Refactor: remove duplication, clarify names. All tests stay green. Clean test code too.
- One behavior per test. Arrange → Act → Assert.
- Test behavior, not implementation — tests must survive internal refactoring.
- Only mock system boundaries: network, filesystem, clock. Not internal collaborators.
- Hard-to-test code signals a design problem — too many dependencies or wrong responsibilities.

**AOP — Aspect-Oriented Programming**

- Cross-cutting concerns (logging, auth, transactions, caching, retry, auditing) belong in one Aspect each.
- Keep Advice thin — if it grows complex, business logic is hiding inside it.
- Apply via annotations or config, never by calling Aspect code directly.
- Keep Pointcuts narrow — an overly broad Pointcut silently intercepts code you didn't intend.
- Never use AOP to compensate for bad design. Fix the coupling first.

| Concern | Advice type |
|---|---|
| Logging | Around |
| Authorization | Before |
| Transaction | Around |
| Cache | Around |
| Retry | Around |
| Audit | After Returning |
| Exception translation | After Throwing |

---

## [Backend] Part IV — Backend Project Structure Rules

### 11. Modular Monolith

본 프로젝트는 **모듈러 모놀리스(Modular Monolith)** 구조입니다.
단일 프로세스로 배포되지만 내부는 Bounded Context 단위로 완전히 분리됩니다.

```
backend/
├── core/       ← 전역 인프라 (백엔드 전체 공유)
└── apps/       ← Bounded Context 모음
    ├── foodopsagent/ ← BC #1
    └── ...           ← BC #N (추후 추가)
```

**`core/`** 는 DB, Secret, API, Agent 등 백엔드 전역에서 공유하는 인프라 매니저를 둡니다.
- `core/` 는 `apps/` 를 절대 import하지 않습니다.
- `apps/` 가 `core/` 를 import합니다. (의존성 방향: `apps` → `core`)

```
core/matrix/
├── grid_oracle_database_manager.py   ← DB 연결 (SQLAlchemy engine/session)
├── grid_keymaker_secret_manager.py   ← Secret/Key 관리
└── grid_{name}_manager.py            ← 추가 전역 인프라 (동일 패턴 반복)
```

---

### 12. Fractal 11-File Set — SRP × AI Harness

**1 ERD 테이블 = 1 Fractal 11-File Set = 1 AI 위임 단위**

하나의 API Router는 반드시 하나의 ERD 테이블만 담당합니다.
이것이 SRP이며, AI 하네스 위임 단위의 기준입니다.

```
테이블 이름: {name}

router:       adapter/inbound/api/v1/{name}_router.py
use_case:     app/ports/input/{name}_use_case.py
interactor:   app/use_cases/{name}_interactor.py
port:         app/ports/output/{name}_port.py
repository:   adapter/outbound/repositories/{name}_repository.py
schema:       adapter/inbound/api/schemas/{name}_schema.py
dto:          app/dtos/{name}_dto.py
orm:          adapter/outbound/orms/{name}_orm.py
entity:       domain/entities/{name}_entity.py
mapper:       adapter/inbound/mappers/{name}_mapper.py
orm_mapper:   adapter/outbound/orm_mappers/{name}_orm_mapper.py
```

**왜 테이블 단위인가:**
- AI는 11개 파일만 컨텍스트에 올리면 해당 테이블을 완전히 이해할 수 있습니다.
- 실수해도 해당 Bounded Context 안에서만 영향을 받습니다.
- 어느 테이블이든 동일한 형태 → AI가 패턴 하나만 학습하면 전체를 구현할 수 있습니다.

**라우터 최초 검증 — myself 엔드포인트:**
- 새 {name}_router.py를 만들 때는 실제 비즈니스 엔드포인트보다 먼저 GET /{prefix}/myself를 추가해, router → use_case(input port) → interactor → port(output port) → repository로 이어지는 
  전체 배선이 실제로 동작하는지부터 확인한다.
- DB·외부 API 의존 없이 하드코딩된 최소 데이터(예: id, name)를 그대로 왕복시켜, 이 엔드포인트가 200을 반환하면 DI/컴파일 오류가 없다는 뜻이다. 이후에 실제 비즈니스 로직을 붙인다.


**Boundary Gate (경계 톨게이트):**
- **Inbound**: `mapper`가 `schema` ↔ `dto` 변환. Router → Interactor 경계.
- **Outbound**: `orm_mapper`가 `entity` ↔ ORM 변환. Repository → DB 경계.
- `domain/`, `app/use_cases/` 레이어에서는 FastAPI, SQLAlchemy 등 외부 프레임워크를 import할 수 없습니다.

**설계 장치 3종:**

| 디렉토리 | 원칙 | 역할 |
|---|---|---|
| `app/ports/input/` | **ISP** | Driving Port — UseCase 인터페이스 (역할별로 분리) |
| `app/ports/output/` | **ISP** | Driven Port — Repository/Gateway 인터페이스 (역할별로 분리) |
| `dependencies/` | **DIP** | Composition Root — Port에 Adapter를 주입 (FastAPI `Depends`) |
| `domain/value_objects/` | **AOP 예외** | 프랙탈 밖 공통 VO — 여러 엔티티가 횡단 공유 |

**AI 하네스 위임 공식:**
```
"테이블 이름만 바꾸면 AI가 나머지 11개 파일을 전부 채울 수 있는 구조"
```

---

### 13. ERD 설계 규칙

**정규화 원칙:**
- 모든 테이블은 **1NF → 2NF → 3NF** 순서로 정규화합니다.
- 성능 또는 편의를 위한 **부분적 역정규화(Denormalization)**는 허용하되, 반드시 명시적 근거가 있어야 합니다.
- 근거 없는 무분별한 역정규화는 절대 금지합니다.

**연결 원칙:**
- ERD의 모든 테이블은 **노드(Node)와 엣지(Edge)로 연결**되어야 합니다.
- 어떤 테이블도 고립(isolated)된 채로 존재할 수 없습니다.
- 연결되지 않은 테이블은 설계 오류로 간주합니다.

**Fractal과의 관계:**
- ERD 테이블 1개 = Fractal 11-File Set 1개 (§12 규칙과 직결)
- 테이블 간 관계(엣지)는 Repository 레이어에서 JOIN 또는 ID 참조로 구현합니다.

---

## [Frontend] Part V — Frontend Project Structure Rules

> 기술 스택: Next.js(App Router) + React + TypeScript + Tailwind v4 + TanStack Query + MapLibre GL + Vitest
> dev/start 포트는 **3200** (포트 규약: 백엔드 8200, 프론트 3200)

### 14. Feature-Sliced 구조

**1 Feature = 1 AI 위임 단위.** 백엔드의 Bounded Context에 대응합니다.

```
frontend/src/
├── app/          ← Next.js 라우팅 + /api/mock. 페이지 조립만 담당
├── features/     ← 기능 단위 (예: map-explorer, agent-report)
│   └── {feature}/
│       ├── components/   ← "use client" 컴포넌트
│       ├── hooks/        ← TanStack Query 훅, SSE 훅
│       ├── lib/          ← 순수 로직 (프레임워크 무관, 단위 테스트 대상)
│       └── api.ts        ← 해당 feature의 API 호출 함수
├── shared/       ← config.ts, 공통 어휘, api/(client·providers·types), ui/
└── styles/tokens.css
```

**의존 방향 규칙 (`features → shared`, 단방향):**
- **feature 간 직접 import 절대 금지.** 두 feature가 함께 쓰는 코드는 `shared/`로 승격합니다.
- `shared/`는 `features/`를 import하지 않습니다. `app/`은 feature 페이지 컴포넌트 조립만 합니다.
- feature 내부는 상대 경로, feature 외부는 `@/shared/...` alias로만 참조합니다.
- 페이지는 서버 컴포넌트로 두고 `<Suspense fallback={<RouteFallback/>}>`로 feature 클라이언트 컴포넌트를 감쌉니다. `"use client"`는 feature의 components/hooks 최상단에만 둡니다.

### 15. Mock API 계약 (`src/app/api/mock/`)

**mock은 실 백엔드 API의 미러입니다.** 경로·쿼리 파라미터·응답 스키마가 실 API와 동일해야 합니다.

- 타입 단일 원천: `@/shared/api/types.ts` — mock 라우트와 feature `api.ts`가 **같은 타입을 양쪽에서 import**합니다.
- 에러 바디는 항상 `{ error: { code, message } }`. 미지원 값은 **500이 아니라 404** (예: `METRIC_NOT_FOUND`). `code`는 SCREAMING_SNAKE, `message`는 한국어.
- 픽스처는 `fixtures.ts`에 집약 (서버 전용 — 클라이언트 번들 진입 금지). **`Math.random` 금지** — 문자열 해시(FNV-1a) 기반 결정적 데이터만 (테스트 재현성).
- API 베이스 스위칭: `shared/config.ts`의 `config.apiBase = NEXT_PUBLIC_API_BASE ?? "/api/mock"`. 실 API 전환은 코드 수정 없이 env로만 합니다.

### 16. 스타일 — 토큰 기반 + 다크모드

- 디자인 토큰은 `src/styles/tokens.css`가 단일 원천: `:root`(light)와 `[data-theme="dark"]` 두 블록에 `--bg-*`, `--text-*`, `--border`, `--accent`, `--ok/--warn/--danger`.
- 컴포넌트는 토큰을 Tailwind arbitrary value로만 소비합니다: `bg-[var(--bg-surface)]`, `text-[var(--text-primary)]`. **하드코딩 hex 금지** (예외: 데이터 시각화 팔레트 — UI 토큰과 별개 체계로 주석 선언).
- Tailwind v4 CSS-first — `tailwind.config.*` 파일 없이 `globals.css`에서 `@import "tailwindcss"` + `tokens.css`.
- 다크모드는 `<html data-theme="light|dark">` 속성 방식(class 전략 아님). 테마 반응 컴포넌트는 `MutationObserver(attributeFilter: ["data-theme"])`로 감지합니다.

### 17. 데이터 레이어 — TanStack Query

- `QueryClient`는 `shared/api/providers.tsx`(Composition Root) 한 곳에서만 생성. 기본 `staleTime 60s, retry 1`.
- queryKey는 `["도메인명", ...params]` — 문자열 리터럴 도메인명 + 파라미터 순서 고정. 예: `["metrics", metric, industry, year]`.
- 불변 데이터(행정동 경계 geojson)는 `staleTime: Infinity`. 선택 의존 쿼리는 `enabled: !!regionCode`.
- fetch는 `shared/api/client.ts`의 `apiGet/apiPost`로만 — 에러 바디 `{error:{code,message}}`를 `ApiError`로 변환하는 톨게이트입니다.
- SSE 스트림은 TanStack Query가 아니라 native `EventSource` + 순수 리듀서 함수로 처리합니다.

### 18. 지도 — MapLibre WebGL 브리징

- **paint 속성은 CSS `var()`를 이해하지 못합니다** (WebGL 렌더링). `readAccentColor()`처럼 `getComputedStyle`로 계산된 값을 문자열로 넘깁니다. 팝업 등 실제 DOM 스타일에는 `var()`를 그대로 씁니다.
- 테마 전환 시 `MutationObserver(data-theme)`로 타일 URL·paint 색을 재적용합니다 (§16의 감지 패턴과 동일).
- 워커는 `public/maplibre-gl/`에 **원본 파일명 그대로 벤더링** + `setWorkerUrl()` (Turbopack이 해시 리네임하면 워커의 상대 import가 깨짐).
- 색상 스케일은 `makeMetricColorScale()`이 단일 원천 — 지도 fill 표현식의 `colorOf`와 범례 `classes`가 **동일 객체를 공유**해 경계 계산이 어긋나지 않습니다.
- 성능 가드: 점 데이터(상점 등)는 동 선택 시에만 로드 — 전 서울 로드 금지.

### 19. 테스트 — Vitest + TDD

- Part III의 TDD 규칙(Red → Green → Refactor)을 그대로 따릅니다.
- 테스트 파일은 대상 파일 옆 co-located `*.test.ts(x)` (별도 `__tests__` 디렉토리 없음). 테스트 제목은 한국어 서술문.
- **mock 라우트 계약 테스트 필수**: 라우트의 `GET/POST`를 직접 import해 `Request`로 호출, status와 `error.code`를 assert — mock이 실 API 계약(§15)을 지키는지 고정합니다.
- `config.apiBase` 기본값 등 설정 계약도 테스트로 고정합니다.
- E2E·스크린샷 매트릭스는 vitest 밖 `scripts/` 셸 스크립트로 분리합니다.

---

## [Shared] Part VI — Version Log 개정 이력 관리

백엔드 또는 프론트엔드 코드가 변경될 때마다 반드시 해당 로그 파일에 개정 이력을 기록합니다.

| 대상 | 로그 파일 경로 |
|---|---|
| 백엔드 | `backend/docs/backend_ver_log.md` |
| 프론트엔드 | `frontend/docs/frontend_ver_log.md` |

**기록 시점:** 코드 변경 완료 직후, 커밋 전에 기록합니다.

**기록 형식:**
```markdown
## [vX.Y.Z] - YYYY-MM-DD

### Added
- 추가된 기능 또는 파일

### Changed
- 변경된 내용

### Fixed
- 수정된 버그 또는 오류

### Removed
- 제거된 기능 또는 파일
```

**규칙:**
- 버전은 `[vX.Y.Z]` 형식을 따릅니다 (Semantic Versioning).
  - `X` (Major): 하위 호환이 깨지는 변경
  - `Y` (Minor): 하위 호환되는 기능 추가
  - `Z` (Patch): 버그 수정 또는 소규모 수정
- 백엔드와 프론트엔드의 버전은 독립적으로 관리합니다.
- 변경이 없는 쪽의 로그는 건드리지 않습니다.

