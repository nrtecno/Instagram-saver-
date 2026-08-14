import os, time, glob, threading, json
import yt_dlp
import telebot
from flask import Flask, request
from telebot import types

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")
bot = telebot.TeleBot(BOT_TOKEN, threaded=True) # Threaded True kiya - ab atake ga nahi
CHANNEL_USERNAME = "@nrtecno2"
CHANNEL_LINK = "https://t.me/nrtecno2"
app = Flask(__name__)
user_links = {}

def is_user_joined(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ['member','administrator','creator']
    except: return False

def get_ydl_opts(quality):
    # Base opts - Instagram ke liye special header
    base = {
        'quiet': True,
        'no_warnings': True,
        'outtmpl': '%(id)s.%(ext)s',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'extractor_args': {'instagram': {'api_version': 'v1'}},
    }
    if quality == "yt_360": base['format'] = "bestvideo[height<=360][ext=mp4]+bestaudio/best[height<=360]"
    elif quality == "yt_720": base['format'] = "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720]"
    elif quality == "yt_1080": base['format'] = "bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080]"
    elif quality == "yt_mp3":
        base['format'] = "bestaudio/best"
        base['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
    else: base['format'] = "bestvideo[ext=mp4]+bestaudio/best/best"
    base['merge_output_format'] = 'mp4'
    return base

def do_download(chat_id, url, quality, status_id):
    try:
        opts = get_ydl_opts(quality)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if quality == "yt_mp3":
                base = os.path.splitext(filename)[0]
                if os.path.exists(base+".mp3"): filename = base+".mp3"

        cap = f"✅ Downloaded\nQuality: {quality}\nJoin: {CHANNEL_USERNAME}"
        with open(filename, 'rb') as f:
            if filename.endswith(('.mp3','m4a')): bot.send_audio(chat_id, f, caption=cap)
            elif filename.endswith(('.mp4','.mkv','.mov')): bot.send_video(chat_id, f, caption=cap, supports_streaming=True)
            else: bot.send_document(chat_id, f, caption=cap)
        if os.path.exists(filename): os.remove(filename)
        try: bot.delete_message(chat_id, status_id)
        except: pass
    except Exception as e:
        print(f"DL Error: {e}")
        try: bot.edit_message_text(f"❌ Failed: {str(e)[:150]}\n\nInsta private hai to nahi hoga. YT ke liye dusri quality try karo.", chat_id, status_id)
        except: bot.send_message(chat_id, "❌ Download failed.")

@bot.message_handler(commands=['start'])
def start_h(m):
    if not is_user_joined(m.from_user.id):
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("💎 Join Channel 💎", url=CHANNEL_LINK))
        mk.add(types.InlineKeyboardButton("✅ Check Now", callback_data="check_join"))
        bot.send_message(m.chat.id, f"Join {CHANNEL_USERNAME} to use bot.", reply_markup=mk)
    else:
        bot.send_message(m.chat.id, "👋 Ready!\nSend Insta / YT / FB / X link.")

@bot.callback_query_handler(func=lambda c: True)
def cb_h(call):
    if call.data == "check_join":
        if is_user_joined(call.from_user.id): bot.edit_message_text("✅ Joined! Now send link.", call.message.chat.id, call.message.message_id)
        else: bot.answer_callback_query(call.id, "❌ Join first!", show_alert=True)
        return

    if call.data.startswith("yt_"):
        url = user_links.get(call.from_user.id)
        if not url:
            bot.answer_callback_query(call.id, "Link expired, send again.")
            return
        bot.answer_callback_query(call.id, f"Downloading {call.data}...")
        bot.edit_message_text(f"⏳ Downloading {call.data}... wait.", call.message.chat.id, call.message.message_id)
        threading.Thread(target=do_download, args=(call.message.chat.id, url, call.data, call.message.message_id)).start()

@bot.message_handler(func=lambda m: True)
def link_h(message):
    txt = message.text.strip()
    if "instagram.com" not in txt and "youtu" not in txt and "facebook.com" not in txt and "fb.watch" not in txt and "twitter.com" not in txt and "x.com" not in txt: return
    if not is_user_joined(message.from_user.id):
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("💎 Join Channel 💎", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, "🚫 Join channel first.", reply_markup=mk)
        return

    if "youtu" in txt:
        user_links[message.from_user.id] = txt
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(types.InlineKeyboardButton("360p", callback_data="yt_360"), types.InlineKeyboardButton("720p HD", callback_data="yt_720"),
               types.InlineKeyboardButton("1080p HD", callback_data="yt_1080"), types.InlineKeyboardButton("Best", callback_data="yt_best"),
               types.InlineKeyboardButton("MP3 Audio", callback_data="yt_mp3"))
        bot.send_message(message.chat.id, "🎬 YouTube Detected - Select Quality:", reply_markup=mk)
    else:
        status = bot.send_message(message.chat.id, "⏳ Downloading... Please wait")
        threading.Thread(target=do_download, args=(message.chat.id, txt, "yt_best", status.message_id)).start()

@app.route('/')
def home(): return "Bot Alive"
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return ''
if __name__ == "__main__":
    bot.remove_webhook(); time.sleep(1)
    if WEBHOOK_URL: bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
