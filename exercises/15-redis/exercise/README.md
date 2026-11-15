# Exercise 15: Redis I, data structures and patterns

| File | What it is |
|---|---|
| `patterns.py` | The functions of the four patterns |
| `demo.py` | Demonstrations of patterns 1, 2, 4 (and the lock's token check) |
| `refresh.py` | Refreshes `monthly_revenue` under a Redis lock (task 3) |
| `pyproject.toml` | Dependencies (`redis`, `psycopg[binary]`) |

## How to run

From the repository root:

```bash
bash scripts/create-db.sh ex15 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex15 -v ON_ERROR_STOP=1 <<'SQL'
CREATE MATERIALIZED VIEW monthly_revenue AS
SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue
FROM payment
GROUP BY 1;

CREATE UNIQUE INDEX ON monthly_revenue (month);
SQL
```

In `.env`, set `DATABASE_URL=postgresql://postgres:<password>@localhost:5432/ex15` (`REDIS_URL` as in `.env.example`). From `exercises/15-redis/exercise/`:

```bash
uv sync
uv run --env-file ../../../.env python demo.py
uv run --env-file ../../../.env python refresh.py & uv run --env-file ../../../.env python refresh.py & wait
```

`demo.py` waits for the start of a new minute before the rate-limit demonstration, and for the next minute after it, so it takes up to about 2 minutes.

## Output of `demo.py`

```

=== 1. Recently viewed films
customer 1 viewed films 1 to 25 in order
recent_views(1): [25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6]
number kept: 20
after viewing film 10 again: [10, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 9, 8, 7, 6]
film 10 appears 1 time(s)
TTL of customer:1:viewed = 2592000 seconds (30 days = 2592000)

=== 2. Cache-aside for film 1
get_film(1): miss  {'title': 'ACADEMY DINOSAUR', 'rating': 'PG', 'length': 86, 'rental_rate': '0.99'}  (TTL 300 s)
get_film(1): hit  {'title': 'ACADEMY DINOSAUR', 'rating': 'PG', 'length': 86, 'rental_rate': '0.99'}
update_film_rate(1, 1.99): PostgreSQL updated, cache key deleted -> gone
get_film(1): miss  {'title': 'ACADEMY DINOSAUR', 'rating': 'PG', 'length': 86, 'rental_rate': '1.99'}

=== 3. Lock (see refresh.py for the two-process demonstration)
process A acquires with token 'aaa': True
process B tries to acquire: False
process B tries to release with its token 'bbb': False -> lock still held by aaa
process A releases with 'aaa': True -> key exists: False

=== 4. Rate limit (10 requests per customer per minute)
(waiting 15 s for a new minute to start)
12 calls for customer 1: [True, True, True, True, True, True, True, True, True, True, False, False]
True: 10  False: 2
counter rate:1:29912308 = 12, TTL 120 s
waiting 60 s for the next minute...
next minute, allow_request(1): True
```

### What each part shows

1. **Recently viewed films:** after viewing films 1 to 25, only the 20 most recent are kept (25 down to 6). Viewing film 10 again just updates its score in the sorted set, so it moves to the front and appears only once. The TTL is 2,592,000 seconds (30 days), and it's reset on every view. `ZADD`, `ZREMRANGEBYRANK` and `EXPIRE` run in one `MULTI`/`EXEC` pipeline, so they're applied together.
2. **Cache-aside:** the first `get_film(1)` is a miss (it reads PostgreSQL and stores the JSON for 300 s), and the second is a hit. `update_film_rate(1, 1.99)` writes to PostgreSQL first and then **deletes** the cache key. The next `get_film` is a miss that returns the new rate 1.99. Deleting instead of updating the cache avoids writing a value to Redis that might not match what was committed in PostgreSQL. (`demo.py` puts the rate back to 0.99 at the end.)
3. **Lock token:** process B can't take the lock while A holds it, and **can't release it either**, because the Lua script only deletes the key if it still holds the caller's token. Only A, with its own token, releases it.
4. **Rate limit:** 12 calls in the same minute give 10 `True` and 2 `False` (the counter reaches 12). In the next minute the key is different (`rate:1:<next minute>`), so the count starts again and the call gives `True`.

## Output of the two `refresh.py` processes

```
[10:29:03] pid 5155: lock acquired, refreshing monthly_revenue
[10:29:03] pid 5156: skipped: lock is held by another process (TTL 60 s)
[10:29:03] pid 5155: refreshed; holding the lock 5 more seconds
[10:29:08] pid 5155: lock released: True
```

Both start in the same second. Process 5155 gets the lock with `SET lock:refresh:monthly_revenue <random token> NX EX 60`, runs `REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue`, holds the lock 5 more seconds and releases it with the Lua script (`True`: it still held its token). Process 5156 finds the key already set (`NX` fails), so it skips the refresh instead of running it a second time.

**The lock is never released by a process that doesn't hold it:** each process uses a random token (`secrets.token_hex(16)`), and the release is a Lua script that runs `GET` and `DEL` as one atomic step on the server, deleting only if the value is still that token. If the refresh took longer than 60 s, the lock would expire and another process could take it. The first process's release would then find a different token and delete nothing (`False`). `EX 60` also makes sure that a process that crashes doesn't leave the lock held forever.

## Key patterns

| Key pattern | Redis type | TTL | Purpose |
|---|---|---|---|
| `customer:{customer_id}:viewed` | Sorted set (member = `film_id`, score = time of the view) | 30 days after the last view (reset by `EXPIRE` on every view) | The 20 films the customer viewed most recently, newest first |
| `cache:film:{film_id}` | String (JSON with `title`, `rating`, `length`, `rental_rate`) | 300 s | Cache-aside copy of a film row from PostgreSQL; deleted when the film is updated |
| `lock:refresh:monthly_revenue` | String (random token) | 60 s | Lock so that only one process refreshes the materialised view at a time |
| `rate:{customer_id}:{minute}` | String used as an integer counter (`INCR`) | 120 s (set once, when the key is created) | Number of requests of the customer in that minute (`minute = unix time // 60`); allowed while ≤ 10 |
