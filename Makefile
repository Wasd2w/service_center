.PHONY: lint format type-check check-all install-hooks

lint:
	flake8 .

format:
	black .

type-check:
	mypy apps/

check-all:
	@echo "=== Flake8 ==="
	flake8 . --count --statistics
	@echo ""
	@echo "=== Black ==="
	black --check .
	@echo ""
	@echo "=== Mypy ==="
	mypy apps/
	@echo ""
	@echo "All checks done!"

install-hooks:
	pip install pre-commit
	pre-commit install
	@echo "Pre-commit hooks installed"

# Документація
docs:  ## Генерує HTML документацію через Sphinx
	sphinx-build -b html docs/source docs/build/html

docs-clean:  ## Видаляє згенеровану документацію
	rm -rf docs/build

lint-docs:  ## Перевіряє якість docstrings (pydocstyle)
	pydocstyle apps/ --convention=google
