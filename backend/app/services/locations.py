"""동승자 실시간 위치 — Redis 캐시 (잦은 갱신, 짧은 TTL)."""

import json
from datetime import datetime, timezone

import redis

from app.core.config import settings

LOCATION_TTL_SEC = 120

_pool = redis.ConnectionPool.from_url(settings.REDIS_URL)


def _client() -> redis.Redis:
    return redis.Redis(connection_pool=_pool)


def _key(match_id: int, user_id: int) -> str:
    return f"match:{match_id}:loc:{user_id}"


def save_location(match_id: int, user_id: int, lat: float, lng: float) -> dict:
    payload = {
        "type": "location",
        "user_id": user_id,
        "lat": lat,
        "lng": lng,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _client().setex(_key(match_id, user_id), LOCATION_TTL_SEC, json.dumps(payload))
    return payload


def get_locations(match_id: int, user_ids: list[int]) -> list[dict]:
    client = _client()
    results = []
    for uid in user_ids:
        raw = client.get(_key(match_id, uid))
        if raw:
            results.append(json.loads(raw))
    return results
