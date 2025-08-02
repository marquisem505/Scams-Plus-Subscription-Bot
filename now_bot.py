
import os
import csv
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, ChatJoinRequestHandler, filters
from aiohttp import web

# 🔐 ENV variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6967780222"))
GROUP_ID = int(os.getenv("GROUP_ID", "-2286707356"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://www.scamsclub.store/telegram-webhook")

headers = {
    "x-api-key": NOWPAYMENTS_API_KEY,
    "Content-Type": "application/json"
}

user_invoices = {}

def is_admin(user_id):
    return int(user_id) == ADMIN_ID

def log_invoice(chat_id, username, invoice_id, invoice_url, amount):
    with open("payments_log.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), chat_id, username, invoice_id, amount, invoice_url])

def log_confirmed_payment(chat_id, username, amount, invoice_id):
    with open("confirmed_payments.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), chat_id, username, amount, invoice_id])

# 📲 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "N/A"
    payload = {
        "price_amount": 97.00,
        "price_currency": "usd",
        "pay_currency": "btc",
        "order_description": f"Scam’s Club Plus Access - {chat_id}",
        "ipn_callback_url": "https://www.scamsclub.store/nowpayments-webhook",
        "success_url": "https://t.me/+gKCi4JF7POg3M2Ux",
        "cancel_url": "https://t.me/+gKCi4JF7POg3M2Ux"
    }

    try:
        response = requests.post("https://api.nowpayments.io/v1/invoice", json=payload, headers=headers)
        data = response.json()
        invoice_url = data.get('invoice_url')
        invoice_id = str(data.get('id'))

        if not invoice_url or not invoice_id:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Unexpected response:\n{data}")
            return

        user_invoices[chat_id] = invoice_id
        log_invoice(chat_id, username, invoice_id, invoice_url, "97.00 USD")

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"💳 To join Scam’s Club Plus:\n\n"
                f"👉 [Click here to pay with BTC]({invoice_url})\n\n"
                f"This link will generate your own QR code and BTC address.\n"
                f"✅ After payment is confirmed, you’ll be added to the group."
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {str(e)}")

# 📊 /status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    invoice_id = user_invoices.get(chat_id)

    if not invoice_id:
        await context.bot.send_message(chat_id=chat_id, text="❌ No payment found. Use /start to create one.")
        return

    try:
        response = requests.get(f"https://api.nowpayments.io/v1/invoice/{invoice_id}", headers=headers)
        data = response.json()
        status = data.get('payment_status', 'Unknown')
        await context.bot.send_message(chat_id=chat_id, text=f"📊 Current payment status: **{status.upper()}**", parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error checking status: {str(e)}")

# 🧪 /testpayment
async def testpayment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /testpayment 123456789")
        return

    telegram_id = context.args[0]
    username = "TestUser"
    amount = "97.00"
    invoice_id = "TEST-" + str(datetime.now().timestamp()).split('.')[0]

    # Add user to group
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember",
        data={"chat_id": GROUP_ID, "user_id": telegram_id}
    )

    log_confirmed_payment(telegram_id, username, amount, invoice_id)

    try:
        if int(telegram_id) in user_invoices:
            del user_invoices[int(telegram_id)]
    except:
        pass

    await context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ (SIMULATED) {username} marked as PAID\nTelegram ID: {telegram_id}\nInvoice: {invoice_id}")
    await update.message.reply_text("✅ Test payment processed.")

# 🧾 New user welcome (group join)
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.new_chat_members[0]
    chat_id = user.id
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "👋 Welcome to Scam’s Club !\n\n"
                "🚀 Ready to level up?\n\n"
                "💳 Join Scam’s Club Plus:\n"
                "👉 Use /start to generate your BTC payment link."
            )
        )
    except Exception as e:
        print(f"❌ Failed DM: {e}")

# ✅ Handle join requests (approval + DM button)
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    join_request: ChatJoinRequest = update.chat_join_request
    user = join_request.from_user

    try:
        # await context.bot.approve_chat_join_request(chat_id=join_request.chat.id, user_id=user.id)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔌 Scam's Plus", url="https://t.me/ScamsClub_Bot?start=welcome")]]
        )
        await context.bot.send_message(
            chat_id=user.id,
            text=("👋 Welcome to Scam’s Club !\n\n"
                "💳 Join Scam’s Club Plus:\n"
                "👉 Use /start to generate your BTC payment link.",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ Failed to process join request: {e}")

# 🌐 Webhook handler
async def telegram_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(text="OK")
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return web.Response(status=500, text="Webhook Error")

# 🌐 aiohttp app
app = web.Application()
app.router.add_post('/telegram-webhook', telegram_webhook)

# 📡 Telegram app
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("testpayment", testpayment))
application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
application.add_handler(ChatJoinRequestHandler(handle_join_request))

# 📌 Set webhook on startup
async def on_startup(app):
    await application.initialize()
    await application.bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook set: {WEBHOOK_URL}")

app.on_startup.append(on_startup)

# 🚀 Run server
if __name__ == "__main__":
    web.run_app(app, port=8080)
