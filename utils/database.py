"""
SQLite Ma'lumotlar Bazasi Moduli
MovieBot uchun barcha xizmat va querylar
"""

import sqlite3
import os
import random
import string
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "moviebot.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        tariff_id INTEGER DEFAULT 0,
        sub_expires TEXT,
        free_used INTEGER DEFAULT 0,
        bonus_dl INTEGER DEFAULT 0,
        ref_code TEXT UNIQUE,
        ref_count INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        created_at TEXT,
        last_active TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        level INTEGER DEFAULT 1,
        added_by INTEGER DEFAULT 0,
        created_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tariffs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        days INTEGER,
        currency TEXT DEFAULT 'so''m',
        description TEXT,
        is_active INTEGER DEFAULT 1
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_number TEXT,
        card_holder TEXT,
        bank_name TEXT,
        is_active INTEGER DEFAULT 1
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        tariff_id INTEGER,
        amount REAL,
        card_id INTEGER,
        file_id TEXT,
        status TEXT DEFAULT 'pending',
        processed_by INTEGER DEFAULT 0,
        created_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        text TEXT,
        reply TEXT DEFAULT '',
        status TEXT DEFAULT 'open',
        created_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS channel_storage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        msg_id INTEGER,
        title TEXT,
        quality TEXT,
        part INTEGER DEFAULT 0,
        file_id TEXT,
        file_size INTEGER DEFAULT 0,
        created_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS userbot_sessions (
        user_id INTEGER PRIMARY KEY,
        api_id TEXT,
        api_hash TEXT,
        phone TEXT,
        session_string TEXT,
        created_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        url TEXT,
        title TEXT,
        quality TEXT,
        part INTEGER DEFAULT 0,
        file_id TEXT,
        file_size INTEGER DEFAULT 0,
        status TEXT DEFAULT 'started',
        created_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        user_id INTEGER PRIMARY KEY,
        rating INTEGER,
        comment TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        created_at TEXT
    );
    """)

    conn.commit()

    # Boshlang'ich default sozlamalar
    defaults = {
        "free_downloads": "1",
        "ref_bonus_dl": "1",
        "subscription_days": "30",
        "maintenance_mode": "0",
        "welcome_message": "🎬 Xush kelibsiz! UzMovie & AsilMedia botiga!",
        "storage_channel": "",
        "mandatory_channel": "",
        "bot_username": ""
    }
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Standart tarif yaratish (agar yo'q bo'lsa)
    cur.execute("SELECT COUNT(*) FROM tariffs")
    if cur.fetchone()[0] == 0:
        cur.execute("""
        INSERT INTO tariffs (name, price, days, currency, description, is_active)
        VALUES ('Premium Month', 9000, 30, 'so''m', '1 oylik cheksiz premium obuna', 1)
        """)

    conn.commit()
    conn.close()


init_db()


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    return [dict(r) for r in rows]


# ─── USER OPERATIONS ──────────────────────────────────────────

def generate_ref_code(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def upsert_user(user_id: int, username: str, full_name: str, referred_by: int = 0) -> dict:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if row is None:
        ref_code = generate_ref_code()
        cur.execute("""
        INSERT INTO users (user_id, username, full_name, ref_code, referred_by, created_at, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, full_name, ref_code, referred_by, now_str, now_str))

        # Referrer ga bonus berish
        if referred_by > 0:
            cur.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?", (referred_by,))
            bonus = int(get_setting("ref_bonus_dl", "1"))
            cur.execute("UPDATE users SET bonus_dl = bonus_dl + ? WHERE user_id = ?", (bonus, referred_by))

        conn.commit()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        res = row_to_dict(cur.fetchone())
    else:
        cur.execute("""
        UPDATE users SET username = ?, full_name = ?, last_active = ? WHERE user_id = ?
        """, (username, full_name, now_str, user_id))
        conn.commit()
        res = row_to_dict(row)

    conn.close()
    return res


def get_user(user_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    res = row_to_dict(cur.fetchone())
    conn.close()
    return res


def get_all_users() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


def get_users_count() -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    cnt = cur.fetchone()[0]
    conn.close()
    return cnt


def get_active_users_count() -> int:
    conn = get_connection()
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE last_active >= ?", (seven_days_ago,))
    cnt = cur.fetchone()[0]
    conn.close()
    return cnt


def ban_user(user_id: int):
    conn = get_connection()
    conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def unban_user(user_id: int):
    conn = get_connection()
    conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def check_subscription(user_id: int) -> bool:
    u = get_user(user_id)
    if not u or not u.get("sub_expires"):
        return False
    try:
        exp_date = datetime.strptime(u["sub_expires"], "%Y-%m-%d %H:%M:%S")
        return exp_date > datetime.now()
    except Exception:
        return False


def set_subscription(user_id: int, tariff_id: int, days: int):
    conn = get_connection()
    cur = conn.cursor()

    u = get_user(user_id)
    now = datetime.now()
    if u and u.get("sub_expires"):
        try:
            curr_exp = datetime.strptime(u["sub_expires"], "%Y-%m-%d %H:%M:%S")
            if curr_exp > now:
                new_exp = curr_exp + timedelta(days=days)
            else:
                new_exp = now + timedelta(days=days)
        except Exception:
            new_exp = now + timedelta(days=days)
    else:
        new_exp = now + timedelta(days=days)

    exp_str = new_exp.strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("UPDATE users SET tariff_id = ?, sub_expires = ? WHERE user_id = ?", (tariff_id, exp_str, user_id))
    conn.commit()
    conn.close()


def get_user_free_used(user_id: int) -> int:
    u = get_user(user_id)
    return u.get("free_used", 0) if u else 0


def increment_free_used(user_id: int):
    conn = get_connection()
    conn.execute("UPDATE users SET free_used = free_used + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_user_bonus_dl(user_id: int) -> int:
    u = get_user(user_id)
    return u.get("bonus_dl", 0) if u else 0


def use_bonus_dl(user_id: int):
    conn = get_connection()
    conn.execute("UPDATE users SET bonus_dl = MAX(0, bonus_dl - 1) WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_user_ref_code(user_id: int) -> str:
    u = get_user(user_id)
    return u.get("ref_code", "") if u else ""


def find_user_by_ref(ref_code: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE ref_code = ?", (ref_code,))
    res = row_to_dict(cur.fetchone())
    conn.close()
    return res


# ─── ADMIN OPERATIONS ──────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    env_ids = [a.strip() for a in os.getenv("ADMIN_IDS", "").split(",") if a.strip()]
    if str(user_id) in env_ids:
        return True
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
    res = cur.fetchone()
    conn.close()
    return res is not None


def get_all_admins() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM admins ORDER BY created_at DESC")
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


def add_admin(user_id: int, username: str, full_name: str, level: int = 1, added_by: int = 0):
    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
    INSERT OR REPLACE INTO admins (user_id, username, full_name, level, added_by, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, full_name, level, added_by, now_str))
    conn.commit()
    conn.close()


def remove_admin(user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ─── TARIFF OPERATIONS ─────────────────────────────────────────

def create_tariff(name: str, price: float, days: int, description: str):
    conn = get_connection()
    conn.execute("""
    INSERT INTO tariffs (name, price, days, description, is_active)
    VALUES (?, ?, ?, ?, 1)
    """, (name, price, days, description))
    conn.commit()
    conn.close()


def get_all_tariffs() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tariffs ORDER BY id ASC")
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


def get_active_tariffs() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tariffs WHERE is_active = 1 ORDER BY id ASC")
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


def get_tariff(tariff_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tariffs WHERE id = ?", (tariff_id,))
    res = row_to_dict(cur.fetchone())
    conn.close()
    return res


def toggle_tariff(tariff_id: int):
    conn = get_connection()
    conn.execute("UPDATE tariffs SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id = ?", (tariff_id,))
    conn.commit()
    conn.close()


def delete_tariff(tariff_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM tariffs WHERE id = ?", (tariff_id,))
    conn.commit()
    conn.close()


# ─── CARD OPERATIONS ───────────────────────────────────────────

def add_card(card_number: str, card_holder: str, bank_name: str):
    conn = get_connection()
    conn.execute("""
    INSERT INTO cards (card_number, card_holder, bank_name, is_active)
    VALUES (?, ?, ?, 1)
    """, (card_number, card_holder, bank_name))
    conn.commit()
    conn.close()


def remove_card(card_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()


def get_all_cards() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cards ORDER BY id ASC")
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


def get_active_cards() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cards WHERE is_active = 1 ORDER BY id ASC")
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


def toggle_card(card_id: int):
    conn = get_connection()
    conn.execute("UPDATE cards SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()


# ─── PAYMENT OPERATIONS ────────────────────────────────────────

def submit_payment(user_id: int, tariff_id: int, amount: float, card_id: int, file_id: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO payments (user_id, tariff_id, amount, card_id, file_id, status, created_at)
    VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (user_id, tariff_id, amount, card_id, file_id, now_str))
    conn.commit()
    pay_id = cur.lastrowid
    conn.close()
    return pay_id


def get_pending_payments() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT p.*, u.username, u.full_name, t.name as tariff_name
    FROM payments p
    LEFT JOIN users u ON p.user_id = u.user_id
    LEFT JOIN tariffs t ON p.tariff_id = t.id
    WHERE p.status = 'pending'
    ORDER BY p.created_at ASC
    """)
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


def get_payment(payment_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    res = row_to_dict(cur.fetchone())
    conn.close()
    return res


def update_payment_status(payment_id: int, status: str, admin_id: int):
    conn = get_connection()
    conn.execute("""
    UPDATE payments SET status = ?, processed_by = ? WHERE id = ?
    """, (status, admin_id, payment_id))
    conn.commit()
    conn.close()


# ─── SETTINGS OPERATIONS ───────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key: str, value: str):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


# ─── COMPLAINT OPERATIONS ──────────────────────────────────────

def submit_complaint(user_id: int, username: str, text: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO complaints (user_id, username, text, created_at)
    VALUES (?, ?, ?, ?)
    """, (user_id, username, text, now_str))
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def get_open_complaints() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints WHERE status = 'open' ORDER BY created_at ASC")
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


def reply_complaint(complaint_id: int, text: str):
    conn = get_connection()
    conn.execute("""
    UPDATE complaints SET reply = ?, status = 'resolved' WHERE id = ?
    """, (text, complaint_id))
    conn.commit()
    conn.close()


def get_complaint_by_id(complaint_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,))
    res = row_to_dict(cur.fetchone())
    conn.close()
    return res


# ─── STORAGE OPERATIONS ───────────────────────────────────────

def get_stored_file(url: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM channel_storage WHERE url = ?", (url,))
    res = row_to_dict(cur.fetchone())
    conn.close()
    return res


def store_channel_file(url: str, msg_id: int, title: str, quality: str, part: int, file_id: str, file_size: int):
    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
    INSERT OR REPLACE INTO channel_storage (url, msg_id, title, quality, part, file_id, file_size, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (url, msg_id, title, quality, part, file_id, file_size, now_str))
    conn.commit()
    conn.close()


def search_channel_storage(query: str) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    like_q = f"%{query}%"
    cur.execute("""
    SELECT * FROM channel_storage
    WHERE title LIKE ? OR quality LIKE ?
    ORDER BY created_at DESC LIMIT 20
    """, (like_q, like_q))
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


# ─── USERBOT SESSION OPERATIONS ────────────────────────────────

def save_userbot_session(user_id: int, api_id: str, api_hash: str, phone: str, session_string: str):
    conn = get_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
    INSERT OR REPLACE INTO userbot_sessions (user_id, api_id, api_hash, phone, session_string, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, api_id, api_hash, phone, session_string, now_str))
    conn.commit()
    conn.close()


def get_userbot_session(user_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM userbot_sessions WHERE user_id = ?", (user_id,))
    res = row_to_dict(cur.fetchone())
    conn.close()
    return res


def get_all_userbot_sessions() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM userbot_sessions")
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


def disconnect_userbot(user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM userbot_sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ─── DOWNLOAD LOG OPERATIONS ───────────────────────────────────

def log_download(user_id: int, url: str, title: str, quality: str, part: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO downloads (user_id, url, title, quality, part, status, created_at)
    VALUES (?, ?, ?, ?, ?, 'started', ?)
    """, (user_id, url, title, quality, part, now_str))
    conn.commit()
    dl_id = cur.lastrowid
    conn.close()
    return dl_id


def update_download(download_id: int, file_id: str, file_size: int, status: str):
    conn = get_connection()
    conn.execute("""
    UPDATE downloads SET file_id = ?, file_size = ?, status = ? WHERE id = ?
    """, (file_id, file_size, status, download_id))
    conn.commit()
    conn.close()


def get_user_downloads_count(user_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM downloads WHERE user_id = ? AND status = 'done'", (user_id,))
    cnt = cur.fetchone()[0]
    conn.close()
    return cnt


# ─── USER LOGS OPERATIONS ─────────────────────────────────────

def log_user_action(user_id: int, action: str, details: str = ""):
    try:
        conn = get_connection()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
        INSERT INTO user_logs (user_id, action, details, created_at)
        VALUES (?, ?, ?, ?)
        """, (user_id, action, details, now_str))
        conn.commit()
        conn.close()
    except Exception as e:
        pass


def get_activity_logs_for_report(limit: int = 1000) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT l.*, u.username, u.full_name
    FROM user_logs l
    LEFT JOIN users u ON l.user_id = u.user_id
    ORDER BY l.created_at DESC LIMIT ?
    """, (limit,))
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


# ─── REVIEWS OPERATIONS ────────────────────────────────────────

def upsert_review(user_id: int, rating: int, comment: str) -> tuple[bool, str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reviews WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    if row is not None:
        last_updated_str = row["updated_at"] or row["created_at"]
        try:
            last_dt = datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
            if (now - last_dt).total_seconds() < 86400:
                hours_left = int((86400 - (now - last_dt).total_seconds()) // 3600) + 1
                conn.close()
                return False, f"⏳ Sharhingizni kuniga faqat 1 marta tahrirlashingiz mumkin! Keyingi tahrirlash uchun {hours_left} soat qoldi."
        except Exception:
            pass

        cur.execute("""
        UPDATE reviews SET rating = ?, comment = ?, updated_at = ? WHERE user_id = ?
        """, (rating, comment, now_str, user_id))
        conn.commit()
        conn.close()
        return True, "✅ Sharhingiz tahrirlandi va yangilandi!"
    else:
        cur.execute("""
        INSERT INTO reviews (user_id, rating, comment, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, rating, comment, now_str, now_str))
        conn.commit()
        conn.close()
        return True, "✅ Rahmat! Sharhingiz saqlandi."


def get_user_review(user_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reviews WHERE user_id = ?", (user_id,))
    res = row_to_dict(cur.fetchone())
    conn.close()
    return res


def get_reviews_summary() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), AVG(rating) FROM reviews")
    row = cur.fetchone()
    count = row[0] or 0
    avg_rating = round(row[1] or 0.0, 1)

    stars = {1:0, 2:0, 3:0, 4:0, 5:0}
    cur.execute("SELECT rating, COUNT(*) FROM reviews GROUP BY rating")
    for r, c in cur.fetchall():
        if r in stars:
            stars[r] = c

    conn.close()
    return {
        "count": count,
        "avg": avg_rating,
        "stars": stars
    }


def get_recent_reviews(limit: int = 10) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT r.*, u.full_name, u.username
    FROM reviews r
    LEFT JOIN users u ON r.user_id = u.user_id
    ORDER BY r.updated_at DESC LIMIT ?
    """, (limit,))
    res = rows_to_list(cur.fetchall())
    conn.close()
    return res


# ─── DETAILED ADVANCED STATISTICS ─────────────────────────────

def get_detailed_statistics() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now()

    # Time cutoffs
    today_start = now.strftime("%Y-%m-%d 00:00:00")
    yest_start  = (now - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
    yest_end    = (now - timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
    week_start  = (now - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")
    month_start = (now - timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")

    # User metrics
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (today_start,))
    new_today = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE created_at >= ? AND created_at <= ?", (yest_start, yest_end))
    new_yesterday = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (week_start,))
    new_week = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (month_start,))
    new_month = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE last_active >= ?", (today_start,))
    active_today = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE last_active >= ?", (week_start,))
    active_week = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE last_active >= ?", (month_start,))
    active_month = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
    banned_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE sub_expires > ?", (now.strftime("%Y-%m-%d %H:%M:%S"),))
    subscribed_users = cur.fetchone()[0]

    # Userbot stats
    cur.execute("SELECT COUNT(*) FROM userbot_sessions")
    userbots_count = cur.fetchone()[0]

    # Download stats
    cur.execute("SELECT COUNT(*), SUM(file_size) FROM downloads WHERE status = 'done'")
    d_row = cur.fetchone()
    total_downloads = d_row[0] or 0
    total_bytes = d_row[1] or 0
    total_gb = round(total_bytes / (1024 * 1024 * 1024), 2)

    cur.execute("SELECT COUNT(*) FROM downloads WHERE status = 'done' AND created_at >= ?", (today_start,))
    downloads_today = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM downloads WHERE status = 'done' AND created_at >= ?", (week_start,))
    downloads_week = cur.fetchone()[0]

    # Quality breakdown
    cur.execute("SELECT quality, COUNT(*) FROM downloads WHERE status = 'done' GROUP BY quality ORDER BY COUNT(*) DESC")
    quality_breakdown = cur.fetchall()

    # Top downloaded movies
    cur.execute("""
    SELECT title, COUNT(*) as cnt, quality
    FROM downloads
    WHERE status = 'done' AND title != ''
    GROUP BY title
    ORDER BY cnt DESC LIMIT 15
    """)
    top_movies = rows_to_list(cur.fetchall())

    # Reviews summary
    rev_summary = get_reviews_summary()

    # Domain breakdown from URLs
    cur.execute("SELECT url FROM downloads WHERE status = 'done'")
    urls = [r[0] for r in cur.fetchall() if r[0]]
    domains = {"asilmedia": 0, "uzmovie": 0, "uzmovi": 0, "kinolar": 0, "boshqa": 0}
    for u in urls:
        if "asilmedia" in u:
            domains["asilmedia"] += 1
        elif "uzmovie" in u:
            domains["uzmovie"] += 1
        elif "uzmovi" in u:
            domains["uzmovi"] += 1
        elif "kinolar" in u:
            domains["kinolar"] += 1
        else:
            domains["boshqa"] += 1

    conn.close()

    return {
        "users": {
            "total": total_users,
            "new_today": new_today,
            "new_yesterday": new_yesterday,
            "new_week": new_week,
            "new_month": new_month,
            "active_today": active_today,
            "active_week": active_week,
            "active_month": active_month,
            "banned": banned_users,
            "subscribed": subscribed_users
        },
        "userbots": {
            "total": userbots_count
        },
        "downloads": {
            "total": total_downloads,
            "total_gb": total_gb,
            "today": downloads_today,
            "week": downloads_week,
            "qualities": quality_breakdown,
            "domains": domains,
            "top_movies": top_movies
        },
        "reviews": rev_summary
    }

