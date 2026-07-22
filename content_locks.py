import re
from telegram import Update
from telegram.ext import ContextTypes

from config import EMOJI
from database import set_setting, get_bool_setting, get_setting
from permissions import can_run_admin_command
import tone

HASHTAG_PATTERN = re.compile(r"#\w+")
MENTION_PATTERN = re.compile(r"@\w{3,}")


async def _toggle(update, context, key, value, msg):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    set_setting(update.effective_chat.id, key, value)
    await update.message.reply_text(msg)


# ---- مدیا (عکس/فیلم/گیف/استیکر/ویس/ویدیو مسیج) ----
async def lock_media(u, c): await _toggle(u, c, "media_locked", "1", f"{EMOJI['lock']} قفل مدیا فعال شد (همه‌ی عکس/فیلم/گیف/استیکر/ویس/ویدیو‌مسیج حذف می‌شن).")
async def unlock_media(u, c): await _toggle(u, c, "media_locked", "0", f"{EMOJI['unlock']} قفل مدیا برداشته شد.")

# ---- گیف (انیمیشن) - جدا از قفل کلی مدیا ----
async def lock_gif(u, c): await _toggle(u, c, "gif_locked", "1", f"{EMOJI['lock']} قفل گیف فعال شد.")
async def unlock_gif(u, c): await _toggle(u, c, "gif_locked", "0", f"{EMOJI['unlock']} قفل گیف برداشته شد.")

# ---- استیکر - جدا از قفل کلی مدیا ----
async def lock_sticker(u, c): await _toggle(u, c, "sticker_locked", "1", f"{EMOJI['lock']} قفل استیکر فعال شد.")
async def unlock_sticker(u, c): await _toggle(u, c, "sticker_locked", "0", f"{EMOJI['unlock']} قفل استیکر برداشته شد.")


async def enforce_media_lock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    if not update.message or chat.type not in ("group", "supergroup"):
        return False
    if await can_run_admin_command(update, context):
        return False
    m = update.message

    media_all_locked = get_bool_setting(chat.id, "media_locked", False)
    gif_locked = get_bool_setting(chat.id, "gif_locked", False)
    sticker_locked = get_bool_setting(chat.id, "sticker_locked", False)

    should_delete = False
    if media_all_locked and any([m.photo, m.video, m.animation, m.voice, m.video_note, m.sticker, m.document]):
        should_delete = True
    elif gif_locked and m.animation:
        should_delete = True
    elif sticker_locked and m.sticker:
        should_delete = True

    if should_delete:
        try:
            await m.delete()
        except Exception:
            pass
        return True
    return False


# ---- لوکیشن ----
async def lock_location(u, c): await _toggle(u, c, "location_locked", "1", f"{EMOJI['lock']} قفل لوکیشن فعال شد.")
async def unlock_location(u, c): await _toggle(u, c, "location_locked", "0", f"{EMOJI['unlock']} قفل لوکیشن برداشته شد.")


async def enforce_location_lock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    if not update.message or not update.message.location or chat.type not in ("group", "supergroup"):
        return False
    if not get_bool_setting(chat.id, "location_locked", False):
        return False
    if await can_run_admin_command(update, context):
        return False
    try:
        await update.message.delete()
    except Exception:
        pass
    return True


# ---- مخاطب (Contact) ----
async def lock_contact(u, c): await _toggle(u, c, "contact_locked", "1", f"{EMOJI['lock']} قفل مخاطب فعال شد.")
async def unlock_contact(u, c): await _toggle(u, c, "contact_locked", "0", f"{EMOJI['unlock']} قفل مخاطب برداشته شد.")


async def enforce_contact_lock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    if not update.message or not update.message.contact or chat.type not in ("group", "supergroup"):
        return False
    if not get_bool_setting(chat.id, "contact_locked", False):
        return False
    if await can_run_admin_command(update, context):
        return False
    try:
        await update.message.delete()
    except Exception:
        pass
    return True


# ---- هشتگ ----
async def lock_hashtag(u, c): await _toggle(u, c, "hashtag_locked", "1", f"{EMOJI['lock']} قفل هشتگ فعال شد.")
async def unlock_hashtag(u, c): await _toggle(u, c, "hashtag_locked", "0", f"{EMOJI['unlock']} قفل هشتگ برداشته شد.")


# ---- آیدی (منشن @) ----
async def lock_id(u, c): await _toggle(u, c, "id_locked", "1", f"{EMOJI['lock']} قفل آیدی فعال شد.")
async def unlock_id(u, c): await _toggle(u, c, "id_locked", "0", f"{EMOJI['unlock']} قفل آیدی برداشته شد.")


# ---- ریپلای ----
async def lock_reply(u, c): await _toggle(u, c, "reply_locked", "1", f"{EMOJI['lock']} قفل ریپلای فعال شد.")
async def unlock_reply(u, c): await _toggle(u, c, "reply_locked", "0", f"{EMOJI['unlock']} قفل ریپلای برداشته شد.")


# ---- پیام (بستن کامل چت متنی، حتی برای ادمین‌ها به‌جز مالک) ----
async def lock_message(u, c):
    if not await can_run_admin_command(u, c):
        await u.message.reply_text(tone.deny_text(u.effective_chat.id))
        return
    set_setting(u.effective_chat.id, "message_locked", "1")
    await u.message.reply_text(f"{EMOJI['lock']} چت متنی گروه کاملاً بسته شد (حتی برای ادمین‌ها).")


async def unlock_message(u, c):
    if not await can_run_admin_command(u, c):
        await u.message.reply_text(tone.deny_text(u.effective_chat.id))
        return
    set_setting(u.effective_chat.id, "message_locked", "0")
    await u.message.reply_text(f"{EMOJI['unlock']} چت متنی گروه باز شد.")


# ---- محدودیت طول پیام ----
async def set_char_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        await update.message.reply_text(tone.deny_text(update.effective_chat.id))
        return
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) < 3:
        await update.message.reply_text(f"{EMOJI['warn']} فرمت درست: «قفل کاراکتر 200» یا «قفل کاراکتر خاموش»")
        return
    arg = parts[2]
    if arg in ("خاموش", "0"):
        set_setting(update.effective_chat.id, "char_limit", "0")
        await update.message.reply_text(f"{EMOJI['unlock']} محدودیت طول پیام غیرفعال شد.")
        return
    if not arg.isdigit():
        await update.message.reply_text(f"{EMOJI['warn']} باید یه عدد بدی، مثلاً «قفل کاراکتر 200»")
        return
    set_setting(update.effective_chat.id, "char_limit", arg)
    await update.message.reply_text(f"{EMOJI['lock']} از الان پیام‌های بیشتر از {arg} کاراکتر حذف می‌شن.")


# ================= بررسی‌های متنی (هشتگ/آیدی/ریپلای/پیام‌کامل/طول) =================
async def enforce_text_content_locks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """این تابع فقط برای پیام‌های متنی صداست، بعد از رد شدن از قفل گروه و عضویت اجباری."""
    message = update.message
    chat = update.effective_chat
    if not message or not message.text or chat.type not in ("group", "supergroup"):
        return False

    is_privileged = await can_run_admin_command(update, context)

    # قفل پیام کامل: حتی ادمین‌ها هم نمی‌تونن (فقط بررسی جدا در main.py قبل از این چک میشه)
    if get_bool_setting(chat.id, "message_locked", False) and not is_privileged:
        try:
            await message.delete()
        except Exception:
            pass
        return True

    if is_privileged:
        return False  # بقیه‌ی قفل‌های زیر شامل ادمین/مالک نمی‌شن

    if get_bool_setting(chat.id, "hashtag_locked", False) and HASHTAG_PATTERN.search(message.text):
        await _delete_and_flag(message)
        return True

    if get_bool_setting(chat.id, "id_locked", False) and MENTION_PATTERN.search(message.text):
        await _delete_and_flag(message)
        return True

    if get_bool_setting(chat.id, "reply_locked", False) and message.reply_to_message:
        await _delete_and_flag(message)
        return True

    limit = get_setting(chat.id, "char_limit", "0")
    if limit and limit.isdigit() and int(limit) > 0 and len(message.text) > int(limit):
        await _delete_and_flag(message)
        return True

    return False


async def _delete_and_flag(message):
    try:
        await message.delete()
    except Exception:
        pass
