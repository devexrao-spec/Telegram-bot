import os
import json
from urllib.parse import urlencode
from urllib.request import urlopen

from pymongo import MongoClient

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# ================= DATABASE =================

MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise RuntimeError("MONGO_URL missing")

client = MongoClient(MONGO_URL)

db = client["hack_store"]

users = db["users"]


# ================= CONFIG =================

UPI_ID = os.getenv("UPI_ID", "bablu.xyztb@fam")
FAMPAY_API_KEY = os.getenv("FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8")


# ================= USER DATABASE =================

def create_user(user):

    users.update_one(
        {"user_id": user.id},
        {
            "$setOnInsert": {
                "user_id": user.id,
                "name": user.first_name or "User",
                "username": user.username,
                "balance": 0,
                "orders": [],
                "pay_amount": "",
                "order_id": ""
            }
        },
        upsert=True
    )


def get_user(user_id):

    data = users.find_one(
        {"user_id": user_id}
    )

    if not data:
        users.insert_one(
            {
                "user_id": user_id,
                "balance": 0,
                "orders": []
            }
        )

        data = users.find_one(
            {"user_id": user_id}
        )

    return data


def update_user(user_id, data):

    users.update_one(
        {"user_id": user_id},
        {
            "$set": data
        },
        upsert=True
    )


def get_balance(user_id):

    user = get_user(user_id)

    return user.get("balance", 0)


def add_balance(user_id, amount):

    users.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "balance": amount
            }
        }
    )


def add_order(user_id, order):

    users.update_one(
        {"user_id": user_id},
        {
            "$push": {
                "orders": order
            }
        }
    )


# ================= API =================

def fetch_json(url):

    with urlopen(url, timeout=20) as r:
        return json.loads(
            r.read().decode()
        )


def build_url(url, params):

    return f"{url}?{urlencode(params)}"

def premium_button(
    text,
    *,
    callback_data=None,
    url=None,
    style="success",
    emoji_id=None
):
    api_kwargs = {
        "style": style
    }

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
        "<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> "
        "PREMIUM FEATURES\n\n"

        "<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> "
        "Instant Key Delivery\n"

        "<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> "
        "Secure Auto-Payment System\n"

        "<tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji> "
        "100% Anti-Ban Support"
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
                    callback_data="shop",
                    emoji_id="6093739864883207194",
                )
            ],

            [
                premium_button(
                    "MY KEY",
                    callback_data="mykey",
                    emoji_id="5967456680940671207",
                ),

                premium_button(
                    "PROFILE",
                    callback_data="profile",
                    emoji_id="5346136537123801643",
                )
            ],

            [
                premium_button(
                    "HOW TO USE",
                    callback_data="how",
                    emoji_id="5345783284653636765",
                ),

                premium_button(
                    "SUPPORT",
                    callback_data="support",
                    emoji_id="5897567714674741148",
                )
            ],

            [
                premium_button(
                    "ADD FUND",
                    callback_data="addfund",
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
                )
            ]
        ]
    )


def get_back_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                premium_button(
                    "BACK",
                    callback_data="back",
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
                    callback_data="product1",
                    emoji_id="6323104647636589287",
                )
            ],

            [
                premium_button(
                    "PROXY SERVER [DR-CL]",
                    callback_data="product2",
                    emoji_id="6212942266957310140",
                )
            ],

            [
                premium_button(
                    "PRIME HOOK",
                    callback_data="product3",
                    emoji_id="6210705396449944693",
                )
            ],

            [
                premium_button(
                    "BACK",
                    callback_data="back",
                    style="danger",
                    emoji_id="6039539366177541657",
                )
            ]
        ]
    )

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user

    create_user(user)

    data = get_user(user.id)

    balance = data.get("balance", 0)

    text = f"""
<blockquote>
<tg-emoji emoji-id="5346136537123801643">👤</tg-emoji>
<b>PROFILE</b>
</blockquote>

<b>Name:</b> {user.first_name or "User"}

<b>User ID:</b>
<code>{user.id}</code>

<b>Username:</b> @{user.username or "None"}

<b>Balance:</b> ₹{balance}
"""

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_keyboard()
    )



async def shop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    text = """
<blockquote>
<tg-emoji emoji-id="6093562529978522804">🛒</tg-emoji>
<b>PANNEL STORE — SHOP</b>
</blockquote>

<tg-emoji emoji-id="6179339404906079822">📦</tg-emoji>
Choose your product:
"""

    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_shop_keyboard()
    )



async def product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()


    products = {

        "product1":
        "DRIP CLIENT NON-ROOT",

        "product2":
        "PROXY SERVER [DR-CL]",

        "product3":
        "PRIME HOOK"
    }


    name = products.get(
        query.data,
        "Unknown Product"
    )


    text = f"""
<blockquote>
📦 <b>{name}</b>
</blockquote>


Product Selected:

📦 Product:
<b>{name}</b>


Please continue payment or contact support.
"""


    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_keyboard()
    )



async def my_key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()


    user = get_user(
        query.from_user.id
    )


    orders = user.get(
        "orders",
        []
    )


    if not orders:

        text = (
            "<blockquote>"
            "📦 <b>MY ORDERS</b>"
            "</blockquote>\n\n"
            "You haven't placed any orders yet."
        )

    else:

        text = "\n\n".join(
            str(x) for x in orders
        )


    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_keyboard()
    )



async def add_fund_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    update_user(
        query.from_user.id,
        {
            "pay_amount": ""
        }
    )

    await query.edit_message_text(
        text=(
            "<blockquote>"
            "💰 <b>ENTER CUSTOM AMOUNT</b>"
            "</blockquote>\n\n"
            "Use keypad to enter amount."
        ),
        parse_mode=ParseMode.HTML
    )


async def verify_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = get_user(query.from_user.id)

    order_id = user.get("order_id")

    if not order_id:
        return
        await query.edit_message_text(
            "❌ No active payment found.",
            reply_markup=get_back_keyboard()
        )
        return


    url = build_url(
        "https://fampay.anujbots.xyz/verify.php",
        {
            "order_id": order_id,
            "api_key": FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8
        }
    )


    try:
        data = fetch_json(url)

    except Exception:

        await query.edit_message_text(
            "❌ API ERROR",
            reply_markup=get_back_keyboard()
        )
        return


    if data.get("status") == "success":

        amount = float(
            data["data"]["amount"]
        )

        add_balance(
            query.from_user.id,
            amount
        )


        update_user(
            query.from_user.id,
            {
                "order_id":"",
                "pay_amount":""
            }
        )


        add_order(
            query.from_user.id,
            {
                "Deposit": amount
            }
        )


        await query.edit_message_text(
            f"✅ Payment Success\n\n💰 Added ₹{amount}",
            reply_markup=get_back_keyboard()
        )


    else:

        await query.edit_message_text(
            "❌ Payment Not Received",
            reply_markup=get_back_keyboard()
        )



async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    balance = get_balance(
        query.from_user.id
    )

    await query.edit_message_text(
        get_home_text(balance),
        parse_mode=ParseMode.HTML,
        reply_markup=get_home_keyboard()
    )



def main():

    token = os.getenv("8828131983:AAG66fQnd9Be1WiGRWKT0sqFYEZM510yWx4")

    if not token:
        raise RuntimeError(
            "BOT_TOKEN missing"
        )


    app = Application.builder().token(token).build()


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            shop_handler,
            pattern="^shop$"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            back_handler,
            pattern="^back$"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            profile_handler,
            pattern="^profile$"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            my_key_handler,
            pattern="^mykey$"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            add_fund_handler,
            pattern="^addfund$"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            product_handler,
            pattern="^product"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            verify_payment_handler,
            pattern="^verify$"
        )
    )


    print("Bot Running...")


    app.run_polling()



if __name__ == "__main__":
    main()
