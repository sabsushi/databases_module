# Lost update

Database `ex08`, prepared with the setup of the brief (`customer.balance` starts at 100). Two `psql` sessions:

```bash
docker compose exec postgres psql -U postgres -d ex08
```

## 1. Reproducing the lost update

Each session reads the balance, subtracts 10 in the application, and writes the value it computed.

| Step | Session A | Session B |
|---|---|---|
| 1 | `BEGIN;` | |
| 2 | | `BEGIN;` |
| 3 | `SELECT balance FROM customer WHERE customer_id = 1;` → `100.00` | |
| 4 | | `SELECT balance FROM customer WHERE customer_id = 1;` → `100.00` |
| 5 | `UPDATE customer SET balance = 90 WHERE customer_id = 1;` → `UPDATE 1` | |
| 6 | | `UPDATE customer SET balance = 90 WHERE customer_id = 1;` → **waits** (A holds the row lock) |
| 7 | `COMMIT;` | |
| 8 | | the `UPDATE` continues → `UPDATE 1` |
| 9 | | `COMMIT;` |
| 10 | `SELECT balance FROM customer WHERE customer_id = 1;` → **`90.00`** | |

Two withdrawals of 10 were made, but the final balance is **90 instead of 80**. B read 100 before A committed, so B wrote `100 - 10 = 90` over A's 90. A's withdrawal is lost. The row lock at step 6 doesn't help, because B's value was computed from an old read before it waited.

Reset:

```sql
UPDATE customer SET balance = 100 WHERE customer_id = 1;
```

## 2. Fix 1: atomic UPDATE

The subtraction happens inside the database, on the current value of the row, so nothing is computed from an old read.

| Step | Session A | Session B |
|---|---|---|
| 1 | `BEGIN;` | |
| 2 | | `BEGIN;` |
| 3 | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1 AND balance >= 10 RETURNING balance;` → `90.00` | |
| 4 | | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1 AND balance >= 10 RETURNING balance;` → **waits** |
| 5 | `COMMIT;` | |
| 6 | | the `UPDATE` re-reads the committed row (90) → `80.00` |
| 7 | | `COMMIT;` |
| 8 | `SELECT balance FROM customer WHERE customer_id = 1;` → **`80.00`** | |

Final balance **80**. Under `READ COMMITTED`, when B's `UPDATE` stops waiting, PostgreSQL re-evaluates the row with A's committed value (90), so B computes `90 - 10`. The `balance >= 10` condition also stops the balance from going negative without a separate read.

Reset to 100.

## 3. Fix 2: SELECT ... FOR UPDATE

The read itself takes the row lock, so the second session can't read until the first one has finished.

| Step | Session A | Session B |
|---|---|---|
| 1 | `BEGIN;` | |
| 2 | | `BEGIN;` |
| 3 | `SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE;` → `100.00` | |
| 4 | | `SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE;` → **waits** |
| 5 | `UPDATE customer SET balance = 90 WHERE customer_id = 1;` | |
| 6 | `COMMIT;` | |
| 7 | | the `SELECT` returns the committed value → `90.00` |
| 8 | | `UPDATE customer SET balance = 80 WHERE customer_id = 1;` |
| 9 | | `COMMIT;` |
| 10 | `SELECT balance FROM customer WHERE customer_id = 1;` → **`80.00`** | |

Final balance **80**. B waits at step 4 instead of reading the old value, so its calculation starts from 90.

Reset to 100.

## Which fix to use

- The **atomic UPDATE** is the simplest when the new value can be written as an expression (`balance - 10`). It's a single statement, and the lock is held for the shortest time.
- **`SELECT ... FOR UPDATE`** is needed when the application has to read the value, decide something in code (for example call another service or apply rules that are hard to write in SQL), and then write.
