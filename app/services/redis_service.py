import json
import redis.asyncio as redis

from app.config import settings

_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(settings.redis_url, decode_responses=True)
    return _pool


# --------------- bloqueio de agente ---------------

async def set_block(chat_id: str, ttl: int = settings.BLOCK_TTL_SECONDS) -> None:
    r = await get_redis()
    key = f"BloquearAgente-{chat_id}--{settings.UAZAPI_INSTANCE}"
    await r.set(key, "1", ex=ttl)


async def is_blocked(chat_id: str) -> bool:
    r = await get_redis()
    key = f"BloquearAgente-{chat_id}--{settings.UAZAPI_INSTANCE}"
    return await r.exists(key) == 1


# --------------- buffer de mensagens (debounce) ---------------

def _buffer_key(phone: str) -> str:
    return f"{phone}--{settings.UAZAPI_INSTANCE}-chat-id"


async def push_buffer(phone: str, text: str) -> int:
    r = await get_redis()
    return await r.rpush(_buffer_key(phone), text)


async def get_buffer(phone: str) -> list[str]:
    r = await get_redis()
    return await r.lrange(_buffer_key(phone), 0, -1)


async def delete_buffer(phone: str) -> None:
    r = await get_redis()
    await r.delete(_buffer_key(phone))


# --------------- historico de chat (Gemini) ---------------

def _history_key(phone: str) -> str:
    return f"chat_history:{phone}--{settings.UAZAPI_INSTANCE}"


async def get_chat_history(phone: str) -> list[dict]:
    r = await get_redis()
    raw = await r.lrange(_history_key(phone), 0, -1)
    return [json.loads(item) for item in raw]


async def append_chat_history(phone: str, role: str, text: str) -> None:
    r = await get_redis()
    entry = json.dumps({"role": role, "parts": [{"text": text}]})
    await r.rpush(_history_key(phone), entry)
    await r.ltrim(_history_key(phone), -50, -1)  # manter ultimas 50 msgs


async def clear_chat_history(phone: str) -> None:
    r = await get_redis()
    await r.delete(_history_key(phone))


# --------------- leads ---------------

def _lead_key(phone: str) -> str:
    return f"lead:{phone}"


async def get_lead(phone: str) -> dict | None:
    r = await get_redis()
    data = await r.hgetall(_lead_key(phone))
    return data if data else None


async def create_lead(phone: str, name: str = "") -> dict:
    r = await get_redis()
    lead = {
        "phone": phone,
        "name": name,
        "status_conversa": "Novo",
        "stage_follow_up": "0",
        "created_at": "",
    }
    await r.hset(_lead_key(phone), mapping=lead)
    return lead


async def update_lead(phone: str, **fields) -> None:
    r = await get_redis()
    if fields:
        await r.hset(_lead_key(phone), mapping=fields)


# --------------- follow-up ---------------

async def schedule_follow_up(phone: str, timestamp: float, stage: int = 1) -> None:
    r = await get_redis()
    await r.zadd("follow_ups", {phone: timestamp})
    await update_lead(phone, status_conversa="Em andamento", stage_follow_up=str(stage))


async def get_due_follow_ups(now: float) -> list[str]:
    r = await get_redis()
    return await r.zrangebyscore("follow_ups", "-inf", now)


async def remove_follow_up(phone: str) -> None:
    r = await get_redis()
    await r.zrem("follow_ups", phone)
