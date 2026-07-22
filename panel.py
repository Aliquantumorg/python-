from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import OWNER_IDS, EMOJI
from database import (
    all_known_chats, list_required_channels, add_required_channel, remove_required_channel,
    list_bad_words, add_bad_word, remove_bad_word, set_vip, recent_actions,
    get_command_alias, set_command_alias, reset_command_alias,
)

# وضعیت موقت مکالمه‌ی مالک با پنل (منتظر چه ورودی‌ای هست)
owner_state = {}
# بنرهایی که عکس/کپشنشون گرفته شده ولی هنوز تصمیم فوری/زمان‌بندی گرفته نشده
pending_banner = {}


async def _broadcast_banner(context, file_id, caption):
    chats = all_known_chats()
    sent = failed = 0
    for chat_id, _, _ in chats:
        try:
            await context.bot.send_photo(chat_id, file_id, caption=caption)
            sent += 1
        except Exception:
            failed += 1
    return sent, failed


async def _send_scheduled_banner_job(context: ContextTypes.DEFAULT_TYPE):
    owner_id, file_id, caption = context.job.data
    sent, failed = await _broadcast_banner(context, file_id, caption)
    await context.bot.send_message(
        owner_id,
        f"⏰ بنر زمان‌بندی‌شده ارسال شد!\n{EMOJI['check']} موفق: {sent} | {EMOJI['cross']} ناموفق: {failed}",
    )


def _is_owner_private(update: Update) -> bool:
    return update.effective_chat.type == "private" and update.effective_user.id in OWNER_IDS


def _main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{EMOJI['broadcast']} ارسال همگانی", callback_data="panel:broadcast")],
        [InlineKeyboardButton(f"{EMOJI['banner']} ارسال بنر تبلیغاتی (فوری/زمان‌دار)", callback_data="panel:banner")],
        [InlineKeyboardButton(f"{EMOJI['channel']} مدیریت کانال‌های عضویت اجباری", callback_data="panel:channels")],
        [InlineKeyboardButton("🚫 مدیریت کلمات ممنوعه", callback_data="panel:badwords")],
        [InlineKeyboardButton(f"{EMOJI['vip']} اعطای VIP", callback_data="panel:vip")],
        [InlineKeyboardButton(f"{EMOJI['stats']} آمار کلی بات", callback_data="panel:stats")],
        [InlineKeyboardButton("🗒 لاگ اخیر اکشن‌ها", callback_data="panel:log")],
        [InlineKeyboardButton("✏️ ویرایش دستورات یک گروه", callback_data="panel:cmdedit")],
    ])


def _back_button(target="panel:home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"{EMOJI['back']} بازگشت", callback_data=target)]])


async def open_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_owner_private(update):
        await update.message.reply_text(f"{EMOJI['cross']} این بخش فقط برای مدیر اصلی بات و فقط در پیوی قابل استفاده‌ست.")
        return
    await update.message.reply_text(f"{EMOJI['panel']} پنل مدیریت بات\nیکی از گزینه‌ها رو انتخاب کن:", reply_markup=_main_menu())


async def _show_channels(query):
    channels = list_required_channels()
    text = f"{EMOJI['channel']} کانال‌های عضویت اجباری فعلی:\n\n"
    text += "\n".join(f"• {c}" for c in channels) if channels else "هیچ کانالی تنظیم نشده."
    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['add']} افزودن کانال جدید", callback_data="panel:add_channel")],
    ]
    if channels:
        keyboard.append([InlineKeyboardButton(f"{EMOJI['remove']} حذف یک کانال", callback_data="panel:remove_channel")])
    keyboard.append([InlineKeyboardButton(f"{EMOJI['back']} بازگشت", callback_data="panel:home")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def _show_badwords(query):
    words = list_bad_words()
    text = "🚫 کلمات ممنوعه‌ی فعلی:\n\n" + ("\n".join(f"• {w}" for w in words) if words else "لیست خالیه.")
    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['add']} افزودن کلمه", callback_data="panel:add_badword")],
        [InlineKeyboardButton(f"{EMOJI['remove']} حذف کلمه", callback_data="panel:remove_badword")],
        [InlineKeyboardButton(f"{EMOJI['back']} بازگشت", callback_data="panel:home")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def _show_group_picker(query):
    chats = [c for c in all_known_chats() if c[2] in ("group", "supergroup")]
    if not chats:
        await query.edit_message_text("هنوز بات توی هیچ گروهی عضو نیست.", reply_markup=_back_button())
        return
    rows = [[InlineKeyboardButton(title or str(cid), callback_data=f"panel:editcmds:{cid}")] for cid, title, _ in chats]
    rows.append([InlineKeyboardButton(f"{EMOJI['back']} بازگشت", callback_data="panel:home")])
    await query.edit_message_text("کدوم گروه رو می‌خوای دستوراتش رو ویرایش کنی؟", reply_markup=InlineKeyboardMarkup(rows))


async def _show_command_list(query, chat_id):
    from registry import COMMANDS
    rows = []
    for key, (default_trigger, _handler, _scope, desc) in COMMANDS.items():
        current = get_command_alias(chat_id, key) or default_trigger
        label = f"«{current}» — {desc}"
        rows.append([InlineKeyboardButton(label, callback_data=f"panel:renamecmd:{chat_id}:{key}")])
    rows.append([InlineKeyboardButton(f"{EMOJI['back']} بازگشت", callback_data="panel:cmdedit")])
    # چون ممکنه لیست خیلی طولانی بشه، فقط پیام رو می‌فرستیم و بله خودش اسکرول می‌کنه
    await query.edit_message_text(
        "روی هر دستور بزن تا کلمه‌ی فعال‌سازیش رو عوض کنی:", reply_markup=InlineKeyboardMarkup(rows)
    )


async def panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in OWNER_IDS:
        await query.answer(f"{EMOJI['cross']} دسترسی نداری.", show_alert=True)
        return

    parts = query.data.split(":")
    action = parts[1]
    await query.answer()  # همیشه اول جواب کوئری رو می‌دیم که منقضی نشه

    if action == "home":
        await query.edit_message_text(f"{EMOJI['panel']} پنل مدیریت بات\nیکی از گزینه‌ها رو انتخاب کن:", reply_markup=_main_menu())

    elif action == "cmdedit":
        await _show_group_picker(query)

    elif action == "editcmds":
        chat_id = int(parts[2])
        await _show_command_list(query, chat_id)

    elif action == "renamecmd":
        chat_id, command_key = int(parts[2]), parts[3]
        owner_state[query.from_user.id] = f"await_rename_new:{chat_id}:{command_key}"
        from registry import COMMANDS
        default_trigger = COMMANDS[command_key][0]
        current = get_command_alias(chat_id, command_key) or default_trigger
        await query.edit_message_text(
            f"کلمه‌ی فعلی: «{current}»\nکلمه‌ی جدید رو بفرست (یا برای بازگشت به پیش‌فرض، دقیقاً بنویس «{default_trigger}»):",
            reply_markup=_back_button(f"panel:editcmds:{chat_id}"),
        )

    elif action == "broadcast":
        owner_state[query.from_user.id] = "await_broadcast"
        await query.edit_message_text(
            f"{EMOJI['broadcast']} متن پیام همگانی رو بفرست تا برای همه‌ی گروه‌ها/کانال‌ها ارسال بشه:",
            reply_markup=_back_button(),
        )

    elif action == "banner":
        owner_state[query.from_user.id] = "await_banner"
        await query.edit_message_text(
            f"{EMOJI['banner']} عکس بنر تبلیغاتی رو همراه با کپشن (متن زیر عکس) بفرست:",
            reply_markup=_back_button(),
        )

    elif action == "banner_now":
        user_id = query.from_user.id
        pending = pending_banner.pop(user_id, None)
        owner_state.pop(user_id, None)
        if not pending:
            await query.edit_message_text(f"{EMOJI['cross']} بنری در انتظار پیدا نشد، دوباره از اول امتحان کن.", reply_markup=_back_button())
            return
        file_id, caption = pending
        sent, failed = await _broadcast_banner(context, file_id, caption)
        await query.edit_message_text(
            f"{EMOJI['check']} بنر فوراً ارسال شد به {sent} چت | {EMOJI['cross']} ناموفق: {failed}",
            reply_markup=_back_button(),
        )

    elif action == "banner_schedule":
        owner_state[query.from_user.id] = "await_banner_minutes"
        await query.edit_message_text(
            "⏰ چند دقیقه‌ی دیگه ارسال بشه؟ فقط عدد بفرست (مثلاً 60 برای یک ساعت دیگه):",
            reply_markup=_back_button(),
        )

    elif action == "banner_cancel":
        pending_banner.pop(query.from_user.id, None)
        owner_state.pop(query.from_user.id, None)
        await query.edit_message_text(f"{EMOJI['cross']} بنر لغو شد.", reply_markup=_back_button())

    elif action == "channels":
        await _show_channels(query)

    elif action == "add_channel":
        owner_state[query.from_user.id] = "await_add_channel"
        await query.edit_message_text(
            "یوزرنیم کانال رو بفرست (با یا بدون @).\nیادت باشه بات باید خودش عضو/ادمین اون کانال باشه.",
            reply_markup=_back_button("panel:channels"),
        )

    elif action == "remove_channel":
        owner_state[query.from_user.id] = "await_remove_channel"
        await query.edit_message_text(
            "یوزرنیم کانالی که می‌خوای حذف کنی رو بفرست:",
            reply_markup=_back_button("panel:channels"),
        )

    elif action == "badwords":
        await _show_badwords(query)

    elif action == "add_badword":
        owner_state[query.from_user.id] = "await_add_badword"
        await query.edit_message_text("کلمه‌ای که می‌خوای فیلتر بشه رو بفرست:", reply_markup=_back_button("panel:badwords"))

    elif action == "remove_badword":
        owner_state[query.from_user.id] = "await_remove_badword"
        await query.edit_message_text("کلمه‌ای که می‌خوای از فیلتر حذف بشه رو بفرست:", reply_markup=_back_button("panel:badwords"))

    elif action == "vip":
        owner_state[query.from_user.id] = "await_vip"
        await query.edit_message_text(
            f"{EMOJI['vip']} به این شکل بفرست: آیدی_عددی تعداد_روز\nمثال: 123456789 30",
            reply_markup=_back_button(),
        )

    elif action == "stats":
        chats = all_known_chats()
        groups = sum(1 for _, _, t in chats if t in ("group", "supergroup"))
        channels = sum(1 for _, _, t in chats if t == "channel")
        await query.edit_message_text(
            f"{EMOJI['stats']} آمار کلی بات:\n"
            f"👥 گروه‌ها: {groups}\n📢 کانال‌ها: {channels}\n🔢 مجموع چت‌ها: {len(chats)}",
            reply_markup=_back_button(),
        )

    elif action == "log":
        logs = recent_actions(15)
        if not logs:
            text = "لاگی ثبت نشده."
        else:
            lines = [f"• چت {c} — کاربر {a} — {act}" + (f" روی {t}" if t else "") for _, c, a, act, t in logs]
            text = "🗒 آخرین اکشن‌ها:\n\n" + "\n".join(lines)
        await query.edit_message_text(text, reply_markup=_back_button())


async def handle_owner_text_or_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if user_id not in OWNER_IDS or update.effective_chat.type != "private":
        return False

    state = owner_state.get(user_id)
    if not state:
        return False

    if state.startswith("await_rename_new:") and update.message.text:
        _, chat_id_str, command_key = state.split(":")
        chat_id = int(chat_id_str)
        from registry import COMMANDS
        default_trigger = COMMANDS[command_key][0]
        new_trigger = update.message.text.strip()
        owner_state.pop(user_id, None)
        if new_trigger == default_trigger:
            reset_command_alias(chat_id, command_key)
            await update.message.reply_text(f"{EMOJI['check']} دستور «{command_key}» به کلمه‌ی پیش‌فرض «{default_trigger}» برگشت.")
        else:
            set_command_alias(chat_id, command_key, new_trigger)
            await update.message.reply_text(f"{EMOJI['check']} از این به بعد کلمه‌ی «{new_trigger}» همون کار «{default_trigger}» رو در اون گروه انجام میده.")
        return True

    if state == "await_broadcast" and update.message.text:
        chats = all_known_chats()
        sent = failed = 0
        for chat_id, _, _ in chats:
            try:
                await context.bot.send_message(chat_id, f"{EMOJI['broadcast']} پیام همگانی:\n\n{update.message.text}")
                sent += 1
            except Exception:
                failed += 1
        owner_state.pop(user_id, None)
        await update.message.reply_text(f"{EMOJI['check']} ارسال شد به {sent} چت | {EMOJI['cross']} ناموفق: {failed}")
        return True

    if state == "await_banner" and update.message.photo:
        file_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        pending_banner[user_id] = (file_id, caption)
        owner_state[user_id] = "await_banner_choice"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 ارسال فوری", callback_data="panel:banner_now")],
            [InlineKeyboardButton("⏰ زمان‌بندی کن", callback_data="panel:banner_schedule")],
            [InlineKeyboardButton(f"{EMOJI['cross']} لغو", callback_data="panel:banner_cancel")],
        ])
        await update.message.reply_text("بنر رو گرفتم! می‌خوای الان بفرستم یا زمان‌بندی کنم؟", reply_markup=keyboard)
        return True

    if state == "await_banner_minutes" and update.message.text:
        text = update.message.text.strip()
        if not text.isdigit() or int(text) <= 0:
            await update.message.reply_text(f"{EMOJI['warn']} باید یه عدد مثبت بفرستی، مثلاً 60")
            return True
        minutes = int(text)
        pending = pending_banner.get(user_id)
        if not pending:
            owner_state.pop(user_id, None)
            await update.message.reply_text(f"{EMOJI['cross']} بنری در انتظار پیدا نشد، دوباره از اول امتحان کن.")
            return True
        file_id, caption = pending
        if not context.job_queue:
            owner_state.pop(user_id, None)
            pending_banner.pop(user_id, None)
            await update.message.reply_text(
                f"{EMOJI['cross']} JobQueue فعال نیست (پکیج job-queue نصب نشده)، پس زمان‌بندی امکان‌پذیر نیست.\n"
                f'لطفاً این رو نصب کن: pip install "python-telegram-bot[job-queue]"'
            )
            return True
        context.job_queue.run_once(
            _send_scheduled_banner_job, minutes * 60, data=(user_id, file_id, caption), name=f"banner_{user_id}"
        )
        owner_state.pop(user_id, None)
        pending_banner.pop(user_id, None)
        await update.message.reply_text(f"{EMOJI['check']} بنر برای {minutes} دقیقه‌ی دیگه زمان‌بندی شد ⏰")
        return True

    if state == "await_add_channel" and update.message.text:
        ch = add_required_channel(update.message.text.strip())
        owner_state.pop(user_id, None)
        await update.message.reply_text(
            f"{EMOJI['check']} کانال {ch} به لیست عضویت اجباری اضافه شد.\n"
            f"{EMOJI['warn']} یادت نره خودِ بات رو هم ادمین اون کانال کنی."
        )
        return True

    if state == "await_remove_channel" and update.message.text:
        remove_required_channel(update.message.text.strip())
        owner_state.pop(user_id, None)
        await update.message.reply_text(f"{EMOJI['check']} کانال حذف شد.")
        return True

    if state == "await_add_badword" and update.message.text:
        add_bad_word(update.message.text.strip())
        owner_state.pop(user_id, None)
        await update.message.reply_text(f"{EMOJI['check']} کلمه به لیست فیلتر اضافه شد.")
        return True

    if state == "await_remove_badword" and update.message.text:
        remove_bad_word(update.message.text.strip())
        owner_state.pop(user_id, None)
        await update.message.reply_text(f"{EMOJI['check']} کلمه از فیلتر حذف شد.")
        return True

    if state == "await_vip" and update.message.text:
        parts = update.message.text.split()
        if len(parts) != 2 or not all(p.lstrip("-").isdigit() for p in parts):
            await update.message.reply_text(f"{EMOJI['cross']} فرمت درست نیست. مثال: 123456789 30")
            return True
        target_id, days = int(parts[0]), int(parts[1])
        set_vip(update.effective_chat.id, target_id, days)
        owner_state.pop(user_id, None)
        await update.message.reply_text(f"{EMOJI['vip']} کاربر {target_id} برای {days} روز VIP شد.")
        return True

    return False
