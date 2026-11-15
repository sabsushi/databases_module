# Deadlock

Database `ex08`, two `psql` sessions. Both balances start at 100.

| Step | Session A | Session B |
|---|---|---|
| 1 | `BEGIN;` | |
| 2 | | `BEGIN;` |
| 3 | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1;` → `UPDATE 1` (locks customer 1) | |
| 4 | | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 2;` → `UPDATE 1` (locks customer 2) |
| 5 | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 2;` → **waits** for B | |
| 6 | | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1;` → **waits** for A → deadlock |
| 7 | about 1 second later (`deadlock_timeout`), PostgreSQL aborts one of the two transactions | |
| 8 | `ROLLBACK;` (the transaction that got the error) | `COMMIT;` (the other one continues) |

## The error

In my run, session A was the one chosen as the victim:

```
ERROR:  deadlock detected
DETAIL:  Process 1004 waits for ShareLock on transaction 1874; blocked by process 1005.
Process 1005 waits for ShareLock on transaction 1873; blocked by process 1004.
HINT:  See server log for query details.
CONTEXT:  while locking tuple (17,14) in relation "customer"
```

After the rollback of A and the commit of B, both customers have `90.00`: only B's two updates were kept.

## What each line means

- **`ERROR: deadlock detected`**: PostgreSQL found a cycle of transactions each waiting for the other, which would never end on its own. It cancelled this transaction to break the cycle. The whole transaction is aborted, so its first update (customer 1) is also undone.
- **`DETAIL: Process 1004 waits for ShareLock on transaction 1874; blocked by process 1005.`**: process 1004 is session A (its backend PID). It wants to update a row that transaction 1874 (session B) has already changed. To wait for a transaction to finish, you ask for a `ShareLock` on that transaction's ID, so A is waiting for B to commit or roll back.
- **`Process 1005 waits for ShareLock on transaction 1873; blocked by process 1004.`**: session B (PID 1005) is waiting in the same way for transaction 1873, which is A's. These two lines together are the cycle: A waits for B, and B waits for A.
- **`HINT: See server log for query details.`**: the full SQL of both statements is written to the PostgreSQL log (`docker compose logs postgres`), not sent to the client, so another user's query isn't shown to you.
- **`CONTEXT: while locking tuple (17,14) in relation "customer"`**: where the error happened. A was trying to lock the row at physical position page 17, item 14 of the `customer` table (that's customer 2).

## How to prevent it

- **Always lock rows in the same order.** If every transaction that touches several customers updates them in ascending `customer_id`, a cycle can't form. B would also start with customer 1, wait for A, and then carry on. One way to do it is to lock all the rows at the start of the transaction, in a fixed order:
  ```sql
  SELECT customer_id FROM customer WHERE customer_id IN (1, 2) ORDER BY customer_id FOR UPDATE;
  ```
- **Keep transactions short**, so locks are held for less time.
- **Retry** a transaction that fails with a deadlock (SQLSTATE `40P01`). Deadlocks can still happen occasionally, so the application should be ready for it.
