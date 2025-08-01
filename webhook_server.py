from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = '7152782887:AAFbItSrIW2uYXHqGHTfp-FKkvWKLA8ChVc'
GROUP_ID = '-2286707356'
ADMIN_ID = '6967780222'  

# Optional: shared memory invoice tracking (if used)
user_invoices = {}

def log_confirmed_payment(telegram_id, username, amount, invoice_id):
    with open("confirmed_payments.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), telegram_id, username, amount, invoice_id])

def add_user_to_group(telegram_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember"
    payload = {
        'chat_id': GROUP_ID,
        'user_id': telegram_id
    }
    requests.post(url, data=payload)

def notify_admin(telegram_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    text = f"💸 Payment confirmed for Telegram user `{telegram_id}`.\nThey've been added to the group."
    payload = {
        'chat_id': ADMIN_ID,
        'text': text,
        'parse_mode': 'Markdown'
    }
    requests.post(url, data=payload)

@app.route("/nowpayments-webhook", methods=["POST"])
def nowpayments_webhook():
    data = request.get_json()
    status = data.get("payment_status")
    description = data.get("order_description", "")
    invoice_id = data.get("payment_id", "N/A")  # Optional fallback
    amount = data.get("price_amount", "97.00")
    
    if ' - ' in description:
        _, telegram_id = description.split(' - ')
    else:
        telegram_id = None

    if status == "confirmed" and telegram_id:
        telegram_id = telegram_id.strip()
        add_user_to_group(telegram_id)

        # Optional: look up username from CSV
        username = "N/A"
        try:
            with open("payments_log.csv", "r") as file:
                for row in reversed(list(csv.reader(file))):
                    if telegram_id == row[1]:  # chat_id is in column 1
                        username = row[2]
                        break
        except:
            pass

        # ✅ Log confirmed payment
        log_confirmed_payment(telegram_id, username, amount, invoice_id)

        # ✅ Auto-remove from memory
        try:
            telegram_id_int = int(telegram_id)
            if telegram_id_int in user_invoices:
                del user_invoices[telegram_id_int]
        except:
            pass

        # ✅ Notify admin
        admin_id = 6967780222  # Replace if needed
        notify_msg = f"✅ {username} just PAID {amount} BTC!\nTelegram ID: {telegram_id}\nInvoice: {invoice_id}"
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": admin_id, "text": notify_msg}
        )

        print(f"✅ Confirmed: {telegram_id} was added + logged")
    return '', 200