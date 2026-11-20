"""
Уведомления о новых заявках в Telegram (через Bot API, без сторонних библиотек).

Настройки в src/.env:
    TELEGRAM_BOT_TOKEN   токен бота от @BotFather
    TELEGRAM_CHAT_ID     куда слать: id чата/группы/канала; несколько — через запятую
    TELEGRAM_API_URL     (необязательно) адрес Bot API, если api.telegram.org недоступен
                         с сервера — например, свой прокси-зеркало. По умолчанию https://api.telegram.org

Узнать chat id и проверить отправку:
    docker compose exec api python -m src.scripts.test_telegram

Как и почта: вызывается в BackgroundTasks, никогда не бросает исключение —
ошибки пишутся в лог (docker compose logs api). Заявка сохраняется в любом случае.
"""
import html
import json
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from src.config import settings

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org").rstrip("/")
TELEGRAM_TIMEOUT = int(os.getenv("TELEGRAM_TIMEOUT", "10"))
TELEGRAM_RETRIES = int(os.getenv("TELEGRAM_RETRIES", "3"))

log = logging.getLogger("telegram")

# Раздел сайта по полю source заявки (как в админке, AdminLeads.jsx → LEAD_SECTIONS)
SECTIONS = {
    "box": "🎁 Новогодние боксы",
    "bags": "👜 Сумки",
}
CARS_SECTION = "🚗 Авто"

CLIENT_TYPES = {
    "company": "Компания (автопарк)",
    "dealer": "Дилер / перекупщик",
    "showroom": "Автосалон / площадка",
    "person": "Частное лицо",
}


def is_telegram_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def chat_ids() -> list[str]:
    return [c.strip() for c in TELEGRAM_CHAT_ID.split(",") if c.strip()]


def api_call(method: str, payload: dict | None = None) -> dict:
    """Вызов Bot API. Бросает исключение при сетевой ошибке или ok=false."""
    url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/{method}"
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TELEGRAM_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Telegram отвечает JSON с описанием ошибки и на 4xx
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            raise RuntimeError(f"HTTP {e.code}") from e
    if not body.get("ok"):
        raise RuntimeError(f"{body.get('error_code')}: {body.get('description')}")
    return body.get("result")


def send_message(text: str, buttons: list[tuple[str, str]] | None = None) -> bool:
    """
    Отправляет HTML-сообщение во все TELEGRAM_CHAT_ID. True — если дошло хотя бы в один чат.
    Сетевые ошибки повторяются; ошибки вида «чат не найден / бот заблокирован» — нет.
    """
    if not is_telegram_configured():
        log.info("[telegram] Не настроен (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID) — пропускаем")
        return False

    payload_base = {"text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if buttons:
        payload_base["reply_markup"] = {"inline_keyboard": [[{"text": t, "url": u} for t, u in buttons]]}

    sent_any = False
    for chat in chat_ids():
        payload = {**payload_base, "chat_id": chat}
        for attempt in range(1, TELEGRAM_RETRIES + 1):
            try:
                api_call("sendMessage", payload)
                log.info("[telegram] Отправлено в %s", chat)
                sent_any = True
                break
            except RuntimeError as e:
                msg = str(e)
                # Кнопка с адресом localhost/http Telegram не принимает — шлём без неё
                if "reply_markup" in payload and ("button" in msg.lower() or "url" in msg.lower()):
                    payload = {k: v for k, v in payload.items() if k != "reply_markup"}
                    continue
                if msg.startswith(("400", "401", "403", "404")):
                    log.error("[telegram] Чат %s: %s. Проверьте TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID и что боту "
                              "написали /start (для группы — бот добавлен в группу).", chat, msg)
                    break
                log.warning("[telegram] Чат %s, попытка %s: %s", chat, attempt, msg)
            except (OSError, ValueError) as e:
                log.warning("[telegram] Чат %s, попытка %s: %s: %s", chat, attempt, type(e).__name__, e)
            if attempt < TELEGRAM_RETRIES:
                time.sleep(2 * attempt)
        else:
            log.error("[telegram] Не отправлено в %s после %s попыток", chat, TELEGRAM_RETRIES)
    return sent_any


def _e(v) -> str:
    return html.escape(str(v)) if v not in (None, "") else "—"


def build_lead_message(lead: dict) -> str:
    source = lead.get("source")
    section = SECTIONS.get(source, CARS_SECTION)
    lines = [
        f"<b>{section} · заявка №{_e(lead.get('id'))}</b>",
        "",
        f"📞 <b>{_e(lead.get('phone'))}</b>",
        f"💬 Связь: {_e(lead.get('contact_method'))}",
    ]
    if source not in SECTIONS:
        # поля сайта авто (B2B)
        lines += [
            f"👥 Клиент: {_e(CLIENT_TYPES.get(lead.get('client_type'), lead.get('client_type')))}",
        ]
        if lead.get("company"):
            lines.append(f"🏢 {_e(lead.get('company'))}" + (f", ИНН {_e(lead.get('inn'))}" if lead.get("inn") else ""))
        if lead.get("quantity"):
            lines.append(f"🚘 Количество: {_e(lead.get('quantity'))}")
    if lead.get("budget"):
        lines.append(f"💰 {'Сумма' if source in SECTIONS else 'Бюджет'}: <b>{_e(lead.get('budget'))}</b>")
    prefs = (lead.get("preferences") or "").strip()
    if prefs:
        if len(prefs) > 3000:  # лимит сообщения Telegram — 4096 символов
            prefs = prefs[:3000] + "…"
        lines += ["", f"<blockquote expandable>{html.escape(prefs)}</blockquote>" if len(prefs) > 400
                  else html.escape(prefs)]
    return "\n".join(lines)


def notify_new_lead_telegram(lead: dict) -> None:
    """Фоновая задача из leads_router.create_lead."""
    admin_url = f"{settings.SITE_URL.rstrip('/')}/admin/leads"
    buttons = [("Открыть заявки", admin_url)] if admin_url.startswith("https://") else None
    send_message(build_lead_message(lead), buttons)
