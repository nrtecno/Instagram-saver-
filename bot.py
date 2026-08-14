import os, time, glob, threading
import yt_dlp
import telebot
from flask import Flask, request
from telebot import types

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")
try:
    ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else None
except: ADMIN_ID = None

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
CHANNEL_USERNAME = "@nrtecno2"
CHANNEL_LINK = "https://t.me/nrtecno2"
app = Flask(__name__)

# Auto cleanup 3 min
def auto_cleanup():
    while True:
        time.sleep(180)
        for f in glob.glob("*.mp4") + glob.glob("*.mp3") + glob.glob("*.jpg") + glob.glob("*.mkv") + glob.glob("*.webm") + glob.glob("*.m4a"):
            try:
                if os.path.exists(f) and (time.time() - os.path.getctime(f) > 180): os.remove(f)
            except: pass
threading.Thread(target=auto_cleanup, daemon=True).start()

def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

# Dictionary to store user links for quality selection
user_links = {}

@bot.message_handler(commands=['start'])
def start_handler(message):
    if not is_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Join Our Channel 💎", url=CHANNEL_LINK))
        markup.add(types.InlineKeyboardButton("✅ I Joined - Check Now 🔥", callback_data="check_join"))
        bot.send_message(message.chat.id, f"👋 **ALL-IN-ONE DOWNLOADER BOT**\n\n⚠️ Join {CHANNEL_USERNAME} to use bot.\n\n📥 Supported:\n• Instagram Reels/Post/Story\n• YouTube (with Quality)\n• Facebook Reels/Video\n• Twitter (X) Videos", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "👋 Welcome Back!\n\n📥 Send me link from:\n• Instagram\n• YouTube\n• Facebook\n• Twitter (X)\n\nFor YouTube you will get Quality Option.", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id

    # Join Check Button
    if call.data == "check_join":
        if is_user_joined(user_id):
            bot.edit_message_text("✅ Thanks for joining!\n\n📩 Now send any link.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Not joined yet!", show_alert=True)
        return

    # YouTube Quality Selection
    if call.data.startswith("yt_"):
        if user_id not in user_links:
            bot.answer_callback_query(call.id, "Link expired, send again.")
            return

        url = user_links[user_id]
        quality = call.data

        bot.edit_message_text(f"⏳ Downloading in **{quality}**... Please wait.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        download_video(call.message, url, quality)

def download_video(message, url, quality_code="best"):
    chat_id = message.chat.id if hasattr(message, 'chat') else message.chat.id
    # YT-DLP options based on quality
    if quality_code == "yt_360": ydl_format = "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]"
    elif quality_code == "yt_720": ydl_format = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]"
    elif quality_code == "yt_1080": ydl_format = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]"
    elif quality_code == "yt_mp3": ydl_format = "bestaudio/best"
    else: ydl_format = "best"

    # For mp3
    if quality_code == "yt_mp3":
        ydl_opts = {'format': ydl_format, 'outtmpl': '%(id)s.%(ext)s', 'quiet': True, 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]}
    else:
        ydl_opts = {'format': ydl_format, 'outtmpl': '%(id)s.%(ext)s', 'quiet': True, 'merge_output_format': 'mp4'}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Fix mp3 filename
            if quality_code == "yt_mp3":
                base = os.path.splitext(filename)[0]
                if os.path.exists(base + ".mp3"): filename = base + ".mp3"

        caption = f"✅ Downloaded\nQuality: {quality_code}\n🔗 Join: {CHANNEL_USERNAME}"
        with open(filename, 'rb') as f:
            if filename.endswith('.mp3') or filename.endswith('.m4a'): bot.send_audio(chat_id, f, caption=caption)
            elif filename.endswith(('.mp4','.mkv','.mov','.webm')): bot.send_video(chat_id, f, caption=caption)
            else: bot.send_document(chat_id, f, caption=caption)

        if os.path.exists(filename): os.remove(filename)
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(chat_id, "❌ Failed to download. Video private or link incorrect ho sakta hai.")

@bot.message_handler(func=lambda m: True)
def handle_link(message):
    text = message.text.strip()
    if not any(x in text for x in ["instagram.com", "youtube.com", "youtu.be", "facebook.com", "fb.watch", "twitter.com", "x.com", "tiktok.com"]):
        return

    if not is_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Join Channel to Unlock 💎", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, f"🚫 Bot Locked\n\nJoin {CHANNEL_USERNAME} first.", reply_markup=markup)
        return

    url = text

    # IF YOUTUBE -> SHOW QUALITY BUTTONS
    if "youtube.com" in url or "youtu.be" in url:
        user_links[message.from_user.id] = url
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🎬 360p", callback_data="yt_360"),
            types.InlineKeyboardButton("🔥 720p HD", callback_data="yt_720"),
            types.InlineKeyboardButton("💎 1080p Full HD", callback_data="yt_1080"),
            types.InlineKeyboardButton("🚀 Best Quality", callback_data="yt_best"),
            types.InlineKeyboardButton("🎵 MP3 Audio Only", callback_data="yt_mp3")
        )
        bot.send_message(message.chat.id, "🎬 **YouTube Link Detected**\n\nSelect quality:", reply_markup=markup, parse_mode="Markdown")
    else:
        # For Insta / FB / Twitter -> Direct Download
        msg = bot.send_message(message.chat.id, "⏳ Downloading... Please wait.")
        download_video(msg, url, "best")
        try: bot.delete_message(message.chat.id, msg.message_id)
        except: pass

@app.route('/')
def home(): return "All-in-One Bot Alive!"
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return ''
if __name__ == "__main__":
    bot.remove_webhook(); time.sleep(1)
    if WEBHOOK_URL: bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
