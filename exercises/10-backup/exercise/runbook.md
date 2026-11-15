# Runbook: restoring rows deleted by mistake (payment, film_actor, film_category)

## When to use it

Use this runbook when rows were **deleted by mistake** from some tables of a PostgreSQL database (a bad `DELETE`, a script run on the wrong database), but the database itself still exists and the rest of it is fine. It restores **only the damaged tables** from the last backup, without dropping or recreating the database, so the other tables and their changes since the backup are not touched.

It is written for the incident of `disaster.sql` on `ex10`:

- `payment`: every payment from `2026-01-01` deleted (partitions `payment_p2026_01` to `payment_p2026_07`);
- `film_actor`: the rows of actors 1 to 50 deleted;
- `film_category`: the rows of category 1 (Action) deleted.

Do **not** use it when the whole database or server is lost (restore the full dump into a new database instead, as in the session 10 tutorial).

## Prerequisites

- The Docker environment of the module running (`docker compose up -d`, `postgres` healthy).
- A custom-format backup (`pg_dump -Fc`) of the database taken **before** the incident, in `backups/` at the repository root.
- Superuser access (`postgres`).
- Every command runs from the **repository root**. They work in both PowerShell and bash: the dump is copied into the container with `docker compose cp`, so binary data never goes through a shell pipe.
- **Stop the application** (or anything writing to these tables) before step 5, and tell the team that the restore is in progress.

## Commands, in order

### 1. Starting point and row counts before the backup (task 1)

```bash
bash scripts/create-db.sh ex10 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex10 -c "SELECT (SELECT count(*) FROM payment) AS payment, (SELECT count(*) FROM film_actor) AS film_actor, (SELECT count(*) FROM film_category) AS film_category;"
 payment | film_actor | film_category
---------+------------+---------------
   51061 |       5462 |          2367
```

### 2. Back up `ex10` in custom format (task 2)

```bash
docker compose exec -T postgres pg_dump -U postgres -Fc -f /tmp/ex10_backup.dump ex10
docker compose cp postgres:/tmp/ex10_backup.dump backups/ex10_backup.dump
```

Backup taken at: **2026-11-15 10:12:23 UTC** (4.5 MB). `backups/` is in `.gitignore`, so the dump is never committed.

### 3. Normal activity, then the incident (task 3)

```bash
docker compose exec -T postgres psql -U postgres -d ex10 -v ON_ERROR_STOP=1 -f - < exercises/10-backup/exercise/activity.sql
docker compose exec -T postgres psql -U postgres -d ex10 -v ON_ERROR_STOP=1 -f - < exercises/10-backup/exercise/disaster.sql
```

(In PowerShell, use `Get-Content exercises/10-backup/exercise/activity.sql | docker compose exec -T postgres psql -U postgres -d ex10 -v ON_ERROR_STOP=1`, and the same for `disaster.sql`.)

```
INSERT 0 5
BEGIN
DELETE 5286
DELETE 1327
DELETE 149
COMMIT
```

Row counts after the incident:

```
 payment | film_actor | film_category
---------+------------+---------------
   45780 |       4135 |          2218
```

`DELETE 5286` is the 5,281 payments of 2026 that were in the backup plus the 5 payments of `activity.sql`, made after the backup.

### 4. Check the backup before touching anything

```bash
docker compose cp backups/ex10_backup.dump postgres:/tmp/ex10_backup.dump
docker compose exec -T postgres pg_restore -l /tmp/ex10_backup.dump
```

The list must contain `TABLE DATA public film_actor`, `TABLE DATA public film_category` and `TABLE DATA public payment_p2026_01` to `payment_p2026_07`.

### 5. Restore (task 4)

**The plan.**

- `film_actor` and `film_category` still hold part of their rows. Restoring the full table on top of them would fail on the primary keys of the rows that are still there. So I empty them with `TRUNCATE`, then reload their data from the backup. No other table references them, and nobody changes them in normal use, so the backup copy is the right content.
- `payment` is partitioned. `pg_restore -t payment` restores nothing, because the rows live in the partitions. Each partition has to be named. Only `payment_p2026_01` to `payment_p2026_07` were damaged, so only those 7 are truncated and reloaded. The 48 older partitions are left alone.
- `--data-only` loads only the rows. The tables, indexes and constraints still exist, and `--clean` would try to drop tables that views depend on.

Both commands run in one step, and the time of the whole step is measured:

```bash
time docker compose exec -T postgres sh -c '
  psql -U postgres -d ex10 -v ON_ERROR_STOP=1 -c "TRUNCATE film_actor, film_category, payment_p2026_01, payment_p2026_02, payment_p2026_03, payment_p2026_04, payment_p2026_05, payment_p2026_06, payment_p2026_07" &&
  pg_restore -U postgres -d ex10 --data-only --exit-on-error \
    -t film_actor -t film_category \
    -t payment_p2026_01 -t payment_p2026_02 -t payment_p2026_03 -t payment_p2026_04 \
    -t payment_p2026_05 -t payment_p2026_06 -t payment_p2026_07 \
    /tmp/ex10_backup.dump'
```

(In PowerShell, replace `time` with `Measure-Command { ... }` around the command, or just note the clock before and after.)

```
TRUNCATE TABLE

real    0m0.305s
```

### 6. Verify the restore (task 5)

```bash
docker compose exec -T postgres psql -U postgres -d ex10 -c "SELECT (SELECT count(*) FROM payment) AS payment, (SELECT count(*) FROM film_actor) AS film_actor, (SELECT count(*) FROM film_category) AS film_category;"
 payment | film_actor | film_category
---------+------------+---------------
   51061 |       5462 |          2367
```

Known values to check:

```sql
SELECT sum(amount) FROM payment WHERE payment_date >= '2026-07-01' AND payment_date < '2026-08-01';
SELECT count(*) FROM film_actor WHERE actor_id <= 50;
SELECT count(*) FROM film_category WHERE category_id = 1;
```

All three returned the expected values. Then restart the application and tell the team.

## Row counts

| | payment | film_actor | film_category |
|---|---|---|---|
| Task 1: before the backup | 51,061 | 5,462 | 2,367 |
| Task 3: after `activity.sql` and `disaster.sql` | 45,780 | 4,135 | 2,218 |
| Task 5: after the restore | **51,061** | **5,462** | **2,367** |

After the restore, the counts are the same as in task 1, not task 1 + 5. The 5 payments of `activity.sql` were made after the backup, so they aren't in it and couldn't be restored.

## Real RTO (restore time)

**0.3 seconds** for step 5 (truncate + `pg_restore` of the 9 tables), measured with `time`. Including checking the backup (step 4) and verifying (step 6), the whole procedure takes a few minutes, and most of that is people, not the machine.

## Real RPO (data lost)

Everything written between the backup (10:12:23) and the incident is lost. Here, those are **the 5 payments of `activity.sql`** (1.99 each, dated `2026-07-30 12:00`).

The query that shows it: the sequence `payment_payment_id_seq` isn't restored by `--data-only -t`, so it still remembers the IDs it handed out after the backup. Any ID above the largest one in the table was a payment that's now lost:

```sql
SELECT s.last_value AS last_id_used, max(p.payment_id) AS last_id_present,
       s.last_value - max(p.payment_id) AS payments_lost
FROM payment p, payment_payment_id_seq s
GROUP BY s.last_value;

SELECT g AS lost_payment_id
FROM generate_series((SELECT max(payment_id) + 1 FROM payment),
                     (SELECT last_value FROM payment_payment_id_seq)) g;
 last_id_used | last_id_present | payments_lost
--------------+-----------------+---------------
       102099 |          102094 |             5

 lost_payment_id
-----------------
          102095
          102096
          102097
          102098
          102099
```

These 5 payments were real money received. Someone has to enter them again by hand from another source (receipts, the payment provider's report).

## What I would change in the backup strategy to lose less

- **Continuous WAL archiving with point-in-time recovery (PITR).** With a base backup (`pg_basebackup`) plus every WAL file archived as it's written, the database can be restored to the second just before the `DELETE` (for example `recovery_target_time = '... 10:12:59'`). The RPO goes from "since the last dump" to seconds, and the 5 payments wouldn't be lost. Tools like pgBackRest or WAL-G handle this.
- **More frequent logical backups** (for example every hour with a cron job and `pg_dump -Fc`), with a retention policy (24 hourly, 7 daily, 4 weekly), as a simpler second layer.
- **Keep copies off the server**, in another location (object storage), so losing the machine doesn't also lose the backups.
- **Test the restore regularly** (for example monthly, into a clean container as in the tutorial), and measure the RTO each time. A backup that's never been restored isn't proven to work.
- **Prevent the incident itself:** the application connects with a role without `DELETE` on these tables, or `DELETE` scripts run in a transaction that is checked (`SELECT count(*)` first) before `COMMIT`.
