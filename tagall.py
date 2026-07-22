from telegram import Update
from telegram.ext import ContextTypes

from config import EMOJI
from database import list_known_members
from permissions import can_run_admin_command
import tone

BATCH_SIZE = 10  # تعداد تگ در هر پیام (برای جلوگیری از پیام خیلی طولانی)


def _mention_html(user_id: int, name: str, username: str | None) -> str:
    """
    اگه کاربر یوزرنیم داشته باشه، با @یوزرنیم تگ می‌شه (تضمینی کلیک‌پذیره).
    اگه یوزرنیم نداشته باشه، با لینک آیدی عددی + اسمش تگ می‌شه (fallback).
    """
    safe_name = name or "کاربر"
    if username:
        return f"@{username}"
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'


async def tag_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return

    chat = update.effective_chat
    members = list_known_members(chat.id)

    if not members:
        await update.message.reply_text(
            f"{EMOJI['warn']} هنوز هیچ عضوی رو نشناختم (کسی پیام نداده). "
            f"فقط اعضایی که حداقل یه پیام فرستاده باشن قابل‌تگ‌ان."
        )
        return

    await update.message.reply_text(f"📣 در حال تگ کردن {len(members)} عضو، در چند پیام جدا...")

    for i in range(0, len(members), BATCH_SIZE):
        batch = members[i:i + BATCH_SIZE]
        mentions = " ".join(_mention_html(uid, name, username) for uid, name, username in batch)
        try:
            await context.bot.send_message(chat.id, mentions, parse_mode="HTML")
        except Exception:
            # اگه HTML/لینک آیدی هم کار نکرد، حداقل اسم و آیدی رو به‌صورت متن ساده می‌فرستیم
            fallback = " | ".join(f"{name or 'کاربر'} ({uid})" for uid, name, _ in batch)
            await context.bot.send_message(chat.id, fallback)
