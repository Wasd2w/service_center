#!/bin/bash
# backup.sh — Резервне копіювання бази даних Service Center

set -e

APP_DIR="/var/www/service_center"
BACKUP_DIR="/var/backups/service_center"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
DB_FILE="$APP_DIR/db.sqlite3"
BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sqlite3"
KEEP_DAYS=30

echo "[$(date)] Починаємо резервне копіювання..."

# Створення директорії для бекапів
mkdir -p "$BACKUP_DIR"

# Копіювання бази даних
if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_FILE"
    echo "[$(date)] Бекап збережено: $BACKUP_FILE"
else
    echo "[$(date)] ПОМИЛКА: База даних не знайдена: $DB_FILE"
    exit 1
fi

# Перевірка цілісності
if sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "[$(date)] Перевірка цілісності: OK"
else
    echo "[$(date)] ПОМИЛКА: Бекап пошкоджений!"
    exit 1
fi

# Видалення старих бекапів
find "$BACKUP_DIR" -name "db_backup_*.sqlite3" -mtime +$KEEP_DAYS -delete
echo "[$(date)] Видалено бекапи старші $KEEP_DAYS днів"

echo "[$(date)] Резервне копіювання завершено успішно."
