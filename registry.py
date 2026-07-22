"""
رجیستری مرکزی دستورات تک‌کلمه‌ای (بدون آرگومان).
هر ورودی: کلید داخلی -> (تریگر پیش‌فرض فارسی، تابع اجراکننده، بخش، توضیح کوتاه، سطح دسترسی)
سطح دسترسی: "public" (همه، مگر دسترسی عمومی خاموش باشه) | "admin" (ادمین/مالک) | "owner" (فقط مالک، فقط پیوی)

نکته: دستورات آرگومان‌دار (قفل کاراکتر [عدد]، بی‌صدا همه [دقیقه]، یادآوری [دقیقه] [متن]،
تنظیم خوش‌آمد [متن]، فیلتر [پاسخ]) به‌خاطر داشتن پارامتر، از این رجیستری مستثنی‌ان و
پیشوندشون ثابته (قابل تغییر نام از پنل نیستن) - در main.py جدا مدیریت می‌شن.
"""

import admin, welcome, games, tagall, timeinfo, wordfilter, group_link
import forwardlock, content_locks, muteall, settings_view, admincall, purge_bot, publicaccess
from antispam import lock_spam, unlock_spam
from filters import lock_link, unlock_link, lock_badwords, unlock_badwords

COMMANDS = {
    # --- عمومی ---
    "rules":        ("قوانین", welcome.send_rules_text, "public", "نمایش قوانین گروه"),
    "dooz":         ("دوز", games.start_tic_tac_toe, "public", "بازی دوز دونفره"),
    "rps":          ("سنگ کاغذ قیچی", games.start_rps, "public", "بازی سنگ‌کاغذقیچی دونفره"),
    "guess":        ("حدس عدد", games.start_guess_number, "public", "بازی حدس عدد"),
    "hangman":      ("دار", games.start_hangman, "public", "بازی حدس کلمه"),
    "group_link":   ("لینک گروه", group_link.send_group_link, "public", "دریافت لینک دعوت گروه"),

    # --- انضباطی (ادمین/مالک) ---
    "ban":          ("بن", admin.ban_user, "admin", "اخراج دائمی (با ریپلای)"),
    "kick":         ("کیک", admin.kick_user, "admin", "اخراج موقت (با ریپلای)"),
    "mute":         ("سکوت", admin.mute_user, "admin", "میوت کردن (با ریپلای)"),
    "unmute":       ("حذف سکوت", admin.unmute_user, "admin", "رفع میوت (با ریپلای)"),
    "purge":        ("پاکسازی", admin.purge_messages, "admin", "حذف پیام‌ها از یک ریپلای تا الان"),
    "purge_bot":    ("پاکسازی ربات", purge_bot.purge_bot_messages, "admin", "حذف پیام‌های اخیر ربات‌ها"),
    "lock_group":   ("قفل گروه", admin.lock_group, "admin", "فقط ادمین‌ها پیام بدن"),
    "unlock_group": ("باز کردن قفل", admin.unlock_group, "admin", "باز کردن قفل گروه"),
    "pin":          ("سنجاق", admin.pin_message, "admin", "پین کردن پیام (با ریپلای)"),
    "unpin":        ("حذف سنجاق", admin.unpin_message, "admin", "برداشتن پین (با ریپلای)"),
    "identity":     ("هویت", admin.show_identity, "admin", "نمایش اطلاعات یک کاربر (با ریپلای؛ بدون ریپلای، اطلاعات خودتو نشون میده)"),
    "unmute_all":   ("باصدا همه", muteall.unmute_all, "admin", "لغو سکوت کامل گروه"),

    # --- قفل‌های محتوا (ادمین/مالک) ---
    "lock_spam":       ("قفل اسپم", lock_spam, "admin", "فعال‌سازی آنتی‌فلود"),
    "unlock_spam":     ("باز اسپم", unlock_spam, "admin", "غیرفعال‌سازی آنتی‌فلود"),
    "lock_link":       ("قفل لینک", lock_link, "admin", "فیلتر لینک روشن"),
    "unlock_link":     ("باز لینک", unlock_link, "admin", "فیلتر لینک خاموش"),
    "lock_badwords":   ("قفل فحش", lock_badwords, "admin", "فیلتر فحش روشن"),
    "unlock_badwords": ("باز فحش", unlock_badwords, "admin", "فیلتر فحش خاموش"),
    "lock_forward":    ("قفل فوروارد", forwardlock.lock_forward, "admin", "حذف پیام فورواردی"),
    "unlock_forward":  ("باز فوروارد", forwardlock.unlock_forward, "admin", "اجازه‌ی فوروارد"),
    "lock_media":      ("قفل مدیا", content_locks.lock_media, "admin", "حذف همه‌ی انواع مدیا"),
    "unlock_media":    ("باز مدیا", content_locks.unlock_media, "admin", "اجازه‌ی ارسال مدیا"),
    "lock_gif":        ("قفل گیف", content_locks.lock_gif, "admin", "حذف فقط گیف/انیمیشن"),
    "unlock_gif":      ("باز گیف", content_locks.unlock_gif, "admin", "اجازه‌ی ارسال گیف"),
    "lock_sticker":    ("قفل استیکر", content_locks.lock_sticker, "admin", "حذف فقط استیکر"),
    "unlock_sticker":  ("باز استیکر", content_locks.unlock_sticker, "admin", "اجازه‌ی ارسال استیکر"),
    "lock_location":   ("قفل لوکیشن", content_locks.lock_location, "admin", "حذف لوکیشن ارسالی"),
    "unlock_location": ("باز لوکیشن", content_locks.unlock_location, "admin", "اجازه‌ی ارسال لوکیشن"),
    "lock_contact":    ("قفل مخاطب", content_locks.lock_contact, "admin", "حذف مخاطب ارسالی"),
    "unlock_contact":  ("باز مخاطب", content_locks.unlock_contact, "admin", "اجازه‌ی ارسال مخاطب"),
    "lock_hashtag":    ("قفل هشتگ", content_locks.lock_hashtag, "admin", "حذف پیام حاوی #"),
    "unlock_hashtag":  ("باز هشتگ", content_locks.unlock_hashtag, "admin", "اجازه‌ی هشتگ"),
    "lock_id":         ("قفل آیدی", content_locks.lock_id, "admin", "حذف پیام حاوی @یوزرنیم"),
    "unlock_id":       ("باز آیدی", content_locks.unlock_id, "admin", "اجازه‌ی منشن"),
    "lock_reply":      ("قفل ریپلای", content_locks.lock_reply, "admin", "حذف پیام‌های ریپلای‌شده"),
    "unlock_reply":    ("باز ریپلای", content_locks.unlock_reply, "admin", "اجازه‌ی ریپلای"),
    "lock_message":    ("قفل پیام", content_locks.lock_message, "admin", "بستن کامل چت متنی"),
    "unlock_message":  ("باز پیام", content_locks.unlock_message, "admin", "باز کردن چت متنی"),

    # --- ابزار و تنظیمات (ادمین/مالک) ---
    "tag":               ("تگ", tagall.tag_all_command, "admin", "تگ اعضای شناخته‌شده"),
    "time":              ("تایم", timeinfo.send_time, "public", "نمایش تاریخ شمسی/میلادی"),
    "remove_filter":     ("حذف فیلتر", wordfilter.remove_filter_command, "admin", "حذف یک فیلتر سفارشی (با ریپلای)"),
    "show_settings":     ("تنظیمات", settings_view.show_settings, "admin", "نمایش وضعیت همه‌ی قفل‌ها"),
    "reset_settings":    ("ریست تنظیمات", settings_view.reset_settings, "admin", "بازگشت به حالت پیش‌فرض"),
    "admin_call_on":     ("فراخوان ادمین روشن", admincall.enable_admin_call, "admin", "فعال‌سازی فراخوان ادمین"),
    "admin_call_off":    ("فراخوان ادمین خاموش", admincall.disable_admin_call, "admin", "غیرفعال‌سازی فراخوان ادمین"),
    "report_on":         ("گزارش تخلف روشن", admincall.enable_report, "admin", "فعال‌سازی گزارش تخلف"),
    "report_off":        ("گزارش تخلف خاموش", admincall.disable_report, "admin", "غیرفعال‌سازی گزارش تخلف"),
    "report":            ("گزارش", admincall.report_command, "public", "گزارش یک پیام به ادمین‌ها (با ریپلای)"),
    "public_access_on":  ("دسترسی عمومی روشن", publicaccess.enable_public_access, "admin", "همه بتونن از امکانات عمومی استفاده کنن"),
    "public_access_off": ("دسترسی عمومی خاموش", publicaccess.disable_public_access, "admin", "فقط ادمین‌ها/مالک به امکانات عمومی دسترسی داشته باشن"),
}

# دستورهایی که آرگومان دارن و در main.py با startswith بررسی می‌شن (غیرقابل تغییرنام از پنل)
PREFIX_COMMANDS = {
    "قفل کاراکتر": 'محدودیت طول پیام. مثال: «قفل کاراکتر 200» (بیشتر از ۲۰۰ کاراکتر حذف میشه) یا «قفل کاراکتر خاموش»',
    "بی‌صدا همه": 'سکوت کامل گروه به مدت مشخص با بازگشت خودکار. مثال: «بی‌صدا همه 15» (۱۵ دقیقه)',
    "یادآوری": 'یادآوری زمان‌بندی‌شده برای گروه. مثال: «یادآوری 10 وقت جلسه‌ست» (۱۰ دقیقه‌ی دیگه ارسال میشه)',
    "تنظیم خوش آمد": 'تغییر متن خوش‌آمدگویی گروه. مثال: «تنظیم خوش آمد سلام {name} خوش اومدی!» (از {name} برای اسم عضو استفاده کن)',
    "فیلتر": 'افزودن پاسخ خودکار. روی پیامی که متنش تریگره ریپلای کن، بعد بنویس مثلاً «فیلتر سلام بر شما»',
}
