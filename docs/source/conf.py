"""Конфігурація Sphinx для генерації документації Service Center.

Запуск: sphinx-build -b html docs/source docs/build/html
Або:    make docs
"""

import os
import sys
import django

# Додаємо корінь проєкту до PYTHONPATH щоб Sphinx міг імпортувати Django-модулі
sys.path.insert(0, os.path.abspath("../.."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_center.settings")
django.setup()

# ── Загальні налаштування ────────────────────────────────────────────────────
project = "Service Center"
copyright = "2024, Service Center Team"
author = "Service Center Team"
release = "1.0.0"

# ── Розширення Sphinx ────────────────────────────────────────────────────────
extensions = [
    "sphinx.ext.autodoc",  # автоімпорт docstrings з Python-коду
    "sphinx.ext.napoleon",  # підтримка Google Style та NumPy docstrings
    "sphinx.ext.viewcode",  # посилання «Переглянути джерело» у документації
    "sphinx.ext.intersphinx",  # посилання на зовнішню документацію (Django, Python)
    "sphinx.ext.autosummary",  # авто-генерація зведених таблиць модулів
]

# ── Налаштування Napoleon (Google Style) ────────────────────────────────────
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True

# ── Налаштування autodoc ─────────────────────────────────────────────────────
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__str__, __init__",
    "undoc-members": False,
    "show-inheritance": True,
}

# ── Шаблони та HTML тема ──────────────────────────────────────────────────────
templates_path = ["_templates"]
exclude_patterns = []
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "navigation_depth": 4,
    "titles_only": False,
}

# ── Intersphinx: посилання на Django docs ────────────────────────────────────
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": (
        "https://docs.djangoproject.com/en/4.2/",
        "https://docs.djangoproject.com/en/4.2/_objects/",
    ),
}
