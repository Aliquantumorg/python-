from telegram import Update
from telegram.ext import ContextTypes

from config import EMOJI
from database import set_setting
from permissions import can_run_admin_command
import tone


async def mute_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return

    parts = update.message.text.strip().split()
    if len(parts) < 3 or not parts[2].isdigit():
        await update.message.reply_text(f"{EMOJI['warn']} فرمت درست: «بی‌صدا همه 15» (به دقیقه)")
        return

    minutes = int(parts[2])
    chat_id = update.effective_chat.id
    set_setting(chat_id, "locked", "1")
    await update.message.reply_text(f"{EMOJI['mute']} گروه به مدت {minutes} دقیقه کاملاً بی‌صدا شد.")

    if context.job_queue:
        context.job_queue.run_once(_auto_unlock, minutes * 60, data=chat_id, name=f"muteall_{chat_id}")
    else:
        await update.message.reply_text(
            f"{EMOJI['warn']} توجه: JobQueue فعال نیست، پس بازگشت خودکار انجام نمی‌شه — "
            f"باید دستی «باصدا همه» رو بزنی."
        )


async def _auto_unlock(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data
    set_setting(chat_id, "locked", "0")
    await context.bot.send_message(chat_id, f"{EMOJI['unlock']} زمان سکوت گروه تموم شد، همه می‌تونن پیام بدن.")


async def unmute_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    set_setting(update.effective_chat.id, "locked", "0")
    await update.message.reply_text(f"{EMOJI['unlock']} سکوت گروه برداشته شد.")
