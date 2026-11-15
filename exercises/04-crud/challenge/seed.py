import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse

import psycopg

SEED = 2026
FIRST_ID = 100_001
ROWS = 1_000_000
LAST_ID = FIRST_ID + ROWS - 1
START = datetime(2022, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 7, 31, tzinfo=timezone.utc)

def database_url(name: str) -> str:
    url = urlparse(os.environ["DATABASE_URL"])
    return urlunparse(url._replace(path=f"/{name}"))

def generate_rows(inventory_ids, customer_ids, staff_ids):
    rng = random.Random(SEED)
    span = int((END - START).total_seconds())
    for i in range(ROWS):
        rental_date = START + timedelta(seconds=rng.randrange(span), microseconds=i)
        if rng.random() < 0.05:
            return_date = None
        else:
            return_date = rental_date + timedelta(seconds=rng.randrange(3600, 10 * 24 * 3600))
        yield (
            FIRST_ID + i,
            rental_date,
            rng.choice(inventory_ids),
            rng.choice(customer_ids),
            return_date,
            rng.choice(staff_ids),
        )

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python seed.py <database name>")
    dbname = sys.argv[1]
    started = time.perf_counter()

    with psycopg.connect(database_url(dbname)) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        existing = conn.execute(
            "SELECT count(*) FROM rental WHERE rental_id BETWEEN %s AND %s", (FIRST_ID, LAST_ID)
        ).fetchone()[0]
        if existing == ROWS:
            print(f"{dbname}: the {ROWS:,} rows are already there; nothing to do")
            return
        if existing:
            print(f"{dbname}: found {existing:,} rows of an incomplete run; deleting them")
            conn.execute("DELETE FROM rental WHERE rental_id BETWEEN %s AND %s", (FIRST_ID, LAST_ID))

        inventory_ids = [r[0] for r in conn.execute("SELECT inventory_id FROM inventory ORDER BY 1")]
        customer_ids = [r[0] for r in conn.execute("SELECT customer_id FROM customer ORDER BY 1")]
        staff_ids = [r[0] for r in conn.execute("SELECT staff_id FROM staff ORDER BY 1")]

        with conn.cursor() as cur:
            with cur.copy(
                "COPY rental (rental_id, rental_date, inventory_id, customer_id, return_date, staff_id) "
                "FROM STDIN"
            ) as copy:
                for row in generate_rows(inventory_ids, customer_ids, staff_ids):
                    copy.write_row(row)

            cur.execute("SELECT setval('rental_rental_id_seq', (SELECT max(rental_id) FROM rental))")

        added = conn.execute(
            "SELECT count(*) FROM rental WHERE rental_id BETWEEN %s AND %s", (FIRST_ID, LAST_ID)
        ).fetchone()[0]

    print(f"{dbname}: added {added:,} rows in {time.perf_counter() - started:.1f} s")

if __name__ == "__main__":
    main()
