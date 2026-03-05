#!/usr/bin/env bash
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "Waiting for database..."
  python - <<'PY'
import os
import time
from urllib.parse import urlparse
import psycopg

url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit(0)

parsed = urlparse(url)
conninfo = {
    "host": parsed.hostname,
    "port": parsed.port,
    "user": parsed.username,
    "password": parsed.password,
    "dbname": parsed.path.lstrip("/"),
}

for _ in range(60):
    try:
        with psycopg.connect(**conninfo):
            print("Database is ready")
            break
    except Exception:
        time.sleep(1)
else:
    raise RuntimeError("Database not reachable")
PY
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

exec "$@"
