# AGENTS.md — Master

> Codex용 작업 지침입니다. 원본은 `CLAUDE.md`(마스터)이며, 본문 규칙은 그 문서와 같습니다.
> 규칙을 바꿀 때는 `CLAUDE.md`와 이 파일(및 `backend/docs/AGENTS.md`)을 함께 갱신합니다.
> 사용자의 명시적 요청이 이 지침보다 우선합니다.

---

## 프로젝트 공통 지침

- **범위별 지침 파일**
  - `backend/` 아래 파일을 바꾸기 전에는 `backend/docs/AGENTS.md`(Part III·IV 백엔드 아키텍처·구조 규칙)를 읽고 따릅니다.
  - `frontend/` 아래 파일을 바꿀 때는 이 파일의 Part V와 `frontend/AGENTS.md`(Next.js 버전 주의)를 따릅니다.
  - 두 영역에 걸친 작업은 각 영역의 지침을 그 범위 안에서 모두 적용합니다.
- **언어** — 사용자에게 보이는 모든 응답·중간 보고·커밋 메시지는 한국어로 씁니다.
- **포트** — 백엔드 8200(~8299), 프론트엔드 3200(~3299). 커밋하는 기본값은 항상 8200/3200입니다.
- **테스트**
  - 백엔드: `backend/`에서 `.venv/bin/python -m pytest tests/ -q`
  - 프론트엔드: `frontend/`에서 `npm test`(vitest run)
  - 테스트를 통과시키려고 `backend/tests/conftest.py`를 고치거나 가짜 데이터 파일을 만들지 않습니다. 실패하면 원인을 보고합니다.
- **공개 저장소** — origin은 공개 저장소입니다. 사업·가격·자금 문서(`docs/plan/`, BM 제안 등)는 커밋하지 않습니다(`.gitignore` 대상). `.env`와 키 값은 출력·커밋하지 않습니다.
- **git** — push·amend는 사용자가 요청할 때만 합니다. `git stash`를 이름 없이 쓰지 않습니다(다른 세션·워크트리와 스택을 공유).
- **버전 로그** — 코드를 바꾸면 커밋 전에 Part VI 형식으로 개정 이력을 남깁니다.

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
- **각 구현 단계에서 과도한 테스트를 금지한다.** 테스트는 요청된 동작과 확인된 위험만 고정한다 — 같은 동작을 여러 각도로 반복 검증하거나, 일어나지 않은 경우를 대비한 테스트를 미리 쌓지 않는다.
- **확인된 요구 없이 선제적으로 복잡도를 늘리는 구현을 금지한다.** 사용자가 요청했거나 실측·리뷰로 확인된 문제만 해결한다 — "나중에 필요할 수도 있는" 옵션·추상화·분기·설정·방어 코드를 미리 넣지 않는다.

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

## [Backend] Part III·IV — 백엔드 아키텍처·구조 규칙

`backend/docs/AGENTS.md`에 있습니다. 백엔드 작업 전에 반드시 읽습니다.
(요지: Hexagonal + Clean Architecture + DDD 프랙탈 구조, 모듈러 모놀리스 `core/`·`apps/`, 1 ERD 테이블 = Fractal 11-File Set, ERD 정규화·연결 규칙)

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
