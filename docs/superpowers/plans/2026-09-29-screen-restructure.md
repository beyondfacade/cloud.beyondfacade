# 플랜 — 화면 재편 (설계서 `specs/2026-09-29-screen-restructure-design.md`)

6 태스크. T1·T2(백엔드, 클로드 서브에이전트)와 T3→T4→T5(프론트, Codex 순차)를 병행하고 T6에서 합친다. 각 태스크는 설계서 해당 절이 명세다.

| # | 담당 | 명세 | 완료 기준 |
|---|---|---|---|
| T1 | Claude BE | §7 | pytest green, 배치 12업종 재실행, `docs/verdict-backtest.md` 재생성, BE 로그 v0.44.0 항목 |
| T2 | Claude BE | §5-2, §6 | pytest green, `POST /analysis` budget, 도구 2개, 섹션 5개, BE 로그 v0.44.0 항목 |
| T3 | Codex FE | §3, §6 | Vitest·tsc clean, 옛 URL 파라미터 무시, 미사용 코드 삭제, FE 로그 v0.31.0 항목 |
| T4 | Codex FE | §4, §7(프론트 set) | Vitest·tsc clean, brief 한 화면, CTA href, FE 로그 누적 |
| T5 | Codex FE | §5-1, §6 | Vitest·tsc clean, URL 자동 시작, 5섹션·verdict 스테이지, mock SSE, FE 로그 누적 |
| T6 | Claude | §9 | 실 API 왕복 확인, HANDOFF·STATUS 갱신, 커밋 |
