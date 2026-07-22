import os
import asyncio
import logging
import tempfile
import uuid

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    EMOJI, FONT_CANDIDATES, FONT_LABELS, GIF_COLOR_OPTIONS, GIF_COLOR_LABELS,
    GIF_SIZE_PRESETS, GIF_SIZE_LABELS, GIF_EXACT_SIZE_MIN, GIF_EXACT_SIZE_MAX,
    GIF_POSITION_LABELS, GIF_MAX_FRAMES, GIF_MAX_WIDTH,
    GIF_MAX_CONCURRENT_JOBS, GIF_PROCESS_TIMEOUT_SECONDS,
)

log = logging.getLogger("gapbot.gifmaker")

# session ساده برای هر کاربر: مرحله‌به‌مرحله انتخاب‌هاش رو نگه می‌داره
gif_sessions = {}

# ضد کد هنگی: حداکثر N ساخت گیف هم‌زمان (چون پردازش تصویر/ویدیو سنگینه)
_gif_semaphore = asyncio.Semaphore(GIF_MAX_CONCURRENT_JOBS)


def _find_font_path(font_key: str) -> str:
    for path in FONT_CANDIDATES.get(font_key, []):
        if os.path.exists(path):
            return path
    return FONT_CANDIDATES.get(font_key, [""])[-1]


def _shape_persian(text: str) -> str:
    """حروف فارسی/عربی رو به هم می‌چسبونه و راست‌به‌چپ می‌کنه تا درست نمایش داده بشه"""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def _resolve_font_size(frame_height: int, size_value) -> int:
    """size_value یا یه کلید پیش‌فرض (small/medium/large)ه یا یه عدد دقیق پیکسل"""
    if isinstance(size_value, int):
        return max(GIF_EXACT_SIZE_MIN, min(GIF_EXACT_SIZE_MAX, size_value))
    ratio = GIF_SIZE_PRESETS.get(size_value, 0.08)
    return max(12, int(frame_height * ratio))


def _text_xy(frame_w, frame_h, text_w, text_h, position: str):
    vert, horiz = position.split("_")  # مثلاً "top_left" -> vert="top", horiz="left"
    pad_x, pad_y = frame_w * 0.03, frame_h * 0.03

    if horiz == "left":
        x = pad_x
    elif horiz == "right":
        x = frame_w - text_w - pad_x
    else:  # center
        x = (frame_w - text_w) / 2

    if vert == "top":
        y = pad_y
    elif vert == "bottom":
        y = frame_h - text_h - pad_y
    else:  # middle
        y = (frame_h - text_h) / 2

    return x, y


def _draw_text_on_frame(frame: Image.Image, text: str, position: str, font_key: str,
                         size_value, color_key: str, outline_enabled: bool, outline_color_key: str) -> Image.Image:
    frame = frame.convert("RGBA")
    draw = ImageDraw.Draw(frame)

    font_size = _resolve_font_size(frame.height, size_value)
    font_path = _find_font_path(font_key)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    display_text = _shape_persian(text)
    bbox = draw.textbbox((0, 0), display_text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = _text_xy(frame.width, frame.height, text_w, text_h, position)

    color = GIF_COLOR_OPTIONS.get(color_key, (255, 255, 255))

    if outline_enabled:
        outline = GIF_COLOR_OPTIONS.get(outline_color_key, (0, 0, 0))
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            draw.text((x + dx, y + dy), display_text, font=font, fill=outline)

    draw.text((x, y), display_text, font=font, fill=color)
    return frame


def _resize_if_needed(frame: Image.Image) -> Image.Image:
    if frame.width > GIF_MAX_WIDTH:
        ratio = GIF_MAX_WIDTH / frame.width
        frame = frame.resize((GIF_MAX_WIDTH, int(frame.height * ratio)))
    return frame


def _build_gif_from_photo_sync(input_path, output_path, opts):
    img = Image.open(input_path)
    img = _resize_if_needed(img)
    img = _draw_text_on_frame(
        img, opts["text"], opts["position"], opts["font"], opts["size"],
        opts["color"], opts["outline_enabled"], opts.get("outline_color"),
    )
    img.convert("RGB").save(output_path, format="GIF")


def _build_gif_from_animation_sync(input_path, output_path, opts):
    """برای گیف/ویدیوی ورودی: فریم‌ها رو استخراج، روش متن می‌کشه، دوباره به گیف تبدیل می‌کنه"""
    import imageio.v3 as iio

    is_video = input_path.lower().endswith((".mp4", ".webm", ".mov", ".mkv"))
    frames_raw = iio.imread(input_path, plugin="pyav") if is_video else iio.imread(input_path, index=None)

    if frames_raw.ndim == 3:
        # فقط یه فریم بود (تصویر ساده)
        img = Image.fromarray(frames_raw)
        img = _resize_if_needed(img)
        img = _draw_text_on_frame(
            img, opts["text"], opts["position"], opts["font"], opts["size"],
            opts["color"], opts["outline_enabled"], opts.get("outline_color"),
        )
        img.convert("RGB").save(output_path, format="GIF")
        return

    total = len(frames_raw)
    step = max(1, total // GIF_MAX_FRAMES)
    selected = frames_raw[::step][:GIF_MAX_FRAMES]

    processed = []
    for arr in selected:
        img = Image.fromarray(arr)
        img = _resize_if_needed(img)
        img = _draw_text_on_frame(
            img, opts["text"], opts["position"], opts["font"], opts["size"],
            opts["color"], opts["outline_enabled"], opts.get("outline_color"),
        )
        processed.append(img.convert("RGB"))

    processed[0].save(
        output_path, format="GIF", save_all=True, append_images=processed[1:],
        duration=80, loop=0, optimize=True,
    )


async def _run_gif_build(is_animated: bool, input_path: str, output_path: str, opts: dict):
    """
    اجرای ساخت گیف در یه ترد جدا (چون CPU-bound و سنگینه) + محدودیت هم‌زمانی + تایم‌اوت.
    این جلوی هنگ کردن کل بات (event loop) رو موقع پردازش تصویر/ویدیو می‌گیره.
    """
    async with _gif_semaphore:
        target = _build_gif_from_animation_sync if is_animated else _build_gif_from_photo_sync
        await asyncio.wait_for(
            asyncio.to_thread(target, input_path, output_path, opts),
            timeout=GIF_PROCESS_TIMEOUT_SECONDS,
        )


# ================= جریان مکالمه (مرحله‌به‌مرحله) =================
def _position_keyboard():
    keys = list(GIF_POSITION_LABELS.keys())
    rows = [
        [InlineKeyboardButton(GIF_POSITION_LABELS[keys[r * 3 + c]], callback_data=f"gifpos:{keys[r*3+c]}") for c in range(3)]
        for r in range(3)
    ]
    return InlineKeyboardMarkup(rows)


async def _start_flow(user_id: int, send_func):
    gif_sessions[user_id] = {"step": "position"}
    await send_func("🎬 بریم گیف بسازیم! اول بگو متن کجای عکس/فیلم باشه:", _position_keyboard())


async def start_gif_maker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ورودی از طریق تایپ متنی «ساخت گیف»"""
    await _start_flow(update.effective_user.id, lambda text, kb: update.message.reply_text(text, reply_markup=kb))


async def start_gif_maker_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ورودی از طریق دکمه‌ی اینلاین «ساخت گیف» (مثلاً بعد از تأیید عضویت در پیوی)"""
    query = update.callback_query
    await query.answer()
    await _start_flow(query.from_user.id, lambda text, kb: query.message.reply_text(text, reply_markup=kb))


async def position_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in gif_sessions:
        await query.answer("یه دفعه‌ی دیگه بنویس «ساخت گیف» تا از اول شروع کنیم 🙂", show_alert=True)
        return
    await query.answer()
    position = query.data.split(":")[1]
    gif_sessions[user_id]["position"] = position
    gif_sessions[user_id]["step"] = "font"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"giffont:{key}")] for key, label in FONT_LABELS.items()]
    )
    await query.edit_message_text("فونت متن رو انتخاب کن:", reply_markup=keyboard)


async def font_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in gif_sessions:
        await query.answer("یه دفعه‌ی دیگه بنویس «ساخت گیف» 🙂", show_alert=True)
        return
    await query.answer()
    font_key = query.data.split(":")[1]
    gif_sessions[user_id]["font"] = font_key
    gif_sessions[user_id]["step"] = "size"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"gifsize:{key}")] for key, label in GIF_SIZE_LABELS.items()]
    )
    await query.edit_message_text("سایز متن چقدر باشه؟", reply_markup=keyboard)


async def size_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in gif_sessions:
        await query.answer("یه دفعه‌ی دیگه بنویس «ساخت گیف» 🙂", show_alert=True)
        return
    await query.answer()
    size_key = query.data.split(":")[1]

    if size_key == "exact":
        gif_sessions[user_id]["step"] = "await_exact_size"
        await query.edit_message_text(
            f"عدد سایز دقیق (بین {GIF_EXACT_SIZE_MIN} تا {GIF_EXACT_SIZE_MAX} پیکسل) رو بفرست:"
        )
        return

    gif_sessions[user_id]["size"] = size_key
    await _ask_outline_choice(query)


async def _ask_outline_choice(query):
    user_id = query.from_user.id
    gif_sessions[user_id]["step"] = "outline_choice"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ بله، خط دور داشته باشه", callback_data="gifoutline:yes"),
        InlineKeyboardButton("❌ نه، خط دور نمی‌خوام", callback_data="gifoutline:no"),
    ]])
    await query.edit_message_text("دور نوشته خط (حاشیه) داشته باشه یا نه؟", reply_markup=keyboard)


async def outline_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in gif_sessions:
        await query.answer("یه دفعه‌ی دیگه بنویس «ساخت گیف» 🙂", show_alert=True)
        return
    await query.answer()
    choice = query.data.split(":")[1]

    if choice == "no":
        gif_sessions[user_id]["outline_enabled"] = False
        gif_sessions[user_id]["step"] = "color"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(label, callback_data=f"gifcolor:{key}")] for key, label in GIF_COLOR_LABELS.items()]
        )
        await query.edit_message_text("رنگ متن چی باشه؟", reply_markup=keyboard)
        return

    gif_sessions[user_id]["outline_enabled"] = True
    gif_sessions[user_id]["step"] = "outline_color"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"gifoutlinecolor:{key}")] for key, label in GIF_COLOR_LABELS.items()]
    )
    await query.edit_message_text("رنگ خط دور نوشته چی باشه؟", reply_markup=keyboard)


async def outline_color_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in gif_sessions:
        await query.answer("یه دفعه‌ی دیگه بنویس «ساخت گیف» 🙂", show_alert=True)
        return
    await query.answer()
    gif_sessions[user_id]["outline_color"] = query.data.split(":")[1]
    gif_sessions[user_id]["step"] = "color"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"gifcolor:{key}")] for key, label in GIF_COLOR_LABELS.items()]
    )
    await query.edit_message_text("رنگ خود متن چی باشه؟", reply_markup=keyboard)


async def color_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in gif_sessions:
        await query.answer("یه دفعه‌ی دیگه بنویس «ساخت گیف» 🙂", show_alert=True)
        return
    await query.answer()
    color_key = query.data.split(":")[1]
    gif_sessions[user_id]["color"] = color_key
    gif_sessions[user_id]["step"] = "await_text"

    await query.edit_message_text("عالی! حالا متنی که می‌خوای روی گیف باشه رو بفرست ✍️")


async def handle_gif_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگه کاربر تو مرحله‌ی «منتظر متن» یا «منتظر سایز دقیق» باشه، این پیام رو مصرف می‌کنه."""
    user_id = update.effective_user.id
    session = gif_sessions.get(user_id)
    if not session or not update.message.text:
        return False

    step = session.get("step")

    if step == "await_exact_size":
        text = update.message.text.strip()
        if not text.isdigit() or not (10 <= int(text) <= 200):
            await update.message.reply_text(f"{EMOJI['warn']} یه عدد بین {GIF_EXACT_SIZE_MIN} تا {GIF_EXACT_SIZE_MAX} بفرست.")
            return True
        session["size"] = int(text)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ بله، خط دور داشته باشه", callback_data="gifoutline:yes"),
            InlineKeyboardButton("❌ نه، خط دور نمی‌خوام", callback_data="gifoutline:no"),
        ]])
        session["step"] = "outline_choice"
        await update.message.reply_text("دور نوشته خط (حاشیه) داشته باشه یا نه؟", reply_markup=keyboard)
        return True

    if step == "await_text":
        session["text"] = update.message.text.strip()
        session["step"] = "await_media"
        await update.message.reply_text(
            f"{EMOJI['check']} متن ثبت شد! حالا عکس، فیلم یا گیفی که می‌خوای روش این متن بیاد رو بفرست 📎"
        )
        return True

    return False


ANIMATED_MIME_TYPES = ("image/gif", "video/mp4", "video/webm", "video/quicktime", "video/x-matroska")
STATIC_MIME_TYPES = ("image/jpeg", "image/png", "image/webp", "image/bmp")


async def handle_gif_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگه کاربر تو مرحله‌ی «منتظر رسانه» باشه، عکس/ویدیو/گیف/استیکر رو پردازش می‌کنه."""
    user_id = update.effective_user.id
    session = gif_sessions.get(user_id)
    if not session or session.get("step") != "await_media":
        return False

    message = update.message
    file_obj = None
    is_animated = False

    if message.photo:
        file_obj = await message.photo[-1].get_file()
    elif message.animation:
        file_obj = await message.animation.get_file()
        is_animated = True
    elif message.video:
        file_obj = await message.video.get_file()
        is_animated = True
    elif message.video_note:
        file_obj = await message.video_note.get_file()
        is_animated = True
    elif message.sticker and not message.sticker.is_animated and not message.sticker.is_video:
        file_obj = await message.sticker.get_file()
    elif message.document:
        mime = message.document.mime_type or ""
        if mime in ANIMATED_MIME_TYPES:
            file_obj = await message.document.get_file()
            is_animated = True
        elif mime in STATIC_MIME_TYPES:
            file_obj = await message.document.get_file()
        else:
            await message.reply_text(f"{EMOJI['warn']} این فرمت فایل پشتیبانی نمی‌شه. عکس، گیف یا ویدیو بفرست.")
            return True
    else:
        await message.reply_text(f"{EMOJI['warn']} باید عکس، فیلم یا گیف بفرستی.")
        return True

    await message.reply_text("⏳ دارم گیفتو می‌سازم، چند لحظه صبر کن...")

    with tempfile.TemporaryDirectory() as tmpdir:
        ext = os.path.splitext(file_obj.file_path or "")[1] or (".mp4" if is_animated else ".jpg")
        input_path = os.path.join(tmpdir, f"input_{uuid.uuid4().hex}{ext}")
        output_path = os.path.join(tmpdir, f"output_{uuid.uuid4().hex}.gif")

        opts = {
            "text": session["text"], "position": session["position"], "font": session["font"],
            "size": session["size"], "color": session["color"],
            "outline_enabled": session.get("outline_enabled", False),
            "outline_color": session.get("outline_color"),
        }

        try:
            await file_obj.download_to_drive(input_path)
            await _run_gif_build(is_animated, input_path, output_path, opts)
            with open(output_path, "rb") as f:
                await message.reply_animation(f, caption="🎉 گیفت آماده‌ست!")
        except asyncio.TimeoutError:
            await message.reply_text(f"{EMOJI['cross']} پردازش این فایل خیلی طول کشید و لغو شد. یه فایل کوچیک‌تر امتحان کن.")
        except Exception as e:
            log.exception("خطا در ساخت گیف")
            await message.reply_text(f"{EMOJI['cross']} یه مشکلی پیش اومد و نتونستم گیف بسازم: {e}")

    gif_sessions.pop(user_id, None)
    return True
