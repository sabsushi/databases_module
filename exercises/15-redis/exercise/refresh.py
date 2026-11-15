import os
import secrets
import time

import psycopg

from patterns import DATABASE_URL, acquire_lock, release_lock, r

LOCK = "lock:refresh:monthly_revenue"
pid = os.getpid()
token = secrets.token_hex(16)

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] pid {pid}: {msg}", flush=True)

if not acquire_lock(LOCK, token, ttl=60):
    log(f"skipped: lock is held by another process (TTL {r.ttl(LOCK)} s)")
    raise SystemExit(0)

try:
    log("lock acquired, refreshing monthly_revenue")
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue")
    log("refreshed; holding the lock 5 more seconds")
    time.sleep(5)
finally:
    released = release_lock(LOCK, token)
    log(f"lock released: {released}")
