# Linting — документація

## Обраний лінтер та причини вибору

| Інструмент | Призначення | Чому обрано |
|---|---|---|
| **flake8** | PEP 8, помилки, складність | Швидкий, розширюється плагінами |
| **black** | Авто-форматування | Детерміністичний результат |
| **mypy** | Статична типізація | Виявляє помилки типів до запуску |
| **pre-commit** | Git-хуки | Автозапуск перед кожним комітом |

## Базові правила (.flake8)

```ini
max-line-length = 100
max-complexity  = 10
ignore = E203, W503, E221, E241
```

| Код | Пояснення | Рішення |
|---|---|---|
| E221/E241 | Вирівнювання пробілами в стовпці | Ігноруємо (авторський стиль проєкту) |
| E501 | Рядок >100 символів | Розбиваємо на кілька рядків |
| F401 | Невикористані імпорти | Видаляємо |
| E302/E303/E305 | Порожні рядки | Виправляємо |
| W504 | Line break after binary operator | Виправляємо |
| E128/E127 | Відступи у продовженнях рядків | Виправляємо |
| E702 | Два оператори на одному рядку | Виправляємо |
| F841/B007 | Невикористані змінні | Видаляємо або перейменовуємо |

## Результати початкового запуску

```
flake8 . --count --statistics
```

```
E241  65    (multiple spaces after ':' or ',')
E221  60    (multiple spaces before operator)
E501  24    (line too long)
E128  12    (continuation line under-indented)
E127   9    (continuation line over-indented)
E302   8    (expected 2 blank lines)
W504   7    (line break after binary operator)
F401   5    (imported but unused)
C901   2    (function too complex)
E702   2    (multiple statements on one line)
E272   1    (multiple spaces before keyword)
F841   1    (local variable assigned but never used)
B007   1    (loop variable not used)
E303   1    (too many blank lines)
E131   1    (continuation line unaligned)
E305   1    (expected 2 blank lines after function)
─────────────────
TOTAL  200
```

## Інструкція з запуску

```bash
pip install flake8 black mypy pre-commit

flake8 .                        # перевірка
flake8 . --count --statistics   # з підрахунком
black --check .                 # перевірка форматування
black .                         # авто-форматування
mypy apps/                      # перевірка типів
python scripts/lint_check.py    # все разом
```

## Git Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## Статична типізація

```bash
mypy apps/
```
