from telegram import Update
from telegram.ext import ContextTypes

from config import EMOJI
from permissions import can_run_admin_command
import tone


async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return

    parts = update.message.text.strip().split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await update.message.reply_text(f"{EMOJI['warn']} فرمت درست: «یادآوری 10 وقت جلسه‌ست»")
        return

    minutes = int(parts[1])
    text = parts[2]
    chat_id = update.effective_chat.id

    if not context.job_queue:
        await update.message.reply_text(f"{EMOJI['cross']} JobQueue فعال نیست، یادآوری زمان‌بندی‌شده کار نمی‌کنه.")
        return

    context.job_queue.run_once(_send_reminder, minutes * 60, data=(chat_id, text), name=f"reminder_{chat_id}")
    await update.message.reply_text(f"⏰ یادآوری برای {minutes} دقیقه‌ی دیگه تنظیم شد.")


async def _send_reminder(context: ContextTypes.DEFAULT_TYPE):
    chat_id, text = context.job.data
    await context.bot.send_message(chat_id, f"⏰ یادآوری:\n{text}")
