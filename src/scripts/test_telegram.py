"""
Настройка и проверка уведомлений в Telegram.

    На сервере:  docker compose exec api python -m src.scripts.test_telegram
    Локально:    python -m src.scripts.test_telegram

1) Если TELEGRAM_CHAT_ID не задан — показывает чаты, которые писали боту
   (напишите боту /start или добавьте его в группу и напишите там что-нибудь),
   и подсказывает, что вписать в .env.
2) Если задан — отправляет тестовую заявку во все чаты.
"""
import logging
import sys

from src import telegram_notifier as tg

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> int:
    if not tg.TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN не задан в src/.env. Создайте бота у @BotFather (/newbot) и впишите токен.")
        return 1

    try:
        me = tg.api_call("getMe")
    except Exception as e:  # noqa: BLE001
        print(f"Не удалось связаться с Telegram ({tg.TELEGRAM_API_URL}): {e}")
        print("Проверьте токен. Если сервер не видит api.telegram.org — задайте TELEGRAM_API_URL (прокси-зеркало).")
        return 1
    print(f"Бот: @{me.get('username')} ({me.get('first_name')})")

    if not tg.chat_ids():
        print("\nTELEGRAM_CHAT_ID не задан. Чаты, которые писали боту:")
        try:
            updates = tg.api_call("getUpdates", {"limit": 100})
        except Exception as e:  # noqa: BLE001
            print(f"  getUpdates: {e}")
            return 1
        seen = {}
        for u in updates or []:
            m = u.get("message") or u.get("channel_post") or u.get("my_chat_member") or {}
            chat = m.get("chat") or {}
            if chat.get("id"):
                seen[chat["id"]] = chat.get("title") or " ".join(
                    x for x in (chat.get("first_name"), chat.get("last_name")) if x) or chat.get("username")
        if not seen:
            print(f"  Пусто. Откройте https://t.me/{me.get('username')} и нажмите «Старт» "
                  "(или добавьте бота в группу и напишите там), затем запустите скрипт снова.")
            return 1
        for cid, name in seen.items():
            print(f"  {cid}  —  {name}")
        print("\nВпишите нужный id в src/.env:  TELEGRAM_CHAT_ID=<id>  (несколько — через запятую)")
        return 0

    ok = tg.send_message(tg.build_lead_message({
        "id": 0, "source": "box", "phone": "+7 (900) 000-00-00", "contact_method": "Telegram",
        "budget": "1 990 ₽", "preferences": "Тестовое сообщение: уведомления о заявках работают ✅",
    }))
    print("Отправлено ✅" if ok else "Не отправлено — смотрите сообщения выше")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
