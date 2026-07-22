from telegram import Update
from telegram.ext import ContextTypes

from config import EMOJI
from database import set_setting, get_bool_setting
from permissions import can_run_admin_command, is_owner
import tone


async def _toggle(update, context, key, value, msg):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    set_setting(update.effective_chat.id, key, value)
    await update.message.reply_text(msg)


async def enable_public_access(u, c): await _toggle(u, c, "public_access_disabled", "0", f"{EMOJI['check']} دسترسی عمومی برای همه‌ی اعضا فعال شد.")
async def disable_public_access(u, c): await _toggle(u, c, "public_access_disabled", "1", f"{EMOJI['cross']} دسترسی عمومی غیرفعال شد؛ فقط ادمین‌ها/مالک می‌تونن از بازی‌ها و امکانات عمومی استفاده کنن.")


def is_public_access_blocked(chat_id) -> bool:
    return get_bool_setting(chat_id, "public_access_disabled", False)


async def set_welcome_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    text = update.message.text
    prefix = "تنظیم خوش آمد "
    if not text.startswith(prefix):
        await update.message.reply_text(f"{EMOJI['warn']} فرمت درست: «تنظیم خوش آمد متن دلخواه»")
        return
    new_text = text[len(prefix):].strip()
    if not new_text:
        await update.message.reply_text(f"{EMOJI['warn']} باید بعدش یه متن هم بنویسی.")
        return
    set_setting(update.effective_chat.id, "custom_welcome_text", new_text)
    await update.message.reply_text(f"{EMOJI['check']} متن خوش‌آمدگویی گروه به‌روزرسانی شد.")
