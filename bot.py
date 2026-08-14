import os, time, glob, json, threading
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
USERS_FILE = "total_users.json"
app = Flask(__name__)

def load_users():
    if not os.path.exists(USERS_FILE): return []
    try:
        with open(USERS_FILE, 'r') as f: return json.load(f)
    except: return []
def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, 'w') as f: json.dump(users, f)
    return len(users)
def get_total_users(): return len(load_users())

def auto_cleanup():
    while True:
        time.sleep(180)
        for f in glob.glob("*.mp4") + glob.glob("*.jpg") + glob.glob("*.mkv") + glob.glob("*.webm"):
            try:
                if os.path.exists(f) and (time.time() - os.path.getctime(f) > 180): os.remove(f)
            except: pass
threading.Thread(target=auto_cleanup, daemon=True).start()

# --- STRICT CHECK ---
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Membership check failed (Bot is not admin?): {e}")
        # Agar bot admin nahi hai to ab FALSE ayega, matlab sab block honge
        return False

@bot.message_handler(commands=['start', 'stats'])
def start_handler(message):
    user_id = message.from_user.id
    total = save_user(user_id)
    if message.text.startswith("/stats"):
        if ADMIN_ID is None or user_id!= ADMIN_ID:
            bot.send_message(message.chat.id, "❌ Admin only.")
            return
        bot.send_message(message.chat.id, f"📊 Total Users: {total} 🚀", parse_mode="Markdown")
        return

    if not is_user_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Join Channel First 💎", url=CHANNEL_LINK))
        markup.add(types.InlineKeyboardButton("✅ I Joined - Check Now 🔥", callback_data="check_join"))
        bot.send_message(message.chat.id, f"⚠️ **Access Denied**\n\nYou must join {CHANNEL_USERNAME} to use this bot.\n\n👥 Total Users: {total}", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"👋 Welcome!\n\n👥 Total Users: {total}\n\n📩 Send Instagram link.", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data!= "check_join": return
    total = save_user(call.from_user.id)
    if is_user_joined(call.from_user.id):
        bot.edit_message_text(f"✅ Thanks for joining!\n👥 Total: {total}\n📩 Send link now.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined yet! Join and try again.", show_alert=True)

@bot.message_handler(func=lambda m: True)
def handle_link(message):
    if "instagram.com" not in message.text: return
    total = save_user(message.from_user.id)

    # --- YAHI STRICT BLOCK HAI ---
    if not is_user_joined(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Join Channel to Unlock Bot 💎", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, f"🚫 **Bot Locked**\n\nYou have not joined {CHANNEL_USERNAME}.\nJoin first to download.\n\n👥 Total: {total}", reply_markup=markup, parse_mode="Markdown")
        return # <-- Yahan se aage bot kaam hi nahi karega

    url = message.text.strip()
    msg = bot.send_message(message.chat.id, "⏳ Downloading...")
    ydl_opts = {'format': 'best', 'outtmpl': '%(id)s.%(ext)s', 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        caption = f"✅ Done\n👥 Total: {total}\nJoin: {CHANNEL_USERNAME}"
        with open(filename, 'rb') as f:
            if filename.endswith(('.mp4','.mkv','.mov','.webm')): bot.send_video(message.chat.id, f, caption=caption)
            else: bot.send_photo(message.chat.id, f, caption=caption)
        if os.path.exists(filename): os.remove(filename)
        bot.delete_message(message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Failed. Private link?", message.chat.id, msg.message_id)

@app.route('/')
def home(): return f"Bot Alive! Total: {get_total_users()}"
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
