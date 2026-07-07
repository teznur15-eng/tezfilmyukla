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
    save_userbot_session, get_userbot_session, get_all_userbot_sessions, disconnect_userbot, upsert_user
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
    await stop_userbot_for_user(user.id)
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
            asyncio.create_task(start_userbot_for_user(user.id, context.application))
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
            asyncio.create_task(start_userbot_for_user(user.id, context.application))
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
                if dt >= 3.0 or current == total:
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
        return True, msg_id, file_id
    except Exception as e:
        logger.error(f"Userbot upload error: {e}")
        return False, 0, str(e)
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


# ─── USERBOT BACKGROUND AUTOMATION SYSTEM ─────────────────

active_clients: dict = {}  # user_id -> TelegramClient
reaction_cache: set = set()


async def send_media_safely(client, to_peer, msg, caption=None, status_msg=None):
    import os
    import tempfile
    import time
    
    local_status_msg = None
    is_local = False

    def make_progress_callback(msg_to_edit, action_text):
        last_update_time = [time.time()]
        last_percent = [0]
        
        async def callback(current, total):
            if not msg_to_edit:
                return
            if not total or total <= 0:
                return
            
            pct = (current / total) * 100
            now = time.time()
            if now - last_update_time[0] >= 1.5 or pct >= 100 or pct - last_percent[0] >= 15:
                last_update_time[0] = now
                last_percent[0] = pct
                
                filled_length = int(pct / 10)
                bar = "█" * filled_length + "░" * (10 - filled_length)
                
                size_mb = total / (1024 * 1024)
                curr_mb = current / (1024 * 1024)
                
                progress_text = (
                    f"🔒 <b>Kanal himoyalangan! Tizim aylanib o'tish rejimida ishlayapti...</b>\n\n"
                    f"⚙️ <b>{action_text}:</b>\n"
                    f"<code>[{bar}]</code> {pct:.1f}%\n"
                    f"📊 {curr_mb:.2f}MB / {size_mb:.2f}MB"
                )
                try:
                    await msg_to_edit.edit(progress_text, parse_mode="html")
                except Exception as edit_err:
                    logger.debug(f"Progress update failed: {edit_err}")
                    pass
        return callback

    try:
        # Harakat qilib ko'ramiz oddiy forward qilishga (faqat ruxsat berilgan chatlarda ishlaydi)
        await client.send_message(to_peer, msg)
        if caption:
            await client.send_message(to_peer, caption, parse_mode="html")
        return True
    except Exception as e:
        err_str = str(e).lower()
        # Agar kanal/guruh himoyalangan bo'lsa (Restrict Saving Content yoqilgan bo'lsa)
        if "forward" in err_str or "protect" in err_str or "restrict" in err_str or "media" in err_str or "privacy" in err_str:
            logger.info("Forwarding failed due to chat protection. Initiating secure cloud-copy...")
            
            if status_msg:
                active_status_msg = status_msg
            else:
                try:
                    active_status_msg = await client.send_message(to_peer, "🔒 <b>Kanal himoyalangan ekan. Yuklab olib, to'g'ridan-to'g'ri yuborish tizimi ishga tushdi...</b>", parse_mode="html")
                    local_status_msg = active_status_msg
                    is_local = True
                except Exception:
                    active_status_msg = None
            
            if active_status_msg:
                try:
                    await active_status_msg.edit("🔒 <b>Kanal himoyalangan ekan. Yuklab olib, qayta yuborish boshlandi...</b>\n⏱ <i>Serverga yuklab olinmoqda...</i>", parse_mode="html")
                except Exception:
                    pass
            
            try:
                suffix = ""
                if msg.file and msg.file.ext:
                    suffix = msg.file.ext
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp_path = tmp.name
                
                # Telethon orqali serverga yuklab olamiz (progress bar bilan)
                download_cb = make_progress_callback(active_status_msg, "Serverga yuklab olinmoqda (Download)") if active_status_msg else None
                downloaded_file = await client.download_media(msg, file=tmp_path, progress_callback=download_cb)
                
                if downloaded_file and os.path.exists(downloaded_file):
                    if active_status_msg:
                        try:
                            await active_status_msg.edit("⚡️ <b>Fayl muvaffaqiyatli yuklandi. Endi sizning 'Saved Messages'ingizga yuborilmoqda...</b>", parse_mode="html")
                        except Exception:
                            pass
                    
                    actual_caption = caption or (msg.text or "")
                    
                    # Telegramga yuklash (progress bar bilan)
                    upload_cb = make_progress_callback(active_status_msg, "Telegramga yuklanmoqda (Upload)") if active_status_msg else None
                    await client.send_file(to_peer, downloaded_file, caption=actual_caption, parse_mode="html", progress_callback=upload_cb)
                    
                    # Agar bu lokal yaratilgan status_msg bo'lsa, tugallanganini ko'rsatamiz
                    if is_local and local_status_msg:
                        try:
                            await local_status_msg.edit("✅ <b>Video muvaffaqiyatli saqlandi!</b>", parse_mode="html")
                        except Exception:
                            pass
                            
                    # Tozalash
                    try:
                        os.remove(downloaded_file)
                    except Exception:
                        pass
                    return True
            except Exception as inner_err:
                logger.error(f"Failed in secure cloud-copy: {inner_err}")
                if is_local and local_status_msg:
                    try:
                        await local_status_msg.edit(f"❌ <b>Xatolik yuz berdi:</b>\n<code>{inner_err}</code>", parse_mode="html")
                    except Exception:
                        pass
                raise inner_err
        raise e


def register_userbot_handlers(client, user_id: int, application=None):
    from telethon import events
    from telethon.tl.types import UpdateMessageReactions, MessageReactions

    # 1. New Message Reply Handler
    # This detects when the userbot owner replies to a video/media with '/ok' or '🔥'
    @client.on(events.NewMessage(outgoing=True))
    async def handle_outgoing_reply(event):
        if not event.is_reply:
            return
            
        text = (event.text or "").strip().lower()
        if text not in ["/ok", "🔥", "ok", "yukla", "save", "saqla"]:
            return
            
        try:
            replied_msg = await event.get_reply_message()
            if not replied_msg or not replied_msg.media:
                return
                
            status_msg = await event.reply("⚡️ <b>Kino saqlanmoqda...</b>", parse_mode="html")
            
            # Send copy safely to Saved Messages ('me')
            await send_media_safely(client, 'me', replied_msg, status_msg=status_msg)
            
            await status_msg.edit("✅ <b>Kino muvaffaqiyatli Saqlangan xabarlar (Saved Messages) papkangizga saqlandi!</b>", parse_mode="html")
        except Exception as e:
            logger.error(f"Error in outgoing reply handler for user {user_id}: {e}")
            try:
                await event.reply(f"❌ <b>Xatolik yuz berdi:</b>\n<code>{esc(str(e))}</code>", parse_mode="html")
            except Exception:
                pass

    # 2. Raw Update Reaction Handler
    # This detects when the user reacts with 🔥 on a message in channels/chats
    @client.on(events.Raw)
    async def handle_raw_reaction(event):
        if not isinstance(event, UpdateMessageReactions):
            return
            
        try:
            peer = event.peer
            msg_id = event.msg_id
            
            cache_key = f"react_{user_id}_{msg_id}"
            if cache_key in reaction_cache:
                return
                
            msg = await client.get_messages(peer, ids=msg_id)
            if not msg or not msg.media:
                return
                
            has_fire = False
            if msg.reactions:
                for r in msg.reactions.results:
                    if hasattr(r.reaction, 'emoticon') and r.reaction.emoticon == '🔥':
                        if r.count > 0:
                            has_fire = True
                            break
                            
            if not has_fire:
                return
                
            # Verify if we are the one who reacted with 🔥 to avoid triggering on other users' reactions
            from telethon.tl.functions.messages import GetMessageReactionsListRequest
            try:
                res = await client(GetMessageReactionsListRequest(
                    peer=peer,
                    id=msg_id,
                    limit=10
                ))
                me = await client.get_me()
                user_reacted = any(x.peer_id.user_id == me.id for x in res.users if hasattr(x.peer_id, 'user_id'))
                if not user_reacted:
                    return
            except Exception as re_err:
                logger.debug(f"Could not verify reaction owner, proceeding: {re_err}")
                pass
                
            # Prevent duplicate actions
            reaction_cache.add(cache_key)
            if len(reaction_cache) > 5000:
                reaction_cache.clear() # Prevent memory bloat
                
            # Send copy safely to Saved Messages ('me')
            await send_media_safely(
                client, 
                'me', 
                msg, 
                caption="🔥 <b>Reaksiya orqali saqlangan video!</b>"
            )
            logger.info(f"Successfully processed reaction download for user {user_id}, msg {msg_id}")
            
        except Exception as e:
            logger.error(f"Error in reaction handler for user {user_id}: {e}")


async def start_userbot_for_user(user_id: int, application=None):
    if user_id in active_clients:
        await stop_userbot_for_user(user_id)
        
    session_row = get_userbot_session(user_id)
    if not session_row or not session_row.get("session_string"):
        return False
        
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        
        client = TelegramClient(
            StringSession(session_row["session_string"]),
            int(session_row["api_id"]),
            session_row["api_hash"]
        )
        await client.connect()
        if not await client.is_user_authorized():
            logger.warning(f"Userbot session for {user_id} is invalid or expired.")
            await client.disconnect()
            return False
            
        register_userbot_handlers(client, user_id, application)
        active_clients[user_id] = client
        logger.info(f"Background userbot started for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error starting userbot for {user_id}: {e}")
        return False


async def stop_userbot_for_user(user_id: int):
    client = active_clients.pop(user_id, None)
    if client:
        try:
            await client.disconnect()
            logger.info(f"Userbot for {user_id} stopped.")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting userbot for {user_id}: {e}")
    return False


async def start_userbot_manager(application):
    logger.info("Initializing Userbot Background Manager...")
    try:
        sessions = get_all_userbot_sessions()
        logger.info(f"Found {len(sessions)} saved userbot sessions. Loading background clients...")
        for row in sessions:
            user_id = row["user_id"]
            asyncio.create_task(start_userbot_for_user(user_id, application))
    except Exception as e:
        logger.error(f"Error starting Userbot Background Manager: {e}")


