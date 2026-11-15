import json
import multiprocessing as mp
from pathlib import Path

FILE = Path(__file__).with_name("records.json")
WORKERS = 10
RECORDS = 1000

def worker(number, failed):
    for n in range(RECORDS):
        try:
            records = json.loads(FILE.read_text())
            records.append({"worker": number, "n": n})
            FILE.write_text(json.dumps(records))
        except (json.JSONDecodeError, ValueError):
            with failed.get_lock():
                failed.value += 1

def main():
    FILE.write_text("[]")
    failed = mp.Value("i", 0)
    processes = [mp.Process(target=worker, args=(i, failed)) for i in range(WORKERS)]
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    text = FILE.read_text()
    try:
        count = len(json.loads(text))
        note = "file is valid JSON"
    except json.JSONDecodeError:
        records, end = json.JSONDecoder().raw_decode(text)
        count = len(records)
        note = f"file is NOT valid JSON: {len(text) - end} bytes of garbage after the array"
    print(f"Records in records.json: {count} (expected {WORKERS * RECORDS}); {note}")
    print(f"Failed writes (invalid JSON read): {failed.value}")

if __name__ == "__main__":
    main()
