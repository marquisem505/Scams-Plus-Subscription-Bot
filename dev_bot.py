import os
import openai
import requests
from base64 import b64decode, b64encode
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

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
            {"role": "system", "content": "You are a Python developer assistant. ONLY return raw .py file code. No explanations, no markdown, no comments."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    content = response.choices[0].message.content

    # ✂️ Clean up — get only code starting from the first `import`
    lines = content.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip().startswith("import"))
        return "\n".join(lines[start:])
    except StopIteration:
        return content

# 📥 Get file contents from GitHub
def get_file_contents():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{TARGET_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_PAT}"}
    res = requests.get(url, headers=headers)
    return b64decode(res.json()["content"]).decode(), res.json()["sha"]

# 📤 Push updated code to GitHub
def push_to_github(new_code: str, sha: str):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{TARGET_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_PAT}"}
    data = {
        "message": "Auto update from Telegram",
        "content": b64encode(new_code.encode()).decode(),
        "sha": sha,
        "branch": BRANCH
    }
    return requests.put(url, headers=headers, json=data).status_code == 200

# 🚀 Trigger Railway Deploy
def trigger_deploy():
    try:
        res = requests.post(f"{RAILWAY_DEPLOY_URL}/__rebuild", timeout=10)
        return res.status_code in [200, 204]
    except:
        return False

# 🧠 Instruction Handler
async def handle_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ You're not my daddy!.")
        return

    prompt = update.message.text.strip()
    await update.message.reply_text("✍️ Okay hold on...")

    current_code, sha = get_file_contents()
    final_code = await ask_gpt(
        f"""Here is the full file content:\n\n{current_code}\n\nUpdate this code according to:\n\n{prompt}"""
    )

    success = push_to_github(final_code, sha)
    deploy_success = trigger_deploy()

    status = "✅ Update pushed & deployed!" if deploy_success else "✅ Update pushed, but deploy not confirmed."
    await update.message.reply_text(
    f"{status}\n\n🔧 Summary:\n{prompt}\n\n📂 Target: {TARGET_FILE}"
    )

# 🔔 Simple /hello Command
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey there, dev!")

# 🚀 Start Bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instruction))
    app.run_polling()
