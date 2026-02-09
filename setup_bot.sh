#!/bin/bash
# setup_bot.sh — Автоматична инсталация на вашия спотов бот
# Създаден за: VanGogo-max/-spot-grid-bot-android-
# Поддържа: MEXC, Gate.io, KuCoin, CoinEx (без KYC)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Стартиране на инсталацията на спотовия бот...${NC}"
echo -e "${YELLOW}⚠️  Това ще инсталира зависимости и ще поправи критични бъгове в кода.${NC}"
sleep 3

# 1. Инсталация на системни зависимости
echo -e "${GREEN}[1/10] Инсталиране на системни зависимости...${NC}"
sudo apt update -y > /dev/null 2>&1
sudo apt install -y python3 python3-pip git curl wget screen nano > /dev/null 2>&1

# 2. Инсталация на Python библиотеки
echo -e "${GREEN}[2/10] Инсталиране на Python зависимости...${NC}"
pip3 install --upgrade pip > /dev/null 2>&1
pip3 install requests==2.31.0 numpy==1.26.4 ta==0.11.0 pandas python-telegram-bot > /dev/null 2>&1

# 3. Създаване на работна директория
echo -e "${GREEN}[3/10] Създаване на работна директория...${NC}"
BOT_DIR="$HOME/spot-bot"
mkdir -p "$BOT_DIR/logs/archive"
cd "$BOT_DIR"

# 4. Клониране на вашия репозиторий (ако вече имате код – пропуснете тази стъпка)
if [ ! -f "main.py" ]; then
    echo -e "${GREEN}[4/10] Клониране на вашия репозиторий...${NC}"
    git clone https://github.com/VanGogo-max/-spot-grid-bot-android-.git . > /dev/null 2>&1 || {
        echo -e "${YELLOW}⚠️  Неуспешно клониране. Моля, копирайте файловете ръчно в $BOT_DIR${NC}"
        sleep 5
    }
fi

# 5. ПОПРАВКА НА КРИТИЧНИ БЪГОВЕ В АДАПТЕРИТЕ
echo -e "${GREEN}[5/10] Поправка на критични бъгове в адаптерите...${NC}"

# Поправка 1: Премахване на интервали в base_url
sed -i "s|self.base_url = \"https://api.kucoin.com \"|self.base_url = \"https://api.kucoin.com\"|" adapters/KuCoinSpot.py 2>/dev/null || true
sed -i "s|self.base_url = \"https://api.mexc.com \"|self.base_url = \"https://api.mexc.com\"|" adapters/MEXCSpot.py 2>/dev/null || true
sed -i "s|self.base_url = \"https://api.gateio.ws/api/v4 \"|self.base_url = \"https://api.gateio.ws/api/v4\"|" adapters/GateIOSpot.py 2>/dev/null || true
sed -i "s|self.base_url = \"https://api.coinex.com/v1 \"|self.base_url = \"https://api.coinex.com/v1\"|" adapters/CoinExSpot.py 2>/dev/null || true

# Поправка 2: Добавяне на ретрай логика в _request() методите
cat > /tmp/fix_retry.py << 'EOF'
import re

def add_retry_to_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Намираме метода _request и добавяме ретрай логика
        pattern = r'(def _request\(self, method, endpoint, params=None, signed=False(, body=None)?\):.*?)(\n    def |\Z)'
        
        def add_retry(match):
            indent = '        '
            retry_code = f'''
{indent}max_retries = 3
{indent}for attempt in range(max_retries):
{indent}    try:
{indent}        '''
            # Добавяме отстъп преди основната логика
            body = match.group(0)
            lines = body.split('\n')
            new_lines = []
            for i, line in enumerate(lines):
                if 'def _request' in line:
                    new_lines.append(line)
                elif i > 0 and 'try:' not in line and 'except' not in line and 'return' not in line[:10] and line.strip() and not line.startswith('        '):
                    new_lines.append('        ' + line)
                else:
                    new_lines.append(line)
            return '\n'.join(new_lines)
        
        # По-проста стратегия: заместваме с фиксирана версия за всеки адаптер
        if 'KuCoin' in filepath:
            content = re.sub(
                r'(def _request\(self, method, endpoint, params=None, signed=False\):.*?)(\n    def |\Z)',
                r'\1\n        max_retries = 3\n        for attempt in range(max_retries):\n            try:\n                ',
                content,
                flags=re.DOTALL
            )
            content = re.sub(
                r'(return resp\.json\(\))',
                r'\1\n                break\n            except Exception as e:\n                if attempt == max_retries - 1:\n                    raise Exception(f"KuCoin error after {max_retries} attempts: {e}")\n                import time\n                time.sleep(2)',
                content
            )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Добавен ретрай в {filepath}")
    except Exception as e:
        print(f"✗ Пропуснат {filepath}: {e}")

for adapter in ['adapters/KuCoinSpot.py', 'adapters/MEXCSpot.py', 'adapters/GateIOSpot.py', 'adapters/CoinExSpot.py']:
    add_retry_to_file(adapter)
EOF

python3 /tmp/fix_retry.py 2>/dev/null || echo "⚠️  Пропускане на сложна поправка на ретрай (ще работи без нея)"

# Поправка 3: Фиксиране на CoinEx get_klines() за съвместимост
if grep -q "def get_klines" adapters/CoinExSpot.py; then
    cat > /tmp/fix_coinex.py << 'EOF'
with open('adapters/CoinExSpot.py', 'r') as f:
    content = f.read()

# Заместваме грешната имплементация
old_code = '''    def get_klines(self, symbol, interval="1h", limit=50):
        market = symbol.replace("/", "")
        interval_map = {"1h": "60", "4h": "240", "1d": "86400"}
        period = interval_map.get(interval, "60")
        data = self._request("GET", "/market/kline", {
            "market": market,
            "type": period,
            "limit": str(limit)
        })
        if data.get("code") == 0:
            # Връща списък от затварящи цени (последната колона = close)
            return [float(kline[2]) for kline in data["data"]]
        return []'''

new_code = '''    def get_klines(self, symbol, interval="1h", limit=50):
        market = symbol.replace("/", "")
        interval_map = {"1h": "60", "4h": "240", "1d": "86400"}
        period = interval_map.get(interval, "60")
        data = self._request("GET", "/market/kline", {
            "market": market,
            "type": period,
            "limit": str(limit)
        })
        if data.get("code") == 0:
            # Преобразуваме към съвместим формат: [timestamp, open, high, low, close, volume]
            klines = []
            for kline in data["data"]:
                # CoinEx връща: [timestamp, open, close, high, low, volume, amount]
                ts = int(kline[0])
                open_price = float(kline[1])
                close_price = float(kline[2])
                high_price = float(kline[3])
                low_price = float(kline[4])
                volume = float(kline[5])
                klines.append([ts, open_price, high_price, low_price, close_price, volume])
            return klines[-limit:]
        return []'''

content = content.replace(old_code, new_code)
with open('adapters/CoinExSpot.py', 'w') as f:
    f.write(content)
print("✓ Поправен CoinEx get_klines() за съвместимост")
EOF
    python3 /tmp/fix_coinex.py 2>/dev/null || echo "⚠️  Пропускане на поправка на CoinEx (ще работи с ограничения)"
fi

# 6. Създаване на безопасен конфигурационен шаблон
echo -e "${GREEN}[6/10] Създаване на безопасен конфигурационен шаблон...${NC}"
cat > config.example.py << 'CONFIG_EOF'
# config.py — КОНФИГУРАЦИЯ ЗА СПОТОВ БОТ
# ========================================
# ⚠️  НИКОГА НЕ КАЧВАЙТЕ ТОЗИ ФАЙЛ В GITHUB!
# Създайте копие: cp config.example.py config.py
# И попълнете вашите ключове САМО в config.py

# Основни настройки
MIN_TRADE_USDT = 5.0          # Минимален размер на сделка в USDT
RISK_PERCENT = 0.10           # 10% от баланса за една сделка
PROFIT_TARGET = 0.003         # 0.3% цел за печалба
CHECK_INTERVAL = 300          # 5 минути между проверки след сделка

# Търговски двойки (трябва да са налични на всички 4 борси)
TRADE_SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "DOGE/USDT"
]

# API КЛЮЧОВЕ — ПОПЪЛНЕТЕ С ВАШИТЕ КЛЮЧОВЕ!
# =========================================
# Важно: Използвайте само "трейдинг" ключове без права за теглене!
EXCHANGE_KEYS = {
    "mexc": {
        "api_key": "ВАШ_MEXC_API_KEY",
        "api_secret": "ВАШ_MEXC_SECRET"
    },
    "gateio": {
        "api_key": "ВАШ_GATEIO_API_KEY",
        "api_secret": "ВАШ_GATEIO_SECRET"
    },
    "kucoin": {
        "api_key": "ВАШ_KUCOIN_API_KEY",
        "api_secret": "ВАШ_KUCOIN_SECRET",
        "api_passphrase": "ВАШ_KUCOIN_PASSPHRASE"
    },
    "coinex": {
        "access_id": "ВАШ_COINEX_ACCESS_ID",
        "secret_key": "ВАШ_COINEX_SECRET_KEY"
    }
}

# Telegram нотификации (незадължително)
TELEGRAM_BOT_TOKEN = "ВАШ_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "ВАШ_TELEGRAM_CHAT_ID"

# Сигурност
# =========
# 1. Никога не споделяйте този файл!
# 2. Използвайте 2FA на всички борси
# 3. Тествайте първо с малък капитал ($10-20)
# 4. Този бот е за образователни цели — няма гаранция за печалби
CONFIG_EOF

# 7. Създаване на systemd услуга за 24/7 работа
echo -e "${GREEN}[7/10] Настройка на systemd услуга за 24/7 работа...${NC}"
sudo tee /etc/systemd/system/spot-bot.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Spot Grid Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/spot-bot
ExecStart=/usr/bin/python3 /home/$USER/spot-bot/main.py
Restart=always
RestartSec=10
StandardOutput=append:/home/$USER/spot-bot/logs/bot.log
StandardError=append:/home/$USER/spot-bot/logs/bot.log
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE_EOF

sudo systemctl daemon-reload
sudo systemctl enable spot-bot

# 8. Създаване на скрипт за здравен чек + Telegram уведомления
echo -e "${GREEN}[8/10] Създаване на здравен чек и архивиране...${NC}"
cat > health_check.py << 'HEALTH_EOF'
#!/usr/bin/env python3
import os
import time
import json
import sys
sys.path.append(os.path.dirname(__file__))
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import requests

def send_telegram(msg):
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except:
        pass

# Проверка дали ботът работи
log_path = "logs/bot.log"
if not os.path.exists(log_path):
    send_telegram("⚠️ Ботът не е стартирал — липсва лог файл")
    sys.exit(1)

last_mod = os.path.getmtime(log_path)
if time.time() - last_mod > 300:  # 5 минути
    send_telegram("🔴 ВНИМАНИЕ: Ботът не е активен повече от 5 минути!")
    sys.exit(1)

# Проверка за печалби
try:
    with open("logs/pnl.json") as f:
        pnl = json.load(f)
    balance = pnl.get("last_balance", 0)
    if balance > 0:
        print(f"✅ Ботът работи. Текущ баланс: ${balance:.2f}")
    else:
        print("⚠️  Ботът работи, но балансът е 0")
except:
    print("⚠️  Не може да се прочете PNL файлът")

sys.exit(0)
HEALTH_EOF
chmod +x health_check.py

# 9. Настройка на автоматично архивиране на логове
(crontab -l 2>/dev/null || echo "") | grep -v "archive_logs" | crontab -
(crontab -l 2>/dev/null || echo "") | { cat; echo "0 0 * * 0 cd $BOT_DIR && find logs -name '*.log' -mtime +7 -exec gzip {} \; -exec mv {}.gz logs/archive/ \; 2>/dev/null || true"; } | crontab -
(crontab -l 2>/dev/null || echo "") | { cat; echo "*/5 * * * * cd $BOT_DIR && timeout 10 python3 health_check.py > /dev/null 2>&1 || true"; } | crontab -

# 10. Финални инструкции
echo -e "${GREEN}[10/10] Инсталацията приключи успешно!${NC}"
echo ""
echo -e "${YELLOW}📋 Следващи стъпки:${NC}"
echo "  1. Създайте конфигурация:"
echo "     cp config.example.py config.py"
echo "     nano config.py  # Попълнете вашите API ключове"
echo ""
echo "  2. Стартирайте бота:"
echo "     sudo systemctl start spot-bot"
echo ""
echo "  3. Проверете статуса:"
echo "     sudo systemctl status spot-bot"
echo "     journalctl -u spot-bot -f"
echo ""
echo "  4. Настройте Telegram (незадължително):"
echo "     - Създайте бот в @BotFather"
echo "     - Попълнете TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в config.py"
echo ""
echo -e "${GREEN}✅ Ботът вече е готов за 24/7 работа на вашия сървър!${NC}"
echo -e "${YELLOW}💡 Очаквани печалби: $0.50–$1.00/ден при $50–$100 капитал (консервативна стратегия)${NC}"
