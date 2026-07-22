from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

from config import EMOJI
from database import log_action, set_setting, get_bool_setting
from permissions import can_run_admin_command
import tone


async def _get_target_user(update: Update):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None


async def _deny(update: Update):
    await update.message.reply_text(tone.deny_text(update.effective_chat.id))


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        return await _deny(update)
    target = await _get_target_user(update)
    if not target:
        await update.message.reply_text(tone.reply_required_text(update.effective_chat.id))
        return
    chat_id = update.effective_chat.id
    await context.bot.ban_chat_member(chat_id, target.id)
    log_action(chat_id, update.effective_user.id, "ban", target.id)
    await update.message.reply_text(
        tone.tt(chat_id, "ban_done", name=target.first_name or "کاربر"),
    )


async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        return await _deny(update)
    target = await _get_target_user(update)
    if not target:
        await update.message.reply_text(tone.reply_required_text(update.effective_chat.id))
        return
    chat_id = update.effective_chat.id
    await context.bot.ban_chat_member(chat_id, target.id)
    await context.bot.unban_chat_member(chat_id, target.id)
    log_action(chat_id, update.effective_user.id, "kick", target.id)
    await update.message.reply_text(
        tone.tt(chat_id, "kick_done", name=target.first_name or "کاربر"),
    )


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        return await _deny(update)
    target = await _get_target_user(update)
    if not target:
        await update.message.reply_text(tone.reply_required_text(update.effective_chat.id))
        return
    chat_id = update.effective_chat.id
    await context.bot.restrict_chat_member(
        chat_id, target.id, permissions=ChatPermissions(can_send_messages=False)
    )
    log_action(chat_id, update.effective_user.id, "mute", target.id)
    await update.message.reply_text(
        tone.tt(chat_id, "mute_done", name=target.first_name or "کاربر"),
    )


async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        return await _deny(update)
    target = await _get_target_user(update)
    if not target:
        await update.message.reply_text(tone.reply_required_text(update.effective_chat.id))
        return
    chat_id = update.effective_chat.id
    await context.bot.restrict_chat_member(
        chat_id,
        target.id,
        permissions=ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_send_polls=True),
    )
    log_action(chat_id, update.effective_user.id, "unmute", target.id)
    await update.message.reply_text(
        tone.tt(chat_id, "unmute_done", name=target.first_name or "کاربر"),
    )


async def lock_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        return await _deny(update)
    chat_id = update.effective_chat.id
    set_setting(chat_id, "locked", "1")
    log_action(chat_id, update.effective_user.id, "lock")
    await update.message.reply_text(f"{EMOJI['lock']} گروه قفل شد؛ فقط ادمین‌ها می‌تونن پیام بدن.")


async def unlock_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        return await _deny(update)
    chat_id = update.effective_chat.id
    set_setting(chat_id, "locked", "0")
    log_action(chat_id, update.effective_user.id, "unlock")
    await update.message.reply_text(f"{EMOJI['unlock']} قفل گروه برداشته شد، همه می‌تونن پیام بدن.")


async def enforce_lock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگه گروه قفله و فرستنده ادمین/مالک نیست، پیامش حذف میشه"""
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return False
    if not get_bool_setting(chat.id, "locked", False):
        return False
    if await can_run_admin_command(update, context):
        return False
    try:
        await update.message.delete()
    except Exception:
        pass
    return True


async def purge_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاکسازی: با ریپلای روی یک پیام و نوشتن «پاکسازی»، از اون پیام تا الان حذف میشه"""
    if not await can_run_admin_command(update, context):
        return await _deny(update)
    if not update.message.reply_to_message:
        await update.message.reply_text(f"{EMOJI['warn']} روی پیامی که می‌خوای پاکسازی از اونجا شروع بشه ریپلای کن.")
        return
    chat_id = update.effective_chat.id
    start_id = update.message.reply_to_message.message_id
    end_id = update.message.message_id
    deleted = 0
    for msg_id in range(start_id, end_id + 1):
        try:
            await context.bot.delete_message(chat_id, msg_id)
            deleted += 1
        except Exception:
            pass
    log_action(chat_id, update.effective_user.id, "purge")
    await context.bot.send_message(chat_id, tone.tt(chat_id, "purge_done", count=deleted))


async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        return await _deny(update)
    if not update.message.reply_to_message:
        await update.message.reply_text(f"{EMOJI['warn']} روی پیامی که می‌خوای سنجاق کنی ریپلای بزن.")
        return
    try:
        await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        await update.message.reply_text(f"📌 پیام سنجاق شد {EMOJI['check']}")
    except Exception:
        await update.message.reply_text(f"{EMOJI['cross']} نتونستم پیام رو سنجاق کنم.")


async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_run_admin_command(update, context):
        return await _deny(update)
    if not update.message.reply_to_message:
        await update.message.reply_text(f"{EMOJI['warn']} روی پیام سنجاق‌شده ریپلای بزن و بنویس «حذف سنجاق».")
        return
    try:
        await context.bot.unpin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        await update.message.reply_text(f"📌 سنجاق پیام برداشته شد {EMOJI['check']}")
    except Exception:
        await update.message.reply_text(f"{EMOJI['cross']} نتونستم سنجاق رو بردارم.")


async def show_identity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """با ریپلای روی پیام یه نفر، اطلاعاتش رو نشون میده"""
    from database import user_message_count
    target = await _get_target_user(update)
    if not target:
        target = update.effective_user
    chat_id = update.effective_chat.id
    count = user_message_count(chat_id, target.id)
    await update.message.reply_text(
        f"🆔 هویت کاربر:\n"
        f"👤 نام: {target.first_name or '-'}\n"
        f"🔢 آیدی عددی: {target.id}\n"
        f"🔗 یوزرنیم: @{target.username}" if target.username else f"🔗 یوزرنیم: ندارد",
    )
    await update.message.reply_text(f"💬 تعداد پیام‌های ثبت‌شده در این گروه: {count}")
