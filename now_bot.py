Your code already contains a /status command that shows the expiration date of the user's subscription. Here is the relevant part of your code:

```python
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    expiry = subscription_expiry.get(chat_id)

    if expiry:
        await context.bot.send_message(chat_id=chat_id, text=f"📊 Your subscription expires on: **{expiry.strftime('%Y-%m-%d')}**", parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ No active subscription found.")
```

This function is already set up to handle the /status command. When a user sends the /status command, the bot checks if the user has an active subscription and sends a message with the expiration date. If the user does not have an active subscription, the bot sends a message saying "No active subscription found."

The command is also already added to the application:

```python
application.add_handler(CommandHandler("status", status))
```

So, there is no need to update the code as the /status command is already implemented as per your requirements.