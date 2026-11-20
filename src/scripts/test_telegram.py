"""
Настройка и проверка публикации заявок в Telegram-канал.

    На сервере:  docker compose exec api python -m src.scripts.test_telegram
    Локально:    python -m src.scripts.test_telegram

1) Если TELEGRAM_CHANNEL не задан — показывает каналы, где бот видел публикации,
   и подсказывает, что вписать в .env. (Добавьте бота администратором канала
   и опубликуйте в канале любое сообщение — тогда канал появится в списке.)
2) Если задан — публикует в канал тестовую заявку.
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
    print(f"Бот: @{me.get('username')}")

    if not tg.TELEGRAM_CHANNEL:
        print("\nTELEGRAM_CHANNEL не задан. Каналы, которые видит бот:")
        try:
            updates = tg.api_call("getUpdates", {"limit": 100, "allowed_updates": ["channel_post", "my_chat_member"]})
        except Exception as e:  # noqa: BLE001
            print(f"  getUpdates: {e}")
            return 1
        channels = {}
        for u in updates or []:
            chat = (u.get("channel_post") or u.get("my_chat_member") or {}).get("chat") or {}
            if chat.get("type") == "channel":
                channels[chat["id"]] = (chat.get("title"), chat.get("username"))
        if not channels:
            print("  Пусто. Добавьте бота в канал АДМИНИСТРАТОРОМ (право «Публикация сообщений»),\n"
                  "  опубликуйте в канале любое сообщение и запустите скрипт снова.")
            return 1
        for cid, (title, username) in channels.items():
            alt = f"   (или @{username})" if username else ""
            print(f"  {cid}  —  {title}{alt}")
        print("\nВпишите в src/.env:  TELEGRAM_CHANNEL=<id канала>  и запустите скрипт ещё раз.")
        return 0

    ok = tg.send_message(tg.build_lead_message({
        "id": 0, "source": "box", "phone": "+7 (900) 000-00-00", "contact_method": "Telegram",
        "budget": "1 990 ₽", "preferences": "Тестовая заявка: публикация в канал работает ✅",
    }))
    print("Опубликовано в канал ✅" if ok else "Не опубликовано — смотрите сообщения выше")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
