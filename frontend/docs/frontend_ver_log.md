# Frontend Version Log

> 2026-09-23 T0-2 병합에서 v0.14.x 충돌로 우리 쪽 4항목(랜딩·E2E·동네 프로필·영업 지속 개월)을 v0.15.0·v0.15.1·v0.16.0·v0.17.0으로 재번호했다. 해당 커밋 메시지의 번호는 병합 전 번호다.

## [v0.20.0] - 2026-09-23

### Added
- **컨트롤바 두 무리 — 동네 / 업종** (무대 설계서 §4). 지표 버튼을 `METRIC_GROUPS`로 가른다:
  동네 `[동네 유형] [심야 체류] [음식·유흥 비중] [영업 지속 개월]`(동×분기 축) / 업종 `[폐업률] [성장률]
  [점포수]`(업종×연도 축). **명시적 모드 토글이 아니다 — 무리 자체가 모드다.** 어느 무리에 있느냐가
  지표의 축(`axis`)이고, `METRIC_SOURCES`의 `axis`와 같아야 한다(어긋나면 실패하는 테스트로 고정)
- **셀렉터가 축을 정직하게 따라간다.** 동네 무리면 연도 `select` 대신 **분기 `select`**(20211~20262,
  "2026년 2분기" 표기 — `lib/quarters.ts`), 업종 무리면 연도. `MapState.year_quarter`(null = 최신,
  백엔드가 고른다)를 `year`와 **따로** 둔다 — 연 데이터를 분기로 위장하지 않고, 무리를 오가도 각자의
  시점과 예산이 유지된다(테스트). 최신 분기를 고르면 null로 되돌려 URL을 짧게 유지한다
- 동네 무리에서 업종 `select`는 **`disabled`가 아니라 흐림**(`opacity .55`) + `aria-describedby`
  "이 지표는 업종과 무관합니다". 값을 죽이면 사이드패널·마커가 업종을 잃는다
- 파생 지표 2종을 지도에 올린다 — **심야 체류**(`night_index`, 1.00 = 하루 평균)·**음식·유흥 비중**
  (`fnb_share`). 원천은 v0.30.0의 `GET /profiles?metric=`. `METRIC_SOURCES`가 `MetricQuery
  {industry, year, yearQuarter}`를 받고 원천이 자기 축의 값만 쓴다 — 질의 키에 무시하는 값을 넣지 않는다
- mock `/api/mock/profiles?metric=`(+계약 테스트 5) — 단일 프로필과 같은 원천(`regionProfileOf`)이라
  두 계약이 어긋나지 않는다. 화면이 노출하는 둘만 지원, 미지원 404 `METRIC_NOT_FOUND`

### Removed
- 범례의 "업종 구분 없는 …" 단서(v0.17.0·v0.19.0). 무리 구조가 그 뜻을 말한다. 대신 심야 체류에만
  값의 기준("1.00 = 하루 평균")을 붙인다 — 숫자만으로 뜻이 안 서는 지표라서다

### Validation
- 테스트 17건 추가(분기 어휘 4 · 무리 파생/왕복 3 · 원천 축 정합 등 · 컨트롤바 5 · mock 계약 5), 전체
  vitest **165/165**(39파일), `tsc` clean. E2E는 연도·지표 버튼을 전제하지 않아 변경 없음(`bash -n`)
- 실 dev 서버(3200→8201): `/map`(기본 유형) → 분기 select·업종 무관 문구·"동네" group ○, 연도 select ×;
  `/map?metric=closure_rate` → 연도 select ○, 분기 ×, 문구 ×; `/map?metric=fnb_share&year_quarter=20254`
  → 분기 ○. 프록시 `/profiles?metric=night_index|fnb_share` 각 422행, `&year_quarter=20254` 422행

## [v0.19.0] - 2026-09-23

### Added
- **유형 단계구분도** — 지도가 동네 유형 6종으로 색칠된다. 백엔드 `GET /profiles/types`(v0.32.0 2/4)의
  범주 계약 첫 구현. 무대 설계서 `docs/superpowers/specs/2026-09-23-map-stage-design.md` §3
  - **범주형은 숫자와 섞지 않는다** (`map-metric-contract` §5). `shared/api/types.ts`에 `CategoryRow
    {region_code, type_code}`를 따로 두고, `MetricSource`를 `kind: "numeric" | "categorical"` 판별
    합집합으로 나눴다. 한 타입에 value/category를 두고 한쪽을 null로 두면 타입이 거짓말한다
  - `lib/metric-color.ts` — `makeCategoryColorScale(codes, palette, order)`를 **분위수 스케일과 별도
    함수**로. `colorOf`와 `classes`가 같은 팔레트를 봐 지도 색과 범례 색이 어긋나지 않는다. 범주
    범례는 구간이 아니라 **키**라 `order` 순 전체 유형을 보여준다(데이터에 없는 유형도)
  - `lib/neighborhood-palette.ts` — 라이트/다크 두 벌. **주거형이 422동 중 60%라 지도를 지배한다 →
    주거형을 가장 옅게**(라이트 `#d9d4c7` 명도 0.66 최고, 다크 `#3d4250` 명도 0.05 최저), 나머지 5종이
    튄다. UI 토큰과 분리된 데이터 시각화 체계(tokens.css 상단 선언과 같은 원칙). 원칙은 상대 명도
    계산으로 테스트에 고정
  - `map-view.tsx` — `source.kind`로 스케일 함수를 고른다. `match` 표현식은 그대로. 테마 `MutationObserver`가
    `theme` 상태를 갱신해 범주 팔레트가 다크에서 다시 칠해진다(실측: 다크 전환 시 `#6ea0e6`·`#b48ae6`)
  - `map-legend.tsx` — `scale` prop(판별 합집합)을 받아 범주면 **유형 이름 6줄 + 괄호 설명**, 숫자면 값
    구간. 단서 "업종 구분 없는 동네 성격" 추가
  - **기본 지표를 동네 유형으로** (`DEFAULT_STATE.metric`). 창업자가 처음 묻는 건 "어디가 망하나"가
    아니라 "어디가 어떤 곳이냐"이고, 관문이 동 선택 상태로 내려놓을 때 지도가 유형으로 색칠돼 있어야
    패널 서사와 이어진다
  - 색 스킴을 `METRIC_SOURCES`로 옮겼다(`map-view`의 `SCHEME_BY_METRIC` 제거) — 지표당 아는 자리를
    하나 줄인다(`map-metric-contract` §6의 다섯 중 하나)
  - `CommerceChangeMetricKey` 타입 분리 — `RegionMetricKey`에 유형이 들어오며 `fetchCommerceChangeMetrics`가
    범주 키를 받을 수 있게 되는 것을 막는다
  - mock `/api/mock/profiles/types` — 실 API 미러, 단일 프로필 mock과 같은 원천(결정적)

### Validation
- 테스트 15건 추가(팔레트 5 · 범주 스케일 3 · 범례 1 · 원천 3 · 상태 2(갱신) · mock 3) — vitest **148/148**,
  `tsc` clean. E2E는 기본 지표·범례 문구를 전제하지 않아 변경 없음(`bash -n`만)
- 실 dev 서버(3200 → 8201): `/map` 파라미터 없이 열면 범례 "동네 유형" 6줄 + 데이터 없음, 라이트 팔레트
  적용, `data-theme=dark` 전환 시 다크 팔레트로 재도색 확인

## [v0.18.3] - 2026-09-23

### Fixed
- **E2E `[6/8]` 프리필 검증 실패** — 실제값은 `region=1168065000, industry=""`였다. region은 맞았고,
  업종이 빈 이유는 스크립트가 `label → input`만 읽는데 분석 폼의 업종 필드가 v0.14.x(analysis-api
  병합분)에서 `select`로 바뀌었기 때문이다. 제품 버그가 아니라 E2E가 폼 변경을 못 따라온 것.
  `input,select`로 읽는다. 앞선 v0.18.2와 함께, 랜딩·analysis-api 병합 뒤 처음 도는 E2E가 드러낸
  선택자 회귀 2건이다

## [v0.18.2] - 2026-09-23

### Fixed
- **E2E `[5/8] AI 분석 클릭` 30초 타임아웃** — 사이드패널에 동네 프로필 섹션(v0.16.0)이 더해지고 랜딩이
  패널을 재배치하면서 "AI 분석 →" CTA가 패널 스크롤 영역 아래로 밀렸다(재현: top 1208px, 뷰포트 577px,
  스크롤 컨테이너 `aside.brief`). `agent-browser`는 화면 밖 요소를 클릭하면 조용히 빗나가고 URL이 안
  바뀐다. 클릭 전에 `scrollIntoView`로 보이게 하고, 상단 바의 "AI 분석" 탭과 구분하려 href로 사이드패널
  링크를 특정한다. 콜드 컴파일 가설은 서버를 데운 재실행에서 같은 자리에 실패해 기각
- 제품 쪽 관찰: 패널이 길어지며 CTA가 접힌다. T2-3 패널 서사 재배열에서 CTA 위치를 같이 본다

## [v0.18.1] - 2026-09-23

### Fixed
- **홈·`/map` 전부 500** — `e1c51c8`(analysis-api 병합분)이 jsdelivr `<link>`를 걷어내고 `globals.css`에
  `@import "pretendard/dist/web/…css"`를 넣었는데, **Tailwind v4 `@tailwindcss/postcss` 리졸버가 패키지
  경로를 못 풀어**(`Can't resolve … in src/app`) 전역 CSS 컴파일이 실패했다. `pretendard`에 `exports`가
  없고 Node 해석은 되므로 리졸버 문제다. 그 브랜치에서도 실제로 돈 적이 없던 줄로 보인다
  (HANDOFF "포스트MVP: Pretendard 셀프호스팅" 항목). `node_modules`에 패키지가 없던 것도 겹쳐 있었다
- 해결: `layout.tsx`에서 **JS `import`로 들여온다.** App Router 레이아웃의 `node_modules` 전역 CSS는
  Next가 직접 처리하고 상대 `url()`의 woff2도 정적 자산으로 옮긴다. `globals.css`의 `@import` 줄 제거.
  셀프호스팅 의도는 그대로다

### Validation
- 홈·`/map` 200, 스타일시트 청크에서 Pretendard `@font-face`와 woff2 정적 경로 확인. `tsc` clean, vitest 전부 통과

## [v0.18.0] - 2026-09-23

### Added
- **채팅 관문** (`features/intent-gate/`) — 랜딩 히어로에 입력창 하나. "역삼동에 카페, 예산 5천" 한
  문장으로 동·업종·예산을 잡고 되묻기 칩을 거쳐 `/map?region&industry&budget`에 착지한다.
  설계서 `docs/superpowers/specs/2026-09-23-chat-first-direction.md` §4-2·§5-2·§5-3·§7.
  백엔드 `POST /intent`(v0.31.0) 두 형태를 그대로 쓴다
  - `api.ts` — `parseIntent(text)` · `diagnoseIntent(region_code, industry_id)` · `fetchRegionList()`.
    경계 GeoJSON 타입은 map-explorer에서 import하지 않고 최소 형태를 지역 선언했다(§14)
  - `lib/intent-url.ts` — 순수 함수. 진단 문장은 URL에 싣지 않는다(패널이 같은 데이터를 다시 읽는다)
  - `components/intent-gate.tsx` — 상태 기계 idle → pending → clarifyRegion(candidates|districts|dongs)
    → clarifyIndustry → done. 칩 선택은 재제출이 아니라 응답 객체를 채워 진행하고, **A가 완성되면
    두 번째 형태로 한 번 더 호출해 진단을 받는다.** 진단 실패는 착지를 막지 않는다.
    react-query를 쓰지 않는다 — 랜딩은 Provider 밖에서도 렌더돼야 하고(테스트·정적) 관문 한 번에
    캐시가 필요 없다
  - `components/intent-form.tsx`·`clarify-chips.tsx`·`diagnosis-line.tsx`(1.5초 뒤 자동 이동, 클릭 즉시)
  - **조립은 `app/page.tsx`가 한다** — `LandingPage`에 `hero` 슬롯 prop 하나만 더했다. 랜딩 feature는
    intent-gate를 모른다(§14 feature 간 직접 import 금지)
- `shared/seoul-districts.ts` — 자치구 25개 코드↔이름(백엔드 `district`와 대조). 관문의 구 칩과
  mock 파서가 함께 쓴다. 행정동 코드 앞 5자리가 구 코드다
- `shared/api/types.ts` — `IntentResult`·`IntentCandidate`·`IntentDiagnosis` (추가만)
- **`MapState.budget`** — 관문에서 온 예산을 실어 `serializeMapState`가 잃지 않게 한다. 지도는
  소비하지 않지만(T3 프리필 원천) 없으면 지표 한 번 바꾸는 순간 URL에서 사라진다
- mock `/api/mock/intent` — 실 API 미러. 백엔드 `master_dictionary.base_name`(번호·'제'·구분점
  제거) 규칙을 TS로 옮겨 "역삼동"→역삼1동·2동 후보를 그대로 재현한다. LLM 경로는 "홍대"→서교동
  한 건만 흉내. 두 번째 형태·400 `INTENT_TEXT_EMPTY` 포함
- `scripts/e2e-journey.sh` — `[0/8] 채팅 관문` 단계 추가(홈 입력 → `/map?region=` 착지 30초 대기).
  입력은 agent-browser 버전에 따라 fill이 달라 native setter + `input` 이벤트로 넣는다

### 문구 결정
- **후보 칩이 주 경로다.** "역삼동"·"신사동"처럼 사람이 말하는 동 이름 다수가 번호 동으로 갈라진다
  (역삼1동·2동, 신사동 4곳). 그래서 후보 칩 라벨은 "강남구 역삼1동"처럼 구를 앞에 붙인다
- 우회로 둘 — 동을 모르면 "아직 몰라요 — 지도에서 고를게요"(C유형, 업종만 싣는다), 업종을 모르면
  "잘 몰라요 — 동네부터 볼게요"(B유형, 패널이 동네 프로필을 연다)
- 예시 칩 셋 — "역삼동에 카페, 예산 5천"(후보 경로) · "연남동에서 뭘 하면 좋을까"(B) ·
  "홍대 근처 미용실"(LLM 경로 시연)

### Validation
- 테스트 20건 추가 — 상태 전이 7(A 진단→자동 이동·후보 칩→진단·업종 우회→B·구→동 2단·동 우회→C·
  실패 알림·예시 칩) · `intent-url` 3 · mock 계약 7 · `MapState.budget` 왕복 2 · 홈 관문 렌더 1.
  `tsc --noEmit` clean, vitest **133/133**(34파일)
- 실 백엔드 프록시: `curl POST /api/backend/intent {"text":"역삼1동에 카페, 예산 5천"}` →
  A · 1168064000 · "역삼1동은 낮 인구 우위형이고, 카페는 점심(11~14시)에 돈이 돕니다."
- **브라우저 E2E는 실행하지 못했다.** 3200 dev 서버가 홈·`/map` 모두 500 — T0-2로 들어온
  `e1c51c8`이 `pretendard`를 `package.json`에 넣었는데 `node_modules`에 설치되지 않은 채 서버가
  떠 있었다(`globals.css` `@import` 해석 실패, 이번 변경과 무관). `npm install`로 설치했지만
  Turbopack이 시작 시점 해석을 캐시해 재기동 전에는 안 풀린다. **`npm run dev` 재기동 후
  `npm run e2e`를 돌리면 관문 단계부터 검증된다** (`bash -n`은 통과)

## [v0.17.0] - 2026-09-23

### Added
- **지도 단계구분도에 "영업 지속 개월" 추가** — 서울 상권분석서비스의 동별 평균 영업 지속
  개월(`GET /commerce-changes`). 실측 31~206개월, 중앙값 117
  - `lib/metric-sources.ts` — **지표 → 원천 레지스트리(GoF Strategy).** 업종×연도 지표는
    `/metrics`, 동×분기 지표는 `/commerce-changes`에서 온다. 원천이 둘로 갈리지만 호출하는 쪽은
    분기하지 않는다. 응답이 `{region_code, value}`로 같아 색 스케일·범례가 그대로 재사용된다
  - `types.ts` — `MetricKey`(업종 지표)와 `RegionMetricKey`(동 단위 지표)를 나누고 화면용
    `MapMetricKey` 합집합을 둔다. 합쳐두면 `fetchMetrics(industry, ...)`에 동 단위 지표가
    들어갈 수 있다
  - 질의 키에서 업종·연도를 뺀다 — 값에 영향을 주지 않는데 넣으면 같은 응답을 업종 10종 ×
    연도 8개만큼 중복 캐싱한다 (테스트로 고정)
  - mock 라우트 `/api/mock/commerce-changes` — 실 API 미러(§15). 업종 파라미터를 받지 않고,
    미지원 metric은 404 `METRIC_NOT_FOUND`

### 오해 방지
범례에 **"업종 구분 없는 동 전체 평균"** 단서를 붙인다. 업종 선택은 사이드패널·마커에 계속
쓰이므로 비활성화하지 않는데, 그러면 업종을 바꿔도 색이 안 변하는 이유를 말해줘야 한다.
지표 이름만으로 오해가 생기는 경우에만 붙는다 — 폐업률·성장률·점포수에는 붙지 않는다.

### Validation
- 테스트 10건 추가 — mock 계약 5 · 원천 레지스트리 3 · 범례 표기와 단서 2. `tsc --noEmit` 통과
- 전체 107 통과 / 1 실패 — `use-agent-report.test.ts` 건은 이번 변경과 무관한 기존 실패

## [v0.16.0] - 2026-09-23

### Added
- **사이드패널 동네 프로필 섹션** — 백엔드 파생 지표(`GET /profiles/{region_code}`)를 화면에 올린다.
  업종과 무관한 동네 맥락이라 업종별 섹션(`INDUSTRY_SECTIONS`)보다 앞에 둔다
  - `features/map-explorer/components/neighborhood-profile.tsx` — 유형 이름 + 괄호 설명 +
    판정 근거 문장 + 시간대 서사 + 근거 수치 5줄. 조회 훅과 표시 본문
    (`NeighborhoodProfileBody`)을 나눠 본문만 단위 테스트한다
  - `shared/neighborhood.ts` — 유형 6종·시간대 라벨 5종·정점→바닥 서사의 표기 어휘.
    지도 탐색과 AI 분석이 함께 쓸 것이므로 shared에 둔다(§14 feature 간 직접 import 금지)
  - `shared/api/types.ts`에 `RegionProfile`, `map-explorer/api.ts`에 `fetchRegionProfile`
  - mock 라우트 `/api/mock/profiles/[regionCode]` — 실 API 미러(§15). 분기 생략 시 최신,
    없는 동·형식이 틀린 분기 모두 404 `REGION_PROFILE_NOT_FOUND`. 픽스처는 FNV-1a 해시 기반
    결정적 생성이고 유형 분포를 실측(주거 60%·먹자 13%…)에 맞춰 가중한다

### 문구 결정
- **`office` 유형을 "낮 인구 우위형"으로 부른다.** 분류 문서 §7-2가 남겨둔 결정이다. 판정 결과
  36개 동에 테헤란로·여의도·가산 같은 오피스와 함께 **가회동(북촌)·한남동·청담동·압구정동**이
  들어오는데, 이들에게 "업무 밀집형"은 틀린 말이다. 이 유형이 실제로 잡는 것은 "상주 대비 낮
  인구가 압도적인 동"이고 전부 `time_label=day`다
- `dining`은 "먹자·나들이형" 유지 — 연남동·이태원·서교동의 성격을 구어체로 정확히 짚는다
- **결측은 0이 아니다.** 직장인구가 없는 11개 동의 `worker_resident_ratio`는 "집계 없음"으로
  띄운다. 0으로 읽으면 주거형으로 오해한다 (테스트로 고정)
- **정점→바닥 서사는 관측이 많은 5종만 만든다.** 나머지 4종은 전 서울에 7개 동뿐이라 문장을
  만들면 한두 동의 잡음이 단정으로 굳는다. 없으면 시간대 라벨 문장으로 물러선다 (분류 문서 §6-4)

### Validation
- 테스트 21건 추가 — 어휘 8 · mock 계약 6 · 표시 본문 7. `tsc --noEmit` 통과
- 전체 97 통과 / 1 실패 — `use-agent-report.test.ts`의 "NEXT_PUBLIC_API_BASE가 실 API여도
  분석 요청·SSE는 mock 베이스를 유지한다"는 **이번 변경과 무관한 기존 실패**다
  (단독 실행에서도 실패하고, import 경로가 이번 변경 파일과 겹치지 않는다)

## [v0.15.1] - 2026-09-23

### Fixed
- **`npm run e2e` / `npm run shots` 동작 불가** — 랜딩 도입으로 지도가 `/`에서 `/map`으로 옮겨진 뒤
  `frontend/scripts/` 두 파일이 작업 트리에서 소실돼 package.json의 두 스크립트가 실행되지 않았다.
  커밋본을 복원하고 지도 진입·헬스체크·폴백 내비게이션 경로를 `/map`으로 갱신.
- **실 백엔드 환경에서 E2E가 통과할 수 없던 목 데이터 전제 6건** (`e2e-journey.sh`) — `.env.local`의
  `NEXT_PUBLIC_API_BASE=/api/backend`로 띄운 개발 서버에서 전부 실패하던 지점들:
  - API 베이스 하드코딩(`/api/mock`) → `NEXT_PUBLIC_API_BASE`·`.env.local`을 next와 같은 우선순위로
    읽는다. §15 "실 API 전환은 코드 수정 없이 env로만"에 맞춘다
  - 클릭 목표가 목 픽스처의 사각형 중심이라 실 행정동 경계에서는 다른 동에 떨어진다 → 렌더된 경계
    GeoJSON에서 대상 동의 중심을 구해 투영한다
  - 이후 단계 기준을 "의도한 동"에서 "실제로 선택된 동"으로. 특정 동을 맞히는 것이 아니라
    동 선택 → 마커 로드 → 프리필 배선 확인이 목적이다
  - 제출 버튼이 라벨 뒤에 `aria-hidden` 화살표 span을 갖게 바뀌어 텍스트 정확일치가 깨졌다
    (`textContent`는 "분석 시작→") → 역할+접근성 이름으로 찾는다
  - 완료 판정 문구 "종합 진단"은 목 픽스처에만 있다 → 리포트 article의 상태와 본문 길이로 판정
- **7단계가 분석 시작 전에 통과하던 버그** — `wait --text "참고 자료"`가 빈 상태 안내문("분석 내용과
  참고 자료가 이곳에 차례로 모입니다")에 걸려 즉시 통과했다. 목 응답이 빨라 가려져 있었다 →
  리포트 상태 폴링으로 교체(`E2E_REPORT_TIMEOUT`, 기본 300초). `작성 중단`이면 즉시 실패한다.
- **4단계 계측이 원리상 동작하지 않던 문제** — `agent-browser network requests`는 문서·스크립트·
  스타일·폰트만 기록하고 fetch/XHR은 남기지 않는다(0.27.0 실측) → 브라우저 리소스 타이밍을 읽는다.

### Validation
- 실 백엔드(`/api/backend`) 상대로 `npm run e2e` 8단계 전량 통과 (리포트 본문 1,401자).
  폴리곤 클릭도 통과 — 알려진 지도 렌더링 버그는 해소된 상태(`E2E_XFAIL_CLICK` 불필요).
- 두 스크립트 `bash -n` 구문 검사 통과.

## [v0.15.0] - 2026-09-17

### Added
- **서울 상권 아틀라스 랜딩** — `/`에 한국어 히어로, 상권 탐색 CTA, 기능 소개와 이용 순서를 추가.
  Blender로 제작한 도시 모형·위치 핀을 투명 WebP 2장(총 74,590 bytes)으로 제공하고 CSS로만 움직임을 표현.
  `art/landing/`에 재현 스크립트·편집 가능한 `.blend`·제작 문서를 포함. 모바일·reduced-motion에서는 장식 모션 정지.
- **지도 전용 `/map` 경로** — 기존 루트의 `region`·`industry`·`metric`·`year` 쿼리 링크는 모든 쿼리를 보존해 이동.
  지도 링크 자동 prefetch를 끄고 랜딩의 지도 모듈·API 로드를 분리.

### Changed
- **세 화면의 톤 통일** — 공통 색상·헤더를 따뜻한 아이보리/청록 계열로 정리하고 다크 테마 제공.
  지도는 필터·지도 프레임·지역 브리프의 위계를, AI 분석은 입력·진행 상황·문서형 리포트의 위계를 정리.
  모바일에서 패널을 세로로 배치하며 지도 렌더링·데이터 색상 스케일·API·분석 SSE 계약은 유지.
- **AI 분석 탭의 mock 고정 상수(`ANALYSIS_API_BASE`) 제거** — 분석 시작 POST와 SSE가 다른 탭과 같은 `config.apiBase`를 따른다.
  이에 맞춰 `use-agent-report.test.ts`의 "mock 베이스 유지" 계약 테스트를 "API 베이스를 따른다"로 갱신(T0-1 착지 시).
  AI 분석은 기존 `/api/mock` 연결을 유지하며 실제 분석 백엔드로 전환하지 않음.
- 기존 e2e·스크린샷 스크립트의 지도 진입 주소를 `/map`으로 갱신.

### Fixed
- 분석 도중 오류가 발생하면 부분 리포트를 유지하면서 상태를 `작성 중단`으로 표시.
- 공통 보조 텍스트 색상을 조정해 밝은 패널에서 일반 텍스트 대비 5.12:1 확보.

### Validation
- Vitest **25파일 77건 통과**, `npx tsc --noEmit`·`npm run build`·스크립트 구문 검사 통과.
- 브라우저: 랜딩 1440/1024/390/320px, 지도·완성 리포트 데스크톱/390/320px 및 다크 테마 확인.
  지도 클릭 → 지역/업종 전달 → 분석 제출 → 리포트 5개 섹션·참고 자료 4건 표시 확인.
  업종·지표·연도 변경과 기존 루트 지도 URL의 이동 확인. 검사한 화면에서 가로 넘침 없음.
- 랜딩의 canvas·지도 API 요청 없음, 모바일/reduced-motion 정지 확인. 별도 서브에이전트 검토 지적 수정 후 재검토 완료.
## [v0.14.4] - 2026-09-22

### Fixed
- **스트림 에러 시 에이전트 슬롯 stale** — SSE onerror·JSON 파싱 실패 때 `running` → `error`
- **테마 새로고침 light 리셋** — `localStorage(metabole-theme)` + layout 부트 스크립트

### Changed
- **Pretendard CDN → 셀프호스트** — `pretendard` 패키지 CSS import (`globals.css`)
- **AnalysisForm 업종 select** — `INDUSTRIES` 목록
- **`readAccentColor` → `shared/lib/accent-color.ts`** (map-view export 제거)
- **maplibre 워커 벤더 자동화** — `scripts/vendor-maplibre-worker.sh` + `postinstall`

## [v0.14.3] - 2026-09-22

### Changed
- **어린이집·편의점 폐업률·성장률 다시 노출** — 지표 버튼·사이드패널 카드 3종 모두 표시.
  값이 없으면 "데이터 없음"으로 두고, 스냅샷 원천 안내 문구만 유지 (v0.14.1 숨김 철회).

## [v0.14.2] - 2026-09-22

### Fixed
- **딥링크 `?region=` 지도 이동** — GeoJSON 행정동 bbox로 `fitBounds` (진입·선택 시).
  순수 함수 `bboxOfRegion` + 단위 테스트.

## [v0.14.1] - 2026-09-22

### Fixed
- **어린이집·편의점 "데이터 없음" 정리** — 스냅샷 원천이라 폐업률·성장률이 NULL인 업종에서
  지표 버튼을 점포수만 노출하고, URL의 폐업률/성장률은 `store_count`로 보정.
  사이드패널은 해당 카드 숨김 + 안내 문구. 지도 빈 지표 배너 문구를 점포수 기준으로 구분.

## [v0.14.0] - 2026-09-21

### Changed
- **AI 분석 탭 실 SSE 전환** — `ANALYSIS_API_BASE=/api/mock` 상수·TODO 제거. 분석 POST·EventSource가
  `config.apiBase`(`NEXT_PUBLIC_API_BASE=/api/backend`)를 따름. 훅 로직 무변경(계약 동일).
- 테스트: mock 고정 계약을 "config.apiBase를 따른다"로 반전

## [v0.13.1] - 2026-09-17

### Fixed
- **원격 개발 환경에서 "지도 데이터를 불러오지 못했습니다" 배너** — VS Code Remote-SSH 포트 포워딩으로 접속하면
  브라우저가 노트북에서 돌아 `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8201`이 서버가 아니라 노트북 자신을 가리켰음
  (백엔드 로그에 브라우저 요청 0건으로 확인)

### Added
- `src/shared/backend-proxy.ts` + `next.config.ts` rewrites — `/api/backend/*` → `BACKEND_ORIGIN/*` 개발 서버 프록시.
  브라우저는 프론트 origin(3200)만 호출. `BACKEND_ORIGIN`(서버 전용 env) 미설정 시 규칙 없음 — Vercel·mock 동작 무변경
- `src/shared/backend-proxy.test.ts` — 규칙 생성(끝 슬래시 정규화)·미설정 시 빈 규칙 테스트 2건

### Changed
- `frontend/.env.local`(미커밋 로컬 설정) — `NEXT_PUBLIC_API_BASE=/api/backend`, `BACKEND_ORIGIN=http://127.0.0.1:8201`
- 검증: 프록시 경유 health·geojson(5.4MB)·metrics 200, 404 에러 바디 전달, 브라우저 요청이 `/api/backend`로만 나감 —
  vitest 23파일 68건 통과, `tsc --noEmit` 통과

## [v0.13.0] - 2026-09-17

### Added
- **어린이집 지도 연결** (백엔드 v0.20.0 childcare 조회 API 소비) — 업종 `어린이집` 선택 + 행정동 클릭 시
  - 지도: 어린이집 클러스터 마커, 팝업에 `유형 · 상태` / `정원 · 현원 (가동률)` / `입소대기` 표시
    (상태·대기 원천 공란은 `상태 미상`·`미공개` — 0으로 추정하지 않음)
  - 사이드패널: `어린이집 현황` 섹션(운영 시설 수·가동률(현원/정원)·입소대기 합(중복 신청 포함)·기준일)
- `src/shared/api/types.ts` — `ChildcareCenter`, `ChildcareRegionSummary` 계약 타입
- `src/app/api/mock/childcare-centers/route.ts`, `src/app/api/mock/childcare-center-stats/summary/route.ts` —
  실 API 미러 mock(404 `REGION_NOT_FOUND`), `fixtures.ts`에 FNV-1a 결정적 `childcareCentersOf`·`childcareSummaryOf`
  (요약 = 마커 목록 합산, 실 API 합산 규칙과 동일)
- `src/features/map-explorer/components/marker-strategies.ts` — **업종별 마커 전략(Strategy)**: 조회 함수·queryKey·
  팝업 DOM을 업종이 스스로 결정. 전용 원천 업종만 레지스트리 등록(`childcare`), 나머지는 store 점포 전략
- `src/features/map-explorer/components/childcare-summary.tsx` — `ChildcareSummaryList`(표시)·
  `ChildcareSummarySection`(TanStack Query `["childcare-summary", region]`)
- `src/features/map-explorer/lib/childcare-format.ts` — `formatOccupancy`·`formatWaiting` 순수 함수
- 테스트 12건 — mock 라우트 계약 5(200 형태·결정성·404·요약=목록 합산), 포맷 2, 마커 전략 3(어린이집 팝업·공란 표기·
  점포 전략 폴백), 요약 목록 2(행 렌더·시설 없음 안내)

- **편의점 지도 연결** (백엔드 v0.20.0 convenience 조회 API 소비) — 업종 `편의점` 선택 + 행정동 클릭 시
  - 지도: 편의점 클러스터 마커, 팝업에 `상호 지점명` / 브랜드(미확인은 `기타 브랜드`) / 도로명주소
  - 사이드패널: `편의점 현황` 섹션(편의점 수·브랜드별 점포 수(미확인은 `기타`)·원천 기준연월)
  - `ConvenienceStore`·`ConvenienceRegionSummary` 타입, mock `convenience-stores`·`convenience-stores/summary` 라우트 +
    결정적 픽스처(요약 = 목록 브랜드 집계, 실 API 정렬 규칙 동일), `marker-strategies.ts`에 `convenience_store` 전략 등록,
    `convenience-summary.tsx`, `side-panel.tsx` 레지스트리 등록
  - 테스트 9건 — mock 계약 5·마커 전략 2(팝업·기타 브랜드)·요약 목록 2
  - 브라우저 실검증: 역삼1동 클러스터 149 → 개별 마커 팝업 "씨유역삼우리점 · CU · 서울특별시 강남구 역삼로19길 14",
    사이드패널 브랜드 분포 표시 — vitest 22파일 66건 통과, `tsc --noEmit` 통과

### Changed
- `src/features/map-explorer/components/store-markers.tsx` → **`region-markers.tsx`(`RegionMarkers`)** — 점포 전용
  클러스터 마커를 전략 주입형으로 일반화(소스/레이어 id `stores-*` → `markers-*`, 클릭 핸들러는 ref로 최신 전략 참조).
  점포 팝업 DOM 생성은 `marker-strategies.ts`로 이동(동작 동일)
- `src/features/map-explorer/components/side-panel.tsx` — 업종별 추가 섹션 레지스트리 `INDUSTRY_SECTIONS`
  (조건 분기 대신 등록) — `childcare`·`convenience_store` 등록
- 브라우저 실검증(agent-browser, 실 API 8201): 청운효자동 클러스터 4 → 개별 마커 팝업 "세종마을어린이집 · 국공립 · 정상 ·
  정원 50 · 현원 44 (88.0%) · 입소대기 25건", 사이드패널 요약 표시. 카페 선택 시 `/stores` 마커 정상·어린이집 섹션 미표시

## [v0.12.0] - 2026-09-07

### Added
- `frontend/src/features/map-explorer/components/map-legend.tsx` — **단계구분도 범례** (포스트MVP 이연 항목): 지도 우하단 패널(MapLibre 어트리뷰션 위·좌하단 Next dev 인디케이터 회피), 7색 스와치 + 값 구간 텍스트 라벨 목록(`<ul>` 시맨틱, 스와치는 `aria-hidden` — 색에만 의존하지 않음) + `데이터 없음`(NO_DATA_COLOR) 행. 값 포맷은 지표별 `formatLegendValue`(폐업률·성장률 %(소수 1자리, 음수 부호 그대로), 점포수 정수 — Record 디스패치). classes가 비면(데이터 없는 업종) 렌더링하지 않음. 테마 토큰(`--bg-surface`/`--border`/`--text-secondary`) 사용, 다크 모드 검증 완료
- `frontend/src/features/map-explorer/components/map-legend.test.tsx` — 포맷 함수(%·정수·음수 부호)/구간+데이터 없음 행 렌더링/빈 classes 숨김 테스트 3건
- `frontend/src/features/map-explorer/lib/metric-color.test.ts` — 클래스 경계 노출 테스트 3건 추가: 7구간 연속성(min~max 빈틈 없음), sequential 분위수 경계값 일치 + colorOf와 단일 원천 일관성, diverging ±extent 대칭·중앙 구간 0 포함

### Changed
- `frontend/src/features/map-explorer/lib/metric-color.ts` — **`makeMetricColorScale` 반환 타입 변경**: `(value) => string` → `{ colorOf, classes }` (`MetricColorScale`). 내부 경계 breaks로 colorOf와 범례용 `classes: {color, from, to}[]`를 함께 생성하는 `scaleFromBreaks` 단일 원천 — 페인트 색과 범례 구간이 항상 일치. 빈 values는 `NO_DATA_COLOR` colorOf + 빈 classes
- `frontend/src/features/map-explorer/components/map-view.tsx` — 색상 스케일을 effect 내부 생성 대신 `useMemo`로 끌어올려 fill-color 페인트와 `<MapLegend>`가 동일 scale을 공유

### Added
- `frontend/src/features/map-explorer/components/map-view.tsx` — **지도 위 에러 배너** (컷오버 필수 결함 3a): geojson/metrics fetch 실패 시 `role="alert"` 배너 표시(기존 side-panel/analysis의 에러 표시 관행과 일관, `--danger` 토큰). 실 API가 데이터 미보유 업종·연도에 200 + 빈 배열을 반환하는 경우 `role="status"` "지표 데이터 없음" 안내 배너 표시(빈 지도 + 데이터 없음 명시)
- `frontend/src/features/agent-report/components/progress-panel.test.tsx` — 동일 tool+summary 이벤트 반복 시 React key 중복 경고가 없음을 검증하는 TDD 테스트
- `frontend/src/features/agent-report/hooks/use-agent-report.test.ts` — SSE payload가 JSON이 아닐 때 error 상태 합류·스트림 close 검증, `NEXT_PUBLIC_API_BASE`가 실 API여도 분석 POST·SSE가 `/api/mock` 베이스를 유지함을 검증하는 테스트 2건 추가(`FakeEventSource`에 listener 캡처/emit 기능 추가)
- `frontend/src/features/map-explorer/lib/map-state.test.ts` — `YEARS`가 2019~2026 8개년임을 고정하는 계약 테스트(백엔드 v0.9.0 지표 제공 범위와 일치 — 코로나 충격 시계열 조회 가능. 상수 자체는 v0.4.0부터 이미 8개년이라 코드 변경 없음)

### Changed
- `frontend/.env.local` — `NEXT_PUBLIC_API_BASE=http://localhost:8201` 추가(실 API 컷오버, 미커밋 로컬 설정 — 커밋되는 `config.ts`의 `/api/mock` 폴백은 유지)
- `frontend/src/features/agent-report/hooks/use-agent-report.ts` — **AI 분석 탭만 mock 유지**: 분석 시작 POST와 SSE `EventSource`가 `config.apiBase` 대신 명시적 `ANALYSIS_API_BASE = "/api/mock"` 상수를 사용(RAG 분석 백엔드 미구현 — 실 분석 API 전환 시 `config.apiBase`로 복귀, TODO 주석)
- `frontend/src/shared/api/client.ts` — `apiPost`에 선택적 `base` 파라미터 추가(기본값 `config.apiBase`, 기존 호출부 무영향)

### Fixed
- `frontend/src/features/agent-report/hooks/use-agent-report.ts` — SSE `JSON.parse` 무가드 수정 (컷오버 필수 결함 3b): 손상된 payload를 try/catch로 잡아 `onerror`와 동일한 에러 경로(에러 메시지 + close + finish)에 합류
- `frontend/src/features/agent-report/components/progress-panel.tsx` — 동일 tool+summary 이벤트 반복 시 React key 중복 경고 수정 (컷오버 필수 결함 3c): `tool:summary` content 기반 key → append-only 리스트에서 안정적인 인덱스 포함 key(`{i}:{tool}`)로 교체

### 실 API 계약 검증 (백엔드 v0.9.0, uvicorn 8201)
- `GET /regions/geojson` 427 MultiPolygon, `GET /metrics` 427행, `GET /regions/{code}/summary` fact 카드 3장(side-panel 정상 렌더), `GET /stores` 역삼1동 카페 705행(클러스터 정상 처리, `status_name: "영업"`) — curl + 브라우저(agent-browser) 실검증
- 데이터 미보유 업종(편의점 등 4종)은 `/metrics`·`/stores` 모두 200 + 빈 배열 → 빈 지도 + "지표 데이터 없음" 배너 + summary 카드 "데이터 없음" 값으로 우아하게 처리됨을 확인
- 백엔드 중단 상태에서 지도 접속 시 `role="alert"` 에러 배너 표시 확인. vitest 39건·`tsc --noEmit` 통과

## [v0.10.1] - 2026-09-07

### Changed
- `frontend/src/features/map-explorer/lib/metric-color.ts` — 단계구분도 색상을 연속 보간에서 **이산 7클래스**로 교체 (인접 동 색 대비 강화)
  - sequential: OrRd 5스톱 보간 → **YlOrRd 7클래스 + 분위수(quantile) 경계** — 각 클래스에 비슷한 수의 동이 배분되어 색 다양성이 최대화됨
  - diverging: RdBu 5스톱 보간(도메인 중점 기준) → **RdBu 7클래스 + 0 중심 대칭** — 성장률 부호가 그대로 색 부호(음수=파랑, 0 부근=중립, 양수=빨강)
  - API: `metricColor(value, domain, scheme)` → `makeMetricColorScale(values, scheme)` (값 분포로부터 색상 함수 생성). `map-view.tsx`의 `domainOf` 제거
- `frontend/src/features/map-explorer/lib/metric-color.test.ts` — 분위수 클래스 배분·클램프·0 중심 대칭·빈 값 폴백 6건으로 재작성 (vitest 35건 통과)

## [v0.10.0] - 2026-09-07

### Added
- `frontend/public/geojson/seoul-regions.geojson` — 서울 행정동 427개 실경계 FeatureCollection (5.2MB). 백엔드 v0.8.0 `GET /regions/geojson` 산출물 스냅샷(좌표 5자리 절삭, `properties={region_code, name}` — name은 DB `region.name` 조인). TownPulse(site.townpulse.www)의 프론트 정적 GeoJSON 패턴 참고

### Changed
- `frontend/src/app/api/mock/fixtures.ts` — `SEOUL_SAMPLE_GEOJSON`(강남권 사각형 8개 mock) → `SEOUL_REGIONS_GEOJSON`(실경계 427개, `readFileSync` 로드)으로 교체. `DONGS`/`rectPolygon` 제거, 지역 목록은 `REGIONS`(features의 properties 파생)로 대체 — `metricRows`가 427개 동 전체를 커버해 코로플레스가 서울 전역에 칠해짐
- `frontend/src/features/map-explorer/api.ts` — `RegionGeoJSON` geometry 타입 `Polygon` → `Polygon | MultiPolygon` 확장 (실경계는 전부 MultiPolygon)
- mock 라우트·테스트의 `SEOUL_SAMPLE_GEOJSON` 참조명 일괄 갱신 (동작 변화 없음, vitest 32건 통과)

## [v0.9.1] - 2026-08-26

### Fixed
- `frontend/src/app/api/mock/fixtures.ts` — `metricRows(metric, year, industry)`에 `industry` 인자 추가, `hashSeed` 입력에 포함해 지표(choropleth)가 업종별로 달라지도록 수정. `summaryOf`가 점포수/폐업률/성장률 카드 계산 시 `metricRows`에 `industry`를 전달하도록 변경 — 업종을 바꿔도 지도 색상·요약 카드 수치가 그대로였던 데모 결함 수정
- `frontend/src/app/api/mock/metrics/route.ts` — `industry` 쿼리 파라미터를 읽어 `metricRows`에 전달, `stores` 라우트와 대칭인 `INDUSTRY_NOT_FOUND` 404 가드 추가
- `frontend/src/features/map-explorer/components/side-panel.tsx` — 에러 상태 div에 `role="alert"` 추가 (`analysis-page.tsx`의 기존 패턴과 일치)
- `frontend/src/app/api/mock/metrics/route.test.ts`, `frontend/src/app/api/mock/fixtures.test.ts` — industry 파라미터 필수화에 맞춰 기존 테스트 업데이트, 업종별 값 분산·결정성(같은 조합→동일 값) 검증 테스트 추가

## [v0.9.0] - 2026-08-26

### Added
- `frontend/src/app/api/mock/store-samples.ts` — backend `store` 테이블 실데이터(297k행, beyondfacade-db)에서 8개 동 × 6개 업종(billiard/cafe/gym/hair_salon/karaoke/pc_bang) bounding box로 필터링해 추출한 점포 표본(`STORE_SAMPLES`, 동×업종당 최대 20건). store 테이블에 실적재 데이터가 없는 업종(convenience_store/real_estate/academy/childcare)은 표본에 없음 — 해당 조합은 의도적으로 빈 배열
- `frontend/src/app/api/mock/stores/route.ts` — `GET /stores?region={code}&industry={id}` mock 라우트. 미등록 region은 404 `REGION_NOT_FOUND`, 미지원 industry는 404 `INDUSTRY_NOT_FOUND`(metrics 라우트의 `METRIC_NOT_FOUND` 가드와 대칭)
- `frontend/src/app/api/mock/stores/route.test.ts` — 정상 조회/미등록 region/미지원 industry/실적재 데이터 없는 업종(빈 배열) TDD 테스트 4건
- `frontend/src/app/api/mock/fixtures.ts` — `storesOf(regionCode, industryId)`: `STORE_SAMPLES`를 region·industry로 필터링해 `Store[]` 반환
- `frontend/src/features/map-explorer/components/store-markers.tsx` — `<StoreMarkers>`: MapLibre GeoJSON 클러스터 소스(`cluster: true`, `clusterMaxZoom: 14`, `clusterRadius: 50`) + 클러스터/클러스터 카운트/비클러스터 3개 레이어. 클러스터 클릭 시 `getClusterExpansionZoom`으로 확대, 개별 마커 클릭 시 상호·개업일·영업상태 팝업. 동 선택(`regionCode`) 없으면 소스를 빈 FeatureCollection으로 유지(성능 가드 — 전 서울 로드 금지). 클러스터/마커 페인트 색상은 `map-view.tsx`와 동일한 `--accent`/`--bg-surface`/`--accent-fg` 토큰을 읽어 적용하고, `data-theme` `MutationObserver`로 테마 전환 시 재적용
- `frontend/src/features/map-explorer/api.ts` — `fetchStores(regionCode, industry)` 추가 (`apiGet` 경유)
- `frontend/src/shared/api/types.ts` — `Store` 인터페이스(`store_id, name, lat, lng, status_name, open_date`)

### Changed
- `frontend/src/features/map-explorer/components/map-view.tsx` — `readAccentColor()`를 export(마커 페인트 색상도 동일 토큰을 읽어야 하므로), `<StoreMarkers>`를 지도 컨테이너에 배선(`mapRef`/`ready`/`regionCode`/`industry` 전달)
- `frontend/scripts/e2e-journey.sh` — 사이드패널 확인 직후 "점포 마커 로드 확인" 단계 추가(동 선택 후 `GET /api/mock/stores` 네트워크 요청 발생 여부를 `agent-browser network requests --filter`로 검증 — WebGL 캔버스 클러스터는 DOM으로 직접 검사할 수 없어 그 트리거인 네트워크 요청으로 배선을 확인). 단계 번호 7→8단계로 재조정
- `frontend/scripts/screenshot-matrix.sh` — 동 선택 후 점포 마커/클러스터가 보이는 지도 화면(`map-markers_{theme}_{width}.png`) 스크린샷 추가

## [v0.8.0] - 2026-08-26

### Added
- `frontend/src/shared/industries.ts` — 업종 id 목록(`INDUSTRIES`)과 한국어 라벨(`INDUSTRY_LABELS`, `industryLabel()`)의 공통 어휘 모듈. 지도 탐색·AI 분석 두 feature가 함께 쓰므로 feature 간 직접 import 금지 규칙에 따라 `shared/`에 배치 (`map-state.ts`의 `INDUSTRIES` 정의를 이곳으로 이동)
- `frontend/src/shared/ui/route-fallback.tsx` — 라우트 셸 `<Suspense>` 폴백 컴포넌트 (`role="status"`, 레이아웃 높이 유지)
- `frontend/src/app/api/mock/metrics/route.test.ts` — metrics mock 라우트 TDD 테스트 2건 (지원 metric 200 / 미지원 metric 404 `METRIC_NOT_FOUND`)
- `frontend/src/app/globals.css` — `.report-markdown` 스코프 스타일. Tailwind preflight가 리셋한 리포트 마크다운 요소(h2/h3, p, strong, ul/ol, table/th/td)를 토큰 기반으로 복원하고 표에 `tabular-nums` 적용. `prefers-reduced-motion` 감축 규칙 추가
- `frontend/src/features/map-explorer/lib/map-state.ts` — `METRIC_LABELS` (폐업률·성장률·점포수)

### Changed
- `frontend/src/styles/tokens.css` — **강조색 확정 (스펙 열린 항목 1 해소)**: `ui-ux-pro-max` 팔레트 DB의 신뢰·데이터 계열 후보 3종(civic-navy / market-teal / ink-sky)을 스크린샷으로 비교해 **market-teal** 선택 — 라이트 `--accent: #0f766e` / 다크 `--accent: #2dd4bf`. 중립 스케일·`--ok/--warn/--danger`를 포함한 라이트/다크 11종 토큰 세트 전체를 확정값으로 교체. 선정 근거: 단계구분도 팔레트(warm 순차 / 청·적 발산)와 색상환이 겹치지 않아 지도 위 선택 강조선이 데이터색과 혼동되지 않으며, 상권·부동산 도메인 정합이 가장 높음
- `frontend/src/features/map-explorer/components/control-bar.tsx` — 지표 세그먼트가 raw id(`closure_rate` 등) 대신 한국어 라벨을 표시(값·URL 파라미터는 영문 유지), 업종 select도 한국어 라벨 표시. 각 컨트롤에 보이는 라벨(업종/지표/연도) 추가, 세그먼트에 `role="group"`+`aria-pressed`, 전 컨트롤에 `focus-visible` 아웃라인·hover·`active` 피드백 부여
- `frontend/src/features/map-explorer/components/side-panel.tsx` — 미선택/에러 상태를 안내 문구가 있는 구성된 빈 상태로 교체, 로딩을 텍스트 대신 스켈레톤으로 교체(`role="status"`), 지표 목록을 카드 대신 `divide-y` 구분선 구성으로 변경, 헤더에 region_code·업종 라벨 캡션 추가, CTA 버튼에 hover/active/focus 상태 추가
- `frontend/src/features/agent-report/components/analysis-form.tsx` — 지역 코드·업종을 2열 그리드로 배치하고 폼 너비를 `max-w-xl`로 제한(1440px에서 입력창이 전폭으로 늘어나던 문제), 업종 입력 아래 한국어 라벨 힌트 표시(입력값 자체는 API 계약상의 영문 id 유지), 추가 질문 placeholder, 제출 버튼 로딩 라벨("분석 중…")·focus/active 상태
- `frontend/src/features/agent-report/components/analysis-page.tsx` — 컨테이너 `max-w-[1400px]` 중앙 정렬, 진행 패널/리포트를 `lg` 이상에서만 2열로 분기(그 이하는 세로 스택), 에러 메시지에 `role="alert"`
- `frontend/src/features/agent-report/components/progress-panel.tsx` — 에이전트 4행을 카드 4개 대신 `divide-y` 타임라인으로 변경, `role="status" aria-live="polite"` 부여, 상태를 색상 점만이 아니라 텍스트 라벨(대기/진행 중/완료/오류)로도 노출(색상 단독 전달 금지 규칙)
- `frontend/src/features/agent-report/components/report-view.tsx` — 섹션에 `.report-markdown` 클래스 적용(제목·표·목록 스타일 복원), 빈 상태를 구성된 안내 박스로 교체, 참고 자료 목록을 `divide-y`+underline-offset 링크로 정리
- `frontend/src/shared/ui/top-bar.tsx` — 활성 탭을 색상만이 아니라 하단 2px 인디케이터로도 표시, 탭에 hover/focus-visible 상태, 헤더 `shrink-0`
- `frontend/src/shared/ui/theme-toggle.tsx`, `frontend/src/shared/ui/grade-badge.tsx` — hover/focus-visible/active 상태, 배지 `shrink-0 whitespace-nowrap`(좁은 패널에서 줄바꿈 방지)
- `frontend/src/app/page.tsx`, `frontend/src/app/analysis/page.tsx` — `<Suspense>`에 `<RouteFallback>` 지정(기존에는 fallback 없음)
- `frontend/package.json`, `frontend/scripts/e2e-journey.sh`, `frontend/scripts/screenshot-matrix.sh` — **포트 규약 정정 3500 → 3200** (`next dev/start -p 3200`, 스크립트 `BASE_URL` 기본값 및 헤더 주석). 루트 `docker-compose.yml`의 frontend 서비스 포트(3200)와 일치
- `frontend/scripts/e2e-journey.sh` — 역삼1동 폴리곤 클릭 좌표를 하드코딩(666,538) 대신 런타임 계산으로 변경. 지도 컨테이너의 실제 `getBoundingClientRect()`에 웹 메르카토르 투영(zoom 11, bearing/pitch 0)으로 구한 오프셋을 더한다. 상단바·컨트롤바 높이가 바뀌면 하드코딩 좌표가 조용히 빗나가던 취약성 제거(이번 레이아웃 변경으로 실제 좌표가 538 → 700으로 이동)

### Fixed
- `frontend/src/features/map-explorer/components/control-bar.tsx` — 존재하지 않는 토큰 `--border-color`를 참조해 border 선언이 무효화되고 `currentColor`로 폴백되던 버그 수정 (올바른 토큰명은 `--border`)
- `frontend/src/app/layout.tsx`, `frontend/src/features/map-explorer/components/map-page.tsx`, `map-view.tsx` — `/` 지도 화면이 뷰포트 높이를 채우지 못하고 하단에 빈 영역이 남던 레이아웃 버그 수정. `<body>`의 `min-h-full`은 `<html>`에 높이가 없어 해석되지 않으므로 `min-h-[100dvh]`로 교체하고, flex 체인에 `min-h-0`·`overflow-hidden`을 추가해 `MapView`의 `h-full`이 실제로 남은 높이를 받도록 함(`min-h-[480px]` → `min-h-[320px]` 안전 하한)
- `frontend/src/app/api/mock/metrics/route.ts` — 미지원 `metric` 파라미터가 들어오면 `METRIC_RANGES` 조회 실패로 500이 나던 문제 수정. summary 라우트의 `REGION_NOT_FOUND` 가드와 대칭으로 404 `METRIC_NOT_FOUND`를 반환하도록 검증 추가
- `frontend/src/app/layout.tsx` — `<title>`이 스캐폴드 기본값("Create Next App")으로 남아 있던 문제 수정 → "Metabole — 상권 분석" + 설명 metadata

### 스택 핀 버전
`next@16.3.2` / `react@19.2.8` · `react-dom@19.2.8` / `maplibre-gl@^6.6.0` / `@tanstack/react-query@^5.102.3` / `react-markdown@^10.1.0` · `remark-gfm@^4.0.1` / `tailwindcss@^4` · `@tailwindcss/postcss@^4` / `typescript@^5` / `vitest@^4.1.11` · `jsdom@^29.1.1` · `@testing-library/react@^16.3.2`

## [v0.7.2] - 2026-08-26

### Fixed
- `frontend/src/features/map-explorer/components/map-view.tsx` — 지도 탭에서 행정동 폴리곤(단계구분도)이 전혀 렌더/클릭되지 않던 버그 수정. 근본 원인: maplibre-gl@6.6.0은 GeoJSON 타일링을 수행하는 워커 스크립트의 URL을 `import.meta.url` 기반으로 런타임에 자체 계산하는데, Turbopack 번들 청크의 `import.meta.url`은 http(s) URL이 아니어서 그 계산이 빈 문자열로 실패해 워커가 뜨지 못하고 타일링이 조용히 멈춰 있었다(콘솔/네트워크 에러 없음). `maplibre-gl`의 `setWorkerUrl()`로 워커 스크립트 경로를 명시 지정해 우회. Turbopack의 `new URL(path, import.meta.url)` 정적 에셋 처리는 참조 파일을 해시된 이름으로 그대로 복사할 뿐 내부 상대 import(`./maplibre-gl-shared.mjs`)는 재작성하지 않으므로, `maplibre-gl-worker.mjs`와 `maplibre-gl-shared.mjs`를 원본 파일명 그대로 `frontend/public/maplibre-gl/`에 함께 두고 그 경로를 지정했다(버전 `maplibre-gl@6.6.0` 고정, 이 패키지를 업그레이드하면 두 파일도 함께 갱신해야 함).
- `frontend/scripts/e2e-journey.sh` — 위 렌더링 버그가 고쳐지면서 실제로 폴리곤을 클릭해 보니, 기존 클릭 좌표(613, 446)가 `map.project()`의 지도-컨테이너 상대 좌표를 그대로 페이지 절대 좌표로 오인해 계산된 값이라 실제로는 대상 폴리곤을 빗나가고 있었음을 확인. 지도 컨테이너의 페이지 오프셋(top:114, left:0)을 더한 올바른 페이지 절대 좌표(666, 538)로 교정.
- `frontend/package.json` — `e2e` 스크립트에서 `E2E_XFAIL_CLICK=1` 기본값 제거. 지도 렌더링 버그가 해결되어 `npm run e2e`가 실제 폴리곤 클릭 경로까지 엄격 모드(클릭 실패 시 exit 1)로 통과한다.

## [v0.7.1] - 2026-08-26

### Fixed
- `frontend/scripts/e2e-journey.sh` — "동 폴리곤 클릭" 단계가 실패해도 stderr 경고만 남기고 조용히 폴백 내비게이션 후 exit 0으로 통과하던 문제 수정: 기본 동작은 클릭 실패 시 exit 1(명확한 한국어 오류 메시지)로 종료하도록 변경. 알려진 지도 렌더링 버그로 인한 실패를 의도적으로 우회하려면 `E2E_XFAIL_CLICK=1`을 명시적으로 지정해야 하며, 이 경우 최종 stdout 요약에 `XFAIL: 폴리곤 클릭 (지도 렌더링 버그)` 줄이 출력된다. 스크립트 헤더 주석에 두 모드를 문서화.
- `frontend/scripts/e2e-journey.sh`, `frontend/scripts/screenshot-matrix.sh` — `set -euo pipefail` 하에서 중간 단계가 실패하면 스크립트 마지막의 `AB close`가 실행되지 못해 헤드리스 브라우저/agent-browser 데몬 프로세스가 누수되던 문제 수정: 스크립트 상단에 `trap 'AB close >/dev/null 2>&1 || true' EXIT`를 추가해 정상/비정상 종료 모두에서 정리되도록 함(기존 말미의 중복 `AB close` 호출 제거).
- `frontend/package.json` — `e2e` npm 스크립트를 `E2E_XFAIL_CLICK=1 bash scripts/e2e-journey.sh`로 변경해, 지도 렌더링 버그가 열려 있는 동안 기본 `npm run e2e`는 계속 녹색을 유지하도록 함. 원본 스크립트(`bash scripts/e2e-journey.sh`)는 계속 엄격 모드를 유지하며, 지도 버그 수정 후 이 환경변수 없이 재검증해야 함.

## [v0.7.0] - 2026-08-26

### Added
- `frontend/src/shared/ui/top-bar.tsx` — `<TopBar />`: 로고("Metabole") + 탭 링크 2개(`/` 지도 탐색, `/analysis` AI 분석, `usePathname` 기반 `aria-current`/accent 하이라이트) + `<ThemeToggle />` 배치
- `frontend/src/shared/ui/top-bar.test.tsx` — 현재 경로 탭에 `aria-current="page"`가 붙는지 검증하는 TDD 테스트
- `frontend/scripts/e2e-journey.sh` — agent-browser(`npx -y agent-browser`) 기반 E2E 여정: `/` → 동 폴리곤 클릭 → 사이드패널 확인 → `[AI 분석 →]` 클릭 → `/analysis` 프리필 확인 → 분석 시작 → `report_done`까지 대기 → 리포트 텍스트 존재 assert. dev 서버 미기동 시 한국어 오류 메시지로 종료
- `frontend/scripts/screenshot-matrix.sh` — 화면(`/`, `/analysis` 시작 전·진행 중·완료) × 테마(light/dark, `ThemeToggle` 클릭으로 전환) × 뷰포트(1440/1024) 16종 스크린샷을 `frontend/screenshots/`에 저장
- `package.json` scripts: `e2e`, `shots`

### Changed
- `frontend/src/app/layout.tsx` — `<body>` 내부 `{children}` 위에 `<TopBar />` 렌더
- `frontend/.gitignore` — `/screenshots/` 추가 (E2E/스크린샷 산출물은 커밋 대상 아님)
- `package.json` — `dev`/`start` 스크립트 포트를 3000 → 3500으로 변경 (`next dev -p 3500`, `next start -p 3500`)

## [v0.6.1] - 2026-08-25

### Fixed
- `frontend/src/features/agent-report/hooks/use-agent-report.ts` — `start()` 재진입 가드 없음으로 인한 `EventSource` 누수 수정: `loadingRef`로 `apiPost` await 이전에 동기적으로 재진입을 차단(진행 중이면 무시), `loading` 상태를 훅 반환값에 추가. `apiPost` 실패를 `try/catch`로 잡아 `state.error`에 반영(기존에는 unhandled rejection이었음)
- `frontend/src/features/agent-report/components/analysis-page.tsx` — `useAgentReport().loading`을 `AnalysisForm`의 `disabled`로 실제 전달(더블클릭 방지 UI 배선)
- `frontend/src/features/agent-report/components/progress-panel.tsx`, `report-view.tsx` — 타임라인/인용 리스트의 index key를 `tool:summary`/`title:url` 조합 키로 교체

### Added
- `frontend/src/features/agent-report/hooks/use-agent-report.test.ts` — `EventSource`/`fetch` mock으로 `start()` 연속 호출 시 연결이 1개만 생성됨을 검증하는 재진입 가드 테스트

## [v0.6.0] - 2026-08-25

### Added
- `frontend/src/features/agent-report/lib/agent-events.ts` — `initialAgentState()`/`applyAgentEvent(state, ev)` 순수 리듀서. `AgentState = { agents: Record<AgentName, {status, tools}>; sections: Record<string, string>; done; citations; error }`, 4개 `AgentEvent` 타입별 불변 갱신
- `frontend/src/features/agent-report/lib/agent-events.test.ts` — agent_status/tool_call 누적/report_delta 이어붙임/report_done TDD 테스트 4건
- `frontend/src/features/agent-report/hooks/use-agent-report.ts` — `useAgentReport()`: `apiPost("/analysis", ...)` → `EventSource(\`${config.apiBase}/analysis/{id}/events\`)` 구독, 4개 이벤트 타입 `addEventListener` → 리듀서 적용, `report_done`/언마운트 시 close, `onerror` 시 `error` 상태 노출
- `frontend/src/features/agent-report/components/progress-panel.tsx` — 에이전트 4행(오케스트레이터/상권 진단/충격 분석/정책자금) 상태 점(idle/running/done/error, 토큰 기반) + 도구 호출 타임라인(최근 항목 강조)
- `frontend/src/features/agent-report/components/report-view.tsx` — 섹션 순서 고정(`verdict,market,shock,funding,calculator`) `react-markdown`(+`remark-gfm`) 렌더, `report_done` 시 citations 목록(`GradeBadge`) — unknown 배열 런타임 가드
- `frontend/src/features/agent-report/components/analysis-form.tsx` — 지역 코드/업종/자유 질문 입력 폼, URL 프리필
- `frontend/src/features/agent-report/components/analysis-page.tsx` — map-page 패턴의 클라이언트 컴포넌트: URL region·industry 프리필 → 폼 → 진행 패널(좌) + 리포트(우)
- `frontend/src/app/analysis/page.tsx` — 서버 컴포넌트 + `<Suspense>`로 `AnalysisPage` 감싸기
- `remark-gfm` 의존성 (계산기 섹션 마크다운 표 렌더)

## [v0.5.0] - 2026-08-25

### Added
- `frontend/src/shared/ui/grade-badge.tsx` — `<GradeBadge grade="fact"|"signal">` 신뢰 배지 (fact=accent solid, signal=outline 중립, 토큰 기반)
- `frontend/src/shared/ui/grade-badge.test.tsx` — fact/signal 라벨 렌더 TDD 테스트
- `frontend/src/features/map-explorer/components/side-panel.tsx` — `<SidePanel regionCode industry>`: region summary TanStack Query(`enabled: !!regionCode`), 미선택/로딩/404("데이터 없음") 상태 분기, 카드 리스트 + `[AI 분석 →]` `/analysis?region=..&industry=..` 딥링크
- `frontend/src/features/map-explorer/api.ts` — `fetchRegionSummary(regionCode, industry)` 추가 (`apiGet` 경유)

### Changed
- `frontend/src/features/map-explorer/components/map-page.tsx` — `SidePanel`을 `MapView` 우측에 배선 (지도 flex-1 래퍼로 폭 조정)

## [v0.4.0] - 2026-08-25

### Added
- `frontend/src/features/map-explorer/lib/map-state.ts` — `MapState` 인터페이스, `parseMapState`/`serializeMapState` 라운드트립, `INDUSTRIES`/`METRICS`/`YEARS` 화이트리스트 상수
- `frontend/src/features/map-explorer/lib/map-state.test.ts` — 기본값/라운드트립/유효성 검증 TDD 테스트 3건
- `frontend/src/features/map-explorer/components/control-bar.tsx` — 업종 select/지표 segment/연도 select 컨트롤 (색상 토큰 기반)

### Changed
- `frontend/src/features/map-explorer/components/map-page.tsx` — `useRouter`/`useSearchParams` 통합: URL ↔ state 양방향 동기화, `ControlBar` 렌더, region 선택 → URL 반영
- `frontend/src/app/page.tsx` — `<Suspense>` 경계 추가 (useSearchParams 클라이언트 컴포넌트 감싸기)

## [v0.3.1] - 2026-08-25

### Fixed
- `map-view.tsx` — 테마(`data-theme`) 전환 시 선택 강조 line-color가 이전 테마의 `--accent`로 남던 버그. 테마 `MutationObserver` 콜백에서도 `readAccentColor()`로 line-color를 재적용하도록 수정.
- `map-view.tsx` — `#cccccc`/`#000000` 하드코딩 hex를 lib 상수/토큰 참조로 교체: `NO_DATA_COLOR`를 `metric-color.ts`에서 export해 fill-color 폴백 2곳에 재사용, 초기 line-color는 리터럴 대신 `readAccentColor()`로 시드.

## [v0.3.0] - 2026-08-25

### Added
- `frontend/src/features/map-explorer/lib/metric-color.ts` — sequential/diverging 색약 안전 5스톱 RGB 선형 보간 + 클램프 (`metricColor`)
- `frontend/src/features/map-explorer/lib/metric-color.test.ts` — 도메인 클램프/단조 증가/중립색 검증
- `frontend/src/features/map-explorer/api.ts` — `fetchRegionsGeoJson`, `fetchMetrics` (`apiGet` 경유)
- `frontend/src/features/map-explorer/hooks/use-map-data.ts` — `useMapData(metric, industry, year)`: geojson(staleTime Infinity) + metrics rows TanStack Query
- `frontend/src/features/map-explorer/components/map-view.tsx` — MapLibre 지도(서울 중심, zoom 11), 브이월드 라이트/다크 래스터 타일(`data-theme` MutationObserver로 전환), geojson 단계구분도(fill match expression) + 선택 강조(line 레이어) + 클릭 시 `onSelectRegion`
- `frontend/src/features/map-explorer/components/map-page.tsx` — 클라이언트 상태 보관용 얇은 래퍼 (`page.tsx` 서버 컴포넌트 유지를 위한 경계)

### Changed
- `frontend/src/app/page.tsx` — Next 기본 스캐폴드 마크업 제거, `MapPage` 렌더로 교체

## [v0.2.0] - 2026-08-25

### Added
- Next.js 16 앱 스캐폴드 (`create-next-app`: TypeScript, App Router, Tailwind, `src/` 디렉토리, `@/*` import alias)
- `@tanstack/react-query`, `maplibre-gl`, `react-markdown` 의존성
- Vitest 테스트 러너 (`frontend/vitest.config.ts`, `frontend/src/test/setup.ts`) + `@testing-library/*`, `jsdom`
- `frontend/src/shared/config.ts` — `NEXT_PUBLIC_API_BASE` 기반 `config.apiBase` (기본값 `/api/mock`), `config.vworldKey`
- `frontend/src/shared/config.test.ts` — `config.apiBase` 기본값 검증
- `package.json` scripts: `test`, `test:watch`

## [v0.1.0] - 2026-08-24

### Added
- `frontend/Dockerfile` — node:22-alpine 로컬 개발용 이미지 (배포는 Vercel 담당, 스택 확정 후 동작)
- 루트 docker-compose.yml에 `frontend` 프로필 서비스 등록 (포트 3200, 스택 확정 전 기본 기동 제외)
