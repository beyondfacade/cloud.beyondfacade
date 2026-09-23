# Seoul Atlas Landing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Build the approved lightweight landing with actual Blender-rendered assets, align map and analysis presentation with its visual tone, and preserve existing data interactions.
**Architecture:** A server-rendered landing feature at `/` links to the existing map at `/map`; existing root map queries redirect with their values intact. Decorative images animate only through CSS; no web 3D runtime.
**Tech Stack:** Existing Next.js 16, React 19, TypeScript, Tailwind/CSS modules, Blender 5, Pillow for render conversion.
**Spec:** `docs/superpowers/specs/2026-09-17-atlas-landing-design.md`

## Global Constraints

- Preserve map/analysis behavior and data contracts; the user subsequently authorized their visual restyle and shared palette alignment.
- No new frontend dependencies. No canvas/WebGL/MapLibre API activity on the landing.
- Root owns Blender assets and documentation. Frontend implementer owns UI, routes, navigation tests, and existing journey script route updates.
- Images: `/landing/seoul-diorama.webp` 1600×1400; `/landing/location-pin.webp` 256×320. Both have alpha.
- Mobile and reduced-motion: no decorative movement. Landing navigation to map disables prefetch.
- Work in the current checkout on `codex/seoul-atlas-landing`; do not change or commit the user's unrelated documents.

### Task 1: Landing and navigation

**Files:** Create `frontend/src/features/landing/components/landing-page.tsx` and scoped styles, `frontend/src/app/map/page.tsx`; modify root page, shared top bar, tokens, existing route-dependent journey scripts. Add only meaningful route/navigation tests.

**Interfaces:** `LandingPage()` is the server-renderable landing. It consumes the image paths above. `/map` renders the existing `MapPage` inside Suspense. Old root map query keys are `region`, `industry`, `metric`, `year`.

- [x] Read repo instructions and local Next page/image/navigation documentation.
- [x] Add failing navigation tests covering the move to `/map`, return to landing, and old query preservation. Example contract: a root URL with `region=1168064000&industry=cafe&year=2025` reaches `/map?region=1168064000&industry=cafe&year=2025`; an unrelated `utm_source` query stays on the landing.
- [x] Run the focused tests and confirm the expected failure.
- [x] Implement the root route using awaited `searchParams` and `redirect` only for map query keys; implement `/map` with the prior root page composition. Use `new URLSearchParams()` with append for repeated keys when forwarding parameters.
- [x] Implement the approved hero: eyebrow `SEOUL COMMERCIAL ATLAS`, heading `서울의 변화 속에서, 내 가게의 자리를 찾다.`, explanatory copy, `상권 탐색하기` link to `/map` with `prefetch={false}`, visual and three labels. Use warm editorial whitespace, clear title scale, restrained shadows, a brief feature strip and how-to section.
- [x] Align shared top bar on map/analysis with the user-approved visual extension. Landing has its own header; shared TopBar returns null for the root route without importing a feature.
- [x] Add scoped motion and responsive styling. Use shared semantic tokens with the approved palette, supply dark variants and visible keyboard focus. Do not fabricate metrics or claim live/complete AI data.
- [x] Update existing e2e/screenshot map URLs to `/map` so they still exercise the map.
- [x] Run focused tests and TypeScript check; report changed files, failures and any interface decisions. Do not commit.

### Task 2: Blender visual assets (root)

**Files:** `frontend/art/landing/build_scene.py`, `frontend/art/landing/README.md`, generated `.blend` source in the same directory, public WebP assets.

**Interfaces:** Exact image paths and dimensions from Global Constraints; city composition fills frame with margins for a light UI overlay. Rendering is offline.

- [x] Build a deterministic Blender scene with a river, low-rise neighborhoods, parks, bridges and a restrained tower; render an orthographic editorial city diorama with alpha.
- [x] Render a separate ceramic location pin with the same material/lighting. Save editable `.blend` and reproducible script.
- [x] Convert the new Blender renders to WebP at a visually sufficient quality, inspect actual images, and target combined image bytes below 700 KB.
- [x] Document commands, asset provenance, and the conceptual (non-geospatial) nature of the scene.

### Task 3: Integration and verification (root)

- [x] Inspect responsive screenshots at 1440, 1024, 390 and 320 px; inspect light/dark/reduced-motion states, CTA and legacy URL preservation, and map behavior.
- [x] Check the landing's network requests for accidental map scripts/API requests and review image payload sizes.
- [x] Run `npm test`, `npx tsc --noEmit`, `npm run build`; address failures caused by this change.
- [x] Request independent review of spec compliance and code quality while doing visual QA; resolve material findings.
- [x] Record final validation and version entry in `frontend/docs/frontend_ver_log.md`; leave work reviewable on the task branch.


### Task 4: User-approved workspace styling extension

- [x] Delegate map presentation to landing_ui; preserve map renderer, markers, URL state and data calls.
- [x] Delegate analysis presentation to analysis_ui; preserve submission/SSE/report data contracts.
- [x] Align shared top bar and semantic tokens with landing. Darken muted text to meet normal-text contrast on panel surfaces.
- [x] Review expanded diff and fix material findings.
- [x] Verify map selection, filter controls, analysis submission and completed report in browser, including mobile and dark layouts.
- [x] Run final full tests, TypeScript and production build after integration.
