
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

CATEGORIES = {
    "normal": "💎 Normal Diamonds",
    "double": "💜 Double Diamonds",
    "weekly": "🎫 Weekly Pass",
    "twilight": "🌙 Twilight Pass"
}


def db():
    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package TEXT UNIQUE NOT NULL,
            price INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS product_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            package TEXT NOT NULL,
            price INTEGER NOT NULL,
            UNIQUE(category, package)
        )
    """)

    # Preserve existing Normal Diamond prices
    conn.execute("""
        INSERT OR IGNORE INTO product_prices
        (category, package, price)
        SELECT 'normal', package, price FROM prices
    """)

    conn.commit()
    return conn


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Normal Diamonds", callback_data="cat:normal")],
        [InlineKeyboardButton("💜 Double Diamonds", callback_data="cat:double")],
        [InlineKeyboardButton("🎫 Weekly Pass", callback_data="cat:weekly")],
        [InlineKeyboardButton("🌙 Twilight Pass", callback_data="cat:twilight")],
        [InlineKeyboardButton("📝 Order Drafts", callback_data="orders"),
         InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("📊 Sales Records", callback_data="sales"),
         InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ])


def product_menu(category):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Price", callback_data=f"add:{category}")],
        [InlineKeyboardButton("📋 View Prices", callback_data=f"view:{category}")],
        [InlineKeyboardButton("✏️ Edit Price", callback_data=f"edit:{category}")],
        [InlineKeyboardButton("🗑️ Delete Price", callback_data=f"delete:{category}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sorry, this bot is private.")
        return

    context.user_data.clear()
    await update.message.reply_text(
        "Welcome to Kelly's Diamond Bot! 💜\n\n👑 Admin Dashboard",
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
        await q.edit_message_text(
            "👑 Kelly's Admin Dashboard",
            reply_markup=main_menu()
        )
        return

    if data.startswith("cat:"):
        category = data.split(":", 1)[1]
        context.user_data.clear()
        await q.edit_message_text(
            f"{CATEGORIES[category]}\n\nPRICE MANAGEMENT",
            reply_markup=product_menu(category)
        )
        return

    if ":" in data:
        action, category = data.split(":", 1)

        if category not in CATEGORIES:
            return

        if action == "add":
            context.user_data.clear()
            context.user_data["category"] = category
            context.user_data["action"] = "add_package"
            await q.edit_message_text(
                f"➕ ADD {CATEGORIES[category]}\n\n"
                "Enter package name:\n"
                "Example: 86 Diamonds"
            )

        elif action == "view":
            conn = db()
            rows = conn.execute(
                "SELECT package, price FROM product_prices "
                "WHERE category = ? ORDER BY id",
                (category,)
            ).fetchall()
            conn.close()

            if rows:
                msg = f"📋 {CATEGORIES[category]} PRICE LIST\n\n"
                for package, price in rows:
                    msg += f"• {package} — {price:,} Ks\n"
            else:
                msg = "No prices saved yet."

            await q.edit_message_text(
                msg,
                reply_markup=product_menu(category)
            )

        elif action in ("edit", "delete"):
            context.user_data.clear()
            context.user_data["category"] = category
            context.user_data["action"] = (
                "edit_package" if action == "edit"
                else "delete_package"
            )

            title = "EDIT" if action == "edit" else "DELETE"
            await q.edit_message_text(
                f"✏️ {title} PRICE\n\n"
                "Enter the exact package name:"
            )

        return

    if data in ("orders", "balance", "sales", "settings"):
        await q.edit_message_text(
            "This section will be developed next.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="home")]
            ])
        )


async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    action = context.user_data.get("action")
    if not action:
        return

    value = update.message.text.strip()

    if not value:
        await update.message.reply_text("Please enter a valid value.")
        return

    category = context.user_data.get("category", "normal")

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
                "INSERT INTO product_prices "
                "(category, package, price) VALUES (?, ?, ?)",
                (category, package, price)
            )
            conn.commit()
            conn.close()

            context.user_data.clear()

            await update.message.reply_text(
                f"✅ Saved!\n"
                f"{CATEGORIES[category]}\n"
                f"📦 {package}\n"
                f"💰 {price:,} Ks",
                reply_markup=product_menu(category)
            )

        except sqlite3.IntegrityError:
            context.user_data["action"] = "add_package"
            await update.message.reply_text(
                "This package already exists. Enter a different name:"
            )

        except ValueError:
            await update.message.reply_text(
                "Please enter a valid price, e.g. 7000"
            )

    elif action in ("edit_package", "delete_package"):
        conn = db()
        row = conn.execute(
            "SELECT id, price FROM product_prices "
            "WHERE category = ? AND package = ?",
            (category, value)
        ).fetchone()

        if not row:
            conn.close()
            await update.message.reply_text(
                "Package not found. Check the exact name and try again."
            )
            return

        if action == "delete_package":
            conn.execute(
                "DELETE FROM product_prices WHERE id = ?",
                (row[0],)
            )
            conn.commit()
            conn.close()

            context.user_data.clear()

            await update.message.reply_text(
                f"🗑️ Deleted: {value}",
                reply_markup=product_menu(category)
            )

        else:
            conn.close()
            context.user_data["edit_id"] = row[0]
            context.user_data["edit_package_name"] = value
            context.user_data["action"] = "edit_price"

            await update.message.reply_text(
                f"Current price: {row[1]:,} Ks\n"
                "Enter new Channel Price:"
            )

    elif action == "edit_price":
        try:
            price = int(value.replace(",", "").replace(" ", ""))
            if price <= 0:
                raise ValueError

            conn = db()
            conn.execute(
                "UPDATE product_prices SET price = ? WHERE id = ?",
                (price, context.user_data["edit_id"])
            )
            conn.commit()
            conn.close()

            package = context.user_data["edit_package_name"]
            context.user_data.clear()

            await update.message.reply_text(
                f"✅ Updated!\n"
                f"📦 {package}\n"
                f"💰 {price:,} Ks",
                reply_markup=product_menu(category)
            )

        except ValueError:
            await update.message.reply_text(
                "Please enter a valid price in Ks."
            )


def main():
    # Initialize and migrate database
    conn = db()
    conn.close()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, messages)
    )

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="telegram",
        webhook_url=f"{BASE_URL}/telegram",
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
            
