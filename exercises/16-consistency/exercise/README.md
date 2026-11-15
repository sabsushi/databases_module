# Exercise 16: Redis II, source of truth, rebuild and persistence

| File | What it is |
|---|---|
| `common.py` | Connections, the PostgreSQL query, and `SCAN` of the keys (shared by both scripts) |
| `rebuild.py` | 1. Rebuilds `customer:{customer_id}:categories` from PostgreSQL |
| `verify.py` | 3. Compares Redis with PostgreSQL; exits with 1 on any difference, 0 otherwise |
| `pyproject.toml` | Dependencies (`redis`, `psycopg[binary]`) |

## How to run

From the repository root:

```bash
bash scripts/create-db.sh ex16 --pagila --reset
```

The scripts use **Redis logical database 1**, so `FLUSHDB` there doesn't touch the keys of other exercises. Create `exercises/16-consistency/exercise/.env` (not committed) with:

```
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/ex16
REDIS_URL=redis://:<redis password>@localhost:6379/1
```

`common.py` refuses to run if `REDIS_URL` doesn't point to database 1. Then, from `exercises/16-consistency/exercise/`:

```bash
uv sync
docker compose exec redis redis-cli -a <redis password> -n 1 FLUSHDB
uv run --env-file .env python rebuild.py
docker compose exec redis redis-cli -a <redis password> -n 1 --scan --pattern "customer:*:categories" | wc -l
uv run --env-file .env python verify.py; echo "exit code: $?"
```

(In PowerShell, use `echo "exit code: $LASTEXITCODE"` and `| Measure-Object -Line` instead of `| wc -l`.)

## Task 1: `rebuild.py`

- **One query** to PostgreSQL: `rental` → `inventory` → `film_category` → `category`, `GROUP BY customer_id` with `array_agg(DISTINCT c.name)`. A film with several categories adds all of them, and `DISTINCT` removes repeats.
- **One pipeline** to Redis (`transaction=False`, sent in one round trip). For each customer: `DEL tmp`, `SADD tmp <categories...>`, `RENAME tmp customer:{id}:categories`.
- **Temporary key + `RENAME`:** the set is built in `tmp:<run>:customer:{id}:categories`, which no reader looks at, and then `RENAME` replaces the real key in one atomic step. A reader always sees either the complete old set or the complete new set, never a half-built one.
- Keys for customers who **shouldn't** have one (found with `SCAN` before the pipeline) are deleted in the same pipeline, so the rebuild also repairs extra keys like `customer:647:categories`.

Result: **997 sets**. Customers 647 and 978 have no rentals, so they have no key.

## Tasks 2 and 3: output

```
$ redis-cli -n 1 FLUSHDB
OK
$ uv run --env-file .env python rebuild.py
Rebuilt 997 sets from 1 query and 1 pipeline (0 stale key(s) deleted) in 0.13 s
Keys matching customer:*:categories (SCAN): 997
$ redis-cli -n 1 --scan --pattern "customer:*:categories" | wc -l
997
$ redis-cli -n 1 --scan --pattern "customer:647:*" ; redis-cli -n 1 --scan --pattern "customer:978:*"   (no output: no keys)
$ redis-cli -n 1 SMEMBERS customer:1:categories
Action Animation Children Classics Comedy Documentary Drama Family Foreign Games Horror Music New Sci-Fi Sports Travel 

$ uv run --env-file .env python verify.py; echo "exit code: $?"
Checked 997 expected sets and 997 keys in Redis: 0 difference(s)
exit code: 0

$ redis-cli -n 1 SREM customer:1:categories Action
1
$ uv run --env-file .env python verify.py; echo "exit code: $?"
DIFF customer:1:categories: size 15 instead of 16, missing ['Action']
Checked 997 expected sets and 997 keys in Redis: 1 difference(s)
exit code: 1

$ redis-cli -n 1 SADD customer:647:categories Fake
1
$ uv run --env-file .env python verify.py; echo "exit code: $?"
DIFF customer:1:categories: size 15 instead of 16, missing ['Action']
DIFF customer:647:categories: should not exist (customer has no rentals); has ['Fake']
Checked 997 expected sets and 998 keys in Redis: 2 difference(s)
exit code: 1

$ uv run --env-file .env python rebuild.py
Rebuilt 997 sets from 1 query and 1 pipeline (1 stale key(s) deleted) in 0.13 s
Keys matching customer:*:categories (SCAN): 997
$ uv run --env-file .env python verify.py; echo "exit code: $?"
Checked 997 expected sets and 997 keys in Redis: 0 difference(s)
exit code: 0
```

- `FLUSHDB` on database 1, `rebuild.py`, then counting with `SCAN` (`redis-cli --scan`, which uses `SCAN` under the hood, and `scan_iter` in Python) gives **997** keys. I used `SCAN` and not `KEYS`, because `KEYS` walks the whole keyspace in one blocking command and freezes the server for every other client while it runs. `SCAN` does it in small steps.
- `verify.py` reads every expected set in one pipeline, and compares the size and members of each with PostgreSQL. It also lists keys that exist in Redis for customers who shouldn't have one:
  - after `SREM customer:1:categories Action`: 1 difference, **exit code 1**;
  - after `SADD customer:647:categories Fake`: 2 differences (customer 1 is still wrong), **exit code 1**;
  - after `rebuild.py` again: 0 differences, **exit code 0**. The rebuild put Action back for customer 1 and deleted the key of customer 647.

## Task 4: what each key is

| Key pattern (exercise) | Class | What is lost if Redis loses it | How it comes back |
|---|---|---|---|
| `customer:{id}:viewed` (15) | **Source of truth.** It only exists in Redis; PostgreSQL doesn't record which film pages were viewed | Each customer's list of recently viewed films. Not critical (no money, no business rule), but the data is really gone | It doesn't come back. The list starts empty and fills again as the customer views films. Only Redis persistence (AOF/RDB) can protect it |
| `cache:film:{film_id}` (15) | **Derived** (a copy of a `film` row) | Nothing. The next `get_film` is a miss and reads PostgreSQL | Automatically, on the next read (cache-aside). For a while there's more load on PostgreSQL |
| `lock:refresh:monthly_revenue` (15) | **Ephemeral** (coordination state, valid for 60 s) | The lock. While it's missing, a second process could start a refresh in parallel | The next process takes it again with `SET NX`. Two `REFRESH ... CONCURRENTLY` at the same time is wasteful but still correct, because PostgreSQL serialises them |
| `rate:{customer_id}:{minute}` (15) | **Ephemeral** (a counter for the current minute) | The count of the current minute. A customer could make up to 10 extra requests in that minute | On the next request (`INCR` creates it again at 1). In the next minute it doesn't matter anyway |
| `customer:{id}:categories` (16) | **Derived** (computed from `rental` + `film_category` in PostgreSQL) | Every set. Whatever reads them gets empty sets until the rebuild | `rebuild.py`: one query + one pipeline, 0.13 s for 997 sets. `verify.py` checks the result |

## Task 5: Redis configuration

My choice for this instance, shared by everything in the table above:

```
appendonly yes
appendfsync everysec
maxmemory 512mb
maxmemory-policy volatile-lru
```

**`appendonly yes` + `appendfsync everysec`.** The only key in the table that is a **source of truth** is `customer:{id}:viewed`: if Redis loses it, nothing can rebuild it. With RDB snapshots only (the default `save 3600 1 300 100 60 10000`), a crash can lose minutes of writes, up to an hour if few keys change. With AOF and `everysec`, every write is logged and written to disk once a second, so a crash loses **at most about one second**. `always` (fsync on every write) would lose nothing but makes every write wait for the disk, and recently viewed films aren't worth that cost. AOF also helps the derived sets: after a restart, Redis reloads them from the AOF, so readers don't see empty `customer:*:categories` sets in the time before someone runs `rebuild.py`.

As the session 16 README warns, AOF must be turned on in the running server first (`CONFIG SET appendonly yes`) **before** recreating the container with `docker-compose.redis-aof.yml`. A Redis that starts with `appendonly yes` and finds no AOF starts **empty** and ignores `dump.rdb`, so every key of every project would be lost.

**`maxmemory 512mb`.** Without a limit, Redis grows until the machine runs out of RAM and the operating system kills it, losing everything. 512 MB is far more than these keys need (997 small sets, 20-item lists, short counters) and leaves room for the AOF rewrite, which forks the process.

**`maxmemory-policy volatile-lru`.** When the limit is reached, Redis evicts the least recently used keys **that have a TTL**, and never touches keys without one. With my keys:
- `customer:*:categories` have no TTL, so they're **never evicted**. Good: they're expensive for readers to lose all at once.
- `cache:film:*` has a TTL, so it gets **evicted first in practice**. Good: that's exactly what a cache is for, and it comes back on the next read.
- **The trade-off:** `customer:*:viewed`, `lock:*` and `rate:*` also have a TTL, so they can be evicted too. Losing an old viewed list is acceptable. Evicting a lock or a rate-limit counter weakens a guarantee (two refreshes at once, or a few extra requests), but it doesn't corrupt data. The other options are worse for a shared instance: `allkeys-lru` could evict the categories sets, and `noeviction` makes **every write fail** when memory is full (locks, rate limits and caches all stop working).

**Why `maxmemory-policy` forces a compromise, and when to use two instances.** The policy applies to the whole instance, not to one key, so I can't say "evict the cache freely but never evict locks or the viewed lists". The keys here need opposite things:
- the **cache** wants `allkeys-lru` and needs no persistence at all;
- the **source of truth** (`viewed`) and the **coordination keys** (`lock`, `rate`) want `noeviction` and AOF.

When the cache becomes big, or the guarantees of the locks and rate limits really matter, I would run **two Redis instances**:
1. **cache instance:** `cache:film:*` only, `maxmemory-policy allkeys-lru`, `appendonly no` (and no RDB). It can be emptied at any time without consequences, and it's fast because it never writes to disk.
2. **data instance:** `customer:*:viewed`, `customer:*:categories`, `lock:*`, `rate:*`, with `appendonly yes`, `appendfsync everysec` and `maxmemory-policy noeviction`, plus monitoring of memory use, so it's the operator, not Redis, who decides what to remove when it fills up.
