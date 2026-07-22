from telegram import Update
from telegram.ext import ContextTypes

from config import EMOJI
from database import set_setting, get_bool_setting
from permissions import can_run_admin_command
import tone


async def lock_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    set_setting(update.effective_chat.id, "forward_locked", "1")
    await update.message.reply_text(f"{EMOJI['lock']} از این به بعد پیام‌های فورواردی حذف می‌شن.")


async def unlock_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    set_setting(update.effective_chat.id, "forward_locked", "0")
    await update.message.reply_text(f"{EMOJI['unlock']} قفل فوروارد برداشته شد.")


def _is_forwarded(message) -> bool:
    # پشتیبانی از نسخه‌های مختلف کتابخونه/فرمت‌های فوروارد
    return bool(
        getattr(message, "forward_origin", None)
        or getattr(message, "forward_date", None)
        or getattr(message, "forward_from", None)
        or getattr(message, "forward_from_chat", None)
    )


async def enforce_forward_lock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگه قفل فوروارد فعاله و پیام فورواردیه، حذفش می‌کنه. خروجی True یعنی بلاک شد."""
    message = update.message
    chat = update.effective_chat
    if not message or chat.type not in ("group", "supergroup"):
        return False
    if not get_bool_setting(chat.id, "forward_locked", False):
        return False
    if not _is_forwarded(message):
        return False

    # ادمین‌ها و مالک از قفل فوروارد مستثنی هستن
    if await can_run_admin_command(update, context):
        return False

    try:
        await message.delete()
    except Exception:
        pass
    return True
