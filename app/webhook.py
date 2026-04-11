"""
Fluxo 1: Webhook -> RabbitMQ
Recebe mensagens do WhatsApp (UAZAPI), filtra e publica na fila.
"""
import logging

from fastapi import APIRouter, Request

from app.config import settings
from app.services.rabbitmq import publish

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_message_type(message: dict) -> tuple[str, str]:
    """Retorna (tipo, conteudo_texto) da mensagem."""
    if "conversation" in message:
        return "Conversation", message["conversation"]
    if "extendedTextMessage" in message:
        return "ExtendedTextMessage", message["extendedTextMessage"].get("text", "")
    if "imageMessage" in message:
        return "ImageMessage", ""
    if "audioMessage" in message:
        return "AudioMessage", ""
    if "videoMessage" in message:
        return "VideoMessage", ""
    if "documentMessage" in message:
        return "DocumentMessage", ""
    if "contactMessage" in message:
        return "ContactMessage", str(message["contactMessage"])
    if "reactionMessage" in message:
        return "ReactionMessage", message["reactionMessage"].get("text", "")
    return "Unknown", ""


@router.post(settings.WEBHOOK_PATH)
async def webhook(request: Request):
    payload = await request.json()

    # Filtra mensagens enviadas pelo proprio n8n / bot (evita loop)
    track_source = payload.get("track_source", "")
    if track_source == "n8n":
        return {"status": "ignored", "reason": "track_source=n8n"}

    # Extrai dados do payload UAZAPI
    data = payload.get("data", payload)
    key = data.get("key", {})
    remote_jid = key.get("remoteJid", "")
    from_me = key.get("fromMe", False)
    message_id = key.get("id", "")

    phone = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
    chat_id = remote_jid
    push_name = data.get("pushName", "")

    message_obj = data.get("message", {})
    msg_type, msg_text = _extract_message_type(message_obj)

    # Monta JSON padronizado para a fila
    queue_message = {
        "phone": phone,
        "push_name": push_name,
        "from_me": from_me,
        "message_id": message_id,
        "uazapi_base_url": settings.UAZAPI_BASE_URL,
        "instance": settings.UAZAPI_INSTANCE,
        "token": settings.UAZAPI_TOKEN,
        "msg_type": msg_type,
        "msg": msg_text,
        "chat_id": chat_id,
        "raw_message": message_obj,
    }

    await publish(queue_message)
    logger.info("Mensagem de %s publicada na fila", phone)
    return {"status": "queued"}
