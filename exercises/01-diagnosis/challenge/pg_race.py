import multiprocessing as mp
import os

import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]
WORKERS = 10
RECORDS = 1000

def worker(number):
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        for n in range(RECORDS):
            conn.execute("INSERT INTO record (worker, n) VALUES (%s, %s)", (number, n))

def main():
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS record (worker integer NOT NULL, n integer NOT NULL)")
        conn.execute("TRUNCATE record")

    processes = [mp.Process(target=worker, args=(i,)) for i in range(WORKERS)]
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    with psycopg.connect(DATABASE_URL) as conn:
        count = conn.execute("SELECT count(*) FROM record").fetchone()[0]
    print(f"SELECT count(*) FROM record: {count} (expected {WORKERS * RECORDS})")

if __name__ == "__main__":
    main()
