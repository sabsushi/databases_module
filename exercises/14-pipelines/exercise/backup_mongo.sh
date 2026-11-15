#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../../.."
set -a; source .env; set +a

MONGO_EXEC="${MONGO_EXEC-docker compose exec -T mongo}"
URI="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@localhost:27017/?authSource=admin"

mkdir -p backups
archive="backups/pagila_docs_$(date +%F_%H%M%S).archive.gz"

$MONGO_EXEC mongodump --uri "$URI" --db pagila_docs --archive --gzip > "$archive"

echo "Backup written to $archive ($(du -h "$archive" | cut -f1))"
