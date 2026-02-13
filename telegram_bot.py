# telegram_bot.py
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(text):
    """
    Изпраща уведомление в Telegram.
    Работи дори ако ключовете не са попълнени (тихо пропуска грешките).
    """
    # Проверка за празни/шаблонни стойности
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    if "YOUR_" in TELEGRAM_BOT_TOKEN or "YOUR_" in TELEGRAM_CHAT_ID:
        return
    
    # 🔴 КРИТИЧНО: НЯМА ИНТЕРВАЛ след "bot"!
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text[:4096],  # Telegram ограничава до 4096 символа
        "parse_mode": "Markdown"
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        # Тихо пропускане на грешки – ботът не трябва да спира заради Telegram
        pass
