import os

import psycopg
import redis

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]

KEY_PATTERN = "customer:*:categories"

CATEGORIES_SQL = """
SELECT r.customer_id, array_agg(DISTINCT c.name ORDER BY c.name) AS categories
FROM rental r
JOIN inventory i      ON i.inventory_id = r.inventory_id
JOIN film_category fc ON fc.film_id = i.film_id
JOIN category c       ON c.category_id = fc.category_id
GROUP BY r.customer_id
ORDER BY r.customer_id
"""

def key(customer_id: int) -> str:
    return f"customer:{customer_id}:categories"

def expected_from_postgres() -> dict[str, set[str]]:
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(CATEGORIES_SQL).fetchall()
    return {key(customer_id): set(categories) for customer_id, categories in rows}

def redis_client() -> redis.Redis:
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    db = r.connection_pool.connection_kwargs.get("db", 0)
    if db != 1:
        raise SystemExit(f"REDIS_URL must use logical database 1 (it uses {db})")
    return r

def scan_keys(r: redis.Redis) -> set[str]:
    return set(r.scan_iter(match=KEY_PATTERN, count=1000))
