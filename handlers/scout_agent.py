import asyncio
import logging
import random
import json
from datetime import datetime
from telethon import TelegramClient, events
from utils.database import (
    get_all_active_scouting_settings, get_scouting_settings, save_scouting_settings,
    add_scouting_lead, get_scouting_leads_for_user, update_scouting_lead_status,
    update_scouting_lead_pitch, add_scouting_log, get_userbot_session
)
from utils.lead_finder import find_leads_for_category
from utils.gemini_client import ask_gemini
from handlers.scout_bot_manager import get_scout_bot_app

logger = logging.getLogger(__name__)

# Active background scout tasks: user_id -> Task
scout_tasks = {}

# Active response monitoring handlers registered per client: user_id -> True
monitored_clients = {}

SYSTEM_PITCH_PROMPT = """
Siz — Oʻzbekiston bozorida biznes jarayonlarini avtomatlashtirish, Telegram WebApp botlari va B2B tizimlarini sotish boʻyicha professional, mustaqil ishlaydigan "AI Sales & Scouting Agent"siz.
Sizning maqsadingiz kichik/o'rta ishlab chiqarish korxonasi yoki sexga ular uchun maxsus, individual va srazi sotadigan qisqa va qulay tijoriy taklif (pitch) yozishdir.

Quyidagi qat'iy qoidalarga rioya qiling:
1. Register (Ohang): Juda rasmiy boʻlmasin ("Sizga oʻz xizmatlarimizni taklif etamiz" deb boshlamang — bu srazi oʻchiriladi). Juda koʻcha tilida ham boʻlmasin. Aka-uka yoki samimiy biznes hamkor ohangida yozing.
2. Suv yo'q: "Yaxshimisiz, charchamayapsizmi, ishlaringiz yaxshimi" kabi ortiqcha kirish qatorlari bilan vaqtni olmang. Salomdan keyin srazi maqsadga oʻting.
3. Muammoni ko'rsatish: "Aka, e'loningizni/profilingizni ko'rdim. Sizlarda {industry_uz} bo'yicha buyurtmalarni faqat telefon yoki lichkada yozishib olar ekansiz. Mijozlariz telefonda kutib qolayotgan bo'lishi mumkin yoki buyurtmalar chalkashib ketishi mumkin."
4. Yechim va Narx: "Sizga atigi 3 kunda eng sodda va juda qulay Telegram Bot qilib beraman. Mijoz buyurtma bersa srazi lichkayizga chiroyli tayyor chek holda tushadi. Katta xarajat emas, jami 100$ bo'ladi."
5. CTA (Call to Action): Oxirida "Qiziq bo'lsa, qanday ishlashini rasm/video orqali ko'rsataman, nima deysiz?" deb tugating.

Xabarni faqat O'zbek tilida yozing. Hech qanday inglizcha yoki ruscha so'z bo'lmasin. Faqat tayyor taklif xabarining o'zini qaytaring, ortiqcha tushuntirish berib o'tirmang.
"""

SYSTEM_REPLY_PROMPT = """
Siz — Oʻzbekiston bozorida biznes jarayonlarini avtomatlashtirish, Telegram WebApp botlari va B2B tizimlarini sotish boʻyicha professional "AI Sales & Scouting Agent"siz.
Mijoz siz yuborgan tijoriy taklifga (pitchga) javob qaytardi. Siz unga aqlli, muloyim va foydali tarzda javob qaytarishingiz kerak.

Qat'iy qoidalar:
1. Agar mijoz "Aytvoraman / O'ylab ko'raman" desa: Srazi ortga chekinib, bosimni kamaytiring. Eshikni ochiq qoldiring. (Masalan: "Xizmat qilmoqchi bo'lsak xursand bo'lamiz aka. O'ylab ko'rib bemalol yozasiz, vaqtingiz bemalol bo'lganda.")
2. Agar mijoz "Qancha bo'ladi / Nima qiladi / Qanaqa bot?" deb so'rasa: Hech qanday texnik terminlarsiz (front-end, back-end, database demasdan), sodda biznes tilida foydasini tushuntiring va jami narxni ($100) yana bir bor tasdiqlang.
3. Agar mijoz rozi bo'lsa ("Mayli ko'raylik" yoki "Kelishdik" desa): Srazi gapni cho'zmasdan, buni real dasturchiga (biznes hamkoringizga) topshirayotganingizni, u tez orada aloqaga chiqishini ayting. (Masalan: "Ajoyib qaror aka! Hozir texnik guruhimiz va bosh dasturchimizni siz bilan guruhga ulayman, batafsil kelishib ishni boshlaymiz.")

Xabarni O'zbek tilida, qisqa, londa va ishonarli yozing. Faqat yuboriladigan javob matnining o'zini qaytaring.
"""

async def generate_pitch(business_name: str, industry: str, offer: str) -> str:
    prompt = (
        f"Kompaniya nomi: '{business_name}'\n"
        f"Sohasi: '{industry}'\n"
        f"Taklif qilinadigan bot narxi va sharti: '{offer}'\n\n"
        f"Ushbu ma'lumotlarga asoslanib, individual va samimiy sotuv taklifini (pitch) tayyorlab bering."
    )
    pitch = await ask_gemini(prompt, system_instruction=SYSTEM_PITCH_PROMPT)
    if not pitch:
        # Fallback manual text
        pitch = (
            f"Assalomu alaykum aka. '{business_name}' faoliyatini ko'rib chiqdim. "
            f"Sizlarda {industry} bo'yicha buyurtmalarni faqat telefon orqali qabul qilar ekansiz.\n\n"
            f"Mijozlar kutib qolmasligi va buyurtmalar avtomatik tushishi uchun, atigi 3 kunda eng sodda "
            f"Telegram Bot qilib beraman. Katta xarajat emas, jami {offer} bo'ladi.\n\n"
            f"Qiziq bo'lsa, qanday ishlashini rasm yoki video orqali ko'rsataman, nima deysiz?"
        )
    return pitch

async def generate_response_to_reply(client_message: str, previous_pitch: str) -> str:
    prompt = (
        f"Biz yuborgan taklif: '{previous_pitch}'\n"
        f"Mijozning javobi: '{client_message}'\n\n"
        f"Ushbu javobga eng mos keladigan strategik va ishonchli javobni tayyorlang."
    )
    reply = await ask_gemini(prompt, system_instruction=SYSTEM_REPLY_PROMPT)
    if not reply:
        reply = "Tushunarli aka. Loyihalarimiz va ishlash tizimimiz bo'yicha savollar bo'lsa bemalol berishingiz mumkin, tushuntirib beraman."
    return reply


async def run_scout_agent_for_user(user_id: int, application):
    """
    Main loop for a single user's scouting agent.
    """
    logger.info(f"Scout agent background loop started for user {user_id}")
    add_scouting_log(user_id, "🕵️‍♂️ AI Scouting Agent muvaffaqiyatli ishga tushdi!")
    
    # Register reaction & reply monitor on their active userbot client
    await register_reply_monitor(user_id, application)

    while True:
        try:
            # Check if setting is still active
            settings = get_scouting_settings(user_id)
            if not settings or not settings.get("is_active"):
                logger.info(f"Scout agent for user {user_id} is disabled. Stopping loop...")
                add_scouting_log(user_id, "🔴 AI Scouting Agent faoliyatini to'xtatdi.")
                break
                
            # Verify active userbot session
            from handlers.userbot import active_clients
            client = active_clients.get(user_id)
            if not client or not await client.is_user_authorized():
                logger.warning(f"Scout agent for {user_id} suspended: userbot client offline.")
                add_scouting_log(user_id, "⚠️ Userbot ulunmagan yoki o'chgan! Scouting to'xtatildi. /connect_api yuboring.")
                # Mark as inactive
                save_scouting_settings(
                    user_id, is_active=0,
                    categories=settings["categories"], pitch_offer=settings["pitch_offer"],
                    daily_limit=settings["daily_limit"], min_delay=settings["min_delay"], max_delay=settings["max_delay"]
                )
                break
                
            # Parse categories
            cats = [c.strip() for c in settings["categories"].split(",") if c.strip()]
            if not cats:
                add_scouting_log(user_id, "❌ Hech qanday qidiruv sohasi kiritilmagan. Sozlamalarni tekshiring.")
                await asyncio.sleep(60)
                continue
                
            # Select random category
            selected_cat = random.choice(cats)
            add_scouting_log(user_id, f"🔍 '{selected_cat}' sohasi bo'yicha yangi bizneslar qidirilmoqda...")
            
            # Find leads
            leads = await find_leads_for_category(selected_cat)
            new_leads_found = 0
            
            for lead in leads:
                # Add to DB (it checks for duplicates automatically)
                lead_id = add_scouting_lead(
                    user_id=user_id,
                    business_name=lead["name"],
                    industry=selected_cat,
                    phone=lead["phone"],
                    address=lead["address"],
                    source=lead["source"]
                )
                
                # Retrieve updated lead to check current status
                from utils.database import get_connection
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT status FROM scouting_leads WHERE id = ?", (lead_id,))
                lead_row = cur.fetchone()
                conn.close()
                
                if lead_row and lead_row["status"] == "found":
                    new_leads_found += 1
                    
                    # 1. Draft specialized pitch using Gemini
                    add_scouting_log(user_id, f"📝 '{lead['name']}' uchun individual taklif matni tuzilmoqda...")
                    pitch_text = await generate_pitch(lead["name"], selected_cat, settings["pitch_offer"])
                    
                    # 2. Try to send via Userbot
                    add_scouting_log(user_id, f"🚀 '{lead['name']}' ({lead['phone']}) raqamiga Telegram orqali yozilmoqda...")
                    
                    try:
                        # Attempt to message the phone number
                        sent_msg = await client.send_message(lead["phone"], pitch_text)
                        
                        # Pitch sent successfully! Update DB
                        update_scouting_lead_pitch(lead_id, pitch_text, "pitched")
                        add_scouting_log(user_id, f"✅ '{lead['name']}'ga taklif yuborildi! Javob kutilmoqda.")
                        
                        # Notify the bot owner
                        try:
                            app_to_use = get_scout_bot_app() or application
                            await app_to_use.bot.send_message(
                                chat_id=user_id,
                                text=(
                                    f"🚀 <b>Yangi mijozga taklif yuborildi!</b>\n\n"
                                    f"🏢 <b>Nomi:</b> {lead['name']}\n"
                                    f"📞 <b>Telefon:</b> <code>{lead['phone']}</code>\n"
                                    f"📍 <b>Manzil:</b> {lead['address']}\n"
                                    f"🏷️ <b>Sohasi:</b> {selected_cat}\n"
                                    f"📡 <b>Manba:</b> {lead['source']}\n\n"
                                    f"📝 <b>Yuborilgan Pitch:</b>\n<i>{pitch_text}</i>"
                                ),
                                parse_mode="html"
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify bot owner: {e}")
                            
                        # Random pause to avoid spam
                        delay = random.randint(settings["min_delay"], settings["max_delay"])
                        add_scouting_log(user_id, f"⏳ Spamdan himoyalanish: {delay // 60} daqiqa kutilmoqda...")
                        await asyncio.sleep(delay)
                        
                    except ValueError:
                        # Number not registered on Telegram
                        update_scouting_lead_status(lead_id, "failed")
                        add_scouting_log(user_id, f"❌ '{lead['name']}' ({lead['phone']}) raqamida Telegram topilmadi.")
                    except Exception as send_err:
                        logger.error(f"Error sending pitch to {lead['phone']}: {send_err}")
                        add_scouting_log(user_id, f"⚠️ '{lead['name']}'ga yozishda xatolik: {str(send_err)[:50]}")
                        await asyncio.sleep(10)
                        
            if new_leads_found == 0:
                add_scouting_log(user_id, f"😴 '{selected_cat}' sohasida yangi yangi ochiq mijoz topilmadi. Navbatdagi sikl kutilmoqda...")
                
            # Wait 30-45 minutes between main cycles
            await asyncio.sleep(random.randint(1800, 2700))
            
        except Exception as loop_err:
            logger.error(f"Error in scout agent loop: {loop_err}")
            await asyncio.sleep(60)


async def register_reply_monitor(user_id: int, application):
    """
    Registers an event handler on the active userbot to monitor replies from our pitched leads.
    """
    if user_id in monitored_clients:
        return
        
    from handlers.userbot import active_clients
    client = active_clients.get(user_id)
    if not client:
        return
        
    monitored_clients[user_id] = True
    
    @client.on(events.NewMessage(incoming=True))
    async def handle_lead_reply(event):
        try:
            sender = await event.get_sender()
            if not sender:
                return
                
            phone = getattr(sender, "phone", None)
            username = getattr(sender, "username", None)
            sender_id = getattr(sender, "id", None)
            
            if not phone and not username:
                return
                
            # Search in our database if this person is a lead we pitched
            from utils.database import get_connection, rows_to_list
            conn = get_connection()
            cur = conn.cursor()
            
            # Find lead by phone or username
            lead_row = None
            if phone:
                formatted_phone = f"+{phone.lstrip('+')}"
                cur.execute("SELECT * FROM scouting_leads WHERE user_id = ? AND phone = ? AND status = 'pitched'", (user_id, formatted_phone))
                lead_row = cur.fetchone()
                
            if not lead_row and username:
                cur.execute("SELECT * FROM scouting_leads WHERE user_id = ? AND tg_username = ? AND status = 'pitched'", (user_id, username))
                lead_row = cur.fetchone()
                
            conn.close()
            
            if not lead_row:
                return
                
            lead_id = lead_row["id"]
            business_name = lead_row["business_name"]
            previous_pitch = lead_row["pitch_sent"]
            client_msg_text = event.text or ""
            
            # We found a reply from an active lead!
            logger.info(f"Lead reply detected from {business_name} (phone: {phone})")
            add_scouting_log(user_id, f"🔥 MIJOZ JAVOBI! '{business_name}' sizga javob qaytardi: '{client_msg_text[:30]}...'")
            
            # Update status to replied
            update_scouting_lead_status(lead_id, "replied")
            
            # Generate response via Gemini
            ai_reply = await generate_response_to_reply(client_msg_text, previous_pitch)
            
            # Auto-send reply to lead via userbot
            await event.reply(ai_reply)
            add_scouting_log(user_id, f"🤖 AI '{business_name}'ning xabariga avtomatik javob berdi.")
            
            # Notify Bot Owner
            tg_link = f"https://t.me/{username}" if username else f"tg://user?id={sender_id}"
            app_to_use = get_scout_bot_app() or application
            await app_to_use.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🔥 <b>Issiq Lead! Mijoz sizga javob berdi!</b>\n\n"
                    f"🏢 <b>Kompaniya:</b> {business_name}\n"
                    f"📞 <b>Telefon:</b> <code>{lead_row['phone']}</code>\n"
                    f"💬 <b>Uning xabari:</b>\n<i>{client_msg_text}</i>\n\n"
                    f"🤖 <b>AI Bergan Avtomatik Javob:</b>\n<i>{ai_reply}</i>\n\n"
                    f"👉 <a href='{tg_link}'>Suhbatga o'tish (Telegram)</a>"
                ),
                parse_mode="html"
            )
            
            # If they sound completely positive/closed, update status
            lowered = client_msg_text.lower()
            if any(ok_word in lowered for ok_word in ["kelishdik", "mayli", "yozing", "qiling", "boshlaymiz", "rozi", "ok"]):
                update_scouting_lead_status(lead_id, "interested")
                
        except Exception as reply_err:
            logger.error(f"Error handling lead reply: {reply_err}")


async def start_all_scout_agents(application):
    """
    Called on system boot to launch all active scouting loops.
    """
    try:
        active_settings = get_all_active_scouting_settings()
        logger.info(f"Found {len(active_settings)} active scouting settings to start.")
        for row in active_settings:
            user_id = row["user_id"]
            task = asyncio.create_task(run_scout_agent_for_user(user_id, application))
            scout_tasks[user_id] = task
    except Exception as e:
        logger.error(f"Error starting active scout agents: {e}")


async def start_scout_agent(user_id: int, application) -> bool:
    """Starts or restarts the scouting agent for a specific user."""
    if user_id in scout_tasks:
        scout_tasks[user_id].cancel()
        scout_tasks.pop(user_id, None)
        
    task = asyncio.create_task(run_scout_agent_for_user(user_id, application))
    scout_tasks[user_id] = task
    return True


async def stop_scout_agent(user_id: int):
    """Stops the scouting agent for a specific user."""
    task = scout_tasks.pop(user_id, None)
    if task:
        task.cancel()
        return True
    return False
