#!/bin/bash
# deploy.sh — Инсталация за мобилни устройства (UserLAnd/Termux)
# Работи с: VanGogo-max/-spot-grid-bot-android-
# ⚠️  Само за тестване! За 24/7 работа използвайте сървър + setup_bot.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Стартиране на инсталацията на спотовия бот...${NC}"
echo -e "${YELLOW}💡 Това е за мобилни устройства (тестов режим). За 24/7 работа използвайте сървър.${NC}"
sleep 2

# 1. Актуализация на пакетите
echo -e "${GREEN}[1/5] Актуализация на системата...${NC}"
apt update > /dev/null 2>&1 && apt upgrade -y > /dev/null 2>&1 || {
    echo -e "${YELLOW}⚠️  Пропускане на актуализация (може да изисква ръчно одобрение)${NC}"
}

# 2. Инсталация на зависимости
echo -e "${GREEN}[2/5] Инсталиране на Python и Git...${NC}"
apt install -y python3 python3-pip git wget > /dev/null 2>&1

# 3. Клониране на репото (ако липсва)
BOT_DIR="$HOME/-spot-grid-bot-android-"
if [ ! -d "$BOT_DIR" ]; then
    echo -e "${GREEN}[3/5] Клониране на репото...${NC}"
    git clone https://github.com/VanGogo-max/-spot-grid-bot-android-.git "$BOT_DIR" > /dev/null 2>&1
else
    echo -e "${GREEN}[3/5] Репото вече съществува. Актуализиране...${NC}"
    cd "$BOT_DIR" && git pull > /dev/null 2>&1
fi
cd "$BOT_DIR"

# 4. Инсталация на Python зависимости
echo -e "${GREEN}[4/5] Инсталиране на Python библиотеки...${NC}"
pip3 install --upgrade pip > /dev/null 2>&1
pip3 install requests==2.31.0 numpy==1.26.4 pandas ta python-telegram-bot > /dev/null 2>&1

# 5. Настройка на конфигурацията
echo -e "${GREEN}[5/5] Проверка на конфигурацията...${NC}"

# Ако няма config.py, създай от шаблона
if [ ! -f "config.py" ]; then
    if [ -f "config.example.py" ]; then
        cp config.example.py config.py
        echo -e "${YELLOW}⚠️  Създаден е файл config.py от шаблона.${NC}"
        echo -e "${YELLOW}📝 МОЛЯ, ПОПЪЛНЕТЕ ВАШИТЕ API КЛЮЧОВЕ В config.py:${NC}"
        echo -e "${YELLOW}   nano config.py${NC}"
        echo ""
        echo -e "${RED}🔒 ВАЖНО: НИКОГА НЕ КАЧВАЙТЕ config.py В GITHUB!${NC}"
        echo -e "${RED}   Той съдържа вашите лични ключове.${NC}"
        echo ""
        echo -e "${YELLOW}💡 Съвет: Използвайте само 'трейдинг' ключове без права за теглене.${NC}"
        echo -e "${YELLOW}   Активирайте 2FA на борсата.${NC}"
        echo ""
        read -p "Натиснете ENTER, за да отворите config.py за редакция..." 
        nano config.py
    else
        echo -e "${RED}❌ Липсва и config.example.py! Клонирайте отново репото.${NC}"
        exit 1
    fi
fi

# Проверка дали ключовете са попълнени (базова проверка)
if grep -q "YOUR_API_KEY_HERE\|ВАШ_" config.py; then
    echo -e "${YELLOW}⚠️  Изглежда ключовете в config.py все още не са попълнени.${NC}"
    echo -e "${YELLOW}   Редактирайте го преди да стартирате бота:${NC}"
    echo -e "${YELLOW}   nano config.py${NC}"
    echo ""
    read -p "Натиснете ENTER, за да продължите въпреки това (само за тестване)..." 
fi

# Стартиране на бота
echo ""
echo -e "${GREEN}✅ Инсталацията завърши успешно!${NC}"
echo -e "${GREEN}▶️  Стартиране на бота...${NC}"
echo ""
echo -e "${YELLOW}💡 Съвет за мобилни устройства:${NC}"
echo -e "${YELLOW}   - Оставете терминала отворен${NC}"
echo -e "${YELLOW}   - Не изключвайте екрана (настройте 'Никога' за автоматично изключване)${NC}"
echo -e "${YELLOW}   - За 24/7 работа препоръчваме сървър (setup_bot.sh)${NC}"
echo ""

python3 main.py
