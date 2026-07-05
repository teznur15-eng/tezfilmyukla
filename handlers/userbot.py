"""
Userbot (Telethon) ulash va boshqarish.
Foydalanuvchi o'z Telegram accountini ulaydi — katta fayllar (50MB+) uchun ishlatiladi.
"""

import re
import time
import asyncio
import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.database import (
    save_userbot_session, get_userbot_session, disconnect_userbot, upsert_user
)

logger = logging.getLogger(__name__)
H = ParseMode.HTML

# Foydalanuvchi holatlari
userbot_states: dict = {}   # user_id -> state_name
userbot_temp:   dict = {}   # user_id -> temp data


def esc(t: str) -> str:
    return html.escape(str(t or ""))


# ─── Userbot Menyu Callbacklar ────────────────────────────

async def show_userbot_menu_panel(q_or_msg, user, context: ContextTypes.DEFAULT_TYPE):
    existing = get_userbot_session(user.id)
    if existing:
        text = (
            f"🔐 <b>Userbot Holati: 🟢 Ulangan</b>\n\n"
            f"📱 <b>Telefon:</b> <code>{esc(existing['phone'])}</code>\n"
            f"📅 <b>Ulangan vaqti:</b> {existing.get('created_at', '—')}\n\n"
            f"✅ <b>50MB dan 2GB gacha</b> bo'lgan barcha kinolarni o'zingizning Telegram accountingiz "
            f"orqali to'g'ridan to'g'ri Saqlangan xabarlar (Saved Messages) papkangizga bepul va cheksiz yuklab olishingiz mumkin!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Qayta ulash", callback_data="ub_connect_start")],
            [InlineKeyboardButton("🔴 Userbotni uzish", callback_data="disconnect_userbot")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]
        ])
    else:
        text = (
            f"🔐 <b>Userbot Tizimi (50MB+ Katta fayllar uchun)</b>\n\n"
            f"Telegram Bot API oddiy botlarga max 50MB fayl yuborishga ruxsat beradi.\n"
            f"<b>Userbot</b> esa shaxsiy Telegram accountingiz kuchi bilan <b>2GB gacha</b> kinolarni yuklab beradi!\n\n"
            f"❓ <b>Ulash osonmi?</b>\n"
            f"Ha! Atigi 1 daqiqa vaqt oladi.\n\n"
            f"👇 Quyidagi tugmani bosing va ko'rsatmalarga amal qiling:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Userbotni ulash (Boshlash)", callback_data="ub_connect_start")],
            [InlineKeyboardButton("📖 Qo'llanma (my.telegram.org)", callback_data="ub_guide")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]
        ])

    if hasattr(q_or_msg, "edit_message_text"):
        await q_or_msg.edit_message_text(text, parse_mode=H, reply_markup=kb, disable_web_page_preview=True)
    else:
        await q_or_msg.reply_text(text, parse_mode=H, reply_markup=kb, disable_web_page_preview=True)


async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, user.username or "", user.full_name or "")
    await show_userbot_menu_panel(update.message, user, context)


async def disconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    disconnect_userbot(user.id)
    userbot_states.pop(user.id, None)
    userbot_temp.pop(user.id, None)
    await update.message.reply_text(
        "✅ <b>Userbot muvaffaqiyatli uzildi!</b>\n\nQayta ulash uchun /connect_api yuboring.",
        parse_mode=H
    )


async def start_ub_connect(q, user):
    userbot_states[user.id] = "waiting_api_id"
    userbot_temp[user.id]   = {}

    text = (
        "🔐 <b>Userbot ulash — 1-Bosqich</b>\n\n"
        "1. <a href='https://my.telegram.org'>my.telegram.org</a> saytiga kiring\n"
        "2. Telefon raqamingizni kiriting va kelgan kodni yozing\n"
        "3. <b>API development tools</b> ga o'ting\n"
        "4. Ixtiyoriy nom va qisqa nom yozib, <b>Create application</b> bosing\n"
        "5. Hosil bo'lgan <b>api_id</b> ni nusxalab bering!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 <b>API ID</b> ni chatga yozib yuboring:\n"
        "<i>Masalan: 12345678</i>"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="ub_cancel")]])
    await q.edit_message_text(text, parse_mode=H, reply_markup=kb, disable_web_page_preview=True)


# ─── Userbot jarayoni message handler ────────────────────

async def userbot_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Userbot ulanish jarayonidagi xabarlarni qayta ishlash.
    True qaytarsa — xabar bu handler tomonidan qabul qilindi.
    """
    user  = update.effective_user
    msg   = update.message
    state = userbot_states.get(user.id)

    if not state:
        return False

    text = (msg.text or "").strip()
    contact = msg.contact

    # ── API ID ──────────────────────────────────────────
    if state == "waiting_api_id":
        if not text.isdigit():
            await msg.reply_text(
                "❌ API ID faqat raqamlardan iborat bo'lishi kerak.\nQaytadan kiriting:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="ub_cancel")]])
            )
            return True
        userbot_temp[user.id]["api_id"] = text
        userbot_states[user.id] = "waiting_api_hash"
        await msg.reply_text(
            f"✅ API ID: <code>{esc(text)}</code> saqlandi!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>API Hash</b> ni yuboring:\n"
            f"<i>Masalan: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6</i>",
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="ub_cancel")]])
        )
        return True

    # ── API Hash ─────────────────────────────────────────
    if state == "waiting_api_hash":
        if len(text) < 10:
            await msg.reply_text("❌ API Hash juda qisqa. Qaytadan kiriting:")
            return True
        userbot_temp[user.id]["api_hash"] = text
        userbot_states[user.id] = "waiting_phone"

        # Telefon raqamini ulash tugmasi bilan birga yuborish
        contact_kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Telefon raqamimni yuborish", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await msg.reply_text(
            f"✅ API Hash saqlandi!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 <b>Endi Telegram telefon raqamingizni yuboring:</b>\n\n"
            f"Tugmani bosing yoki chatga qo'lda yozing:\n"
            f"<i>Format: +998901234567</i>",
            parse_mode=H,
            reply_markup=contact_kb
        )
        return True

    # ── Telefon raqami ───────────────────────────────────
    if state == "waiting_phone":
        phone = ""
        if contact and contact.phone_number:
            phone = contact.phone_number
        elif text:
            phone = text.replace(" ", "").replace("-", "")

        if not phone or not re.match(r"^\+?\d{10,15}$", phone):
            await msg.reply_text(
                "❌ Noto'g'ri telefon format.\n"
                "Quyidagi tugmani bosing yoki to'g'ri yozing: <code>+998901234567</code>",
                parse_mode=H
            )
            return True

        if not phone.startswith("+"):
            phone = "+" + phone
        userbot_temp[user.id]["phone"] = phone

        wait = await msg.reply_text("⏳ Telegram'ga kod so'rovi yuborilmoqda...", reply_markup=ReplyKeyboardRemove())
        success, err = await _send_code(user.id)
        if not success:
            await wait.edit_text(
                f"❌ Kod yuborishda xatolik yuz berdi:\n<code>{esc(err)}</code>\n\n"
                f"API ID va API Hash to'g'riligini tekshiring.\nQayta boshlash uchun /connect_api bosing.",
                parse_mode=H
            )
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
        else:
            userbot_states[user.id] = "waiting_code"
            await wait.edit_text(
                f"📩 Telegram'ingizga <b>rasmiy tasdiqlash kodi</b> keldi!\n\n"
                f"Kodni chatga kiriting. <i>Agar xavfsizlik uchun kod kelmasa raqamlar orasiga nuqta qo'ying:</i>\n"
                f"<code>1.2.3.4.5</code>",
                parse_mode=H
            )
        return True

    # ── Tasdiqlash kodi ──────────────────────────────────
    if state == "waiting_code":
        code = text.replace(".", "").replace(" ", "")
        if not code.isdigit():
            await msg.reply_text("❌ Kod faqat raqamlardan iborat. Qaytadan kiriting:")
            return True
        wait = await msg.reply_text("⏳ Kirish tekshirilmoqda...")
        result, err = await _sign_in(user.id, code)
        if result == "ok":
            await wait.edit_text(
                "🎉 <b>Userbot muvaffaqiyatli ulandi!</b>\n\n"
                "Endi 50MB dan 2GB gacha bo'lgan kinolarni bemalol yuklay olasiz!",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]])
            )
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
        elif result == "2fa":
            userbot_states[user.id] = "waiting_password"
            await wait.edit_text(
                "🔒 <b>Ikki bosqichli tasdiqlash (2FA Passcode)</b>\n\n"
                "Telegram parolingizni yuboring:",
                parse_mode=H
            )
        else:
            await wait.edit_text(
                f"❌ Kod xatosi: <code>{esc(err)}</code>\n\n"
                f"Qaytadan urinish uchun /connect_api yuboring.",
                parse_mode=H
            )
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
        return True

    # ── 2FA paroli ──────────────────────────────────────
    if state == "waiting_password":
        wait = await msg.reply_text("⏳ Parol tekshirilmoqda...")
        result, err = await _sign_in_2fa(user.id, text)
        if result == "ok":
            await wait.edit_text(
                "🎉 <b>Userbot ulandi (2FA bilan)!</b>\n\n"
                "Katta kinolarni yuklash imkoniyati yoqildi.",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]])
            )
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
        else:
            await wait.edit_text(
                f"❌ 2FA Parol xatosi: <code>{esc(err)}</code>\n\nQaytadan: /connect_api",
                parse_mode=H
            )
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
        return True

    return False


# ─── Telethon operatsiyalari ──────────────────────────────

async def _send_code(user_id: int) -> tuple[bool, str]:
    temp = userbot_temp.get(user_id, {})
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        api_id   = int(temp["api_id"])
        api_hash = temp["api_hash"]
        phone    = temp["phone"]

        session = StringSession()
        client = TelegramClient(session, api_id, api_hash)
        await client.connect()
        result = await client.send_code_request(phone)
        userbot_temp[user_id]["phone_code_hash"] = result.phone_code_hash
        userbot_temp[user_id]["session_obj"]     = session
        userbot_temp[user_id]["client_ref"]      = client
        return True, ""
    except Exception as e:
        logger.error(f"Send code error: {e}")
        return False, str(e)[:200]


async def _sign_in(user_id: int, code: str) -> tuple[str, str]:
    temp = userbot_temp.get(user_id, {})
    try:
        from telethon import TelegramClient
        from telethon.errors import SessionPasswordNeededError
        from telethon.sessions import StringSession

        client: TelegramClient = temp.get("client_ref")
        session: StringSession = temp.get("session_obj")

        if not client:
            api_id   = int(temp["api_id"])
            api_hash = temp["api_hash"]
            session  = StringSession()
            client   = TelegramClient(session, api_id, api_hash)
            await client.connect()

        phone           = temp["phone"]
        phone_code_hash = temp.get("phone_code_hash", "")
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        except SessionPasswordNeededError:
            userbot_temp[user_id]["client_ref"]  = client
            userbot_temp[user_id]["session_obj"] = session
            return "2fa", ""

        session_str = session.save()
        save_userbot_session(
            user_id,
            str(temp["api_id"]),
            temp["api_hash"],
            phone,
            session_str
        )
        await client.disconnect()
        return "ok", ""
    except Exception as e:
        logger.error(f"Sign in error: {e}")
        return "error", str(e)[:200]


async def _sign_in_2fa(user_id: int, password: str) -> tuple[str, str]:
    temp = userbot_temp.get(user_id, {})
    try:
        from telethon import TelegramClient

        client: TelegramClient = temp.get("client_ref")
        session = temp.get("session_obj")

        if not client:
            return "error", "Client topilmadi. /connect_api qaytadan boshlang."

        await client.sign_in(password=password)
        session_str = session.save()
        save_userbot_session(
            user_id,
            str(temp["api_id"]),
            temp["api_hash"],
            temp["phone"],
            session_str
        )
        await client.disconnect()
        return "ok", ""
    except Exception as e:
        logger.error(f"2FA sign in error: {e}")
        return "error", str(e)[:200]


async def get_telethon_client(user_id: int):
    session_row = get_userbot_session(user_id)
    if not session_row or not session_row.get("session_string"):
        return None
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        client = TelegramClient(
            StringSession(session_row["session_string"]),
            int(session_row["api_id"]),
            session_row["api_hash"]
        )
        await client.connect()
        if await client.is_user_authorized():
            return client
        await client.disconnect()
    except Exception as e:
        logger.error(f"Telethon client error: {e}")
    return None


async def upload_file_via_userbot(user_id: int, target_chat: int | str, filepath: str, caption: str = "", progress_cb=None) -> tuple[bool, int, str]:
    """
    Userbot orqali 50MB dan katta fayllarni yuboradi va real-time callback taqdim etadi.
    Returns: (success, message_id, error_str)
    """
    client = await get_telethon_client(user_id)
    if not client:
        return False, 0, "Userbot ulanmagan"

    try:
        start_time = time.time()
        last_update = [start_time, 0]

        def callback(current, total):
            if progress_cb and total > 0:
                now = time.time()
                dt = now - last_update[0]
                if dt >= 0.8 or current == total:
                    speed = (current - last_update[1]) / dt if dt > 0 else 0
                    elapsed = now - start_time
                    pct = (current / total) * 100
                    last_update[0] = now
                    last_update[1] = current
                    try:
                        asyncio.create_task(progress_cb(current, total, pct, speed, elapsed))
                    except Exception:
                        pass

        msg = await client.send_file(
            target_chat,
            filepath,
            caption=caption,
            progress_callback=callback,
            parse_mode="html"
        )
        msg_id = msg.id if msg else 0
        file_id = f"ub_doc_{msg_id}"
        await client.disconnect()
        return True, msg_id, file_id
    except Exception as e:
        logger.error(f"Userbot upload error: {e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return False, 0, str(e)

