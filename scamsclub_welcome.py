import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# Enable logs
logging.basicConfig(level=logging.INFO)

# Replace with your actual bot token
BOT_TOKEN = "7152782887:AAFbItSrIW2uYXHqGHTfp-FKkvWKLA8ChVc"

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# Handle new members joining the group
@dp.chat_member_handler()
async def handle_new_member(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        user = event.new_chat_member.user

        # Create an inline keyboard with a Start button
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                text="📩 Start Here",
                url="https://t.me/ScamsClub_Bot?start=welcome"
            )
        )

        welcome_text = (
            f"👋 Welcome <b>{user.full_name}</b> to <b>Scam’s Plus 🏪</b>\n\n"
            "Start exploring tools, walkthroughs, and methods (simulation only):"
        )

        await bot.send_message(chat_id=event.chat.id, text=welcome_text, reply_markup=keyboard)

# Handle /start in DM with ?start=welcome
@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    args = message.get_args()

    if args == "welcome":
        await message.answer(
            "👋 Thanks for joining Scam’s Club Store 🏪\n\n"
            "You now have access to:\n"
            "📚 /methods – Explore simulated guides\n"
            "🛠 /tools – OTP bots, spoofers, etc.\n"
            "💳 /banklogs – Walkthroughs and log shops\n"
            "🎓 /mentorship – Learn 1-on-1 (mock)\n"
            "🧠 /faq – Learn the language\n"
            "📜 /terms – Simulation disclaimer\n\n"
            "DM @ScamsClub_Store if you need help."
        )

# Run the bot
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)