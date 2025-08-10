from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import datetime, json, os
import threading

TOKEN = os.getenv("BOT_TOKEN")  # Render me env var set karein
ADMIN_ID = 6324825537  # apna Telegram user ID
DATABASE_FILE = "database.json"

# Flask app
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

# DB functions
def load_db():
    try:
        with open(DATABASE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DATABASE_FILE, "w") as f:
        json.dump(data, f)

db = load_db()

def is_premium(user_id):
    user = db.get(str(user_id), {})
    if "premium_until" in user:
        return datetime.datetime.now() < datetime.datetime.fromisoformat(user["premium_until"])
    return False

def gen_key(days):
    expiry = datetime.datetime.now() + datetime.timedelta(days=days)
    return f"KEY-{expiry.timestamp()}"

def check_key(key, user_id):
    try:
        expiry_ts = float(key.split("-")[1])
        expiry_date = datetime.datetime.fromtimestamp(expiry_ts)
        if datetime.datetime.now() < expiry_date:
            db[str(user_id)]["premium_until"] = expiry_date.isoformat()
            save_db(db)
            return True
    except:
        return False
    return False

# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if str(uid) not in db:
        db[str(uid)] = {"requests": 0, "banned": False}
        save_db(db)

    keyboard = [
        [InlineKeyboardButton("Redeem Request", callback_data="redeem")],
        [InlineKeyboardButton("Buy Premium", callback_data="buy_premium")],
        [InlineKeyboardButton("Service", callback_data="service")],
        [InlineKeyboardButton("Dev", callback_data="dev")],
    ]
    await update.message.reply_text(
        "👋 Welcome to the Bot!\nPlease choose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if db[str(uid)].get("banned"):
        await q.message.reply_text("🚫 You are banned.")
        return

    if q.data == "redeem":
        if is_premium(uid) or db[str(uid)]["requests"] == 0:
            db[str(uid)]["waiting_for_redeem"] = True
            if not is_premium(uid):
                db[str(uid)]["requests"] += 1
            save_db(db)
            await q.message.reply_text("Please enter your redeem details:")
        else:
            await q.message.reply_text("⚠ Free users can only redeem once.")

    elif q.data == "buy_premium":
        db[str(uid)]["waiting_for_key"] = True
        save_db(db)
        await q.message.reply_text("Please enter your premium key:")

    elif q.data == "service":
        await q.message.reply_text(
            "1. Prime Video\n2. Spotify\n3. Crunchyroll\n4. Turbo VPN\n5. Hotspot Shield VPN"
        )

    elif q.data == "dev":
        await q.message.reply_text("@YourAizen")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if db[str(uid)].get("waiting_for_redeem"):
        db[str(uid)]["waiting_for_redeem"] = False
        save_db(db)
        await context.bot.send_message(ADMIN_ID, f"📨 Redeem Request from {update.effective_user.mention_html()}:\n{text}", parse_mode="HTML")
        await update.message.reply_text("✅ Request sent to admin.")

    elif db[str(uid)].get("waiting_for_key"):
        db[str(uid)]["waiting_for_key"] = False
        save_db(db)
        if check_key(text, uid):
            await update.message.reply_text("🎉 Premium Activated!")
            await context.bot.send_message(ADMIN_ID, f"💎 Premium activated for {update.effective_user.mention_html()}", parse_mode="HTML")
        else:
            await update.message.reply_text("❌ Invalid key.")

# Admin Commands
async def genk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /genk <days>")
        return
    try:
        days = int(context.args[0])
        key = gen_key(days)
        await update.message.reply_text(f"Generated key: `{key}`", parse_mode="Markdown")
    except:
        await update.message.reply_text("Invalid number of days.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = " ".join(context.args)
    for uid in db.keys():
        try:
            await context.bot.send_message(int(uid), msg)
        except:
            pass
    await update.message.reply_text("✅ Broadcast sent.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid = context.args[0]
    db[uid]["banned"] = True
    save_db(db)
    await update.message.reply_text(f"🚫 Banned {uid}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid = context.args[0]
    db[uid]["banned"] = False
    save_db(db)
    await update.message.reply_text(f"✅ Unbanned {uid}")

# Run bot in background thread
def run_bot():
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(button_click))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_bot.add_handler(CommandHandler("genk", genk))
    app_bot.add_handler(CommandHandler("broadcast", broadcast))
    app_bot.add_handler(CommandHandler("ban", ban))
    app_bot.add_handler(CommandHandler("unban", unban))
    app_bot.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
