# Challenge 01: JSON file vs PostgreSQL under concurrent writes

| File | What it is |
|---|---|
| `json_race.py` | 10 processes append 1,000 records each to `records.json` (read the whole file, append one, write the whole file), with no lock |
| `pg_race.py` | 10 processes, each with its own connection, insert 1,000 records each into `record`, one `INSERT` per record |
| `pyproject.toml` | Dependency (`psycopg[binary]`) |

## How to run

From the repository root:

```bash
bash scripts/create-db.sh ch01
```

`pg_race.py` creates the table if it doesn't exist (`CREATE TABLE record (worker integer NOT NULL, n integer NOT NULL)`) and empties it before each run. `json_race.py` writes `[]` to `records.json` before each run. In `.env`, set `DATABASE_URL=postgresql://postgres:<password>@localhost:5432/ch01`. From `exercises/01-diagnosis/challenge/`:

```bash
uv sync
uv run python json_race.py
uv run --env-file ../../../.env python pg_race.py
```

## Results

### JSON file (expected 10,000 every time)

```
== JSON run 1
Records in records.json: 55 (expected 10000); file is NOT valid JSON: 25 bytes of garbage after the array
Failed writes (invalid JSON read): 9801
== JSON run 2
Records in records.json: 63 (expected 10000); file is NOT valid JSON: 25 bytes of garbage after the array
Failed writes (invalid JSON read): 9785
== JSON run 3
Records in records.json: 9 (expected 10000); file is NOT valid JSON: 50 bytes of garbage after the array
Failed writes (invalid JSON read): 9979
```

| Run | Records in the file | Failed writes |
|---|---|---|
| 1 | 55 | 9,801 |
| 2 | 63 | 9,785 |
| 3 | 9 | 9,979 |

At the end of every run, the file wasn't even valid JSON: two writes overlapped and left part of another write after the array. The script reads the valid array at the start of the file to count it, and reports the bytes left over.

### PostgreSQL (expected 10,000 every time)

```
== PG run 1
SELECT count(*) FROM record: 10000 (expected 10000)
== PG run 2
SELECT count(*) FROM record: 10000 (expected 10000)
== PG run 3
SELECT count(*) FROM record: 10000 (expected 10000)
```

| Run | `count(*)` |
|---|---|
| 1 | 10,000 |
| 2 | 10,000 |
| 3 | 10,000 |

## Why the numbers differ

The JSON file loses almost every record because of **lost updates from concurrent read-modify-write**. Each append is three separate steps: read the whole file, change the list in memory, write the whole file. Nothing stops another process from doing the same in between. If processes A and B both read a file with 40 records, each adds its own, and each writes back 41. The one that writes last wins, and the other's record disappears. With 10 processes doing this 1,000 times each, almost every write is overwritten by another. It's also worse than lost updates: writing a file isn't atomic. A process can read the file while another is halfway through writing it, and gets invalid JSON (counted here as a failed write: about 9,800 per run). Two writes can also overlap and leave a corrupted file. The result depends on the exact timing of the processes, which is why the count changes on every run.

PostgreSQL gets exactly 10,000 every time because the client never does read-modify-write. Each `INSERT` asks the **engine** to add one row, and the engine applies concurrent changes safely. Every `INSERT` is its own transaction (atomic: the row is either fully written or not at all). New rows go into free space in the table's pages under short internal locks, so two inserts never overwrite each other. The write-ahead log (WAL) makes every committed insert durable, and MVCC isolation means a reader never sees a half-written row. Concurrency control is the engine's job, not each client's.
