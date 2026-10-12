FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 비루트 실행 — 앱은 /app에 쓰지 않는다(로그는 stdout, 원천 파일은 /data 볼륨)
RUN useradd --create-home --uid 10001 app
COPY --chown=app:app . .
# 행정동 경계 427개(8MB) — /regions/geojson과 크론(assign_regions·childcare_collector)이 실행 중에 읽는다.
# region.geometry_ref("data/geojson/regions/*.json")가 루트 기준 상대경로라 /data/geojson에 둔다.
# 빌드 컨텍스트(backend/) 밖이라 이름 붙은 컨텍스트로 받는다: --build-context geojson=data/geojson
COPY --from=geojson . /data/geojson/
USER app

EXPOSE 8000
# SIGTERM 뒤 새 요청은 받지 않고 진행 중 요청(SSE 리포트 최대 60초)만 마친다 — k8s 종료 유예 90초 = preStop 10 + 75 + 여유
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "75"]
