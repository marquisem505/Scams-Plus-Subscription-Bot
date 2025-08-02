import os
import openai
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from base64 import b64decode, b64encode

# 🔐 ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GITHUB_PAT = os.getenv("GITHUB_PAT")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
BRANCH = os.getenv("BRANCH", "main")
TARGET_FILE = os.getenv("TARGET_FILE")
RAILWAY_DEPLOY_URL = os.getenv("RAILWAY_DEPLOY_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🤖 GPT Request
async def ask_gpt(prompt: str) -> str:
    openai.api_key = OPENAI_API_KEY
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're a Python developer assistant. Only return raw valid Python code with no markdown formatting or comments."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    content = response.choices[0].message.content

    # ✂️ Clean markdown and extract valid Python
    lines = content.splitlines()
    lines = [line for line in lines if not line.strip().startswith("```")]
    try:
        start_index = next(i for i, line in enumerate(lines) if line.strip().startswith("import"))
        clean_code = "\n".join(lines[start_index:])
    except StopIteration:
        clean_code = "\n".join(lines)

    return clean_code

# 📥 Get file contents from GitHub
def get_file_contents():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{TARGET_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_PAT}"}
    response = requests.get(url, headers=headers)
    content = response.json()["content"]
    return b64decode(content).decode()

# 📤 Push file update to GitHub
def push_to_github(updated_code: str):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{TARGET_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_PAT}"}
    current = requests.get(url, headers=headers).json()
    data = {
        "message": "Auto update from Telegram",
        "content": b64encode(updated_code.encode()).decode(),
        "sha": current["sha"],
        "branch": BRANCH
    }
    response = requests.put(url, headers=headers, json=data)
    return response.status_code == 200

# 🚀 Trigger Railway deployment
def trigger_deploy():
    try:
        response = requests.post(f"{RAILWAY_DEPLOY_URL}/__rebuild", timeout=10)
        return response.status_code in [200, 204]
    except:
        return False

# 🧠 Message handler
async def handle_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ Unauthorized.")
        return

    prompt = update.message.text.strip()
    await update.message.reply_text("✍️ Thinking...")

    current_code = get_file_contents()
    new_code = await ask_gpt(
        f"Here is a Python Telegram bot file:\n\n{current_code}\n\nPlease update it based on this instruction:\n\n{prompt}"
    )

    success = push_to_github(new_code)
    if not success:
        await update.message.reply_text("❌ Failed to update GitHub.")
        return

    deployed = trigger_deploy()
    status = "✅ Update pushed & deployed!" if deployed else "✅ Update pushed, but deploy not confirmed."

    await update.message.reply_text(f"{status}\n\n🔧 Summary:\n{prompt}")

# 🤖 Command handler
def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text('Hey there, dev!')

# 🚀 App launcher
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_instruction))
    app.add_handler(CommandHandler('hello', hello))
    app.run_polling()
