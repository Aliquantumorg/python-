import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, ContextTypes, MessageHandler, CallbackQueryHandler, ChatMemberHandler,
    ApplicationHandlerStop, filters,
)

from config import BOT_TOKEN, BALE_API_BASE, BALE_FILE_BASE, EMOJI, BOT_NAME, BOT_INTRO, OWNER_IDS
from database import init_db, register_chat, remove_chat, record_known_member, get_command_alias
import admin, filters as word_filters, force_join, games, panel, welcome
import wordfilter, tagall, timeinfo, forwardlock, content_locks, muteall, tone
import settings_view, admincall, purge_bot, reminder, publicaccess, recent_messages
import group_link, gifmaker, security
from antispam import check_flood
from registry import COMMANDS, PREFIX_COMMANDS
from permissions import can_run_admin_command

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gapbot")


def _build_help_text() -> str:
    sections = {
        "public": ("🎮 *عمومی و بازی‌ها:*", []),
        "admin": ("⚖️ *فقط ادمین گروه یا مالک بات:*", []),
    }
    for key, (trigger, _handler, scope, desc) in COMMANDS.items():
        if scope in sections:
            sections[scope][1].append(f"«{trigger}» » {desc}")

    lines = []
    lines.append(sections["public"][0])
    lines.extend(sections["public"][1])
    lines.append("")
    lines.append(sections["admin"][0])
    lines.extend(sections["admin"][1])
    lines.append("")
    lines.append("🔧 *دستورات آرگومان‌دار:*")
    for prefix, desc in PREFIX_COMMANDS.items():
        lines.append(f"«{prefix} ...» » {desc}")
    lines.append("")
    lines.append(f"🎬 *فقط در پیوی:* «ساخت گیف» » ساخت گیف سفارشی از عکس/فیلم/گیف با متن دلخواه\n")
    lines.append(f"🛠 *فقط مالک بات، فقط در پیوی:* «پنل» » پنل مدیریت کامل و ویرایش نام دستورات\n")
    lines.append(f"💡 {BOT_INTRO}")
    return "\n".join(lines)


HELP_TEXT = _build_help_text()
_OWNER_IDS_CACHE = set(OWNER_IDS)


def _normalize_name(text: str) -> str:
    """نیم‌فاصله و فاصله‌ی اضافه رو یکسان می‌کنه تا «گروه یار» و «گروه‌یار» هر دو تشخیص داده بشن"""
    return text.replace("\u200c", " ").replace("  ", " ").strip()


_BOT_NAME_NORMALIZED = _normalize_name(BOT_NAME)


def _resolve_command(chat_id: int, text: str):
    """متن پیام رو به یه دستور از رجیستری تبدیل می‌کنه (با در نظر گرفتن نام سفارشی)"""
    for key, (default_trigger, handler, scope, _desc) in COMMANDS.items():
        current_trigger = get_command_alias(chat_id, key) or default_trigger
        if text == current_trigger:
            return key, handler, scope
    return None


async def master_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await welcome.track_chat(update, context)
    await recent_messages.track_message(update, context)

    chat = update.effective_chat
    user = update.effective_user

    if chat and chat.type in ("group", "supergroup") and user:
        record_known_member(chat.id, user.id, user.first_name, user.username)

    # ۱) ورودی‌های پی‌درپیِ مالک در پنل (پیوی)
    if await panel.handle_owner_text_or_photo(update, context):
        return

    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # ۱.۵) اگه کاربر الان بلاکه (به‌خاطر تخلف قبلی)، به‌طور کامل نادیده گرفته می‌شه
    if user and user.id not in _OWNER_IDS_CACHE and security.is_blocked(user.id):
        return

    # ۱.۶) پیوی: محدودیت تعداد دفعاتِ زدن «شروع» (ضد اسپم پیوی)
    if chat and chat.type == "private" and user and user.id not in _OWNER_IDS_CACHE:
        if _normalize_name(text) == "شروع":
            if not security.register_pv_start(user.id):
                return

    # ۱.۷) پیوی: اگه پیوی بات و مالک نیست، اول باید عضویت اجباری رو رد کنه
    if chat and chat.type == "private" and user and user.id not in _OWNER_IDS_CACHE:
        if await force_join.enforce_pv_gate(update, context):
            return

    # ۱.۸) پیوی: جریان ساخت گیف (متنِ در انتظار)
    if chat and chat.type == "private":
        if await gifmaker.handle_gif_text(update, context):
            return

    # ۲) قفل‌های سخت‌گیرانه‌تر (پیام کامل / هشتگ / آیدی / ریپلای / طول پیام)
    if await content_locks.enforce_text_content_locks(update, context):
        return

    # ۳) قفل گروه معمولی (فقط غیرادمین‌ها)
    if await admin.enforce_lock(update, context):
        return

    # ۴) عضویت اجباری داخل گروه (ادمین‌ها/مالک معافن)
    if await force_join.enforce_membership(update, context):
        return

    # ۵) آنتی‌فلود (شامل گیف هم می‌شه، چون از هندلر مدیا هم صدا زده می‌شه)
    if await check_flood(update, context):
        return

    # ۶) افزودن فیلتر سفارشی
    if text.startswith("فیلتر ") and update.message.reply_to_message:
        await wordfilter.add_filter_command(update, context)
        return

    # ۷) دستورات آرگومان‌دار (پیشوندی)
    if text.startswith("قفل کاراکتر "):
        await content_locks.set_char_limit(update, context)
        return
    if text.startswith("بی‌صدا همه") or text.startswith("بیصدا همه"):
        await muteall.mute_all(update, context)
        return
    if text.startswith("یادآوری "):
        await reminder.set_reminder(update, context)
        return
    if text.startswith("تنظیم خوش آمد "):
        await publicaccess.set_welcome_text(update, context)
        return
    if text.startswith("تغییر لحن به "):
        await tone.change_tone_command(update, context)
        return

    # ۸) دستورات ساده‌ی متنی
    if _normalize_name(text) == _BOT_NAME_NORMALIZED:
        await update.message.reply_text(tone.tt(chat.id, "intro"))
        return

    if text == "آمار من":
        from database import user_message_count
        count = user_message_count(chat.id, user.id)
        await update.message.reply_text(f"{EMOJI['stats']} تعداد پیام‌های شما در این گروه: {count}")
        return

    if text == "کیف پول":
        from database import get_coins
        balance = get_coins(user.id)
        await update.message.reply_text(f"{EMOJI['coin']} موجودی سکه‌ی شما: {balance}")
        return

    if text in ("راهنما", "شروع"):
        if chat.type != "private" and not tone.has_tone_been_set(chat.id):
            await tone.show_tone_picker(update, context)
            return
        if chat.type == "private":
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎬 ساخت گیف", callback_data="startgif")]])
            await update.message.reply_text(
                tone.tt(chat.id, "help_intro") + "\n\n" + HELP_TEXT, parse_mode="Markdown", reply_markup=keyboard
            )
            return
        await update.message.reply_text(
            tone.tt(chat.id, "help_intro") + "\n\n" + HELP_TEXT, parse_mode="Markdown"
        )
        return

    if text == "پنل":
        await panel.open_panel(update, context)
        return

    if text in ("لینک", "لینک گروه"):
        await group_link.send_group_link(update, context)
        return

    if chat.type == "private" and text == "ساخت گیف":
        await gifmaker.start_gif_maker(update, context)
        return

    # ۹) دستورات رجیستری (با در نظر گرفتن نام سفارشی هر گروه)
    if chat and chat.type in ("group", "supergroup"):
        resolved = _resolve_command(chat.id, text)
        if resolved:
            key, handler, scope = resolved
            if scope == "public" and publicaccess.is_public_access_blocked(chat.id):
                if not await can_run_admin_command(update, context):
                    await update.message.reply_text(f"{EMOJI['cross']} فعلاً فقط ادمین‌ها/مالک به این امکانات دسترسی دارن.")
                    return
            await handler(update, context)
            return

    # ۱۰) پاسخ خودکار فیلتر سفارشی
    if await wordfilter.handle_custom_filter_trigger(update, context):
        return

    # ۱۱) فراخوان ادمین
    if await admincall.handle_admin_call(update, context):
        return

    # ۱۲) ورودی بازی‌های در حال اجرا
    if await games.handle_guess_text(update, context):
        return
    if await games.handle_hangman_text(update, context):
        return

    # ۱۳) فیلتر کلمات/لینک/اسپم
    await word_filters.moderate_message(update, context)

    # ۱۴) ریپلای به خودِ بات که هیچ‌کدوم از موارد بالا مصرفش نکرد
    if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
        await update.message.reply_text(tone.tt(chat.id, "intro"))


async def handle_non_text_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسانه، لوکیشن و مخاطب - چون در filters.TEXT نمی‌گنجن، جدا بررسی می‌شن"""
    await recent_messages.track_message(update, context)

    # مهم: اول بررسی کن آیا این عکس، بنر تبلیغاتیِ در انتظار مالک بات (در پیوی) هست
    if await panel.handle_owner_text_or_photo(update, context):
        return

    chat = update.effective_chat

    # پیوی: رسانه‌ی مربوط به ساخت گیف
    if chat and chat.type == "private":
        await gifmaker.handle_gif_media(update, context)
        return

    if not chat or chat.type not in ("group", "supergroup"):
        return

    user = update.effective_user
    if user:
        record_known_member(chat.id, user.id, user.first_name, user.username)

    # آنتی‌فلود باید گیف/عکس/استیکر و غیره رو هم بشمره، نه فقط پیام متنی
    if await check_flood(update, context):
        return

    if await content_locks.enforce_media_lock(update, context):
        return
    if await content_locks.enforce_location_lock(update, context):
        return
    if await content_locks.enforce_contact_lock(update, context):
        return


async def handle_forward_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await forwardlock.enforce_forward_lock(update, context)


async def security_callback_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    قبل از هر کال‌بک دیگه‌ای اجرا می‌شه.
    - اگه کاربر از قبل بلاکه (به هر دلیلی)، کلاً بی‌پاسخ می‌مونه.
    - اگه روی همین دکمه‌ی خاص (همون callback_data) چندبار پشت‌سرهم بزنه، بلاک می‌شه.
    """
    query = update.callback_query
    user_id = query.from_user.id
    if user_id in _OWNER_IDS_CACHE:
        return

    if security.is_blocked(user_id):
        raise ApplicationHandlerStop

    if not security.register_button_press(user_id, query.data):
        try:
            await query.answer()
        except Exception:
            pass
        raise ApplicationHandlerStop


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, ApplicationHandlerStop):
        return
    log.warning(f"⚠️ یک خطای گذرا رخ داد و نادیده گرفته شد: {context.error}")


async def track_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    chat = result.chat
    new_status = result.new_chat_member.status
    if new_status in ("member", "administrator"):
        register_chat(chat.id, chat.title or "بدون‌نام", chat.type)
    elif new_status in ("left", "kicked"):
        remove_chat(chat.id)


def build_application() -> Application:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .base_url(BALE_API_BASE)
        .base_file_url(BALE_FILE_BASE)
        .concurrent_updates(4)  # چند آپدیت رو هم‌زمان پردازش کن؛ یه کاربر کند بقیه رو بلاک نکنه
        .connect_timeout(15)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(15)
        .build()
    )

    # اولویت بالا: قفل فوروارد قبل از هر پردازش دیگه‌ای
    app.add_handler(MessageHandler(filters.ALL, handle_forward_guard), group=-1)
    # اولویت بالاتر از همه برای کال‌بک‌ها: چک امنیتی ضد سوءاستفاده
    app.add_handler(CallbackQueryHandler(security_callback_guard, pattern=None), group=-2)

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome.welcome_new_members))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, welcome.farewell_member))
    app.add_handler(MessageHandler(filters.TEXT, master_text_handler))
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.VOICE
        | filters.VIDEO_NOTE | filters.Sticker.ALL | filters.LOCATION | filters.CONTACT | filters.Document.ALL,
        handle_non_text_content,
    ))

    app.add_handler(CallbackQueryHandler(games.tic_join_callback, pattern=r"^ticjoin:"))
    app.add_handler(CallbackQueryHandler(games.tic_tac_toe_callback, pattern=r"^tic:"))
    app.add_handler(CallbackQueryHandler(games.rps_join_callback, pattern=r"^rpsjoin:"))
    app.add_handler(CallbackQueryHandler(games.rps_choice_callback, pattern=r"^rpschoice:"))
    app.add_handler(CallbackQueryHandler(force_join.check_join_callback, pattern=r"^checkjoin:"))
    app.add_handler(CallbackQueryHandler(force_join.check_join_pv_callback, pattern=r"^checkjoinpv:"))
    app.add_handler(CallbackQueryHandler(force_join.exempt_callback, pattern=r"^fjexempt:"))
    app.add_handler(CallbackQueryHandler(welcome.rules_callback, pattern=r"^rules$"))
    app.add_handler(CallbackQueryHandler(panel.panel_callback, pattern=r"^panel:"))
    app.add_handler(CallbackQueryHandler(tone.tone_picker_callback, pattern=r"^tone:"))
    app.add_handler(CallbackQueryHandler(gifmaker.position_callback, pattern=r"^gifpos:"))
    app.add_handler(CallbackQueryHandler(gifmaker.font_callback, pattern=r"^giffont:"))
    app.add_handler(CallbackQueryHandler(gifmaker.size_callback, pattern=r"^gifsize:"))
    app.add_handler(CallbackQueryHandler(gifmaker.outline_choice_callback, pattern=r"^gifoutline:"))
    app.add_handler(CallbackQueryHandler(gifmaker.outline_color_callback, pattern=r"^gifoutlinecolor:"))
    app.add_handler(CallbackQueryHandler(gifmaker.color_callback, pattern=r"^gifcolor:"))
    app.add_handler(CallbackQueryHandler(gifmaker.start_gif_maker_from_callback, pattern=r"^startgif$"))

    app.add_handler(ChatMemberHandler(track_membership, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_error_handler(global_error_handler)

    return app


def main():
    init_db()
    app = build_application()
    log.info(f"🤝 {BOT_NAME} با موفقیت استارت خورد و در حال گوش دادن به پیام‌هاست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
