#!/bin/bash
set -e

echo "⏳ Waiting for DB"
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 1
done
echo "📦 Applying migrations"
alembic upgrade head

echo "🌱 Seeding fees"
python scripts/init_db.py

echo "🚀 Start App"
exec "$@"