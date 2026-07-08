import html
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.database import (
    get_scouting_settings, save_scouting_settings,
    get_scouting_leads_for_user, get_scouting_logs, clear_scouting_logs,
    get_userbot_session
)
from handlers.scout_agent import start_scout_agent, stop_scout_agent

H = ParseMode.HTML

def esc(t: str) -> str:
    return html.escape(str(t or ""))

async def show_scout_dashboard(q_or_msg, user, context: ContextTypes.DEFAULT_TYPE):
    """
    Renders the main AI Scouting Agent Control Panel.
    """
    user_id = user.id
    settings = get_scouting_settings(user_id)
    ub_session = get_userbot_session(user_id)
    
    # Calculate stats
    leads = get_scouting_leads_for_user(user_id)
    total_found = len(leads)
    total_pitched = len([l for l in leads if l["status"] in ["pitched", "replied", "interested"]])
    total_replied = len([l for l in leads if l["status"] in ["replied", "interested"]])
    total_interested = len([l for l in leads if l["status"] == "interested"])
    
    status_text = "🟢 <b>FAOL (Ishlamoqda)</b>" if settings.get("is_active") else "🔴 <b>TO'XTATILGAN</b>"
    
    ub_status = "🟢 Ulangan" if ub_session else "🔴 Ulanmagan"
    
    text = (
        f"🕵️‍♂️ <b>AI Sales & Scouting Agent boshqaruv paneli</b>\n\n"
        f"Ushbu tizim sizning nomingizdan O'zbekistondagi kichik sexlar, korxonalar va do'konlarni qidirib topadi, "
        f"ularning sayti yo'qligini tekshiradi va ulaydigan Telegram bot xizmatlarimizni individual va samimiy ohangda "
        f"shaxsiy accountingiz (Userbot) orqali taklif qiladi!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Agent Holati:</b> {status_text}\n"
        f"📱 <b>Shaxsiy Userbot:</b> <code>{ub_status}</code>\n"
        f"🎯 <b>Taklif (Offer):</b> <code>{esc(settings.get('pitch_offer'))}</code>\n\n"
        f"🗂️ <b>Qidiruv sohalari (Sohalar):</b>\n<i>{esc(settings.get('categories'))}</i>\n\n"
        f"📈 <b>Sotuv Voronkasi (Statistika):</b>\n"
        f"🔍 Topilgan kompaniyalar: <b>{total_found} ta</b>\n"
        f"🚀 Pitch yuborilganlar: <b>{total_pitched} ta</b>\n"
        f"🔥 Javob qaytarganlar: <b>{total_replied} ta</b>\n"
        f"🤝 Qiziqish bildirganlar (Warm): <b>{total_interested} ta</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>👇 Quyidagi tugmalar orqali agentni boshqaring:</i>"
    )
    
    toggle_btn = (
        InlineKeyboardButton("🔴 Agentni To'xtatish", callback_data="scout_toggle")
        if settings.get("is_active") else
        InlineKeyboardButton("🚀 Agentni Boshlash", callback_data="scout_toggle")
    )
    
    kb = InlineKeyboardMarkup([
        [toggle_btn],
        [
            InlineKeyboardButton("⚙️ Sohalarni sozlash", callback_data="scout_edit_cats"),
            InlineKeyboardButton("📝 Taklifni sozlash", callback_data="scout_edit_offer")
        ],
        [
            InlineKeyboardButton("🔥 Issiq Leadlar", callback_data="scout_view_leads_warm"),
            InlineKeyboardButton("📊 Barcha Leadlar", callback_data="scout_view_leads_all")
        ],
        [
            InlineKeyboardButton("📜 Jurnal (Logs)", callback_data="scout_view_logs"),
            InlineKeyboardButton("🔙 Bosh Menyu", callback_data="back_main")
        ]
    ])
    
    if hasattr(q_or_msg, "edit_message_text"):
        await q_or_msg.edit_message_text(text, parse_mode=H, reply_markup=kb, disable_web_page_preview=True)
    else:
        await q_or_msg.reply_text(text, parse_mode=H, reply_markup=kb, disable_web_page_preview=True)


async def handle_scout_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handles all callback interactions for the scouting menus.
    Returns True if handled, False otherwise.
    """
    q = update.callback_query
    data = q.data
    user = update.effective_user
    user_id = user.id
    
    from handlers.user import user_states
    
    if data == "scout_menu":
        await show_scout_dashboard(q, user, context)
        return True
        
    elif data == "scout_toggle":
        settings = get_scouting_settings(user_id)
        ub_session = get_userbot_session(user_id)
        
        if not ub_session:
            await q.answer("❌ Avval shaxsiy Userbotingizni ulang! (/connect_api)", show_alert=True)
            return True
            
        new_active = 0 if settings.get("is_active") else 1
        
        save_scouting_settings(
            user_id, is_active=new_active,
            categories=settings["categories"], pitch_offer=settings["pitch_offer"],
            daily_limit=settings["daily_limit"], min_delay=settings["min_delay"], max_delay=settings["max_delay"]
        )
        
        if new_active:
            await start_scout_agent(user_id, context.application)
            await q.answer("🚀 AI Scouting Agent muvaffaqiyatli ishga tushirildi!", show_alert=True)
        else:
            await stop_scout_agent(user_id)
            await q.answer("🔴 AI Scouting Agent to'xtatildi.", show_alert=True)
            
        await show_scout_dashboard(q, user, context)
        return True
        
    elif data == "scout_edit_cats":
        settings = get_scouting_settings(user_id)
        user_states[user_id] = "scout_waiting_categories"
        text = (
            "⚙️ <b>Qidiruv sohalari va kalit so'zlarini sozlash</b>\n\n"
            f"Hozirgi kalit so'zlar:\n<code>{esc(settings.get('categories'))}</code>\n\n"
            "✍️ Yangi kalit so'zlarni <b>vergul (,) bilan ajratilgan holda</b> yozib yuboring.\n"
            "<i>Masalan: mebel sexi, kuryerlik xizmati, tikuv sexi, go'zallik saloni</i>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Bekor qilish", callback_data="scout_menu")]])
        await q.edit_message_text(text, parse_mode=H, reply_markup=kb)
        return True
        
    elif data == "scout_edit_offer":
        settings = get_scouting_settings(user_id)
        user_states[user_id] = "scout_waiting_offer"
        text = (
            "📝 <b>Tijoriy taklif (Offer) shartlarini sozlash</b>\n\n"
            f"Hozirgi taklif sharti: <code>{esc(settings.get('pitch_offer'))}</code>\n\n"
            "✍️ Yangi taklif matnini (masalan, narxi va yetkazib berish vaqtini) qisqa qilib yozib yuboring.\n"
            "<i>Masalan: Atigi 3 kunda eng qulay Telegram bot, jami $120</i>"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Bekor qilish", callback_data="scout_menu")]])
        await q.edit_message_text(text, parse_mode=H, reply_markup=kb)
        return True
        
    elif data.startswith("scout_view_leads_"):
        lead_type = data.split("_")[3] # warm or all
        leads = get_scouting_leads_for_user(user_id)
        
        if lead_type == "warm":
            leads = [l for l in leads if l["status"] in ["replied", "interested"]]
            title = "🔥 <b>Sizning Issiq (Warm) Leadlaringiz:</b>"
        else:
            title = "📊 <b>Barcha Topilgan Leadlar:</b>"
            
        if not leads:
            text = f"{title}\n\nHozircha hech qanday lead mavjud emas."
        else:
            text = f"{title}\n\n"
            for idx, lead in enumerate(leads[:20], 1):
                status_emoji = "🔍"
                if lead["status"] == "pitched": status_emoji = "🚀"
                elif lead["status"] == "replied": status_emoji = "🔥"
                elif lead["status"] == "interested": status_emoji = "🤝"
                elif lead["status"] == "failed": status_emoji = "❌"
                
                text += (
                    f"{idx}. {status_emoji} <b>{esc(lead['business_name'])}</b>\n"
                    f"   📞 {esc(lead['phone'])} | 🏷️ {esc(lead['industry'])}\n"
                    f"   📍 {esc(lead['address'][:40])}...\n"
                    f"   📅 {lead['created_at']}\n\n"
                )
                
            if len(leads) > 20:
                text += f"<i>...va yana {len(leads) - 20} ta mijoz.</i>"
                
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="scout_menu")]])
        await q.edit_message_text(text, parse_mode=H, reply_markup=kb)
        return True
        
    elif data == "scout_view_logs":
        logs = get_scouting_logs(user_id, limit=20)
        
        if not logs:
            log_text = "Hozircha tizim jurnallari bo'sh."
        else:
            log_text = "\n".join(logs)
            
        text = (
            "📜 <b>AI Scouting Agent Tizim Jurnali (Logs)</b>\n\n"
            f"<pre>{esc(log_text)}</pre>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🧹 Jurnalni tozalash", callback_data="scout_clear_logs")],
            [InlineKeyboardButton("🔄 Yangilash", callback_data="scout_view_logs")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="scout_menu")]
        ])
        await q.edit_message_text(text, parse_mode=H, reply_markup=kb)
        return True
        
    elif data == "scout_clear_logs":
        clear_scouting_logs(user_id)
        await q.answer("🧹 Jurnal tozalandi.")
        # Refresh logs view
        q.data = "scout_view_logs"
        await handle_scout_callbacks(update, context)
        return True
        
    return False


async def handle_scout_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handles user text inputs for the scouting settings.
    Returns True if handled, False otherwise.
    """
    user = update.effective_user
    user_id = user.id
    msg = update.message
    
    from handlers.user import user_states
    state = user_states.get(user_id)
    
    if not state or not state.startswith("scout_waiting_"):
        return False
        
    text_input = (msg.text or "").strip()
    settings = get_scouting_settings(user_id)
    
    if state == "scout_waiting_categories":
        if not text_input or len(text_input) < 3:
            await msg.reply_text("❌ Kalit so'zlar matni juda qisqa. Qayta urinib ko'ring:")
            return True
            
        save_scouting_settings(
            user_id, is_active=settings["is_active"],
            categories=text_input, pitch_offer=settings["pitch_offer"],
            daily_limit=settings["daily_limit"], min_delay=settings["min_delay"], max_delay=settings["max_delay"]
        )
        
        user_states.pop(user_id, None)
        await msg.reply_text(
            f"✅ <b>Qidiruv sohalari muvaffaqiyatli yangilandi!</b>\n\nYangi qiymat:\n<code>{esc(text_input)}</code>",
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🕵️‍♂️ Boshqaruv paneliga qaytish", callback_data="scout_menu")]])
        )
        return True
        
    elif state == "scout_waiting_offer":
        if not text_input or len(text_input) < 5:
            await msg.reply_text("❌ Tijoriy taklif matni juda qisqa. Qayta urinib ko'ring:")
            return True
            
        save_scouting_settings(
            user_id, is_active=settings["is_active"],
            categories=settings["categories"], pitch_offer=text_input,
            daily_limit=settings["daily_limit"], min_delay=settings["min_delay"], max_delay=settings["max_delay"]
        )
        
        user_states.pop(user_id, None)
        await msg.reply_text(
            f"✅ <b>Tijoriy taklif (Offer) muvaffaqiyatli yangilandi!</b>\n\nYangi qiymat:\n<code>{esc(text_input)}</code>",
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🕵️‍♂️ Boshqaruv paneliga qaytish", callback_data="scout_menu")]])
        )
        return True
        
    return False
