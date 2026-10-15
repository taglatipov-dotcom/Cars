import logging
import os
import smtplib
import socket
import ssl
import time
from email.header import Header
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

from dotenv import load_dotenv

from src.config import settings

# .env лежит рядом с этим файлом (src/.env)
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER
SMTP_TO = os.getenv("SMTP_TO", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "false").lower() in ("1", "true", "yes")
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "15"))
# В Docker часто нет IPv6, а smtp.yandex.ru отдаёт и IPv6-адрес — соединение
# по нему зависает до таймаута. По умолчанию подключаемся только по IPv4.
SMTP_FORCE_IPV4 = os.getenv("SMTP_FORCE_IPV4", "true").lower() in ("1", "true", "yes")
SMTP_RETRIES = int(os.getenv("SMTP_RETRIES", "3"))

log = logging.getLogger("email")


def is_email_configured() -> bool:
    """True, если все обязательные настройки SMTP заданы."""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_TO)


def _encode_header(value: str) -> str:
    """
    Кодирует заголовок письма в RFC 2047, чтобы корректно
    переносить кириллицу и эмодзи (например: =?utf-8?b?...?=).
    """
    return Header(value, "utf-8").encode()


IS_YANDEX = "yandex" in SMTP_HOST.lower()


def _sender() -> str:
    """
    Адрес отправителя.
      • Яндекс: только SMTP_USER — иначе ошибка 553 «Sender address rejected».
      • Другие сервисы (SendGrid и т.п.): SMTP_FROM — у них логин не адрес
        (например, «apikey»), а отправитель должен быть подтверждён в кабинете сервиса.
    """
    if IS_YANDEX:
        return SMTP_USER
    return SMTP_FROM or SMTP_USER


if IS_YANDEX and SMTP_FROM and SMTP_FROM.lower() != SMTP_USER.lower():
    log.warning("[email] Яндекс: SMTP_FROM (%s) ≠ SMTP_USER — письма уйдут от %s", SMTP_FROM, SMTP_USER)


def _resolve_ipv4(host: str, port: int) -> str:
    """IPv4-адрес хоста (или сам host, если не нашли)."""
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        if infos:
            return infos[0][4][0]
    except OSError as e:
        log.warning("[email] Не удалось получить IPv4 для %s: %s", host, e)
    return host


class _SMTP_SSL_IPv4(smtplib.SMTP_SSL):
    """SMTP_SSL, который подключается к IPv4, но проверяет сертификат по имени хоста."""

    def __init__(self, host, port, **kw):
        self._real_host = host
        super().__init__(host, port, **kw)

    def _get_socket(self, host, port, timeout):
        target = _resolve_ipv4(host, port) if SMTP_FORCE_IPV4 else host
        sock = socket.create_connection((target, port), timeout, self.source_address)
        return self.context.wrap_socket(sock, server_hostname=self._real_host)


class _SMTP_IPv4(smtplib.SMTP):
    def _get_socket(self, host, port, timeout):
        target = _resolve_ipv4(host, port) if SMTP_FORCE_IPV4 else host
        return socket.create_connection((target, port), timeout, self.source_address)


def _attempts() -> list[tuple[str, int]]:
    """
    Порядок попыток: сначала настроенный способ, потом запасной.
    Некоторые хостинги закрывают 465 или 587 — второй порт часто открыт.
    """
    primary = ("starttls", SMTP_PORT) if SMTP_USE_TLS else ("ssl", SMTP_PORT)
    fallback = ("ssl", 465) if primary[0] == "starttls" else ("starttls", 587)
    return [primary] if primary == fallback else [primary, fallback]


def _send_once(mode: str, port: int, msg: EmailMessage, recipients: list[str]) -> None:
    context = ssl.create_default_context()
    if mode == "ssl":
        with _SMTP_SSL_IPv4(SMTP_HOST, port, timeout=SMTP_TIMEOUT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg, from_addr=_sender(), to_addrs=recipients)
    else:
        with _SMTP_IPv4(SMTP_HOST, port, timeout=SMTP_TIMEOUT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg, from_addr=_sender(), to_addrs=recipients)


def build_message(subject: str, body: str, recipients: list[str]) -> EmailMessage:
    msg = EmailMessage()
    # Кодируем заголовки через RFC 2047 — так эмодзи и кириллица
    # безопасно уходят на любой SMTP-сервер.
    msg["Subject"] = _encode_header(subject)
    msg["From"] = formataddr(("ILSATAO", _sender()), charset="utf-8")
    msg["To"] = ", ".join(formataddr(("", r), charset="utf-8") for r in recipients)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=(_sender().split("@")[-1] or "ilsatao.ru"))
    msg.set_content(body, charset="utf-8")
    return msg


def send_email(subject: str, body: str, to: str | None = None) -> bool:
    """
    Отправляет письмо. Возвращает True при успехе, False при ошибке.
    Никогда не бросает исключение — ошибки пишутся в лог контейнера
    (docker compose logs api).

    Ошибки сети (таймаут, обрыв) повторяются с паузой и запасным портом.
    Ошибка авторизации не повторяется — её надо исправлять в .env.
    """
    if not is_email_configured():
        log.warning("[email] SMTP не настроен — уведомления отключены")
        return False

    recipients = [r.strip() for r in (to or SMTP_TO).split(",") if r.strip()]
    if not recipients:
        log.warning("[email] Не указан получатель SMTP_TO")
        return False

    msg = build_message(subject, body, recipients)
    last_error: Exception | None = None

    for attempt in range(1, SMTP_RETRIES + 1):
        for mode, port in _attempts():
            try:
                _send_once(mode, port, msg, recipients)
                log.info("[email] Отправлено (%s:%s, попытка %s): '%s' → %s",
                         mode, port, attempt, subject, recipients)
                return True
            except smtplib.SMTPAuthenticationError as e:
                if IS_YANDEX:
                    log.error(
                        "[email] Яндекс отклонил логин/пароль (%s). Нужен ПАРОЛЬ ПРИЛОЖЕНИЯ "
                        "(id.yandex.ru → Безопасность → Пароли приложений → Почта), а SMTP_USER — "
                        "полный адрес. Также включите доступ почтовых программ в настройках Почты.",
                        e.smtp_code,
                    )
                else:
                    log.error("[email] Сервер отклонил логин/пароль (%s): проверьте SMTP_USER/SMTP_PASSWORD "
                              "(для SendGrid: SMTP_USER=apikey, SMTP_PASSWORD=API-ключ)", e.smtp_code)
                return False
            except smtplib.SMTPSenderRefused as e:
                log.error("[email] Отправитель отклонён (%s): %s", e.smtp_code, e.smtp_error)
                return False
            except (OSError, smtplib.SMTPException) as e:
                last_error = e
                log.warning("[email] %s:%s не удалось (попытка %s): %s: %s",
                            mode, port, attempt, type(e).__name__, e)
        if attempt < SMTP_RETRIES:
            time.sleep(2 * attempt)

    log.error("[email] Письмо не отправлено после %s попыток: %s", SMTP_RETRIES, last_error)
    return False


def notify_new_lead(lead: dict) -> None:
    """Уведомление о новой заявке. Вызывается из фоновой задачи."""
    # Убираем эмодзи из темы — не все SMTP любят их в заголовке.
    # Эмодзи можно оставить в теле письма, там они безопасны.
    subject = f"Новая заявка #{lead.get('id')} — ILSATAO"

    body = f"""🚗 Новая заявка с сайта ILSATAO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Заявка №{lead.get('id')}
  {lead.get('created_at', '')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 Телефон:        {lead.get('phone') or '—'}
💬 Способ связи:   {lead.get('contact_method') or '—'}
💰 Бюджет:         {lead.get('budget') or '—'}

📝 Предпочтения:
{lead.get('preferences') or '—'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Согласие на обработку: {'да' if lead.get('consent') else 'нет'}
Рассылка:              {'да' if lead.get('newsletter') else 'нет'}
Источник:              {lead.get('source') or '—'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Открыть в админке: {settings.SITE_URL.rstrip('/')}/admin/leads
"""

    send_email(subject, body)