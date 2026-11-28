
import os
import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = os.environ["RENDER_EXTERNAL_URL"].rstrip("/")

DB_NAME = (
    "/var/data/kelly_prices.db"
    if os.path.isdir("/var/data")
    else "kelly_prices.db"
)

CATEGORIES = {
    "normal": "💎 Normal Diamonds",
    "double": "💜 Double Diamonds",
    "weekly": "🎫 Weekly Pass",
    "twilight": "🌙 Twilight Pass",
}


def db():
    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS product_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            package TEXT NOT NULL,
            price INTEGER NOT NULL,
            UNIQUE(category, package)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL,
            server_id TEXT NOT NULL,
            category TEXT NOT NULL,
            package TEXT NOT NULL,
            price INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            supplier_cost INTEGER,
            profit INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS wallet (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            balance INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.execute("""
        INSERT OR IGNORE INTO wallet (id, balance)
        VALUES (1, 0)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS balance_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            note TEXT,
            order_id INTEGER,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    return conn


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Normal Diamonds", callback_data="cat:normal")],
        [InlineKeyboardButton("💜 Double Diamonds", callback_data="cat:double")],
        [InlineKeyboardButton("🎫 Weekly Pass", callback_data="cat:weekly")],
        [InlineKeyboardButton("🌙 Twilight Pass", callback_data="cat:twilight")],
        [InlineKeyboardButton("📝 Order Management", callback_data="orders")],
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("📊 Sales", callback_data="sales"),
        ],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
    ])


def product_menu(category):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Price", callback_data=f"add:{category}")],
        [InlineKeyboardButton("📋 View Prices", callback_data=f"view:{category}")],
        [InlineKeyboardButton("✏️ Edit Price", callback_data=f"edit:{category}")],
        [InlineKeyboardButton("🗑️ Delete Price", callback_data=f"delete:{category}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")],
    ])


def orders_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create New Order", callback_data="order_new")],
        [InlineKeyboardButton("⏳ Pending Orders", callback_data="order_list:pending")],
        [InlineKeyboardButton("✅ Completed Orders", callback_data="order_list:completed")],
        [InlineKeyboardButton("❌ Cancelled Orders", callback_data="order_list:cancelled")],
        [InlineKeyboardButton("📚 All Order History", callback_data="order_list:all")],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sorry, this bot is private.")
        return

    context.user_data.clear()

    await update.message.reply_text(
        "💜 Welcome to Kelly's Boutique!\n\n"
        "👑 ADMIN DASHBOARD\n\n"
        "Select an option below:",
        reply_markup=main_menu(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data.clear()

    await update.message.reply_text(
        "Action cancelled.",
        reply_markup=main_menu(),
    )


async def show_order(message, order_id):
    conn = db()

    row = conn.execute("""
        SELECT player_id, server_id, category,
               package, price, status, created_at
        FROM orders WHERE id = ?
    """, (order_id,)).fetchone()

    conn.close()

    if not row:
        await message.edit_message_text("Order not found.")
        return

    player, server, category, package, price, status, created = row

    status_text = {
        "pending": "⏳ Pending",
        "completed": "✅ Completed",
        "cancelled": "❌ Cancelled",
    }.get(status, status)

    keyboard = []

    if status == "pending":
        keyboard.append([
            InlineKeyboardButton(
                "✅ Complete",
                callback_data=f"order_status:{order_id}:completed",
            ),
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data=f"order_status:{order_id}:cancelled",
            ),
        ])

    keyboard.append([
        InlineKeyboardButton("⬅️ Order History", callback_data="order_list:all")
    ])

    keyboard.append([
        InlineKeyboardButton("🏠 Main Menu", callback_data="home")
    ])

    await message.edit_message_text(
        f"📝 ORDER #{order_id}\n\n"
        f"👤 Player ID: {player}\n"
        f"🌐 Server ID: {server}\n"
        f"📦 Category: {CATEGORIES.get(category, category)}\n"
        f"💎 Package: {package}\n"
        f"💰 Price: {price:,} Ks\n"
        f"📌 Status: {status_text}\n"
        f"🕒 Created: {created}",
        reply_markup=InlineKeyboardMarkup(keyboard),
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
            "👑 KELLY'S BOUTIQUE\n\nADMIN DASHBOARD",
            reply_markup=main_menu(),
        )
        return

    if data == "orders":
        context.user_data.clear()
        await q.edit_message_text(
            "📝 ORDER MANAGEMENT",
            reply_markup=orders_menu(),
        )
        return

    if data == "balance":
        conn = db()
        balance = conn.execute(
            "SELECT balance FROM wallet WHERE id = 1"
        ).fetchone()[0]
        conn.close()

        await q.edit_message_text(
            f"💰 WALLET BALANCE\n\n{balance:,} Ks",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="home")]
            ]),
        )
        return

    if data == "settings":
        await q.edit_message_text(
            "⚙️ SETTINGS\n\n"
            "Shop: Kelly's Boutique\n"
            "Admin Access: ON\n"
            "Supplier: Juvirastore\n"
            "API: Not connected yet\n"
            "Auto Top Up: Not connected yet",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="home")]
            ]),
        )
        return

    if data == "sales":
        conn = db()

        count, total = conn.execute("""
            SELECT COUNT(*), COALESCE(SUM(price), 0)
            FROM orders WHERE status = 'completed'
        """).fetchone()

        conn.close()

        await q.edit_message_text(
            f"📊 SALES RECORDS\n\n"
            f"✅ Completed Orders: {count}\n"
            f"💰 Total Sales: {total:,} Ks",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="home")]
            ]),
        )
        return

    if data.startswith("cat:"):
        category = data.split(":")[1]

        if category not in CATEGORIES:
            return

        context.user_data.clear()

        await q.edit_message_text(
            f"{CATEGORIES[category]}\n\nPRICE MANAGEMENT",
            reply_markup=product_menu(category),
        )
        return

    if data.startswith(("add:", "edit:", "delete:", "view:")):
        action, category = data.split(":", 1)

        if category not in CATEGORIES:
            return

        if action == "view":
            conn = db()
            rows = conn.execute("""
                SELECT package, price
                FROM product_prices
                WHERE category = ?
                ORDER BY id
            """, (category,)).fetchall()
            conn.close()

            msg = f"📋 {CATEGORIES[category]}\n\n"

            if rows:
                for package, price in rows:
                    msg += f"💎 {package} — {price:,} Ks\n"
            else:
                msg += "No prices saved yet."

            await q.edit_message_text(
                msg,
                reply_markup=product_menu(category),
            )
            return

        context.user_data.clear()
        context.user_data["category"] = category

        if action == "add":
            context.user_data["action"] = "add_package"
            prompt = "➕ Enter package name:"
        elif action == "edit":
            context.user_data["action"] = "edit_package"
            prompt = "✏️ Enter the exact package name to edit:"
        else:
            context.user_data["action"] = "delete_package"
            prompt = "🗑️ Enter the exact package name to delete:"

        await q.edit_message_text(
            prompt,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data=f"cat:{category}")]
            ]),
        )
        return

    if data == "order_new":
        context.user_data.clear()
        context.user_data["action"] = "order_player"

        await q.edit_message_text(
            "➕ CREATE NEW ORDER\n\nEnter Player ID:"
        )
        return

    if data.startswith("ordercat:"):
        category = data.split(":")[1]

        if category not in CATEGORIES:
            return

        conn = db()
        rows = conn.execute("""
            SELECT id, package, price
            FROM product_prices
            WHERE category = ?
            ORDER BY id
        """, (category,)).fetchall()
        conn.close()

        if not rows:
            await q.edit_message_text(
                "No packages available.",
                reply_markup=orders_menu(),
            )
            return

        context.user_data["order_category"] = category

        keyboard = [
            [InlineKeyboardButton(
                f"{package} — {price:,} Ks",
                callback_data=f"orderpkg:{pid}",
            )]
            for pid, package, price in rows
        ]

        keyboard.append([
            InlineKeyboardButton("⬅️ Back", callback_data="orders")
        ])

        await q.edit_message_text(
            f"📦 {CATEGORIES[category]}\n\nSelect Package:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("orderpkg:"):
        pid = int(data.split(":")[1])

        conn = db()
        row = conn.execute("""
            SELECT category, package, price
            FROM product_prices WHERE id = ?
        """, (pid,)).fetchone()
        conn.close()

        if not row:
            await q.edit_message_text("Package not found.")
            return

        category, package, price = row

        context.user_data["order_category"] = category
        context.user_data["order_package"] = package
        context.user_data["order_price"] = price

        await q.edit_message_text(
            f"📦 {package}\n"
            f"💰 {price:,} Ks\n\n"
            f"Player ID: {context.user_data['player_id']}\n"
            f"Server ID: {context.user_data['server_id']}\n\n"
            "Confirm this order?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm Order", callback_data="order_confirm")],
                [InlineKeyboardButton("❌ Cancel", callback_data="orders")],
            ]),
        )
        return

    if data == "order_confirm":
        info = context.user_data

        required = [
            "player_id",
            "server_id",
            "order_category",
            "order_package",
            "order_price",
        ]

        if not all(key in info for key in required):
            await q.edit_message_text(
                "Order information missing. Start again.",
                reply_markup=orders_menu(),
            )
            return

        conn = db()

        cursor = conn.execute("""
            INSERT INTO orders (
                player_id, server_id, category,
                package, price, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (
            info["player_id"],
            info["server_id"],
            info["order_category"],
            info["order_package"],
            info["order_price"],
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))

        order_id = cursor.lastrowid
        conn.commit()
        conn.close()

        package = info["order_package"]
        price = info["order_price"]

        context.user_data.clear()

        await q.edit_message_text(
            f"✅ ORDER CREATED!\n\n"
            f"📝 Order ID: #{order_id}\n"
            f"📦 Package: {package}\n"
            f"💰 Price: {price:,} Ks\n"
            f"📌 Status: Pending",
            reply_markup=orders_menu(),
        )
        return

    if data.startswith("order_list:"):
        status = data.split(":")[1]

        conn = db()

        if status == "all":
            rows = conn.execute("""
                SELECT id, player_id, package, price, status
                FROM orders ORDER BY id DESC LIMIT 30
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, player_id, package, price, status
                FROM orders
                WHERE status = ?
                ORDER BY id DESC LIMIT 30
            """, (status,)).fetchall()

        conn.close()

        if not rows:
            await q.edit_message_text(
                "No orders found.",
                reply_markup=orders_menu(),
            )
            return

        keyboard = []
        msg = "📚 ORDER HISTORY\n\n"

        for oid, player, package, price, state in rows:
            emoji = {
                "pending": "⏳",
                "completed": "✅",
                "cancelled": "❌",
            }.get(state, "")

            msg += (
                f"{emoji} #{oid} | {package}\n"
                f"Player: {player} | {price:,} Ks\n\n"
            )

            keyboard.append([
                InlineKeyboardButton(
                    f"Order #{oid} {emoji}",
                    callback_data=f"order_view:{oid}",
                )
            ])

        keyboard.append([
            InlineKeyboardButton("⬅️ Back", callback_data="orders")
        ])

        await q.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("order_view:"):
        order_id = int(data.split(":")[1])
        await show_order(q, order_id)
        return

    if data.startswith("order_status:"):
        _, order_id, new_status = data.split(":")
        order_id = int(order_id)

        if new_status not in ("completed", "cancelled"):
            return

        conn = db()
        conn.execute("""
            UPDATE orders SET status = ?
            WHERE id = ? AND status = 'pending'
        """, (new_status, order_id))
        conn.commit()
        conn.close()

        await show_order(q, order_id)
        return


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

    if action == "order_player":
        context.user_data["player_id"] = value
        context.user_data["action"] = "order_server"

        await update.message.reply_text("Enter Server ID:")
        return

    if action == "order_server":
        context.user_data["server_id"] = value
        context.user_data["action"] = None

        keyboard = [
            [InlineKeyboardButton(
                name,
                callback_data=f"ordercat:{key}",
            )]
            for key, name in CATEGORIES.items()
        ]

        keyboard.append([
            InlineKeyboardButton("⬅️ Back", callback_data="orders")
        ])

        await update.message.reply_text(
            "Select Diamond Category:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    category = context.user_data.get("category", "normal")

    if action == "add_package":
        context.user_data["package"] = value
        context.user_data["action"] = "add_price"

        await update.message.reply_text(
            f"📦 Package: {value}\n\nEnter selling price in Ks:"
        )
        return

    if action == "add_price":
        try:
            price = int(value.replace(",", "").replace(" ", ""))

            if price <= 0:
                raise ValueError

            conn = db()
            conn.execute("""
                INSERT INTO product_prices (category, package, price)
                VALUES (?, ?, ?)
            """, (category, context.user_data["package"], price))
            conn.commit()
            conn.close()

            package = context.user_data["package"]
            context.user_data.clear()

            await update.message.reply_text(
                f"✅ PRICE SAVED!\n\n"
                f"📦 {package}\n"
                f"💰 {price:,} Ks",
                reply_markup=product_menu(category),
            )

        except sqlite3.IntegrityError:
            context.user_data["action"] = "add_package"
            await update.message.reply_text(
                "Package already exists. Enter another name:"
            )

        except ValueError:
            await update.message.reply_text(
                "Enter a valid price, e.g. 7000"
            )
        return

    if action in ("edit_package", "delete_package"):
        conn = db()

        row = conn.execute("""
            SELECT id, price FROM product_prices
            WHERE category = ? AND package = ?
        """, (category, value)).fetchone()

        if not row:
            conn.close()
            await update.message.reply_text(
                "Package not found. Check the exact name."
            )
            return

        if action == "delete_package":
            conn.execute(
                "DELETE FROM product_prices WHERE id = ?",
                (row[0],),
            )
            conn.commit()
            conn.close()

            context.user_data.clear()

            await update.message.reply_text(
                f"🗑️ Deleted: {value}",
                reply_markup=product_menu(category),
            )
        else:
            conn.close()

            context.user_data["edit_id"] = row[0]
            context.user_data["edit_package_name"] = value
            context.user_data["action"] = "edit_price"

            await update.message.reply_text(
                f"Current price: {row[1]:,} Ks\n"
                "Enter new price:"
            )
        return

    if action == "edit_price":
        try:
            price = int(value.replace(",", "").replace(" ", ""))

            if price <= 0:
                raise ValueError

            conn = db()
            conn.execute("""
                UPDATE product_prices SET price = ?
                WHERE id = ?
            """, (price, context.user_data["edit_id"]))
            conn.commit()
            conn.close()

            package = context.user_data["edit_package_name"]
            context.user_data.clear()

            await update.message.reply_text(
                f"✅ PRICE UPDATED!\n\n"
                f"📦 {package}\n"
                f"💰 {price:,} Ks",
                reply_markup=product_menu(category),
            )

        except ValueError:
            await update.message.reply_text(
                "Enter a valid price in Ks."
            )


def main():
    conn = db()
    conn.close()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
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
