# Challenge 04: 1,000,000 valid, reproducible rentals with COPY

| File | What it is |
|---|---|
| `seed.py` | Adds 1,000,000 rows to `rental` with `COPY`; the database name is the argument |
| `pyproject.toml` | Dependencies (`faker`, `psycopg[binary]`, as in the brief) |

## How to run

From the repository root:

```bash
bash scripts/create-db.sh ch04_a --pagila --reset
bash scripts/create-db.sh ch04_b --pagila --reset
```

`seed.py` takes the user, password and host from `DATABASE_URL` in `.env`, and replaces the database name with its argument. From `exercises/04-crud/challenge/`:

```bash
uv sync
time uv run --env-file ../../../.env python seed.py ch04_a
time uv run --env-file ../../../.env python seed.py ch04_b
uv run --env-file ../../../.env python seed.py ch04_a
```

(In PowerShell: `Measure-Command { uv run --env-file ../../../.env python seed.py ch04_a }`.)

## How it meets each rule

| Rule | How |
|---|---|
| 1,000,000 rows with `COPY` | `cursor.copy("COPY rental (...) FROM STDIN")` and `write_row` for each generated row, all in one transaction |
| Same keys every run | Explicit `rental_id` from 100,001 to 1,100,000; then `setval('rental_rental_id_seq', max(rental_id))` |
| IDs exist in Pagila | `inventory_id`, `customer_id` and `staff_id` are chosen from the IDs read from `inventory`, `customer` and `staff` (sorted, so the same seed picks the same ones in every database). The foreign keys are checked by PostgreSQL during the `COPY` too |
| Dates | `rental_date` = 2022-01-01 + a random number of seconds below 2026-07-31; `return_date` is NULL for about 5% of rows, otherwise 1 hour to 10 days after `rental_date` |
| Unique `(rental_date, inventory_id, customer_id)` | The microseconds of each `rental_date` are the row number (0 to 999,999), so the 1,000,000 new `rental_date` values are all different from each other |
| Fixed random seed | `random.Random(2026)`: the same sequence of numbers on every run, so the same rows. Dates are generated in UTC and the session uses `SET TIME ZONE 'UTC'` |
| Idempotent | Before writing, it counts the rows with `rental_id` between 100,001 and 1,100,000. If there are 1,000,000, it does nothing. If a previous run left only some (it failed halfway), it deletes them and loads again, in the same transaction |

(`faker` is in `pyproject.toml` because the brief adds it, but plain `random` with a seed is enough here: every column is an ID, a date or NULL.)

## Results

```
$ time uv run --env-file ../../../.env python seed.py ch04_a
ch04_a: added 1,000,000 rows in 22.8 s
real    0m23.080s

$ time uv run --env-file ../../../.env python seed.py ch04_b
ch04_b: added 1,000,000 rows in 22.1 s
real	0m22.319s
 new_rows |             checksum             
----------+----------------------------------
  1000000 | 056394940615c0238af6d8d932ea683b
(1 row)

 new_rows |             checksum             
----------+----------------------------------
  1000000 | 056394940615c0238af6d8d932ea683b
(1 row)

$ uv run --env-file ../../../.env python seed.py ch04_a
ch04_a: the 1,000,000 rows are already there; nothing to do
 new_rows |             checksum             
----------+----------------------------------
  1000000 | 056394940615c0238af6d8d932ea683b
(1 row)

 bad_rental_date | bad_return_date | open_rentals |              min              |              max              
-----------------+-----------------+--------------+-------------------------------+-------------------------------
               0 |               0 |        50206 | 2022-01-01 00:00:11.776329+00 | 2026-07-30 23:59:15.163507+00
(1 row)

 orphan_rows 
-------------
           0
(1 row)

 last_value 
------------
    1100000
(1 row)

 total_rentals 
---------------
       1051805
(1 row)

```

### Times

| Database | Time |
|---|---|
| `ch04_a` | 22.8 s (23.1 s with `uv` start-up) |
| `ch04_b` | 22.1 s (22.3 s with `uv` start-up) |

Both are under 30 s on my machine. Most of the time is spent by PostgreSQL maintaining the 4 indexes of `rental` and checking the 3 foreign keys for every row, not by Python.

### Checksums

| Database | New rows | Checksum |
|---|---|---|
| `ch04_a` | 1,000,000 | `056394940615c0238af6d8d932ea683b` |
| `ch04_b` | 1,000,000 | `056394940615c0238af6d8d932ea683b` |

**Equal**: the two databases have identical new rows.

### Idempotency

| | Rows with `rental_id > 100000` | Checksum |
|---|---|---|
| `ch04_a` before the second run | 1,000,000 | `056394940615c0238af6d8d932ea683b` |
| `ch04_a` after the second run | 1,000,000 | `056394940615c0238af6d8d932ea683b` |

The second run printed `the 1,000,000 rows are already there; nothing to do` and changed no row.

### Validity

On `ch04_a`: 0 rows with `rental_date` outside 2022-01-01 to 2026-07-31, 0 rows with `return_date <= rental_date`, 0 rows whose `inventory_id`, `customer_id` or `staff_id` doesn't exist, 50,206 open rentals (`return_date` NULL), the sequence is at 1,100,000, and the table has 51,805 + 1,000,000 = 1,051,805 rentals.
