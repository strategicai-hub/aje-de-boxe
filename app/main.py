import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.webhook import router
from app.api import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="AJE DE BOXE - API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
