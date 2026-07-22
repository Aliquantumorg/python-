from telegram import Update
from telegram.ext import ContextTypes

from config import EMOJI
from database import add_custom_filter, remove_custom_filter, get_custom_filter_response
from permissions import can_run_admin_command
import tone


async def add_filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    استفاده: روی پیامی که متنش «تریگر» ماست ریپلای کن و بنویس «فیلتر پاسخ»
    مثال: ریپلای روی پیامی که توش نوشته «طاها»، بعد بنویس «فیلتر گاوه»
    از این به بعد هر وقت کسی «طاها» بنویسه، بات جواب میده «گاوه»
    """
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return

    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text(
            f"{EMOJI['warn']} باید روی پیامی که متنش رو می‌خوای تریگر کنی ریپلای بزنی، بعد بنویسی «فیلتر پاسخ»."
        )
        return

    text = update.message.text.strip()
    if not text.startswith("فیلتر "):
        return
    response = text[len("فیلتر "):].strip()
    trigger = update.message.reply_to_message.text.strip()

    if not response:
        await update.message.reply_text(f"{EMOJI['warn']} باید بعد از «فیلتر» یه متن پاسخ هم بنویسی.")
        return

    add_custom_filter(update.effective_chat.id, trigger, response)
    await update.message.reply_text(
        f"{EMOJI['check']} از این به بعد هر وقت کسی بنویسه «{trigger}»، جواب میدم «{response}»"
    )


async def remove_filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استفاده: روی پیامی که تریگرشه ریپلای کن و بنویس «حذف فیلتر»"""
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return

    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text(f"{EMOJI['warn']} روی پیامی که تریگرشه ریپلای بزن و بنویس «حذف فیلتر».")
        return

    trigger = update.message.reply_to_message.text.strip()
    remove_custom_filter(update.effective_chat.id, trigger)
    await update.message.reply_text(f"{EMOJI['check']} فیلتر «{trigger}» حذف شد.")


async def handle_custom_filter_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگه متن پیام دقیقاً یه تریگر ثبت‌شده باشه، پاسخ خودکار میده. خروجی True یعنی مصرف شد."""
    if not update.message or not update.message.text:
        return False
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return False

    response = get_custom_filter_response(chat.id, update.message.text)
    if response is None:
        return False

    await update.message.reply_text(response)
    return True
