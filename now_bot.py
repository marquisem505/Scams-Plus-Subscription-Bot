import os
import csv
import requests
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, ChatJoinRequestHandler, filters
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6967780222"))
FREE_GROUP_ID = int(os.getenv("FREE_GROUP_ID", "2019911042"))
PAID_GROUP_ID = int(os.getenv("GROUP_ID", "-2286707356"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://www.scamsclub.store/telegram-webhook")

headers = {
    "x-api-key": NOWPAYMENTS_API_KEY,
    "Content-Type": "application/json"
}

user_invoices = {}
subscription_expiry = {}
COUNTDOWN_START_DAYS = 5

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "N/A"

    try:
        await update.message.delete()
    except Exception as e:
        print(f"❌ Could not delete /start message: {e}")

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
                f"💳 Scam’s Club Plus is $97/month:\n\n"
                f"👉 [Click Here To Sign Up]({invoice_url})\n\n"
                f"✅ After payment is confirmed, you’ll be automatically added to Scam's Plus!"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    expiry = subscription_expiry.get(chat_id)

    if expiry:
        await context.bot.send_message(chat_id=chat_id, text=f"📊 Your subscription expires on: **{expiry.strftime('%Y-%m-%d')}**", parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ No active subscription found.")

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

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember",
        data={"chat_id": PAID_GROUP_ID, "user_id": telegram_id}
    )

    subscription_expiry[int(telegram_id)] = datetime.now() + timedelta(days=30)
    log_confirmed_payment(telegram_id, username, amount, invoice_id)

    try:
        if int(telegram_id) in user_invoices:
            del user_invoices[int(telegram_id)]
    except:
        pass

    await context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ (SIMULATED) {username} marked as PAID\nTelegram ID: {telegram_id}\nInvoice: {invoice_id}")
    await update.message.reply_text("✅ Test payment processed.")

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    join_request: ChatJoinRequest = update.chat_join_request
    user = join_request.from_user

    try:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔌 Join Scam's Plus", url="https://t.me/ScamsClub_Bot?start=welcome")]]
        )
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                "👋 Thank You For Joining Scam’s Club!\n\n"
                "🚀 Ready To Level Up? Join Scam’s Plus For Access To:\n\n"
                "🔒 Our VIP Lounge\n"
                "📋 Verified & Current Working Methods\n"
                "🙋 Help With Any/All Questions\n"
                "🛠️ Our Favorite Tools & Bots\n"
                "🧑‍🎓 Con Academy (Our 1-on-1 Mentorship Program)\n"
                "📋 Verified Vendors For Collaborations\n\n"
                "👇 Join Scam's Plus Now! 👇"
            ),
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"❌ Failed to process join request: {e}")

async def poll_invoice_statuses():
    while True:
        await asyncio.sleep(300)
        for chat_id, invoice_id in list(user_invoices.items()):
            try:
                response = requests.get(f"https://api.nowpayments.io/v1/invoice/{invoice_id}", headers=headers)
                data = response.json()

                if data.get("payment_status") == "finished":
                    username = "User"
                    amount = "97.00"

                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember",
                        data={"chat_id": PAID_GROUP_ID, "user_id": chat_id}
                    )

                    subscription_expiry[int(chat_id)] = datetime.now() + timedelta(days=30)
                    log_confirmed_payment(chat_id, username, amount, invoice_id)

                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"✅ Your payment was successful!\n\n"
                            f"You’ve been added to Scam’s Club Plus.\n"
                            f"Invoice: `{invoice_id}`\n"
                            f"Amount: ${amount} USD"
                        ),
                        parse_mode="Markdown"
                    )

                    await application.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=(
                            f"📢 New Paid Member Added\n\n"
                            f"• Telegram ID: `{chat_id}`\n"
                            f"• Invoice: `{invoice_id}`\n"
                            f"• Amount: ${amount} USD"
                        ),
                        parse_mode="Markdown"
                    )

                    del user_invoices[chat_id]
            except Exception as e:
                print(f"❌ Error checking invoice {invoice_id} for {chat_id}: {e}")

        for uid, expiry in list(subscription_expiry.items()):
            days_left = (expiry - datetime.now()).days
            if 0 < days_left <= COUNTDOWN_START_DAYS:
                try:
                    keyboard = InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🔁 Renew Now", url="https://t.me/ScamsClub_Bot?start=renew")]]
                    )
                    await application.bot.send_message(
                        chat_id=uid,
                        text=(
                            f"⏳ Your Scam’s Club Plus access expires in {days_left} day(s)!\n"
                            f"Renew now to stay connected."
                        ),
                        reply_markup=keyboard
                    )
                except Exception as e:
                    print(f"❌ Failed to send renewal reminder to {uid}: {e}")
            elif datetime.now() > expiry:
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/banChatMember",
                        data={"chat_id": PAID_GROUP_ID, "user_id": uid}
                    )
                    print(f"✅ Removed expired member: {uid}")
                    del subscription_expiry[uid]
                except Exception as e:
                    print(f"❌ Error removing expired user {uid}: {e}")

async def telegram_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(text="OK")
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return web.Response(status=500, text="Webhook Error")

app = web.Application()
app.router.add_post('/telegram-webhook', telegram_webhook)

application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("testpayment", testpayment))
application.add_handler(ChatJoinRequestHandler(handle_join_request))

async def on_startup(app):
    await application.initialize()
    await application.bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(poll_invoice_statuses())
    print(f"✅ Webhook set: {WEBHOOK_URL}")

app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, port=8080)