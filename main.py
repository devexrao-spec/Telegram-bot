from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
import json
import os

BOT_TOKEN = "8828131983:AAHf7iP4dm-qhcnm8nayCzNNXVyQlSvEpls"

ADMINS = [8102646437, 7937757398]

PHOTO = "https://i.postimg.cc/ryC2ypLJ/IMG-20250929-182323-680.jpg"

START_TEXT = "Welcome!"

CHANNELS = [
    "https://t.me/+hd8XwDL8030yNzE1",
    "https://t.me/+hd8XwDL8030yNzE1",
    "https://t.me/+hd8XwDL8030yNzE1",
    "https://t.me/+hd8XwDL8030yNzE1",
    "https://t.me/+hd8XwDL8030yNzE1",
    "https://t.me/+hd8XwDL8030yNzE1",
    "https://t.me/+hd8XwDL8030yNzE1",
]

DB = "users.json"

if not os.path.exists(DB):
    with open(DB, "w") as f:
        json.dump([], f)

def load_users():
    with open(DB) as f:
        return json.load(f)

def save_users(users):
    with open(DB, "w") as f:
        json.dump(users, f)

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

    for admin in ADMINS:
        try:

            text = (
                f"{'🚨 NEW USER' if new else '♻️ OLD USER'}\n\n"
                f"Name : {user.first_name}\n"
                f"ID : {uid}\n"
                f"Username : @{user.username}\n\n"
                f"Total Users : {total}"
            )

            await context.bot.send_message(
                admin,
                text
            )

        except:
            pass

    keyboard = []

    for i, link in enumerate(CHANNELS, start=1):
        keyboard.append([
            InlineKeyboardButton(f"𝐂ʜᴀɴɴᴇʟ {i}", url=link)
        ])

    keyboard.append([
        InlineKeyboardButton(
            "𝐂ʜᴇᴄᴋ 𝐉ᴏɪɴᴇᴅ ✅",
            url="https://t.me/+Mp0GYMGK-hthOTZl"
        )
    ])

    await context.bot.send_photo(
        chat_id=uid,
        photo=PHOTO,
        caption=f"𝗛𝗘𝗟𝗟𝗢 𝗨𝗦𝗘𝗥 🗿!! {user.first_name}\n\n{START_TEXT}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    try:
        await context.bot.send_document(
            chat_id=uid,
            document="https://t.me/DEVEXSETUP/23",
            caption="📁 APK FILE",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬇️ DOWNLOAD + OPEN",
                        url="https://t.me/+oaYfm6vNj0JjMTc9"
                    )
                ]
            ])
        )
    except Exception as e:
        print(e)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("Bot Started ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
