import os
import threading
from collections import Counter

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
N = 5

barrier = threading.Barrier(N)
results = [None] * N

def rent(i):
    body = {"customer_id": i + 1, "film_id": 7, "store_id": 1, "staff_id": 6}
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        barrier.wait()
        r = client.post("/rentals", json=body)
        results[i] = (body["customer_id"], r.status_code, r.json())

threads = [threading.Thread(target=rent, args=(i,)) for i in range(N)]
for t in threads:
    t.start()
for t in threads:
    t.join()

for customer_id, status, body in results:
    print(f"customer {customer_id}: {status} {body}")

statuses = Counter(status for _, status, _ in results)
copies = {body["inventory_id"] for _, status, body in results if status == 201}
print()
print(f"201: {statuses[201]}, 409: {statuses[409]}, different inventory_id: {sorted(copies)}")
ok = statuses[201] == 2 and statuses[409] == 3 and len(copies) == 2
print("OK" if ok else "UNEXPECTED RESULT")
raise SystemExit(0 if ok else 1)
