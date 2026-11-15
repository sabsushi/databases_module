# Exercise 12: ORM II, migrations, transactions and API

| Path | What it is |
|---|---|
| `app/models.py` | SQLAlchemy models for `customer`, `staff`, `film`, `inventory`, `rental` |
| `app/db.py` | Engine and session factory; reads `DATABASE_URL`; `echo=True` (set `SQL_ECHO=0` to turn it off) |
| `app/main.py` | The API: `POST /rentals`, `POST /rentals/{rental_id}/return`, `GET /rentals/overdue` |
| `alembic.ini`, `migrations/env.py` | Alembic configuration; the URL comes from `DATABASE_URL`, and `include_object` filters what autogenerate sees |
| `migrations/versions/0001_baseline.py` | Empty baseline |
| `migrations/versions/0002_loyalty_points.py` | `customer.loyalty_points` |
| `migrations/versions/0003_one_open_rental_per_copy.py` | Data fix + partial unique index `rental_one_open_per_copy` |
| `concurrency_test.py` | 5 simultaneous `POST /rentals` |
| `pyproject.toml` | Dependencies |

## How to run

From the repository root:

```bash
bash scripts/create-db.sh ex12 --pagila --reset
```

In `.env`, set `DATABASE_URL=postgresql://postgres:<password>@localhost:5432/ex12`. Then, from `exercises/12-api/exercise/`:

```bash
uv sync

uv run --env-file ../../../.env alembic stamp 0001_baseline
uv run --env-file ../../../.env alembic upgrade head
uv run --env-file ../../../.env alembic downgrade base
uv run --env-file ../../../.env alembic upgrade head
uv run --env-file ../../../.env alembic check

uv run --env-file ../../../.env uvicorn app.main:app --port 8000

uv run python concurrency_test.py
```

## Task 1: baseline and `include_object`

`0001_baseline` has empty `upgrade()` and `downgrade()`. When it was the only migration, `alembic stamp head` wrote `0001_baseline` into `alembic_version` without running anything, because the Pagila tables already exist.

`include_object` in `migrations/env.py` makes `--autogenerate` (and `alembic check`) ignore:
- tables in the database that aren't in the models;
- columns of mapped tables that aren't in the models (`customer.uuid`, `film.fulltext`, ...);
- Pagila's own indexes and unique constraints;
- foreign keys. Pagila already has them all (with `ON UPDATE CASCADE ON DELETE RESTRICT`), and the models only declare `ForeignKey()` so the ORM knows how to join.

With it, `alembic check` after the migrations says `No new upgrade operations detected.`

**Without the baseline**, the first `--autogenerate` would compare the models with an empty migration history and generate `CREATE TABLE` for `customer`, `staff`, `film`, `inventory` and `rental`. `alembic upgrade head` would then fail, because those tables already exist. If someone "fixed" it by dropping the tables first, all the data would be lost.

**Without `include_object`**, autogenerate compares `Base.metadata` (5 tables, only some columns) with the whole Pagila database and treats everything it doesn't know as something to remove. I measured it on `ex12` with `alembic.autogenerate.compare_metadata`:

| Operation it would generate | Count | Examples |
|---|---|---|
| `drop_table` | 65 | `actor`, `country`, `payment_p2022_01` ... every payment partition |
| `drop_column` | 22 | `customer.address_id`, `customer.uuid`, `film.description`, `film.special_features` |
| `drop_index` | 91 | Pagila's indexes |
| `drop_constraint` (FK) | 11 | |

**Why that's dangerous:** a generated migration looks like any other file. If someone runs `alembic upgrade head` without reading it carefully, it drops 65 tables (with all payments, actors, addresses...) and 22 columns, and the data can't be recovered without a backup. Autogenerate is only a draft. Every generated migration has to be reviewed, and the filter has to make sure it only sees what this project owns.

## Task 2: `0002_loyalty_points`

Three steps, because you can't add a `NOT NULL` column without a value to a table that already has rows:

1. `op.add_column("customer", sa.Column("loyalty_points", sa.Integer(), nullable=True, server_default=sa.text("0")))`
2. `UPDATE customer c SET loyalty_points = (SELECT count(*) FROM rental r WHERE r.customer_id = c.customer_id)`
3. `op.alter_column("customer", "loyalty_points", nullable=False)`

`server_default` 0 is for new customers. `downgrade()` drops the column. Result: customer 1 has **66** points.

## Task 3: `0003_one_open_rental_per_copy`

Before the migration, three copies have two open rentals each:

```
 inventory_id | count
--------------+-------
         1358 |     2
         1435 |     2
         2408 |     2
```

`upgrade()` uses window functions to find, for each copy, its open rentals ordered from newest to oldest. Every open rental except the newest gets `return_date` = the `rental_date` of the newest one (the copy must have come back before it was rented again). Then it creates `CREATE UNIQUE INDEX rental_one_open_per_copy ON rental (inventory_id) WHERE return_date IS NULL`. After the upgrade, the same query returns 0 rows. `downgrade()` drops the index only.

**Why the data fix isn't undone:** the index can't exist while the bad data is there, but the reverse isn't true. The data was *wrong* before (a copy can't be in two places at once), and putting the two open rentals back would put back an impossible state for no reason. Undoing it would also need to remember exactly which rentals were closed and with what value, which the migration doesn't store. Since then, the API may also have created new rentals for those copies, and reopening old rentals could break the index or the data. Dropping the index on downgrade is enough to let the schema go back to `0002`. The corrected data is still valid under the old schema.

## Task 4: upgrade, downgrade, upgrade

Output of the three commands, each followed by `\d customer` and `\d rental`. To keep this short, the foreign keys, "Referenced by" and triggers sections are left out, because no migration changes them.

```
$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade 0001_baseline -> 0002_loyalty_points
INFO  [alembic.runtime.migration] Running upgrade 0002_loyalty_points -> 0003_one_open_rental_per_copy
                                             Table "public.customer"
     Column     |           Type           | Collation | Nullable |                    Default
----------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id    | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id       | integer                  |           | not null |
 first_name     | text                     |           | not null |
 last_name      | text                     |           | not null |
 email          | text                     |           |          |
 address_id     | integer                  |           | not null |
 activebool     | boolean                  |           | not null | true
 create_date    | date                     |           | not null | CURRENT_DATE
 last_update    | timestamp with time zone |           |          | now()
 active         | integer                  |           |          |
 uuid           | uuid                     |           | not null | uuidv7()
 loyalty_points | integer                  |           | not null | 0
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)

                                           Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null |
 inventory_id | integer                  |           | not null |
 customer_id  | integer                  |           | not null |
 return_date  | timestamp with time zone |           |          |
 staff_id     | integer                  |           | not null |
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_one_open_per_copy" UNIQUE, btree (inventory_id) WHERE return_date IS NULL
    "rental_uuid_key" UNIQUE, btree (uuid)

 customer_id | loyalty_points
-------------+----------------
           1 |             66
(1 row)

 inventory_id | count
--------------+-------
(0 rows)

$ alembic downgrade base
INFO  [alembic.runtime.migration] Running downgrade 0003_one_open_rental_per_copy -> 0002_loyalty_points
INFO  [alembic.runtime.migration] Running downgrade 0002_loyalty_points -> 0001_baseline
INFO  [alembic.runtime.migration] Running downgrade 0001_baseline -> 
                                            Table "public.customer"
   Column    |           Type           | Collation | Nullable |                    Default
-------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id    | integer                  |           | not null |
 first_name  | text                     |           | not null |
 last_name   | text                     |           | not null |
 email       | text                     |           |          |
 address_id  | integer                  |           | not null |
 activebool  | boolean                  |           | not null | true
 create_date | date                     |           | not null | CURRENT_DATE
 last_update | timestamp with time zone |           |          | now()
 active      | integer                  |           |          |
 uuid        | uuid                     |           | not null | uuidv7()
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)

                                           Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null |
 inventory_id | integer                  |           | not null |
 customer_id  | integer                  |           | not null |
 return_date  | timestamp with time zone |           |          |
 staff_id     | integer                  |           | not null |
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_uuid_key" UNIQUE, btree (uuid)

$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_baseline
INFO  [alembic.runtime.migration] Running upgrade 0001_baseline -> 0002_loyalty_points
INFO  [alembic.runtime.migration] Running upgrade 0002_loyalty_points -> 0003_one_open_rental_per_copy
                                             Table "public.customer"
     Column     |           Type           | Collation | Nullable |                    Default
----------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id    | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id       | integer                  |           | not null |
 first_name     | text                     |           | not null |
 last_name      | text                     |           | not null |
 email          | text                     |           |          |
 address_id     | integer                  |           | not null |
 activebool     | boolean                  |           | not null | true
 create_date    | date                     |           | not null | CURRENT_DATE
 last_update    | timestamp with time zone |           |          | now()
 active         | integer                  |           |          |
 uuid           | uuid                     |           | not null | uuidv7()
 loyalty_points | integer                  |           | not null | 0
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)

                                           Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null |
 inventory_id | integer                  |           | not null |
 customer_id  | integer                  |           | not null |
 return_date  | timestamp with time zone |           |          |
 staff_id     | integer                  |           | not null |
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_one_open_per_copy" UNIQUE, btree (inventory_id) WHERE return_date IS NULL
    "rental_uuid_key" UNIQUE, btree (uuid)
```

`loyalty_points` and `rental_one_open_per_copy` are there after each `upgrade head` and gone after `downgrade base`. The downgrade only removes the column and the index: the 3 rentals closed by `0003` stay closed (see task 3).

## Task 5: the API

### `POST /rentals`

One transaction (`with session.begin()`):
1. `404` if the customer or the film doesn't exist.
2. Find a copy of the film in that store **with no open rental**, `ORDER BY inventory_id LIMIT 1`, with `with_for_update(skip_locked=True)`. That's `SELECT ... FOR UPDATE SKIP LOCKED`: the copy is locked, and a copy already locked by another request is **skipped** instead of waited for. Two concurrent requests never pick the same copy, and nobody blocks.
3. `409` if no copy is left.
4. Insert the rental with `rental_date = now()`, then `flush()` so the `INSERT` runs inside the transaction.

If the insert violates `rental_one_open_per_copy` (`IntegrityError`, another request rented the copy between our read and our insert), the transaction is rolled back and **retried from the start**, at most 3 times, before returning `409`. `SKIP LOCKED` makes this rare, but the unique index is the guarantee that a copy can never have two open rentals, whatever the application does.

### `POST /rentals/{rental_id}/return`

Loads the rental `FOR UPDATE` (so two simultaneous returns can't both succeed), returns `404` if it doesn't exist, `409` if `return_date` is already set, and otherwise sets `return_date = now()`.

### `GET /rentals/overdue?as_of=2026-07-31`

Open rentals whose due date (`rental_date + make_interval(days => film.rental_duration)`) is before `as_of`, ordered by `rental_date`. `rental`, `customer`, `inventory` and `film` are joined in **one** query, and `contains_eager` tells the ORM to fill `rental.customer` and `rental.inventory.film` from the joined rows. Reading them to build the response runs no extra query.

**Number of SQL statements (from the `echo=True` log): 1 `SELECT`** (between `BEGIN (implicit)` and `ROLLBACK`), whatever the number of items:

```
BEGIN (implicit)
SELECT customer.customer_id, customer.store_id, customer.first_name, customer.last_name, ..., film.film_id, film.title, film.rental_duration, ..., inventory.inventory_id, ..., rental.rental_id, rental.rental_date, ..., rental.rental_date + make_interval(%(make_interval_1)s::INTEGER, %(make_interval_2)s::INTEGER, %(make_interval_3)s::INTEGER, film.rental_duration) AS due_date
FROM rental JOIN customer ON customer.customer_id = rental.customer_id JOIN inventory ON inventory.inventory_id = rental.inventory_id JOIN film ON film.film_id = inventory.film_id
WHERE rental.return_date IS NULL AND rental.rental_date + make_interval(...) < %(param_1)s::TIMESTAMP WITH TIME ZONE ORDER BY rental.rental_date, rental.rental_id
[generated in 0.00014s] {'make_interval_1': 0, 'make_interval_2': 0, 'make_interval_3': 0, 'param_1': datetime.datetime(2026, 7, 31, 0, 0, tzinfo=datetime.timezone.utc)}
ROLLBACK
```

Result: **229 items**. The first one:

```json
{
  "rental_id": 11496,
  "rental_date": "2022-02-14T15:16:03+00:00",
  "due_date": "2022-02-19T15:16:03+00:00",
  "customer": {"customer_id": 155, "first_name": "GAIL", "last_name": "KNIGHT"},
  "film": {"film_id": 445, "title": "HYDE DOCTOR"}
}
```

(Before migration `0003` this query returned 232. The 3 rentals closed by the data fix are no longer open.)

### Status codes

```
$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/rentals -H 'content-type: application/json' -d '{"customer_id": 9999, "film_id": 7, "store_id": 1, "staff_id": 6}'
{"detail":"customer 9999 not found"}
404

$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/rentals -H 'content-type: application/json' -d '{"customer_id": 1, "film_id": 9999, "store_id": 1, "staff_id": 6}'
{"detail":"film 9999 not found"}
404

$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/rentals -H 'content-type: application/json' -d '{"customer_id": 6, "film_id": 7, "store_id": 1, "staff_id": 6}'
{"detail":"no copy of this film is available in this store"}
409

$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/rentals/87560/return 
{"rental_id":87560,"return_date":"2026-11-15T10:16:47.617973+00:00"}
200

$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/rentals/87560/return 
{"detail":"rental 87560 was already returned"}
409

$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/rentals/99999999/return 
{"detail":"rental 99999999 not found"}
404

```

(These ran after the concurrency test, so both copies of film 7 in store 1 were already rented and the third request got `409`.)

## Task 6: concurrency test

`concurrency_test.py` starts 5 threads that wait at a `threading.Barrier(5)` and then each send `POST /rentals` for film 7 in store 1 (customers 1 to 5, staff 6) at the same moment.

```
customer 1: 201 {'rental_id': 87560, 'inventory_id': 32}
customer 2: 409 {'detail': 'no copy of this film is available in this store'}
customer 3: 201 {'rental_id': 87561, 'inventory_id': 33}
customer 4: 409 {'detail': 'no copy of this film is available in this store'}
customer 5: 409 {'detail': 'no copy of this film is available in this store'}

201: 2, 409: 3, different inventory_id: [32, 33]
OK
```

I ran it 3 more times, each on a fresh copy (`create-db.sh ex12 --pagila --reset`, `stamp`, `upgrade head`, start the API), and got the same result every time:

```
== run 1
201: 2, 409: 3, different inventory_id: [32, 33]
OK
== run 2
201: 2, 409: 3, different inventory_id: [32, 33]
OK
== run 3
201: 2, 409: 3, different inventory_id: [32, 33]
OK
```

Which customers get the two copies changes from run to run, but there are always exactly two `201` with the two different copies (32 and 33), and three `409`.
