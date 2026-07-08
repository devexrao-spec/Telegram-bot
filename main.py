from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)


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


async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = """
━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id="6093562529978522804">🛒</tg-emoji> <b>PANNEL STORE — SHOP</b>
━━━━━━━━━━━━━━━━━━━━

<tg-emoji emoji-id="6179339404906079822">📦</tg-emoji> Choose a product:
"""

    keyboard = [
        [
            InlineKeyboardButton(
                text="DRIP CLIENT NON-ROOT",
                callback_data="/SHOP_P1"
            )
        ],
        [
            InlineKeyboardButton(
                text="PROXY SERVER [DR-CL]",
                callback_data="/SHOP_P2"
            )
        ],
        [
            InlineKeyboardButton(
                text="PRIME HOOK",
                callback_data="/SHOP_P4"
            )
        ],
        [
            InlineKeyboardButton(
                text="BACK",
                callback_data="/backkkk"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        if "Message is not modified" not in str(e):
            raise e


async def back_to_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
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

    try:
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        if "Message is not modified" not in str(e):
            raise e


async def product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product = query.data

    if product == "/SHOP_P1":
        product_name = "DRIP CLIENT NON-ROOT"
    elif product == "/SHOP_P2":
        product_name = "PROXY SERVER [DR-CL]"
    elif product == "/SHOP_P4":
        product_name = "PRIME HOOK"
    else:
        product_name = "Unknown Product"

    text = f"""
<b>Product Selected:</b>

<tg-emoji emoji-id="6179339404906079822">📦</tg-emoji> {product_name}

Please continue with payment or contact support.
"""

    keyboard = [
        [
            InlineKeyboardButton(
                text="BACK",
                callback_data="/shopnawkk"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )


def main():
    BOT_TOKEN = "8828131983:AAHf7iP4dm-qhcnm8nayCzNNXVyQlSvEpls"

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # BUY HACK button handler
    app.add_handler(CallbackQueryHandler(shop_menu, pattern="^/shopnawkk$"))

    # BACK button handler
    app.add_handler(CallbackQueryHandler(back_to_home, pattern="^/backkkk$"))

    # Product buttons handler
    app.add_handler(CallbackQueryHandler(product_handler, pattern="^/SHOP_P"))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
