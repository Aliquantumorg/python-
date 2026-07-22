"""
سیستم ضد سوءاستفاده (Anti-Abuse) - نسخه‌ی دقیق‌شده:

۱) اگه کاربر روی یک دکمه‌ی اینلاینِ خاص (همون callback_data) چند بار پشت‌سرهم بزنه
   (نه اینکه چندتا دکمه‌ی مختلف رو استفاده کنه)، مسدود می‌شه.
۲) اگه توی پیوی، دستور «شروع» رو بیش از حد مجاز بزنه، مسدود می‌شه.

بعد از مسدود شدن، تا پایان مدت محدودیت، بات به هیچ کدوم از اکشن‌های اون کاربر (نه دستور، نه دکمه) پاسخ نمی‌ده.
با تکرار مسدودشدن، مدت محدودیت بیشتر می‌شه: ۱۰ -> ۳۰ -> ۶۰ -> ۱۲۰ دقیقه.
"""
import time
from collections import defaultdict, deque

BLOCK_STEPS_MINUTES = [10, 30, 60, 120]

# --- تنظیمات هر دسته از محدودیت ---
BUTTON_REPEAT_MAX = 3          # حداکثر کلیک مجاز روی یک دکمه‌ی یکسان
BUTTON_REPEAT_WINDOW = 6        # در این بازه‌ی زمانی (ثانیه)

PV_START_MAX = 5                # حداکثر «شروع» زدن مجاز در پیوی
PV_START_WINDOW = 60             # در این بازه‌ی زمانی (ثانیه)

_action_log = defaultdict(deque)   # (user_id, action_key) -> deque[timestamp]
_block_until = {}                  # user_id -> unix_timestamp
_offense_count = defaultdict(int)  # user_id -> تعداد دفعاتی که بلاک شده


def is_blocked(user_id: int) -> bool:
    until = _block_until.get(user_id)
    if until and time.time() < until:
        return True
    if until and time.time() >= until:
        _block_until.pop(user_id, None)
    return False


def remaining_block_minutes(user_id: int) -> int:
    until = _block_until.get(user_id, 0)
    remaining = max(0, int(until - time.time()))
    return (remaining // 60) + (1 if remaining % 60 else 0)


def _trigger_block(user_id: int):
    offense = _offense_count[user_id]
    minutes = BLOCK_STEPS_MINUTES[min(offense, len(BLOCK_STEPS_MINUTES) - 1)]
    _block_until[user_id] = time.time() + minutes * 60
    _offense_count[user_id] += 1


def _register(user_id: int, action_key: str, max_count: int, window_seconds: int) -> bool:
    """خروجی True یعنی مجازه ادامه بده. False یعنی الان بلاک شد یا از قبل بلاک بوده."""
    if is_blocked(user_id):
        return False

    now = time.time()
    key = (user_id, action_key)
    log = _action_log[key]
    log.append(now)
    while log and now - log[0] > window_seconds:
        log.popleft()

    if len(log) > max_count:
        _trigger_block(user_id)
        log.clear()
        return False

    return True


def register_button_press(user_id: int, callback_data: str) -> bool:
    """برای هر کلیک روی هر دکمه‌ی اینلاین صدا بزن. فقط تکرارِ زیاد روی همون دکمه‌ی خاص مسدود می‌کنه."""
    return _register(user_id, f"btn:{callback_data}", BUTTON_REPEAT_MAX, BUTTON_REPEAT_WINDOW)


def register_pv_start(user_id: int) -> bool:
    """برای هر بار زدن «شروع» در پیوی صدا بزن."""
    return _register(user_id, "pv_start", PV_START_MAX, PV_START_WINDOW)
