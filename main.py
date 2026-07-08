import json
from urllib.parse import urlencode
from urllib.request import urlopen

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)


# Simple in-memory storage.
# Production me database use karna better hai.
user_data = {}
balances = {}
user_orders = {}

UPI_ID = "bablu.xyztb@fam"
FAMPAY_API_KEY = "FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8"


def premium_button(text, *, callback_data=None, url=None, style="success", emoji_id=None):
    api_kwargs = {"style": style}
    if emoji_id:
        api_kwargs["icon_custom_emoji_id"] = emoji_id

    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
        url=url,
        api_kwargs=api_kwargs,
    )


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
    return InlineKeyboardMarkup(
        [
            [
                premium_button(
                    "BUY HACK",
                    callback_data="/shopnawkk",
                    emoji_id="6093739864883207194",
                )
            ],
            [
                premium_button(
                    "MY KEY",
                    callback_data="/orderksk",
                    emoji_id="5967456680940671207",
                ),
                premium_button(
                    "PROFILE",
                    callback_data="/profilemmm",
                    emoji_id="5346136537123801643",
                ),
            ],
            [
                premium_button(
                    "HOW TO USE",
                    callback_data="/spinj",
                    emoji_id="5345783284653636765",
                ),
                premium_button(
                    "SUPPORT",
                    callback_data="/supportj",
                    emoji_id="5897567714674741148",
                ),
            ],
            [
                premium_button(
                    "ADD FUND",
                    callback_data="/addpayment",
                    emoji_id="6278302366303260172",
                )
            ],
            [
                premium_button(
                    "PAY PROOF",
                    url="https://t.me/subhajit_feedback",
                    emoji_id="5258134813302332906",
                ),
                premium_button(
                    "DOWNLOAD APK",
                    url="https://t.me/+hasTLSVjzaZjZGVl",
                    emoji_id="6028115612163641653",
                ),
            ],
        ]
    )


def get_back_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                premium_button(
                    "BACK",
                    callback_data="/backkkk",
                    style="danger",
                    emoji_id="6039539366177541657",
                )
            ]
        ]
    )


def get_shop_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                premium_button(
                    "DRIP CLIENT NON-ROOT",
                    callback_data="/SHOP_P1",
                    emoji_id="6323104647636589287",
                )
            ],
            [
                premium_button(
                    "PROXY SERVER [DR-CL]",
                    callback_data="/SHOP_P2",
                    emoji_id="6212942266957310140",
                )
            ],
            [
                premium_button(
                    "PRIME HOOK",
                    callback_data="/SHOP_P4",
                    emoji_id="6210705396449944693",
                )
            ],
            [
                premium_button(
                    "BACK",
                    callback_data="/backkkk",
                    style="danger",
                    emoji_id="6039539366177541657",
                )
            ],
        ]
    )


def get_support_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                premium_button(
                    "WHATSAPP",
                    url="https://wa.me/917908696630",
                    emoji_id="6109296665926047025",
                )
            ],
            [
                premium_button(
                    "BACK",
                    callback_data="/backkkk",
                    style="danger",
                    emoji_id="6039539366177541657",
                )
            ],
        ]
    )


def get_amount_text(amount):
    display_amount = amount or "0"
    return (
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        f"Amount: ₹{display_amount}\n\n"
        "Use the keypad below to enter amount."
    )


def get_amount_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("1", callback_data="/num1"),
                InlineKeyboardButton("2", callback_data="/num2"),
                InlineKeyboardButton("3", callback_data="/num3"),
            ],
            [
                InlineKeyboardButton("4", callback_data="/num4"),
                InlineKeyboardButton("5", callback_data="/num5"),
                InlineKeyboardButton("6", callback_data="/num6"),
            ],
            [
                InlineKeyboardButton("7", callback_data="/num7"),
                InlineKeyboardButton("8", callback_data="/num8"),
                InlineKeyboardButton("9", callback_data="/num9"),
            ],
            [
                premium_button("❌ CLEAR", callback_data="/clearamt", style="danger"),
                InlineKeyboardButton("0", callback_data="/num0"),
                premium_button("✅ CONFIRM", callback_data="/done"),
            ],
            [
                premium_button(
                    "BACK",
                    callback_data="/backkkk",
                    style="danger",
                    emoji_id="6039539366177541657",
                )
            ],
        ]
    )


def get_payment_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                premium_button(
                    "VERIFY PAYMENT",
                    callback_data="/verify_addpay",
                    emoji_id="6278302366303260172",
                )
            ],
            [
                premium_button(
                    "CANCEL",
                    callback_data="/cancel",
                    style="danger",
                    emoji_id="6278116707751956084",
                )
            ],
        ]
    )


def fetch_json(url):
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def build_url(base_url, params):
    return f"{base_url}?{urlencode(params)}"


async def edit_query_message(query, *, text, reply_markup, parse_mode=ParseMode.HTML):
    try:
        await query.edit_message_text(
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            raise e


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    if user.id not in user_data:
        user_data[user.id] = {"joined_date": update.message.date}

    balance = balances.get(user.id, 0)

    await context.bot.send_message(
        chat_id=chat_id,
        text=get_home_text(balance),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=get_home_keyboard(),
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

    await edit_query_message(query, text=text, reply_markup=get_shop_keyboard())


async def back_to_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    balance = balances.get(user.id, 0)

    await edit_query_message(
        query,
        text=get_home_text(balance),
        reply_markup=get_home_keyboard(),
    )


async def product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    products = {
        "/SHOP_P1": ("DRIP CLIENT NON-ROOT", "6323104647636589287"),
        "/SHOP_P2": ("PROXY SERVER [DR-CL]", "6212942266957310140"),
        "/SHOP_P4": ("PRIME HOOK", "6210705396449944693"),
    }

    product_name, product_emoji_id = products.get(
        query.data,
        ("Unknown Product", "6179339404906079822"),
    )

    text = f"""
━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id="{product_emoji_id}">📦</tg-emoji> <b>{product_name}</b>
━━━━━━━━━━━━━━━━━━━━

<b>Product Selected:</b>

<tg-emoji emoji-id="6179339404906079822">📦</tg-emoji> Product: <b>{product_name}</b>

Please continue with payment or contact support.
"""

    keyboard = InlineKeyboardMarkup(
        [
            [
                premium_button(
                    "BACK",
                    callback_data="/shopnawkk",
                    style="danger",
                    emoji_id="6039539366177541657",
                )
            ]
        ]
    )

    await edit_query_message(query, text=text, reply_markup=keyboard)


async def my_key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    orders = user_orders.get(user.id, [])

    if not orders:
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<tg-emoji emoji-id='6008118472066732010'>📦</tg-emoji> <b>MY ORDERS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "You haven't placed any orders yet.\n"
            "Tap <tg-emoji emoji-id='6093562529978522804'>🛒</tg-emoji> Shop Now to get started!"
        )
    else:
        latest_10 = orders[-10:][::-1]
        safe_list = [str(item) for item in latest_10 if item]
        text = "\n\n".join(safe_list) if safe_list else "No valid entries found."

    await edit_query_message(query, text=text, reply_markup=get_back_keyboard())


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

    await edit_query_message(query, text=text, reply_markup=get_back_keyboard())


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

    await edit_query_message(query, text=text, reply_markup=get_back_keyboard())


async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = """
━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id='5891120964468480450'>💬</tg-emoji> <b>Support — Seller</b> <tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji>
━━━━━━━━━━━━━━━━━━━━

Need help? We're here for you! <tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji>

📩 <b>Telegram:</b> <tg-emoji emoji-id='5776182936638329359'>⭐</tg-emoji>

<a href="https://t.me/UR_SUBHAJIT0">𝐒υвʜᴀᎫιт</a> <tg-emoji emoji-id='6118314396440596568'>⭐</tg-emoji>

<tg-emoji emoji-id='5891120964468480450'>💡</tg-emoji> <i>Include your User ID (from Profile)
when contacting for faster help.</i>
"""

    await edit_query_message(query, text=text, reply_markup=get_support_keyboard())


async def add_fund_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_data.setdefault(query.from_user.id, {})["pay_amount"] = ""

    await edit_query_message(
        query,
        text=get_amount_text(""),
        reply_markup=get_amount_keyboard(),
    )


async def amount_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    digit = query.data.replace("/num", "", 1)
    user_store = user_data.setdefault(query.from_user.id, {})
    current_amount = user_store.get("pay_amount", "")

    if len(current_amount) >= 7:
        return

    if current_amount == "" and digit == "0":
        new_amount = ""
    else:
        new_amount = current_amount + digit

    user_store["pay_amount"] = new_amount

    await edit_query_message(
        query,
        text=get_amount_text(new_amount),
        reply_markup=get_amount_keyboard(),
    )


async def clear_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_data.setdefault(query.from_user.id, {})["pay_amount"] = ""

    await edit_query_message(
        query,
        text=get_amount_text(""),
        reply_markup=get_amount_keyboard(),
    )


async def confirm_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_store = user_data.setdefault(query.from_user.id, {})
    amount = user_store.get("pay_amount", "")

    if not amount or int(amount) <= 0:
        text = (
            "<blockquote>"
            "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
            "</blockquote>\n\n"
            "Please enter an amount greater than ₹0."
        )
        await edit_query_message(query, text=text, reply_markup=get_amount_keyboard())
        return

    user_store["last_deposit_amount"] = amount

    url = build_url(
        "https://fampay.anujbots.xyz/qr.php",
        {"upi": UPI_ID, "amount": amount},
    )

    try:
        data = fetch_json(url)
    except Exception:
        await edit_query_message(
            query,
            text="❌ API ERROR",
            reply_markup=get_back_keyboard(),
            parse_mode=None,
        )
        return

    if data.get("status") != "success":
        await edit_query_message(
            query,
            text="❌ QR GENERATION FAILED",
            reply_markup=get_back_keyboard(),
            parse_mode=None,
        )
        return

    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    user_store["addpay_order_id"] = order_id

    await edit_query_message(
        query,
        text=(
            "<blockquote>"
            "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> PAYMENT QR GENERATED"
            "</blockquote>\n\n"
            "QR image sent below. Scan it and complete payment.\n\n"
            f"Amount: ₹{amount}"
        ),
        reply_markup=get_payment_keyboard(),
    )

    await context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=qr_url,
        caption=(
            "<blockquote>"
            "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> PAYMENT QR GENERATED"
            "</blockquote>\n"
            "Scan the QR and complete payment.\n\n"
            f"Amount: ₹{amount}"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=get_payment_keyboard(),
    )


async def verify_addpay_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_store = user_data.setdefault(query.from_user.id, {})
    order_id = user_store.get("addpay_order_id")

    if not order_id:
        await edit_query_message(
            query,
            text="❌ No active payment found.",
            reply_markup=get_back_keyboard(),
            parse_mode=None,
        )
        return

    if not FAMPAY_API_KEY or FAMPAY_API_KEY == "YAHAN_APNI_FAMPAY_API_KEY":
        await edit_query_message(
            query,
            text="❌ Payment verify API key missing.",
            reply_markup=get_back_keyboard(),
            parse_mode=None,
        )
        return

    url = build_url(
        "https://fampay.anujbots.xyz/verify.php",
        {"order_id": order_id, "api_key": FAMPAY_API_KEY},
    )

    try:
        data = fetch_json(url)
    except Exception:
        await edit_query_message(
            query,
            text="❌ API ERROR",
            reply_markup=get_payment_keyboard(),
            parse_mode=None,
        )
        return

    if data.get("status") == "success":
        amount = float(data["data"]["amount"])

        balances[query.from_user.id] = balances.get(query.from_user.id, 0) + amount

        user_store["addpay_order_id"] = ""
        user_store["pay_amount"] = ""
        user_store["last_deposit_amount"] = ""

        await edit_query_message(
            query,
            text=f"✅ Payment Success\n\n💰 Added ₹{amount}",
            reply_markup=get_back_keyboard(),
            parse_mode=None,
        )
    else:
        await edit_query_message(
            query,
            text="❌ Payment Not Received",
            reply_markup=get_payment_keyboard(),
            parse_mode=None,
        )


async def cancel_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_store = user_data.setdefault(query.from_user.id, {})
    user_store["addpay_order_id"] = ""
    user_store["pay_amount"] = ""
    user_store["last_deposit_amount"] = ""

    await edit_query_message(
        query,
        text="❌ Payment cancelled.",
        reply_markup=get_back_keyboard(),
        parse_mode=None,
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
    app.add_handler(CallbackQueryHandler(amount_number_handler, pattern="^/num[0-9]$"))
    app.add_handler(CallbackQueryHandler(clear_amount_handler, pattern="^/clearamt$"))
    app.add_handler(CallbackQueryHandler(confirm_amount_handler, pattern="^/done$"))

    app.add_handler(CallbackQueryHandler(verify_addpay_handler, pattern="^/verify_addpay$"))
    app.add_handler(CallbackQueryHandler(cancel_payment_handler, pattern="^/cancel$"))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
