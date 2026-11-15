import os
import sys
import threading

import psycopg
from psycopg import errors

STORE_ID = 1
DATABASE_URL = os.environ["DATABASE_URL"]

LEVELS = {
    "read-committed": psycopg.IsolationLevel.READ_COMMITTED,
    "serializable": psycopg.IsolationLevel.SERIALIZABLE,
}

def active_staff_ids():
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            "SELECT staff_id FROM staff WHERE store_id = %s AND active ORDER BY staff_id",
            (STORE_ID,),
        ).fetchall()
    return [r[0] for r in rows]

def worker(staff_id, level, barrier, results, lock):
    retries = 0
    first_attempt = True
    with psycopg.connect(DATABASE_URL) as conn:
        conn.isolation_level = level
        while True:
            try:
                with conn.transaction():
                    count = conn.execute(
                        "SELECT count(*) FROM staff WHERE store_id = %s AND active",
                        (STORE_ID,),
                    ).fetchone()[0]
                    if first_attempt:
                        first_attempt = False
                        barrier.wait()
                    deactivated = False
                    if count > 1:
                        conn.execute(
                            "UPDATE staff SET active = false WHERE staff_id = %s",
                            (staff_id,),
                        )
                        deactivated = True
                with lock:
                    results.append((staff_id, count, deactivated, retries))
                return
            except errors.SerializationFailure:
                retries += 1

def main():
    level_name = sys.argv[1] if len(sys.argv) > 1 else "read-committed"
    level = LEVELS[level_name]

    ids = active_staff_ids()
    print(f"Isolation level: {level_name}")
    print(f"Active staff in store {STORE_ID} before: {len(ids)}")

    barrier = threading.Barrier(len(ids))
    results, lock = [], threading.Lock()
    threads = [
        threading.Thread(target=worker, args=(sid, level, barrier, results, lock))
        for sid in ids
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    deactivated = sum(1 for r in results if r[2])
    retries = sum(r[3] for r in results)
    print(f"Threads that deactivated their member: {deactivated}")
    print(f"Serialisation failures retried: {retries}")
    print(f"Active staff in store {STORE_ID} after: {len(active_staff_ids())}")

if __name__ == "__main__":
    main()
