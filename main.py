from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)


# Simple in-memory storage
# Production ke liye database use karna better hai
user_data = {}
balances = {}


def get_home_text(balance):
    return (
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


def get_home_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(
                text="BUY HACK",
                callback_data="/shopnawkk",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "6093739864883207194"
                }
            )
        ],
        [
            InlineKeyboardButton(
                text="MY KEY",
                callback_data="/orderksk",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "5967456680940671207"
                }
            ),
            InlineKeyboardButton(
                text="PROFILE",
                callback_data="/profilemmm",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "5346136537123801643"
                }
            )
        ],
        [
            InlineKeyboardButton(
                text="HOW TO USE",
                callback_data="/spinj",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "5345783284653636765"
                }
            ),
            InlineKeyboardButton(
                text="SUPPORT",
                callback_data="/supportj",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "5897567714674741148"
                }
            )
        ],
        [
            InlineKeyboardButton(
                text="ADD FUND",
                callback_data="/addpayment",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "6278302366303260172"
                }
            )
        ],
        [
            InlineKeyboardButton(
                text="PAY PROOF",
                url="https://t.me/subhajit_feedback",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "5258134813302332906"
                }
            ),
            InlineKeyboardButton(
                text="DOWNLOAD APK",
                url="https://t.me/+hasTLSVjzaZjZGVl",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "6028115612163641653"
                }
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def get_shop_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(
                text="DRIP CLIENT NON-ROOT",
                callback_data="/SHOP_P1",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "6323104647636589287"
                }
            )
        ],
        [
            InlineKeyboardButton(
                text="PROXY SERVER [DR-CL]",
                callback_data="/SHOP_P2",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "6212942266957310140"
                }
            )
        ],
        [
            InlineKeyboardButton(
                text="PRIME HOOK",
                callback_data="/SHOP_P4",
                api_kwargs={
                    "style": "success",
                    "icon_custom_emoji_id": "6210705396449944693"
                }
            )
        ],
        [
            InlineKeyboardButton(
                text="BACK",
                callback_data="/backkkk",
                api_kwargs={
                    "style": "danger",
                    "icon_custom_emoji_id": "6039539366177541657"
                }
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    if user.id not in user_data:
        user_data[user.id] = {
            "joined_date": update.message.date
        }

    balance = balances.get(user.id, 0)

    await context.bot.send_message(
        chat_id=chat_id,
        text=get_home_text(balance),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=get_home_keyboard()
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

    try:
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_shop_keyboard(),
            disable_web_page_preview=True
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            raise e


async def back_to_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    balance = balances.get(user.id, 0)

    try:
        await query.edit_message_text(
            text=get_home_text(balance),
            parse_mode=ParseMode.HTML,
            reply_markup=get_home_keyboard(),
            disable_web_page_preview=True
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            raise e


async def product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product = query.data

    if product == "/SHOP_P1":
        product_name = "DRIP CLIENT NON-ROOT"
        product_emoji_id = "6323104647636589287"
    elif product == "/SHOP_P2":
        product_name = "PROXY SERVER [DR-CL]"
        product_emoji_id = "6212942266957310140"
    elif product == "/SHOP_P4":
        product_name = "PRIME HOOK"
        product_emoji_id = "6210705396449944693"
    else:
        product_name = "Unknown Product"
        product_emoji_id = "6179339404906079822"

    text = f"""
━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id="{product_emoji_id}">📦</tg-emoji> <b>{product_name}</b>
━━━━━━━━━━━━━━━━━━━━

<b>Product Selected:</b>

<tg-emoji emoji-id="6179339404906079822">📦</tg-emoji> Product: <b>{product_name}</b>

Please continue with payment or contact support.
"""

    keyboard = [
        [
            InlineKeyboardButton(
                text="BACK",
                callback_data="/shopnawkk",
                api_kwargs={
                    "style": "danger",
                    "icon_custom_emoji_id": "6039539366177541657"
                }
            )
        ]
    ]

    try:
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            raise e


async def my_key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = """
<blockquote>
<tg-emoji emoji-id="5967456680940671207">🔑</tg-emoji> <b>MY KEY</b>
</blockquote>

You don't have any active key yet.
"""

    keyboard = [
        [
            InlineKeyboardButton(
                text="BACK",
                callback_data="/backkkk",
                api_kwargs={
                    "style": "danger",
                    "icon_custom_emoji_id": "6039539366177541657"
                }
            )
        ]
    ]

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )


async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    balance = balances.get(user.id, 0)
    joined_date = user_data.get(user.id, {}).get("joined_date", "Not saved")

    text = f"""
<blockquote>
<tg-emoji emoji-id="5346136537123801643">👤</tg-emoji> <b>PROFILE</b>
</blockquote>

<b>Name:</b> {user.first_name or "User"}
<b>User ID:</b> <code>{user.id}</code>
<b>Balance:</b> ₹{balance}
<b>Joined:</b> {joined_date}
"""

    keyboard = [
        [
            InlineKeyboardButton(
                text="BACK",
                callback_data="/backkkk",
                api_kwargs={
                    "style": "danger",
                    "icon_custom_emoji_id": "6039539366177541657"
                }
            )
        ]
    ]

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )


async def how_to_use_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = """
<blockquote>
<tg-emoji emoji-id="5345783284653636765">📖</tg-emoji> <b>HOW TO USE</b>
</blockquote>

1. Click on BUY HACK.
2. Choose your product.
3. Add fund.
4. Contact support if you need help.
"""

    keyboard = [
        [
            InlineKeyboardButton(
                text="BACK",
                callback_data="/backkkk",
                api_kwargs={
                    "style": "danger",
                    "icon_custom_emoji_id": "6039539366177541657"
                }
            )
        ]
    ]

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )


async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = """
<blockquote>
<tg-emoji emoji-id="5897567714674741148">🛠</tg-emoji> <b>SUPPORT</b>
</blockquote>

For support, contact admin.
"""

    keyboard = [
        [
            InlineKeyboardButton(
                text="BACK",
                callback_data="/backkkk",
                api_kwargs={
                    "style": "danger",
                    "icon_custom_emoji_id": "6039539366177541657"
                }
            )
        ]
    ]

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )


async def add_fund_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = """
<blockquote>
<tg-emoji emoji-id="6278302366303260172">💰</tg-emoji> <b>ADD FUND</b>
</blockquote>

Add fund system coming soon.
"""

    keyboard = [
        [
            InlineKeyboardButton(
                text="BACK",
                callback_data="/backkkk",
                api_kwargs={
                    "style": "danger",
                    "icon_custom_emoji_id": "6039539366177541657"
                }
            )
        ]
    ]

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )


def main():
    BOT_TOKEN = "8828131983:AAHf7iP4dm-qhcnm8nayCzNNXVyQlSvEpls"

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(shop_menu, pattern="^/shopnawkk$"))
    app.add_handler(CallbackQueryHandler(back_to_home, pattern="^/backkkk$"))

    app.add_handler(CallbackQueryHandler(product_handler, pattern="^/SHOP_P"))

    app.add_handler(CallbackQueryHandler(my_key_handler, pattern="^/orderksk$"))
    app.add_handler(CallbackQueryHandler(profile_handler, pattern="^/profilemmm$"))
    app.add_handler(CallbackQueryHandler(how_to_use_handler, pattern="^/spinj$"))
    app.add_handler(CallbackQueryHandler(support_handler, pattern="^/supportj$"))
    app.add_handler(CallbackQueryHandler(add_fund_handler, pattern="^/addpayment$"))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
