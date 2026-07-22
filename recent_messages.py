from collections import defaultdict, deque
from telegram import Update
from telegram.ext import ContextTypes

MAX_TRACK = 200  # حداکثر پیام اخیر که برای هر چت به خاطر می‌سپاریم
_recent = defaultdict(lambda: deque(maxlen=MAX_TRACK))  # chat_id -> deque[(message_id, is_bot)]


async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user:
        return
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return
    _recent[chat.id].append((message.message_id, message.from_user.is_bot))


def get_recent_bot_messages(chat_id):
    return [mid for mid, is_bot in _recent[chat_id] if is_bot]
