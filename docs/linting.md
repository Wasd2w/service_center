# Linting — документація

## Обраний лінтер та причини вибору

Проєкт **Service Center** написаний на **Python 3.12 / Django 4.2**.
Обрано такий стек інструментів:

| Інструмент | Призначення | Чому обрано |
|---|---|---|
| **flake8** | Перевірка стилю (PEP 8), виявлення помилок | Швидкий, легко конфігурується, підтримує плагіни |
| **black** | Авто-форматування | Детерміністичний — один правильний формат |
| **mypy** | Статична перевірка типів | Виявляє помилки типів до запуску |
| **pylint** | Комплексний аналіз | Перевіряє логіку, складність, архітектуру |
| **pre-commit** | Git-хуки | Автоматичний запуск перед кожним комітом |

## Базові правила та їх пояснення

```ini
# .flake8
max-line-length = 100     # Рядки >100 символів важко читати
max-complexity = 10       # Обмеження цикломатичної складності функцій
exclude = migrations      # Автозгенерований код не перевіряємо
ignore = E203, W503       # Сумісність з black-форматуванням
```

| Код | Правило | Пояснення |
|---|---|---|
| E302 | 2 порожні рядки між функціями | Читабельність top-level визначень |
| E501 | Максимальна довжина рядка 100 | Читабельність без горизонтального скролу |
| F401 | Невикористані імпорти | Чистота простору імен, менше плутанини |
| W605 | Невалідні escape-послідовності | Потенційні баги у regex/рядках |
| E711 | `== None` замість `is None` | Коректна перевірка на None |

## Запуск лінтера

### Встановлення
```bash
pip install -r requirements.txt
```

### Flake8
```bash
# Перевірити весь проєкт
flake8 .

# З підрахунком та статистикою
flake8 . --count --statistics

# Конкретний файл
flake8 apps/repairs/views.py
```

### Black
```bash
black --check .        # тільки перевірка
black .                # авто-форматування
```

### Mypy
```bash
mypy apps/
```

### Комплексна перевірка
```bash
python scripts/lint_check.py
# або
make check-all
```

## Результати початкового запуску flake8

```
apps/accounts/views.py:12: E501 line too long (131 > 100 characters)
apps/accounts/views.py:15: E501 line too long (117 > 100 characters)
apps/accounts/views.py:30: E501 line too long (120 > 100 characters)
apps/accounts/views.py:31: E501 line too long (118 > 100 characters)
apps/accounts/views.py:32: E501 line too long (128 > 100 characters)
apps/accounts/views.py:60: E302 expected 2 blank lines, got 0
apps/accounts/views.py:66: E302 expected 2 blank lines, got 0
apps/analytics/views.py:4: F401 'Sum' imported but unused
apps/analytics/views.py:11: F401 'Part' imported but unused
apps/analytics/views.py:23: E302 expected 2 blank lines, got 0
apps/repairs/admin.py:6: E302 expected 2 blank lines, got 0
apps/repairs/admin.py:12: E302 expected 2 blank lines, got 0
apps/repairs/admin.py:30: E302 expected 2 blank lines, got 0
apps/repairs/forms.py:24: W605 invalid escape sequence
apps/repairs/forms.py:34: W605 invalid escape sequence
apps/repairs/forms.py:52-59: E501 line too long (6 violations)
apps/repairs/forms.py:70: W605 invalid escape sequence
apps/repairs/forms.py:85-87: E501 line too long (3 violations)
apps/repairs/forms.py:105,363,365: E501 line too long
apps/repairs/management/commands/seed_data.py:2: F401 'date' imported but unused
apps/repairs/management/commands/seed_data.py:132: E501 line too long
apps/repairs/models.py:45,86-89,114,129,159: E501 line too long (7 violations)
apps/repairs/services.py:9: E302 expected 2 blank lines, got 0
apps/repairs/services.py:93: E302 expected 2 blank lines, got 0
apps/repairs/views.py:8: F401 'RepairComment' imported but unused
apps/repairs/views.py:23-297: E302 expected 2 blank lines (14 violations)
service_center/urls.py:5: F401 'RedirectView' imported but unused

Всього: 54 проблеми
  E302: 20
  E501: 27
  F401:  4
  W605:  3
```

## Git Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    hooks: [id: black]
  - repo: https://github.com/pycqa/flake8
    hooks: [id: flake8]
```

```bash
pre-commit install       # активувати хуки
pre-commit run --all-files  # ручний запуск
```

## Інтеграція з процесом збірки

```bash
make lint        # flake8 + black --check
make format      # black .
make check-all   # flake8 + black + mypy
```

## Статична типізація (mypy)

Конфіг у `mypy.ini`. Запуск: `mypy apps/`

Ключові налаштування:
- `warn_return_any = True` — попередження при поверненні `Any`
- `ignore_missing_imports = True` — Django stubs необов'язкові
