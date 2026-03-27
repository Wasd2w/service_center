#!/usr/bin/env python3
"""Комплексна перевірка якості коду — Service Center."""
import subprocess
import sys


def run(cmd: list[str], name: str) -> bool:
    print(f"\n{'=' * 50}\n  {name}\n{'=' * 50}")
    ok = subprocess.run(cmd).returncode == 0
    print(f"  {'✅ OK' if ok else '❌ ПОМИЛКИ'}")
    return ok


def main() -> None:
    checks = [
        (["flake8", ".", "--count", "--statistics"], "Flake8  — стиль PEP 8"),
        (["black", "--check", "."], "Black   — форматування"),
        (["mypy", "apps/"], "Mypy    — типізація"),
    ]
    results = [run(cmd, name) for cmd, name in checks]
    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 50}")
    print(f"  Пройдено: {passed}/{total}")
    if all(results):
        print("  ✅ Можна робити коміт!\n")
        sys.exit(0)
    else:
        print("  ❌ Виправте помилки перед комітом.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
