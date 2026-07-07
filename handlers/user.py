"""
Foydalanuvchi handlerlari — HTML parse mode
Majburiy kanal obuna + Admin limitsiz + uzmovi.tv/kinolar.tv qo'llab-quvvatlash
"""

import os
import re
import html
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

from utils.database import (
    upsert_user, get_user, check_subscription, get_setting,
    get_active_tariffs, get_tariff, get_active_cards,
    submit_complaint, get_user_ref_code, find_user_by_ref,
    log_download, update_download,
    get_user_free_used, get_user_bonus_dl, increment_free_used, use_bonus_dl,
    is_admin, submit_payment, get_userbot_session, get_user_downloads_count,
    get_stored_file, store_channel_file,
    get_reviews_summary, get_recent_reviews, get_user_review, upsert_review,
    log_user_action,
)
from utils.scraper import (
    scrape_movie, search_movies, internet_search_movie,
    MovieInfo, DownloadLink, resolve_real_url,
)
from utils.downloader import (
    download_file, delete_file, make_filename, get_file_size_mb,
    upload_to_channel, forward_from_channel, send_by_file_id,
)

logger = logging.getLogger(__name__)
H = ParseMode.HTML

# ─── Foydalanuvchi holatlari ─────────────────────────────
STATE_COMPLAINT   = "complaint"
STATE_SEARCH      = "search"
STATE_URL         = "url"
STATE_INET        = "inet_search"
STATE_REVIEW_TEXT = "review_text"

user_states: dict[int, str] = {}
active_downloads: dict[int, asyncio.Task] = {}
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(3)  # Maksimal 3 ta parallel yuklash


def esc(text: str) -> str:
    return html.escape(str(text or ""))


# ═══════════════════════════════════════════════════════
#  MAJBURIY KANAL OBUNA TEKSHIRUVI
# ═══════════════════════════════════════════════════════

async def check_mandatory_channel(bot, user_id: int) -> bool:
    """Foydalanuvchi majburiy kanalga obuna bo'lganini tekshirish."""
    channel = get_setting("mandatory_channel", "")
    if not channel or is_admin(user_id):
        return True
    
    # Username formatini to'g'rilash (masalan, 'kanal' -> '@kanal')
    if not str(channel).startswith("-") and not str(channel).startswith("@"):
        channel = f"@{channel}"

    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status not in (
            ChatMember.LEFT, ChatMember.BANNED, "kicked", "left"
        )
    except TelegramError as e:
        logger.warning(f"Mandatory channel check error for {channel}: {e}")
        return True  # Kanal mavjud bo'lmasa yoki bot admin bo'lmasa — o'tkazib yuborish


def _mandatory_channel_kb() -> InlineKeyboardMarkup:
    channel = get_setting("mandatory_channel", "")
    rows = []
    if channel:
        clean_channel = str(channel).lstrip("@")
        label = channel if str(channel).startswith("@") else f"@{clean_channel}"
        rows.append([InlineKeyboardButton(f"📢 {label}", url=f"https://t.me/{clean_channel}")])
    rows.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_subscription_ch")])
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════════════
#  YORDAM FUNKSIYALAR
# ═══════════════════════════════════════════════════════

def _can_download(user_id: int) -> tuple[bool, str]:
    if is_admin(user_id):              return True, "admin"
    if check_subscription(user_id):    return True, "sub"
    if get_user_bonus_dl(user_id) > 0: return True, "bonus"
    free_limit = int(get_setting("free_downloads", "1"))
    if get_user_free_used(user_id) < free_limit:
        return True, "free"
    return False, "no"


def _status_line(user_id: int) -> str:
    if is_admin(user_id):
        return "👑 Admin (limitsiz)"
    if check_subscription(user_id):
        u    = get_user(user_id)
        exp  = u["sub_expires"][:10] if u and u["sub_expires"] else "?"
        t    = get_tariff(u["tariff_id"]) if u and u["tariff_id"] else None
        name = esc(t["name"]) if t else "Obuna"
        return f"✅ {name} (tugash: {exp})"
    bonus = get_user_bonus_dl(user_id)
    used  = get_user_free_used(user_id)
    limit = int(get_setting("free_downloads", "1"))
    left  = max(0, limit - used)
    extra = f" + {bonus} bonus" if bonus else ""
    return f"🆓 Bepul: {left} ta{extra}"


def _main_kb(user_id: int) -> InlineKeyboardMarkup:
    is_sub = check_subscription(user_id)
    sub_btn = (
        InlineKeyboardButton("✅ Obuna faol", callback_data="my_profile")
        if is_sub else
        InlineKeyboardButton("💎 Obuna olish", callback_data="buy_subscription")
    )
    rows = [
        [InlineKeyboardButton("🔍 Kino qidirish",  callback_data="search_movie"),
         InlineKeyboardButton("🔗 URL yuborish",   callback_data="send_url")],
        [sub_btn,
         InlineKeyboardButton("👤 Profil",          callback_data="my_profile")],
        [InlineKeyboardButton("👥 Referral",         callback_data="referral"),
         InlineKeyboardButton("📋 Shikoyat",         callback_data="complaint")],
        [InlineKeyboardButton("🔐 Userbot (50MB+)",  callback_data="userbot_menu"),
         InlineKeyboardButton("⭐ Sharhlar & Fikrlar", callback_data="reviews_menu")],
        [InlineKeyboardButton("ℹ️ Yordam / FAQ",     callback_data="help")],
    ]
    if check_subscription(user_id) or is_admin(user_id):
        rows.append([InlineKeyboardButton("🌐 Internet qidirish", callback_data="internet_search")])
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════════════
#  /start
# ═══════════════════════════════════════════════════════

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args or []

    ref_by = 0
    if args:
        ref = find_user_by_ref(args[0].strip())
        if ref and ref["user_id"] != user.id:
            ref_by = ref["user_id"]

    upsert_user(user.id, user.username or "", user.full_name or "", referred_by=ref_by)

    if get_setting("maintenance_mode", "0") == "1" and not is_admin(user.id):
        await update.message.reply_text("🔧 Bot texnik ishlar uchun to'xtatilgan. Tez orada qaytamiz!")
        return

    # Majburiy kanal tekshiruvi
    if not await check_mandatory_channel(context.bot, user.id):
        channel = get_setting("mandatory_channel","")
        await update.message.reply_text(
            f"📢 <b>Botdan foydalanish uchun kanalga obuna bo'ling!</b>\n\n"
            f"Kanal: {esc(channel)}\n\n"
            f"Obuna bo'lgach, «✅ Tekshirish» ni bosing.",
            parse_mode=H,
            reply_markup=_mandatory_channel_kb()
        )
        return

    welcome = get_setting("welcome_message", "🎬 Botimizga xush kelibsiz! Barcha mashhur va yangi kinolarni tez va oson yuklab oling.")
    start_photo = get_setting("start_photo", "")

    caption = (
        f"👋 <b>Salom, {esc(user.first_name)}!</b>\n\n"
        f"{esc(welcome)}\n\n"
        f"📊 <b>Sizning holatingiz:</b> {_status_line(user.id)}\n\n"
        f"🎬 Kino URL'ini yuboring yoki izlang!\n"
        f"<i>Qo'llab-quvvatlanadi: asilmedia.org, uzmovie.uz, uzmovi.tv, kinolar.tv</i>"
    )

    if start_photo:
        try:
            await update.message.reply_photo(
                photo=start_photo,
                caption=caption,
                parse_mode=H,
                reply_markup=_main_kb(user.id)
            )
            return
        except Exception as e:
            logger.warning(f"Start photo error: {e}")

    await update.message.reply_text(
        caption,
        parse_mode=H,
        reply_markup=_main_kb(user.id)
    )


# ═══════════════════════════════════════════════════════
#  CALLBACK HANDLER
# ═══════════════════════════════════════════════════════

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()
    user = q.from_user
    data = q.data or ""

    # Majburiy kanal tekshiruvi
    if data == "check_subscription_ch":
        if await check_mandatory_channel(context.bot, user.id):
            await q.edit_message_text(
                f"✅ <b>Rahmat!</b> Kanalga obuna bo'ldingiz.\n\n"
                f"📊 Holat: {_status_line(user.id)}",
                parse_mode=H,
                reply_markup=_main_kb(user.id)
            )
        else:
            await q.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
        return

    # Kanalga obuna tekshirish (agar kerak bo'lsa)
    if not is_admin(user.id) and data not in ("check_subscription_ch",):
        if not await check_mandatory_channel(context.bot, user.id):
            await q.answer("📢 Avval kanalga obuna bo'ling!", show_alert=True)
            return

    try:
        if data == "back_main":
            welcome = get_setting("welcome_message", "🎬 Botimizga xush kelibsiz! Barcha mashhur va yangi kinolarni tez va oson yuklab oling.")
            caption = (
                f"👋 <b>Salom, {esc(user.first_name)}!</b>\n\n"
                f"{esc(welcome)}\n\n"
                f"📊 <b>Sizning holatingiz:</b> {_status_line(user.id)}\n\n"
                f"🎬 Kino URL'ini yuboring yoki izlang!\n"
                f"<i>Qo'llab-quvvatlanadi: asilmedia.org, uzmovie.uz, uzmovi.tv, kinolar.tv</i>"
            )
            if q.message.photo:
                try:
                    await q.edit_message_caption(caption=caption, parse_mode=H, reply_markup=_main_kb(user.id))
                    return
                except Exception:
                    pass
            try:
                await q.edit_message_text(caption, parse_mode=H, reply_markup=_main_kb(user.id))
            except Exception:
                await q.message.reply_text(caption, parse_mode=H, reply_markup=_main_kb(user.id))

        elif data == "search_movie":
            user_states[user.id] = STATE_SEARCH
            await q.edit_message_text(
                "🔍 <b>Kino qidirish</b>\n\n"
                "Kino nomini yozing:\n"
                "<i>Barcha saytlarda qidiradi: asilmedia, uzmovie, uzmovi.tv, kinolar.tv</i>",
                parse_mode=H
            )

        elif data == "send_url":
            user_states[user.id] = STATE_URL
            await q.edit_message_text(
                "🔗 <b>Kino URL'ini yuboring:</b>\n\n"
                "Qo'llab-quvvatlanadi:\n"
                "• <code>https://asilmedia.org/...</code>\n"
                "• <code>https://uzmovie.uz/...</code>\n"
                "• <code>https://uzmovi.tv/...</code>\n"
                "• <code>https://kinolar.tv/...</code>",
                parse_mode=H
            )

        elif data == "my_profile":
            await _show_profile(q, user)

        elif data == "buy_subscription":
            await _show_tariffs(q)

        elif data.startswith("pick_tariff_"):
            tariff_id = int(data.split("_")[2])
            await _show_payment_cards(q, tariff_id, context)

        elif data.startswith("pay_card_"):
            parts = data.split("_")
            await _show_payment_form(q, user, int(parts[2]), int(parts[3]), context)

        elif data == "referral":
            await _show_referral(q, user)

        elif data == "complaint":
            user_states[user.id] = STATE_COMPLAINT
            await q.edit_message_text(
                "📋 <b>Shikoyat yoki taklif</b>\n\nXabaringizni yozing:",
                parse_mode=H
            )

        elif data == "reviews_menu":
            await _show_reviews_menu(q, user)

        elif data == "write_review":
            await _start_write_review(q, user)

        elif data.startswith("review_rate_"):
            rating = int(data.split("_")[2])
            context.user_data["pending_review_rating"] = rating
            user_states[user.id] = STATE_REVIEW_TEXT
            await q.edit_message_text(
                f"⭐ Bahoingiz: <b>{'⭐' * rating} ({rating}/5)</b>\n\n"
                f"Endi bot haqida qisqacha fikringiz (sharhingiz)ni yozib yuboring (masalan: <i>Bot juda tez va qulay ishlaydi!</i>):",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Bekor qilish", callback_data="reviews_menu")]])
            )

        elif data == "userbot_menu":
            from handlers.userbot import show_userbot_menu_panel
            await show_userbot_menu_panel(q, user, context)

        elif data == "ub_connect_start":
            from handlers.userbot import start_ub_connect
            await start_ub_connect(q, user)

        elif data == "ub_guide":
            text = (
                "📖 <b>my.telegram.org 'dan API ID olish qo'llanmasi:</b>\n\n"
                "1. Braunzerda <a href='https://my.telegram.org'>my.telegram.org</a> ga kiring\n"
                "2. Telegram telefon raqamingizni kiriting va kelgan kodni yozing\n"
                "3. <b>API development tools</b> menyusini tanlang\n"
                "4. App title va short name (masalan: <i>MyMovieApp</i>) deb yozing\n"
                "5. Save bosing va <b>App api_id</b> hamda <b>App api_hash</b> ga ega bo'lasiz!\n\n"
                "Ushbu raqamlarni botimizga kiritib, 2GB gacha kinolarni bepul yuklang."
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Ulashni boshlash", callback_data="ub_connect_start")],
                [InlineKeyboardButton("🛡️ Userbot Xavfsizligi", callback_data="ub_security_info")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="userbot_menu")]
            ])
            await q.edit_message_text(text, parse_mode=H, reply_markup=kb, disable_web_page_preview=True)

        elif data == "ub_security_info":
            text = (
                "🛡️ <b>Userbot Xavfsizligi va Uning Maqsadi:</b>\n\n"
                "<b>1. Userbot nima uchun kerak?</b>\n"
                "Telegram Bot API rasmiy qoidasiga ko'ra oddiy botlar maksimal 50MB fayl yuborishi mumkin. "
                "4K va HD kinolar hajmi esa 50MB dan 2,000MB (2GB) gacha bo'ladi. "
                "Userbot yordamida siz kinolarni cheklovsiz o'z Telegram accountingiz orqali yuklaysiz!\n\n"
                "<b>2. Userbot xavfsizmi?</b>\n"
                "• Session ma'lumotingiz shifrlangan bazada saqlanadi va faqat kinoni Saqlangan xabarlar (Saved Messages) papkangizga yuborish uchun ishlatiladi.\n"
                "• Bot hech qachon shaxsiy yozishmalaringizni o'qimaydi va boshqalarga yubormaydi.\n"
                "• Istalgan vaqtda '🔴 Userbotni uzish' tugmasi orqali yoki Telegram Sozlamalari -> Qurilmalar bo'limidan seansni darhol tugatishingiz mumkin!\n"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Userbotni ulash", callback_data="ub_connect_start")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="userbot_menu")]
            ])
            await q.edit_message_text(text, parse_mode=H, reply_markup=kb)

        elif data == "ub_cancel":
            from handlers.userbot import userbot_states, userbot_temp, show_userbot_menu_panel
            userbot_states.pop(user.id, None)
            userbot_temp.pop(user.id, None)
            await show_userbot_menu_panel(q, user, context)

        elif data == "disconnect_userbot":
            from utils.database import disconnect_userbot
            disconnect_userbot(user.id)
            await q.edit_message_text(
                "✅ Userbot uzildi.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]])
            )

        elif data == "help":
            await _show_help(q)

        elif data == "internet_search":
            if not check_subscription(user.id) and not is_admin(user.id):
                await q.answer("⛔ Bu funksiya faqat Premium uchun!", show_alert=True)
                return
            user_states[user.id] = STATE_INET
            await q.edit_message_text(
                "🌐 <b>Internet qidirish</b> (Premium)\n\nKino nomini yozing:",
                parse_mode=H
            )

        elif data.startswith("cancel_dl_"):
            target_user_id = int(data.split("_")[-1])
            if q.from_user.id != target_user_id and not is_admin(q.from_user.id):
                await q.answer("⛔ Bu yuklashni faqat uning egasi yoki admin to'xtatishi mumkin!", show_alert=True)
                return
            await q.answer("Yuklash to'xtatilmoqda...")
            await _cancel_user_download(target_user_id, q.message)
            return

        elif data.startswith("movie_part_"):
            await _show_part_qualities(q, context, data, user)

        elif data.startswith("dl_"):
            await _handle_download(q, context, data, user)

        elif data.startswith("search_pick_"):
            key = data[len("search_pick_"):]
            url = context.bot_data.get(f"sres_{key}", "")
            if url:
                await q.edit_message_text("🔎 Sahifa o'qilmoqda...")
                await _process_url(q.message, context, url, user)
            else:
                await q.edit_message_text("❌ Havola muddati o'tgan. Qaytadan qidiring.")

    except Exception as e:
        logger.error(f"Button [{data}]: {e}")
        try:
            await q.answer("Xatolik yuz berdi.", show_alert=True)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════
#  PROFIL
# ═══════════════════════════════════════════════════════

async def _show_profile(q, user):
    try:
        u        = get_user(user.id)
        total_dl = get_user_downloads_count(user.id)
        ref_code = get_user_ref_code(user.id)
        bot_un   = get_setting("bot_username", "")
        ref_link = f"https://t.me/{bot_un}?start={ref_code}" if bot_un else ref_code
        session  = get_userbot_session(user.id)
        ub_ok    = "✅ Ulangan" if session else "❌ Ulanmagan"
        name     = esc(user.full_name or "")
        username = esc(user.username or "yo'q")

        await q.edit_message_text(
            f"👤 <b>Profil</b>\n\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"👤 Ism: {name}\n"
            f"📱 @{username}\n\n"
            f"💎 Obuna: {_status_line(user.id)}\n"
            f"🎬 Yuklab olishlar: {total_dl} ta\n"
            f"👥 Taklif qilganlar: {u['ref_count'] if u else 0} ta\n"
            f"🎁 Bonus: {u['bonus_dl'] if u else 0} ta\n"
            f"🔐 Userbot: {ub_ok}\n\n"
            f"🔗 Referral:\n<code>{ref_link}</code>",
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")
            ]])
        )
    except Exception as e:
        logger.error(f"Profile: {e}")
        await q.answer("Profil yuklanmadi.", show_alert=True)


# ═══════════════════════════════════════════════════════
#  TARIF & TO'LOV
# ═══════════════════════════════════════════════════════

async def _show_tariffs(q):
    tariffs = get_active_tariffs()
    if not tariffs:
        await q.edit_message_text(
            "💎 Hozircha tariflar mavjud emas.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]])
        )
        return
    text = "💎 <b>Obuna tariflar</b>\n\n"
    rows = []
    for t in tariffs:
        text += (
            f"🏷 <b>{esc(t['name'])}</b>\n"
            f"   💰 {t['price']:,.0f} {esc(t['currency'])}\n"
            f"   📅 {t['days']} kun\n"
        )
        if t["description"]:
            text += f"   📝 <i>{esc(t['description'])}</i>\n"
        text += "\n"
        rows.append([InlineKeyboardButton(
            f"✅ {t['name']} — {t['price']:,.0f} so'm ({t['days']} kun)",
            callback_data=f"pick_tariff_{t['id']}"
        )])
    rows.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
    await q.edit_message_text(text, parse_mode=H, reply_markup=InlineKeyboardMarkup(rows))


async def _show_payment_cards(q, tariff_id: int, context):
    tariff = get_tariff(tariff_id)
    if not tariff:
        await q.edit_message_text("Tarif topilmadi.")
        return
    cards = get_active_cards()
    if not cards:
        await q.edit_message_text(
            "💳 To'lov kartasi mavjud emas. Admin bilan bog'laning.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="buy_subscription")]])
        )
        return
    rows = [[InlineKeyboardButton(
        f"💳 {c['bank_name'] or 'Karta'} · ...{c['card_number'][-4:]}",
        callback_data=f"pay_card_{tariff_id}_{c['id']}"
    )] for c in cards]
    rows.append([InlineKeyboardButton("🔙", callback_data="buy_subscription")])
    await q.edit_message_text(
        f"💳 <b>Karta tanlang</b>\n\n"
        f"🏷 {esc(tariff['name'])} — {tariff['price']:,.0f} {esc(tariff['currency'])} / {tariff['days']} kun",
        parse_mode=H, reply_markup=InlineKeyboardMarkup(rows)
    )


async def _show_payment_form(q, user, tariff_id: int, card_id: int, context):
    tariff = get_tariff(tariff_id)
    card   = next((c for c in get_active_cards() if c["id"] == card_id), None)
    if not tariff or not card:
        await q.edit_message_text("Ma'lumot topilmadi.")
        return
    context.user_data["waiting_payment"] = {
        "tariff_id": tariff_id, "card_id": card_id, "amount": tariff["price"]
    }
    await q.edit_message_text(
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"🏦 Bank: <b>{esc(card['bank_name'] or '—')}</b>\n"
        f"💳 Karta: <code>{esc(card['card_number'])}</code>\n"
        f"👤 Egasi: <code>{esc(card['card_holder'])}</code>\n\n"
        f"💰 Summa: <b>{tariff['price']:,.0f} {esc(tariff['currency'])}</b>\n"
        f"🏷 Tarif: <b>{esc(tariff['name'])}</b> ({tariff['days']} kun)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Qadamlar:</b>\n"
        f"1️⃣ Kartaga pul o'tkazing\n"
        f"2️⃣ Chek rasmini shu chatga yuboring\n"
        f"3️⃣ Admin 10–30 daqiqada faollashtiradi",
        parse_mode=H,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data=f"pick_tariff_{tariff_id}")]])
    )


# ═══════════════════════════════════════════════════════
#  REFERRAL
# ═══════════════════════════════════════════════════════

async def _show_referral(q, user):
    ref_code = get_user_ref_code(user.id)
    bot_un   = get_setting("bot_username","")
    ref_link = f"https://t.me/{bot_un}?start={ref_code}" if bot_un else ref_code
    u        = get_user(user.id)
    bdl      = get_setting("ref_bonus_dl","1")

    await q.edit_message_text(
        f"👥 <b>Referral tizimi</b>\n\n"
        f"Do'stingizni taklif qiling — bonuslar oling!\n\n"
        f"🔗 <b>Havolangiz:</b>\n<code>{ref_link}</code>\n\n"
        f"📊 Taklif qilganlar: <b>{u['ref_count'] if u else 0} ta</b>\n"
        f"🎁 Bonus yuklab olish: <b>{u['bonus_dl'] if u else 0} ta</b>\n\n"
        f"<b>Har yangi foydalanuvchi uchun:</b>\n"
        f"• +{bdl} ta yuklab olish huquqi",
        parse_mode=H,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]])
    )


async def _show_userbot_menu(q, user, context):
    session = get_userbot_session(user.id)
    if session:
        await q.edit_message_text(
            f"🔐 <b>Userbot</b> ✅ Ulangan\n\n"
            f"📱 Telefon: <code>{esc(session['phone'])}</code>\n\n"
            f"50MB dan katta fayllar userbot orqali yuklanadi.",
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Uzish", callback_data="disconnect_userbot")],
                [InlineKeyboardButton("🔙", callback_data="back_main")],
            ])
        )
    else:
        await q.edit_message_text(
            "🔐 <b>Userbot ulash</b>\n\n"
            "50MB+ fayllar uchun o'z Telegram accountingizni ulang.\n\n"
            "Ulash uchun: /connect_api buyrug'ini yuboring\n\n"
            "<b>Qadamlar:</b>\n"
            "1. my.telegram.org → API development tools\n"
            "2. api_id va api_hash oling\n"
            "3. /connect_api → ma'lumotlarni kiriting",
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]])
        )


async def _show_help(q):
    await q.edit_message_text(
        "❓ <b>Yordam</b>\n\n"
        "🎬 <b>Kino yuklab olish:</b>\n"
        "• URL yuboring yoki qidiring\n"
        "• Qo'llab-quvvatlanadi: asilmedia.org, uzmovie.uz, uzmovi.tv, kinolar.tv\n"
        "• Qism va sifatni tanlang\n\n"
        "🆓 <b>Bepul:</b> 1 ta yuklab olish\n"
        "💎 <b>Premium (9000 so'm/oy):</b> Cheksiz + internet qidirish\n"
        "👥 <b>Referral:</b> Do'st taklif → bonus yuklab olish\n\n"
        "📱 <b>Buyruqlar:</b>\n"
        "/start — boshlash\n"
        "/connect_api — userbot ulash\n"
        "/disconnect — userbot uzish\n\n"
        "📋 <b>Shikoyat:</b> muammo bo'lsa yozing",
        parse_mode=H,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]])
    )


async def _show_reviews_menu(q, user):
    summary = get_reviews_summary()
    recent = get_recent_reviews(6)
    user_rev = get_user_review(user.id)

    total = summary["count"]
    avg = summary["avg"]
    stars = summary["stars"]

    star_str = ""
    if total > 0:
        bars = []
        for s in [5, 4, 3, 2, 1]:
            cnt = stars.get(s, 0)
            pct = int(cnt / total * 10) if total else 0
            bar = "★" * pct + "☆" * (10 - pct)
            bars.append(f"  {s} ⭐: {bar} ({cnt})")
        star_str = "\n".join(bars) + "\n\n"

    rec_text = ""
    if recent:
        rec_text = "💬 <b>So'nggi foydalanuvchilar sharhlari:</b>\n\n"
        for r in recent:
            name = esc(r.get("full_name") or r.get("username") or f"Foydalanuvchi #{r['user_id']}")
            star_icons = "⭐" * r["rating"]
            comment = esc(r.get("comment", "")[:120])
            dt = str(r.get("updated_at", ""))[:10]
            rec_text += f"👤 <b>{name}</b> ({star_icons}) — <i>{dt}</i>\n«{comment}»\n\n"
    else:
        rec_text = "<i>Hozircha sharhlar mavjud emas. Birinchi bo'lib sharh qoldiring!</i>\n\n"

    user_rev_text = ""
    if user_rev:
        u_stars = "⭐" * user_rev["rating"]
        user_rev_text = (
            f"✍️ <b>Sizning sharhingiz:</b> {u_stars} ({user_rev['rating']}/5)\n"
            f"«<i>{esc(user_rev['comment'])}</i>»\n"
            f"<i>Kuniga 1 marta tahrirlash mumkin.</i>\n\n"
        )

    text = (
        f"⭐ <b>Fikrlar va Sharhlar Bo'limi</b>\n\n"
        f"🏆 <b>O'rtacha baho:</b> ⭐ <b>{avg} / 5.0</b> ({total} ta sharh)\n\n"
        f"{star_str}"
        f"{user_rev_text}"
        f"{rec_text}"
        f"📌 Bot haqida o'z fikringiz va bahoingizni qoldiring!"
    )

    btn_label = "✏️ Sharhingizni tahrirlash" if user_rev else "✍️ Sharh va Baho qoldirish"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(btn_label, callback_data="write_review")],
        [InlineKeyboardButton("🔄 Yangilash", callback_data="reviews_menu")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]
    ])

    if q.message.photo:
        await q.message.reply_text(text, parse_mode=H, reply_markup=kb)
    else:
        await q.edit_message_text(text, parse_mode=H, reply_markup=kb)


async def _start_write_review(q, user):
    user_rev = get_user_review(user.id)
    if user_rev and user_rev.get("updated_at"):
        try:
            from datetime import datetime
            last_dt = datetime.strptime(str(user_rev["updated_at"])[:19], "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - last_dt).total_seconds() < 86400:
                hours_left = int((86400 - (datetime.now() - last_dt).total_seconds()) // 3600) + 1
                await q.answer(
                    f"⏳ Sharhingizni kuniga faqat 1 marta tahrirlashingiz mumkin! Keyingi tahrirlash uchun {hours_left} soat qoldi.",
                    show_alert=True
                )
                return
        except Exception:
            pass

    text = (
        "⭐ <b>Botga baho bering:</b>\n\n"
        "Quyidagi yulduzchalardan birini tanlang:"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ 1", callback_data="review_rate_1"),
            InlineKeyboardButton("⭐ 2", callback_data="review_rate_2"),
            InlineKeyboardButton("⭐ 3", callback_data="review_rate_3"),
            InlineKeyboardButton("⭐ 4", callback_data="review_rate_4"),
            InlineKeyboardButton("⭐ 5", callback_data="review_rate_5"),
        ],
        [InlineKeyboardButton("🔙 Bekor qilish", callback_data="reviews_menu")]
    ])
    await q.edit_message_text(text, parse_mode=H, reply_markup=kb)


# ═══════════════════════════════════════════════════════
#  XABAR HANDLER
# ═══════════════════════════════════════════════════════

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg  = update.message
    if not msg:
        return

    upsert_user(user.id, user.username or "", user.full_name or "")

    if get_setting("maintenance_mode","0") == "1" and not is_admin(user.id):
        await msg.reply_text("🔧 Bot texnik ishlar uchun to'xtatilgan.")
        return

    u = get_user(user.id)
    if u and u["is_banned"]:
        await msg.reply_text("🚫 Siz bloklangansiz.")
        return

    # Majburiy kanal
    if not await check_mandatory_channel(context.bot, user.id):
        channel = get_setting("mandatory_channel","")
        await msg.reply_text(
            f"📢 <b>Botdan foydalanish uchun kanalga obuna bo'ling!</b>\n\n"
            f"Kanal: {esc(channel)}",
            parse_mode=H,
            reply_markup=_mandatory_channel_kb()
        )
        return

    # Admin holatida bo'lsa
    if is_admin(user.id) and context.user_data.get("adm_state"):
        from handlers.admin import admin_message
        await admin_message(update, context)
        return

    # Userbot jarayoni
    from handlers.userbot import userbot_message_handler
    if await userbot_message_handler(update, context):
        return

    # To'lov screenshoti
    if msg.photo and context.user_data.get("waiting_payment"):
        await _handle_payment_photo(update, context)
        return

    state = user_states.get(user.id)
    text  = (msg.text or "").strip()

    if state == STATE_COMPLAINT:
        if len(text) < 5:
            await msg.reply_text("⚠️ Kamida 5 ta belgi kiriting.")
            return
        cid = submit_complaint(user.id, user.username or "", text)
        user_states.pop(user.id, None)
        for aid in os.getenv("ADMIN_IDS","").split(","):
            try:
                await context.bot.send_message(
                    int(aid.strip()),
                    f"📋 <b>Yangi shikoyat #{cid}</b>\n\n"
                    f"👤 @{esc(user.username or str(user.id))} (<code>{user.id}</code>)\n\n"
                    f"{esc(text)}",
                    parse_mode=H
                )
            except Exception:
                pass
        await msg.reply_text(f"✅ Shikoyat qabul qilindi (#{cid}).", reply_markup=_main_kb(user.id))
        return

    if state == STATE_REVIEW_TEXT:
        rating = context.user_data.get("pending_review_rating", 5)
        text_val = text
        if len(text_val) < 3:
            await msg.reply_text("❌ Sharh matni juda qisqa! Kamida 3 ta belgi yozing.")
            return
        if len(text_val) > 300:
            text_val = text_val[:300]

        ok, resp_msg = upsert_review(user.id, rating, text_val)
        user_states.pop(user.id, None)
        context.user_data.pop("pending_review_rating", None)
        log_user_action(user.id, "submit_review", f"rating={rating}")

        await msg.reply_text(
            f"{resp_msg}\n\n"
            f"Baho: <b>{'⭐' * rating} ({rating}/5)</b>\n"
            f"Sharh: «<i>{esc(text_val)}</i>»",
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⭐ Sharhlar bo'limiga qaytish", callback_data="reviews_menu")]])
        )
        return

    if state == STATE_SEARCH:
        user_states.pop(user.id, None)
        await _do_search(update, context, text)
        return

    if state == STATE_INET:
        user_states.pop(user.id, None)
        await _do_internet_search(update, context, text)
        return

    if state == STATE_URL:
        user_states.pop(user.id, None)
        if text.startswith("http"):
            await _process_url(msg, context, text, user)
        else:
            await msg.reply_text("⚠️ URL http:// bilan boshlanishi kerak.")
        return

    if text.startswith("http"):
        await _process_url(msg, context, text, user)
        return

    if text:
        log_user_action(user.id, "search_text", text)
        await _do_search(update, context, text)
        return


# ═══════════════════════════════════════════════════════
#  URL QA'TA ISHLASH
# ═══════════════════════════════════════════════════════

async def _process_url(msg, context, url: str, user):
    can, reason = _can_download(user.id)
    if not can:
        await msg.reply_text(
            "⛔ <b>Bepul limit tugadi!</b>\n\n"
            "Davom etish uchun obuna oling yoki do'st taklif qiling.",
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Obuna olish", callback_data="buy_subscription")],
                [InlineKeyboardButton("👥 Referral",    callback_data="referral")],
            ])
        )
        return

    wait = await msg.reply_text("🔎 Sahifa o'qilmoqda...")
    try:
        movie = await scrape_movie(url)
    except Exception as e:
        logger.error(f"Scrape: {e}")
        movie = None

    if not movie:
        await wait.edit_text("❌ Sahifadan ma'lumot olib bo'lmadi. URL to'g'riligini tekshiring.")
        return

    if not movie.links:
        await wait.edit_text(
            f"🎬 <b>{esc(movie.title)}</b>\n\n❌ Yuklab olish havolasi topilmadi.\n\n"
            f"<i>Bu sayt JavaScript orqali yuklar yoki maxsus himoyalangan bo'lishi mumkin.</i>",
            parse_mode=H
        )
        return

    context.bot_data[f"movie_{user.id}"] = movie
    await wait.delete()
    await _send_movie_card(msg, context, movie, user)


async def _send_movie_card(msg, context, movie: MovieInfo, user):
    lines = [f"🎬 <b>{esc(movie.title)}</b>"]
    if movie.year:     lines.append(f"📅 Yil: {esc(movie.year)}")
    if movie.quality:  lines.append(f"📺 Sifat: {esc(movie.quality)}")
    if movie.language: lines.append(f"🌐 Til: {esc(movie.language)}")
    if movie.genre:    lines.append(f"🎭 Janr: {esc(movie.genre)}")
    if movie.description:
        lines.append(f"\n<i>{esc(movie.description[:250])}...</i>")
    lines.append(f"\n🔢 Havolalar: {len(movie.links)} ta")
    caption = "\n".join(lines)

    keyboard = _build_movie_kb(movie, user.id, context)
    try:
        if movie.poster_url and movie.poster_url.startswith("http"):
            await msg.reply_photo(photo=movie.poster_url, caption=caption,
                                  parse_mode=H, reply_markup=keyboard)
            return
    except Exception:
        pass
    await msg.reply_text(caption, parse_mode=H, reply_markup=keyboard)


def _build_movie_kb(movie: MovieInfo, user_id: int, context) -> InlineKeyboardMarkup:
    rows = []
    if movie.has_parts():
        row = []
        for part in movie.get_parts():
            plinks = movie.get_links_for_part(part)
            quals  = list(dict.fromkeys(l.quality for l in plinks))
            ql     = f"({quals[0]})" if len(quals) == 1 else ""
            row.append(InlineKeyboardButton(
                f"📹 {part}-qism {ql}".strip(),
                callback_data=f"movie_part_{user_id}_{part}"
            ))
            if len(row) == 2:
                rows.append(row); row = []
        if row: rows.append(row)
    else:
        row = []
        for i, link in enumerate(movie.links[:12]):
            key = f"dl_{user_id}_{i}"
            context.bot_data[key] = {
                "url": link.url, "title": movie.title,
                "quality": link.quality, "part": link.part, "size": link.size,
            }
            label = link.display_label() or f"Variant {i+1}"
            if link.size: label += f" ({link.size})"
            row.append(InlineKeyboardButton(f"⬇️ {label}", callback_data=f"dl_{key}"))
            if len(row) == 2:
                rows.append(row); row = []
        if row: rows.append(row)

    if check_subscription(user_id) or is_admin(user_id):
        rows.append([InlineKeyboardButton("🌐 Internet qidirish", callback_data="internet_search")])
    rows.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


async def _show_part_qualities(q, context, data: str, user):
    parts = data.split("_")
    part  = int(parts[-1])
    movie: MovieInfo = context.bot_data.get(f"movie_{user.id}")
    if not movie:
        await q.answer("❌ Kino ma'lumoti topilmadi. Qaytadan URL yuboring.", show_alert=True)
        return
    part_links = movie.get_links_for_part(part)
    rows = []
    row  = []
    for i, link in enumerate(part_links[:10]):
        key = f"dl_{user.id}_p{part}_{i}"
        context.bot_data[key] = {
            "url": link.url, "title": movie.title,
            "quality": link.quality, "part": part, "size": link.size,
        }
        label = link.quality or f"Variant {i+1}"
        if link.size: label += f" ({link.size})"
        row.append(InlineKeyboardButton(f"⬇️ {label}", callback_data=f"dl_{key}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Qismlar", callback_data="back_main")])
    try:
        await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════
#  QIDIRISH
# ═══════════════════════════════════════════════════════

async def _do_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str):
    msg  = update.message
    user = update.effective_user
    wait = await msg.reply_text(f"🔍 <b>{esc(query_text)}</b> qidirilmoqda...", parse_mode=H)

    try:
        results = await search_movies(query_text)
    except Exception as e:
        logger.error(f"Search: {e}")
        results = []

    if not results:
        await wait.edit_text(
            "❌ Natija topilmadi. Boshqacha nom kiriting.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]])
        )
        return

    rows = []
    for i, r in enumerate(results[:10]):
        key = f"{user.id}_{i}"
        context.bot_data[f"sres_{key}"] = r["url"]
        domain = re.search(r"https?://([^/]+)", r["url"])
        dm     = domain.group(1) if domain else ""
        icon   = "🟡" if "uzmovie" in dm else ("🔵" if "uzmovi.tv" in dm else ("🟠" if "kinolar" in dm else "🟢"))
        title  = r["title"][:38]
        rows.append([InlineKeyboardButton(f"{icon} {title}", callback_data=f"search_pick_{key}")])

    rows.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
    await wait.edit_text(
        f"🔍 <b>'{esc(query_text)}'</b> bo'yicha {len(results)} ta natija:\n\n"
        f"🟢 asilmedia  🟡 uzmovie  🔵 uzmovi.tv  🟠 kinolar.tv",
        parse_mode=H, reply_markup=InlineKeyboardMarkup(rows)
    )


async def _do_internet_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str):
    msg  = update.message
    user = update.effective_user
    wait = await msg.reply_text(f"🌐 Internet qidirilmoqda: <b>{esc(query_text)}</b>...", parse_mode=H)
    try:
        results = await internet_search_movie(query_text)
    except Exception as e:
        logger.error(f"ISearch: {e}")
        results = []

    if not results:
        await wait.edit_text(
            "❌ Internet'dan natija topilmadi.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]])
        )
        return

    rows = []
    for i, r in enumerate(results[:6]):
        key = f"i_{user.id}_{i}"
        context.bot_data[f"sres_{key}"] = r["url"]
        rows.append([InlineKeyboardButton(f"🌐 {r['title'][:40]}", callback_data=f"search_pick_{key}")])
    rows.append([InlineKeyboardButton("🔙", callback_data="back_main")])
    await wait.edit_text(
        f"🌐 <b>Internet natijalari</b> ({len(results)} ta):",
        parse_mode=H, reply_markup=InlineKeyboardMarkup(rows)
    )


async def _cancel_user_download(user_id: int, message):
    task = active_downloads.get(user_id)
    if task and not task.done():
        task.cancel()
        try:
            await message.edit_text(
                "❌ <b>Yuklash to'xtatildi!</b>\n\nFoydalanuvchi tomonidan bekor qilindi.",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")
                ]])
            )
        except Exception:
            pass
    else:
        try:
            await message.edit_text(
                "❌ <b>Yuklash jarayoni topilmadi yoki allaqachon yakunlangan.</b>",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")
                ]])
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════
#  YUKLAB OLISH — Telegram kanal storage
# ═══════════════════════════════════════════════════════

async def _handle_download(q, context: ContextTypes.DEFAULT_TYPE, data: str, user):
    key       = data[3:]
    link_data = context.bot_data.get(key)
    if not link_data:
        await q.answer("❌ Havola muddati o'tgan. Qaytadan URL yuboring.", show_alert=True)
        return

    can, reason = _can_download(user.id)
    if not can:
        await q.answer("⛔ Limit tugadi! Obuna oling.", show_alert=True)
        return

    if user.id in active_downloads:
        await q.answer("⚠️ Sizda hozirda yuklash jarayoni faol. Uni to'xtatib keyin boshlashingiz mumkin.", show_alert=True)
        return

    filepath = ""
    dl_id = 0

    try:
        active_downloads[user.id] = asyncio.current_task()
        url     = link_data["url"]
        title   = link_data.get("title","Kino")
        quality = link_data.get("quality","HD")
        part    = link_data.get("part", 0)
        size    = link_data.get("size","")

        dl_id   = log_download(user.id, url, title, quality, part)
        channel = get_setting("storage_channel","")

        # ── Kanalda saqlangan fayl bormi? ──
        stored = get_stored_file(url)
        if stored:
            caption = _build_caption(title, part, quality, stored["file_size"] or 0)
            ok = False
            if stored["file_id"]:
                ok = await send_by_file_id(context.bot, user.id, stored["file_id"], caption)
            if not ok and channel and stored["msg_id"]:
                ok = await forward_from_channel(context.bot, channel, stored["msg_id"], user.id)
            if ok:
                _apply_limit(user.id, reason)
                update_download(dl_id, stored["file_id"] or "", stored["file_size"] or 0, "done")
                await q.answer("✅ Yuborildi!")
                return

        # ── URL resolve ──
        wait = await q.message.reply_text(
            f"🔎 Havola tekshirilmoqda...\n"
            f"🎬 <b>{esc(title)}</b>"
            + (f" — {part}-qism" if part else "")
            + (f" [{esc(quality)}]" if quality else ""),
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ To'xtatish", callback_data=f"cancel_dl_{user.id}")
            ]])
        )

        real_url = await resolve_real_url(url)

        from utils.downloader import format_progress_bar

        async def dl_progress(downloaded: int, total: int, pct: float, speed_bps: float, elapsed_sec: float):
            try:
                bar_text = format_progress_bar(downloaded, total, speed_bps, elapsed_sec, stage="⬇️ Serverga yuklanmoqda")
                await wait.edit_text(
                    f"🎬 <b>{esc(title)}</b>" + (f" — {part}-qism" if part else "") + "\n\n" + bar_text,
                    parse_mode=H,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ To'xtatish", callback_data=f"cancel_dl_{user.id}")
                    ]])
                )
            except Exception:
                pass

        async def ul_progress(current: int, total: int, pct: float, speed_bps: float, elapsed_sec: float):
            try:
                bar_text = format_progress_bar(current, total, speed_bps, elapsed_sec, stage="📤 Telegram'ga yuklanmoqda")
                await wait.edit_text(
                    f"🎬 <b>{esc(title)}</b>" + (f" — {part}-qism" if part else "") + "\n\n" + bar_text,
                    parse_mode=H,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ To'xtatish", callback_data=f"cancel_dl_{user.id}")
                    ]])
                )
            except Exception:
                pass

        if DOWNLOAD_SEMAPHORE.locked():
            try:
                await wait.edit_text(
                    f"🎬 <b>{esc(title)}</b>" + (f" — {part}-qism" if part else "") + "\n\n"
                    f"⏳ <b>Server yuklangan!</b> So'rovingiz yuklash navbatiga qo'shildi.\n"
                    f"<i>Navbatingiz kelishi bilan yuklash avtomatik boshlanadi. Iltimos, kuting...</i>",
                    parse_mode=H,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ To'xtatish", callback_data=f"cancel_dl_{user.id}")
                    ]])
                )
            except Exception:
                pass

        async with DOWNLOAD_SEMAPHORE:
            filename = make_filename(title, quality, part)
            filepath = await download_file(real_url, filename, progress_cb=dl_progress)

        if not filepath:
            await wait.edit_text(
                "❌ <b>Yuklab olishda xatolik!</b>\n\n"
                "Fayl mavjud emas, juda katta yoki himoyalangan.\n"
                "Boshqa sifatni sinab ko'ring.",
                parse_mode=H
            )
            update_download(dl_id, "", 0, "failed")
            return

        mb      = get_file_size_mb(filepath)
        caption = _build_caption(title, part, quality, int(mb * 1024 * 1024))

        file_id = ""
        msg_id  = 0

        try:
            if mb > 50.0:
                session = get_userbot_session(user.id)
                if session:
                    await wait.edit_text(
                        f"📤 Userbot orqali Telegram'ga yuborilmoqda... ({mb:.1f} MB)", 
                        parse_mode=H,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("❌ To'xtatish", callback_data=f"cancel_dl_{user.id}")
                        ]])
                    )
                    from handlers.userbot import upload_file_via_userbot
                    target_chat = channel if channel else user.id
                    ok, msg_id, ub_err = await upload_file_via_userbot(user.id, target_chat, filepath, caption, progress_cb=ul_progress)
                    if ok:
                        file_id = f"ub_{msg_id}"
                        if channel:
                            store_channel_file(url, msg_id, title, quality, part, file_id, int(mb*1024*1024))
                            await forward_from_channel(context.bot, channel, msg_id, user.id)
                            try:
                                await wait.delete()
                            except Exception:
                                pass
                        else:
                            # Direct to Saved Messages
                            await wait.edit_text(
                                f"🎉 <b>Kino muvaffaqiyatli yuklandi!</b>\n\n"
                                f"🎬 <b>{esc(title)}</b> ({mb:.1f} MB)\n\n"
                                f"📁 <b>Eslatma:</b>\n"
                                f"Fayl hajmi 50MB dan katta bo'lgani uchun Telethon Userbotingiz orqali Telegram'dagi <b>Saqlangan xabarlar (Saved Messages / Избранное)</b> papkangizga yuborildi!\n\n"
                                f"👇 Telegram'dagi 'Saved Messages' bo'limingizni tekshiring!",
                                parse_mode=H,
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")]])
                            )
                        _apply_limit(user.id, reason)
                        update_download(dl_id, file_id, int(mb * 1024 * 1024), "done")
                    else:
                        update_download(dl_id, "", 0, "failed")
                        await wait.edit_text(f"❌ Userbot yuborishda xatolik: {esc(ub_err)}", parse_mode=H)
                else:
                    update_download(dl_id, "", 0, "failed")
                    await wait.edit_text(
                        f"⚠️ <b>Fayl hajmi {mb:.1f} MB (50MB dan katta)!</b>\n\n"
                        f"Telegram Bot API orqali 50MB dan katta fayllarni yuborib bo'lmaydi.\n\n"
                        f"Katta fayllarni yuklash uchun /connect_api orqali Userbotingizni ulang!",
                        parse_mode=H,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔐 Userbot ulash", callback_data="userbot_menu")]
                        ])
                    )
                return

            await wait.edit_text(
                f"📤 Telegramga yuborilmoqda... ({mb:.1f} MB)",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ To'xtatish", callback_data=f"cancel_dl_{user.id}")
                ]])
            )

            if channel:
                result = await upload_to_channel(context.bot, channel, filepath, caption)
                if result:
                    msg_id, file_id = result
                    store_channel_file(url, msg_id, title, quality, part, file_id, int(mb*1024*1024))
                    await forward_from_channel(context.bot, channel, msg_id, user.id)
                else:
                    await _send_to_user(q.message, filepath, caption)
            else:
                await _send_to_user(q.message, filepath, caption)

            _apply_limit(user.id, reason)
            update_download(dl_id, file_id, int(mb * 1024 * 1024), "done")
            try:
                await wait.delete()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Upload inner error: {e}")
            raise e

    except asyncio.CancelledError:
        logger.info(f"Download for user {user.id} was cancelled.")
        if dl_id:
            update_download(dl_id, "", 0, "cancelled")
        return

    except Exception as e:
        logger.error(f"Upload: {e}")
        if dl_id:
            update_download(dl_id, "", 0, "failed")
        try:
            await wait.edit_text(f"❌ Yuborishda xatolik: {esc(str(e)[:150])}", parse_mode=H)
        except Exception:
            pass
    finally:
        active_downloads.pop(user.id, None)
        if filepath:
            delete_file(filepath)


def _build_caption(title: str, part: int, quality: str, size_bytes: int) -> str:
    lines = [f"🎬 {title}"]
    if part:         lines.append(f"📹 {part}-qism")
    if quality:      lines.append(f"📺 {quality}")
    if size_bytes > 0: lines.append(f"📦 {size_bytes/1024/1024:.1f} MB")
    bot_un = get_setting("bot_username","")
    if bot_un:       lines.append(f"🤖 @{bot_un}")
    return "\n".join(lines)


async def _send_to_user(msg, filepath: str, caption: str):
    with open(filepath, "rb") as f:
        await msg.reply_document(document=f, caption=caption)


def _apply_limit(user_id: int, reason: str):
    if   reason == "free":  increment_free_used(user_id)
    elif reason == "bonus": use_bonus_dl(user_id)


# ═══════════════════════════════════════════════════════
#  TO'LOV SCREENSHOTI
# ═══════════════════════════════════════════════════════

async def _handle_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user  = update.effective_user
    msg   = update.message
    pd    = context.user_data.get("waiting_payment", {})
    photo = msg.photo[-1]
    fid   = photo.file_id

    tid    = pd.get("tariff_id", 0)
    cid    = pd.get("card_id",   0)
    amount = pd.get("amount",   0.0)
    tariff = get_tariff(tid) if tid else None

    pay_id = submit_payment(user.id, tid, amount, cid, fid)
    context.user_data.pop("waiting_payment", None)

    tname = tariff["name"] if tariff else "Noma'lum"
    days  = tariff["days"] if tariff else 30

    for aid in os.getenv("ADMIN_IDS","").split(","):
        try:
            await context.bot.send_photo(
                int(aid.strip()), photo=fid,
                caption=(
                    f"💳 <b>Yangi to'lov #{pay_id}</b>\n\n"
                    f"👤 @{esc(user.username or str(user.id))} (<code>{user.id}</code>)\n"
                    f"🏷 {esc(tname)} ({days} kun)\n"
                    f"💰 {amount:,.0f} so'm"
                ),
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_payment_{pay_id}"),
                    InlineKeyboardButton("❌ Rad etish",  callback_data=f"reject_payment_{pay_id}"),
                ]])
            )
        except Exception as e:
            logger.error(f"Admin notify: {e}")

    await msg.reply_text(
        f"✅ <b>To'lovingiz qabul qilindi!</b> (#{pay_id})\n\n"
        f"🏷 {esc(tname)}\n⏳ 10–30 daqiqada ko'rib chiqiladi.",
        parse_mode=H, reply_markup=_main_kb(user.id)
    )
