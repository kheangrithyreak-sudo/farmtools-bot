"""
Telcom Tech — Telegram storefront bot
------------------------------------------------------
A demo Telegram bot for selling PBX and phone systems (IKE PBX, Panaphone, etc.).
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
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
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

if Path(".env").exists():
    load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # optional: your own Telegram chat id
ORDERS_FILE = Path(__file__).parent / "orders.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---- Catalog (keep this in sync with the website's product list) ----
PRODUCTS = [
    {"id": "pbx408p", "name": "IKE PBX 408P", "desc": "Analog PBX telephone system for small offices and shops.", "price": 70.00},
    {"id": "pbx416p", "name": "IKE PBX 416P", "desc": "Analog PBX telephone system for small offices and guesthouses.", "price": 120.00},
    {"id": "pbx424p", "name": "IKE PBX 424P", "desc": "Analog PBX telephone system for offices, factories and guesthouses.", "price": 170.00},
    {"id": "pbx432p", "name": "IKE PBX 432P", "desc": "Analog PBX telephone system for larger offices and schools.", "price": 220.00},
    {"id": "pbx2000b", "name": "IKE PBX 2000B (64EXT)", "desc": "Analog PBX telephone system for schools, hospitals and hotels — 64 extensions.", "price": 420.00},
    {"id": "panaphone", "name": "Panaphone Call ID", "desc": "Corded desk phone with caller ID display.", "price": 15.00},
]
PRODUCTS_BY_ID = {p["id"]: p for p in PRODUCTS}

# ---- Conversation states for checkout ----
ASK_NAME, ASK_PHONE, ASK_ADDRESS = range(3)


def get_cart(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault("cart", {})


def cart_total(cart: dict) -> float:
    return sum(PRODUCTS_BY_ID[pid]["price"] * qty for pid, qty in cart.items())


SHOP_URL = "https://kheangrithyreak-sudo.github.io/TelcomTech_store/"
CONTACT_URL = "https://t.me/NopRavy7"  # opens the owner's personal Telegram chat
MENU_BUTTON_TEXT = "🏠 Menu"


def main_menu_markup() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🛒 Browse products / មើលទំនិញ", callback_data="browse")],
        [InlineKeyboardButton("🧺 View cart / មើលកន្ត្រក", callback_data="view_cart")],
        [InlineKeyboardButton("📞 Contact us / ទាក់ទងយើង", url=CONTACT_URL)],
    ]
    return InlineKeyboardMarkup(keyboard)


def shop_keyboard() -> ReplyKeyboardMarkup:
    # A Mini App opened from a *keyboard* button (unlike an inline button)
    # is allowed to send data back to the bot via Telegram.WebApp.sendData().
    # is_persistent keeps these buttons on screen so customers never have to
    # type /start again.
    return ReplyKeyboardMarkup(
        [[
            KeyboardButton("🛖 Open Shop", web_app=WebAppInfo(url=SHOP_URL)),
            KeyboardButton(MENU_BUTTON_TEXT),
        ]],
        resize_keyboard=True,
        is_persistent=True,
    )


def seen_button_markup(order_ref: str, customer_chat_id: int) -> InlineKeyboardMarkup:
    # Encodes the order ref and the customer's chat id right into the button,
    # so tapping it later needs no extra lookup.
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Mark as Seen (notify customer)", callback_data=f"seen_{order_ref}_{customer_chat_id}")]]
    )


async def mark_order_seen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        _, order_ref, customer_chat_id = query.data.split("_", 2)
        customer_chat_id = int(customer_chat_id)
    except (ValueError, IndexError):
        await query.answer("Something went wrong reading this button.", show_alert=True)
        return

    try:
        await context.bot.send_message(
            chat_id=customer_chat_id,
            text=(f"👀 Good news — we've seen your order `{order_ref}` and we're getting it ready. "
                  "We'll be in touch shortly to confirm details and payment."),
            parse_mode=ParseMode.MARKDOWN,
        )
        await query.answer("Customer notified ✅")
        # Replace the button with a plain confirmation so it can't be tapped twice.
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"✅ Notified the customer for order {order_ref}.")
    except Exception as e:
        log.warning("Could not notify customer: %s", e)
        await query.answer("Failed to notify the customer — they may have blocked the bot.", show_alert=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "សូមស្វាគមន៍មកកាន់ *Telcom Tech* 👋\n"
        "Welcome to *Telcom Tech — PBX and Phone Shop*.\n\n"
        "Browse our Telcom Tech Shop and add what you need to your cart. "
        "This is a demo shop — no real payment is taken."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_markup())
    await update.message.reply_text(
        "Use the buttons at the bottom any time — no need to type /start:",
        reply_markup=shop_keyboard(),
    )


async def text_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Any plain message outside checkout brings the menu back."""
    if update.message.text == MENU_BUTTON_TEXT:
        await update.message.reply_text(
            "What would you like to do? / តើអ្នកចង់ធ្វើអ្វី?",
            reply_markup=main_menu_markup(),
        )
    else:
        # Someone typed something else (or their bottom buttons vanished):
        # show the full welcome again, which also restores the buttons.
        await start(update, context)


async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(f"{p['name']} — ${p['price']:.2f}", callback_data=f"view_{p['id']}")]
        for p in PRODUCTS
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="menu")])
    await query.edit_message_text(
        "*Our products / ទំនិញរបស់យើង*\nTap an item to see details.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def render_product_view(update: Update, context: ContextTypes.DEFAULT_TYPE, pid: str):
    query = update.callback_query
    p = PRODUCTS_BY_ID[pid]
    keyboard = [
        [InlineKeyboardButton("➕ Add to cart", callback_data=f"add_{pid}")],
        [InlineKeyboardButton("⬅️ Back to list", callback_data="browse")],
    ]
    text = f"*{p['name']}*\n{p['desc']}\n\nPrice: ${p['price']:.2f}"
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


async def view_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = query.data.replace("view_", "")
    await render_product_view(update, context, pid)


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pid = query.data.replace("add_", "")
    cart = get_cart(context)
    cart[pid] = cart.get(pid, 0) + 1
    await query.answer(f"Added {PRODUCTS_BY_ID[pid]['name']} to cart ✅")
    await render_product_view(update, context, pid)


def render_cart_text(cart: dict) -> str:
    if not cart:
        return "Your cart is empty. Tap *Browse products* to add something."
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
    order_ref = f"TT-{random.randint(100000, 999999)}"
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    order = {
        "ref": order_ref,
        "date": order_date,
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
        f"✅ *Order placed!* Reference `{order_ref}`\n"
        f"Date: {order_date}\n\n"
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
                text=(f"🆕 New order {order_ref}\nDate: {order_date}\n{summary}\n\n"
                      f"Name: {order['name']}\nPhone: {order['phone']}\nAddress: {order['address']}"),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=seen_button_markup(order_ref, update.effective_user.id),
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
            orders = json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            orders = []
    orders.append(order)
    ORDERS_FILE.write_text(json.dumps(orders, indent=2, ensure_ascii=False), encoding="utf-8")


async def web_app_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle an order submitted from the website Mini App via sendData()."""
    raw = update.effective_message.web_app_data.data
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, AttributeError):
        await update.message.reply_text(
            "Sorry, something went wrong reading that order — please try again.",
            reply_markup=main_menu_markup(),
        )
        return

    order_ref = payload.get("ref") or f"TT-{random.randint(100000, 999999)}"
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    name = payload.get("name", "")
    phone = payload.get("phone", "")
    address = payload.get("address", "")
    items = payload.get("items", [])
    total = payload.get("total", 0)

    lines = ["*Your order / ការបញ្ជាទិញរបស់អ្នក*\n"]
    for item in items:
        lines.append(f"• {item.get('name')} x{item.get('qty')} — ${item.get('price', 0) * item.get('qty', 0):.2f}")
    lines.append(f"\n*Total: ${total:.2f}*")
    summary = "\n".join(lines)

    order = {
        "ref": order_ref,
        "date": order_date,
        "user_id": update.effective_user.id,
        "username": update.effective_user.username,
        "name": name,
        "phone": phone,
        "address": address,
        "items": items,
        "total": total,
        "source": "mini_app",
    }
    save_order(order)

    await update.message.reply_text(
        f"✅ *Order placed!* Reference `{order_ref}`\n"
        f"Date: {order_date}\n\n"
        f"{summary}\n\n"
        f"Name: {name}\nPhone: {phone}\nAddress: {address}\n\n"
        "This is a demo — we'll contact you to confirm final price and payment. "
        "No money has been charged.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_markup(),
    )

    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(f"🆕 New order (Mini App) {order_ref}\nDate: {order_date}\n{summary}\n\n"
                      f"Name: {name}\nPhone: {phone}\nAddress: {address}"),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=seen_button_markup(order_ref, update.effective_user.id),
            )
        except Exception as e:
            log.warning("Could not notify admin: %s", e)


async def post_init(application: Application):
    """Runs once when the bot starts. Sets the command list and the intro
    text people see above Telegram's built-in START button."""
    try:
        await application.bot.set_my_commands([BotCommand("start", "Open the shop menu")])
        await application.bot.set_my_description(
            "សូមស្វាគមន៍មកកាន់ Telcom Tech\n"
            "Telcom Tech — PBX and Phone Shop. Tap START to browse IKE PBX systems "
            "and Panaphone phones, then order right here in Telegram."
        )
    except Exception as e:
        log.warning("Could not update the bot's description/commands: %s", e)


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # The bottom "Menu" button sends this exact text. During checkout it must not
    # be mistaken for a name/phone/address answer.
    menu_text = filters.Regex(f"^{MENU_BUTTON_TEXT}$")
    answer = filters.TEXT & ~filters.COMMAND & ~menu_text

    checkout_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout_start, pattern="^checkout$")],
        states={
            ASK_NAME: [MessageHandler(answer, checkout_name)],
            ASK_PHONE: [MessageHandler(answer, checkout_phone)],
            ASK_ADDRESS: [MessageHandler(answer, checkout_address)],
        },
        fallbacks=[
            CommandHandler("cancel", checkout_cancel),
            MessageHandler(menu_text, checkout_cancel),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(checkout_conv)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_order))
    # Must come after the checkout conversation so it never steals checkout answers.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_fallback))
    app.add_handler(CallbackQueryHandler(browse, pattern="^browse$"))
    app.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(add_to_cart, pattern="^add_"))
    app.add_handler(CallbackQueryHandler(remove_from_cart, pattern="^remove_"))
    app.add_handler(CallbackQueryHandler(view_product, pattern="^view_"))
    app.add_handler(CallbackQueryHandler(mark_order_seen, pattern="^seen_"))

    log.info("Bot starting (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
