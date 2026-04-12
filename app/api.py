"""
Rotas de observabilidade/logs para painel externo.
Prefixo: /ajeboxe/logs/
"""
import json
import logging

from fastapi import APIRouter, HTTPException

from app.services.redis_service import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ajeboxe")

# Sufixo base das chaves Redis deste projeto
_KEY_SUFFIX = "--aje"


def _phone_from_lead_key(key: str) -> str:
    return key.replace(f"{_KEY_SUFFIX}:lead", "")


def _phone_from_history_key(key: str) -> str:
    return key.replace(f"{_KEY_SUFFIX}:history", "")


@router.get("/logs/leads")
async def logs_leads():
    """Retorna todos os leads com dados de CRM."""
    r = await get_redis()

    lead_keys = await r.keys(f"*{_KEY_SUFFIX}:lead")
    history_keys = await r.keys(f"*{_KEY_SUFFIX}:history")

    phones: set[str] = set()
    for k in lead_keys:
        phones.add(_phone_from_lead_key(k))
    for k in history_keys:
        phones.add(_phone_from_history_key(k))

    leads = []
    for phone in sorted(phones):
        crm = await r.hgetall(f"{phone}{_KEY_SUFFIX}:lead")
        msg_count = await r.llen(f"{phone}{_KEY_SUFFIX}:history")
        has_followup = await r.exists(f"{phone}{_KEY_SUFFIX}:followup:active") == 1
        leads.append({
            "phone": phone,
            "nome": crm.get("name", ""),
            "nicho": crm.get("nicho", ""),
            "resumo": crm.get("resumo", ""),
            "event_id": crm.get("event_id", ""),
            "msg_count": msg_count,
            "has_followup": has_followup,
        })

    leads.sort(key=lambda x: x["msg_count"], reverse=True)
    return leads


@router.get("/logs/history/{phone}")
async def logs_history(phone: str):
    """Retorna o histórico de mensagens de um lead."""
    r = await get_redis()

    raw = await r.lrange(f"{phone}{_KEY_SUFFIX}:history", 0, -1)
    messages = []
    for item in raw:
        try:
            entry = json.loads(item)
            messages.append({
                "role": entry.get("type", ""),
                "content": entry.get("data", {}).get("content", ""),
            })
        except Exception:
            pass
    return messages


@router.get("/logs/events")
async def logs_events(limit: int = 100):
    """Retorna os últimos N eventos de execução do worker."""
    r = await get_redis()

    raw = await r.lrange("aje:logs", 0, limit - 1)
    events = []
    for item in raw:
        try:
            events.append(json.loads(item))
        except Exception:
            pass
    return events
