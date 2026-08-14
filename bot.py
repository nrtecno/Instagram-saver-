import os
import re
import time
import glob
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN") # Render pe yahi use hoga
CHANNEL_USERNAME = "@nrtecno2"
CHANNEL_LINK = "https://t.me/nrtecno2"

logging.basicConfig(level=logging.INFO)

# --- 1. Channel Join Check ---
async def is_user_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return True # Agar bot admin nahi hai to error na de

# --- 2. Auto-Delete Function (Har 3 min) ---
async def auto_cleanup(context: ContextTypes.DEFAULT_TYPE):
    print("Cleaning storage...")
    files = glob.glob("*.mp4") + glob.glob("*.jpg") + glob.glob("*.mkv") + glob.glob("*.webm") + glob.glob("*.mp3")
    for f in files:
        # 3 minute = 180 second purani file delete
        if os.path.exists(f) and (time.time() - os.path.getctime(f) > 180):
            os.remove(f)
            print(f"Deleted: {f}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_joined(update, context):
        keyboard = [[InlineKeyboardButton("📢 Channel Join Karo", url=CHANNEL_LINK)], [InlineKeyboardButton("✅ Check Joined", callback_data="check_join")]]
        await update.message.reply_text(f"⚠️ Pehle {CHANNEL_USERNAME} join karna compulsory hai.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    await update.message.reply_text("👋 Link bhejo! Main Quality options dunga.\n\nReels / Posts / Stories sab chalega.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_joined(update, context):
        await update.message.reply_text(f"Pehle {CHANNEL_USERNAME} join karo.")
        return

    url = update.message.text.strip()
    if "instagram.com" not in url:
        return

    context.user_data['last_url'] = url # URL save kar liya

    # User ko Quality buttons dikhao
    keyboard = [
        [InlineKeyboardButton("Low - 360p", callback_data="q_360"), InlineKeyboardButton("Medium - 480p", callback_data="q_480")],
        [InlineKeyboardButton("HD - 720p", callback_data="q_720"), InlineKeyboardButton("Full HD - 1080p", callback_data="q_1080")],
        [InlineKeyboardButton("Best Quality - 8K/4K", callback_data="q_best")]
    ]
    await update.message.reply_text("👇 Kis Quality me download karna hai?", reply_markup=InlineKeyboardMarkup(keyboard))

async def quality_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_join":
        if await is_user_joined(update, context):
            await query.edit_message_text("✅ Joined! Ab link bhejo.")
        else:
            await query.answer("❌ Join nahi kiya abhi tak!", show_alert=True)
        return

    url = context.user_data.get('last_url')
    if not url:
        await query.edit_message_text("Link expire ho gaya, dobara bhejo.")
        return

    quality = query.data.split("_")[1] # 360, 720, best
    await query.edit_message_text(f"⏳ {quality} Quality me download kar raha hu...")

    # Quality mapping
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
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        caption = f"✅ {quality} me Downloaded\nJoin: {CHANNEL_USERNAME}"
        if filename.endswith(('.mp4','.mkv','.mov','.webm')):
            await context.bot.send_video(chat_id=query.message.chat_id, video=open(filename, 'rb'), caption=caption)
        else:
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(filename, 'rb'), caption=caption)

        # Turant delete
        if os.path.exists(filename):
            os.remove(filename)
        await query.delete()

    except Exception as e:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"❌ Fail ho gaya: {e}")

if __name__ == '__main__':
    # Flask server for Render (Bot ko alive rakhne ke liye)
    from threading import Thread
    from flask import Flask
    app_flask = Flask('')
    @app_flask.route('/')
    def home(): return "Bot is Alive!"
    def run_flask(): app_flask.run(host='0.0.0.0', port=8080)
    Thread(target=run_flask).start()

    # Telegram Bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(quality_download))

    # Har 3 minute me cleanup job
    app.job_queue.run_repeating(auto_cleanup, interval=180, first=10)

    print("Bot Started...")
    app.run_polling()
