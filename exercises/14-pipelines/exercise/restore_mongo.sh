#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../../.."
set -a; source .env; set +a

MONGO_EXEC="${MONGO_EXEC-docker compose exec -T mongo}"
URI="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/?authSource=admin"

archive="$(ls -1t backups/pagila_docs_*.archive.gz 2>/dev/null | head -n 1 || true)"
if [ -z "$archive" ]; then
    echo "No archive found in backups/. Run backup_mongo.sh first." >&2
    exit 1
fi
echo "Restoring $archive into pagila_docs_restored"

$MONGO_EXEC mongorestore --uri "$URI" --archive --gzip --drop \
    --nsFrom 'pagila_docs.*' --nsTo 'pagila_docs_restored.*' < "$archive"

$MONGO_EXEC mongosh "$URI" --quiet --eval '
  const a = db.getSiblingDB("pagila_docs"), b = db.getSiblingDB("pagila_docs_restored");
  const names = a.getCollectionNames().sort();
  let same = true;
  print("collection".padEnd(14) + "pagila_docs".padStart(14) + "pagila_docs_restored".padStart(22));
  for (const c of names) {
    const x = a[c].countDocuments({}), y = b[c].countDocuments({});
    if (x !== y) same = false;
    print(c.padEnd(14) + String(x).padStart(14) + String(y).padStart(22));
  }
  print(same ? "OK: every collection has the same number of documents" : "DIFFERENT COUNTS");
'
