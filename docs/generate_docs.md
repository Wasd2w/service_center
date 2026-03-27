# Інструкція з генерації документації — Service Center

## Передумови

Встановіть залежності для документації:

```bash
pip install sphinx sphinx-rtd-theme
```

Або додайте до `requirements.txt` та виконайте:

```bash
pip install -r requirements.txt
```

---

## 1. Генерація HTML документації (Sphinx)

### Через Makefile (рекомендовано)

```bash
make docs
```

### Вручну

```bash
sphinx-build -b html docs/source docs/build/html
```

### Перегляд результату

```bash
# macOS
open docs/build/html/index.html

# Linux
xdg-open docs/build/html/index.html

# Windows
start docs/build/html/index.html
```

---

## 2. Очищення та повна регенерація

```bash
make docs-clean   # або вручну:
rm -rf docs/build
sphinx-build -b html docs/source docs/build/html
```

---

## 3. Перевірка якості docstrings (лінтинг)

Проєкт використовує `pydocstyle` для перевірки наявності та формату docstrings.

```bash
# Запуск лінтера
make lint-docs   # або:
pydocstyle apps/ --convention=google

# Ігноруємо __pycache__ та міграції
pydocstyle apps/ --convention=google --match='(?!migrations).*\.py'
```

### Налаштування у `pyproject.toml`

```toml
[tool.pydocstyle]
convention = "google"
match = "(?!migrations|seed_data).*\\.py"
add-ignore = "D100,D104"   # дозволяємо модулі без docstring у __init__.py
```

---

## 4. Структура згенерованої документації

```
docs/
├── source/                   ← Sphinx вхідні файли
│   ├── conf.py               ← Конфігурація Sphinx
│   ├── index.rst             ← Головна сторінка
│   └── modules/              ← .rst для кожного модуля
│       ├── repairs_models.rst
│       ├── repairs_services.rst
│       ├── repairs_views.rst
│       └── analytics_views.rst
├── build/                    ← Згенерована документація (не в git)
│   └── html/
│       └── index.html        ← Відкрити в браузері
└── generate_docs.md          ← Ця інструкція
```

---

## 5. Що документувати — чек-лист

| Що | Обов'язково | Бажано |
|---|---|---|
| Модуль (`module docstring`) | ✅ | приклад архіт. рішення |
| Публічна функція | ✅ Args, Returns | Raises, Example |
| Клас | ✅ опис | Attributes section |
| Публічний метод | ✅ | Example для складних |
| Приватна функція (`_func`) | — | короткий опис |
| `__str__`, `__repr__` | — | якщо логіка нетривіальна |

---

## 6. Скрипти в Makefile

```makefile
docs:         ## Генерує HTML документацію через Sphinx
    sphinx-build -b html docs/source docs/build/html

docs-clean:   ## Видаляє згенеровану документацію
    rm -rf docs/build

lint-docs:    ## Перевіряє якість docstrings через pydocstyle
    pydocstyle apps/ --convention=google
```

---

## 7. Додавання нового модуля до документації

1. Додайте docstrings до нового файлу (Google Style)
2. Створіть `.rst` файл у `docs/source/modules/`:

```rst
Назва модуля
=============

.. automodule:: apps.my_app.my_module
   :members:
   :undoc-members:
   :show-inheritance:
```

3. Додайте посилання до `docs/source/index.rst`:

```rst
.. toctree::
   modules/my_module
```

4. Перегенеруйте: `make docs`
