import requests
import csv
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.ext import MessageHandler, filters

# 🔐 API keys
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
headers = {
    "x-api-key": NOWPAYMENTS_API_KEY,
    "Content-Type": "application/json"
}

ADMIN_ID = 6967780222
GROUP_ID = -2286707356

def is_admin(user_id):
    return int(user_id) == ADMIN_ID
    


# In-memory storage of invoice IDs per user
user_invoices = {}

# Log invoice
def log_invoice(chat_id, username, invoice_id, invoice_url, amount ):
    with open("payments_log.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), chat_id, username, invoice_id, amount, invoice_url])

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "N/A"
    payload = {
        "price_amount": 97.00,
        "price_currency": "usd",
        "pay_currency": "btc",
        "order_description": f"Scam’s Club Plus Access - {chat_id}",
        "ipn_callback_url": "https://59afd3479b7f.ngrok-free.app/nowpayments-webhook",
        "success_url": "https://t.me/+gKCi4JF7POg3M2Ux",
        "cancel_url": "https://t.me/+gKCi4JF7POg3M2Ux"
    }

    try:
        response = requests.post("https://api.nowpayments.io/v1/invoice", json=payload, headers=headers)
        data = response.json()

        # 👇 Log full response
        print("NOWPayments response:", data)

        invoice_url = data['invoice_url']  # ✅ This is the hosted BTC payment link
        invoice_id = str(data['id'])       # ✅ This is the unique invoice ID
        user_invoices[chat_id] = invoice_id
        log_invoice(chat_id, username, invoice_id, invoice_url, "97.00 USD")

        if not invoice_url or not invoice_id:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ NOWPayments did not return expected fields:\n{data}")
            return

        # ✅ Save invoice to memory
        user_invoices[chat_id] = invoice_id

        # ✅ Log invoice to CSV
        log_invoice(chat_id, username, invoice_id, invoice_url, "97.00 USD")

        # ✅ Send payment link
        message = (
            f"💳 To join Scam’s Club Plus:\n\n"
            f"👉 [Click here to pay with BTC]({invoice_url})\n\n"
            f"This link will generate your own QR code and BTC address.\n"
            f"✅ After payment is confirmed, you’ll be added to the group."
        )
        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {str(e)}")

# /status handler
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    invoice_id = user_invoices.get(chat_id)

    if not invoice_id:
        await context.bot.send_message(chat_id=chat_id, text="❌ No payment found. Use /start to create one.")
        return

    try:
        response = requests.get(
            f"https://api.nowpayments.io/v1/invoice/{invoice_id}",
            headers=headers
        )
        data = response.json()
        status = data.get('payment_status', 'Unknown')
        await context.bot.send_message(chat_id=chat_id, text=f"📊 Current payment status: **{status.upper()}**", parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error checking status: {str(e)}")

def log_confirmed_payment(chat_id, username, amount, invoice_id):
    with open("confirmed_payments.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), chat_id, username, amount, invoice_id])

# /testpayment handler
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

    # Log payment 
    log_confirmed_payment(telegram_id, username, amount, invoice_id)

    # Remove from in-memory invoice tracking
    try:
        if int(telegram_id) in user_invoices:
            del user_invoices[int(telegram_id)]
    except:
        pass

    # Notify admin when payment is confirmed
    notify_msg = f"✅ (SIMULATED) {username} marked as PAID\nTelegram ID: {telegram_id}\nInvoice: {invoice_id}"
    await context.bot.send_message(chat_id=ADMIN_ID, text=notify_msg)

    await update.message.reply_text("✅ Test payment processed.")

# Welcome Message & Invite To Private
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.new_chat_members[0]
    chat_id = user.id

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "👋 Welcome to Scam’s Club Free!\n\n"
                "🚀 Ready to level up?\n\n"
                "💳 Join Scam’s Club Plus:\n"
                "👉 Use /start to generate your BTC payment link and get instant access to exclusive drops and sauce."
            )
        )
    except Exception as e:
        print(f"❌ Failed to message new user: {e}")


# Launch bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("testpayment", testpayment))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder

# Create Telegram app
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Add all handlers (same as before)
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("testpayment", testpayment))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))

# Aiohttp route to handle Telegram webhook updates
async def telegram_webhook_handler(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(text="OK")

# Aiohttp app and routes
web_app = web.Application()
web_app.router.add_post("/telegram-webhook", telegram_webhook_handler)

# 🚀 Start aiohttp server
if __name__ == '__main__':
    import asyncio
    async def start():
        # Set webhook with Telegram
        webhook_url = "https://yourdomain.com/telegram-webhook"  # 👈 update to your real domain
        await app.bot.set_webhook(webhook_url)

        # Run the aiohttp server
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        print("🚀 Webhook server running on port 8080")

    asyncio.run(start())
