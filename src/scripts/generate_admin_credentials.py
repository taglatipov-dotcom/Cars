"""Генератор значений для .env: bcrypt-хеш пароля + JWT-секрет.

Запуск:
    python src/scripts/generate_admin_credentials.py
"""
import secrets
import sys

import bcrypt


def main() -> None:
    password = input("Введите пароль администратора: ").strip()
    if not password:
        print("Пароль не может быть пустым", file=sys.stderr)
        sys.exit(1)

    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")

    secret = secrets.token_urlsafe(64)

    print()
    print("=" * 60)
    print("Скопируйте строки ниже в src/.env:")
    print("=" * 60)
    print("ADMIN_USERNAME=admin")
    # Одинарные кавычки обязательны: в хеше есть $, docker compose иначе его подставит
    print(f"ADMIN_PASSWORD_HASH='{hashed}'")
    print(f"JWT_SECRET_KEY='{secret}'")
    print("JWT_ALGORITHM=HS256")
    print("JWT_EXPIRE_MINUTES=480")


if __name__ == "__main__":
    main()