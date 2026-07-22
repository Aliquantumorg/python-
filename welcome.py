from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import EMOJI
from database import register_chat, get_setting
import tone

RULES_TEXT = (
    f"{EMOJI['rules']} قوانین گروه:\n"
    f"1️⃣ احترام به همه‌ی اعضا الزامیه 🙏\n"
    f"2️⃣ ارسال لینک و تبلیغ بدون اجازه‌ی ادمین ممنوعه {EMOJI['cross']}\n"
    f"3️⃣ فحاشی و توهین = اخطار و در نهایت حذف از گروه {EMOJI['ban']}\n"
    f"4️⃣ اسپم و پیام‌های تکراری ممنوعه {EMOJI['mute']}\n\n"
    f"برای راهنمای کامل بات بنویس «راهنما» {EMOJI['rules']}"
)


async def track_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat:
        register_chat(chat.id, chat.title or chat.first_name or "بدون‌نام", chat.type)


async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            # خود بات تازه به گروه اضافه شده - اول لحن رو بپرس
            await context.bot.send_message(chat.id, tone.tt(chat.id, "ask_tone"), reply_markup=tone.tone_picker_keyboard(chat.id))
            continue

        name = member.first_name or "دوست جدید"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(tone.tt(chat.id, "rules_prompt_button"), callback_data="rules")]])
        custom_text = get_setting(chat.id, "custom_welcome_text", None)
        if custom_text:
            text = custom_text.replace("{name}", name)
        else:
            text = tone.tt(chat.id, "welcome_new_member", name=name)
        await context.bot.send_message(chat.id, text, reply_markup=keyboard)


async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    left = update.message.left_chat_member
    if not left or left.id == context.bot.id:
        return
    name = left.first_name or "یکی از اعضا"
    await update.message.reply_text(f"👋 {name} از گروه رفت. امیدواریم به‌زودی برگرده 💔")


async def send_rules_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_TEXT)


async def rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(RULES_TEXT)
