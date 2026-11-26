

import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = os.environ["RENDER_EXTERNAL_URL"].rstrip("/")
DB_NAME = "/var/data/kelly_prices.db" if os.path.isdir("/var/data") else "kelly_prices.db"


def db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package TEXT UNIQUE NOT NULL,
            price INTEGER NOT NULL
        )
    """)
    return conn


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Diamond Prices", callback_data="prices")],
        [InlineKeyboardButton("🎫 Weekly Pass", callback_data="weekly")],
        [InlineKeyboardButton("📝 Order Drafts", callback_data="orders"),
         InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("📊 Sales Records", callback_data="sales"),
         InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ])


def price_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Price", callback_data="add")],
        [InlineKeyboardButton("📋 View Prices", callback_data="view")],
        [InlineKeyboardButton("✏️ Edit Price", callback_data="edit")],
        [InlineKeyboardButton("🗑️ Delete Price", callback_data="delete")],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")]
    ])


def back_price():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Diamond Prices", callback_data="prices")]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sorry, this bot is private.")
        return
    context.user_data.clear()
    await update.message.reply_text(
        "Welcome to Kelly's Diamond Bot! 💜\n\nAdmin Dashboard",
        reply_markup=main_menu()
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("Private Admin Only!", show_alert=True)
        return
    await q.answer()
    data = q.data

    if data == "home":
        context.user_data.clear()
        await q.edit_message_text("👑 Kelly's Admin Dashboard", reply_markup=main_menu())
    elif data == "prices":
        context.user_data.clear()
        await q.edit_message_text("💎 DIAMOND PRICE MANAGEMENT", reply_markup=price_menu())
    elif data == "add":
        context.user_data["action"] = "add_package"
        await q.edit_message_text(
            "➕ ADD DIAMOND PRICE\n\nEnter package name:\nExample: 86 Diamonds"
        )
    elif data == "view":
        conn = db()
        rows = conn.execute("SELECT package, price FROM prices ORDER BY id").fetchall()
        conn.close()
        if rows:
            msg = "📋 DIAMOND PRICE LIST\n\n"
            for package, price in rows:
                msg += f"💎 {package} — {price:,} Ks\n"
        else:
            msg = "No diamond prices saved yet."
        await q.edit_message_text(msg, reply_markup=back_price())
    elif data == "edit":
        context.user_data["action"] = "edit_package"
        await q.edit_message_text(
            "✏️ EDIT PRICE\n\nEnter the exact package name you want to edit:"
        )
    elif data == "delete":
        context.user_data["action"] = "delete_package"
        await q.edit_message_text(
            "🗑️ DELETE PRICE\n\nEnter the exact package name you want to delete:"
        )
    elif data in ("weekly", "orders", "balance", "sales", "settings"):
        await q.edit_message_text(
            "This section will be developed next.",
            reply_markup=back_price()
        )


async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    action = context.user_data.get("action")
    if not action:
        return

    value = update.message.text.strip()

    if action == "add_package":
        context.user_data["package"] = value
        context.user_data["action"] = "add_price"
        await update.message.reply_text(
            f"Package: {value}\n\nEnter Channel Price in Ks:"
        )

    elif action == "add_price":
        try:
            price = int(value.replace(",", "").replace(" ", ""))
            if price <= 0:
                raise ValueError
            package = context.user_data["package"]
            conn = db()
            conn.execute(
                "INSERT INTO prices (package, price) VALUES (?, ?)",
                (package, price)
            )
            conn.commit()
            conn.close()
            context.user_data.clear()
            await update.message.reply_text(
                f"✅ Saved!\n💎 {package}\n💰 {price:,} Ks",
                reply_markup=price_menu()
            )
        except sqlite3.IntegrityError:
            context.user_data["action"] = "add_package"
            await update.message.reply_text("This package already exists. Enter a different name:")
        except ValueError:
            await update.message.reply_text("Please enter a valid price, e.g. 1550")

    elif action in ("edit_package", "delete_package"):
        conn = db()
        row = conn.execute(
            "SELECT id, price FROM prices WHERE package = ?", (value,)
        ).fetchone()

        if not row:
            conn.close()
            await update.message.reply_text("Package not found. Check the exact name and try again.")
            return

        if action == "delete_package":
            conn.execute("DELETE FROM prices WHERE id = ?", (row[0],))
            conn.commit()
            conn.close()
            context.user_data.clear()
            await update.message.reply_text(
                f"🗑️ Deleted: {value}", reply_markup=price_menu()
            )
        else:
            conn.close()
            context.user_data["edit_id"] = row[0]
            context.user_data["edit_package_name"] = value
            context.user_data["action"] = "edit_price"
            await update.message.reply_text(
                f"Current price: {row[1]:,} Ks\nEnter new Channel Price:"
            )

    elif action == "edit_price":
        try:
            price = int(value.replace(",", "").replace(" ", ""))
            if price <= 0:
                raise ValueError
            conn = db()
            conn.execute(
                "UPDATE prices SET price = ? WHERE id = ?",
                (price, context.user_data["edit_id"])
            )
            conn.commit()
            conn.close()
            package = context.user_data["edit_package_name"]
            context.user_data.clear()
            await update.message.reply_text(
                f"✅ Updated!\n💎 {package}\n💰 {price:,} Ks",
                reply_markup=price_menu()
            )
        except ValueError:
            await update.message.reply_text("Please enter a valid price in Ks.")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="telegram",
        webhook_url=f"{BASE_URL}/telegram",
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()

