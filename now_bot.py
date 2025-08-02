# 🔁 Background invoice checker
async def poll_invoice_statuses():
    while True:
        await asyncio.sleep(300)  # 5 minutes
        for chat_id, invoice_id in list(user_invoices.items()):
            try:
                response = requests.get(f"https://api.nowpayments.io/v1/invoice/{invoice_id}", headers=headers)
                data = response.json()

                if data.get("payment_status") == "finished":
                    username = "User"
                    amount = "97.00"

                    # ✅ Add to Scam’s Club Plus
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/unbanChatMember",
                        data={"chat_id": GROUP_ID, "user_id": chat_id}
                    )

                    # ✅ Log payment
                    log_confirmed_payment(chat_id, username, amount, invoice_id)

                    # ✅ Notify user
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

                    # ✅ Notify admin
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

                    # ✅ Remove from tracking
                    del user_invoices[chat_id]

            except Exception as e:
                print(f"❌ Error checking invoice {invoice_id} for {chat_id}: {e}")
