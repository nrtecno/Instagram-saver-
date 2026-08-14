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
except:
    ADMIN_ID = None

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
CHANNEL_USERNAME = "@nrtecno2"
CHANNEL_LINK = "https://t.me/nrtecno2"
app = Flask(__name__)

def auto_cleanup():
    while True:
        time.sleep(180)
        for f in glob.glob("*.mp4") + glob.glob("*.jpg") + glob.glob("*.mkv") + glob.glob("*.webm"):
            try:
                if os.path.exists(f) and (time.time() - os.path.getctime(f) > 180): os.remove(f)
            except: pass
threading.Thread(target=auto_cleanup, daemon=True).start()

def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False # Bot admin nahi hai to block karega

@bot.message_handler(commands=['start'])
def start_handler(message):
    if not is_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Join Our Channel 💎", url=CHANNEL_LINK))
        markup.add(types.InlineKeyboardButton("✅ I Joined - Check Now 🔥", callback_data="check_join"))
        bot.send_message(message.chat.id, f"👋 Welcome to INSTAGRAM DOWNLOADER BOT\n\n⚠️ To use bot, you must join {CHANNEL_USERNAME}\n\nJoin and click Check button.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, f"👋 Welcome Back!\n\n✅ You are our channel member.\n\n📩 Send me any Instagram link and I will download it.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if is_user_joined(call.from_user.id):
        bot.edit_message_text("✅ Thanks for joining!\n\n📩 Now send any Instagram link.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined yet! Join first.", show_alert=True)

@bot.message_handler(func=lambda m: True)
def handle_link(message):
    if "instagram.com" not in message.text: return

    if not is_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Join Channel to Unlock Bot 💎", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, f"🚫 Bot Locked\n\nYou must join {CHANNEL_USERNAME} first.", reply_markup=markup)
        return

    url = message.text.strip()
    msg = bot.send_message(message.chat.id, "⏳ Downloading...")
    ydl_opts = {'format': 'best', 'outtmpl': '%(id)s.%(ext)s', 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        caption = f"✅ Downloaded\n🔗 Join: {CHANNEL_USERNAME}\n🤖 Bot: @{bot.get_me().username}"
        with open(filename, 'rb') as f:
            if filename.endswith(('.mp4','.mkv','.mov','.webm')): bot.send_video(message.chat.id, f, caption=caption)
            else: bot.send_photo(message.chat.id, f, caption=caption)
        if os.path.exists(filename): os.remove(filename)
        bot.delete_message(message.chat.id, msg.message_id)
    except Exception as e:
        print(e)
        bot.edit_message_text("❌ Failed to download. Private post?", message.chat.id, msg.message_id)

@app.route('/')
def home(): return "Bot is Alive!"
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
