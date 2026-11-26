

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = os.environ["RENDER_EXTERNAL_URL"].rstrip("/")


def admin_menu():
    keyboard = [
        [
            InlineKeyboardButton("💎 Diamond Prices", callback_data="prices"),
            InlineKeyboardButton("🎫 Weekly Pass", callback_data="weekly"),
        ],
        [
            InlineKeyboardButton("📝 Order Drafts", callback_data="orders"),
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
        ],
        [
            InlineKeyboardButton("📊 Sales Records", callback_data="sales"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Admin Menu", callback_data="home")]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sorry, this bot is private.")
        return

    await update.message.reply_text(
        "Welcome to Kelly's Diamond Bot! 💜\n\n"
        "👑 Admin Dashboard\n"
        "Choose an option below:",
        reply_markup=admin_menu()
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sorry, this bot is private.")
        return

    await update.message.reply_text(
        "👑 Kelly's Admin Dashboard 💜",
        reply_markup=admin_menu()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer("Private Admin Only!", show_alert=True)
        return

    await query.answer()

    pages = {
        "prices": "💎 DIAMOND PRICE MANAGEMENT\n\nDiamond price management is ready.\nNext: Add and edit diamond prices.",
        "weekly": "🎫 WEEKLY PASS MANAGEMENT\n\nWeekly Pass: 6,550 MMK\nNext: Edit Weekly Pass price.",
        "orders": "📝 ORDER DRAFTS\n\nNo order drafts yet.",
        "balance": "💰 BALANCE MANAGEMENT\n\nCurrent balance: 0 MMK",
        "sales": "📊 SALES RECORDS\n\nNo sales records yet.",
        "settings": "⚙️ SETTINGS\n\nKelly's Diamond Bot\nAdmin Only: Enabled",
    }

    if query.data == "home":
        await query.edit_message_text(
            "👑 Kelly's Admin Dashboard 💜\n\nChoose an option below:",
            reply_markup=admin_menu()
        )
        return

    if query.data in pages:
        await query.edit_message_text(
            pages[query.data],
            reply_markup=back_menu()
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="telegram",
        webhook_url=f"{BASE_URL}/telegram",
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()

