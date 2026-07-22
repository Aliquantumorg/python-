from telegram import Update
from telegram.ext import ContextTypes

from config import EMOJI
from database import log_action
from permissions import can_run_admin_command
from recent_messages import get_recent_bot_messages
import tone


async def purge_bot_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return

    chat_id = update.effective_chat.id
    bot_message_ids = get_recent_bot_messages(chat_id)
    deleted = 0
    for mid in bot_message_ids:
        try:
            await context.bot.delete_message(chat_id, mid)
            deleted += 1
        except Exception:
            pass

    log_action(chat_id, update.effective_user.id, "purge_bot")
    await context.bot.send_message(
        chat_id,
        f"🧹 {deleted} پیام از ربات‌ها پاکسازی شد {EMOJI['check']}\n"
        f"(این فقط پیام‌های اخیریه که بات از وقتی روشن شده دیده، نه کل تاریخچه‌ی گروه)",
    )
