from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

from config import EMOJI, BOT_NAME
from database import list_required_channels, get_bool_setting, is_force_join_exempt, add_force_join_exempt
from permissions import can_run_admin_command
import tone

MEMBER_STATUSES = (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


async def _is_member_of(context: ContextTypes.DEFAULT_TYPE, channel: str, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(channel, user_id)
        return member.status in MEMBER_STATUSES
    except Exception:
        # اگه بات عضو کانال نباشه یا کانال در دسترس نباشه، برای امنیت فرض می‌کنیم عضو نیست
        return False


async def _missing_channels(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> list:
    channels = list_required_channels()
    missing = []
    for ch in channels:
        if not await _is_member_of(context, ch, user_id):
            missing.append(ch)
    return missing


def _join_keyboard(missing: list, user_id: int, callback_prefix: str = "checkjoin", chat_id: int = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{EMOJI['channel']} عضویت در {ch}", url=f"https://ble.ir/{ch.lstrip('@')}")]
        for ch in missing
    ]
    rows.append([InlineKeyboardButton(f"{EMOJI['check']} عضو شدم، بررسی کن", callback_data=f"{callback_prefix}:{user_id}")])
    # دکمه‌ی معافیت فقط برای پیام‌های داخل گروه معنی داره (ادمین/مالک می‌تونن بزنن)
    if chat_id is not None:
        rows.append([InlineKeyboardButton("🛡 معاف کردن این کاربر", callback_data=f"fjexempt:{chat_id}:{user_id}")])
    return InlineKeyboardMarkup(rows)


async def enforce_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    خروجی True یعنی پیام بلاک شد (کاربر عضو نبود و باید متوقف بشه).
    فقط داخل گروه/سوپرگروه اجرا میشه، نه در پیوی.
    ادمین‌های همون گروه، مالک بات، و کاربرانِ دستی معاف‌شده از این قانون معافن.
    """
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        return False

    if get_bool_setting(chat.id, "force_join_disabled", False):
        return False

    # ادمین‌های گروه و مالک بات از عضویت اجباری معافن
    if await can_run_admin_command(update, context):
        return False

    # کاربری که قبلاً دستی معاف شده
    if is_force_join_exempt(chat.id, user.id):
        return False

    channels = list_required_channels()
    if not channels:
        return False  # هیچ کانالی تنظیم نشده، عضویت اجباری غیرفعاله

    missing = await _missing_channels(context, user.id)
    if not missing:
        return False  # عضو همه‌جا هست ✅

    try:
        await update.message.delete()
    except Exception:
        pass

    name = user.first_name or "کاربر عزیز"
    await context.bot.send_message(
        chat.id,
        tone.tt(chat.id, "force_join_group", name=name),
        reply_markup=_join_keyboard(missing, user.id, "checkjoin", chat_id=chat.id),
    )
    return True


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, target_user_id = query.data.split(":")
    target_user_id = int(target_user_id)

    if query.from_user.id != target_user_id:
        await query.answer("این دکمه برای شما نیست 🙂", show_alert=True)
        return

    missing = await _missing_channels(context, target_user_id)
    if not missing:
        await query.answer(f"{EMOJI['welcome']} عضویتت تأیید شد، حالا می‌تونی پیام بدی!", show_alert=True)
        try:
            await query.message.delete()
        except Exception:
            pass
    else:
        await query.answer(f"{EMOJI['cross']} هنوز عضو همه‌ی کانال‌ها نشدی!", show_alert=True)


async def exempt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دکمه‌ی «معاف کردن این کاربر» - فقط ادمین همون گروه یا مالک بات می‌تونه بزنه"""
    query = update.callback_query
    _, chat_id_str, target_user_id_str = query.data.split(":")
    chat_id, target_user_id = int(chat_id_str), int(target_user_id_str)

    if not await can_run_admin_command(update, context):
        await query.answer(f"{EMOJI['cross']} فقط ادمین‌های گروه یا مالک بات می‌تونن این کارو بکنن.", show_alert=True)
        return

    add_force_join_exempt(chat_id, target_user_id)
    await query.answer(f"{EMOJI['check']} این کاربر از عضویت اجباری معاف شد.", show_alert=True)
    try:
        await query.message.delete()
    except Exception:
        pass


# ================= نسخه‌ی پیوی (وقتی کسی استارت میزنه) =================
async def enforce_pv_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    وقتی کسی توی پیوی بات پیام میده، اگه عضو کانال‌های اجباری نباشه، پیام عضویت نشونش میده.
    خروجی True یعنی باید متوقف بشه و ادامه‌ی پردازش انجام نشه.
    """
    user = update.effective_user
    channels = list_required_channels()
    if not channels:
        return False

    missing = await _missing_channels(context, user.id)
    if not missing:
        return False

    name = user.first_name or "دوست عزیز"
    await update.message.reply_text(
        tone.tt(update.effective_chat.id, "force_join_pv", name=name),
        reply_markup=_join_keyboard(missing, user.id, "checkjoinpv"),  # پیوی نیازی به دکمه‌ی معافیت نداره
    )
    return True


async def check_join_pv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بعد از تأیید عضویت در پیوی، راهنمای افزودن بات به گروه خودشون رو نشون میده"""
    query = update.callback_query
    _, target_user_id = query.data.split(":")
    target_user_id = int(target_user_id)

    if query.from_user.id != target_user_id:
        await query.answer("این دکمه برای شما نیست 🙂", show_alert=True)
        return

    missing = await _missing_channels(context, target_user_id)
    if missing:
        await query.answer(f"{EMOJI['cross']} هنوز عضو همه‌ی کانال‌ها نشدی!", show_alert=True)
        return

    await query.answer(f"{EMOJI['welcome']} عضویتت تأیید شد!", show_alert=True)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎬 ساخت گیف", callback_data="startgif")]])
    await query.edit_message_text(tone.tt(query.message.chat.id, "pv_join_success"), reply_markup=keyboard)
