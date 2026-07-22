import time
from collections import defaultdict, deque
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

from config import EMOJI, FLOOD_MAX_MESSAGES, FLOOD_WINDOW_SECONDS, FLOOD_MUTE_MINUTES, FLOOD_LONG_MUTE_MINUTES
from database import log_action, get_bool_setting, set_setting
from permissions import can_run_admin_command
import tone

# (chat_id, user_id) -> deque[(timestamp, message_id)]  - این حالا هر نوع پیامی رو ردیابی می‌کنه (متن، گیف، عکس و...)
_message_log = defaultdict(deque)
_offense_count = defaultdict(int)


async def lock_spam(update, context):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    set_setting(update.effective_chat.id, "antispam_disabled", "0")
    await update.message.reply_text(f"{EMOJI['lock']} آنتی‌اسپم فعال شد.")


async def unlock_spam(update, context):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    set_setting(update.effective_chat.id, "antispam_disabled", "1")
    await update.message.reply_text(f"{EMOJI['unlock']} آنتی‌اسپم غیرفعال شد.")


async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    برای هر نوع پیامی صداست: متن، گیف (انیمیشن)، عکس، استیکر و غیره.
    وقتی فلود تشخیص داده بشه، تمام پیام‌های همون کاربر که توی بازه‌ی زمانی اخیر فرستاده (نه فقط آخری) پاک می‌شن.
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.message
    if not message or chat.type not in ("group", "supergroup"):
        return False
    if get_bool_setting(chat.id, "antispam_disabled", False):
        return False
    if await can_run_admin_command(update, context):
        return False  # ادمین‌ها/مالک از آنتی‌فلود معافن

    key = (chat.id, user.id)
    now = time.time()
    log = _message_log[key]
    log.append((now, message.message_id))
    while log and now - log[0][0] > FLOOD_WINDOW_SECONDS:
        log.popleft()

    if len(log) <= FLOOD_MAX_MESSAGES:
        return False

    # فلود تشخیص داده شد: همه‌ی پیام‌های این کاربر توی همین بازه (متن یا گیف یا هرچی) پاک می‌شن
    for _, mid in log:
        try:
            await context.bot.delete_message(chat.id, mid)
        except Exception:
            pass

    _offense_count[key] += 1
    offense = _offense_count[key]
    minutes = FLOOD_LONG_MUTE_MINUTES if offense >= 2 else FLOOD_MUTE_MINUTES
    until = int(now) + minutes * 60

    try:
        await context.bot.restrict_chat_member(
            chat.id, user.id, permissions=ChatPermissions(can_send_messages=False), until_date=until
        )
    except Exception:
        pass

    log_action(chat.id, user.id, f"flood_mute:{minutes}m")
    await context.bot.send_message(
        chat.id,
        f"{EMOJI['fire']} {user.first_name} به‌خاطر ارسال پیام/گیف پشت‌سرهم (فلود)، "
        f"به مدت {minutes} دقیقه سکوت شد و پیام‌های اسپمش پاک شدن {EMOJI['mute']}",
    )
    log.clear()
    return True
