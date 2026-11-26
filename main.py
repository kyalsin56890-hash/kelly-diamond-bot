
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "Sorry, this bot is private."
        )
        return

    await update.message.reply_text(
        "Welcome to Kelly's Diamond Bot! 💜\n\n"
        "Admin Panel is ready."
    )


def main():
    if not BOT_TOKEN or not ADMIN_ID:
        raise ValueError("BOT_TOKEN or ADMIN_ID is missing.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("Kelly's Diamond Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
  
