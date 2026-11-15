import time

from patterns import (
    RATE_LIMIT, acquire_lock, allow_request, film_cache_key, get_film, r, recent_views,
    record_view, release_lock, update_film_rate, viewed_key,
)

def title(text):
    print(f"\n=== {text}")

title("1. Recently viewed films")
r.delete(viewed_key(1))
for film_id in range(1, 26):
    record_view(1, film_id)
    time.sleep(0.002)
print("customer 1 viewed films 1 to 25 in order")
print("recent_views(1):", recent_views(1))
print("number kept:", len(recent_views(1)))
record_view(1, 10)
print("after viewing film 10 again:", recent_views(1))
print("film 10 appears", recent_views(1).count(10), "time(s)")
print("TTL of", viewed_key(1), "=", r.ttl(viewed_key(1)), "seconds (30 days = 2592000)")

title("2. Cache-aside for film 1")
r.delete(film_cache_key(1))
update_film_rate(1, 0.99)
film, status = get_film(1)
print(f"get_film(1): {status}  {film}  (TTL {r.ttl(film_cache_key(1))} s)")
film, status = get_film(1)
print(f"get_film(1): {status}  {film}")
update_film_rate(1, 1.99)
print("update_film_rate(1, 1.99): PostgreSQL updated, cache key deleted ->",
      "exists" if r.exists(film_cache_key(1)) else "gone")
film, status = get_film(1)
print(f"get_film(1): {status}  {film}")
update_film_rate(1, 0.99)

title("3. Lock (see refresh.py for the two-process demonstration)")
name = "lock:demo"
r.delete(name)
print("process A acquires with token 'aaa':", acquire_lock(name, "aaa", ttl=60))
print("process B tries to acquire:", acquire_lock(name, "bbb", ttl=60))
print("process B tries to release with its token 'bbb':", release_lock(name, "bbb"),
      "-> lock still held by", r.get(name))
print("process A releases with 'aaa':", release_lock(name, "aaa"),
      "-> key exists:", bool(r.exists(name)))

title(f"4. Rate limit ({RATE_LIMIT} requests per customer per minute)")
wait = 60 - time.time() % 60
if wait < 50:
    print(f"(waiting {wait:.0f} s for a new minute to start)")
    time.sleep(wait + 0.1)
for key in r.scan_iter("rate:1:*"):
    r.delete(key)
results = [allow_request(1) for _ in range(12)]
minute = int(time.time() // 60)
print("12 calls for customer 1:", results)
print("True:", results.count(True), " False:", results.count(False))
print(f"counter rate:1:{minute} = {r.get(f'rate:1:{minute}')}, TTL {r.ttl(f'rate:1:{minute}')} s")
wait = 60 - time.time() % 60
print(f"waiting {wait:.0f} s for the next minute...")
time.sleep(wait + 0.1)
print("next minute, allow_request(1):", allow_request(1))
