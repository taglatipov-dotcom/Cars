import os
import smtplib
import ssl
from email.header import Header
from email.message import EmailMessage
from email.utils import formataddr
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
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_TO = os.getenv("SMTP_TO", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "false").lower() in ("1", "true", "yes")


def is_email_configured() -> bool:
    """True, если все обязательные настройки SMTP заданы."""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_TO)


def _encode_header(value: str) -> str:
    """
    Кодирует заголовок письма в RFC 2047, чтобы корректно
    переносить кириллицу и эмодзи (например: =?utf-8?b?...?=).
    """
    return Header(value, "utf-8").encode()


def send_email(subject: str, body: str, to: str | None = None) -> bool:
    """
    Отправляет письмо. Возвращает True при успехе, False при ошибке.
    Никогда не бросает исключение — все ошибки логируются в stdout.
    """
    if not is_email_configured():
        print("[email] SMTP не настроен — уведомления отключены")
        return False

    recipients = [r.strip() for r in (to or SMTP_TO).split(",") if r.strip()]
    if not recipients:
        print("[email] Не указан получатель SMTP_TO")
        return False

    msg = EmailMessage()
    # Кодируем заголовки через RFC 2047 — так эмодзи и кириллица
    # безопасно уходят на любой SMTP-сервер.
    msg["Subject"] = _encode_header(subject)
    msg["From"] = formataddr(("ILSATAO", SMTP_FROM), charset="utf-8")
    msg["To"] = ", ".join(
        formataddr(("", r), charset="utf-8") for r in recipients
    )

    # Тело письма — обычный текст, кодируем в UTF-8 автоматически
    msg.set_content(body, charset="utf-8")

    try:
        if SMTP_USE_TLS:
            # STARTTLS (порт 587)
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg, from_addr=SMTP_FROM, to_addrs=recipients)
        else:
            # SSL (порт 465)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20, context=context) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg, from_addr=SMTP_FROM, to_addrs=recipients)

        print(f"[email] Отправлено: '{subject}' → {recipients}")
        return True
    except Exception as e:
        print(f"[email] Ошибка отправки: {type(e).__name__}: {e}")
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