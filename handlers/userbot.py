"""
Userbot (Telethon) ulash va boshqarish.
Foydalanuvchi o'z Telegram accountini ulaydi — katta fayllar (50MB+) uchun ishlatiladi.
"""

import re
import asyncio
import logging
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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


# ─── /connect_api buyrug'i ───────────────────────────────

async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, user.username or "", user.full_name or "")

    existing = get_userbot_session(user.id)
    if existing:
        await update.message.reply_text(
            f"✅ <b>Userbot allaqachon ulangan!</b>\n\n"
            f"📱 Telefon: <code>{esc(existing['phone'])}</code>\n\n"
            f"Uzish uchun /disconnect buyrug'ini yuboring.",
            parse_mode=H
        )
        return

    userbot_states[user.id] = "waiting_api_id"
    userbot_temp[user.id]   = {}

    await update.message.reply_text(
        "🔐 <b>Userbot ulash</b>\n\n"
        "50MB dan katta fayllar uchun o'z Telegram accountingizni ulang.\n\n"
        "<b>1-qadam:</b> API ma'lumotlarini oling:\n"
        "1. <a href='https://my.telegram.org'>my.telegram.org</a> ga kiring\n"
        "2. <b>API development tools</b> ga o'ting\n"
        "3. Yangi app yarating → <b>api_id</b> va <b>api_hash</b> oling\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔑 <b>API ID</b> ni yuboring:\n"
        "<i>Masalan: 12345678</i>",
        parse_mode=H,
        disable_web_page_preview=True
    )


# ─── /disconnect buyrug'i ────────────────────────────────

async def disconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    disconnect_userbot(user.id)
    userbot_states.pop(user.id, None)
    userbot_temp.pop(user.id, None)
    await update.message.reply_text(
        "✅ Userbot uzildi.\n\n"
        "Qayta ulash uchun /connect_api yuboring.",
        parse_mode=H
    )


# ─── Userbot jarayoni message handler ────────────────────

async def userbot_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Userbot ulanish jarayonidagi xabarlarni qayta ishlash.
    True qaytarsa — xabar bu handler tomonidan qabul qilindi.
    """
    user  = update.effective_user
    msg   = update.message
    state = userbot_states.get(user.id)
    text  = (msg.text or "").strip()

    if not state or not text:
        return False

    # ── API ID ──────────────────────────────────────────
    if state == "waiting_api_id":
        if not text.isdigit():
            await msg.reply_text("❌ API ID faqat raqamlardan iborat bo'lishi kerak.\nQaytadan kiriting:")
            return True
        userbot_temp[user.id]["api_id"] = text
        userbot_states[user.id] = "waiting_api_hash"
        await msg.reply_text(
            f"✅ API ID: <code>{esc(text)}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>API Hash</b> ni yuboring:\n"
            f"<i>Masalan: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6</i>",
            parse_mode=H
        )
        return True

    # ── API Hash ─────────────────────────────────────────
    if state == "waiting_api_hash":
        if len(text) < 10:
            await msg.reply_text("❌ API Hash juda qisqa. Qaytadan kiriting:")
            return True
        userbot_temp[user.id]["api_hash"] = text
        userbot_states[user.id] = "waiting_phone"
        await msg.reply_text(
            f"✅ API Hash saqlandi.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 <b>Telefon raqamingizni kiriting:</b>\n"
            f"<i>Format: +998901234567</i>",
            parse_mode=H
        )
        return True

    # ── Telefon raqami ───────────────────────────────────
    if state == "waiting_phone":
        phone = text.replace(" ", "").replace("-", "")
        if not re.match(r"^\+?\d{10,15}$", phone):
            await msg.reply_text(
                "❌ Noto'g'ri format.\n"
                "Masalan: <code>+998901234567</code>",
                parse_mode=H
            )
            return True
        if not phone.startswith("+"):
            phone = "+" + phone
        userbot_temp[user.id]["phone"] = phone

        wait = await msg.reply_text("⏳ Kod yuborilmoqda...")
        success, err = await _send_code(user.id)
        if not success:
            await wait.edit_text(
                f"❌ Kod yuborishda xatolik:\n<code>{esc(err)}</code>\n\n"
                f"API ID/Hash to'g'riligini tekshiring. Qaytadan boshlash uchun /connect_api",
                parse_mode=H
            )
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
        else:
            userbot_states[user.id] = "waiting_code"
            await wait.edit_text(
                f"📩 Telegram'dan <b>tasdiqlash kodi</b> keldi!\n\n"
                f"Kodni yuboring. 2FA bo'lsa, raqamlar orasiga nuqta qo'ying:\n"
                f"<code>1.2.3.4.5</code> → <code>12345</code>",
                parse_mode=H
            )
        return True

    # ── Tasdiqlash kodi ──────────────────────────────────
    if state == "waiting_code":
        code = text.replace(".", "").replace(" ", "")
        if not code.isdigit():
            await msg.reply_text("❌ Kod faqat raqamlar. Qaytadan kiriting:")
            return True
        wait = await msg.reply_text("⏳ Tekshirilmoqda...")
        result, err = await _sign_in(user.id, code)
        if result == "ok":
            await wait.edit_text(
                "🎉 <b>Userbot muvaffaqiyatli ulandi!</b>\n\n"
                "Endi 50MB dan katta fayllarni ham yuklay olasiz.",
                parse_mode=H
            )
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
        elif result == "2fa":
            userbot_states[user.id] = "waiting_password"
            await wait.edit_text(
                "🔒 <b>Ikki bosqichli tasdiqlash (2FA)</b>\n\n"
                "Parolingizni yuboring:",
                parse_mode=H
            )
        else:
            await wait.edit_text(
                f"❌ Xatolik: <code>{esc(err)}</code>\n\n"
                f"Qaytadan: /connect_api",
                parse_mode=H
            )
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
        return True

    # ── 2FA paroli ──────────────────────────────────────
    if state == "waiting_password":
        wait = await msg.reply_text("⏳ Tekshirilmoqda...")
        result, err = await _sign_in_2fa(user.id, text)
        if result == "ok":
            await wait.edit_text(
                "🎉 <b>Userbot ulandi (2FA bilan)!</b>\n\n"
                "Katta fayllarni ham yuklay olasiz.",
                parse_mode=H
            )
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
        else:
            await wait.edit_text(
                f"❌ 2FA xatolik: <code>{esc(err)}</code>\n\nQaytadan: /connect_api",
                parse_mode=H
            )
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
        return True

    return False


# ─── Telethon operatsiyalari ──────────────────────────────

async def _send_code(user_id: int) -> tuple[bool, str]:
    """Telethon orqali kod yuborish"""
    temp = userbot_temp.get(user_id, {})
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.errors import (
            ApiIdInvalidError, PhoneNumberInvalidError, FloodWaitError
        )
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
    """Kod bilan kirish"""
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

        # Muvaffaqiyatli
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
    """2FA paroli bilan kirish"""
    temp = userbot_temp.get(user_id, {})
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        client: TelegramClient = temp.get("client_ref")
        session: StringSession = temp.get("session_obj")

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
    """Saqlangan session bilan Telethon client yaratish"""
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
    Userbot orqali 50MB dan katta fayllarni yuboradi
    Returns: (success, message_id, file_id)
    """
    client = await get_telethon_client(user_id)
    if not client:
        return False, 0, "Userbot ulanmagan"

    try:
        def callback(current, total):
            if progress_cb and total > 0:
                pct = (current / total) * 100
                asyncio.create_task(progress_cb(current, total, pct))

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
