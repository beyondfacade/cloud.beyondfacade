from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from apps.master.adapter.inbound.api.v1.region_router import router as region_router
from apps.metric.adapter.inbound.api.v1.region_industry_metric_router import (
    router as metric_router,
)
from apps.news.adapter.inbound.api.v1.news_article_router import router as news_router
from apps.store.adapter.inbound.api.v1.store_router import router as store_router

app = FastAPI(title="beyondfacade backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3200", "http://127.0.0.1:3200"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)  # /regions/geojson 등 대형 응답 압축
app.include_router(region_router)
app.include_router(metric_router)
app.include_router(news_router)
app.include_router(store_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
