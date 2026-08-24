from fastapi import FastAPI

app = FastAPI(title="beyondfacade backend")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
