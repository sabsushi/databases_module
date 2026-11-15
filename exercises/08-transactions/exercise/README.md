# Exercise 8: Transactions and concurrency

Files:

- `lost_update.md`: tasks 1 and 2 (the lost update and its two fixes)
- `deadlock.md`: task 3
- `write_skew.py`, `pyproject.toml`: task 4

## Setup

```bash
bash scripts/create-db.sh ex08 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex08 -v ON_ERROR_STOP=1 <<'EOF'
ALTER TABLE customer ADD COLUMN balance numeric(10,2) NOT NULL DEFAULT 100 CHECK (balance >= 0);

INSERT INTO staff (first_name, last_name, address_id, store_id, username)
SELECT 'Temp', 'Staff ' || g, 1, 1, 'temp' || g
FROM generate_series(1, 14) AS g;
EOF
```

In `.env`, set `DATABASE_URL` to the `ex08` database:

```
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/ex08
```

## Task 4: write skew

From `exercises/08-transactions/exercise/`:

```bash
uv sync
uv run --env-file ../../../.env python write_skew.py read-committed
docker compose exec -T postgres psql -U postgres -d ex08 -c "UPDATE staff SET active = true WHERE store_id = 1;"
uv run --env-file ../../../.env python write_skew.py serializable
```

`write_skew.py` starts one thread per active staff member of store 1 (20), each with its own connection. Each thread runs one transaction: count the active staff of store 1, wait at `threading.Barrier(20)` so that every thread has read before any thread writes, and if the count was above 1, set its own member to `active = false`. Under `SERIALIZABLE`, a transaction that fails with SQLSTATE `40001` (`psycopg.errors.SerializationFailure`) is retried from the start, without the barrier.

### Run 1: READ COMMITTED

```
Isolation level: read-committed
Active staff in store 1 before: 20
Threads that deactivated their member: 20
Serialisation failures retried: 0
Active staff in store 1 after: 0
```

Reset:

```
UPDATE 20
```

### Run 2: SERIALIZABLE

```
Isolation level: serializable
Active staff in store 1 before: 20
Threads that deactivated their member: 19
Serialisation failures retried: 128
Active staff in store 1 after: 1
```

(I ran it a second time after another reset and got 1 active member again, with 122 retries. The number of retries changes from run to run, but the result is always 1.)

### Why READ COMMITTED breaks the rule and SERIALIZABLE does not

Under **READ COMMITTED**, each thread counts the active staff and sees 20, because nobody has written yet (the barrier makes sure of that). Each one decides "20 > 1, so I can leave" and updates **its own row**. The 20 updates touch 20 different rows, so they never wait for each other and there's no conflict for the row locks to catch. Every transaction is correct on its own, but together they break the rule, leaving **0** active staff. This is called **write skew**: two or more transactions read the same data, make a decision from it, and write *different* rows, so each one changes the premise the others relied on.

Under **SERIALIZABLE**, PostgreSQL uses Serializable Snapshot Isolation (SSI). It tracks which rows each transaction *read* (the count over the staff of store 1) as well as which rows it wrote. When a transaction writes a row that another concurrent transaction has read, PostgreSQL records a read-write dependency. If those dependencies form a cycle, the result couldn't be produced by running the transactions one after the other, so PostgreSQL aborts one of them with `40001 could not serialize access due to read/write dependencies among transactions`. The retry starts a fresh transaction, which sees the committed deactivations and counts again. In the end, only orders that give the same result as a serial execution survive. In any serial order, the last thread counts 1 and doesn't deactivate itself, so exactly **1** member stays active.

Other ways to protect this rule under `READ COMMITTED` would be to lock the store row first (`SELECT ... FROM store WHERE store_id = 1 FOR UPDATE`) so the transactions run one at a time, or to enforce the rule with a trigger. `SERIALIZABLE` with retries is the general solution because it doesn't need to know in advance which rows to lock.
