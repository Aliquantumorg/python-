import os

# توکن بات رو از پنل بله (ble.ir) بگیر و اینجا یا در متغیر محیطی BOT_TOKEN بذار
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT-YOUR-TOKEN-HERE")

# آدرس پایه‌ی API بله
BALE_API_BASE = "https://tapi.bale.ai/bot"
# آدرس پایه‌ی دانلود فایل از بله (این با آدرس API فرق داره! بدون این، دانلود فایل‌ها از تلگرام تلاش می‌شد نه بله)
BALE_FILE_BASE = "https://tapi.bale.ai/file/bot"

# فقط این آیدی عددی، مالک بات محسوب میشه و به پنل مدیریت (فقط در پیوی) دسترسی داره
OWNER_IDS = [581301761]

# کلمات ممنوعه‌ی پیش‌فرض (از پنل هم قابل افزودن/حذفه)
DEFAULT_BAD_WORDS = [
    "کلمه_نامناسب_۱",
    "کلمه_نامناسب_۲",
]

# جلوگیری از لینک/تبلیغ توسط اعضای عادی (پیش‌فرض)
BLOCK_LINKS_FOR_MEMBERS_DEFAULT = True

# --- تنظیمات پیش‌فرض آنتی‌فلود سطح‌بندی‌شده ---
FLOOD_MAX_MESSAGES = 6        # حداکثر پیام مجاز در بازه
FLOOD_WINDOW_SECONDS = 8      # بازه‌ی زمانی بررسی (ثانیه)
FLOOD_MUTE_MINUTES = 10       # مدت میوت خودکار سطح اول
FLOOD_LONG_MUTE_MINUTES = 60  # مدت میوت طولانی برای تکرار

DB_PATH = "gapbot.db"

# نام و هویت بات
BOT_NAME = "گروه‌یار"
BOT_INTRO = "🤝 گروه‌یار در خدمته! برای شروع بنویس «راهنما» دوست عزیز 🤝"

# --- تنظیمات ساخت گیف ---
# چون بات روی ویندوز اجرا میشه، اول فونت‌های رایج ویندوز رو امتحان می‌کنیم؛
# اگه پیدا نشد، به فونت‌های لینوکسی/پیشفرض برمی‌گردیم (ولی اون‌ها فارسی رو درست نشون نمی‌دن).
FONT_CANDIDATES = {
    "tahoma": [r"C:\Windows\Fonts\tahoma.ttf", r"C:\Windows\Fonts\Tahoma.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "arial": [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "b_nazanin": [r"C:\Windows\Fonts\BNazanin.ttf", r"C:\Windows\Fonts\tahoma.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}
FONT_LABELS = {"tahoma": "Tahoma", "arial": "Arial", "b_nazanin": "B Nazanin"}

GIF_COLOR_OPTIONS = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (230, 30, 30),
    "yellow": (250, 210, 20),
    "green": (30, 200, 90),
    "blue": (40, 120, 230),
}
GIF_COLOR_LABELS = {
    "white": "⚪️ سفید", "black": "⚫️ مشکی", "red": "🔴 قرمز",
    "yellow": "🟡 زرد", "green": "🟢 سبز", "blue": "🔵 آبی",
}

# سایزهای آماده (نسبت به ارتفاع تصویر) + گزینه‌ی سایز دقیق (کاربر خودش عدد پیکسل وارد می‌کنه)
GIF_SIZE_PRESETS = {"small": 0.05, "medium": 0.08, "large": 0.12}
GIF_SIZE_LABELS = {"small": "کوچیک", "medium": "متوسط", "large": "بزرگ", "exact": "✏️ سایز دقیق (خودم می‌نویسم)"}
GIF_EXACT_SIZE_MIN = 10
GIF_EXACT_SIZE_MAX = 200

# موقعیت‌های متن: شبکه‌ی ۹تایی (۳x۳)
GIF_POSITION_LABELS = {
    "top_left": "↖️ بالا-چپ", "top_center": "⬆️ بالا-وسط", "top_right": "↗️ بالا-راست",
    "middle_left": "⬅️ وسط-چپ", "middle_center": "⏺ وسط-وسط", "middle_right": "➡️ وسط-راست",
    "bottom_left": "↙️ پایین-چپ", "bottom_center": "⬇️ پایین-وسط", "bottom_right": "↘️ پایین-راست",
}

GIF_MAX_FRAMES = 40      # حداکثر فریم پردازش‌شده (برای سرعت و حجم مناسب)
GIF_MAX_WIDTH = 480      # حداکثر عرض خروجی به پیکسل
GIF_MAX_CONCURRENT_JOBS = 2   # حداکثر تعداد ساخت گیف هم‌زمان (ضد کد هنگی)
GIF_PROCESS_TIMEOUT_SECONDS = 90  # اگه پردازش بیشتر از این طول بکشه، لغو می‌شه

# ایموجی‌های ثابت برای طراحی یکپارچه‌ی پیام‌ها
EMOJI = {
    "welcome": "🎉",
    "wave": "👋",
    "rules": "📖",
    "warn": "⚠️",
    "ban": "🚫",
    "kick": "👢",
    "mute": "🔇",
    "unmute": "🔊",
    "stats": "📊",
    "panel": "🛠",
    "broadcast": "📣",
    "banner": "🖼",
    "channel": "📢",
    "check": "✅",
    "cross": "❌",
    "game": "🎮",
    "coin": "🪙",
    "vip": "👑",
    "lock": "🔒",
    "unlock": "🔓",
    "fire": "🚨",
    "star": "⭐️",
    "back": "🔙",
    "add": "➕",
    "remove": "➖",
}
