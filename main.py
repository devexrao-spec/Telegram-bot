import asyncio
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = "8828131983:AAG66fQnd9Be1WiGRWKT0sqFYEZM510yWx4"
API_URL = "https://fampay.anujbots.xyz"
DATA_FILE = "bot_data.json"

# ============================================================
# PERSISTENT STORAGE
# ============================================================

def load_all_data():
    """Load all data from file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"users": {}}
    return {"users": {}}

def save_all_data(data):
    """Save all data to file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ============================================================
# DATA STORAGE CLASSES
# ============================================================

class BotData:
    _data = load_all_data()
    
    @classmethod
    def get(cls, key: str, default=None):
        return cls._data.get(key, default)
    
    @classmethod
    def set(cls, key: str, value: Any):
        cls._data[key] = value
        save_all_data(cls._data)
    
    @classmethod
    def delete(cls, key: str):
        if key in cls._data:
            del cls._data[key]
            save_all_data(cls._data)
    
    @classmethod
    def reload(cls):
        cls._data = load_all_data()

class UserData:
    _data = load_all_data()
    
    @classmethod
    def get(cls, key: str, user_id: str = None, default=None):
        if user_id:
            return cls._data.get("users", {}).get(str(user_id), {}).get(key, default)
        return cls._data.get(key, default)
    
    @classmethod
    def set(cls, key: str, value: Any, user_id: str = None):
        if user_id:
            user_id = str(user_id)
            if "users" not in cls._data:
                cls._data["users"] = {}
            if user_id not in cls._data["users"]:
                cls._data["users"][user_id] = {}
            cls._data["users"][user_id][key] = value
        else:
            cls._data[key] = value
        save_all_data(cls._data)
    
    @classmethod
    def get_user_data(cls, user_id: str) -> Dict:
        return cls._data.get("users", {}).get(str(user_id), {})

class UserResources:
    @staticmethod
    def get_balance(user_id: str) -> float:
        return UserData.get("balance", user_id, 0.0)
    
    @staticmethod
    def set_balance(user_id: str, amount: float):
        UserData.set("balance", amount, user_id)
    
    @staticmethod
    def add_balance(user_id: str, amount: float):
        current = UserData.get("balance", user_id, 0.0)
        UserData.set("balance", current + amount, user_id)
    
    @staticmethod
    def cut_balance(user_id: str, amount: float):
        current = UserData.get("balance", user_id, 0.0)
        if current >= amount:
            UserData.set("balance", current - amount, user_id)
            return True
        return False
    
    @staticmethod
    def get_orders(user_id: str) -> int:
        return UserData.get("orders", user_id, 0)
    
    @staticmethod
    def add_order(user_id: str):
        current = UserData.get("orders", user_id, 0)
        UserData.set("orders", current + 1, user_id)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_indian_time() -> Dict:
    now = datetime.now()
    hour = now.hour
    ampm = "am"
    if hour >= 12:
        ampm = "pm"
    if hour > 12:
        hour -= 12
    if hour == 0:
        hour = 12
    
    months = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
    }
    
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "easy_time": f"{now.day} {months[now.strftime('%m')]}, {hour:02d}:{now.strftime('%M')} {ampm}"
    }

def is_admin(user_id: str) -> bool:
    admins = BotData.get("AllBotAdminss", [])
    if not admins:
        BotData.set("AllBotAdminss", [str(user_id)])
        BotData.set("Owner", str(user_id))
        return True
    return str(user_id) in [str(a) for a in admins]

def get_reseller_prices(product: str, user_id: str) -> tuple:
    resellers = BotData.get("resellers_list", [])
    is_reseller = str(user_id) in [str(r) for r in resellers]
    
    if product == "drip":
        normal = {
            "1d": BotData.get("drip_1d_price", 108),
            "3d": BotData.get("drip_3d_price", 260),
            "7d": BotData.get("drip_7d_price", 360),
            "15d": BotData.get("drip_15d_price", 560),
            "30d": BotData.get("drip_30d_price", 810)
        }
        reseller = {
            "1d": BotData.get("drip_1d_reseller_price", 95),
            "3d": BotData.get("drip_3d_reseller_price", 220),
            "7d": BotData.get("drip_7d_reseller_price", 320),
            "15d": BotData.get("drip_15d_reseller_price", 480),
            "30d": BotData.get("drip_30d_reseller_price", 750)
        }
        return (reseller if is_reseller else normal), is_reseller
    
    elif product == "proxy":
        normal = {
            "1d": BotData.get("PATO_1d_price", 108),
            "3d": BotData.get("PATO_3d_price", 260),
            "7d": BotData.get("PATO_7d_price", 360),
            "15d": BotData.get("PATO_15d_price", 560)
        }
        reseller = {
            "1d": BotData.get("PATO_1d_reseller_price", 95),
            "3d": BotData.get("PATO_3d_reseller_price", 220),
            "7d": BotData.get("PATO_7d_reseller_price", 320),
            "15d": BotData.get("PATO_15d_reseller_price", 480)
        }
        return (reseller if is_reseller else normal), is_reseller
    
    elif product == "prime":
        normal = {
            "1d": BotData.get("HG_1d_price", 108),
            "3d": BotData.get("HG_3d_price", 200),
            "7d": BotData.get("HG_7d_price", 360),
            "14d": BotData.get("HG_14d_price", 600),
            "21d": BotData.get("HG_21d_price", 700)
        }
        reseller = {
            "1d": BotData.get("HG_1d_reseller_price", 95),
            "3d": BotData.get("HG_3d_reseller_price", 180),
            "7d": BotData.get("HG_7d_reseller_price", 320),
            "14d": BotData.get("HG_14d_reseller_price", 550),
            "21d": BotData.get("HG_21d_reseller_price", 650)
        }
        return (reseller if is_reseller else normal), is_reseller
    
    return {}, is_reseller

def get_stock(key_name: str) -> List:
    stock = BotData.get(key_name, [])
    if isinstance(stock, str):
        return [stock] if stock else []
    return stock if stock else []

# ============================================================
# COMMAND HANDLERS
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not UserData.get("joined_date", user_id):
        UserData.set("joined_date", int(update.message.date.timestamp()), user_id)
    
    first_name = update.effective_user.first_name or "User"
    balance = UserResources.get_balance(user_id)
    
    text = (
        "<blockquote>"
        "🌟 WELCOME TO HACK STORE 🌙"
        "</blockquote>\n\n"
        "✨ Your ultimate destination for premium mods, cheats & clients!\n\n"
        "<blockquote>"
        "🚀 PREMIUM FEATURES\n\n"
        "⚡ Instant Key Delivery\n"
        "💳 Secure Auto-Payment System\n"
        "🛡 100% Anti-Ban Support"
        "</blockquote>\n\n"
        f"<blockquote>💰 Your Balance: ₹{balance}</blockquote>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 BUY HACK", callback_data="shopnawkk")],
        [InlineKeyboardButton("📦 MY KEY", callback_data="orderksk"), InlineKeyboardButton("👤 PROFILE", callback_data="profilemmm")],
        [InlineKeyboardButton("📖 HOW TO USE", callback_data="spinj"), InlineKeyboardButton("💬 SUPPORT", callback_data="supportj")],
        [InlineKeyboardButton("💰 ADD FUND", callback_data="addpayment")],
        [InlineKeyboardButton("📩 PAY PROOF", url="https://t.me/subhajit_feedback"), InlineKeyboardButton("📥 DOWNLOAD APK", url="https://t.me/+hasTLSVjzaZjZGVl")]
    ]
    
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not BotData.get("AllBotAdminss"):
        BotData.set("AllBotAdminss", [user_id])
        BotData.set("Owner", user_id)
    
    if not is_admin(user_id):
        await update.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    bot_mode = BotData.get("BotMode", "ON")
    bot_status = "🟢 On"
    toggle_text = "OFF"
    
    if bot_mode == "OFF":
        bot_status = "🔴 Off"
        toggle_text = "ON"
    
    keyboard = [
        [InlineKeyboardButton("👑 Admins", callback_data="TUSHAR_Admins")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton(f"🤖 Bot: {bot_status}", callback_data=f"admin BotMode {toggle_text}")],
        [InlineKeyboardButton("💰 Add Balance", callback_data="ChangeAnyUserBal"), InlineKeyboardButton("📝 Recent Actions", callback_data="TUSHAR_AdminAction")],
        [InlineKeyboardButton("📊 Shop Setup", callback_data="setshop_psue")],
        [InlineKeyboardButton("💰 Add Reseller", callback_data="addreseller"), InlineKeyboardButton("⛔ Remove Reseller", callback_data="removereseller")],
        [InlineKeyboardButton("📝 Reseller List", callback_data="resellerlist")]
    ]
    
    text = f"""<b>
👋 Welcome {update.effective_user.first_name} 🎉

━━━━━━━━━━━━━━━
🤖 Bot Status : {bot_status}
━━━━━━━━━━━━━━━
</b>"""
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

# ============================================================
# SHOP COMMANDS (Keep all existing shop functions)
# ============================================================

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
━━━━━━━━━━━━━━━━━━━━
🛒 <b>PANNEL STORE — SHOP</b>
━━━━━━━━━━━━━━━━━━━━

📦 Choose a product:
"""
    
    keyboard = [
        [InlineKeyboardButton("📦 DRIP CLIENT NON-ROOT", callback_data="SHOP_P1")],
        [InlineKeyboardButton("📦 PROXY SERVER [DR-CL]", callback_data="SHOP_P2")],
        [InlineKeyboardButton("🔥 PRIME HOOK", callback_data="SHOP_P4")],
        [InlineKeyboardButton("🔙 BACK", callback_data="backkkk")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

async def shop_p1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    prices, is_reseller = get_reseller_prices("drip", user_id)
    buy_cmd = "buyjai_reseller" if is_reseller else "buyjai"
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📦 𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗✅ ( 𝘉𝘌𝘚𝘛 𝘚𝘌𝘓𝘓𝘌𝘙 💫 )\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<i>📦 Extra 2% discount applied</i>\n"
        "Choose a plan 👇"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"1 DAY - ₹{prices['1d']}", callback_data=f"{buy_cmd} 1")],
        [InlineKeyboardButton(f"3 DAYS - ₹{prices['3d']}", callback_data=f"{buy_cmd} 2")],
        [InlineKeyboardButton(f"7 DAYS - ₹{prices['7d']}", callback_data=f"{buy_cmd} 3")],
        [InlineKeyboardButton(f"15 DAYS - ₹{prices['15d']}", callback_data=f"{buy_cmd} 4")],
        [InlineKeyboardButton(f"30 DAYS - ₹{prices['30d']}", callback_data=f"{buy_cmd} 5")],
        [InlineKeyboardButton("🔙 BACK", callback_data="shopnawkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shop_p2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    prices, is_reseller = get_reseller_prices("proxy", user_id)
    buy_cmd = "buyjai_reseller" if is_reseller else "buyjai"
    
    text = """
━━━━━━━━━━━━━━━━━━━━
📦 PROXY SERVER [DR-CL]
━━━━━━━━━━━━━━━━━━━━

Choose a plan 👇
"""
    
    keyboard = [
        [InlineKeyboardButton(f"1 Day - ₹{prices['1d']}", callback_data=f"{buy_cmd} 6")],
        [InlineKeyboardButton(f"3 Days - ₹{prices['3d']}", callback_data=f"{buy_cmd} 7")],
        [InlineKeyboardButton(f"7 Days - ₹{prices['7d']}", callback_data=f"{buy_cmd} 8")],
        [InlineKeyboardButton(f"15 Days - ₹{prices['15d']}", callback_data=f"{buy_cmd} 9")],
        [InlineKeyboardButton("🔙 BACK", callback_data="shopnawkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shop_p4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    prices, is_reseller = get_reseller_prices("prime", user_id)
    buy_cmd = "buyjai_reseller" if is_reseller else "buyjai"
    
    text = """
━━━━━━━━━━━━━━━━━━━━
🔥 PRIME HOOK
━━━━━━━━━━━━━━━━━━━━

Choose a plan 👇
"""
    
    keyboard = [
        [InlineKeyboardButton(f"1 Day - ₹{prices['1d']}", callback_data=f"{buy_cmd} 10")],
        [InlineKeyboardButton(f"3 Days - ₹{prices['3d']}", callback_data=f"{buy_cmd} 11")],
        [InlineKeyboardButton(f"7 Days - ₹{prices['7d']}", callback_data=f"{buy_cmd} 12")],
        [InlineKeyboardButton(f"14 Days - ₹{prices['14d']}", callback_data=f"{buy_cmd} 13")],
        [InlineKeyboardButton(f"21 Days - ₹{prices['21d']}", callback_data=f"{buy_cmd} 14")],
        [InlineKeyboardButton("🔙 BACK", callback_data="shopnawkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ============================================================
# BUY COMMANDS
# ============================================================

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split()
    if len(data) < 2:
        await query.message.reply_text("❌ Invalid Product")
        return
    
    params = data[1]
    user_id = str(query.from_user.id)
    
    products = {
        "1": {"price": "drip_1d_price", "key": "drip_1d_keys", "title": "DRIP CLIENT APK MOD\n1 Day", "product": "DRIP CLIENT APK MOD", "plan": "1 Day"},
        "2": {"price": "drip_3d_price", "key": "drip_3d_keys", "title": "DRIP CLIENT APK MOD\n3 Days", "product": "DRIP CLIENT APK MOD", "plan": "3 Days"},
        "3": {"price": "drip_7d_price", "key": "drip_7d_keys", "title": "DRIP CLIENT APK MOD\n7 Days", "product": "DRIP CLIENT APK MOD", "plan": "7 Days"},
        "4": {"price": "drip_15d_price", "key": "drip_15d_keys", "title": "DRIP CLIENT APK MOD\n15 Days", "product": "DRIP CLIENT APK MOD", "plan": "15 Days"},
        "5": {"price": "drip_30d_price", "key": "drip_30d_keys", "title": "DRIP CLIENT APK MOD\n30 Days", "product": "DRIP CLIENT APK MOD", "plan": "30 Days"},
        "6": {"price": "PATO_1d_price", "key": "PATO_1d_keys", "title": "PROXY SERVER [DR-CL]\n1 Day", "product": "PROXY SERVER [DR-CL]", "plan": "1 Day"},
        "7": {"price": "PATO_3d_price", "key": "PATO_3d_keys", "title": "PROXY SERVER [DR-CL]\n3 Days", "product": "PROXY SERVER [DR-CL]", "plan": "3 Days"},
        "8": {"price": "PATO_7d_price", "key": "PATO_7d_keys", "title": "PROXY SERVER [DR-CL]\n7 Days", "product": "PROXY SERVER [DR-CL]", "plan": "7 Days"},
        "9": {"price": "PATO_15d_price", "key": "PATO_15d_keys", "title": "PROXY SERVER [DR-CL]\n10 Days", "product": "PROXY SERVER [DR-CL]", "plan": "10 Days"},
        "10": {"price": "HG_1d_price", "key": "HG_1d_keys", "title": "PRIME-HOOK\n1 Day", "product": "PRIME-HOOK", "plan": "1 Day"},
        "11": {"price": "HG_3d_price", "key": "HG_3d_keys", "title": "PRIME-HOOK\n3 Days", "product": "PRIME-HOOK", "plan": "3 Days"},
        "12": {"price": "HG_7d_price", "key": "HG_7d_keys", "title": "PRIME-HOOK\n7 Days", "product": "PRIME-HOOK", "plan": "7 Days"},
        "13": {"price": "HG_14d_price", "key": "HG_14d_keys", "title": "PRIME-HOOK\n14 Days", "product": "PRIME-HOOK", "plan": "14 Days"},
        "14": {"price": "HG_21d_price", "key": "HG_21d_keys", "title": "PRIME-HOOK\n21 Days", "product": "PRIME-HOOK", "plan": "21 Days"},
    }
    
    if params not in products:
        await query.message.reply_text("❌ Invalid Product ID")
        return
    
    product = products[params]
    is_reseller_cmd = "reseller" in data[0]
    if is_reseller_cmd:
        price_key = product["price"].replace("price", "reseller_price")
        if BotData.get(price_key):
            product["price"] = price_key
    
    await process_purchase(update, context, query.message, user_id, product)

async def process_purchase(update, context, message, user_id: str, product: Dict):
    price = BotData.get(product["price"], 0)
    keys = get_stock(product["key"])
    
    if price <= 0:
        await message.reply_text("❌ Price not set. Contact Admin.")
        return
    
    if len(keys) == 0:
        await message.reply_text("❌ Out of Stock.")
        return
    
    balance = UserResources.get_balance(user_id)
    time_info = get_indian_time()
    
    if balance < price:
        UserData.set("last_deposit_amount", price, user_id)
        UserData.set("last_product", product["product"], user_id)
        UserData.set("last_plan", product["plan"], user_id)
        await auto_buy(update, context, message, user_id, price, product)
        return
    
    if not UserResources.cut_balance(user_id, price):
        await message.reply_text("❌ Insufficient balance.")
        return
    
    UserResources.add_order(user_id)
    key = str(keys[0])
    keys.pop(0)
    BotData.set(product["key"], keys)
    
    success_text = (
        f"🛒 {product['title']}\n\n"
        f"🔑 <b>Your Key:</b>\n<code>{key}</code>\n\n"
        f"💰 Deducted: ₹{price}\n"
        f"📦 Remaining Stock: {len(keys)}\n"
        f"📦 Time: {time_info['easy_time']}\n\n"
        f"📢 <b>ALL FILES UPDATE</b>\n@SUBHAJIT_UPDATES"
    )
    
    await message.reply_text(success_text, parse_mode="HTML")
    
    user_actions = UserData.get("userhAC", user_id, [])
    user_actions.append(
        f"📆 {time_info['easy_time']}\n"
        f"👤 {message.from_user.first_name} [{user_id}]\n"
        f"💰 ₹{price}\n"
        f"🔑 {key}\n"
    )
    UserData.set("userhAC", user_actions, user_id)

async def auto_buy(update, context, message, user_id: str, price: float, product: Dict):
    upi = "bablu.xyztb@fam"
    balance = UserResources.get_balance(user_id)
    need = max(0, price - balance)
    
    url = f"{API_URL}/qr.php?upi={upi}&amount={price}"
    
    try:
        resp = requests.get(url)
        data = resp.json()
    except:
        await message.reply_text("❌ API ERROR")
        return
    
    if data.get("status") != "success":
        await message.reply_text("❌ QR GENERATION FAILED")
        return
    
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    UserData.set("last_order_id", order_id, user_id)
    
    caption = (
        f"<blockquote>💰 INSUFFICIENT BALANCE</blockquote>\n\n"
        f"┣ Product: {product['product']}\n"
        f"┣ Plan: {product['plan']}\n"
        f"┣ Price: ₹{price}\n"
        f"┣ Your Balance: ₹{balance}\n"
        f"┗ Need: ₹{need}"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ VERIFY PAYMENT", callback_data="autobuyi")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="cancel")]
    ]
    
    await message.reply_photo(
        photo=qr_url,
        caption=caption,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    order_id = UserData.get("last_order_id", user_id)
    
    if not order_id:
        await query.message.reply_text("❌ No active payment found.")
        return
    
    url = f"{API_URL}/verify.php?order_id={order_id}&api_key=FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8"
    
    try:
        resp = requests.get(url)
        data = resp.json()
    except:
        await query.message.reply_text("❌ API ERROR")
        return
    
    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        UserResources.add_balance(user_id, amount)
        UserData.set("last_order_id", "", user_id)
        
        await query.message.reply_text(
            f"✅ Payment Success!\n\n"
            f"💰 Added ₹{amount}\n"
            f"💳 New Balance: ₹{UserResources.get_balance(user_id)}",
            parse_mode="HTML"
        )
        
        admins = BotData.get("AllBotAdminss", [])
        for admin in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin,
                    text=(
                        f"✅ New Payment Received!\n\n"
                        f"👤 User ID: <code>{user_id}</code>\n"
                        f"💰 Amount: ₹{amount}\n"
                        f"🧾 Order ID: <code>{order_id}</code>\n"
                        f"💳 User Balance: ₹{UserResources.get_balance(user_id)}"
                    ),
                    parse_mode="HTML"
                )
            except:
                pass
    else:
        await query.message.reply_text(
            "❌ Payment Not Received\n\nPlease complete the payment and try again.",
            parse_mode="HTML"
        )

# ============================================================
# ADD PAYMENT COMMANDS
# ============================================================

async def add_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    UserData.set("pay_amount", "", query.from_user.id)
    
    text = (
        "<blockquote>💰 ENTER CUSTOM AMOUNT</blockquote>\n\n"
        "Amount: ₹0\n\n"
        "Use the keypad below to enter amount."
    )
    
    keyboard = [
        [InlineKeyboardButton("1", callback_data="num1"), InlineKeyboardButton("2", callback_data="num2"), InlineKeyboardButton("3", callback_data="num3")],
        [InlineKeyboardButton("4", callback_data="num4"), InlineKeyboardButton("5", callback_data="num5"), InlineKeyboardButton("6", callback_data="num6")],
        [InlineKeyboardButton("7", callback_data="num7"), InlineKeyboardButton("8", callback_data="num8"), InlineKeyboardButton("9", callback_data="num9")],
        [InlineKeyboardButton("❌ CLEAR", callback_data="clearamt"), InlineKeyboardButton("0", callback_data="num0"), InlineKeyboardButton("✅ CONFIRM", callback_data="done")],
        [InlineKeyboardButton("🔙 BACK", callback_data="backkkk")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

async def num_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, num: str):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    amt = str(UserData.get("pay_amount", user_id, "")) + num
    UserData.set("pay_amount", amt, user_id)
    
    text = (
        "<blockquote>💰 ENTER CUSTOM AMOUNT</blockquote>\n\n"
        f"Amount: ₹{amt}\n\n"
        "Use the keypad below to enter amount."
    )
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=query.message.reply_markup
    )

async def clear_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    UserData.set("pay_amount", "", user_id)
    
    text = (
        "<blockquote>💰 ENTER CUSTOM AMOUNT</blockquote>\n\n"
        "Amount: ₹0\n\n"
        "Use the keypad below to enter amount."
    )
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=query.message.reply_markup
    )

async def done_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    amt = UserData.get("pay_amount", user_id)
    
    if not amt:
        await query.message.reply_text("❌ Enter amount first")
        return
    
    UserData.set("last_deposit_amount", float(amt), user_id)
    await add_payment_qr(update, context)

async def add_payment_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    amount = UserData.get("last_deposit_amount", user_id)
    
    if not amount:
        await query.message.reply_text("❌ Amount missing")
        return
    
    upi = "bablu.xyztb@fam"
    url = f"{API_URL}/qr.php?upi={upi}&amount={amount}"
    
    try:
        resp = requests.get(url)
        data = resp.json()
    except:
        await query.message.reply_text("❌ API ERROR")
        return
    
    if data.get("status") != "success":
        await query.message.reply_text("❌ QR GENERATION FAILED")
        return
    
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    UserData.set("addpay_order_id", order_id, user_id)
    
    caption = (
        "<blockquote>💰 PAYMENT QR GENERATED</blockquote>\n"
        f"Scan the QR and complete payment.\n\nAmount: ₹{amount}"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ VERIFY PAYMENT", callback_data="verify_addpay")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="cancel")]
    ]
    
    await query.message.reply_photo(
        photo=qr_url,
        caption=caption,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ============================================================
# PROFILE & ORDERS
# ============================================================

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    balance = UserResources.get_balance(user_id)
    orders = UserResources.get_orders(user_id)
    first_name = query.from_user.first_name or "User"
    
    joined = UserData.get("joined_date", user_id)
    if not joined:
        member_since = "Today"
    else:
        diff = int(datetime.now().timestamp()) - int(joined)
        if diff < 86400:
            member_since = "Today"
        elif diff < 86400 * 7:
            member_since = f"{diff // 86400} days ago"
        elif diff < 86400 * 30:
            member_since = f"{diff // (86400 * 7)} weeks ago"
        else:
            member_since = f"{diff // (86400 * 30)} months ago"
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👤 YOUR PROFILE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Name: {first_name}\n"
        f"🆔 User ID: {user_id}\n"
        f"💰 Balance: ₹{balance}\n"
        f"📅 Member Since: {member_since}\n"
        f"🛒 Total Orders: {orders}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 BUY HACK", callback_data="shopnawkk"), InlineKeyboardButton("📦 MY KEY", callback_data="orderksk")],
        [InlineKeyboardButton("🔙 BACK", callback_data="backkkk")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    user_actions = UserData.get("userhAC", user_id, [])
    
    if not user_actions:
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📦 <b>MY ORDERS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "You haven't placed any orders yet.\n"
            "Tap 🛒 Shop Now to get started!"
        )
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="backkkk")]]
        
        try:
            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                raise e
    else:
        latest = user_actions[-10:][::-1]
        text = "\n\n".join([str(item) for item in latest if item])
        keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="backkkk")]]
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                raise e

# ============================================================
# BACK & SUPPORT COMMANDS
# ============================================================

async def back_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start_callback(update, context)

async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    balance = UserResources.get_balance(user_id)
    
    text = (
        "<blockquote>🌟 WELCOME TO HACK STORE 🌙</blockquote>\n\n"
        "✨ Your ultimate destination for premium mods, cheats & clients!\n\n"
        "<blockquote>🚀 PREMIUM FEATURES\n\n"
        "⚡ Instant Key Delivery\n"
        "💳 Secure Auto-Payment System\n"
        "🛡 100% Anti-Ban Support</blockquote>\n\n"
        f"<blockquote>💰 Your Balance: ₹{balance}</blockquote>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 BUY HACK", callback_data="shopnawkk")],
        [InlineKeyboardButton("📦 MY KEY", callback_data="orderksk"), InlineKeyboardButton("👤 PROFILE", callback_data="profilemmm")],
        [InlineKeyboardButton("📖 HOW TO USE", callback_data="spinj"), InlineKeyboardButton("💬 SUPPORT", callback_data="supportj")],
        [InlineKeyboardButton("💰 ADD FUND", callback_data="addpayment")],
        [InlineKeyboardButton("📩 PAY PROOF", url="https://t.me/subhajit_feedback"), InlineKeyboardButton("📥 DOWNLOAD APK", url="https://t.me/+hasTLSVjzaZjZGVl")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
━━━━━━━━━━━━━━━━━━━━
💬 <b>Support — Seller</b> 🛡
━━━━━━━━━━━━━━━━━━━━

Need help? We're here for you! ⚡

📩 <b>Telegram:</b> ⭐

<a href="https://t.me/UR_SUBHAJIT0">𝐒υвʜᴀᎫιт</a> ⭐

💡 <i>Include your User ID (from Profile)
when contacting for faster help.</i>
"""
    
    keyboard = [
        [InlineKeyboardButton("💬 WHATSAPP", url="https://wa.me/917908696630")],
        [InlineKeyboardButton("🔙 BACK", callback_data="backkkk")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

async def spinj_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
🎥 <b>Watch the full tutorial video below</b>

👇
"""
    
    keyboard = [
        [InlineKeyboardButton("▶️ Watch Tutorial", url="https://t.me/hehehehhhsljg/162")],
        [InlineKeyboardButton("🔙 BACK", callback_data="backkkk")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        await query.delete_message()
    except:
        pass
    
    await query.message.reply_text(
        "❌ Cancelled",
        parse_mode="HTML"
    )

# ============================================================
# ADMIN COMMANDS
# ============================================================

async def add_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "💡 Send User Telegram Id & Amount\n\n"
                "⚠️ Use Format: `user_id 10`\n\n"
                "Add - Before Amount To Deduct Balance Like `-10`",
                parse_mode="HTML"
            )
            return
        
        target_user = args[0].strip()
        amount = float(args[1].strip())
        
        current_balance = UserResources.get_balance(target_user)
        new_balance = current_balance + amount
        UserResources.set_balance(target_user, new_balance)
        
        time_info = get_indian_time()
        await update.message.reply_text(
            f"<b>✅ Account Updated!\n\n"
            f"💰 {'Added' if amount > 0 else 'Deducted'}: ₹{abs(amount)}\n"
            f"💳 Final Balance: ₹{UserResources.get_balance(target_user)}</b>",
            parse_mode="HTML"
        )
        
        admin_actions = BotData.get("AdmAC", [])
        admin_actions.append(
            f"<b>📆 Time:</b> {time_info['easy_time']}\n"
            f"👥 <b>By {update.effective_user.first_name}</b> [ID: <code>{user_id}</code>]\n"
            f"🔍<b> Action: </b> {'Added' if amount > 0 else 'Deducted'} {abs(amount)} Rs To {target_user} Account"
        )
        BotData.set("AdmAC", admin_actions)
        
    except ValueError as e:
        await update.message.reply_text(f"❌ Invalid amount format. Use numbers only.\nError: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def add_reseller_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    try:
        args = context.args
        if not args:
            await update.message.reply_text("📩 Send me id reseller")
            return
        
        target_user = args[0]
        resellers = BotData.get("resellers_list", [])
        if target_user in [str(r) for r in resellers]:
            await update.message.reply_text("⚠️ User already a reseller.")
            return
        
        resellers.append(target_user)
        BotData.set("resellers_list", resellers)
        
        await update.message.reply_text(
            f"✅ User <code>{target_user}</code> added as Reseller.",
            parse_mode="html"
        )
        
        try:
            await context.bot.send_message(
                chat_id=target_user,
                text="🎉 You are now a Reseller 👑"
            )
        except:
            pass
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def remove_reseller_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    try:
        args = context.args
        if not args:
            await update.message.reply_text("📩 Send me reseller id to remove")
            return
        
        target_user = args[0]
        resellers = BotData.get("resellers_list", [])
        if target_user not in [str(r) for r in resellers]:
            await update.message.reply_text("⚠️ User is not a reseller.")
            return
        
        resellers = [r for r in resellers if str(r) != target_user]
        BotData.set("resellers_list", resellers)
        
        await update.message.reply_text(
            f"✅ User <code>{target_user}</code> removed from Resellers.",
            parse_mode="html"
        )
        
        try:
            await context.bot.send_message(
                chat_id=target_user,
                text="❌ You are no longer a Reseller."
            )
        except:
            pass
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def reseller_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    resellers = BotData.get("resellers_list", [])
    if not resellers:
        await update.message.reply_text("📭 No resellers found.")
        return
    
    text = "👑 <b>Reseller List</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for i, reseller_id in enumerate(resellers, 1):
        text += f"{i}. 🆔 <code>{reseller_id}</code>\n"
    
    text += f"\n━━━━━━━━━━━━━━━━━━\n📊 Total Resellers: {len(resellers)}"
    
    await update.message.reply_text(text, parse_mode="html")

async def admin_actions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    actions = BotData.get("AdmAC", [])
    if not actions:
        await update.message.reply_text("No admin actions recorded.")
        return
    
    latest = actions[-10:][::-1]
    await update.message.reply_text("\n\n".join(latest), parse_mode="HTML")

async def shop_setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        await update.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    text = f"""<b>
👋 Welcome {update.effective_user.first_name} 🎉

━━━━━━━━━━━━━━━
SHOP 🛍️ MOOD
━━━━━━━━━━━━━━━
</b>"""
    
    keyboard = [
        [InlineKeyboardButton("📦 𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗✅", callback_data="SHOPADMIN_P1")],
        [InlineKeyboardButton("📦 PROXY SERVER [DR-CL]", callback_data="SHOPADMIN_P3")],
        [InlineKeyboardButton("🔥 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀", callback_data="SHOPADMIN_P2")],
        [InlineKeyboardButton("🔙 BACK", callback_data="admin")]
    ]
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

# ============================================================
# SHOP ADMIN COMMANDS
# ============================================================

async def shop_admin_p1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    def get_old(day):
        price = BotData.get(f"drip_{day}d_price", 0)
        reseller = BotData.get(f"drip_{day}d_reseller_price", 0)
        stock = BotData.get(f"drip_{day}d_keys", [])
        
        if not stock:
            st = "❌ Out of Stock"
        elif len(stock) <= 2:
            st = f"⚠️ Only {len(stock)} left!"
        else:
            st = "✅ In Stock"
        
        return price, reseller, st
    
    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p15, r15, s15 = get_old(15)
    p30, r30, s30 = get_old(30)
    
    text = (
        "🎮 🛒  𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗✅\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 1D Reseller: ₹{r1}\n"
        f"💰 1D Price: ₹{p1}\n📦 {s1}\n\n"
        f"👑 3D Reseller: ₹{r3}\n"
        f"💰 3D Price: ₹{p3}\n📦 {s3}\n\n"
        f"👑 7D Reseller: ₹{r7}\n"
        f"💰 7D Price: ₹{p7}\n📦 {s7}\n\n"
        f"👑 15D Reseller: ₹{r15}\n"
        f"💰 15D Price: ₹{p15}\n📦 {s15}\n\n"
        f"👑 30D Reseller: ₹{r30}\n"
        f"💰 30D Price: ₹{p30}\n📦 {s30}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 Select duration below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("👑 RESELLER 1D", callback_data="SHOPADD_PM 6")],
        [InlineKeyboardButton("1D Price", callback_data="SHOPADD_PM 1"), InlineKeyboardButton("Add 1D Key", callback_data="SHOPADDKEY 1")],
        [InlineKeyboardButton("👑 RESELLER 3D", callback_data="SHOPADD_PM 7")],
        [InlineKeyboardButton("3D Price", callback_data="SHOPADD_PM 2"), InlineKeyboardButton("Add 3D Key", callback_data="SHOPADDKEY 2")],
        [InlineKeyboardButton("👑 RESELLER 7D", callback_data="SHOPADD_PM 8")],
        [InlineKeyboardButton("7D Price", callback_data="SHOPADD_PM 3"), InlineKeyboardButton("Add 7D Key", callback_data="SHOPADDKEY 3")],
        [InlineKeyboardButton("👑 RESELLER 15D", callback_data="SHOPADD_PM 9")],
        [InlineKeyboardButton("15D Price", callback_data="SHOPADD_PM 4"), InlineKeyboardButton("Add 15D Key", callback_data="SHOPADDKEY 4")],
        [InlineKeyboardButton("👑 RESELLER 30D", callback_data="SHOPADD_PM 10")],
        [InlineKeyboardButton("30D Price", callback_data="SHOPADD_PM 5"), InlineKeyboardButton("Add 30D Key", callback_data="SHOPADDKEY 5")],
        [InlineKeyboardButton("🔙 Back", callback_data="setshop_psue")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

async def shop_admin_p2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    def get_old(day):
        price = BotData.get(f"HG_{day}d_price", 0)
        reseller = BotData.get(f"HG_{day}d_reseller_price", 0)
        stock = BotData.get(f"HG_{day}d_keys", [])
        
        if not stock:
            st = "❌ Out of Stock"
        elif len(stock) <= 2:
            st = f"⚠️ Only {len(stock)} left!"
        else:
            st = "✅ In Stock"
        
        return price, reseller, st
    
    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p14, r14, s14 = get_old(14)
    p21, r21, s21 = get_old(21)
    
    text = (
        "📦 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 1D Reseller: ₹{r1}\n"
        f"💰 1D Price: ₹{p1}\n"
        f"📦 {s1}\n\n"
        f"👑 3D Reseller: ₹{r3}\n"
        f"💰 3D Price: ₹{p3}\n"
        f"📦 {s3}\n\n"
        f"👑 7D Reseller: ₹{r7}\n"
        f"💰 7D Price: ₹{p7}\n"
        f"📦 {s7}\n\n"
        f"👑 14D Reseller: ₹{r14}\n"
        f"💰 14D Price: ₹{p14}\n"
        f"📦 {s14}\n\n"
        f"👑 21D Reseller: ₹{r21}\n"
        f"💰 21D Price: ₹{p21}\n"
        f"📦 {s21}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 Select duration below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("👑 RESELLER 1D", callback_data="SHOPADD_PM 316"), InlineKeyboardButton("1D Price", callback_data="SHOPADD_PM 311"), InlineKeyboardButton("Add 1D Key", callback_data="SHOPADDKEY 306")],
        [InlineKeyboardButton("👑 RESELLER 3D", callback_data="SHOPADD_PM 317"), InlineKeyboardButton("3D Price", callback_data="SHOPADD_PM 312"), InlineKeyboardButton("Add 3D Key", callback_data="SHOPADDKEY 307")],
        [InlineKeyboardButton("👑 RESELLER 7D", callback_data="SHOPADD_PM 318"), InlineKeyboardButton("7D Price", callback_data="SHOPADD_PM 313"), InlineKeyboardButton("Add 7D Key", callback_data="SHOPADDKEY 308")],
        [InlineKeyboardButton("👑 RESELLER 14D", callback_data="SHOPADD_PM 319"), InlineKeyboardButton("14D Price", callback_data="SHOPADD_PM 314"), InlineKeyboardButton("Add 14D Key", callback_data="SHOPADDKEY 309")],
        [InlineKeyboardButton("👑 RESELLER 21D", callback_data="SHOPADD_PM 320"), InlineKeyboardButton("21D Price", callback_data="SHOPADD_PM 315"), InlineKeyboardButton("Add 21D Key", callback_data="SHOPADDKEY 310")],
        [InlineKeyboardButton("🔙 Back", callback_data="setshop_psue")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

async def shop_admin_p3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    def get_old(day):
        price = BotData.get(f"PATO_{day}d_price", 0)
        reseller = BotData.get(f"PATO_{day}d_reseller_price", 0)
        stock = BotData.get(f"PATO_{day}d_keys", [])
        
        if not stock:
            st = "❌ Out of Stock"
        elif len(stock) <= 2:
            st = f"⚠️ Only {len(stock)} left!"
        else:
            st = "✅ In Stock"
        
        return price, reseller, st
    
    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p15, r15, s15 = get_old(15)
    
    text = (
        "🎮 PROXY SERVER [DR-CL]\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 1D Reseller: ₹{r1}\n"
        f"💰 1D Price: ₹{p1}\n📦 {s1}\n\n"
        f"👑 3D Reseller: ₹{r3}\n"
        f"💰 3D Price: ₹{p3}\n📦 {s3}\n\n"
        f"👑 7D Reseller: ₹{r7}\n"
        f"💰 7D Price: ₹{p7}\n📦 {s7}\n\n"
        f"👑 15D Reseller: ₹{r15}\n"
        f"💰 15D Price: ₹{p15}\n📦 {s15}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 Select duration below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("👑 RESELLER 1D", callback_data="SHOPADD_PM 221"), InlineKeyboardButton("1D Price", callback_data="SHOPADD_PM 191"), InlineKeyboardButton("Add 1D Key", callback_data="SHOPADDKEY 101")],
        [InlineKeyboardButton("👑 RESELLER 3D", callback_data="SHOPADD_PM 22"), InlineKeyboardButton("3D Price", callback_data="SHOPADD_PM 19"), InlineKeyboardButton("Add 3D Key", callback_data="SHOPADDKEY 10")],
        [InlineKeyboardButton("👑 RESELLER 7D", callback_data="SHOPADD_PM 23"), InlineKeyboardButton("7D Price", callback_data="SHOPADD_PM 20"), InlineKeyboardButton("Add 7D Key", callback_data="SHOPADDKEY 11")],
        [InlineKeyboardButton("👑 RESELLER 15D", callback_data="SHOPADD_PM 24"), InlineKeyboardButton("15D Price", callback_data="SHOPADD_PM 21"), InlineKeyboardButton("Add 15D Key", callback_data="SHOPADDKEY 12")],
        [InlineKeyboardButton("🔙 Back", callback_data="setshop_psue")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

# ============================================================
# SHOPADD HANDLERS - FIXED
# ============================================================

async def shopadd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting price for a product"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    data = query.data.split()
    if len(data) < 2:
        await query.message.reply_text("❌ Invalid option")
        return
    
    option = data[1]
    
    price_map = {
        "1": ("drip_1d_price", "DRIP CLIENT APK MOD\n1 Days"),
        "2": ("drip_3d_price", "DRIP CLIENT APK MOD\n3 Days"),
        "3": ("drip_7d_price", "DRIP CLIENT APK MOD\n7 Days"),
        "4": ("drip_15d_price", "DRIP CLIENT APK MOD\n15 Days"),
        "5": ("drip_30d_price", "DRIP CLIENT APK MOD\n30 Days"),
        "6": ("drip_1d_reseller_price", "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n1 Days"),
        "7": ("drip_3d_reseller_price", "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n3 Days"),
        "8": ("drip_7d_reseller_price", "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n7 Days"),
        "9": ("drip_15d_reseller_price", "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n15 Days"),
        "10": ("drip_30d_reseller_price", "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n30 Days"),
        "311": ("HG_1d_price", "🛒 PRIME HOOK\n1 Days"),
        "312": ("HG_3d_price", "🛒 PRIME HOOK\n3 Days"),
        "313": ("HG_7d_price", "🛒 PRIME HOOK\n7 Days"),
        "314": ("HG_14d_price", "🛒 PRIME HOOK\n14 Days"),
        "315": ("HG_21d_price", "🛒 PRIME HOOK\n21 Days"),
        "316": ("HG_1d_reseller_price", "👑 RESELLER PANEL\n🛒 PRIME HOOK\n1 Days"),
        "317": ("HG_3d_reseller_price", "👑 RESELLER PANEL\n🛒 PRIME HOOK\n3 Days"),
        "318": ("HG_7d_reseller_price", "👑 RESELLER PANEL\n🛒 PRIME HOOK\n7 Days"),
        "319": ("HG_14d_reseller_price", "👑 RESELLER PANEL\n🛒 PRIME HOOK\n14 Days"),
        "320": ("HG_21d_reseller_price", "👑 RESELLER PANEL\n🛒 PRIME HOOK\n21 Days"),
        "191": ("PATO_1d_price", "🛒 PROXY SERVER\n1 Days"),
        "19": ("PATO_3d_price", "🛒 PROXY SERVER\n3 Days"),
        "20": ("PATO_7d_price", "🛒 PROXY SERVER\n7 Days"),
        "21": ("PATO_15d_price", "🛒 PROXY SERVER\n10 Days"),
        "221": ("PATO_1d_reseller_price", "👑 RESELLER PANEL\n🛒 PROXY SERVER\n1 Days"),
        "22": ("PATO_3d_reseller_price", "👑 RESELLER PANEL\n🛒 PROXY SERVER\n3 Days"),
        "23": ("PATO_7d_reseller_price", "👑 RESELLER PANEL\n🛒 PROXY SERVER\n7 Days"),
        "24": ("PATO_15d_reseller_price", "👑 RESELLER PANEL\n🛒 PROXY SERVER\n10 Days"),
    }
    
    if option not in price_map:
        await query.message.reply_text("❌ Invalid option number.")
        return
    
    price_key, title = price_map[option]
    
    # Store in context
    context.user_data['waiting_for_price'] = True
    context.user_data['price_key'] = price_key
    context.user_data['price_title'] = title
    
    await query.message.reply_text(
        f"🛒 <b>{title}</b>\n\n"
        "Send key price (numbers only).\n\n"
        "Type /cancel to stop.",
        parse_mode="HTML"
    )

async def shopadd_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding a key for a product"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    data = query.data.split()
    if len(data) < 2:
        await query.message.reply_text("❌ Invalid option")
        return
    
    option = data[1]
    
    key_map = {
        "1": "drip_1d_keys",
        "2": "drip_3d_keys",
        "3": "drip_7d_keys",
        "4": "drip_15d_keys",
        "5": "drip_30d_keys",
        "306": "HG_1d_keys",
        "307": "HG_3d_keys",
        "308": "HG_7d_keys",
        "309": "HG_14d_keys",
        "310": "HG_21d_keys",
        "101": "PATO_1d_keys",
        "10": "PATO_3d_keys",
        "11": "PATO_7d_keys",
        "12": "PATO_15d_keys",
    }
    
    if option not in key_map:
        await query.message.reply_text("❌ Invalid option number.")
        return
    
    key_name = key_map[option]
    
    title_map = {
        "1": "DRIP CLIENT APK MOD\n1d Key",
        "2": "DRIP CLIENT APK MOD\n3d Key",
        "3": "DRIP CLIENT APK MOD\n7d Key",
        "4": "DRIP CLIENT APK MOD\n15d Key",
        "5": "DRIP CLIENT APK MOD\n30d Key",
        "306": "PRIME HOOK\n1d Key",
        "307": "PRIME HOOK\n3d Key",
        "308": "PRIME HOOK\n7d Key",
        "309": "PRIME HOOK\n14d Key",
        "310": "PRIME HOOK\n21d Key",
        "101": "PROXY SERVER\n1d Key",
        "10": "PROXY SERVER\n3d Key",
        "11": "PROXY SERVER\n7d Key",
        "12": "PROXY SERVER\n10d Key",
    }
    
    title = title_map.get(option, "Product")
    
    # Store in context
    context.user_data['waiting_for_key'] = True
    context.user_data['key_name'] = key_name
    context.user_data['key_title'] = title
    
    await query.message.reply_text(
        f"🛒 <b>{title}</b>\n\n"
        "Send the key (minimum 3 characters).\n\n"
        "Type /cancel to stop.",
        parse_mode="HTML"
    )

# ============================================================
# SINGLE MESSAGE HANDLER - FIXED
# ============================================================

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages in one place"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    # Check if user is admin
    is_admin_user = is_admin(user_id)
    
    # 1. Check for price input
    if context.user_data.get('waiting_for_price'):
        if text == "/cancel":
            await update.message.reply_text("❌ Cancelled", parse_mode="HTML")
            context.user_data['waiting_for_price'] = False
            return
        
        try:
            price = float(text.strip())
            price_key = context.user_data.get('price_key')
            title = context.user_data.get('price_title')
            
            if not price_key:
                await update.message.reply_text("❌ Error: No product selected. Please start again.")
                context.user_data['waiting_for_price'] = False
                return
            
            BotData.set(price_key, price)
            
            time_info = get_indian_time()
            admin_actions = BotData.get("AdmAC", [])
            admin_actions.append(
                f"<b>📆 Time:</b> {time_info['easy_time']}\n"
                f"👥 <b>By {update.effective_user.first_name}</b> [ID: <code>{user_id}</code>]\n"
                f"🔍<b> Action: </b> {title} Price = ₹{price}"
            )
            BotData.set("AdmAC", admin_actions)
            
            await update.message.reply_text(
                f"✅ <b>Successfully Set</b>\n\n"
                f"{title} Price = ₹{price}",
                parse_mode="HTML"
            )
            context.user_data['waiting_for_price'] = False
            
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid number.\n"
                "Send numeric value like 90\n\n"
                "Type /cancel to stop.",
                parse_mode="HTML"
            )
        return
    
    # 2. Check for key input
    if context.user_data.get('waiting_for_key'):
        if text == "/cancel":
            await update.message.reply_text("❌ Cancelled", parse_mode="HTML")
            context.user_data['waiting_for_key'] = False
            return
        
        key_value = text.strip()
        
        if len(key_value) < 3:
            await update.message.reply_text("❌ Invalid Key. Minimum 3 characters.\n\nType /cancel to stop.", parse_mode="HTML")
            return
        
        key_name = context.user_data.get('key_name')
        title = context.user_data.get('key_title')
        
        if not key_name:
            await update.message.reply_text("❌ Error: No product selected. Please start again.")
            context.user_data['waiting_for_key'] = False
            return
        
        existing_data = BotData.get(key_name)
        
        if not existing_data:
            keys_list = []
        elif isinstance(existing_data, str):
            keys_list = [existing_data]
        else:
            keys_list = existing_data
        
        keys_list.append(key_value)
        BotData.set(key_name, keys_list)
        
        await update.message.reply_text(
            f"✅ <b>Key Added Successfully</b>\n\n"
            f"{title}\n"
            f"🔑 <code>{key_value}</code>\n"
            f"📦 Total Stock: {len(keys_list)}",
            parse_mode="HTML"
        )
        context.user_data['waiting_for_key'] = False
        return
    
    # 3. Check for admin input
    if context.user_data.get('waiting_for_admin'):
        if text == "/cancel":
            await update.message.reply_text("❌ Cancelled", parse_mode="HTML")
            context.user_data['waiting_for_admin'] = False
            return
        
        admin_id = text.strip()
        
        if not admin_id.isdigit():
            await update.message.reply_text("❌ Invalid User ID. Please send a numeric Telegram ID.", parse_mode="HTML")
            return
        
        admins = BotData.get("AllBotAdminss", [])
        
        if admin_id in admins:
            await update.message.reply_text("⚠️ Admin Already Exists", parse_mode="HTML")
        else:
            admins.append(admin_id)
            BotData.set("AllBotAdminss", admins)
            
            time_info = get_indian_time()
            admin_actions = BotData.get("AdmAC", [])
            admin_actions.append(
                f"<b>📆 Time:</b> {time_info['easy_time']}\n"
                f"👥 <b>By {update.effective_user.first_name}</b> [ID: <code>{user_id}</code>]\n"
                f"🔍<b> Action: </b> Added {admin_id} as Bot Admin"
            )
            BotData.set("AdmAC", admin_actions)
            
            await update.message.reply_text(
                f"✅ Admin Added Successfully: <code>{admin_id}</code>\n\n"
                f"📊 Total Admins: {len(admins)}",
                parse_mode="HTML"
            )
            
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text="🎉 Congratulations! You have been added as a Bot Admin.\n\nUse /admin to access admin panel."
                )
            except:
                pass
        
        context.user_data['waiting_for_admin'] = False
        return
    
    # 4. Check for broadcast input
    if context.user_data.get('waiting_for_broadcast'):
        if text == "/cancel":
            await update.message.reply_text("❌ Broadcast cancelled", parse_mode="HTML")
            context.user_data['waiting_for_broadcast'] = False
            return
        
        broadcast_msg = text
        
        users_data = BotData.get("users", {})
        user_ids = list(users_data.keys())
        
        if not user_ids:
            await update.message.reply_text("❌ No users found to broadcast.", parse_mode="HTML")
            context.user_data['waiting_for_broadcast'] = False
            return
        
        progress_msg = await update.message.reply_text(
            f"📣 <b>Broadcasting...</b>\n\n"
            f"📊 Total Users: {len(user_ids)}\n"
            f"⏳ Please wait...",
            parse_mode="HTML"
        )
        
        success_count = 0
        fail_count = 0
        
        for idx, uid in enumerate(user_ids):
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=f"📣 <b>Announcement</b>\n\n{broadcast_msg}",
                    parse_mode="HTML"
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(f"Failed to send to {uid}: {e}")
            
            if (idx + 1) % 10 == 0:
                try:
                    await progress_msg.edit_text(
                        f"📣 <b>Broadcasting...</b>\n\n"
                        f"📊 Progress: {idx + 1}/{len(user_ids)}\n"
                        f"✅ Success: {success_count}\n"
                        f"❌ Failed: {fail_count}",
                        parse_mode="HTML"
                    )
                except:
                    pass
        
        await progress_msg.edit_text(
            f"✅ <b>Broadcast Complete!</b>\n\n"
            f"📊 Total Users: {len(user_ids)}\n"
            f"✅ Success: {success_count}\n"
            f"❌ Failed: {fail_count}",
            parse_mode="HTML"
        )
        
        time_info = get_indian_time()
        admin_actions = BotData.get("AdmAC", [])
        admin_actions.append(
            f"<b>📆 Time:</b> {time_info['easy_time']}\n"
            f"👥 <b>By {update.effective_user.first_name}</b> [ID: <code>{user_id}</code>]\n"
            f"🔍<b> Action: </b> Broadcast sent to {success_count} users"
        )
        BotData.set("AdmAC", admin_actions)
        
        context.user_data['waiting_for_broadcast'] = False
        return

# ============================================================
# BROADCAST COMMAND
# ============================================================

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast functionality"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    await query.message.reply_text(
        "📣 <b>Send your broadcast message</b>\n\n"
        "This message will be sent to ALL bot users.\n\n"
        "Type /cancel to stop.",
        parse_mode="HTML"
    )
    context.user_data['waiting_for_broadcast'] = True

# ============================================================
# ADMIN ADD HANDLERS
# ============================================================

async def add_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Add Admin button click"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    await query.message.reply_text(
        "📩 Send UserID of Admin You Want To Add\n\n"
        "Type /cancel to stop.",
        parse_mode="HTML"
    )
    context.user_data['waiting_for_admin'] = True

async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new admin via command"""
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    await update.message.reply_text("📩 Send UserID of Admin You Want To Add\n\nType /cancel to stop.", parse_mode="HTML")
    context.user_data['waiting_for_admin'] = True

# ============================================================
# CALLBACK ROUTER
# ============================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    commands = {
        "shopnawkk": shop_command,
        "SHOP_P1": shop_p1,
        "SHOP_P2": shop_p2,
        "SHOP_P4": shop_p4,
        "profilemmm": profile_command,
        "orderksk": orders_command,
        "backkkk": back_command,
        "supportj": support_command,
        "spinj": spinj_command,
        "addpayment": add_payment,
        "clearamt": clear_amount,
        "done": done_amount,
        "autobuyi": verify_payment,
        "verify_addpay": verify_payment,
        "cancel": cancel_command,
        "admin": admin_callback,
        "setshop_psue": shop_setup_callback,
        "addreseller": add_reseller_callback,
        "removereseller": remove_reseller_callback,
        "resellerlist": reseller_list_callback,
        "TUSHAR_AdminAction": admin_actions_callback,
        "SHOPADMIN_P1": shop_admin_p1,
        "SHOPADMIN_P2": shop_admin_p2,
        "SHOPADMIN_P3": shop_admin_p3,
        "TUSHAR_AddAdmin": add_admin_callback,
        "broadcast": broadcast_command,
    }
    
    if data.startswith("buyjai") or data.startswith("buyjai_reseller"):
        await buy_command(update, context)
        return
    
    if data.startswith("num"):
        num = data[3:]
        await num_handler(update, context, num)
        return
    
    if data.startswith("admin"):
        await admin_callback(update, context)
        return
    
    if data.startswith("TUSHAR_Admins"):
        await admins_callback(update, context)
        return
    
    if data.startswith("ChangeAnyUserBal"):
        await add_balance_callback(update, context)
        return
    
    if data.startswith("SHOPADD_PM"):
        await shopadd_price(update, context)
        return
    
    if data.startswith("SHOPADDKEY"):
        await shopadd_key(update, context)
        return
    
    if data in commands:
        await commands[data](update, context)
        return
    
    await query.answer()

# ============================================================
# ADMIN CALLBACKS
# ============================================================

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    if query.data and "BotMode" in query.data:
        parts = query.data.split()
        if len(parts) >= 2:
            mode = parts[1]
            BotData.set("BotMode", mode)
            time_info = get_indian_time()
            admin_actions = BotData.get("AdmAC", [])
            admin_actions.append(
                f"<b>📆 Time:</b> {time_info['easy_time']}\n"
                f"👥 <b>By {query.from_user.first_name}</b> [ID: <code>{user_id}</code>]\n"
                f"🔍<b> Action: </b> Bot Mode Turned {mode}"
            )
            BotData.set("AdmAC", admin_actions)
    
    bot_mode = BotData.get("BotMode", "ON")
    bot_status = "🟢 On"
    toggle_text = "OFF"
    
    if bot_mode == "OFF":
        bot_status = "🔴 Off"
        toggle_text = "ON"
    
    text = f"""<b>
👋 Welcome {query.from_user.first_name} 🎉

━━━━━━━━━━━━━━━
🤖 Bot Status : {bot_status}
━━━━━━━━━━━━━━━
</b>"""
    
    keyboard = [
        [InlineKeyboardButton("👑 Admins", callback_data="TUSHAR_Admins")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton(f"🤖 Bot: {bot_status}", callback_data=f"admin BotMode {toggle_text}")],
        [InlineKeyboardButton("💰 Add Balance", callback_data="ChangeAnyUserBal"), InlineKeyboardButton("📝 Recent Actions", callback_data="TUSHAR_AdminAction")],
        [InlineKeyboardButton("📊 Shop Setup", callback_data="setshop_psue")],
        [InlineKeyboardButton("💰 Add Reseller", callback_data="addreseller"), InlineKeyboardButton("⛔ Remove Reseller", callback_data="removereseller")],
        [InlineKeyboardButton("📝 Reseller List", callback_data="resellerlist")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

async def shop_setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    text = f"""<b>
👋 Welcome {query.from_user.first_name} 🎉

━━━━━━━━━━━━━━━
SHOP 🛍️ MOOD
━━━━━━━━━━━━━━━
</b>"""
    
    keyboard = [
        [InlineKeyboardButton("📦 𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗✅", callback_data="SHOPADMIN_P1")],
        [InlineKeyboardButton("📦 PROXY SERVER [DR-CL]", callback_data="SHOPADMIN_P3")],
        [InlineKeyboardButton("🔥 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀", callback_data="SHOPADMIN_P2")],
        [InlineKeyboardButton("🔙 BACK", callback_data="admin")]
    ]
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

async def add_reseller_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    await query.message.reply_text("📩 Send me id reseller")

async def remove_reseller_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    await query.message.reply_text("📩 Send me reseller id to remove")

async def reseller_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    resellers = BotData.get("resellers_list", [])
    if not resellers:
        await query.message.reply_text("📭 No resellers found.")
        return
    
    text = "👑 <b>Reseller List</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for i, reseller_id in enumerate(resellers, 1):
        text += f"{i}. 🆔 <code>{reseller_id}</code>\n"
    
    text += f"\n━━━━━━━━━━━━━━━━━━\n📊 Total Resellers: {len(resellers)}"
    
    await query.message.reply_text(text, parse_mode="html")

async def admin_actions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    actions = BotData.get("AdmAC", [])
    if not actions:
        await query.message.reply_text("No admin actions recorded.")
        return
    
    latest = actions[-10:][::-1]
    await query.message.reply_text("\n\n".join(latest), parse_mode="HTML")

async def add_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    await query.message.reply_text(
        "💡 Send User Telegram Id & Amount\n\n"
        "⚠️ Use Format: `user_id 10`\n\n"
        "Add - Before Amount To Deduct Balance Like `-10`",
        parse_mode="HTML"
    )

async def admins_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return
    
    admins = BotData.get("AllBotAdminss", [])
    
    if len(query.data.split()) > 1:
        parts = query.data.split()
        if len(parts) >= 2:
            remove_id = parts[1]
            if remove_id in admins:
                admins.remove(remove_id)
                BotData.set("AllBotAdminss", admins)
                time_info = get_indian_time()
                admin_actions = BotData.get("AdmAC", [])
                admin_actions.append(
                    f"<b>📆 Time:</b> {time_info['easy_time']}\n"
                    f"👥 <b>By {query.from_user.first_name}</b> [ID: <code>{user_id}</code>]\n"
                    f"🔍<b> Action: </b> Removed {remove_id} from Bot Admin"
                )
                BotData.set("AdmAC", admin_actions)
    
    text = "<b>Here You Can Manage Your Admins</b>"
    keyboard = []
    
    for admin in admins:
        keyboard.append([
            InlineKeyboardButton(admin, callback_data=f"TUSHAR_Admins {admin}"),
            InlineKeyboardButton("❌", callback_data=f"TUSHAR_Admins {admin}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Add Admin", callback_data="TUSHAR_AddAdmin")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin")])
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

# ============================================================
# MAIN
# ============================================================

async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("Start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("ChangeAnyUserBal", add_balance_command))
    application.add_handler(CommandHandler("addreseller", add_reseller_command))
    application.add_handler(CommandHandler("removereseller", remove_reseller_command))
    application.add_handler(CommandHandler("resellerlist", reseller_list_command))
    application.add_handler(CommandHandler("TUSHAR_AddAdmin", add_admin_command))
    
    # SINGLE message handler for all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🤖 Bot is running...")
    print("📁 Data saved to: bot_data.json")
    print("✅ All features are now working properly!")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
