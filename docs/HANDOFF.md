> ⚠️ **2026-09-24: 이 문서는 낡았다. 현재 상태의 정본은 [`docs/STATUS.md`](STATUS.md)다** — 실DB·크론·git을 직접 재서 만든 것이고, 여기 적힌 "차단"·"대기" 항목 다수(SGIS·fp16 등)는 이미 끝났다.

# HANDOFF — 남은 작업

> 작성: 2026-09-22 · `feature/analysis-api` · 백엔드 v0.22.x / 프론트 v0.14.4

## 1. 현재 상태 요약

| 영역 | 상태 |
|---|---|
| 지도 탐색 | 실 API 연결 완료 — 업종 10종 지표, 어린이집·편의점 마커·사이드패널·점포수 지표까지 동작 |
| AI 분석 탭 | ✅ 실 SSE (`feature/analysis-api`, FE v0.14.x) — 두뇌 A/B/C 팀 결정 대기 |
| 수집 크론 | store 매일 04:20(+지표·지오코딩) · funding 05:10 · rag 색인 05:50 · 어린이집 월 05:30 · 편의점 월 05:40 · 뉴스 매시 10분 |
| 도커 | 백엔드 이미지 v0.20.0, `beyondfacade-api` 8200 (조회 전용) — compose 프론트 포트 3200 정합 |
| 로컬 개발 서버 | 백엔드 uvicorn 8201(--reload), 프론트 next dev 3200 (`/api/backend` 프록시 → 8201) |
| 원격 | `feature/analysis-api` 푸시됨 · PR #1 |

## 2. 남은 작업 (우선순위순)

### 2-1. AI 분석 실구현 — Task 11~14 ✅ (feature/analysis-api)

| 태스크 | 내용 | 상태 |
|---|---|---|
| Task 11 | `POST /analysis` + SSE + 영속화 | ✅ BE v0.21.0 |
| Task 12 | 프론트 mock → 실 SSE | ✅ FE v0.14.0 |
| Task 13 | 모델 비교 평가 러너 | ✅ |
| Task 14 | gemma4 vs Gemini 2.5 비교표 | ✅ — 채택(A/B/C)은 팀 결정 대기 |

### 2-2. 데이터 계층

- [x] **SGIS 지오코딩** (v0.22.0) — 완료.
  학원 25,504·중개 25,299 좌표 / 행정동 배정 25,504·25,281 / `region_industry_metric` 3,408·3,416행.
  미매칭 잔여 학원 4·중개 2. (워크트리에 `data/geojson` 심링크 필요 — 본진 `data/geojson` 참조)
- [x] **fp16 전량 재색인** — 7,505건 전부 `qwen3-embedding-4b-fp16` (343.8s).
  (참고) candidate 50건 Recall@5 **0.900** / MRR 0.791 — confirmed 0건이라 본지표 미산출
- [ ] **RAG 평가셋 검수 (사용자 작업)** — `data/eval/rag_evalset.jsonl` candidate 50건 → confirmed 승격해야 Recall@5 본지표 산출 가능
- [ ] **어린이집 폐업률** — 원천이 폐지 시설을 주지 않아 주간 스냅샷의 소실(`last_seen_on` 정지)로만 산출 가능. 몇 달 누적 후 산출 방식 결정
- [ ] 연령별 인구 2026.07분 1파일 추가 (공표 확인 후)
- [ ] 국토부 상업업무용 실거래가(매입가 추정), 상권→자치구 매핑표 (포스트MVP 후보)

결정된 사항(재검토 불필요): 편의점 폐업률·성장률을 담배소매인 데이터로 대체 산출하지 않음 (슈퍼·가판 혼재).

### 2-3. 프론트엔드 UX

- [x] **어린이집·편의점 선택 시 "데이터 없음" 표시 정리** — FE v0.14.1/v0.14.3 (스냅샷 업종 안내 + 폐업률·성장률 카드 유지)
- [x] 딥링크(`?region=`) 지도 이동 — FE v0.14.2 fitBounds
- [x] 포스트MVP 잔여 (v0.14.4): 스트림 stale·테마 유지·Pretendard 셀프호스트·`readAccentColor` lib·AnalysisForm select·maplibre 워커 postinstall

### 2-4. 배포·인프라

- [x] `feature/analysis-api` 푸시 + [PR #1](https://github.com/beyondfacade/cloud.beyondfacade/pull/1) — main 머지는 리뷰 후
- [ ] **Vercel 앱 배포** — CLI 계정(`amysoo02-7611s-projects`)에 Metabole 프로젝트 없음.
  `beyondfacade.cloud` / `metabole.beyondfacade.cloud` = GitHub Pages(문서) 200.
  앱은 Vercel 프로젝트 신설 + `NEXT_PUBLIC_API_BASE` + 백엔드 터널 필요
- [x] docker-compose 프론트 포트 — `3200:3200` + Dockerfile `EXPOSE 3200` (next -p 3200 정합)
- [ ] AWS G 인스턴스 쿼터 증설 신청 (8/25 이월)

### 2-5. 정리

- [ ] 미커밋 파일: `docs/jekyll.md`(수정), `docs/superpowers/plans/2026-08-25-frontend-mvp.md`·`docs/프로젝트_산출물_구조.md`(미추적) — 커밋 여부 결정
- [x] 플랜·스펙 문서의 버전 표기 — rag-agent 설계/플랜에 실제 버전(BE v0.21+/FE v0.14+) 주석
- [ ] 원장의 deferred minor 10건 — 최종 리뷰에서 머지 전 처리 여부 분류
- [x] `test_latest_source_updated_at_returns_cursor` — 실DB 오염 회피(미래 커서 시각)

## 3. 작업 시 주의

- **원격 개발 환경**: VS Code Remote-SSH라 브라우저는 노트북에서 돈다. 브라우저가 서버 포트(127.0.0.1:8201 등)에 직접 붙는 설정 금지 — `NEXT_PUBLIC_API_BASE=/api/backend` + `BACKEND_ORIGIN=http://127.0.0.1:8201` 유지
- 사용자 열람용 8201·3200 프로세스는 종료 금지 (검증용은 8299 등 별도 포트)
- 크론 등록은 이 서버 crontab에만 있음 (git 미포함)
- 컨테이너(8200)에는 `backend/.env`가 들어가지 않음 — 수집·LLM 호출은 로컬 venv에서
- 어린이집정보공개포털 API는 https 전용, 일 1,000회(서울 전체 25회/스냅샷)
