#!/usr/bin/env bash
set -euo pipefail

echo "[start] init_db..."
python -m app.init_db

echo "[start] starting gunicorn..."
exec gunicorn -c gunicorn_conf.py "app:create_app()" \
  --bind "0.0.0.0:${PORT:-5000}" \
  --access-logfile - --error-logfile -

