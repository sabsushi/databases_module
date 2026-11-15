# Exercise 7: Indexes and optimisation

Files:

- `setup.sql` creates `big_rental` (2,000,000 rows, no indexes). I added `DROP TABLE IF EXISTS` at the top so it can be run again to recreate the table.
- `indexes.sql` has every index I kept.

## How to run

```bash
bash scripts/create-db.sh ex07 --reset
docker compose exec -T postgres psql -U postgres -d ex07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/setup.sql
docker compose exec -T postgres psql -U postgres -d ex07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/indexes.sql
```

Every time below is the median of 3 runs of `EXPLAIN (ANALYZE, BUFFERS)`.

## Summary

| Query | Plan before | Index | Plan after | Before | After |
|---|---|---|---|---|---|
| Q1 | Parallel Seq Scan | `big_rental_open_customer_idx` (partial) | Index Only Scan | 54.6 ms | 0.07 ms |
| Q2 | Parallel Seq Scan + Sort | `big_rental_rented_at_idx` | Bitmap Heap Scan | 104.3 ms | 3.7 ms |
| Q3 | Parallel Seq Scan | none (as written) | Parallel Seq Scan | 119.3 ms | 120.2 ms |
| Q3 rewritten | Parallel Seq Scan | `big_rental_rented_at_idx` | Bitmap Heap Scan | 78.4 ms | 3.8 ms |
| Q4 | Parallel Seq Scan | none | Parallel Seq Scan | 185.3 ms | 203.0 ms |
| Q5 | Parallel Seq Scan + Sort | `big_rental_customer_rented_at_idx` | Bitmap Heap Scan | 73.8 ms | 1.3 ms |

## Q1

```sql
SELECT count(*) FROM big_rental WHERE customer_id = 42 AND returned_at IS NULL;
```

**What it does:** counts the rentals of customer 42 that have not been returned yet.

**Before:**
```
Finalize Aggregate (actual time=52.814..54.564 rows=1 loops=1)
  Buffers: shared hit=2272 read=10464
  ->  Gather
        ->  Partial Aggregate
              ->  Parallel Seq Scan on big_rental
                    Filter: ((returned_at IS NULL) AND (customer_id = 42))
```

**Index:**
```sql
CREATE INDEX big_rental_open_customer_idx ON big_rental (customer_id) WHERE returned_at IS NULL;
```

**After:**
```
Aggregate (actual time=0.036..0.037 rows=1 loops=1)
  Buffers: shared hit=3
  ->  Index Only Scan using big_rental_open_customer_idx on big_rental (rows=93)
        Index Cond: (customer_id = 42)
        Heap Fetches: 0
```

**Median:** 54.6 ms → 0.07 ms.

**Why:** a partial index only holds the 3% of rows where `returned_at IS NULL`, so it's small. The query only needs `count(*)`, so PostgreSQL answers from the index without reading the table (`Heap Fetches: 0`). It reads 3 pages instead of about 12,700.

## Q2

```sql
SELECT * FROM big_rental WHERE rented_at >= now() - interval '1 day' ORDER BY rented_at;
```

**What it does:** returns every rental made in the last 24 hours, oldest first.

**Before:**
```
Gather Merge (actual time=101.937..104.165 rows=1880 loops=1)
  Buffers: shared hit=2674 read=10176
  ->  Sort
        Sort Key: rented_at
        ->  Parallel Seq Scan on big_rental
              Filter: (rented_at >= (now() - '1 day'::interval))
```

**Index:**
```sql
CREATE INDEX big_rental_rented_at_idx ON big_rental (rented_at);
```

**After:**
```
Sort (actual time=3.462..3.570 rows=1880 loops=1)
  Sort Key: rented_at
  Buffers: shared hit=1752
  ->  Bitmap Heap Scan on big_rental
        Recheck Cond: (rented_at >= (now() - '1 day'::interval))
        ->  Bitmap Index Scan on big_rental_rented_at_idx
```

**Median:** 104.3 ms → 3.7 ms.

**Why:** the query only wants about 0.1% of the rows (1,880 out of 2 million). The index finds them directly instead of scanning the whole table. PostgreSQL picks a Bitmap Heap Scan because those rows are spread over about 1,750 different pages.

## Q3

```sql
SELECT * FROM big_rental WHERE rented_at::date = current_date - 10;
```

**What it does:** returns every rental made exactly 10 days ago, on that calendar day.

**Before:**
```
Gather (actual time=0.492..146.053 rows=1883 loops=1)
  ->  Parallel Seq Scan on big_rental
        Filter: ((rented_at)::date = (CURRENT_DATE - 10))
        Rows Removed by Filter: 666039
```

**Index:** none works for the query as written.

**After** (with `big_rental_rented_at_idx` present):
```
Gather (actual time=0.319..120.120 rows=1883 loops=1)
  ->  Parallel Seq Scan on big_rental
        Filter: ((rented_at)::date = (CURRENT_DATE - 10))
        Rows Removed by Filter: 666039
```

**Median:** 119.3 ms → 120.2 ms (no change).

**Why the index doesn't help:** the condition applies a cast to the column (`rented_at::date`). The index on `rented_at` stores timestamps, not dates, so PostgreSQL can't use it, and it has to compute the cast for all 2 million rows. An expression index on `rented_at::date` isn't allowed either, because `rented_at` is `timestamptz` and converting it to a date depends on the session's time zone:

```
CREATE INDEX ON big_rental ((rented_at::date));
ERROR:  functions in index expression must be marked IMMUTABLE
```

**Rewritten query:** compare the column itself against a range, so the existing index on `rented_at` can be used:

```sql
SELECT * FROM big_rental
WHERE rented_at >= current_date - 10 AND rented_at < current_date - 9;
Bitmap Heap Scan on big_rental (actual time=0.417..3.094 rows=1883 loops=1)
  Recheck Cond: ((rented_at >= (CURRENT_DATE - 10)) AND (rented_at < (CURRENT_DATE - 9)))
  Buffers: shared hit=1762
  ->  Bitmap Index Scan on big_rental_rented_at_idx
        Index Cond: ((rented_at >= (CURRENT_DATE - 10)) AND (rented_at < (CURRENT_DATE - 9)))
```

**Median of the rewritten query:** 78.4 ms (no index) → 3.8 ms (with index). It returns the same 1,883 rows.

## Q4

```sql
SELECT customer_id, count(*) FROM big_rental WHERE returned_at IS NOT NULL GROUP BY customer_id;
```

**What it does:** for each customer, counts how many of their rentals have been returned.

**Before:**
```
Finalize GroupAggregate (actual time=184.049..185.130 rows=600 loops=1)
  Group Key: customer_id
  Buffers: shared hit=3438 read=9312
  ->  Gather Merge
        ->  Sort
              ->  Partial HashAggregate
                    ->  Parallel Seq Scan on big_rental
                          Filter: (returned_at IS NOT NULL)
```

**Index:** none.

**After:** same plan, 203.0 ms (the difference from 185.3 ms is noise).

**Why no index helps:** the filter keeps about 97% of the table (1,940,000 of 2,000,000 rows), and the query reads all of them to count per customer. When you read almost every row, a sequential scan is the cheapest plan. I tested it with the partial index `(customer_id) WHERE returned_at IS NOT NULL` (13 MB):
- by default, the planner ignored it and kept the `Parallel Seq Scan` (204.7 ms);
- forcing it with `SET enable_seqscan = off` gave a `Parallel Index Only Scan` at around 128 ms, but the planner would never choose that plan on its own.

An index that's 13 MB, slows down every insert and is never picked by the planner isn't worth keeping. If this report were run very often, the better fix would be a materialised view (session 06) or a counter per customer, not an index.

## Q5

```sql
SELECT * FROM big_rental
WHERE customer_id IN (7, 42, 99) AND rented_at >= now() - interval '30 days'
ORDER BY rented_at DESC;
```

**What it does:** the rentals of customers 7, 42 and 99 in the last 30 days, most recent first.

**Before:**
```
Gather Merge (actual time=75.121..77.587 rows=295 loops=1)
  Buffers: shared hit=3826 read=9024
  ->  Sort
        Sort Key: rented_at DESC
        ->  Parallel Seq Scan on big_rental
              Filter: ((customer_id = ANY ('{7,42,99}'::integer[])) AND (rented_at >= (now() - '30 days'::interval)))
```

**Index:**
```sql
CREATE INDEX big_rental_customer_rented_at_idx ON big_rental (customer_id, rented_at);
```

**After:**
```
Sort (actual time=1.190..1.211 rows=295 loops=1)
  Sort Key: rented_at DESC
  Buffers: shared hit=306
  ->  Bitmap Heap Scan on big_rental
        Recheck Cond: ((customer_id = ANY ('{7,42,99}'::integer[])) AND (rented_at >= (now() - '30 days'::interval)))
        ->  Bitmap Index Scan on big_rental_customer_rented_at_idx
```

**Median:** 73.8 ms → 1.3 ms.

**Why:** the column tested with equality (`customer_id`) goes first and the range column (`rented_at`) second. That way the index jumps to each of the 3 customers and reads only their last 30 days. With the columns the other way round, it would have to read 30 days of rentals for every customer and then filter. Sorting 295 rows at the end costs almost nothing.

## Write cost

`INSERT INTO big_rental SELECT g, 1, now(), NULL FROM generate_series(2000001, 2100000) g;` (100,000 rows), with the table recreated by `setup.sql` before each run:

| Table | Time |
|---|---|
| No indexes | 66.3 ms |
| With the 3 indexes of `indexes.sql` | 304.5 ms |

With the indexes, the insert is about 4.6 times slower. Every new row also has to be added to each of the 3 B-trees, in the right position. All the new rows have `returned_at = NULL`, so they also go into the partial index. This is the price of the faster reads, and it's why I didn't keep an index for Q4: it would add write cost on every insert for a plan the planner doesn't choose.

> Times were measured on my machine; the exact numbers will vary, but the order of magnitude and the plan nodes are the same.
