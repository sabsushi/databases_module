# Challenge 07: OFFSET vs keyset pagination, and VACUUM

`pagination.sql` has every statement in order. It runs on `big_rental` (2,000,000 rows), created by the exercise's `setup.sql` in its own database.

## How to run

From the repository root:

```bash
bash scripts/create-db.sh ch07 --reset
docker compose exec -T postgres psql -U postgres -d ch07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/setup.sql
docker compose exec -T postgres psql -U postgres -d ch07 -v ON_ERROR_STOP=1 < exercises/07-indexes/challenge/pagination.sql
```

`pagination.sql` uses `\gset` (a psql command), so it has to run in `psql`.

## Task 1: an index that matches the sort order

```sql
CREATE INDEX big_rental_page_idx ON big_rental (rented_at DESC, id DESC);
```

Its order is exactly `ORDER BY rented_at DESC, id DESC`, so PostgreSQL reads the index from the start and never sorts. `id` is in the index so the order is total: two rentals with the same `rented_at` always come out in the same order, and the keyset condition can point at one exact row.

## Task 2: page 5,000 with OFFSET

```sql
SELECT id, rented_at, customer_id FROM big_rental
ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20;
 Limit  (cost=5580.11..5581.23 rows=20 width=16) (actual time=131.867..131.882 rows=20 loops=1)
   Buffers: shared hit=89432 read=10945 written=2837
   ->  Index Scan using big_rental_page_idx on big_rental  (cost=0.43..111616.43 rows=2000000 width=16) (actual time=0.037..128.091 rows=100000 loops=1)
         Buffers: shared hit=89432 read=10945 written=2837
 Planning:
   Buffers: shared hit=47 read=1 dirtied=1
 Planning Time: 0.303 ms
 Execution Time: 131.907 ms
```

**131.9 ms.** The `Index Scan` returns `rows=100000`: PostgreSQL reads the first 99,980 rows in order (about 100,000 buffers) only to throw them away, and then returns 20.

## Task 3: the same page with keyset pagination

```sql
SELECT rented_at AS last_rented_at, id AS last_id
FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 99979 LIMIT 1 \gset

SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;
 Limit  (cost=0.43..1.62 rows=20 width=16) (actual time=0.019..0.036 rows=20 loops=1)
   Buffers: shared hit=22 read=1
   ->  Index Scan using big_rental_page_idx on big_rental  (cost=0.43..113238.25 rows=1897247 width=16) (actual time=0.019..0.033 rows=20 loops=1)
         Index Cond: (ROW(rented_at, id) < ROW('2026-09-21 13:05:25.100108+00'::timestamp with time zone, 13584))
         Buffers: shared hit=22 read=1
 Planning Time: 0.058 ms
 Execution Time: 0.058 ms
```

**0.058 ms**, compared with 131.9 ms for OFFSET: about 2,000 times faster. The row comparison `(rented_at, id) < (...)` becomes an `Index Cond`, so the scan **starts at the last row of page 4,999** and reads only 20 rows (23 buffers instead of about 100,000).

**Same 20 rows:** `pagination.sql` compares the two results with `EXCEPT` in both directions, and both return `(0 rows)`. The 20 rows of page 5,000:

```
   id    |           rented_at           | customer_id 
---------+-------------------------------+-------------
 1063464 | 2026-09-21 13:05:00.648908+00 |         184
 1427159 | 2026-09-21 13:04:23.842508+00 |          44
  461918 | 2026-09-21 13:04:00.514508+00 |         269
 1827010 | 2026-09-21 13:01:52.988108+00 |         464
  247357 | 2026-09-21 13:01:49.359308+00 |         166
 1329654 | 2026-09-21 13:01:14.280908+00 |         452
  326643 | 2026-09-21 12:59:41.573708+00 |         230
  193105 | 2026-09-21 12:58:58.200908+00 |         301
 1935371 | 2026-09-21 12:57:37.503308+00 |         473
 1514794 | 2026-09-21 12:56:49.637708+00 |         421
  342651 | 2026-09-21 12:55:10.536908+00 |         476
 1721447 | 2026-09-21 12:54:54.639308+00 |           6
 1641744 | 2026-09-21 12:54:07.896908+00 |         340
  973890 | 2026-09-21 12:53:56.319308+00 |         578
 1678817 | 2026-09-21 12:53:27.980108+00 |         286
 1184506 | 2026-09-21 12:52:50.655308+00 |         317
  313311 | 2026-09-21 12:52:15.922508+00 |          31
  915109 | 2026-09-21 12:51:59.247308+00 |         428
 1726621 | 2026-09-21 12:50:30.341708+00 |         386
 1845692 | 2026-09-21 12:50:04.248908+00 |         471
(20 rows)
```

**The keyset query doesn't depend on the page number.** The same query for page 2 and for page 50,000 (the last one), compared with OFFSET for page 50,000:

| Query | Rows read by the scan | Buffers | Time |
|---|---|---|---|
| Keyset, page 2 | 20 | 23 | 0.026 ms |
| Keyset, page 5,000 | 20 | 23 | 0.058 ms |
| Keyset, page 50,000 | 20 | 23 | 0.052 ms |
| OFFSET, page 5,000 | 100,000 | 100,377 | 131.9 ms |
| OFFSET, page 50,000 | 1,000,000 | 1,003,750 | 641.1 ms |

Keyset, page 50,000:

```
 Limit  (cost=0.43..2.11 rows=20 width=16) (actual time=0.020..0.038 rows=20 loops=1)
   Buffers: shared hit=22 read=1
   ->  Index Scan using big_rental_page_idx on big_rental  (cost=0.43..83421.21 rows=990445 width=16) (actual time=0.019..0.036 rows=20 loops=1)
         Index Cond: (ROW(rented_at, id) < ROW('2025-05-16 13:19:55.666508+00'::timestamp with time zone, 1695510))
         Buffers: shared hit=22 read=1
 Planning Time: 0.089 ms
 Execution Time: 0.052 ms
```

OFFSET, page 50,000:

```
 Limit  (cost=55807.31..55808.43 rows=20 width=16) (actual time=641.060..641.073 rows=20 loops=1)
   Buffers: shared hit=1000302 read=3448 written=5
   ->  Index Scan using big_rental_page_idx on big_rental  (cost=0.43..111616.43 rows=2000000 width=16) (actual time=0.007..602.573 rows=1000000 loops=1)
         Buffers: shared hit=1000302 read=3448 written=5
 Planning Time: 0.020 ms
 Execution Time: 641.084 ms
```

### Why OFFSET gets slower as the page number grows

`OFFSET n` doesn't jump to row n. An index (a B-tree) can find a **value** quickly, but not "the n-th entry", because the tree doesn't store how many entries are before each position. So PostgreSQL produces the rows in order and **discards the first n one by one**. Page p costs about `20 × p` rows read: page 5,000 reads 100,000 rows and page 50,000 reads 1,000,000, and the time grows with them (132 ms → 641 ms). Keyset pagination remembers *where* the last page ended (`rented_at`, `id`), which is a value the index can search for directly. Every page costs the same: one index descent plus 20 rows.

## Task 4: `INCLUDE (customer_id)` → Index Only Scan

```sql
DROP INDEX big_rental_page_idx;
CREATE INDEX big_rental_page_idx ON big_rental (rented_at DESC, id DESC) INCLUDE (customer_id);
VACUUM ANALYZE big_rental;
 Limit  (cost=0.43..1.09 rows=20 width=16) (actual time=0.070..0.074 rows=20 loops=1)
   Buffers: shared hit=1 read=3
   ->  Index Only Scan using big_rental_page_idx on big_rental  (cost=0.43..62499.11 rows=1900496 width=16) (actual time=0.068..0.071 rows=20 loops=1)
         Index Cond: (ROW(rented_at, id) < ROW('2026-09-21 13:05:25.100108+00'::timestamp with time zone, 13584))
         Heap Fetches: 0
         Buffers: shared hit=1 read=3
 Planning:
   Buffers: shared hit=12
 Planning Time: 0.131 ms
 Execution Time: 0.090 ms
```

The query needs `id`, `rented_at` and `customer_id`. With `customer_id` stored in the index leaf entries (`INCLUDE`: stored but not part of the sort key), every column is in the index, so the plan is an **`Index Only Scan`**, and **`Heap Fetches: 0`** means it didn't read the table at all.

## Task 5: UPDATE, then VACUUM

```sql
UPDATE big_rental SET customer_id = customer_id WHERE id % 50 = 0;
```

Keyset query right after the update:

```
 Limit  (cost=0.43..1.09 rows=20 width=16) (actual time=0.040..0.197 rows=20 loops=1)
   Buffers: shared hit=18 read=6 dirtied=6 written=6
   ->  Index Only Scan using big_rental_page_idx on big_rental  (cost=0.43..64177.04 rows=1938321 width=16) (actual time=0.039..0.194 rows=20 loops=1)
         Index Cond: (ROW(rented_at, id) < ROW('2026-09-21 13:05:25.100108+00'::timestamp with time zone, 13584))
         Heap Fetches: 20
         Buffers: shared hit=18 read=6 dirtied=6 written=6
 Planning Time: 0.113 ms
 Execution Time: 0.216 ms
```

**`Heap Fetches: 20`.** Still an Index Only Scan, but it had to visit the table for all 20 rows (0.216 ms, and the buffers went from 4 to 24).

After `VACUUM big_rental;`:

```
 Limit  (cost=0.43..1.09 rows=20 width=16) (actual time=0.020..0.023 rows=20 loops=1)
   Buffers: shared hit=4
   ->  Index Only Scan using big_rental_page_idx on big_rental  (cost=0.43..62499.11 rows=1900496 width=16) (actual time=0.019..0.020 rows=20 loops=1)
         Index Cond: (ROW(rented_at, id) < ROW('2026-09-21 13:05:25.100108+00'::timestamp with time zone, 13584))
         Heap Fetches: 0
         Buffers: shared hit=4
 Planning:
   Buffers: shared hit=1 read=3 written=3
 Planning Time: 0.126 ms
 Execution Time: 0.039 ms
```

**`Heap Fetches: 0`** again (0.039 ms, 4 buffers).

| Moment | Plan | Heap Fetches | Time |
|---|---|---|---|
| After `CREATE INDEX ... INCLUDE` + `VACUUM` | Index Only Scan | 0 | 0.090 ms |
| After the `UPDATE` | Index Only Scan | **20** | 0.216 ms |
| After `VACUUM` | Index Only Scan | **0** | 0.039 ms |

### What VACUUM changes in the visibility map

An index entry doesn't say whether the row it points to is **visible** to the current transaction. Under MVCC, the row might have been deleted, or updated into a new version, by a transaction that this query can't see yet, and only the row in the table (the heap) has that information. To skip the heap, PostgreSQL uses the **visibility map**: one bit per table page (8 kB) that says "**all-visible**: every row on this page is visible to every transaction". For an index entry on an all-visible page, the index only scan trusts the index and doesn't read the table. For any other page, it has to fetch the row from the heap to check its visibility, and **each of those visits is a heap fetch**.

- `UPDATE` never changes a row in place: it writes a **new version** of the row and marks the old one as dead. The `UPDATE` touched 1 row in 50, which is about 1 row on almost every page of the table (each page holds about 150 rows). That **cleared the all-visible bit** on almost every page, and on the pages the new versions were written to. So all 20 rows of the page needed a heap fetch.
- `VACUUM` removes the dead row versions (once no transaction can still see them), and **sets the all-visible bit again** for every page whose rows are now all visible to everyone. After that, the index only scan can trust the index again: `Heap Fetches: 0`.

That's why an index only scan is only as good as the table's last `VACUUM`. On a table that changes often, autovacuum has to run often enough to keep the visibility map up to date.

> The timestamps come from `setup.sql`, which uses `now()`, so the exact rows and times are different on each machine and on each run. The plans, row counts and Heap Fetches are the same.
