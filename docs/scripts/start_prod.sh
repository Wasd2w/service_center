#!/bin/bash
# start_prod.sh — Запуск Service Center у Production режимі

set -e

APP_DIR="/var/www/service_center"
cd "$APP_DIR"

echo "[$(date)] Активація віртуального середовища..."
source venv/bin/activate

echo "[$(date)] Запуск Gunicorn..."
gunicorn \
    --workers 3 \
    --bind unix:/run/service_center.sock \
    --log-level info \
    --access-logfile /var/log/service_center_access.log \
    --error-logfile /var/log/service_center_error.log \
    service_center.wsgi:application

echo "[$(date)] Production сервер запущено"
