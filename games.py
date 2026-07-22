import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import EMOJI
from database import record_game_result, add_coins

# --- حافظه‌ی موقت بازی‌ها (per chat) ---
tic_lobbies = {}     # chat_id -> {"initiator": id, "name": str}
tic_games = {}       # chat_id -> game state
rps_lobbies = {}
rps_games = {}
guess_numbers = {}
hangman_games = {}

EMPTY, X, O = "➖", "❌", "⭕️"
WIN_COINS = 10


# ================= دوز دونفره =================
async def start_tic_tac_toe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    tic_lobbies[chat_id] = {"initiator": user.id, "name": user.first_name}
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🙋 پیوستن به بازی", callback_data=f"ticjoin:{user.id}")]]
    )
    await update.message.reply_text(
        f"{EMOJI['game']} {user.first_name} یه بازی دوز راه انداخته!\n"
        f"یه نفر دیگه رو دکمه‌ی زیر بزنه تا بازی شروع بشه 👇",
        reply_markup=keyboard,
    )


def _tic_board_keyboard(chat_id):
    board = tic_games[chat_id]["board"]
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(board[r * 3 + c], callback_data=f"tic:{r*3+c}") for c in range(3)] for r in range(3)]
    )


def _check_winner(board):
    lines = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a, b, c in lines:
        if board[a] != EMPTY and board[a] == board[b] == board[c]:
            return board[a]
    return "draw" if EMPTY not in board else None


async def tic_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    lobby = tic_lobbies.get(chat_id)

    if not lobby:
        await query.answer("این دعوت دیگه معتبر نیست 🙁", show_alert=True)
        return
    if query.from_user.id == lobby["initiator"]:
        await query.answer("نمی‌تونی با خودت بازی کنی 😄", show_alert=True)
        return

    await query.answer(f"{EMOJI['check']} بازی شروع شد!")
    tic_games[chat_id] = {
        "board": [EMPTY] * 9,
        "players": {lobby["initiator"]: X, query.from_user.id: O},
        "names": {lobby["initiator"]: lobby["name"], query.from_user.id: query.from_user.first_name},
        "turn": lobby["initiator"],
    }
    del tic_lobbies[chat_id]

    game = tic_games[chat_id]
    await query.edit_message_text(
        f"{EMOJI['game']} {game['names'][lobby['initiator']]} ({X}) در برابر {game['names'][query.from_user.id]} ({O})\n"
        f"نوبت {game['names'][game['turn']]} عزیزه:",
        reply_markup=_tic_board_keyboard(chat_id),
    )


async def tic_tac_toe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    game = tic_games.get(chat_id)

    if not game:
        await query.answer(f"بازی‌ای در جریان نیست. بنویس «دوز» {EMOJI['game']}", show_alert=True)
        return
    if query.from_user.id not in game["players"]:
        await query.answer("این بازی مال شما نیست 🙂", show_alert=True)
        return
    if query.from_user.id != game["turn"]:
        await query.answer("صبر کن نوبتت بشه 😅", show_alert=True)
        return

    idx = int(query.data.split(":")[1])
    if game["board"][idx] != EMPTY:
        await query.answer("این خونه پره ❌", show_alert=True)
        return

    await query.answer()
    mark = game["players"][query.from_user.id]
    game["board"][idx] = mark
    winner_mark = _check_winner(game["board"])

    if winner_mark:
        return await _end_tic(query, chat_id, winner_mark, game)

    other_id = next(uid for uid in game["players"] if uid != query.from_user.id)
    game["turn"] = other_id
    await query.edit_message_text(
        f"{EMOJI['game']} نوبت {game['names'][other_id]} عزیزه:",
        reply_markup=_tic_board_keyboard(chat_id),
    )


async def _end_tic(query, chat_id, winner_mark, game):
    board_text = "\n".join(" ".join(game["board"][r*3:(r+1)*3]) for r in range(3))

    if winner_mark == "draw":
        text = "🤝 بازی مساوی شد!"
        for uid in game["players"]:
            record_game_result(uid, "tic", False)
    else:
        winner_id = next(uid for uid, mark in game["players"].items() if mark == winner_mark)
        loser_id = next(uid for uid in game["players"] if uid != winner_id)
        record_game_result(winner_id, "tic", True)
        record_game_result(loser_id, "tic", False)
        add_coins(winner_id, WIN_COINS)
        text = f"🏆 {game['names'][winner_id]} برنده شد و {WIN_COINS} {EMOJI['coin']} گرفت! تبریک 🎉"

    await query.edit_message_text(f"{text}\n\n{board_text}\n\nبرای بازی جدید بنویس «دوز»")
    del tic_games[chat_id]


# ================= سنگ کاغذ قیچی دونفره =================
RPS_CHOICES = {"rock": "🪨 سنگ", "paper": "📄 کاغذ", "scissors": "✂️ قیچی"}
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


async def start_rps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    rps_lobbies[chat_id] = {"initiator": user.id, "name": user.first_name}
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🙋 پیوستن به بازی", callback_data=f"rpsjoin:{user.id}")]]
    )
    await update.message.reply_text(
        f"✊✋✌️ {user.first_name} یه بازی سنگ‌کاغذقیچی راه انداخته!\n"
        f"یه نفر دیگه دکمه‌ی زیر رو بزنه تا بازی شروع بشه 👇",
        reply_markup=keyboard,
    )


def _rps_choice_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🪨 سنگ", callback_data="rpschoice:rock"),
        InlineKeyboardButton("📄 کاغذ", callback_data="rpschoice:paper"),
        InlineKeyboardButton("✂️ قیچی", callback_data="rpschoice:scissors"),
    ]])


async def rps_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    lobby = rps_lobbies.get(chat_id)

    if not lobby:
        await query.answer("این دعوت دیگه معتبر نیست 🙁", show_alert=True)
        return
    if query.from_user.id == lobby["initiator"]:
        await query.answer("نمی‌تونی با خودت بازی کنی 😄", show_alert=True)
        return

    await query.answer(f"{EMOJI['check']} بازی شروع شد! هر دو نفر دکمه‌شون رو بزنن.")
    rps_games[chat_id] = {
        "players": [lobby["initiator"], query.from_user.id],
        "names": {lobby["initiator"]: lobby["name"], query.from_user.id: query.from_user.first_name},
        "choices": {},
    }
    del rps_lobbies[chat_id]

    game = rps_games[chat_id]
    await query.edit_message_text(
        f"✊✋✌️ {game['names'][game['players'][0]]} در برابر {game['names'][game['players'][1]]}\n"
        f"هر دو نفر باید مخفیانه انتخابشون رو بزنن:",
        reply_markup=_rps_choice_keyboard(),
    )


async def rps_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    game = rps_games.get(chat_id)
    choice = query.data.split(":")[1]

    if not game or query.from_user.id not in game["players"]:
        await query.answer("این بازی مال شما نیست 🙂", show_alert=True)
        return
    if query.from_user.id in game["choices"]:
        await query.answer("قبلاً انتخابتو زدی، منتظر نفر دوم باش ⏳", show_alert=True)
        return

    game["choices"][query.from_user.id] = choice
    await query.answer(f"{EMOJI['check']} انتخابت ثبت شد!")

    if len(game["choices"]) < 2:
        return  # هنوز نفر دوم انتخاب نکرده

    p1, p2 = game["players"]
    c1, c2 = game["choices"][p1], game["choices"][p2]

    if c1 == c2:
        result_text = "🤝 مساوی شدید!"
        winner_id = None
    elif RPS_BEATS[c1] == c2:
        winner_id = p1
    else:
        winner_id = p2

    if winner_id:
        loser_id = p2 if winner_id == p1 else p1
        record_game_result(winner_id, "rps", True)
        record_game_result(loser_id, "rps", False)
        add_coins(winner_id, WIN_COINS)
        result_text = f"🏆 {game['names'][winner_id]} برد و {WIN_COINS} {EMOJI['coin']} گرفت!"

    await query.edit_message_text(
        f"{game['names'][p1]}: {RPS_CHOICES[c1]}\n{game['names'][p2]}: {RPS_CHOICES[c2]}\n\n{result_text}\n\n"
        f"برای بازی جدید بنویس «سنگ کاغذ قیچی»"
    )
    del rps_games[chat_id]


# ================= حدس عدد (تک‌نفره) =================
async def start_guess_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    guess_numbers[chat_id] = {"number": random.randint(1, 100), "tries": 0, "player": update.effective_user.id}
    await update.message.reply_text("🔢 یه عدد بین ۱ تا ۱۰۰ توی ذهنم انتخاب کردم! فقط کافیه عددتو بنویسی 😎")


async def handle_guess_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_id = update.effective_chat.id
    game = guess_numbers.get(chat_id)
    if not game or not update.message.text or not update.message.text.strip().isdigit():
        return False

    guess = int(update.message.text.strip())
    game["tries"] += 1

    if guess == game["number"]:
        record_game_result(game["player"], "guess", True)
        add_coins(game["player"], WIN_COINS)
        await update.message.reply_text(
            f"🎯 آفرین! عدد {game['number']} بود، در {game['tries']} تلاش حدس زدی و "
            f"{WIN_COINS} {EMOJI['coin']} گرفتی!\nبرای بازی دوباره بنویس «حدس عدد»"
        )
        del guess_numbers[chat_id]
    elif guess < game["number"]:
        await update.message.reply_text("⬆️ عدد بزرگ‌تری بگو!")
    else:
        await update.message.reply_text("⬇️ عدد کوچیک‌تری بگو!")
    return True


# ================= دار (تک‌نفره، با ۱۰۰ کلمه و ۲ راهنما) =================
from hangman_words import HANGMAN_WORDS
HANGMAN_STAGES = ["🙂", "😐", "😟", "😨", "😰", "💀"]
MAX_HINTS = 2


async def start_hangman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    entry = random.choice(HANGMAN_WORDS)
    hangman_games[chat_id] = {
        "word": entry["word"], "hints": entry["hints"], "hints_used": 0,
        "guessed": set(), "wrong": 0, "player": update.effective_user.id,
    }
    display = " ".join("_" for _ in entry["word"])
    await update.message.reply_text(
        f"🪢 بازی دار شروع شد! یه حرف فارسی بفرست حدس بزنی.\n"
        f"اگه گیر کردی، بنویس «راهنمایی» (حداکثر {MAX_HINTS} بار می‌تونی ازش استفاده کنی):\n\n"
        f"{display}\n\n{HANGMAN_STAGES[0]}"
    )


async def handle_hangman_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_id = update.effective_chat.id
    game = hangman_games.get(chat_id)
    text = update.message.text
    if not game or not text:
        return False

    stripped = text.strip()

    # درخواست راهنمایی
    if stripped == "راهنمایی":
        if game["hints_used"] >= MAX_HINTS:
            await update.message.reply_text(f"{EMOJI['warn']} دیگه راهنمایی نداری، خودت باید حدس بزنی 😄")
        else:
            hint_text = game["hints"][game["hints_used"]]
            game["hints_used"] += 1
            await update.message.reply_text(
                f"💡 راهنمایی {game['hints_used']} از {MAX_HINTS}:\n{hint_text}"
            )
        return True

    if len(stripped) != 1:
        return False

    letter = stripped
    word = game["word"]
    if letter in game["guessed"]:
        await update.message.reply_text("قبلاً این حرف رو گفتی 🙂")
        return True

    game["guessed"].add(letter)
    if letter not in word:
        game["wrong"] += 1
        if game["wrong"] >= len(HANGMAN_STAGES) - 1:
            record_game_result(game["player"], "hangman", False)
            await update.message.reply_text(f"💀 باختی! کلمه «{word}» بود.\nبرای بازی دوباره بنویس «دار»")
            del hangman_games[chat_id]
            return True

    display = " ".join(c if c in game["guessed"] else "_" for c in word)
    if "_" not in display:
        record_game_result(game["player"], "hangman", True)
        add_coins(game["player"], WIN_COINS)
        await update.message.reply_text(f"🎉 آفرین! کلمه «{word}» درست بود و {WIN_COINS} {EMOJI['coin']} گرفتی!")
        del hangman_games[chat_id]
        return True

    await update.message.reply_text(f"{display}\n\n{HANGMAN_STAGES[game['wrong']]}")
    return True

