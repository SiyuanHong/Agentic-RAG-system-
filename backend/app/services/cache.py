import struct
import uuid

import redis.asyncio as aioredis

from app.core.config import settings

_redis: aioredis.Redis | None = None

INDEX_NAME = "cache_idx"
PREFIX = "cache:"


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis


def _floats_to_bytes(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


async def init_cache_index() -> None:
    r = await get_redis()
    try:
        await r.execute_command("FT.INFO", INDEX_NAME)
    except Exception:
        # Index doesn't exist, create it
        await r.execute_command(
            "FT.CREATE",
            INDEX_NAME,
            "ON",
            "HASH",
            "PREFIX",
            "1",
            PREFIX,
            "SCHEMA",
            "query_embedding",
            "VECTOR",
            "FLAT",
            "6",
            "TYPE",
            "FLOAT32",
            "DIM",
            str(settings.EMBEDDING_DIMENSIONS),
            "DISTANCE_METRIC",
            "COSINE",
            "kb_id",
            "TAG",
            "answer",
            "TEXT",
        )


async def cache_lookup(
    query_embedding: list[float], kb_id: str, threshold: float = 0.95
) -> str | None:
    r = await get_redis()
    vec_bytes = _floats_to_bytes(query_embedding)

    # FT.SEARCH with KNN — cosine distance (0 = identical, 2 = opposite)
    # similarity = 1 - distance
    try:
        result = await r.execute_command(
            "FT.SEARCH",
            INDEX_NAME,
            f"(@kb_id:{{{kb_id}}})=>[KNN 1 @query_embedding $vec AS dist]",
            "PARAMS",
            "2",
            "vec",
            vec_bytes,
            "RETURN",
            "2",
            "answer",
            "dist",
            "SORTBY",
            "dist",
            "ASC",
            "LIMIT",
            "0",
            "1",
            "DIALECT",
            "2",
        )
    except Exception:
        return None

    # result: [total, key, [field, value, field, value, ...]]
    if not result or result[0] == 0:
        return None

    fields = result[2]
    answer = None
    dist = None
    for i in range(0, len(fields), 2):
        key = fields[i]
        val = fields[i + 1]
        if key == b"answer":
            answer = val.decode() if isinstance(val, bytes) else val
        elif key == b"dist":
            dist = float(val)

    if dist is not None and answer is not None:
        similarity = 1.0 - dist
        if similarity >= threshold:
            return answer
    return None


async def cache_store(
    query_embedding: list[float], kb_id: str, answer: str, ttl: int = 3600
) -> None:
    r = await get_redis()
    key = f"{PREFIX}{uuid.uuid4()}"
    vec_bytes = _floats_to_bytes(query_embedding)

    await r.hset(
        key,
        mapping={
            "query_embedding": vec_bytes,
            "kb_id": kb_id,
            "answer": answer,
        },
    )
    await r.expire(key, ttl)
