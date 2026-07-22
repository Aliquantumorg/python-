from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

from config import EMOJI
from database import set_setting, get_bool_setting
from permissions import can_run_admin_command
import tone

ADMIN_CALL_TRIGGERS = ("ادمین", "@admin")


async def _toggle(update, context, key, value, msg):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    set_setting(update.effective_chat.id, key, value)
    await update.message.reply_text(msg)


async def enable_admin_call(u, c): await _toggle(u, c, "admin_call_enabled", "1", f"{EMOJI['check']} فراخوان ادمین فعال شد.")
async def disable_admin_call(u, c): await _toggle(u, c, "admin_call_enabled", "0", f"{EMOJI['cross']} فراخوان ادمین غیرفعال شد.")

async def enable_report(u, c): await _toggle(u, c, "report_enabled", "1", f"{EMOJI['check']} گزارش تخلف فعال شد.")
async def disable_report(u, c): await _toggle(u, c, "report_enabled", "0", f"{EMOJI['cross']} گزارش تخلف غیرفعال شد.")


async def handle_admin_call(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگه فعال باشه و کسی «ادمین» یا «@admin» بنویسه، به ادمین‌ها اطلاع میده"""
    chat = update.effective_chat
    text = update.message.text
    if chat.type not in ("group", "supergroup") or not text:
        return False
    if not get_bool_setting(chat.id, "admin_call_enabled", False):
        return False
    if not any(t in text for t in ADMIN_CALL_TRIGGERS):
        return False

    try:
        admins = await context.bot.get_chat_administrators(chat.id)
    except Exception:
        return False

    mentions = " ".join(
        f'<a href="tg://user?id={a.user.id}">{a.user.first_name}</a>'
        for a in admins if a.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    )
    await update.message.reply_text(f"🔔 {mentions}\nیکی از اعضا نیاز به کمک ادمین داره!", parse_mode="HTML")
    return True


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """با ریپلای روی پیام تخلف‌آمیز + نوشتن «گزارش»، به ادمین‌ها اطلاع میده"""
    chat = update.effective_chat
    if not get_bool_setting(chat.id, "report_enabled", False):
        await update.message.reply_text(f"{EMOJI['warn']} قابلیت گزارش تخلف در این گروه فعال نیست.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text(f"{EMOJI['warn']} روی پیام موردنظر ریپلای کن و بنویس «گزارش».")
        return

    try:
        admins = await context.bot.get_chat_administrators(chat.id)
    except Exception:
        admins = []

    mentions = " ".join(
        f'<a href="tg://user?id={a.user.id}">{a.user.first_name}</a>'
        for a in admins if a.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    ) or "ادمین‌ها"

    reporter = update.effective_user.first_name
    reported = update.message.reply_to_message.from_user.first_name
    await update.message.reply_text(
        f"🕵️‍♂️ {mentions}\n{reporter} از {reported} گزارش تخلف داد. لطفاً بررسی کنید.",
        parse_mode="HTML",
    )
