from fastapi import FastAPI

from apps.news.adapter.inbound.api.v1.news_article_router import router as news_router
from apps.store.adapter.inbound.api.v1.store_router import router as store_router

app = FastAPI(title="beyondfacade backend")
app.include_router(news_router)
app.include_router(store_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
