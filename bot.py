import os, time, glob, threading
import yt_dlp
import telebot
from flask import Flask, request
from telebot import types

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
CHANNEL_USERNAME = "@nrtecno2"
CHANNEL_LINK = "https://t.me/nrtecno2"

app = Flask(__name__)
user_links = {}

def is_user_joined(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ['member', 'administrator', 'creator']
    except:
        return False

def get_ydl_opts(quality):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'outtmpl': '%(id)s.%(ext)s',
        'merge_output_format': 'mp4',
        'noplaylist': True,
    }
    # Cookies file agar hai to auto use hogi
    if os.path.exists("cookies.txt"):
        opts['cookiefile'] = 'cookies.txt'

    if quality == "yt_360":
        opts['format'] = "bestvideo[height<=360][ext=mp4]+bestaudio/best[height<=360]/best"
    elif quality == "yt_720":
        opts['format'] = "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720]/best"
    elif quality == "yt_1080":
        opts['format'] = "bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080]/best"
    elif quality == "yt_mp3":
        opts['format'] = "bestaudio/best"
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else: # yt_best and insta/fb
        opts['format'] = "bestvideo[ext=mp4]+bestaudio/best/best"

    return opts

def do_download(chat_id, url, quality, status_id):
    filename = None
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(quality)) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if quality == "yt_mp3":
                base = os.path.splitext(filename)[0]
                # mp3 conversion ke baad naam badal jata hai
                mp3_file = base + ".mp3"
                if os.path.exists(mp3_file):
                    filename = mp3_file

        caption = f"✅ Downloaded\nJoin {CHANNEL_USERNAME}"
        with open(filename, 'rb') as f:
            if filename.endswith(('.mp3', '.m4a', '.webm')):
                bot.send_audio(chat_id, f, caption=caption)
            else:
                bot.send_video(chat_id, f, caption=caption, supports_streaming=True)

        if os.path.exists(filename):
            os.remove(filename)
        try: bot.delete_message(chat_id, status_id)
        except: pass

    except Exception as e:
        print(f"ERROR: {e}")
        try:
            bot.edit_message_text(f"❌ Failed: {e}", chat_id, status_id)
        except: pass
        # cleanup
        if filename and os.path.exists(filename):
            try: os.remove(filename)
            except: pass
        for f in glob.glob("*.mp4") + glob.glob("*.mp3") + glob.glob("*.webm") + glob.glob("*.m4a"):
            try: os.remove(f)
            except: pass

@bot.message_handler(commands=['start'])
def start_h(m):
    if not is_user_joined(m.from_user.id):
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("💎 Join Channel 💎", url=CHANNEL_LINK))
        mk.add(types.InlineKeyboardButton("✅ Check Now", callback_data="check_join"))
        bot.send_message(m.chat.id, f"👋 Bot use karne ke liye {CHANNEL_USERNAME} join karo.", reply_markup=mk)
    else:
        bot.send_message(m.chat.id, "👋 Ready! YouTube / Insta / FB ka link bhejo.")

@bot.callback_query_handler(func=lambda c: True)
def cb_h(call):
    if call.data == "check_join":
        if is_user_joined(call.from_user.id):
            bot.edit_message_text("✅ Joined! Ab link bhejo.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Abhi join nahi kiya!", show_alert=True)
        return

    if call.data.startswith("yt_"):
        url = user_links.get(call.from_user.id)
        if not url:
            bot.answer_callback_query(call.id, "Link expire ho gaya, dobara bhejo.")
            return
        bot.edit_message_text(f"⏳ Downloading {call.data}...", call.message.chat.id, call.message.message_id)
        threading.Thread(target=do_download, args=(call.message.chat.id, url, call.data, call.message.message_id)).start()

@bot.message_handler(func=lambda m: True)
def link_h(message):
    txt = message.text.strip()
    if "instagram.com" not in txt and "youtu" not in txt and "facebook.com" not in txt and "fb.watch" not in txt and "twitter.com" not in txt and "x.com" not in txt:
        return

    if not is_user_joined(message.from_user.id):
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("💎 Join Channel 💎", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, "🚫 Pehle channel join karo.", reply_markup=mk)
        return

    if "youtu" in txt:
        user_links[message.from_user.id] = txt
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("360p", callback_data="yt_360"),
            types.InlineKeyboardButton("720p", callback_data="yt_720"),
            types.InlineKeyboardButton("1080p", callback_data="yt_1080"),
            types.InlineKeyboardButton("Best", callback_data="yt_best"),
            types.InlineKeyboardButton("MP3 🎵", callback_data="yt_mp3")
        )
        bot.send_message(message.chat.id, "🎬 YouTube - Quality Select Karo:", reply_markup=mk)
    else:
        s = bot.send_message(message.chat.id, "⏳ Downloading...")
        threading.Thread(target=do_download, args=(message.chat.id, txt, "yt_best", s.message_id)).start()

@app.route('/')
def home(): return "Bot Alive ✅"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return ''

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    if WEBHOOK_URL:
        bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
