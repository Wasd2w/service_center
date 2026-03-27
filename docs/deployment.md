# 🚀 Deployment Guide — Production

## Вимоги до апаратного забезпечення

| Параметр | Мінімум | Рекомендовано |
|---|---|---|
| Архітектура | x86_64 | x86_64 |
| CPU | 1 vCPU | 2 vCPU |
| RAM | 512 MB | 1 GB |
| Диск | 5 GB | 20 GB |

---

## Необхідне програмне забезпечення

- Ubuntu 22.04 LTS (або Debian 11+)
- Python 3.10+
- Nginx
- Gunicorn
- SQLite3 (або PostgreSQL для великих навантажень)

---

## Крок 1 — Оновлення системи та встановлення залежностей

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx git
```

## Крок 2 — Клонування репозиторію

```bash
cd /var/www
sudo git clone https://github.com/Wasd2w/service_center.git
sudo chown -R www-data:www-data /var/www/service_center
cd /var/www/service_center
```

## Крок 3 — Віртуальне середовище та залежності

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

## Крок 4 — Налаштування середовища

Створіть файл `/var/www/service_center/.env`:

```env
SECRET_KEY=your-very-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-server-ip
```

Відредагуйте `service_center/settings.py` для production:

```python
import os
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

## Крок 5 — Міграції та збір статики

```bash
source venv/bin/activate
python manage.py migrate --run-syncdb
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## Крок 6 — Налаштування Gunicorn

Створіть systemd сервіс `/etc/systemd/system/service_center.service`:

```ini
[Unit]
Description=Service Center Django App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/service_center
EnvironmentFile=/var/www/service_center/.env
ExecStart=/var/www/service_center/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/service_center.sock \
    service_center.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable service_center
sudo systemctl start service_center
```

## Крок 7 — Налаштування Nginx

Створіть `/etc/nginx/sites-available/service_center`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        root /var/www/service_center/staticfiles;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/service_center.sock;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/service_center /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Перевірка працездатності

```bash
# Статус сервісу
sudo systemctl status service_center

# Логи
sudo journalctl -u service_center -f

# HTTP відповідь
curl -I http://your-domain.com
```

Якщо все налаштовано правильно:
- `systemctl status service_center` → `active (running)`
- `curl` повертає `HTTP/1.1 200 OK`
- Сторінка входу доступна у браузері
