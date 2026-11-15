import sys

from common import expected_from_postgres, redis_client, scan_keys

def main() -> int:
    expected = expected_from_postgres()
    r = redis_client()
    present = scan_keys(r)

    pipe = r.pipeline(transaction=False)
    keys = sorted(expected, key=lambda k: int(k.split(":")[1]))
    for k in keys:
        pipe.smembers(k)
    actual = dict(zip(keys, pipe.execute()))

    problems = []
    for k in keys:
        want, got = expected[k], actual[k]
        if not got:
            problems.append(f"{k}: missing in Redis (expected {len(want)} categories)")
        elif want != got:
            detail = []
            if len(want) != len(got):
                detail.append(f"size {len(got)} instead of {len(want)}")
            if want - got:
                detail.append(f"missing {sorted(want - got)}")
            if got - want:
                detail.append(f"unexpected {sorted(got - want)}")
            problems.append(f"{k}: " + ", ".join(detail))

    for k in sorted(present - expected.keys()):
        problems.append(f"{k}: should not exist (customer has no rentals); "
                        f"has {sorted(r.smembers(k))}")

    for p in problems:
        print("DIFF", p)
    print(f"Checked {len(keys)} expected sets and {len(present)} keys in Redis: "
          f"{len(problems)} difference(s)")
    return 1 if problems else 0

if __name__ == "__main__":
    sys.exit(main())
