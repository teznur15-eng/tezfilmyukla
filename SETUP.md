# 🎬 MovieBot & Userbot — Linux (Ubuntu/Debian) O'rnatish Qo'llanmasi

Ushbu loyiha **Asilmedia**, **UzMovie**, **Kinolar.tv** va boshqa manbalardan kinolarni avtomatik skanerlab, Telegram foydalanuvchilariga yetkazuvchi va **Userbot (Telethon)** orqali **50MB dan katta fayllarni** ham uzatuvchi professional Telegram bot tizimidir.

---

## ⚡ 1-Usul: Bitta Buyruq Bilan Avtomatik O'rnatish (Tavsiya etiladi)

Serveringizga (Ubuntu 20.04 / 22.04 / 24.04 / Debian) `ssh` orqali kiring va loyiha papkasida quyidagi buyruqni ishga tushiring:

```bash
sudo bash setup.sh
```

### `setup.sh` skripti avtomatik nimalar qiladi:
1. Linux paketlarini yangilaydi (`apt-get update`)
2. `python3`, `pip`, `venv`, `ffmpeg`, `sqlite3`, `git`, `build-essential` va barcha zaruriy kutubxonalarni o'rnatadi.
3. Python `venv` virtual muhitini yaratadi.
4. `requirements.txt` dagi barcha paketlarni (`python-telegram-bot`, `telethon`, `aiohttp`, `beautifulsoup4`, va h.k.) o'rnatadi.
5. `.env` faylini yaratib, sizdan `BOT_TOKEN` va `ADMIN_IDS` so'raydi.
6. `/etc/systemd/system/moviebot.service` faylini hosil qilib, **systemctl** ga qo'shadi.
7. Botni avtomatik ishga tushiradi va server o'chib-yonishida avto-start rejimiga qo'yadi (`Restart=always`).

---

## 🛠 2-Usul: Qo'lda (Manual) O'rnatish Bosqichlari

Agar skriptsiz qo'lda o'rnatmoqchi bo'lsangiz:

### 1. Tizim paketlarini o'rnatish
```bash
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git ffmpeg sqlite3 curl build-essential
```

### 2. Virtual muhit yaratish va aktivlashtirish
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Python kutubxonalarini o'rnatish
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. `.env` faylini sozlash
`.env` faylini yarating yoki tahrirlang:
```bash
nano .env
```

Tarkibi:
```env
BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ"
ADMIN_IDS="123456789,987654321"
APP_URL="http://localhost:3000"
```

### 5. Systemd xizmatini yaratish (`/etc/systemd/system/moviebot.service`)
```bash
sudo nano /etc/systemd/system/moviebot.service
```

Quyidagi matnni qo'ying (papkalar yo'lini o'zingizniki bilan almashtiring):
```ini
[Unit]
Description=MovieBot Telegram Bot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/moviebot
ExecStart=/var/www/moviebot/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile=/var/www/moviebot/.env

[Install]
WantedBy=multi-user.target
```

### 6. Service ni yoqish va ishga tushirish
```bash
sudo systemctl daemon-reload
sudo systemctl enable moviebot
sudo systemctl start moviebot
```

---

## 📋 Systemctl Buyruqlari va Boshqaruv

Botni serverda boshqarish uchun quyidagi buyruqlardan foydalaning:

* **Bot statusini ko'rish:**
  ```bash
  sudo systemctl status moviebot
  ```

* **Jonli konsol loglarini ko'rish:**
  ```bash
  sudo journalctl -u moviebot -f
  ```

* **Botni qayta yoqish (Restart):**
  ```bash
  sudo systemctl restart moviebot
  ```

* **Botni to'xtatish:**
  ```bash
  sudo systemctl stop moviebot
  ```

---

## 🔐 50MB+ Katta Fayllar Uchun Userbot Ulash (Telethon)

Telegram Bot API oddiy botlarga **max 50MB** fayl yuborishga ruxsat beradi. 
Bizning botimizda **Userbot** tizimi integratsiya qilingan:

1. Telegram botingizda `/connect_api` buyrug'ini yuboring.
2. [my.telegram.org](https://my.telegram.org) saytiga kirib, **API development tools** bo'limidan `api_id` va `api_hash` oling.
3. Bot so'raganida `api_id`, `api_hash`, telefon raqamingiz va Telegram'ga kelgan tasdiqlash kodini kiriting.
4. Telethon seans kaliti (`StringSession`) SQLite ma'lumotlar bazasiga saqlanadi.
5. Endi **50MB dan 2GB gacha** bo'lgan kinolar ham to'g'ridan to'g'ri Telegram foydalanuvchilariga muvaffaqiyatli yuboriladi!

---

## 👑 Admin Panel va Buyruqlar

* `/admin` — HTML Tugmali boshqaruv paneli (Tariflar, Kartalar, Statistika, To'lovlar, Shikoyatlar, Reklama post yuborish).
* `/connect_api` — Userbot ulanish paneli.
* `/disconnect` — Userbotni uzish.
* `/ban [user_id]` — Foydalanuvchini bloklash.
* `/unban [user_id]` — Blokdan chiqarish.
* `/sub [user_id] [kun]` — Qo'lda obuna berish.
* `/addadmin [user_id]` — Yangi admin qo'shish.
* `/removeadmin [user_id]` — Adminlikdan olish.
