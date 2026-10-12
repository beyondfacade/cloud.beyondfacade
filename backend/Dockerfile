FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 비루트 실행 — 앱은 /app에 쓰지 않는다(로그는 stdout, 원천 파일은 /data 볼륨)
RUN useradd --create-home --uid 10001 app
COPY --chown=app:app . .
USER app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
