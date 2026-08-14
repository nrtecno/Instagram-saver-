import os
import time
import glob
import json
import threading
import yt_dlp
import telebot
from flask import Flask, request
from telebot import types

# --- ENV VARIABLES (Render se ayenge) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID") # Render me add karna: ADMIN_ID = 7231318491
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

# Admin ID ko int me convert
try:
    ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else None
except:
    ADMIN_ID = None

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not found in Environment Variables!")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# --- CONFIG ---
CHANNEL_USERNAME = "@nrtecno2"
CHANNEL_LINK = "https://t.me/nrtecno2"
USERS_FILE = "total_users.json"

app = Flask(__name__)

# --- TOTAL USERS SYSTEM ---
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        try:
            with open(USERS_FILE, 'w') as f:
                json.dump(users, f)
        except:
            pass
    return len(users)

def get_total_users():
    return len(load_users())

# --- AUTO CLEANUP (3 min me file delete) ---
def auto_cleanup():
    while True:
        time.sleep(180)
        files = glob.glob("*.mp4") + glob.glob("*.jpg") + glob.glob("*.jpeg") + glob.glob("*.mkv") + glob.glob("*.webm")
        for f in files:
            try:
                if os.path.exists(f) and (time.time() - os.path.getctime(f) > 180):
                    os.remove(f)
            except:
                pass

threading.Thread(target=auto_cleanup, daemon=True).start()

# --- CHANNEL JOIN CHECK ---
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return True # Agar bot admin nahi hai to check skip kar dega

# --- START & STATS COMMAND ---
@bot.message_handler(commands=['start', 'stats', 'users'])
def start_handler(message):
    user_id = message.from_user.id
    total = save_user(user_id)

    # Stats command - only for admin
    if message.text.startswith("/stats") or message.text.startswith("/users"):
        if ADMIN_ID is None or user_id!= ADMIN_ID:
            bot.send_message(message.chat.id, "❌ This command is only for Admin.")
            return
        bot.send_message(message.chat.id, f"📊 **Total Bot Users: {total}** 🚀\n\nBot is running perfectly!", parse_mode="Markdown")
        return

    # Normal Start
    if not is_user_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Join Our Channel 💎", url=CHANNEL_LINK))
        markup.add(types.InlineKeyboardButton("✅ I Joined - Check Now 🔥", callback_data="check_join"))
        bot.send_message(
            message.chat.id,
            f"👋 **Welcome to INSTAGRAM DOWNLOADER BOT**\n\n"
            f"⚠️ To use this bot, you must join our channel {CHANNEL_USERNAME}\n\n"
            f"👥 **Total Users: {total}**\n\n"
            f"Join channel and click Check button.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            message.chat.id,
            f"👋 **Welcome Back!**\n\n"
            f"👥 **Total Users: {total}**\n\n"
            f"✅ You are our channel member.\n\n"
            f"📩 Now send me any Instagram Reels / Post / Story link and I will download it for you.",
            parse_mode="Markdown"
        )

# --- CHECK JOIN BUTTON ---
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_handler(call):
    user_id = call.from_user.id
    total = save_user(user_id)
    if is_user_joined(user_id):
        bot.edit_message_text(
            f"✅ **Thank you for joining!**\n\n👥 **Total Users: {total}**\n\n📩 Now send me any Instagram link and I will download it.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined yet! Please join first.", show_alert=True)

# --- LINK HANDLER - DIRECT DOWNLOAD ---
@bot.message_handler(func=lambda m: True)
def handle_link(message):
    if "instagram.com" not in message.text:
        if not message.text.startswith("/"):
            bot.send_message(message.chat.id, "❌ Please send a valid Instagram link.")
        return

    user_id = message.from_user.id
    total = save_user(user_id)

    # Again check join before download
    if not is_user_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Join Channel First 💎", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, f"⚠️ Please join {CHANNEL_USERNAME} first to use bot.\n\n👥 Total Users: {total}", reply_markup=markup)
        return

    url = message.text.strip()
    status_msg = bot.send_message(message.chat.id, "⏳ **Downloading... Please wait**", parse_mode="Markdown")

    ydl_opts = {
        'format': 'best',
        'outtmpl': '%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        caption = f"✅ **Downloaded Successfully**\n\n👥 Total Users: {total}\n🔗 Join: {CHANNEL_USERNAME}\n🤖 Bot: @{bot.get_me().username}"
        with open(filename, 'rb') as f:
            if filename.endswith(('.mp4', '.mkv', '.mov', '.webm')):
                bot.send_video(message.chat.id, f, caption=caption)
            else:
                bot.send_photo(message.chat.id, f, caption=caption)

        if os.path.exists(filename):
            os.remove(filename)
        try:
            bot.delete_message(message.chat.id, status_msg.message_id)
        except:
            pass

    except Exception as e:
        print(f"Download Error: {e}")
        try:
            bot.edit_message_text("❌ **Failed to download.**\n\nReason: Post might be private or link is incorrect.", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        except:
            bot.send_message(message.chat.id, "❌ Failed to download.")

# --- FLASK WEBHOOK ---
@app.route('/')
def home():
    return f"Bot is Alive! Total Users: {get_total_users()}"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'OK', 403

# --- MAIN ---
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        if WEBHOOK_URL:
            full_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
            bot.set_webhook(url=full_url)
            print(f"Webhook set to: {full_url}")
        else:
            print("RENDER_EXTERNAL_URL not found, webhook not set (local run)")
    except Exception as e:
        print(f"Webhook setup error: {e}")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
