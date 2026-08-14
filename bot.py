import os
import time
import glob
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "@nrtecno2"
CHANNEL_LINK = "https://t.me/nrtecno2"

logging.basicConfig(level=logging.INFO)

# 1. Check if user joined channel
async def is_user_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Join check error: {e}")
        return True

# 2. Auto-Delete Job - Runs every 3 minutes
async def auto_cleanup(context: ContextTypes.DEFAULT_TYPE):
    print("Cleaning storage...")
    files = glob.glob("*.mp4") + glob.glob("*.jpg") + glob.glob("*.mkv") + glob.glob("*.webm") + glob.glob("*.mp3") + glob.glob("*.m4a")
    for f in files:
        try:
            if os.path.exists(f) and (time.time() - os.path.getctime(f) > 180):
                os.remove(f)
                print(f"Deleted: {f}")
        except Exception as e:
            print(f"Error deleting {f}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_joined(update, context):
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ I Joined - Check", callback_data="check_join")]
        ]
        await update.message.reply_text(
            f"⚠️ To use this bot, you must join our channel {CHANNEL_USERNAME} first.\n\nAfter joining, click on 'I Joined - Check'.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    await update.message.reply_text(
        "👋 Welcome!\n\nSend me any Instagram Reels / Posts / Stories link and I will download it for you in your desired quality."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_joined(update, context):
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]]
        await update.message.reply_text(f"Please join {CHANNEL_USERNAME} first to use the bot.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    url = update.message.text.strip()
    if "instagram.com" not in url:
        await update.message.reply_text("Please send a valid Instagram link.")
        return

    context.user_data['last_url'] = url

    keyboard = [
        [InlineKeyboardButton("Low - 360p", callback_data="q_360"), InlineKeyboardButton("Medium - 480p", callback_data="q_480")],
        [InlineKeyboardButton("HD - 720p", callback_data="q_720"), InlineKeyboardButton("Full HD - 1080p", callback_data="q_1080")],
        [InlineKeyboardButton("Best Quality - 8K/4K", callback_data="q_best")]
    ]
    await update.message.reply_text("👇 Select download quality:", reply_markup=InlineKeyboardMarkup(keyboard))

async def quality_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_join":
        if await is_user_joined(update, context):
            await query.edit_message_text("✅ Thank you for joining! Now you can send me any Instagram link.")
        else:
            await query.answer("❌ You haven't joined yet! Please join first.", show_alert=True)
        return

    url = context.user_data.get('last_url')
    if not url:
        await query.edit_message_text("Link expired. Please send the link again.")
        return

    quality = query.data.split("_")[1]
    await query.edit_message_text(f"⏳ Downloading in {quality} quality, please wait...")

    format_map = {
        "360": "best[height<=360]",
        "480": "best[height<=480]",
        "720": "best[height<=720]",
        "1080": "best[height<=1080]",
        "best": "best"
    }

    ydl_opts = {
        'format': format_map.get(quality, 'best'),
        'outtmpl': '%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        caption = f"✅ Downloaded in {quality} quality\nBot by @{context.bot.username}\nJoin: {CHANNEL_USERNAME}"
        if filename.endswith(('.mp4','.mkv','.mov','.webm')):
            await context.bot.send_video(chat_id=query.message.chat_id, video=open(filename, 'rb'), caption=caption)
        else:
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(filename, 'rb'), caption=caption)

        if os.path.exists(filename):
            os.remove(filename)
        await query.delete()

    except Exception as e:
        print(f"Download Error: {e}")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"❌ Failed to download. The post might be private.\nError: {e}")

if __name__ == '__main__':
    from threading import Thread
    from flask import Flask

    app_flask = Flask('')
    @app_flask.route('/')
    def home(): return "Bot is Alive!"

    def run_flask():
        port = int(os.environ.get("PORT", 8080))
        app_flask.run(host='0.0.0.0', port=port)

    Thread(target=run_flask).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(quality_download))

    # Auto delete every 3 minutes (180 seconds)
    app.job_queue.run_repeating(auto_cleanup, interval=180, first=10)

    print("Bot Started...")
    app.run_polling()
