# 💾 Backup Guide — Резервне копіювання

## Що резервуємо

| Компонент | Метод | Частота |
|---|---|---|
| База даних SQLite | Копіювання файлу | Щодня |
| Медіа-файли (якщо є) | rsync | Щодня |
| Конфігурація .env | Ручно, у захищеному сховищі | При змінах |

---

## Автоматичне резервне копіювання

Скрипт: `docs/scripts/backup.sh`

### Запуск вручну
```bash
bash /var/www/service_center/docs/scripts/backup.sh
```

### Налаштування автоматичного запуску (cron)
```bash
crontab -e
# Додати рядок — щодня о 03:00
0 3 * * * /var/www/service_center/docs/scripts/backup.sh >> /var/log/service_center_backup.log 2>&1
```

---

## Відновлення з резервної копії

```bash
# Зупинити сервіс
sudo systemctl stop service_center

# Переглянути доступні бекапи
ls -lh /var/backups/service_center/

# Відновити потрібний бекап
cp /var/backups/service_center/db_backup_2024-03-27.sqlite3 \
   /var/www/service_center/db.sqlite3

# Запустити сервіс
sudo systemctl start service_center
```

---

## Перевірка резервних копій

```bash
# Список бекапів
ls -lh /var/backups/service_center/

# Перевірити цілісність SQLite
sqlite3 /var/backups/service_center/db_backup_LATEST.sqlite3 "PRAGMA integrity_check;"
# Очікувана відповідь: ok
```

---

## Зберігання бекапів

- Локально: `/var/backups/service_center/` (зберігати 30 днів)
- Рекомендовано: копіювати на зовнішній сервер або хмарне сховище (S3, Google Drive)
- Автоматичне видалення старих бекапів: скрипт `backup.sh` видаляє файли старші 30 днів
