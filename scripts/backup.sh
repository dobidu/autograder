#!/usr/bin/env bash
# backup.sh — Backup SQLite database and storage
set -euo pipefail

APP_DIR="/opt/lpii-autograder"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/autograder}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=30

echo "=== LPII AutoGrader — Backup ==="

mkdir -p "$BACKUP_DIR"

# Backup SQLite (online safe copy)
DB_PATH="$APP_DIR/storage/db/autograder.db"
DB_BACKUP="$BACKUP_DIR/autograder_${TIMESTAMP}.db"

if [ -f "$DB_PATH" ]; then
    echo "[1/3] Backing up database..."
    sqlite3 "$DB_PATH" ".backup '$DB_BACKUP'"
    gzip "$DB_BACKUP"
    echo "    Database: ${DB_BACKUP}.gz"
else
    echo "[1/3] No database found at $DB_PATH"
fi

# Backup storage (submissions, assignments)
echo "[2/3] Backing up storage..."
STORAGE_BACKUP="$BACKUP_DIR/storage_${TIMESTAMP}.tar.gz"
tar -czf "$STORAGE_BACKUP" -C "$APP_DIR" storage/submissions storage/assignments 2>/dev/null || true
echo "    Storage: $STORAGE_BACKUP"

# Cleanup old backups
echo "[3/3] Cleaning up backups older than ${KEEP_DAYS} days..."
find "$BACKUP_DIR" -name "autograder_*.db.gz" -mtime +${KEEP_DAYS} -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "storage_*.tar.gz" -mtime +${KEEP_DAYS} -delete 2>/dev/null || true

echo ""
echo "=== Backup complete ==="
ls -lh "$BACKUP_DIR"/ | tail -5
