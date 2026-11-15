import secrets
import time

from common import expected_from_postgres, redis_client, scan_keys

def main():
    start = time.perf_counter()
    expected = expected_from_postgres()
    r = redis_client()
    stale = scan_keys(r) - expected.keys()

    run = secrets.token_hex(4)
    pipe = r.pipeline(transaction=False)
    for k, members in expected.items():
        tmp = f"tmp:{run}:{k}"
        pipe.delete(tmp)
        pipe.sadd(tmp, *members)
        pipe.rename(tmp, k)
    for k in stale:
        pipe.delete(k)
    pipe.execute()

    elapsed = time.perf_counter() - start
    print(f"Rebuilt {len(expected)} sets from 1 query and 1 pipeline "
          f"({len(stale)} stale key(s) deleted) in {elapsed:.2f} s")
    print(f"Keys matching customer:*:categories (SCAN): {len(scan_keys(r))}")

if __name__ == "__main__":
    main()
