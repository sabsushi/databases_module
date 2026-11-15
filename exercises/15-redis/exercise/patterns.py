import json
import os
import time

import psycopg
import redis

DATABASE_URL = os.environ["DATABASE_URL"]
r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

VIEWED_MAX = 20
VIEWED_TTL = 30 * 24 * 3600

def viewed_key(customer_id: int) -> str:
    return f"customer:{customer_id}:viewed"

def record_view(customer_id: int, film_id: int, now: float | None = None) -> None:
    key = viewed_key(customer_id)
    now = time.time() if now is None else now
    with r.pipeline(transaction=True) as p:
        p.zadd(key, {str(film_id): now})
        p.zremrangebyrank(key, 0, -(VIEWED_MAX + 1))
        p.expire(key, VIEWED_TTL)
        p.execute()

def recent_views(customer_id: int) -> list[int]:
    return [int(f) for f in r.zrevrange(viewed_key(customer_id), 0, -1)]

FILM_CACHE_TTL = 300

def film_cache_key(film_id: int) -> str:
    return f"cache:film:{film_id}"

def get_film(film_id: int) -> tuple[dict | None, str]:
    key = film_cache_key(film_id)
    cached = r.get(key)
    if cached is not None:
        return json.loads(cached), "hit"

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT title, rating::text, length, rental_rate FROM film WHERE film_id = %s",
            (film_id,),
        ).fetchone()
    if row is None:
        return None, "miss"
    film = {"title": row[0], "rating": row[1], "length": row[2], "rental_rate": str(row[3])}
    r.set(key, json.dumps(film), ex=FILM_CACHE_TTL)
    return film, "miss"

def update_film_rate(film_id: int, rate) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("UPDATE film SET rental_rate = %s WHERE film_id = %s", (rate, film_id))
    r.delete(film_cache_key(film_id))

RELEASE_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
else
    return 0
end
"""
_release = r.register_script(RELEASE_LUA)

def acquire_lock(name: str, token: str, ttl: int = 60) -> bool:
    return bool(r.set(name, token, nx=True, ex=ttl))

def release_lock(name: str, token: str) -> bool:
    return _release(keys=[name], args=[token]) == 1

RATE_LIMIT = 10

def allow_request(customer_id: int, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    minute = int(now // 60)
    key = f"rate:{customer_id}:{minute}"
    with r.pipeline(transaction=True) as p:
        p.incr(key)
        p.expire(key, 120, nx=True)
        count, _ = p.execute()
    return count <= RATE_LIMIT
