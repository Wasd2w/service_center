#!/bin/bash
# start_dev.sh — Запуск Service Center у Development режимі

set -e

# Знаходимо кореневу директорію проекту (де знаходиться manage.py)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$APP_DIR"
echo "[INFO] Директорія проекту: $APP_DIR"

# Перевірка наявності venv
if [ ! -d "venv" ]; then
    echo "[INFO] Створення віртуального середовища..."
    python3 -m venv venv
fi

echo "[INFO] Активація віртуального середовища..."
source venv/bin/activate

echo "[INFO] Встановлення/оновлення залежностей..."
pip install -r requirements.txt -q

echo "[INFO] Застосування міграцій..."
python manage.py migrate --run-syncdb

echo "[INFO] Запуск сервера розробки..."
echo "[INFO] Відкрийте браузер: http://127.0.0.1:8000"
python manage.py runserver
