from telegram import Update
from telegram.ext import ContextTypes

from config import EMOJI
from database import get_bool_setting, get_setting, reset_all_settings
from permissions import can_run_admin_command
import tone

LOCK_SETTINGS = [
    ("locked", "قفل گروه"),
    ("message_locked", "قفل پیام (کامل)"),
    ("antispam_disabled", "آنتی‌اسپم غیرفعال؟"),
    ("link_filter_disabled", "فیلتر لینک غیرفعال؟"),
    ("badword_filter_disabled", "فیلتر فحش غیرفعال؟"),
    ("forward_locked", "قفل فوروارد"),
    ("media_locked", "قفل مدیا"),
    ("location_locked", "قفل لوکیشن"),
    ("contact_locked", "قفل مخاطب"),
    ("hashtag_locked", "قفل هشتگ"),
    ("id_locked", "قفل آیدی"),
    ("reply_locked", "قفل ریپلای"),
    ("public_access_disabled", "دسترسی عمومی غیرفعال؟"),
    ("admin_call_enabled", "فراخوان ادمین"),
    ("report_enabled", "گزارش تخلف"),
]


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return

    chat_id = update.effective_chat.id
    lines = ["⚙️ *وضعیت فعلی تنظیمات گروه:*\n"]
    for key, label in LOCK_SETTINGS:
        on = get_bool_setting(chat_id, key, False)
        lines.append(f"{'✅' if on else '⬜️'} {label}")

    char_limit = get_setting(chat_id, "char_limit", "0")
    lines.append(f"\n🔡 محدودیت طول پیام: {char_limit if char_limit != '0' else 'غیرفعال'}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def reset_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    reset_all_settings(update.effective_chat.id)
    await update.message.reply_text(f"{EMOJI['check']} همه‌ی تنظیمات و نام‌های سفارشیِ دستورات این گروه به حالت پیش‌فرض برگشت.")
