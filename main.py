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

# ===========================
# /admin
# ===========================

from telegram import ReplyKeyboardMarkup

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    if uid not in ADMINS:
        await update.message.reply_text("🚫 You Are Not Admin")
        return

    keyboard = [
        ["ᴀᴅᴍɪɴꜱ"],
        ["ʙᴏᴛ ᴏɴ", "ʙᴏᴛ ꜱᴛᴏᴘ"],
        ["ꜱᴇᴛ ᴄʜᴀɴɴᴇʟ 1", "ꜱᴇᴛ ᴄʜᴀɴɴᴇʟ 2", "ꜱᴇᴛ ᴄʜᴀɴɴᴇʟ 3"],
        ["ꜱᴇᴛ ᴄʜᴀɴɴᴇʟ 4", "ꜱᴇᴛ ᴄʜᴀɴɴᴇʟ 5", "ꜱᴇᴛ ᴄʜᴀɴɴᴇʟ 6"],
        ["ꜱᴇᴛ ᴄʜᴀɴɴᴇʟ 7"],
        ["ꜱᴡɪᴛᴄʜ 𝟓 ʙᴜᴛᴛᴏɴ", "ꜱᴡɪᴛᴄʜ 𝟕 ʙᴜᴛᴛᴏɴ"],
        ["ꜱᴇᴛ ᴘʜᴏᴛᴏ", "ꜱᴇᴛ ꜱᴛᴀʀᴛ ᴛᴇxᴛ"],
        ["ʙʀᴏᴀᴅᴄᴀꜱᴛ"],
        ["ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ"]
    ]

    await update.message.reply_text(
        "✅ ADMIN PANEL",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
    )

# ===========================
# SWITCH 7 BUTTON MODE
# ===========================

AllBotAdminss = Bot.getData("AllBotAdminss") or []

is_Admin = False

# If no admin exists, assign owner automatically
if not AllBotAdminss:
    MAIN_ADMIN = u
    AllBotAdminss.append(MAIN_ADMIN)
    Bot.saveData("AllBotAdminss", AllBotAdminss)
    Bot.saveData("Owner", u)
    is_Admin = True

# Check admin access
for userid in AllBotAdminss:
    if str(u) == str(userid):
        is_Admin = True
        break

# Not admin → block access
if not is_Admin:
    bot.replyText(
        u,
        "<b><i>🚫 You Are Not This Bot Admin</i></b>",
        parse_mode="html"
    )
    raise ReturnCommand()

# Save button mode
Bot.saveData("button_count", 7)

# Response
bot.sendMessage("✅ Switched to 7 Buttons")

# ===========================
# SWITCH 5 BUTTON MODE
# ===========================

AllBotAdminss = Bot.getData("AllBotAdminss") or []

is_Admin = False

# Auto assign owner if no admin exists
if not AllBotAdminss:
    MAIN_ADMIN = u
    AllBotAdminss.append(MAIN_ADMIN)
    Bot.saveData("AllBotAdminss", AllBotAdminss)
    Bot.saveData("Owner", u)
    is_Admin = True

# Check admin access
for userid in AllBotAdminss:
    if str(u) == str(userid):
        is_Admin = True
        break

# Not admin → block access
if not is_Admin:
    bot.replyText(
        u,
        "<b><i>🚫 You Are Not This Bot Admin</i></b>",
        parse_mode="html"
    )
    raise ReturnCommand()

# Save button mode
Bot.saveData("button_count", 5)

# Response
bot.sendMessage("✅ Switched to 5 Buttons")


if message.text == "ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ":

    admins = ["7937757398", "8102646437", "7669606015"]

    if str(message.from_user.id) not in admins:
        raise ReturnCommand()

    users = Bot.getData("users") or []

    total = len(users)

    bot.sendMessage(
        chat_id=message.chat.id,
        text=f"👥 <b>ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ :</b> <code>{total}</code>",
        parse_mode="html"
    )

    ADMINS = ["7937757398", "8102646437", "7669606015"]


def is_admin(user_id):
    return str(user_id) in ADMINS


def send_message(chat_id, text):
    requests.post(URL + "/sendMessage", data={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    })


# =========================
# WEBHOOK ROUTE
# =========================
@app.route("/", methods=["GET"])
def home():
    return "Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_id = str(message["from"]["id"])
    text = message.get("text", "")

    # =========================
    # SET START TEXT (ADMIN)
    # =========================
    if text == "ꜱᴇᴛ ꜱᴛᴀʀᴛ ᴛᴇxᴛ":

        if not is_admin(user_id):
            send_message(chat_id, "🚫 You Are Not This Bot Admin")
            return "ok"

        send_message(chat_id, "📩 Send me Start Message Text")
        NEXT_CMD[user_id] = "save_start_text"
        return "ok"

    # =========================
    # SAVE START TEXT
    # =========================
    if NEXT_CMD.get(user_id) == "save_start_text":

        if not is_admin(user_id):
            send_message(chat_id, "🚫 Not Allowed")
            return "ok"

        DATA["start_text"] = text

        send_message(
            chat_id,
            "✅ Start message saved successfully\n\n" + text
        )

        NEXT_CMD.pop(user_id, None)
        return "ok"

    # =========================
    # TOTAL START
    # =========================
    if text == "/start":
        send_message(
            chat_id,
            DATA.get("start_text", "👋 Default Start Message")
        )
        return "ok"

    return "ok"


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
