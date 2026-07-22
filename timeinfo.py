from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime

from telegram import Update
from telegram.ext import ContextTypes

TEHRAN_TZ = ZoneInfo("Asia/Tehran")

WEEKDAYS_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
MONTHS_FA = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


async def send_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TEHRAN_TZ)
    jnow = jdatetime.datetime.fromgregorian(datetime=now)

    weekday_fa = WEEKDAYS_FA[now.weekday()]
    month_fa = MONTHS_FA[jnow.month - 1]
    shamsi_numeric = f"{jnow.year}/{jnow.month:02d}/{jnow.day:02d}"
    shamsi_text = f"{weekday_fa} {jnow.day} {month_fa} {jnow.year}"
    miladi_text = now.strftime("%Y-%m-%d")

    await update.message.reply_text(
        f"🕒 تایم دقیق الان:\n\n"
        f"📅 شمسی: {shamsi_text}  ({shamsi_numeric})\n"
        f"📅 میلادی: {miladi_text}\n"
        f"⏰ ساعت: {now.strftime('%H:%M:%S')}\n"
        f"🌍 منطقه‌ی زمانی: تهران (Asia/Tehran, +03:30)\n\n"
        f"اگه این تاریخ با تقویم واقعی فرق داره، لطفاً همین متن رو کپی کن و بفرست تا دقیق بررسی کنم."
    )
