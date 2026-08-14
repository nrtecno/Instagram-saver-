import os
import time
import glob
import threading
import yt_dlp
import telebot
from flask import Flask, request
from telebot import types

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

CHANNEL_USERNAME = "@nrtecno2"
CHANNEL_LINK = "https://t.me/nrtecno2"
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL") # Render khud ye de dega

app = Flask(__name__)

# --- Auto Cleanup every 3 min ---
def auto_cleanup():
    while True:
        time.sleep(180)
        print("Cleaning storage...")
        files = glob.glob("*.mp4") + glob.glob("*.jpg") + glob.glob("*.mkv") + glob.glob("*.webm") + glob.glob("*.m4a") + glob.glob("*.webp")
        for f in files:
            try:
                if os.path.exists(f) and (time.time() - os.path.getctime(f) > 180):
                    os.remove(f)
                    print(f"Deleted: {f}")
            except: pass
threading.Thread(target=auto_cleanup, daemon=True).start()

def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return True

# --- Handlers ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if not is_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        markup.add(types.InlineKeyboardButton("✅ I Joined - Check", callback_data="check_join"))
        bot.send_message(message.chat.id, f"⚠️ To use this bot, you must join {CHANNEL_USERNAME} first.", reply_markup=markup)
        return
    bot.send_message(message.chat.id, "👋 Welcome!\nSend me any Instagram link.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "check_join":
        if is_user_joined(call.from_user.id):
            bot.edit_message_text("✅ Thanks for joining! Now send me any Instagram link.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ You haven't joined yet!", show_alert=True)
        return

    url = bot_data.get(call.from_user.id)
    if not url:
        bot.edit_message_text("Link expired. Send again.", call.message.chat.id, call.message.message_id)
        return

    quality = call.data.split("_")[1]
    bot.edit_message_text(f"⏳ Downloading in {quality}...", call.message.chat.id, call.message.message_id)

    format_map = {"360": "best[height<=360]", "480": "best[height<=480]", "720": "best[height<=720]", "1080": "best[height<=1080]", "best": "best"}

    ydl_opts = {'format': format_map.get(quality, 'best'), 'outtmpl': '%(id)s.%(ext)s', 'quiet': True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        caption = f"✅ {quality} Quality\nJoin: {CHANNEL_USERNAME}"
        with open(filename, 'rb') as f:
            if filename.endswith(('.mp4','.mkv','.mov')):
                bot.send_video(call.message.chat.id, f, caption=caption)
            else:
                bot.send_photo(call.message.chat.id, f, caption=caption)
        os.remove(filename)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Failed: {e}")

bot_data = {}
@bot.message_handler(func=lambda m: True)
def handle_link(message):
    if "instagram.com" not in message.text:
        if message.text.startswith("/"): return
        bot.send_message(message.chat.id, "Please send a valid Instagram link.")
        return
    if not is_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, f"Please join {CHANNEL_USERNAME} first.", reply_markup=markup)
        return

    bot_data[message.from_user.id] = message.text.strip()
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Low 360p", callback_data="q_360"),
        types.InlineKeyboardButton("Med 480p", callback_data="q_480"),
        types.InlineKeyboardButton("HD 720p", callback_data="q_720"),
        types.InlineKeyboardButton("Full HD 1080p", callback_data="q_1080"),
        types.InlineKeyboardButton("Best 4K/8K", callback_data="q_best"),
    )
    bot.send_message(message.chat.id, "👇 Select Quality:", reply_markup=markup)

# --- Webhook Routes ---
@app.route('/')
def home():
    return "Bot is Alive! - Webhook Mode"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'OK', 403

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    # Render automatically provides RENDER_EXTERNAL_URL like https://your-app.onrender.com
    if WEBHOOK_URL:
        full_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        bot.set_webhook(url=full_url)
        print(f"Webhook set to: {full_url}")
    else:
        print("RENDER_EXTERNAL_URL not found, set webhook manually")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
