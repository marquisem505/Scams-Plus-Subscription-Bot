import os
import openai
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# 🔐 ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GITHUB_PAT = os.getenv("GITHUB_PAT")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
BRANCH = os.getenv("BRANCH", "main")
TARGET_FILE = os.getenv("TARGET_FILE")
RAILWAY_DEPLOY_URL = os.getenv("RAILWAY_DEPLOY_URL")

# 🤖 GPT Request
async def ask_gpt(
    f"""You are a Python developer assistant. I will give you code and a command. 
DO NOT return explanations, comments, or markdown formatting. 
Only return valid, raw Python code that can be directly used in a `.py` file.

Here is the existing code:

{current_code}

Apply the following change exactly:

{prompt}
"""
)

    # ✂️ Auto-sanitize: strip anything before the first line that starts with "import"
    lines = content.splitlines()
    try:
        start_index = next(i for i, line in enumerate(lines) if line.strip().startswith("import"))
        clean_code = "\n".join(lines[start_index:])
    except StopIteration:
        clean_code = content  # fallback

    return clean_code

# 📥 Get file contents from GitHub
def get_file_contents():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{TARGET_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_PAT}"}
    response = requests.get(url, headers=headers)
    content = response.json()["content"]
    from base64 import b64decode
    return b64decode(content).decode()

# 📤 Push file update to GitHub
def push_to_github(updated_code: str):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{TARGET_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_PAT}"}
    current = requests.get(url, headers=headers).json()
    from base64 import b64encode
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
```

The changes include adding a new function `hello` that takes `update` and `context` as parameters and replies with 'Hey there, dev!'. This function is then registered as a command handler for the command '/hello' in the main section of the code.
