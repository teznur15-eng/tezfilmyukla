"""
Admin panel — HTML parse mode.
Admin qo'shish/o'chirish + majburiy kanal + barcha sozlamalar.
"""

import os
import html
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.database import (
    is_admin, get_all_users, get_users_count, get_active_users_count,
    ban_user, unban_user, get_user,
    get_all_admins, add_admin, remove_admin,
    create_tariff, get_all_tariffs, get_tariff, toggle_tariff, delete_tariff,
    add_card, remove_card, get_all_cards, toggle_card,
    get_pending_payments, get_payment, update_payment_status, set_subscription,
    get_setting, set_setting,
    get_open_complaints, reply_complaint, get_complaint_by_id,
    search_channel_storage,
    get_detailed_statistics, get_activity_logs_for_report, log_user_action,
)
from utils.pdf_generator import PDFBuilder

logger = logging.getLogger(__name__)
H = ParseMode.HTML


def esc(text: str) -> str:
    return html.escape(str(text or ""))


def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            if update.message:
                await update.message.reply_text("⛔ Ruxsat yo'q.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Ruxsat yo'q.", show_alert=True)
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


def _admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Foydalanuvchilar",  callback_data="adm_users"),
         InlineKeyboardButton("📊 Statistika",         callback_data="adm_stats")],
        [InlineKeyboardButton("🏷 Tariflar",           callback_data="adm_tariffs"),
         InlineKeyboardButton("💳 Kartalar",           callback_data="adm_cards")],
        [InlineKeyboardButton("💰 To'lovlar",          callback_data="adm_payments"),
         InlineKeyboardButton("📋 Shikoyatlar",        callback_data="adm_complaints")],
        [InlineKeyboardButton("📢 Broadcast",          callback_data="adm_broadcast"),
         InlineKeyboardButton("⚙️ Sozlamalar",          callback_data="adm_settings")],
        [InlineKeyboardButton("📦 Kanal storage",      callback_data="adm_channel"),
         InlineKeyboardButton("🔐 Adminlar",           callback_data="adm_admins")],
        [InlineKeyboardButton("📢 Majburiy kanal",     callback_data="adm_mandatory"),
         InlineKeyboardButton("🔍 Storage qidirish",   callback_data="adm_search_storage")],
    ])


# ─── /admin ──────────────────────────────────────────────

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total   = get_users_count()
    active  = get_active_users_count()
    pending = len(get_pending_payments())
    open_c  = len(get_open_complaints())
    await update.message.reply_text(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Jami: <b>{total}</b> ta\n"
        f"🟢 Faol (7 kun): <b>{active}</b> ta\n"
        f"💰 Kutilayotgan to'lovlar: <b>{pending}</b>\n"
        f"📋 Ochiq shikoyatlar: <b>{open_c}</b>",
        parse_mode=H, reply_markup=_admin_kb()
    )


# ─── Callback dispatcher ─────────────────────────────────

@admin_only
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()
    data = q.data or ""

    try:
        if   data == "adm_stats":           await _stats(q)
        elif data == "export_pdf_report":   await _export_pdf_report(q, context)
        elif data == "adm_users":           await _users(q)
        elif data == "adm_tariffs":         await _tariffs(q)
        elif data == "adm_cards":           await _cards(q)
        elif data == "adm_payments":        await _payments(q)
        elif data == "adm_complaints":      await _complaints(q)
        elif data == "adm_broadcast":       await _broadcast_prompt(q, context)
        elif data == "adm_settings":        await _settings(q)
        elif data == "adm_channel":         await _channel_info(q)
        elif data == "adm_admins":          await _admins_panel(q)
        elif data == "adm_mandatory":       await _mandatory_panel(q)
        elif data == "adm_search_storage":  await _search_storage_prompt(q, context)
        elif data == "adm_back":            await _admin_main(q)

        elif data.startswith("approve_payment_"):
            pid = int(data.split("_")[2])
            await _approve_payment(q, context, pid)
        elif data.startswith("reject_payment_"):
            pid = int(data.split("_")[2])
            await _reject_payment(q, context, pid)

        elif data.startswith("adm_toggle_tariff_"):
            toggle_tariff(int(data.split("_")[3]))
            await _tariffs(q)
        elif data.startswith("adm_del_tariff_"):
            delete_tariff(int(data.split("_")[3]))
            await _tariffs(q)
        elif data == "adm_add_tariff":
            context.user_data["adm_state"] = "add_tariff"
            await q.edit_message_text(
                "🏷 <b>Yangi tarif</b>\n\n<code>nom|narx|kunlar|tavsif</code>\n\n"
                "Masalan:\n<code>Premium|9000|30|Bir oylik premium</code>",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_tariffs")]])
            )

        elif data.startswith("adm_toggle_card_"):
            toggle_card(int(data.split("_")[3]))
            await _cards(q)
        elif data.startswith("adm_del_card_"):
            remove_card(int(data.split("_")[3]))
            await _cards(q)
        elif data == "adm_add_card":
            context.user_data["adm_state"] = "add_card"
            await q.edit_message_text(
                "💳 <b>Yangi karta</b>\n\n<code>raqam|egasi|bank</code>\n\n"
                "Masalan:\n<code>8600 1234 5678 9012|Alisher|Uzcard</code>",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_cards")]])
            )

        elif data.startswith("adm_ban_"):
            uid = int(data.split("_")[2])
            ban_user(uid)
            await q.edit_message_text(
                f"🚫 Foydalanuvchi <code>{uid}</code> bloklandi.",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_users")]])
            )
        elif data.startswith("adm_unban_"):
            uid = int(data.split("_")[2])
            unban_user(uid)
            await q.edit_message_text(
                f"✅ Foydalanuvchi <code>{uid}</code> blokdan chiqarildi.",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_users")]])
            )

        elif data.startswith("adm_resolve_"):
            cid = int(data.split("_")[2])
            context.user_data["adm_state"] = f"resolve_{cid}"
            await q.edit_message_text(
                f"📋 Shikoyat #{cid} ga javob yozing:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_complaints")]])
            )

        elif data == "adm_set_channel":
            context.user_data["adm_state"] = "set_channel"
            cur = get_setting("storage_channel","")
            await q.edit_message_text(
                f"📦 <b>Storage kanal ID</b>\n\n"
                f"Joriy: <code>{esc(cur) or 'sozlanmagan'}</code>\n\n"
                f"• <code>-1001234567890</code> (private)\n"
                f"• <code>@kanalUsername</code> (public)\n\n"
                f"⚠️ Bot kanalga <b>admin</b> bo'lishi kerak!",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_channel")]])
            )
        elif data == "adm_set_mandatory":
            context.user_data["adm_state"] = "set_mandatory"
            cur = get_setting("mandatory_channel","")
            await q.edit_message_text(
                f"📢 <b>Majburiy obuna kanali</b>\n\n"
                f"Joriy: <code>{esc(cur) or 'sozlanmagan'}</code>\n\n"
                f"Formatlar:\n"
                f"• <code>@kanalUsername</code> — public kanal\n"
                f"• <code>-1001234567890</code> — private kanal\n"
                f"• O'chirish uchun: <code>0</code>\n\n"
                f"⚠️ Bot kanalga admin bo'lishi kerak!",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_mandatory")]])
            )
        elif data == "adm_set_botusername":
            context.user_data["adm_state"] = "set_botusername"
            await q.edit_message_text(
                "🤖 Bot username kiriting (@ siz):\nMasalan: <code>MovieBotUz</code>",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_settings")]])
            )
        elif data == "adm_set_free":
            context.user_data["adm_state"] = "set_free"
            cur = get_setting("free_downloads","1")
            await q.edit_message_text(
                f"🆓 Bepul limit (hozir: {cur}).\nYangi sonni kiriting:",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_settings")]])
            )
        elif data == "adm_set_welcome":
            context.user_data["adm_state"] = "set_welcome"
            await q.edit_message_text(
                "👋 Yangi xush kelibsiz xabarini yozing:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_settings")]])
            )
        elif data == "adm_set_start_photo":
            context.user_data["adm_state"] = "set_start_photo"
            cur = get_setting("start_photo", "")
            await q.edit_message_text(
                f"🖼 <b>Start uchun Banner Rasm (URL yoki photo_id)</b>\n\n"
                f"Joriy: <code>{esc(cur) or 'Default rasm'}</code>\n\n"
                f"Rasm havolasini (https://...) yuboring yoki o'chirish uchun <code>0</code> deb yozing:",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_settings")]])
            )
        elif data == "adm_maintenance_on":
            set_setting("maintenance_mode","1")
            await q.answer("🔧 Texnik rejim yoqildi!", show_alert=True)
            await _settings(q)
        elif data == "adm_maintenance_off":
            set_setting("maintenance_mode","0")
            await q.answer("✅ Texnik rejim o'chirildi!", show_alert=True)
            await _settings(q)

        elif data == "adm_add_admin":
            context.user_data["adm_state"] = "add_admin"
            await q.edit_message_text(
                "🔐 <b>Yangi admin qo'shish</b>\n\n"
                "Foydalanuvchi ID'sini yuboring:\n<code>123456789</code>",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_admins")]])
            )
        elif data.startswith("adm_del_admin_"):
            uid = int(data.split("_")[3])
            env_ids = [a.strip() for a in os.getenv("ADMIN_IDS","").split(",")]
            if str(uid) in env_ids:
                await q.answer("ENV admin o'chirib bo'lmaydi!", show_alert=True)
            else:
                remove_admin(uid)
                await q.answer(f"✅ Admin {uid} o'chirildi.")
                await _admins_panel(q)

    except Exception as e:
        logger.error(f"Admin callback [{data}]: {e}")
        try:
            await q.answer("Xatolik yuz berdi.", show_alert=True)
        except Exception:
            pass


# ─── Admin message handler ─────────────────────────────

@admin_only
async def admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg   = update.message
    state = context.user_data.get("adm_state","")
    text  = (msg.text or "").strip()

    if not state:
        return

    if state == "add_tariff":
        try:
            parts = [p.strip() for p in text.split("|")]
            name  = parts[0]
            price = float(parts[1].replace(",","").replace(" ",""))
            days  = int(parts[2])
            desc  = parts[3] if len(parts) > 3 else ""
            create_tariff(name, price, days, desc)
            context.user_data.pop("adm_state", None)
            await msg.reply_text(
                f"✅ Tarif qo'shildi: <b>{esc(name)}</b> — {price:,.0f} so'm / {days} kun",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Tariflar", callback_data="adm_tariffs")]])
            )
        except Exception as e:
            await msg.reply_text(f"❌ Xato: {esc(str(e))}\nFormat: <code>nom|narx|kunlar|tavsif</code>", parse_mode=H)

    elif state == "add_card":
        try:
            parts  = [p.strip() for p in text.split("|")]
            cnum   = parts[0]
            holder = parts[1]
            bank   = parts[2] if len(parts) > 2 else ""
            add_card(cnum, holder, bank)
            context.user_data.pop("adm_state", None)
            await msg.reply_text(
                f"✅ Karta qo'shildi: <code>{esc(cnum)}</code> ({esc(holder)})",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Kartalar", callback_data="adm_cards")]])
            )
        except Exception as e:
            await msg.reply_text(f"❌ Xato: {esc(str(e))}\nFormat: <code>raqam|egasi|bank</code>", parse_mode=H)

    elif state == "add_admin":
        context.user_data.pop("adm_state", None)
        if not text.isdigit():
            await msg.reply_text("❌ Faqat user ID (raqam) kiriting.")
            return
        uid = int(text)
        u   = get_user(uid)
        uname = u["username"] if u else ""
        fname = u["full_name"] if u else ""
        add_admin(uid, uname, fname, level=1, added_by=msg.from_user.id)
        await msg.reply_text(
            f"✅ Admin qo'shildi: <code>{uid}</code>"
            + (f" (@{esc(uname)})" if uname else ""),
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔐 Adminlar", callback_data="adm_admins")]])
        )

    elif state == "set_channel":
        set_setting("storage_channel", text)
        context.user_data.pop("adm_state", None)
        await msg.reply_text(
            f"✅ Storage kanal: <code>{esc(text)}</code>",
            parse_mode=H,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 Kanal", callback_data="adm_channel")]])
        )

    elif state == "set_mandatory":
        val = "" if text == "0" else text
        set_setting("mandatory_channel", val)
        context.user_data.pop("adm_state", None)
        if val:
            await msg.reply_text(
                f"✅ Majburiy obuna kanali: <code>{esc(val)}</code>\n\n"
                f"⚠️ Bot kanalga admin ekanligini tekshiring!",
                parse_mode=H,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Majburiy kanal", callback_data="adm_mandatory")]])
            )
        else:
            await msg.reply_text("✅ Majburiy obuna o'chirildi.")

    elif state == "set_botusername":
        un = text.lstrip("@")
        set_setting("bot_username", un)
        context.user_data.pop("adm_state", None)
        await msg.reply_text(f"✅ Bot username: @{esc(un)}", parse_mode=H)

    elif state == "set_free":
        if text.isdigit():
            set_setting("free_downloads", text)
            context.user_data.pop("adm_state", None)
            await msg.reply_text(f"✅ Bepul yuklab olish: {text} ta")
        else:
            await msg.reply_text("❌ Faqat raqam kiriting.")

    elif state == "set_welcome":
        set_setting("welcome_message", text)
        context.user_data.pop("adm_state", None)
        await msg.reply_text("✅ Xush kelibsiz xabari o'zgartirildi.")

    elif state == "set_start_photo":
        if msg.photo:
            val = msg.photo[-1].file_id
        else:
            val = "" if text == "0" else text
        set_setting("start_photo", val)
        context.user_data.pop("adm_state", None)
        await msg.reply_text("✅ Start xabari uchun rasm / banner sozlamasi yangilandi!")

    elif state.startswith("resolve_"):
        try:
            cid = int(state.split("_")[1])
            c   = get_complaint_by_id(cid)
            if c:
                reply_complaint(cid, text)
                try:
                    await context.bot.send_message(
                        c["user_id"],
                        f"📋 <b>Shikoyatingizga javob (#{cid})</b>\n\n"
                        f"<i>{esc(c['text'][:300])}</i>\n\n"
                        f"👑 Admin javobi:\n{esc(text)}",
                        parse_mode=H
                    )
                except Exception:
                    pass
                context.user_data.pop("adm_state", None)
                await msg.reply_text(f"✅ Javob yuborildi (#{cid}).")
        except Exception as e:
            await msg.reply_text(f"❌ {e}")

    elif state == "broadcast":
        context.user_data.pop("adm_state", None)
        users = get_all_users()
        ok, fail = 0, 0
        wait = await msg.reply_text(f"📢 {len(users)} ta foydalanuvchiga yuborilmoqda...")
        for u in users:
            try:
                if msg.photo:
                    await context.bot.send_photo(u["user_id"], msg.photo[-1].file_id, caption=text or "")
                else:
                    await context.bot.send_message(u["user_id"], text, parse_mode=H)
                ok += 1
            except Exception:
                fail += 1
        await wait.edit_text(
            f"✅ <b>Broadcast tugadi</b>\n\n✅ Yuborildi: {ok}\n❌ Xato: {fail}",
            parse_mode=H
        )

    elif state == "search_storage":
        context.user_data.pop("adm_state", None)
        results = search_channel_storage(text)
        if not results:
            await msg.reply_text(f"❌ <b>'{esc(text)}'</b> uchun hech narsa topilmadi.", parse_mode=H)
        else:
            t = f"🔍 <b>Kanal storage: '{esc(text)}'</b>\n\n"
            for r in results[:10]:
                t += (
                    f"🎬 {esc(r['title'] or '—')} [{esc(r['quality'])}]"
                    + (f" — {r['part']}-qism" if r["part"] else "")
                    + f"\n   msg_id: <code>{r['msg_id']}</code>\n\n"
                )
            await msg.reply_text(t, parse_mode=H)


# ─── Panel bo'limlari ─────────────────────────────────────

async def _admin_main(q):
    total   = get_users_count()
    active  = get_active_users_count()
    pending = len(get_pending_payments())
    open_c  = len(get_open_complaints())
    await q.edit_message_text(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Jami: <b>{total}</b>\n"
        f"🟢 Faol: <b>{active}</b>\n"
        f"💰 To'lovlar: <b>{pending}</b>\n"
        f"📋 Shikoyatlar: <b>{open_c}</b>",
        parse_mode=H, reply_markup=_admin_kb()
    )


async def _stats(q):
    s = get_detailed_statistics()
    u = s["users"]
    d = s["downloads"]
    r = s["reviews"]

    top_m_text = ""
    if d["top_movies"]:
        top_m_text = "\n🔥 <b>Top Kinolar:</b>\n" + "\n".join([
            f"• {esc(m['title'][:25])} — {m['cnt']} ta" for m in d["top_movies"][:5]
        ])

    text = (
        f"📊 <b>Kengaytirilgan Bot Statistikasi</b>\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f" • Jami: <b>{u['total']} ta</b>\n"
        f" • Bugun yangi: <b>+{u['new_today']}</b> | Kecha: <b>+{u['new_yesterday']}</b>\n"
        f" • Bugun faol (24h): <b>{u['active_today']}</b>\n"
        f" • Haftalik faol: <b>{u['active_week']}</b> | Oylik: <b>{u['active_month']}</b>\n"
        f" • Premium obunachilar: <b>{u['subscribed']} ta</b>\n"
        f" • Userbot ulaganlar: <b>{s['userbots']['total']} ta</b>\n\n"
        f"📦 <b>Yuklab Olishlar:</b>\n"
        f" • Jami: <b>{d['total']} ta</b> (<b>{d['total_gb']} GB</b> trafik)\n"
        f" • Bugun yuklangan: <b>{d['today']} ta</b>\n"
        f" • Haftalik yuklangan: <b>{d['week']} ta</b>\n\n"
        f"⭐ <b>Fikrlar va Reyting:</b>\n"
        f" • O'rtacha baho: <b>⭐ {r['avg']} / 5.0</b> ({r['count']} ta sharh)\n"
        f"{top_m_text}\n\n"
        f"📥 <i>1,000+ qatorlik batafsil hisobot, foydalanuvchilar loglari va grafiklar uchun PDF faylni yuklab oling:</i>"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 PDF Hisobotni Yuklash (Batafsil Loglar)", callback_data="export_pdf_report")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")]
    ])

    await q.edit_message_text(text, parse_mode=H, reply_markup=kb)


async def _export_pdf_report(q, context):
    try:
        await q.answer("⏳ PDF hisobot tayyorlanmoqda...", show_alert=False)
    except Exception:
        pass

    stats = get_detailed_statistics()
    logs = get_activity_logs_for_report(1000)

    pdf = PDFBuilder(title="MovieBot Kengaytirilgan Analitik Hisoboti")

    # 1. Executive Summary Cards
    pdf.add_section_header("1. ASOSIY STATISTIKA")
    pdf.add_metric_cards([
        ("Jami Foydalanuvchilar", str(stats["users"]["total"])),
        ("Bugun Faol", str(stats["users"]["active_today"])),
        ("Haftalik Faol", str(stats["users"]["active_week"])),
        ("Userbot Ulangan", str(stats["userbots"]["total"]))
    ])

    pdf.add_metric_cards([
        ("Jami Yuklanmalar", str(stats["downloads"]["total"])),
        ("Trafik Hajmi", f"{stats['downloads']['total_gb']} GB"),
        ("Bugun Yuklangan", str(stats["downloads"]["today"])),
        ("O'rtacha Baho", f"⭐ {stats['reviews']['avg']} / 5")
    ])

    # 2. Users Breakdown
    pdf.add_section_header("2. FOYDALANUVCHILAR DINAMIKASI")
    u_headers = ["Kategoriya", "Soni / Ko'rsatkich"]
    u_rows = [
        ["Jami ro'yxatdan o'tganlar", str(stats["users"]["total"])],
        ["Bugun qo'shilgan yangi foydalanuvchilar", str(stats["users"]["new_today"])],
        ["Kecha qo'shilgan yangi foydalanuvchilar", str(stats["users"]["new_yesterday"])],
        ["Shu haftada qo'shilganlar", str(stats["users"]["new_week"])],
        ["Shu oyda qo'shilganlar", str(stats["users"]["new_month"])],
        ["Bugun aktiv bo'lganlar (24 soat)", str(stats["users"]["active_today"])],
        ["So'nggi 7 kunda aktivlar", str(stats["users"]["active_week"])],
        ["So'nggi 30 kunda aktivlar", str(stats["users"]["active_month"])],
        ["Faol Premium obunachilar", str(stats["users"]["subscribed"])],
        ["Bloklangan foydalanuvchilar", str(stats["users"]["banned"])],
    ]
    pdf.add_table(u_headers, u_rows, [250, 275])

    # 3. Downloads & Sites Breakdown
    pdf.add_section_header("3. MANBALAR VA SIFAT TAQSIMOTI")
    d_headers = ["Manba Sayt", "Yuklashlar Soni"]
    d_rows = [[domain, str(cnt)] for domain, cnt in stats["downloads"]["domains"].items()]
    pdf.add_table(d_headers, d_rows, [250, 275])

    q_headers = ["Kino Sifati (Quality)", "Yuklashlar Soni"]
    q_rows = [[str(q[0] or "Nomalum"), str(q[1])] for q in stats["downloads"]["qualities"]]
    pdf.add_table(q_headers, q_rows, [250, 275])

    # 4. Top Movies
    if stats["downloads"]["top_movies"]:
        pdf.add_section_header("4. ENG KO'P YUKLANGAN KINOLAR TOP-15")
        m_headers = ["#", "Kino Nomlanishi", "Sifati", "Yuklanishlar"]
        m_rows = [
            [str(i+1), m["title"], m.get("quality", "HD"), str(m["cnt"])]
            for i, m in enumerate(stats["downloads"]["top_movies"])
        ]
        pdf.add_table(m_headers, m_rows, [30, 280, 90, 125])

    # 5. User Activity Logs
    if logs:
        pdf.add_section_header("5. FOYDALANUVCHILARNING SO'NGGI HARAKATLARI LOGI")
        l_headers = ["Sana / Vaqt", "User ID", "Foydalanuvchi", "Harakat / Buyruq", "Tafsilot"]
        l_rows = [
            [
                l["created_at"],
                str(l["user_id"]),
                l.get("full_name") or l.get("username") or "Anonim",
                l.get("action") or "-",
                l.get("details") or "-"
            ]
            for l in logs[:800]
        ]
        pdf.add_table(l_headers, l_rows, [100, 70, 110, 110, 135])

    from datetime import datetime
    out_filename = f"reports/MovieBot_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.build(out_filename)

    with open(out_filename, "rb") as pdf_file:
        await context.bot.send_document(
            chat_id=q.from_user.id,
            document=pdf_file,
            filename=os.path.basename(out_filename),
            caption=(
                f"📄 <b>MovieBot Analitik Hisobot (PDF)</b>\n\n"
                f"📊 <b>Barcha ko'rsatkichlar, foydalanuvchilar faolligi va tizim loglari yuklandi!</b>\n"
                f"📅 Sana: <b>{datetime.now().strftime('%d.%m.%Y %H:%M')}</b>"
            ),
            parse_mode=H
        )


async def _users(q):
    users = get_all_users()
    text  = f"👥 <b>Foydalanuvchilar ({len(users)} ta)</b>\n\n"
    for u in users[-20:]:
        is_sub = "✅" if (u["tariff_id"] and u["sub_expires"]) else "⬜"
        banned = " 🚫" if u["is_banned"] else ""
        uname  = f"@{esc(u['username'])}" if u["username"] else f"<code>{u['user_id']}</code>"
        text  += f"{is_sub}{banned} {uname} — <code>{u['user_id']}</code>\n"
    rows = []
    for u in users[-10:]:
        rows.append([
            InlineKeyboardButton(
                f"🚫 {u['user_id']}" if not u["is_banned"] else f"✅ {u['user_id']}",
                callback_data=f"adm_ban_{u['user_id']}" if not u["is_banned"] else f"adm_unban_{u['user_id']}"
            )
        ])
    rows.append([InlineKeyboardButton("🔙", callback_data="adm_back")])
    await q.edit_message_text(text, parse_mode=H, reply_markup=InlineKeyboardMarkup(rows))


async def _tariffs(q):
    tariffs = get_all_tariffs()
    text    = "🏷 <b>Tariflar</b>\n\n" if tariffs else "🏷 Tariflar yo'q.\n\n"
    for t in tariffs:
        icon = "✅" if t["is_active"] else "❌"
        text += f"{icon} <b>#{t['id']} {esc(t['name'])}</b> — {t['price']:,.0f} {esc(t['currency'])} / {t['days']} kun\n"
        if t["description"]:
            text += f"   <i>{esc(t['description'])}</i>\n"
    rows = []
    for t in tariffs:
        rows.append([
            InlineKeyboardButton(
                f"{'✅→❌' if t['is_active'] else '❌→✅'} #{t['id']} {t['name'][:12]}",
                callback_data=f"adm_toggle_tariff_{t['id']}"
            ),
            InlineKeyboardButton("🗑", callback_data=f"adm_del_tariff_{t['id']}")
        ])
    rows.append([InlineKeyboardButton("➕ Yangi tarif", callback_data="adm_add_tariff")])
    rows.append([InlineKeyboardButton("🔙", callback_data="adm_back")])
    await q.edit_message_text(text, parse_mode=H, reply_markup=InlineKeyboardMarkup(rows))


async def _cards(q):
    cards = get_all_cards()
    text  = "💳 <b>Kartalar</b>\n\n" if cards else "💳 Kartalar yo'q.\n\n"
    for c in cards:
        icon = "✅" if c["is_active"] else "❌"
        text += f"{icon} <code>{esc(c['card_number'])}</code> — {esc(c['card_holder'])} ({esc(c['bank_name'] or '—')})\n"
    rows = []
    for c in cards:
        rows.append([
            InlineKeyboardButton(
                f"{'✅→❌' if c['is_active'] else '❌→✅'} ...{c['card_number'][-4:]}",
                callback_data=f"adm_toggle_card_{c['id']}"
            ),
            InlineKeyboardButton("🗑", callback_data=f"adm_del_card_{c['id']}")
        ])
    rows.append([InlineKeyboardButton("➕ Yangi karta", callback_data="adm_add_card")])
    rows.append([InlineKeyboardButton("🔙", callback_data="adm_back")])
    await q.edit_message_text(text, parse_mode=H, reply_markup=InlineKeyboardMarkup(rows))


async def _payments(q):
    payments = get_pending_payments()
    if not payments:
        await q.edit_message_text(
            "💰 Kutilayotgan to'lovlar yo'q.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_back")]])
        )
        return
    text = f"💰 <b>Kutilayotgan to'lovlar ({len(payments)} ta)</b>\n\n"
    rows = []
    for p in payments[:10]:
        uname = f"@{esc(p['username'])}" if p["username"] else f"<code>{p['user_id']}</code>"
        text += (
            f"#{p['id']} | {uname}\n"
            f"   🏷 {esc(p['tariff_name'] or '—')} | 💰 {p['amount']:,.0f} so'm\n\n"
        )
        rows.append([
            InlineKeyboardButton(f"✅ #{p['id']}", callback_data=f"approve_payment_{p['id']}"),
            InlineKeyboardButton(f"❌ #{p['id']}", callback_data=f"reject_payment_{p['id']}"),
        ])
    rows.append([InlineKeyboardButton("🔙", callback_data="adm_back")])
    await q.edit_message_text(text, parse_mode=H, reply_markup=InlineKeyboardMarkup(rows))


async def _approve_payment(q, context, pid: int):
    p = get_payment(pid)
    if not p:
        await q.answer("To'lov topilmadi.", show_alert=True)
        return
    t    = get_tariff(p["tariff_id"]) if p["tariff_id"] else None
    days = t["days"] if t else int(get_setting("subscription_days","30"))
    set_subscription(p["user_id"], p["tariff_id"] or 0, days)
    update_payment_status(pid, "approved", q.from_user.id)
    try:
        tname = esc(t["name"]) if t else "Premium"
        await context.bot.send_message(
            p["user_id"],
            f"🎉 <b>Obunangiz faollashtirildi!</b>\n\n"
            f"🏷 Tarif: <b>{tname}</b>\n"
            f"📅 Muddat: <b>{days} kun</b>\n\n"
            f"Cheksiz kino yuklab olishingiz mumkin! 🎬",
            parse_mode=H
        )
    except Exception:
        pass
    try:
        await q.edit_message_caption(
            f"✅ <b>To'lov #{pid} tasdiqlandi</b>\n👤 <code>{p['user_id']}</code> +{days} kun",
            parse_mode=H
        )
    except Exception:
        await q.edit_message_text(
            f"✅ To'lov #{pid} tasdiqlandi — <code>{p['user_id']}</code> +{days} kun",
            parse_mode=H
        )


async def _reject_payment(q, context, pid: int):
    p = get_payment(pid)
    if not p:
        await q.answer("To'lov topilmadi.", show_alert=True)
        return
    update_payment_status(pid, "rejected", q.from_user.id)
    try:
        await context.bot.send_message(
            p["user_id"],
            f"❌ <b>To'lovingiz rad etildi</b> (#{pid})\n\nAdmin bilan bog'laning.",
            parse_mode=H
        )
    except Exception:
        pass
    try:
        await q.edit_message_caption(f"❌ To'lov #{pid} rad etildi.", parse_mode=H)
    except Exception:
        await q.edit_message_text(f"❌ To'lov #{pid} rad etildi.", parse_mode=H)


async def _complaints(q):
    comps = get_open_complaints()
    if not comps:
        await q.edit_message_text(
            "📋 Ochiq shikoyatlar yo'q.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_back")]])
        )
        return
    text = f"📋 <b>Ochiq shikoyatlar ({len(comps)} ta)</b>\n\n"
    rows = []
    for c in comps[:10]:
        uname = f"@{esc(c['username'])}" if c["username"] else f"<code>{c['user_id']}</code>"
        text += f"#{c['id']} {uname}:\n<i>{esc(c['text'][:100])}</i>\n\n"
        rows.append([InlineKeyboardButton(f"✏️ Javob #{c['id']}", callback_data=f"adm_resolve_{c['id']}")])
    rows.append([InlineKeyboardButton("🔙", callback_data="adm_back")])
    await q.edit_message_text(text, parse_mode=H, reply_markup=InlineKeyboardMarkup(rows))


async def _broadcast_prompt(q, context):
    context.user_data["adm_state"] = "broadcast"
    await q.edit_message_text(
        "📢 <b>Broadcast</b>\n\nBarcha foydalanuvchilarga xabar yoki rasm yuboring:",
        parse_mode=H,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_back")]])
    )


async def _settings(q):
    free  = get_setting("free_downloads","1")
    maint = get_setting("maintenance_mode","0")
    botun = get_setting("bot_username","—")
    sphoto = get_setting("start_photo", "")
    maint_icon = "🔴 Yoqilgan" if maint == "1" else "🟢 O'chirilgan"
    await q.edit_message_text(
        f"⚙️ <b>Sozlamalar</b>\n\n"
        f"🆓 Bepul limit: <b>{free} ta</b>\n"
        f"🖼 Start Rasmi: <b>{'Sozlingan' if sphoto else 'Default banner'}</b>\n"
        f"🔧 Texnik rejim: <b>{maint_icon}</b>\n"
        f"🤖 Bot username: <b>@{esc(botun)}</b>",
        parse_mode=H,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆓 Bepul limit", callback_data="adm_set_free")],
            [InlineKeyboardButton("🖼 Start Banner Rasm", callback_data="adm_set_start_photo")],
            [InlineKeyboardButton("🤖 Bot username", callback_data="adm_set_botusername")],
            [InlineKeyboardButton("👋 Welcome xabari", callback_data="adm_set_welcome")],
            [InlineKeyboardButton(
                "🔧 Texnik rejim yoq" if maint == "0" else "🟢 Texnik rejimni o'chir",
                callback_data="adm_maintenance_on" if maint == "0" else "adm_maintenance_off"
            )],
            [InlineKeyboardButton("🔙", callback_data="adm_back")],
        ])
    )


async def _channel_info(q):
    ch = get_setting("storage_channel","")
    await q.edit_message_text(
        f"📦 <b>Telegram Storage Kanal</b>\n\n"
        f"Joriy kanal: <code>{esc(ch) if ch else 'sozlanmagan'}</code>\n\n"
        f"<b>Qanday ishlaydi:</b>\n"
        f"• Kino bir marta yuklanadi → kanalda saqlanadi\n"
        f"• Keyingi so'rovda forward qilinadi (tez!)\n"
        f"• Bot kanal ID bilan indeks yuritadi\n\n"
        f"<b>Kanal ID topish:</b>\n"
        f"• @userinfobot → kanalga qo'shib ID oling\n"
        f"• Private: -100XXXXXXXXXX formatda",
        parse_mode=H,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Kanal ID o'zgartirish", callback_data="adm_set_channel")],
            [InlineKeyboardButton("🔙", callback_data="adm_back")],
        ])
    )


async def _mandatory_panel(q):
    mc = get_setting("mandatory_channel","")
    status_str = esc(mc) if mc else "o'chirilgan"
    btn_label = "❌ O'chirish" if mc else "🔕 (O'chirilgan)"
    await q.edit_message_text(
        f"📢 <b>Majburiy kanal obunasi</b>\n\n"
        f"Joriy kanal: <code>{status_str}</code>\n\n"
        f"<b>Nima qiladi:</b>\n"
        f"• Foydalanuvchi botni ishlatishdan oldin\n"
        f"  kanalga obuna bo'lishi shart\n"
        f"• Obuna bo'lmagan → «Kanalga o'tish» tugmasi\n\n"
        f"<b>Sozlash:</b>\n"
        f"• Bot kanalga admin bo'lsin\n"
        f"• Kanal ID yoki @username kiriting",
        parse_mode=H,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Kanal o'rnatish", callback_data="adm_set_mandatory")],
            [InlineKeyboardButton(btn_label, callback_data="adm_set_mandatory")],
            [InlineKeyboardButton("🔙", callback_data="adm_back")],
        ])
    )


async def _admins_panel(q):
    admins  = get_all_admins()
    env_ids = [a.strip() for a in os.getenv("ADMIN_IDS","").split(",") if a.strip()]
    text    = "🔐 <b>Adminlar</b>\n\n<b>ENV adminlar (o'zgartirib bo'lmaydi):</b>\n"
    for aid in env_ids:
        text += f"• <code>{esc(aid)}</code>\n"
    text += "\n<b>Qo'shilgan adminlar:</b>\n"
    rows = []
    if admins:
        for a in admins:
            uname = f"@{esc(a['username'])}" if a["username"] else f"<code>{a['user_id']}</code>"
            text += f"• {uname} ({a['user_id']}) — level {a['level']}\n"
            rows.append([
                InlineKeyboardButton(f"🗑 {a['user_id']}", callback_data=f"adm_del_admin_{a['user_id']}")
            ])
    else:
        text += "<i>Yo'q</i>\n"
    rows.append([InlineKeyboardButton("➕ Admin qo'shish", callback_data="adm_add_admin")])
    rows.append([InlineKeyboardButton("🔙", callback_data="adm_back")])
    await q.edit_message_text(text, parse_mode=H, reply_markup=InlineKeyboardMarkup(rows))


async def _search_storage_prompt(q, context):
    context.user_data["adm_state"] = "search_storage"
    await q.edit_message_text(
        "🔍 <b>Kanal storage qidirish</b>\n\nKino nomini yozing:",
        parse_mode=H,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="adm_channel")]])
    )


# ─── Qo'shimcha buyruqlar ─────────────────────────────────

@admin_only
async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.message.reply_text("Foydalanish: /ban <user_id>")
        return
    try:
        uid = int(args[0])
        ban_user(uid)
        await update.message.reply_text(f"🚫 <code>{uid}</code> bloklandi.", parse_mode=H)
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri user ID.")


@admin_only
async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.message.reply_text("Foydalanish: /unban <user_id>")
        return
    try:
        uid = int(args[0])
        unban_user(uid)
        await update.message.reply_text(f"✅ <code>{uid}</code> blokdan chiqarildi.", parse_mode=H)
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri user ID.")


@admin_only
async def sub_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin foydalanuvchiga obuna beradi: /sub user_id tariff_id"""
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text("Foydalanish: /sub <user_id> <tariff_id>")
        return
    try:
        uid = int(args[0])
        tid = int(args[1])
        t   = get_tariff(tid)
        if not t:
            await update.message.reply_text(f"❌ Tarif #{tid} topilmadi.")
            return
        set_subscription(uid, tid, t["days"])
        await update.message.reply_text(
            f"✅ <code>{uid}</code> ga <b>{esc(t['name'])}</b> ({t['days']} kun) berildi.",
            parse_mode=H
        )
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri parametrlar.")


@admin_only
async def addadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/addadmin user_id"""
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Foydalanish: /addadmin <user_id>")
        return
    uid = int(args[0])
    u   = get_user(uid)
    add_admin(uid, u["username"] if u else "", u["full_name"] if u else "",
              level=1, added_by=update.effective_user.id)
    await update.message.reply_text(f"✅ Admin qo'shildi: <code>{uid}</code>", parse_mode=H)


@admin_only
async def removeadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/removeadmin user_id"""
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Foydalanish: /removeadmin <user_id>")
        return
    uid     = int(args[0])
    env_ids = [a.strip() for a in os.getenv("ADMIN_IDS","").split(",")]
    if str(uid) in env_ids:
        await update.message.reply_text("❌ ENV admin o'chirib bo'lmaydi!")
        return
    remove_admin(uid)
    await update.message.reply_text(f"✅ Admin o'chirildi: <code>{uid}</code>", parse_mode=H)
