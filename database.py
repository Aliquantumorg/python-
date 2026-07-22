import sqlite3
import time
import json
from contextlib import contextmanager

from config import DB_PATH, DEFAULT_BAD_WORDS, BLOCK_LINKS_FOR_MEMBERS_DEFAULT


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS known_chats (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            type TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            chat_id INTEGER, user_id INTEGER, username TEXT, count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS warnings (
            chat_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS vip_users (
            chat_id INTEGER, user_id INTEGER, expires_at INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS coins (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS game_scores (
            user_id INTEGER, game TEXT, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, game)
        )""")

        # تنظیمات عمومی هر چت (کلید-مقدار) - پایه‌ی توسعه‌ی نامحدود قابلیت‌ها
        c.execute("""CREATE TABLE IF NOT EXISTS settings (
            chat_id INTEGER, key TEXT, value TEXT,
            PRIMARY KEY (chat_id, key)
        )""")

        # کانال‌های عضویت اجباری - چندکاناله و قابل مدیریت از پنل
        c.execute("""CREATE TABLE IF NOT EXISTS required_channels (
            channel_username TEXT PRIMARY KEY,
            added_at INTEGER
        )""")

        # کلمات ممنوعه‌ی سراسری قابل افزودن/حذف از پنل
        c.execute("""CREATE TABLE IF NOT EXISTS bad_words (
            word TEXT PRIMARY KEY
        )""")

        # لاگ اکشن‌های ادمین برای پیگیری
        c.execute("""CREATE TABLE IF NOT EXISTS action_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER, chat_id INTEGER, actor_id INTEGER, action TEXT, target_id INTEGER
        )""")

        # فیلترهای سفارشی: هر بار کلمه‌ی trigger نوشته بشه، بات با response جواب میده
        c.execute("""CREATE TABLE IF NOT EXISTS custom_filters (
            chat_id INTEGER, trigger TEXT, response TEXT,
            PRIMARY KEY (chat_id, trigger)
        )""")

        # هر عضوی که حداقل یه پیام (هر نوعی) توی گروه فرستاده، اینجا ثبت میشه
        c.execute("""CREATE TABLE IF NOT EXISTS known_members (
            chat_id INTEGER, user_id INTEGER, name TEXT, username TEXT,
            PRIMARY KEY (chat_id, user_id)
        )""")
        # مهاجرت نرم: اگه دیتابیس قدیمی بدون ستون username باشه، اضافه‌ش کن
        try:
            c.execute("ALTER TABLE known_members ADD COLUMN username TEXT")
        except Exception:
            pass

        # کاربرانی که ادمین/مالک به‌صورت دستی از عضویت اجباری معافشون کرده
        c.execute("""CREATE TABLE IF NOT EXISTS force_join_exempt (
            chat_id INTEGER, user_id INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )""")

        # نام سفارشیِ دستورات (برای ویرایش کلمه‌ی فعال‌ساز هر دستور از پنل)
        c.execute("""CREATE TABLE IF NOT EXISTS command_aliases (
            chat_id INTEGER, command_key TEXT, trigger TEXT,
            PRIMARY KEY (chat_id, command_key)
        )""")

        conn.commit()

        # مقداردهی اولیه‌ی کلمات ممنوعه‌ی پیش‌فرض (فقط بار اول)
        c.execute("SELECT COUNT(*) FROM bad_words")
        if c.fetchone()[0] == 0:
            for w in DEFAULT_BAD_WORDS:
                c.execute("INSERT OR IGNORE INTO bad_words (word) VALUES (?)", (w,))
            conn.commit()


# ================= چت‌ها (برای ارسال همگانی) =================
def register_chat(chat_id, title, chat_type):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO known_chats (chat_id, title, type) VALUES (?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title, type=excluded.type""",
            (chat_id, title, chat_type),
        )
        conn.commit()


def remove_chat(chat_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM known_chats WHERE chat_id=?", (chat_id,))
        conn.commit()


def all_known_chats():
    with get_conn() as conn:
        return conn.execute("SELECT chat_id, title, type FROM known_chats").fetchall()


# ================= آمار پیام =================
def bump_message_count(chat_id, user_id, username):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO messages (chat_id, user_id, username, count) VALUES (?, ?, ?, 1)
               ON CONFLICT(chat_id, user_id)
               DO UPDATE SET count = count + 1, username = excluded.username""",
            (chat_id, user_id, username),
        )
        conn.commit()


def top_users(chat_id, limit=10):
    with get_conn() as conn:
        return conn.execute(
            "SELECT username, count FROM messages WHERE chat_id=? ORDER BY count DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()


def user_message_count(chat_id, user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT count FROM messages WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        ).fetchone()
        return row[0] if row else 0


# ================= اخطارها =================
def add_warning(chat_id, user_id):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO warnings (chat_id, user_id, count) VALUES (?, ?, 1)
               ON CONFLICT(chat_id, user_id) DO UPDATE SET count = count + 1""",
            (chat_id, user_id),
        )
        conn.commit()
        return conn.execute(
            "SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        ).fetchone()[0]


def reset_warning(chat_id, user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        conn.commit()


# ================= تنظیمات عمومی هر چت =================
def set_setting(chat_id, key, value):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO settings (chat_id, key, value) VALUES (?, ?, ?)
               ON CONFLICT(chat_id, key) DO UPDATE SET value=excluded.value""",
            (chat_id, key, str(value)),
        )
        conn.commit()


def get_setting(chat_id, key, default=None):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE chat_id=? AND key=?", (chat_id, key)
        ).fetchone()
        return row[0] if row else default


def get_bool_setting(chat_id, key, default=False):
    val = get_setting(chat_id, key, None)
    if val is None:
        return default
    return val in ("1", "true", "True")


# ================= لحن گفتگوی هر چت =================
def get_tone(chat_id):
    """None یعنی هنوز لحن انتخاب نشده (باید ازش پرسیده بشه)"""
    return get_setting(chat_id, "tone", None)


def set_tone(chat_id, tone):
    set_setting(chat_id, "tone", tone)


# ================= کانال‌های عضویت اجباری (چندکاناله) =================
def add_required_channel(username):
    username = username if username.startswith("@") else f"@{username}"
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO required_channels (channel_username, added_at) VALUES (?, ?)",
            (username, int(time.time())),
        )
        conn.commit()
    return username


def remove_required_channel(username):
    username = username if username.startswith("@") else f"@{username}"
    with get_conn() as conn:
        conn.execute("DELETE FROM required_channels WHERE channel_username=?", (username,))
        conn.commit()


def list_required_channels():
    with get_conn() as conn:
        return [r[0] for r in conn.execute("SELECT channel_username FROM required_channels").fetchall()]


# ================= کلمات ممنوعه =================
def add_bad_word(word):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO bad_words (word) VALUES (?)", (word,))
        conn.commit()


def remove_bad_word(word):
    with get_conn() as conn:
        conn.execute("DELETE FROM bad_words WHERE word=?", (word,))
        conn.commit()


def list_bad_words():
    with get_conn() as conn:
        return [r[0] for r in conn.execute("SELECT word FROM bad_words").fetchall()]


# ================= وی‌آی‌پی =================
def set_vip(chat_id, user_id, days):
    expires_at = int(time.time()) + days * 86400
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO vip_users (chat_id, user_id, expires_at) VALUES (?, ?, ?)
               ON CONFLICT(chat_id, user_id) DO UPDATE SET expires_at=excluded.expires_at""",
            (chat_id, user_id, expires_at),
        )
        conn.commit()


def is_vip(chat_id, user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT expires_at FROM vip_users WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        ).fetchone()
        return bool(row) and row[0] > int(time.time())


# ================= سکه‌ی داخلی =================
def add_coins(user_id, amount):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO coins (user_id, balance) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?""",
            (user_id, amount, amount),
        )
        conn.commit()


def get_coins(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT balance FROM coins WHERE user_id=?", (user_id,)).fetchone()
        return row[0] if row else 0


# ================= امتیاز بازی‌ها =================
def record_game_result(user_id, game, won):
    with get_conn() as conn:
        if won:
            conn.execute(
                """INSERT INTO game_scores (user_id, game, wins, losses) VALUES (?, ?, 1, 0)
                   ON CONFLICT(user_id, game) DO UPDATE SET wins = wins + 1""",
                (user_id, game),
            )
        else:
            conn.execute(
                """INSERT INTO game_scores (user_id, game, wins, losses) VALUES (?, ?, 0, 1)
                   ON CONFLICT(user_id, game) DO UPDATE SET losses = losses + 1""",
                (user_id, game),
            )
        conn.commit()


def get_game_score(user_id, game):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT wins, losses FROM game_scores WHERE user_id=? AND game=?", (user_id, game)
        ).fetchone()
        return row if row else (0, 0)


# ================= لاگ اکشن ادمین =================
def log_action(chat_id, actor_id, action, target_id=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO action_log (ts, chat_id, actor_id, action, target_id) VALUES (?, ?, ?, ?, ?)",
            (int(time.time()), chat_id, actor_id, action, target_id),
        )
        conn.commit()


def recent_actions(limit=15):
    with get_conn() as conn:
        return conn.execute(
            "SELECT ts, chat_id, actor_id, action, target_id FROM action_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()


# ================= فیلترهای سفارشی (تریگر -> پاسخ خودکار) =================
def add_custom_filter(chat_id, trigger, response):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO custom_filters (chat_id, trigger, response) VALUES (?, ?, ?)
               ON CONFLICT(chat_id, trigger) DO UPDATE SET response=excluded.response""",
            (chat_id, trigger.strip(), response.strip()),
        )
        conn.commit()


def remove_custom_filter(chat_id, trigger):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM custom_filters WHERE chat_id=? AND trigger=?", (chat_id, trigger.strip())
        )
        conn.commit()


def get_custom_filter_response(chat_id, trigger):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT response FROM custom_filters WHERE chat_id=? AND trigger=?",
            (chat_id, trigger.strip()),
        ).fetchone()
        return row[0] if row else None


def list_custom_filters(chat_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT trigger, response FROM custom_filters WHERE chat_id=?", (chat_id,)
        ).fetchall()


# ================= اعضای شناخته‌شده (برای دستور «تگ») =================
def record_known_member(chat_id, user_id, name, username=None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO known_members (chat_id, user_id, name, username) VALUES (?, ?, ?, ?)
               ON CONFLICT(chat_id, user_id) DO UPDATE SET name=excluded.name, username=excluded.username""",
            (chat_id, user_id, name, username),
        )
        conn.commit()


def list_known_members(chat_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT user_id, name, username FROM known_members WHERE chat_id=?", (chat_id,)
        ).fetchall()


# ================= معافیت از عضویت اجباری =================
def add_force_join_exempt(chat_id, user_id):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO force_join_exempt (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id)
        )
        conn.commit()


def is_force_join_exempt(chat_id, user_id) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM force_join_exempt WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        ).fetchone()
        return row is not None


def remove_force_join_exempt(chat_id, user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM force_join_exempt WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        conn.commit()


# ================= نام سفارشی دستورات =================
def set_command_alias(chat_id, command_key, trigger):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO command_aliases (chat_id, command_key, trigger) VALUES (?, ?, ?)
               ON CONFLICT(chat_id, command_key) DO UPDATE SET trigger=excluded.trigger""",
            (chat_id, command_key, trigger.strip()),
        )
        conn.commit()


def get_command_alias(chat_id, command_key):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT trigger FROM command_aliases WHERE chat_id=? AND command_key=?",
            (chat_id, command_key),
        ).fetchone()
        return row[0] if row else None


def reset_command_alias(chat_id, command_key):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM command_aliases WHERE chat_id=? AND command_key=?", (chat_id, command_key)
        )
        conn.commit()


def list_command_aliases(chat_id):
    with get_conn() as conn:
        return dict(conn.execute(
            "SELECT command_key, trigger FROM command_aliases WHERE chat_id=?", (chat_id,)
        ).fetchall())


def reset_all_settings(chat_id):
    """ریست تنظیمات: پاک کردن تمام تنظیمات و نام‌های سفارشیِ همین گروه (فیلترها و اخطارها دست‌نخورده می‌مونن)"""
    with get_conn() as conn:
        conn.execute("DELETE FROM settings WHERE chat_id=?", (chat_id,))
        conn.execute("DELETE FROM command_aliases WHERE chat_id=?", (chat_id,))
        conn.commit()
