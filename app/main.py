import logging

from fastapi import FastAPI

from app.webhook import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="AJE DE BOXE - API")
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
