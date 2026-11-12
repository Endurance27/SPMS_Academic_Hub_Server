#!/bin/bash

echo "🚀 Starting SPMS Academic Hub Server..."

# Create necessary directories
mkdir -p /app/uploads
mkdir -p /app/logs

# Run database migrations
if [ "$DB_AUTO_CREATE_TABLES" != "True" ]; then
    echo "🔄 Running database migrations..."
    if PYTHONPATH=. python scripts/migrate_db.py; then
        echo "✓ Migrations completed"
    else
        echo "⚠️  Migrations failed, but continuing (DB_AUTO_CREATE_TABLES will handle schema)"
        export DB_AUTO_CREATE_TABLES="true"
    fi
else
    echo "⚠️  DB_AUTO_CREATE_TABLES is enabled - skipping migrations"
fi

echo "✓ Startup complete, starting application..."
exec "$@"
