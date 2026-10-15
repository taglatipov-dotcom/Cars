"""
Диагностика отправки почты. Запуск на сервере:

    docker compose exec api python -m src.scripts.test_email

Локально:  python -m src.scripts.test_email

Проверяет по шагам: настройки → DNS → открыт ли порт → вход → отправка
тестового письма, и пишет, что делать, если шаг не прошёл.
"""
import logging
import socket
import ssl
import sys

from src import email_notifier as em

logging.basicConfig(level=logging.INFO, format="%(message)s")


def mask(v: str) -> str:
    return (v[:2] + "***" + v[-2:]) if v and len(v) > 4 else ("***" if v else "—")


def step(title):
    print(f"\n=== {title}")


def tcp_check(family, host, port):
    name = "IPv4" if family == socket.AF_INET else "IPv6"
    try:
        addr = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)[0][4]
    except OSError:
        print(f"  {name}: адреса нет")
        return False
    try:
        with socket.create_connection(addr[:2], timeout=7):
            print(f"  {name} {addr[0]}:{port} — порт ОТКРЫТ")
            return True
    except OSError as e:
        print(f"  {name} {addr[0]}:{port} — НЕ ДОСТУПЕН ({type(e).__name__}: {e})")
        return False


def main() -> int:
    step("1. Настройки из .env")
    print(f"  SMTP_HOST={em.SMTP_HOST or '—'}  SMTP_PORT={em.SMTP_PORT}  SMTP_USE_TLS={em.SMTP_USE_TLS}")
    print(f"  SMTP_USER={em.SMTP_USER or '—'}  SMTP_FROM={em.SMTP_FROM or '—'}  SMTP_TO={em.SMTP_TO or '—'}")
    print(f"  SMTP_PASSWORD={mask(em.SMTP_PASSWORD)}  SMTP_FORCE_IPV4={em.SMTP_FORCE_IPV4}")
    print(f"  Письма уйдут от: {em._sender()}")
    if not em.IS_YANDEX and em._sender().lower().endswith(("@yandex.ru", "@ya.ru", "@gmail.com", "@mail.ru")):
        print("  ⚠ Отправитель на бесплатном домене, а сервер не его родной (не smtp.yandex.ru).\n"
              "    Почтовики часто кладут такие письма в спам или отклоняют (политика DMARC).\n"
              "    Надёжнее: отправлять через smtp.yandex.ru от этого же ящика, либо подтвердить\n"
              "    свой домен (например, info@ilsatao.ru) в кабинете SendGrid.")
    if not em.is_email_configured():
        print("  ✗ Заполните SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_TO в src/.env "
              "и перезапустите: docker compose up -d")
        return 1

    step("2. Доступность портов")
    ok_any = False
    for port in (465, 587):
        print(f" порт {port}:")
        ok_v4 = tcp_check(socket.AF_INET, em.SMTP_HOST, port)
        tcp_check(socket.AF_INET6, em.SMTP_HOST, port)
        ok_any = ok_any or ok_v4
    if not ok_any:
        print("  ✗ Оба порта закрыты по IPv4. Скорее всего, хостинг блокирует исходящую почту —\n"
              "    напишите в поддержку хостинга с просьбой открыть исходящие 465/587.")
        return 1

    step("3. Вход на SMTP")
    for mode, port in em._attempts():
        try:
            if mode == "ssl":
                with em._SMTP_SSL_IPv4(em.SMTP_HOST, port, timeout=em.SMTP_TIMEOUT,
                                       context=ssl.create_default_context()) as s:
                    s.login(em.SMTP_USER, em.SMTP_PASSWORD)
            else:
                with em._SMTP_IPv4(em.SMTP_HOST, port, timeout=em.SMTP_TIMEOUT) as s:
                    s.ehlo(); s.starttls(context=ssl.create_default_context()); s.ehlo()
                    s.login(em.SMTP_USER, em.SMTP_PASSWORD)
            print(f"  ✓ {mode}:{port} — вход выполнен")
            break
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {mode}:{port} — {type(e).__name__}: {e}")
    else:
        print("  Если ошибка 535 / authentication failed — нужен пароль приложения Яндекса\n"
              "  (id.yandex.ru → Безопасность → Пароли приложений → Почта) и включённый\n"
              "  доступ почтовых программ (Почта → Настройки → Почтовые программы).")
        return 1

    step("4. Отправка тестового письма")
    ok = em.send_email("Тестовое письмо ILSATAO", "Если вы читаете это — уведомления о заявках работают.")
    print("  ✓ Отправлено — проверьте ящик (и папку «Спам»)" if ok else "  ✗ Не отправлено — см. сообщения выше")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
