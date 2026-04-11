import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.consumer import start_consumer
from app.webhook import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(start_consumer())
    logging.getLogger(__name__).info("Consumer RabbitMQ iniciado")
    yield
    task.cancel()


app = FastAPI(title="AJE DE BOXE - Bot WhatsApp", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
