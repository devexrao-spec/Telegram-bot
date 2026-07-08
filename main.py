from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes


# Simple in-memory storage
# Production me database use karna better hai
user_data = {}
balances = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    # joined_date save
    if user.id not in user_data:
        user_data[user.id] = {
            "joined_date": update.message.date
        }

    first_name = user.first_name or "User"

    # Balance get
    balance = balances.get(user.id, 0)

    text = (
        "<blockquote>"
        "<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> "
        "WELCOME TO HACK STORE "
        "<tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji>"
        "</blockquote>\n\n"

        "<i>"
        "<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> "
        "Your ultimate destination for premium mods, cheats & clients!"
        "</i>\n\n"

        "<blockquote>"
        "<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> PREMIUM FEATURES\n\n"

        "<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Instant Key Delivery\n"

        "<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Secure Auto-Payment System\n"

        "<tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji> 100% Anti-Ban Support"
        "</blockquote>\n\n"

        "<blockquote>"
        "<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> "
        f"Your Balance: ₹{balance}"
        "</blockquote>"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                text="BUY HACK",
                callback_data="/shopnawkk"
            )
        ],
        [
            InlineKeyboardButton(
                text="MY KEY",
                callback_data="/orderksk"
            ),
            InlineKeyboardButton(
                text="PROFILE",
                callback_data="/profilemmm"
            )
        ],
        [
            InlineKeyboardButton(
                text="HOW TO USE",
                callback_data="/spinj"
            ),
            InlineKeyboardButton(
                text="SUPPORT",
                callback_data="/supportj"
            )
        ],
        [
            InlineKeyboardButton(
                text="ADD FUND",
                callback_data="/addpayment"
            )
        ],
        [
            InlineKeyboardButton(
                text="PAY PROOF",
                url="https://t.me/subhajit_feedback"
            ),
            InlineKeyboardButton(
                text="DOWNLOAD APK",
                url="https://t.me/+hasTLSVjzaZjZGVl"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )


def main():
    BOT_TOKEN = "8828131983:AAHf7iP4dm-qhcnm8nayCzNNXVyQlSvEpls"

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
