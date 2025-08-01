import os
import csv
import requests
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update

BOT_TOKEN = os.getenv("BOT_TOKEN", "7152782887:AAFbItSrIW2uYXHqGHTfp-FKkvWKLA8ChVc")
GROUP_ID = os.getenv("GROUP_ID", "-2286707356")
ADMIN_ID = os.getenv("ADMIN_ID", "6967780222")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_invoices = {}

# Webhook Handler for Telegram (optional)
async def telegram_webhook(request):
    data = await request.json()
    update = Update.to_object(data)
    await dp.process_update(update)
    return web.Response()

# NOWPayments Webhook Handler
async def nowpayments_webhook(request):
    data = await request.json()
    status = data.get("payment_status")
    description = data.get("order_description", "")
    invoice_id = data.get("payment_id", "N/A")
    amount = data.get("price_amount", "97.00")
    
    telegram_id = None
    if ' - ' in description:
        _, telegram_id = description.split(' - ')
        telegram_id = telegram_id.strip()

    if status == "confirmed" and telegram_id:
        # ✅ Add user to group
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember",
            data={"chat_id": GROUP_ID, "user_id": telegram_id}
        )

        # ✅ Retrieve username from payment log (optional)
        username = "N/A"
        try:
            with open("payments_log.csv", "r") as file:
                for row in reversed(list(csv.reader(file))):
                    if telegram_id == row[1]:
                        username = row[2]
                        break
        except:
            pass

        # ✅ Log confirmed payment
        with open("confirmed_payments.csv", "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now(), telegram_id, username, amount, invoice_id])

        # ✅ Clear in-memory invoice
        try:
            telegram_id_int = int(telegram_id)
            if telegram_id_int in user_invoices:
                del user_invoices[telegram_id_int]
        except:
            pass

        # ✅ Notify admin
        notify_msg = f"✅ {username} just PAID {amount} BTC!\nTelegram ID: {telegram_id}\nInvoice: {invoice_id}"
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": ADMIN_ID, "text": notify_msg}
        )

        print(f"✅ Confirmed: {telegram_id} was added + logged")

    return web.Response()

# Create aiohttp app and routes
app = web.Application()
app.router.add_post("/telegram-webhook", telegram_webhook)
app.router.add_post("/nowpayments-webhook", nowpayments_webhook)

# Run server
if __name__ == '__main__':
    web.run_app(app, port=8080)
