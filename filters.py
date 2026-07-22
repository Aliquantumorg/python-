import re
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

from config import EMOJI
from database import list_bad_words, bump_message_count, add_warning, reset_warning, log_action, get_bool_setting, set_setting
from permissions import can_run_admin_command
import tone

LINK_PATTERN = re.compile(r"(https?://|t\.me/|ble\.ir/|@\w{4,})", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(09\d{9}|\+989\d{9})")
CARD_PATTERN = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
MAX_WARNINGS = 3


async def _toggle(update, context, key, value, msg):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    set_setting(update.effective_chat.id, key, value)
    await update.message.reply_text(msg)


async def lock_link(update, context):
    await _toggle(update, context, "link_filter_disabled", "0", f"{EMOJI['lock']} فیلتر لینک فعال شد.")


async def unlock_link(update, context):
    await _toggle(update, context, "link_filter_disabled", "1", f"{EMOJI['unlock']} فیلتر لینک غیرفعال شد.")


async def lock_badwords(update, context):
    await _toggle(update, context, "badword_filter_disabled", "0", f"{EMOJI['lock']} فیلتر فحش فعال شد.")


async def unlock_badwords(update, context):
    await _toggle(update, context, "badword_filter_disabled", "1", f"{EMOJI['unlock']} فیلتر فحش غیرفعال شد.")


async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    user = update.effective_user
    chat = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        return  # فیلتر فقط داخل گروه معنی داره

    bump_message_count(chat.id, user.id, user.username or user.first_name)

    text = message.text
    text_lower = text.lower()
    bad_words = list_bad_words()
    badwords_off = get_bool_setting(chat.id, "badword_filter_disabled", False)
    links_off = get_bool_setting(chat.id, "link_filter_disabled", False)

    violated = (not badwords_off) and any(w.lower() in text_lower for w in bad_words)
    reason = None
    if violated:
        reason = "استفاده از کلمه‌ی نامناسب"
    elif CARD_PATTERN.search(text):
        reason = "ارسال شماره کارت بانکی (احتمال کلاهبرداری)"
    elif PHONE_PATTERN.search(text):
        reason = "ارسال شماره تلفن"
    elif (not links_off) and LINK_PATTERN.search(text):
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            reason = "ارسال لینک/تبلیغ غیرمجاز"

    if not reason:
        return

    try:
        await message.delete()
    except Exception:
        pass

    warn_count = add_warning(chat.id, user.id)
    log_action(chat.id, user.id, f"filter:{reason}")

    if warn_count >= MAX_WARNINGS:
        await context.bot.ban_chat_member(chat.id, user.id)
        reset_warning(chat.id, user.id)
        await context.bot.send_message(
            chat.id,
            f"{EMOJI['ban']} کاربر {user.mention_html()} به‌خاطر تکرار «{reason}» از گروه حذف شد.",
            parse_mode="HTML",
        )
    else:
        await context.bot.send_message(
            chat.id,
            f"{EMOJI['warn']} {user.mention_html()} پیامت به‌خاطر «{reason}» حذف شد.\n"
            f"اخطار {warn_count} از {MAX_WARNINGS} {EMOJI['fire']}",
            parse_mode="HTML",
        )
