"""
Dai Kasekor (Farmer's Hand) — Telegram storefront bot
------------------------------------------------------
A demo Telegram bot for selling farm hand tools (hoe, sickle, etc.).
No real payment is processed — checkout just confirms order details
and (optionally) forwards the order to an admin chat.

Setup:
  1. pip install -r requirements.txt
  2. Copy .env.example to .env and fill in BOT_TOKEN (and ADMIN_CHAT_ID)
  3. python bot.py

See README.md for how to get a bot token and deploy this for real.
"""

import json
import logging
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

  load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # optional: your own Telegram chat id
ORDERS_FILE = Path(__file__).parent / "orders.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---- Catalog (keep this in sync with the website's product list) ----
PRODUCTS = [
    {"id": "hoe", "name": "Hoe (ចប)", "desc": "For tilling and weeding garden or paddy soil.", "price": 6.50},
    {"id": "sickle", "name": "Sickle (កណ្ដៀវ)", "desc": "Curved blade for harvesting rice and cutting grass.", "price": 4.00},
    {"id": "rake", "name": "Garden Rake", "desc": "Clears debris and levels soil before planting.", "price": 5.50},
    {"id": "machete", "name": "Machete", "desc": "Heavy blade for clearing brush.", "price": 8.00},
    {"id": "watercan", "name": "Watering Can", "desc": "6-litre galvanized can for seedling beds.", "price": 7.20},
    {"id": "plowblade", "name": "Plow Blade", "desc": "Replacement steel blade for hand-pulled plows.", "price": 11.00},
]
PRODUCTS_BY_ID = {p["id"]: p for p in PRODUCTS}

# ---- Conversation states for checkout ----
ASK_NAME, ASK_PHONE, ASK_ADDRESS = range(3)


def get_cart(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault("cart", {})


def cart_total(cart: dict) -> float:
    return sum(PRODUCTS_BY_ID[pid]["price"] * qty for pid, qty in cart.items())


def main_menu_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🛒 Browse tools / មើលទំនិញ", callback_data="browse")],
        [InlineKeyboardButton("🧺 View cart / មើលកន្ត្រក", callback_data="view_cart")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "សូមស្វាគមន៍មកកាន់ *ដៃកសិករ* 👋\n"
        "Welcome to *Dai Kasekor — Farmer's Hand Tools*.\n\n"
        "Browse our hand tools below and add what you need to your cart. "
        "This is a demo shop — no real payment is taken."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_markup())


async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(f"{p['name']} — ${p['price']:.2f}", callback_data=f"view_{p['id']}")]
        for p in PRODUCTS
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="menu")])
    await query.edit_message_text(
        "*Our tools / ទំនិញរបស់យើង*\nTap an item to see details.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def view_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = query.data.replace("view_", "")
    p = PRODUCTS_BY_ID[pid]
    keyboard = [
        [InlineKeyboardButton("➕ Add to cart", callback_data=f"add_{pid}")],
        [InlineKeyboardButton("⬅️ Back to list", callback_data="browse")],
    ]
    text = f"*{p['name']}*\n{p['desc']}\n\nPrice: ${p['price']:.2f}"
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pid = query.data.replace("add_", "")
    cart = get_cart(context)
    cart[pid] = cart.get(pid, 0) + 1
    await query.answer(f"Added {PRODUCTS_BY_ID[pid]['name']} to cart ✅")
    await view_product(update, context)


def render_cart_text(cart: dict) -> str:
    if not cart:
        return "Your cart is empty. Tap *Browse tools* to add something."
    lines = ["*Your cart / កន្ត្រករបស់អ្នក*\n"]
    for pid, qty in cart.items():
        p = PRODUCTS_BY_ID[pid]
        lines.append(f"• {p['name']} x{qty} — ${p['price']*qty:.2f}")
    lines.append(f"\n*Total: ${cart_total(cart):.2f}*")
    return "\n".join(lines)


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cart = get_cart(context)
    keyboard = []
    for pid in cart:
        p = PRODUCTS_BY_ID[pid]
        keyboard.append([
            InlineKeyboardButton(f"− {p['name']}", callback_data=f"remove_{pid}"),
            InlineKeyboardButton(f"+ {p['name']}", callback_data=f"add_{pid}"),
        ])
    if cart:
        keyboard.append([InlineKeyboardButton("✅ Checkout", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton("🛒 Browse more", callback_data="browse")])
    keyboard.append([InlineKeyboardButton("⬅️ Menu", callback_data="menu")])
    await query.edit_message_text(
        render_cart_text(cart), parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def remove_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pid = query.data.replace("remove_", "")
    cart = get_cart(context)
    if pid in cart:
        cart[pid] -= 1
        if cart[pid] <= 0:
            del cart[pid]
    await query.answer()
    await view_cart(update, context)


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "What would you like to do? / តើអ្នកចង់ធ្វើអ្វី?", reply_markup=main_menu_markup()
    )


# ---- Checkout conversation ----

async def checkout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cart = get_cart(context)
    if not cart:
        await query.edit_message_text("Your cart is empty.", reply_markup=main_menu_markup())
        return ConversationHandler.END
    await query.edit_message_text(
        "This is a demo checkout — no real payment is taken.\n\n"
        "What's your full name? / តើអ្នកឈ្មោះអ្វី?"
    )
    return ASK_NAME


async def checkout_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["checkout_name"] = update.message.text.strip()
    await update.message.reply_text("What's your phone number? / លេខទូរស័ព្ទ?")
    return ASK_PHONE


async def checkout_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["checkout_phone"] = update.message.text.strip()
    await update.message.reply_text(
        "What's your delivery address (village, commune, district, province)? / អាសយដ្ឋានដឹកជញ្ជូន?"
    )
    return ASK_ADDRESS


async def checkout_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["checkout_address"] = update.message.text.strip()
    cart = get_cart(context)
    order_ref = f"DK-{random.randint(100000, 999999)}"

    order = {
        "ref": order_ref,
        "user_id": update.effective_user.id,
        "username": update.effective_user.username,
        "name": context.user_data["checkout_name"],
        "phone": context.user_data["checkout_phone"],
        "address": context.user_data["checkout_address"],
        "items": [
            {"id": pid, "name": PRODUCTS_BY_ID[pid]["name"], "qty": qty,
             "price": PRODUCTS_BY_ID[pid]["price"]}
            for pid, qty in cart.items()
        ],
        "total": cart_total(cart),
    }
    save_order(order)

    summary = render_cart_text(cart)
    await update.message.reply_text(
        f"✅ *Order placed!* Reference `{order_ref}`\n\n"
        f"{summary}\n\n"
        f"Name: {order['name']}\nPhone: {order['phone']}\nAddress: {order['address']}\n\n"
        "This is a demo — we'll contact you to confirm final price and payment. "
        "No money has been charged.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_markup(),
    )

    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(f"🆕 New order {order_ref}\n{summary}\n\n"
                      f"Name: {order['name']}\nPhone: {order['phone']}\nAddress: {order['address']}"),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            log.warning("Could not notify admin: %s", e)

    context.user_data["cart"] = {}
    return ConversationHandler.END


async def checkout_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checkout cancelled.", reply_markup=main_menu_markup())
    return ConversationHandler.END


def save_order(order: dict):
    orders = []
    if ORDERS_FILE.exists():
        try:
            orders = json.loads(ORDERS_FILE.read_text())
        except json.JSONDecodeError:
            orders = []
    orders.append(order)
    ORDERS_FILE.write_text(json.dumps(orders, indent=2, ensure_ascii=False))


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    app = Application.builder().token(BOT_TOKEN).build()

    checkout_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern="^checkout$")],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_phone)],
            ASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, checkout_address)],
        },
        fallbacks=[CommandHandler("cancel", checkout_cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(checkout_conv)
    app.add_handler(CallbackQueryHandler(browse, pattern="^browse$"))
    app.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(add_to_cart, pattern="^add_"))
    app.add_handler(CallbackQueryHandler(remove_from_cart, pattern="^remove_"))
    app.add_handler(CallbackQueryHandler(view_product, pattern="^view_"))

    log.info("Bot starting (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
