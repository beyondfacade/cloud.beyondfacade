# 서울 행정동 경계 (427개)

- 원천: 통계청 통계지리정보서비스(SGIS, https://sgis.kostat.go.kr) 행정동 경계 — 공공누리 제1유형(출처표시)
- 가공: vuski/admdongkor ver20260701 (https://github.com/vuski/admdongkor) — CC BY 4.0
- 이 저장소에서는 서울 행정동만 동별 파일(`regions/{region_code}.json`)로 나눴다

백엔드가 실행 중에 읽는다(`/regions/geojson`, 크론 assign_regions·childcare_collector). 이미지 빌드 때 `--build-context geojson=data/geojson`으로 들어간다 — CI(`.github/workflows/backend-deploy.yml`)에서 빌드하려고 저장소에 둔다.
