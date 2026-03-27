# 🔄 Update Guide — Оновлення системи

## Підготовка до оновлення

### 1. Перевірка сумісності
```bash
# Переглянути список змін у новій версії
git log HEAD..origin/main --oneline

# Перевірити нові міграції
git diff HEAD..origin/main -- apps/*/migrations/
```

### 2. Планування часу простою
- Стандартне оновлення: ~5-10 хвилин
- Оновлення з міграціями БД: ~15-30 хвилин
- Рекомендований час: нічний час (02:00–05:00)

### 3. Резервне копіювання ПЕРЕД оновленням
```bash
# Обов'язково! Виконайте резервне копіювання БД
/var/www/service_center/docs/scripts/backup.sh
```

---

## Процес оновлення

### Крок 1 — Зупинка сервісу
```bash
sudo systemctl stop service_center
```

### Крок 2 — Оновлення коду
```bash
cd /var/www/service_center
sudo git fetch origin
sudo git pull origin main
```

### Крок 3 — Оновлення залежностей
```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Крок 4 — Міграція бази даних
```bash
python manage.py migrate
```

### Крок 5 — Оновлення статики
```bash
python manage.py collectstatic --noinput
```

### Крок 6 — Запуск сервісу
```bash
sudo systemctl start service_center
sudo systemctl status service_center
```

### Крок 7 — Перезапуск Nginx
```bash
sudo systemctl reload nginx
```

---

## Перевірка після оновлення

```bash
# Перевірити статус процесу
sudo systemctl status service_center

# Перевірити логи на помилки
sudo journalctl -u service_center --since "5 minutes ago"

# HTTP перевірка
curl -I http://your-domain.com

# Перевірити адмін-панель
curl -I http://your-domain.com/admin/
```

---

## 🔙 Процедура відкату (Rollback)

У разі невдалого оновлення:

### Крок 1 — Зупинити сервіс
```bash
sudo systemctl stop service_center
```

### Крок 2 — Повернути попередню версію коду
```bash
cd /var/www/service_center

# Переглянути попередні коміти
git log --oneline -10

# Повернутись до попереднього коміту
git checkout <PREVIOUS_COMMIT_HASH>
```

### Крок 3 — Відновити базу даних з резервної копії
```bash
# Знайти останній бекап
ls -lt /var/backups/service_center/

# Відновити
cp /var/backups/service_center/db_backup_YYYY-MM-DD.sqlite3 /var/www/service_center/db.sqlite3
```

### Крок 4 — Запустити попередню версію
```bash
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate  # Застосує зворотні міграції якщо є
sudo systemctl start service_center
```

### Крок 5 — Перевірка
```bash
curl -I http://your-domain.com
sudo journalctl -u service_center --since "2 minutes ago"
```
