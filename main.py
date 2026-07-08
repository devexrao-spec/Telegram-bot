from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
import json
import os

# ================= CONFIG =================

BOT_TOKEN = "8828131983:AAHf7iP4dm-qhcnm8nayCzNNXVyQlSvEpls"

ADMINS = [8102646437, 7937757398]

PHOTO = "https://i.postimg.cc/ryC2ypLJ/IMG-20250929-182323-680.jpg"

START_TEXT = "Welcome To The Bot!"

CHANNELS = [
    "https://t.me/+hd8XwDL8030yNzE1",
    "https://t.me/+hd8XwDL8030yNzE1",
    "https://t.me/+hd8XwDL8030yNzE1",
]

DB = "users.json"

# ================= DATABASE =================

if not os.path.exists(DB):
    with open(DB, "w") as f:
        json.dump([], f)


def load_users():
    with open(DB, "r") as f:
        return json.load(f)


def save_users(users):
    with open(DB, "w") as f:
        json.dump(users, f)


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    uid = user.id

    users = load_users()

    new = False

    if uid not in users:
        users.append(uid)
        save_users(users)
        new = True

    total = len(users)

    text = (
        f"{'🚨 NEW USER' if new else '♻️ OLD USER'}\n\n"
        f"👤 Name : {user.first_name}\n"
        f"🆔 ID : {uid}\n"
        f"📛 Username : @{user.username}\n\n"
        f"👥 Total Users : {total}"
    )

    for admin in ADMINS:
        try:
            await context.bot.send_message(admin, text)
        except:
            pass

    keyboard = []

    for i, link in enumerate(CHANNELS, start=1):
        keyboard.append(
            [InlineKeyboardButton(f"CHANNEL {i}", url=link)]
        )

    keyboard.append(
        [InlineKeyboardButton("CHECK JOINED ✅", url="https://t.me/")]
    )

    await context.bot.send_photo(
        chat_id=uid,
        photo=PHOTO,
        caption=f"👋 Hello {user.first_name}\n\n{START_TEXT}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        # ================= ADMIN =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ You Are Not Admin.")
        return

    users = load_users()

    text = (
        "🛠 ADMIN PANEL\n\n"
        f"👥 Total Users : {len(users)}\n"
        "🤖 Bot Status : ONLINE"
    )

    await update.message.reply_text(text)


# ================= BROADCAST =================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ You Are Not Admin.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n/broadcast Your Message"
        )
        return

    msg = " ".join(context.args)

    users = load_users()

    success = 0
    failed = 0

    for uid in users:
        try:
            await context.bot.send_message(uid, msg)
            success += 1
        except:
            failed += 1

    await update.message.reply_text(
        f"✅ Broadcast Complete\n\n"
        f"Success : {success}\n"
        f"Failed : {failed}"
    )


# ================= USERS =================

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMINS:
        return

    total = len(load_users())

    await update.message.reply_text(
        f"👥 Total Users : {total}"
        # ================= MAIN =================

def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", users))

    print("🤖 Bot Started Successfully...")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
    )
    )
