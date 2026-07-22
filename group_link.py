from telegram import Update
from telegram.ext import ContextTypes

from config import EMOJI
import tone


async def send_group_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(f"{EMOJI['warn']} این دستور فقط داخل گروه معنی داره.")
        return

    try:
        chat_info = await context.bot.get_chat(chat.id)
        link = chat_info.invite_link
        if not link:
            link = await context.bot.export_chat_invite_link(chat.id)
    except Exception:
        await update.message.reply_text(
            f"{EMOJI['cross']} نتونستم لینک گروه رو بگیرم. مطمئن شو گروه‌یار ادمینه و دسترسی «دعوت با لینک» رو داره."
        )
        return

    await update.message.reply_text(tone.tt(chat.id, "group_link_result", link=link))
