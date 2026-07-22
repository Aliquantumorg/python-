from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import get_tone, set_tone

DEFAULT_TONE = "polite"
TONE_LABELS = {
    "polite": "🎩 محترمانه",
    "friendly": "😄 صمیمی",
    "street": "😎 چاله‌میدونی",
}
TONE_NAME_TO_KEY = {
    "محترمانه": "polite",
    "صمیمی": "friendly",
    "چاله میدونی": "street",
    "چاله‌میدونی": "street",
}

# هر کلید یه پیام پرتکرار بات رو نشون می‌ده که تو هر سه لحن نوشته شده.
# برای افزودن پیام جدید فقط کافیه یه کلید جدید با سه نسخه اضافه کنی.
MESSAGES = {
    "intro": {
        "polite": "🤝 گروه‌یار در خدمت شماست. برای شروع لطفاً «راهنما» را ارسال بفرمایید 🤝",
        "friendly": "🤝 سلاااام! من گروه‌یارم، اینجام کمکت کنم 😄 برای شروع بنویس «راهنما»",
        "street": "🤝 هوووی داداش/آبجی! گروه‌یار اومد 😎 بنویس «راهنما» تا ببینی چه خبره اینجا",
    },
    "ask_tone": {
        "polite": "پیش از آغاز، لطفاً لحن گفت‌وگوی مایل خود با ربات را انتخاب بفرمایید:",
        "friendly": "قبل از شروع، بگو دوست داری چه‌جوری باهات حرف بزنم:",
        "street": "بگو ببینم داداش، چه مدلی باهات صحبت کنم؟ 😎",
    },
    "tone_set": {
        "polite": "✅ لحن گفت‌وگو با موفقیت روی «{tone_label}» تنظیم شد. سپاسگزاریم.",
        "friendly": "✅ باشه! از الان با لحن «{tone_label}» باهات حرف می‌زنم 😄",
        "street": "✅ اوکی داداش، از الان لحنمون شد «{tone_label}» 😎 بزن بریم!",
    },
    "tone_change_usage": {
        "polite": "لطفاً به این شکل بنویسید: «تغییر لحن به محترمانه» یا «صمیمی» یا «چاله میدونی»",
        "friendly": "اینجوری بنویس: «تغییر لحن به صمیمی» یا «محترمانه» یا «چاله میدونی»",
        "street": "بنویس «تغییر لحن به چاله میدونی» یا هرکدوم دیگه که خواستی داداش",
    },
    "help_intro": {
        "polite": "💠 راهنمای جامع گروه‌یار (لحن: محترمانه)\n\nدر ادامه امکانات ربات را با احترام کامل تقدیم می‌کنیم:",
        "friendly": "💠 راهنمای گروه‌یار (لحن: صمیمی) 😄\n\nبیا با هم ببینیم چه امکاناتی داریم:",
        "street": "💠 راهنمای گروه‌یار (لحن: چاله‌میدونی) 😎\n\nخب داداش گوش کن ببین چه امکاناتی رو داریم:",
    },
    "welcome_new_member": {
        "polite": "🎉 ورود شما را به این گروه خیر مقدم عرض می‌کنیم، {name} عزیز. خواهشمندیم پیش از ارسال پیام، قوانین گروه را مطالعه بفرمایید 👇",
        "friendly": "🎉 به‌به {name} جان خوش اومدی! 😄 یه نگاهی به قوانین گروه بنداز، بعد راحت باش 👇",
        "street": "🎉 اوه اوه {name} اومد! خوش اومدی داداش/آبجی 😎 یه چشم به قوانین بنداز که دعوا نشه بعداً 👇",
    },
    "rules_prompt_button": {
        "polite": "📖 مشاهده‌ی قوانین گروه",
        "friendly": "📖 قوانین گروه رو ببین",
        "street": "📖 قوانینو ببین داداش",
    },
    "force_join_group": {
        "polite": "❌ {name} عزیز، با نهایت احترام، پیام شما پاک شد. برای ارسال پیام در این گروه، ابتدا لازم است عضو کانال(های) زیر شوید 👇",
        "friendly": "❌ {name} جان پیامتو پاک کردم، شرمنده 😅 اول عضو این کانال(ها) شو، بعد راحت پیام بده 👇",
        "street": "❌ {name} پیامتو زدم داداش، دلگیر نشو 😅 اول برو عضو این کانال(ها) شو، بعد بیا هرچی دلت خواست بگو 👇",
    },
    "force_join_pv": {
        "polite": "👋 سلام {name}. برای استفاده از خدمات گروه‌یار، خواهشمندیم ابتدا عضو کانال(های) زیر شوید 👇",
        "friendly": "👋 سلام {name} جان! برای استفاده از گروه‌یار اول باید عضو این کانال(ها) بشی 👇",
        "street": "👋 هوی {name}! اول برو عضو این کانال(ها) شو داداش، بعدش میتونی از امکانات گروه‌یار استفاده کنی 👇",
    },
    "pv_join_success": {
        "polite": "✅ خوش آمدید! جهت بهره‌مندی از خدمات گروه‌یار:\n\n1️⃣ ربات را به گروه خود اضافه بفرمایید\n2️⃣ لطفاً دسترسی «ادمین کامل» به ربات اعطا کنید\n\nسپس در گروه «راهنما» را ارسال بفرمایید.\n\n🎬 همچنین می‌توانید همین‌جا در پیوی با ارسال «ساخت گیف» یک گیف اختصاصی بسازید.",
        "friendly": "✅ آفرین، خوش اومدی! حالا برای استفاده از گروه‌یار:\n\n1️⃣ من رو به گروهت اضافه کن\n2️⃣ حتماً ادمین کاملم کن، وگرنه دست‌وبالم بسته‌س 😄\n\nبعدش توی گروه بنویس «راهنما»\n\n🎬 راستی، همین‌جا هم می‌تونی بنویسی «ساخت گیف» تا یه گیف باحال بسازیم!",
        "street": "✅ آفرین داداش! حالا اینکارارو بکن:\n\n1️⃣ من رو بنداز تو گروهت\n2️⃣ ادمین فولم کن ها، وگرنه هیچ غلطی نمی‌تونم بکنم 😎\n\nبعدش تو گروه بنویس «راهنما» ببین چه خبره\n\n🎬 آها یه چیز باحال: همین‌جا بنویس «ساخت گیف» تا یه گیف توپ برات بسازم!",
    },
    "deny_admin_only": {
        "polite": "⛔️ این دستور صرفاً برای ادمین‌های محترم گروه یا مالک ربات مجاز است.",
        "friendly": "⛔️ این دستور فقط دست ادمینا و مالک بات می‌چرخه، شرمنده 😅",
        "street": "⛔️ بیخیال داداش، این دکمه فقط دست ادمیناست، تو دست نزن بهش 😎",
    },
    "reply_required_generic": {
        "polite": "⚠️ خواهشمندیم روی پیام فرد موردنظر ریپلای بفرمایید.",
        "friendly": "⚠️ اول رو پیام همون آدم ریپلای کن، بعد بزن این دکمه رو",
        "street": "⚠️ داداش رو پیام طرف ریپلای کن اول، اینجوری که نمیشه",
    },
    "ban_done": {
        "polite": "🚫 کاربر {name} با احترام از گروه اخراج گردید.",
        "friendly": "🚫 {name} رو انداختم بیرون از گروه 😅",
        "street": "🚫 {name} رو پرت کردم بیرون داداش، دیگه راهش نده 😎",
    },
    "kick_done": {
        "polite": "👢 کاربر {name} از گروه اخراج شد (امکان بازگشت مجدد دارند).",
        "friendly": "👢 {name} رو موقتاً از گروه انداختم بیرون",
        "street": "👢 {name} یه گاز گرفت رفت بیرون، میتونه برگرده باز داداش",
    },
    "mute_done": {
        "polite": "🔇 کاربر {name} با موفقیت میوت گردید.",
        "friendly": "🔇 {name} رو ساکت کردم، یکم آروم شه 😄",
        "street": "🔇 دهن {name} رو بستم داداش، یکم نفس بکشه 😎",
    },
    "unmute_done": {
        "polite": "🔊 محدودیت کاربر {name} برداشته شد.",
        "friendly": "🔊 {name} آزاد شد، دوباره می‌تونه حرف بزنه 😄",
        "street": "🔊 {name} رو ول کردم داداش، برو حرف بزن باز 😎",
    },
    "purge_done": {
        "polite": "🧹 تعداد {count} پیام با موفقیت پاک‌سازی گردید.",
        "friendly": "🧹 {count} تا پیام رو تمیز کردم 😄",
        "street": "🧹 {count} تا پیامو جارو کردم داداش، تمیز شد 😎",
    },
    "group_link_result": {
        "polite": "📎 لینک دعوت این گروه به شرح زیر است:\n{link}",
        "friendly": "📎 بفرما، لینک گروه اینه:\n{link}",
        "street": "📎 بیا داداش، لینک گروه رو بگیر:\n{link}",
    },
}


def get_chat_tone(chat_id) -> str:
    return get_tone(chat_id) or DEFAULT_TONE


def has_tone_been_set(chat_id) -> bool:
    return get_tone(chat_id) is not None


def tt(chat_id, key, **kwargs) -> str:
    tone = get_chat_tone(chat_id)
    template = MESSAGES.get(key, {}).get(tone) or MESSAGES.get(key, {}).get(DEFAULT_TONE, "")
    return template.format(**kwargs) if kwargs else template


def deny_text(chat_id) -> str:
    return tt(chat_id, "deny_admin_only")


def reply_required_text(chat_id) -> str:
    return tt(chat_id, "reply_required_generic")


def tone_picker_keyboard(target_chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(TONE_LABELS["polite"], callback_data=f"tone:{target_chat_id}:polite")],
        [InlineKeyboardButton(TONE_LABELS["friendly"], callback_data=f"tone:{target_chat_id}:friendly")],
        [InlineKeyboardButton(TONE_LABELS["street"], callback_data=f"tone:{target_chat_id}:street")],
    ])


async def show_tone_picker(update, context):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        tt(chat_id, "ask_tone"), reply_markup=tone_picker_keyboard(chat_id)
    )


async def tone_picker_callback(update, context):
    query = update.callback_query
    _, chat_id_str, tone = query.data.split(":")
    chat_id = int(chat_id_str)
    set_tone(chat_id, tone)
    await query.answer()
    await query.edit_message_text(tt(chat_id, "tone_set", tone_label=TONE_LABELS[tone]))


async def change_tone_command(update, context):
    """دستور متنی: «تغییر لحن به محترمانه/صمیمی/چاله میدونی»"""
    from permissions import can_run_admin_command

    chat_id = update.effective_chat.id
    if update.effective_chat.type in ("group", "supergroup") and not await can_run_admin_command(update, context):
        await update.message.reply_text(deny_text(chat_id))
        return

    text = update.message.text.strip()
    prefix = "تغییر لحن به "
    requested = text[len(prefix):].strip() if text.startswith(prefix) else ""
    tone = TONE_NAME_TO_KEY.get(requested)

    if not tone:
        await update.message.reply_text(tt(chat_id, "tone_change_usage"))
        return

    set_tone(chat_id, tone)
    await update.message.reply_text(tt(chat_id, "tone_set", tone_label=TONE_LABELS[tone]))
