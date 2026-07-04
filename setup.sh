#!/usr/bin/env bash

# ==============================================================================
# MovieBot & Userbot Auto-Installer for Linux (Ubuntu/Debian)
# Ushbu skript barcha kerakli dastur va kutubxonalarni o'rnatib,
# botni systemctl orqali avtomatik ishga tushiradi.
# ==============================================================================

set -e

GREEN='\033[0;32m'
NC='\033[0m'
BOLD='\033[1m'
YELLOW='\033[1;33m'
RED='\033[0;31m'

echo -e "${BOLD}${GREEN}====================================================${NC}"
echo -e "${BOLD}${GREEN}   MovieBot & Userbot Avtomatik O'rnatish Skripti   ${NC}"
echo -e "${BOLD}${GREEN}====================================================${NC}"

# Root huquqini tekshirish
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[XATOLIK] Ushbu skriptni sudo yoki root bo'lib ishga tushiring!${NC}"
  echo -e "Masalan: ${BOLD}sudo bash setup.sh${NC}"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "📁 Loyiha papkasi: ${BOLD}${PROJECT_DIR}${NC}"

# 1. Tizim paketlarini yangilash va o'rnatish
echo -e "\n${YELLOW}[1/6] Linux paketlarini yangilash va zaruriy dasturlarni o'rnatish...${NC}"
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git ffmpeg sqlite3 curl build-essential

# 2. Python Virtual Environment (venv) yaratish
echo -e "\n${YELLOW}[2/6] Python venv virtual muhitini sozlash...${NC}"
if [ ! -d "${PROJECT_DIR}/venv" ]; then
    python3 -m venv "${PROJECT_DIR}/venv"
    echo -e "${GREEN}✓ venv yaratildi.${NC}"
else
    echo -e "${GREEN}✓ venv allaqachon mavjud.${NC}"
fi

# 3. Pip va kutubxonalarni o'rnatish
echo -e "\n${YELLOW}[3/6] Python paketlarini (requirements.txt) o'rnatish...${NC}"
"${PROJECT_DIR}/venv/bin/pip" install --upgrade pip
if [ -f "${PROJECT_DIR}/requirements.txt" ]; then
    "${PROJECT_DIR}/venv/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"
    echo -e "${GREEN}✓ Barcha Python kutubxonalari o'rnatildi.${NC}"
else
    echo -e "${RED}[XATOLIK] requirements.txt topilmadi!${NC}"
    exit 1
fi

# 4. .env sozlamalarini tekshirish va yaratish
echo -e "\n${YELLOW}[4/6] Config (.env) faylini tekshirish...${NC}"
ENV_FILE="${PROJECT_DIR}/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}.env fayli topilmadi. Yangi yaratilmoqda...${NC}"
    if [ -f "${PROJECT_DIR}/.env.example" ]; then
        cp "${PROJECT_DIR}/.env.example" "$ENV_FILE"
    else
        touch "$ENV_FILE"
    fi

    echo -e "${BOLD}"
    read -p "Telegram BOT_TOKEN kiritasizmi? (bo'sh qoldirsangiz keyin .env ga yozasiz): " INPUT_TOKEN
    read -p "Admin Telegram ID kiritasizmi? (masalan: 123456789): " INPUT_ADMINS
    echo -e "${NC}"

    if [ -n "$INPUT_TOKEN" ]; then
        echo "BOT_TOKEN=\"$INPUT_TOKEN\"" > "$ENV_FILE"
    fi
    if [ -n "$INPUT_ADMINS" ]; then
        echo "ADMIN_IDS=\"$INPUT_ADMINS\"" >> "$ENV_FILE"
    fi
    echo "APP_URL=\"http://localhost:3000\"" >> "$ENV_FILE"
    echo -e "${GREEN}✓ .env saqlandi.${NC}"
else
    echo -e "${GREEN}✓ .env fayli mavjud.${NC}"
fi

# 5. Systemd xizmatini (systemctl) yaratish
echo -e "\n${YELLOW}[5/6] Systemd xizmatini (moviebot.service) sozlash...${NC}"

SERVICE_FILE="/etc/systemd/system/moviebot.service"

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=MovieBot Telegram Bot & Userbot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile=${PROJECT_DIR}/.env

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ ${SERVICE_FILE} fayli yaratildi.${NC}"

# 6. Service ni qayta yuklash va ishga tushirish
echo -e "\n${YELLOW}[6/6] Systemctl servisini yoqish va ishga tushirish...${NC}"
systemctl daemon-reload
systemctl enable moviebot.service
systemctl restart moviebot.service

sleep 2

# Statusni ko'rsatish
if systemctl is-active --quiet moviebot.service; then
    STATUS_MSG="${GREEN}● ACTIVE (Ishlamoqda)${NC}"
else
    STATUS_MSG="${RED}● INACTIVE (To'xtalgan - .env va loglarni tekshiring)${NC}"
fi

echo -e "\n${BOLD}${GREEN}====================================================${NC}"
echo -e "${BOLD}${GREEN} 🎉 O'RNATISH VA ISHGA TUSHIRISH YAKUNLANDI! 🎉 ${NC}"
echo -e "${BOLD}${GREEN}====================================================${NC}\n"

echo -e " Holati: ${STATUS_MSG}"
echo -e " Bot statusini tekshirish uchun: ${BOLD}systemctl status moviebot${NC}"
echo -e " Jonli loglarni ko'rish uchun:   ${BOLD}journalctl -u moviebot -f${NC}"
echo -e " Botni qayta yoqish uchun:     ${BOLD}systemctl restart moviebot${NC}"
echo -e " Botni to'xtatish uchun:       ${BOLD}systemctl stop moviebot${NC}"

echo -e "\n${YELLOW}Eslatma:${NC} .env faylidagi BOT_TOKEN to'g'ri kiritilganiga ishonch hosil qiling!"
