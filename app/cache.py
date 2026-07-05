import hashlib
import json

import redis.asyncio as aioredis

from app.config import settings

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


class CacheKeys:
    @staticmethod
    def templates_list() -> str:
        return "cache:templates"

    @staticmethod
    def template(slug: str) -> str:
        return f"cache:template:{slug}"

    @staticmethod
    def user_requests(user_id: str) -> str:
        return f"cache:user:{user_id}:requests"

    @staticmethod
    def extraction(template_id: str, text: str) -> str:
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"cache:extraction:{template_id}:{text_hash}"


class CacheTTL:
    TEMPLATES = 600  # 10 minutes
    USER_REQUESTS = 120  # 2 minutes
    EXTRACTION = 3600  # 1 hour — one-shot AI call, deterministic given (template, text)


async def get_cached(key: str) -> dict | list | None:
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None


async def set_cached(key: str, data, ttl: int) -> None:
    await redis_client.setex(key, ttl, json.dumps(data, default=str))


async def delete_cached(key: str) -> None:
    await redis_client.delete(key)
