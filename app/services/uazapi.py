import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30)
    return _client


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "token": settings.UAZAPI_TOKEN,
    }


async def send_text(number: str, text: str) -> dict:
    url = f"{settings.UAZAPI_BASE_URL}/send/text"
    payload = {"number": number, "text": text}
    client = _get_client()
    resp = await client.post(url, json=payload, headers=_headers())
    resp.raise_for_status()
    logger.info("Texto enviado para %s", number)
    return resp.json()


async def send_image(number: str, image_url: str, caption: str = "") -> dict:
    url = f"{settings.UAZAPI_BASE_URL}/send/image"
    payload = {"number": number, "image": image_url, "caption": caption}
    client = _get_client()
    resp = await client.post(url, json=payload, headers=_headers())
    resp.raise_for_status()
    logger.info("Imagem enviada para %s", number)
    return resp.json()


async def send_document(number: str, document_url: str, filename: str = "arquivo.pdf") -> dict:
    url = f"{settings.UAZAPI_BASE_URL}/send/document"
    payload = {"number": number, "document": document_url, "fileName": filename}
    client = _get_client()
    resp = await client.post(url, json=payload, headers=_headers())
    resp.raise_for_status()
    logger.info("Documento enviado para %s", number)
    return resp.json()


async def send_video(number: str, video_url: str, caption: str = "") -> dict:
    url = f"{settings.UAZAPI_BASE_URL}/send/video"
    payload = {"number": number, "video": video_url, "caption": caption}
    client = _get_client()
    resp = await client.post(url, json=payload, headers=_headers())
    resp.raise_for_status()
    logger.info("Video enviado para %s", number)
    return resp.json()


async def download_media(media_url: str) -> bytes:
    client = _get_client()
    resp = await client.get(media_url, headers=_headers())
    resp.raise_for_status()
    return resp.content
