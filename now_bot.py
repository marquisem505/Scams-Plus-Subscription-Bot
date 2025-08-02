import os
import csv
import requests
from datetime import datetime
from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, filters, AIORateLimiter
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))

headers = {
    "x-api-key": NOWPAYMENTS_API_KEY,
    "Content-Type": "application/json"
}

user_invoices = {}

def is_admin(user_id): return int(user_id) == ADMIN_ID

def log_invoice(chat_id, username, invoice_id, invoice_url, amount):
    with open("payments_log.csv", "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(), chat_id, username, invoice_id, amount, invoice_url])

def log_confirmed_payment(chat_id, username, amount, invoice_id):
    with open("confirmed_payments.csv", "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(), chat_id, username, amount, invoice_id])

# Telegram Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "N/A"
    payload = {
        "price_amount": 97.00,
        "price_currency": "usd",
        "pay_currency": "btc",
        "order_description": f"Scam’s Club Plus Access - {chat_id}",
        "ipn_callback_url": "https://scamsclub.store/nowpayments-webhook",
        "success_url": "https://t.me/+gKCi4JF7POg3M2Ux",
        "cancel_url": "https://t.me/+gKCi4JF7POg3M2Ux"
    }

    try:
        res = requests.post("https://api.nowpayments.io/v1/invoice", json=payload, headers=headers).json()
        invoice_url, invoice_id = res["invoice_url"], str(res["id"])
        user_invoices[chat_id] = invoice_id
        log_invoice(chat_id, username, invoice_id, invoice_url, "97.00 USD")

        msg = (
            f"💳 To join Scam’s Club Plus:\n\n"
            f"👉 [Click here to pay with BTC]({invoice_url})\n\n"
            f"This link will generate your own QR code and BTC address.\n"
            f"✅ After payment is confirmed, you’ll be added to the group."
        )
        await context.bot.send_message(chat_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id, text=f"❌ Error: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    invoice_id = user_invoices.get(chat_id)
    if not invoice_id:
        return await context.bot.send_message(chat_id, "❌ No payment found. Use /start to create one.")

    try:
        res = requests.get(f"https://api.nowpayments.io/v1/invoice/{invoice_id}", headers=headers).json()
        await context.bot.send_message(chat_id, f"📊 Status: **{res.get('payment_status', 'Unknown').upper()}**", parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id, f"❌ Error checking status: {str(e)}")

async def testpayment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("🚫 You are not authorized.")
    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /testpayment <telegram_id>")
    
    telegram_id = context.args[0]
    username, amount = "TestUser", "97.00"
    invoice_id = "TEST-" + str(datetime.now().timestamp()).split('.')[0]
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember",
                  data={"chat_id": GROUP_ID, "user_id": telegram_id})
    log_confirmed_payment(telegram_id, username, amount, invoice_id)
    user_invoices.pop(int(telegram_id), None)
    
    await context.bot.send_message(ADMIN_ID, text=f"✅ (SIMULATED) {username} marked as PAID\nID: {telegram_id}\nInvoice: {invoice_id}")
    await update.message.reply_text("✅ Test payment processed.")

async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.new_chat_members[0]
    await context.bot.send_message(user.id, text=(
        "👋 Welcome to Scam’s Club Free!\n\n"
        "🚀 Ready to level up?\n\n"
        "💳 Join Scam’s Club Plus:\n"
        "👉 Use /start to generate your BTC payment link."
    ))

# 🌐 Webhook Handlers
async def telegram_webhook(request):
    data = await request.json()
    await app.update_queue.put(Update.de_json(data, bot))
    return web.Response()

async def nowpayments_webhook(request):
    data = await request.json()
    status = data.get("payment_status")
    description = data.get("order_description", "")
    invoice_id = data.get("payment_id", "N/A")
    amount = data.get("price_amount", "97.00")

    if " - " in description:
        _, telegram_id = description.split(" - ")
        telegram_id = telegram_id.strip()

        if status == "confirmed":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember",
                          data={"chat_id": GROUP_ID, "user_id": telegram_id})
            username = "N/A"
            try:
                with open("payments_log.csv", "r") as f:
                    for row in reversed(list(csv.reader(f))):
                        if telegram_id == row[1]:
                            username = row[2]
                            break
            except:
                pass

            log_confirmed_payment(telegram_id, username, amount, invoice_id)
            notify = f"✅ {username} PAID {amount} BTC!\nID: {telegram_id}\nInvoice: {invoice_id}"
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                          data={"chat_id": ADMIN_ID, "text": notify})

    return web.Response()

# 🚀 Main app setup
app = Application.builder().token(BOT_TOKEN).rate_limiter(AIORateLimiter()).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("testpayment", testpayment))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))

aio_app = web.Application()
aio_app.router.add_post("/telegram-webhook", telegram_webhook)
aio_app.router.add_post("/nowpayments-webhook", nowpayments_webhook)

# ⏯️ Serve web app on port 8080
if __name__ == "__main__":
    web.run_app(aio_app, port=8080)
