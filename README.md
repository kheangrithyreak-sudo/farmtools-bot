# ដៃកសិករ (Dai Kasekor) — Telegram Bot

A demo Telegram storefront bot for selling farm hand tools (hoe, sickle, and more). It mirrors the product catalog on the companion website. No real payment is processed yet — checkout just collects name, phone, and address, then confirms the order.

## 1. Create your bot and get a token

1. Open Telegram and message **@BotFather**.
2. Send `/newbot` and follow the prompts (choose a display name and a unique username ending in `bot`, e.g. `DaiKasekorBot`).
3. BotFather will reply with a token that looks like `123456789:AA...`. Copy it.

## 2. (Optional) Get your admin chat id

If you want the bot to notify you when a new order comes in:

1. Message **@userinfobot** on Telegram.
2. It replies with your numeric chat id — copy it.

## 3. Configure

```bash
cd farmtools-bot
cp .env.example .env
```

Open `.env` and paste in:
- `BOT_TOKEN` — the token from BotFather
- `ADMIN_CHAT_ID` — your chat id from step 2 (optional, leave blank to skip)

## 4. Install and run locally

```bash
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

Open Telegram, find your bot by its username, and send `/start`.

Orders are appended to `orders.json` in this folder as they come in.

## 5. Editing the product catalog

Products live near the top of `bot.py` in the `PRODUCTS` list. Add, remove, or reprice items there. **Keep this list the same as the product list in `farmtools-store.html`** (the website) so customers see the same items and prices in both places — this demo doesn't share a live database between them yet (see "Next steps" below).

## 6. Deploying so it runs all the time

Running `python bot.py` on your own laptop only works while your laptop is on and connected. To keep the bot running permanently, deploy it to a small always-on host, for example:

- **Railway** or **Render** — connect this folder to a GitHub repo, set `BOT_TOKEN` and `ADMIN_CHAT_ID` as environment variables in their dashboard, and set the start command to `python bot.py`.
- **A cheap VPS** (e.g. DigitalOcean, Vultr) — copy the folder over, install Python, and run the bot inside `tmux`, `screen`, or as a `systemd` service so it survives reboots.

This bot uses polling (`app.run_polling()`), so no public URL or webhook setup is required — it just needs to keep running somewhere.

## Next steps for a real production shop

This is a working demo, not a production system. Before you take real orders and payment:

- **Shared catalog/database**: right now the website and bot each have their own copy of the product list. For a real shop, move products into a small database (e.g. SQLite, or a hosted one like Supabase) and have both the website and bot read from it, so updating a price or stock level updates everywhere at once.
- **Real payment**: for Cambodia, look into ABA PayWay or a bank/Wing manual-transfer flow where an admin confirms payment before the order ships.
- **Order management**: `orders.json` is fine for a demo; a real shop will want orders in a proper database with a simple admin view.
- **Hosting the website**: the HTML file works as-is when opened directly, but for a public store put it on real hosting (e.g. Vercel, Netlify, or a basic web host) with your own domain.
