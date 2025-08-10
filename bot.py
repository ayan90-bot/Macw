from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import datetime
import json

TOKEN = "8306328481:AAEFUyQMdrRnLvC0XcWgWsav6dKXUwMLZpU"    # BotFather se mila token yahan dalein
ADMIN_ID = 6324825537             # Apna Telegram ID yahan dalein (admin ke liye)

# Simple JSON file me data save aur load karne ke functions
def load_db():
    try:
        with open("database.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open("database.json", "w") as f:
        json.dump(data, f)

db = load_db()

def is_premium(user_id):
    user = db.get(str(user_id), {})
    if "premium_until" in user:
        return datetime.datetime.now() < datetime.datetime.fromisoformat(user["premium_until"])
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) not in db:
        db[str(user_id)] = {"requests": 0, "banned": False}
        save_db(db)
    keyboard = [
        [InlineKeyboardButton("Redeem Request", callback_data="redeem")],
        [InlineKeyboardButton("Buy Premium", callback_data="buy_premium")],
        [InlineKeyboardButton("Service", callback_data="service")],
        [InlineKeyboardButton("Dev", callback_data="dev")],
    ]
    await update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if db[str(user_id)].get("banned"):
        await query.message.reply_text("🚫 You are banned from using this bot.")
        return

    if query.data == "redeem":
        if is_premium(user_id) or db[str(user_id)]["requests"] == 0:
            db[str(user_id)]["waiting_for_redeem"] = True
            if not is_premium(user_id):
                db[str(user_id)]["requests"] += 1
            save_db(db)
            await query.message.reply_text("Please Enter Details:")
        else:
            await query.message.reply_text("⚠ Free users can only redeem once.")
    
    elif query.data == "buy_premium":
        db[str(user_id)]["waiting_for_key"] = True
        save_db(db)
        await query.message.reply_text("Please enter your premium key:")

    elif query.data == "service":
        await query.message.reply_text("1. Prime Video\n2. Spotify\n3. Crunchyroll\n4. Turbo VPN\n5. Hotspot Shield VPN")

    elif query.data == "dev":
        await query.message.reply_text("@YourAizen")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if db[str(user_id)].get("waiting_for_redeem"):
        db[str(user_id)]["waiting_for_redeem"] = False
        save_db(db)
        await context.bot.send_message(ADMIN_ID, f"📨 Redeem Request from {update.effective_user.mention_html()}:\n{text}", parse_mode="HTML")
        await update.message.reply_text("✅ Your request has been sent to admin.")

    elif db[str(user_id)].get("waiting_for_key"):
        db[str(user_id)]["waiting_for_key"] = False
        save_db(db)
        if check_key(text, user_id):
            await update.message.reply_text("🎉 Premium Activated!")
            await context.bot.send_message(ADMIN_ID, f"💎 Premium Activated for {update.effective_user.mention_html()}", parse_mode="HTML")
        else:
            await update.message.reply_text("❌ Invalid key")

def gen_key(days):
    expiry = datetime.datetime.now() + datetime.timedelta(days=days)
    return f"KEY-{expiry.timestamp()}"

def check_key(key, user_id):
    try:
        parts = key.split("-")
        expiry_timestamp = float(parts[1])
        expiry_date = datetime.datetime.fromtimestamp(expiry_timestamp)
        if datetime.datetime.now() < expiry_date:
            db[str(user_id)]["premium_until"] = expiry_date.isoformat()
            save_db(db)
            return True
    except:
        return False
    return False

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
        await update.message.reply_text("Please enter a valid number of days.")

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
    if uid in db:
        db[uid]["banned"] = True
        save_db(db)
        await update.message.reply_text(f"🚫 Banned {uid}")
    else:
        await update.message.reply_text("User not found.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid = context.args[0]
    if uid in db:
        db[uid]["banned"] = False
        save_db(db)
        await update.message.reply_text(f"✅ Unbanned {uid}")
    else:
        await update.message.reply_text("User not found.")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(CommandHandler("genk", genk))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
