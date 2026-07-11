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

BOT_TOKEN = "8644946592:AAGqcXNTd0TRpYSkK3XkwGjXVQMwxTZKoao"
API_URL = "https://fampay.anujbots.xyz"
DATA_FILE = "bot_data.json"

# 👉 apna Firebase Realtime Database URL yahan daalo (rules: public read/write)
FIREBASE_URL = "https://subhajit-selling-bot-default-rtdb.asia-southeast1.firebasedatabase.app/"

# ============================================================
# FIREBASE LAYER
# ============================================================

def _fb_path(node: str = "bot_data") -> str:
    return f"{FIREBASE_URL.rstrip('/')}/{node}.json"

def fb_get(node: str = "bot_data", default=None):
    """Read from Firebase, fail silently and return default on any issue"""
    try:
        r = requests.get(_fb_path(node), timeout=10)
        if r.status_code == 200:
            val = r.json()
            if val is not None:
                return val
        return default
    except Exception:
        return default

def fb_set(value, node: str = "bot_data") -> bool:
    """Write full value to Firebase, fail silently on any issue"""
    try:
        r = requests.put(_fb_path(node), json=value, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

# ============================================================
# PERSISTENT STORAGE (Firebase primary, local file fallback/cache)
# ============================================================

def load_all_data():
    """Load all data - tries Firebase first, falls back to local file"""
    data = fb_get("bot_data")
    if isinstance(data, dict):
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
        if "users" not in data:
            data["users"] = {}
        return data

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                local = json.load(f)
                if "users" not in local:
                    local["users"] = {}
                return local
        except Exception:
            return {"users": {}}

    return {"users": {}}

def save_all_data(data):
    """Save all data - writes to Firebase and keeps a local file backup"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
    fb_set(data, "bot_data")

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

# ============================================================
# FIXED: GET STOCK FUNCTION
# ============================================================

def get_stock(key_name: str) -> List:
    """Get stock list from BotData"""
    stock = BotData.get(key_name, [])
    
    # If stock is None or empty
    if stock is None:
        return []
    
    # If stock is a string, convert to list
    if isinstance(stock, str):
        if stock.strip():
            return [stock.strip()]
        return []
    
    # If stock is a list
    if isinstance(stock, list):
        # Filter out empty strings and None values
        return [str(s).strip() for s in stock if s and str(s).strip()]
    
    # If stock is anything else, return empty list
    return []

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
        "<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Your Balance: ₹" + str(balance) +
        "</blockquote>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(
                "BUY HACK",
                callback_data="shopnawkk"
            )
        ],
        [
            InlineKeyboardButton(
                "MY KEY",
                callback_data="orderksk"
            ),
            InlineKeyboardButton(
                "PROFILE",
                callback_data="profilemmm"
            )
        ],
        [
            InlineKeyboardButton(
                "HOW TO USE",
                callback_data="spinj"
            ),
            InlineKeyboardButton(
                "SUPPORT",
                callback_data="supportj"
            )
        ],
        [
            InlineKeyboardButton(
                "ADD FUND",
                callback_data="addpayment"
            )
        ],
        [
            InlineKeyboardButton(
                "PAY PROOF",
                url="https://t.me/subhajit_feedback"
            ),
            InlineKeyboardButton(
                "DOWNLOAD APK",
                url="https://t.me/+hasTLSVjzaZjZGVl"
            )
        ]
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
    toggle_text = "BotMode OFF"
    
    if bot_mode == "OFF":
        bot_status = "🔴 Off"
        toggle_text = "BotMode ON"
    
    keyboard = [
        [InlineKeyboardButton("👑 Aᴅᴍɪɴs", callback_data="TUSHAR_Admins")],
        [
            InlineKeyboardButton("📣 Bʀᴏᴀᴅᴄᴀsᴛ", callback_data="broadcast"),
            InlineKeyboardButton("🤖 Bᴏᴛ: " + str(bot_status), callback_data="admin " + toggle_text)
        ],
        [
            InlineKeyboardButton("💰 Aᴅᴅ Bᴀʟᴀɴᴄᴇ", callback_data="ChangeAnyUserBal"),
            InlineKeyboardButton("📝 Rᴇᴄᴇɴᴛ Aᴅᴍɪɴ Aᴄᴛɪᴏɴs", callback_data="TUSHAR_AdminAction")
        ],
        [InlineKeyboardButton("📊 Shop setup", callback_data="setshop_psue")],
        [
            InlineKeyboardButton("💰 Aᴅᴅ Reseller", callback_data="addreseller"),
            InlineKeyboardButton("⛔ Remove Reseller", callback_data="removereseller")
        ],
        [InlineKeyboardButton("📝 Reseller List", callback_data="resellerlist")]
    ]
    
    text = f"""<b>
👋 Welcome {update.effective_user.first_name} 🎉

━━━━━━━━━━━━━━━
🤖 Bᴏᴛ Sᴛᴀᴛᴜs : {bot_status}
━━━━━━━━━━━━━━━
</b>"""
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

# ============================================================
# CANCEL AND DONE COMMANDS
# ============================================================

async def cancel_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    user_id = str(update.effective_user.id)
    
    context.user_data.clear()
    
    await update.message.reply_text(
        "<tg-emoji emoji-id='6278116707751956084'>❌</tg-emoji> <b>Cancelled</b>",
        parse_mode="HTML"
    )

async def done_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done command - finish adding keys"""
    user_id = str(update.effective_user.id)
    
    if context.user_data.get('waiting_for_key'):
        context.user_data['waiting_for_key'] = False
        context.user_data['key_name'] = None
        context.user_data['key_title'] = None
        
        await update.message.reply_text(
            "✅ <b>Done!</b>\n\nYou have finished adding keys.\nYou can add more anytime.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "ℹ️ You are not in 'Add Key' mode.\nUse 'Add Key' button first.",
            parse_mode="HTML"
        )

# ============================================================
# SHOP COMMANDS
# ============================================================

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                "DRIP CLIENT NON-ROOT",
                callback_data="SHOP_P1"
            )
        ],
        [
            InlineKeyboardButton(
                "PROXY SERVER [DR-CL]",
                callback_data="SHOP_P2"
            )
        ],
        [
            InlineKeyboardButton(
                "PRIME HOOK",
                callback_data="SHOP_P4"
            )
        ],
        [
            InlineKeyboardButton(
                "BACK",
                callback_data="backkkk"
            )
        ]
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
        "<tg-emoji emoji-id='6323104647636589287'>📦</tg-emoji> "
        "𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗"
        "<tg-emoji emoji-id='6179339404906079822'>✅</tg-emoji> "
        "( 𝘉𝘌𝘚𝘛 𝘚𝘌𝘓𝘓𝘌𝘙"
        "<tg-emoji emoji-id='5841693351249710667'>💫</tg-emoji> )\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<i><tg-emoji emoji-id='5258134813302332906'>📦</tg-emoji> Extra 2% discount applied</i>\n"
        "Choose a plan <tg-emoji emoji-id='5258336354642697821'>👇</tg-emoji>"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"1 DAY - ₹{prices['1d']}", callback_data=f"{buy_cmd} 1")],
        [InlineKeyboardButton(f"3 DAYS - ₹{prices['3d']}", callback_data=f"{buy_cmd} 2")],
        [InlineKeyboardButton(f"7 DAYS - ₹{prices['7d']}", callback_data=f"{buy_cmd} 3")],
        [InlineKeyboardButton(f"15 DAYS - ₹{prices['15d']}", callback_data=f"{buy_cmd} 4")],
        [InlineKeyboardButton(f"30 DAYS - ₹{prices['30d']}", callback_data=f"{buy_cmd} 5")],
        [InlineKeyboardButton("BACK", callback_data="shopnawkk")]
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
<tg-emoji emoji-id="6212942266957310140">📦</tg-emoji> PROXY SERVER [DR-CL]
━━━━━━━━━━━━━━━━━━━━

Choose a plan <tg-emoji emoji-id="5258336354642697821">👇</tg-emoji>
"""
    
    keyboard = [
        [InlineKeyboardButton(f"1 Day - ₹{prices['1d']}", callback_data=f"{buy_cmd} 6")],
        [InlineKeyboardButton(f"3 Days - ₹{prices['3d']}", callback_data=f"{buy_cmd} 7")],
        [InlineKeyboardButton(f"7 Days - ₹{prices['7d']}", callback_data=f"{buy_cmd} 8")],
        [InlineKeyboardButton(f"15 Days - ₹{prices['15d']}", callback_data=f"{buy_cmd} 9")],
        [InlineKeyboardButton("BACK", callback_data="shopnawkk")]
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
<tg-emoji emoji-id="6210705396449944693">🔥</tg-emoji> PRIME HOOK
━━━━━━━━━━━━━━━━━━━━

Choose a plan <tg-emoji emoji-id="5258336354642697821">👇</tg-emoji>
"""
    
    keyboard = [
        [InlineKeyboardButton(f"1 Day - ₹{prices['1d']}", callback_data=f"{buy_cmd} 10")],
        [InlineKeyboardButton(f"3 Days - ₹{prices['3d']}", callback_data=f"{buy_cmd} 11")],
        [InlineKeyboardButton(f"7 Days - ₹{prices['7d']}", callback_data=f"{buy_cmd} 12")],
        [InlineKeyboardButton(f"14 Days - ₹{prices['14d']}", callback_data=f"{buy_cmd} 13")],
        [InlineKeyboardButton(f"21 Days - ₹{prices['21d']}", callback_data=f"{buy_cmd} 14")],
        [InlineKeyboardButton("BACK", callback_data="shopnawkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ============================================================
# BUY COMMANDS - FIXED FOR OUT OF STOCK
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
    # FIXED: Get stock using fixed function
    keys = get_stock(product["key"])
    
    # Debug log
    logger.info(f"Stock for {product['key']}: {keys}")
    logger.info(f"Stock count: {len(keys)}")
    
    # FIXED: If no keys, show out of stock
    if len(keys) == 0:
        await message.reply_text(
            "❌ <b>Out of Stock!</b>\n\n"
            f"Sorry, {product['product']} is currently out of stock.\n"
            "Please contact admin for restock.",
            parse_mode="HTML"
        )
        return
    
    price = BotData.get(product["price"], 0)
    
    if price <= 0:
        await message.reply_text("❌ Price not set. Contact Admin.")
        return
    
    balance = UserResources.get_balance(user_id)
    time_info = get_indian_time()
    
    if balance < price:
        UserData.set("last_deposit_amount", price, user_id)
        UserData.set("last_product", product["product"], user_id)
        UserData.set("last_plan", product["plan"], user_id)
        await auto_buy(update, context, message, user_id, price, product)
        return
    
    # FIXED: Double check stock before deducting balance
    keys = get_stock(product["key"])
    if len(keys) == 0:
        await message.reply_text(
            "❌ <b>Out of Stock!</b>\n\n"
            f"Sorry, {product['product']} is currently out of stock.\n"
            "Please contact admin for restock.",
            parse_mode="HTML"
        )
        return
    
    # Deduct balance
    if not UserResources.cut_balance(user_id, price):
        await message.reply_text("❌ Insufficient balance.")
        return
    
    UserResources.add_order(user_id)
    key = str(keys[0])
    keys.pop(0)
    BotData.set(product["key"], keys)
    
    success_text = (
        f"<tg-emoji emoji-id='6172208745582433583'>🛒</tg-emoji> {product['title']}\n\n"
        f"<tg-emoji emoji-id='6005570495603282482'>🔑</tg-emoji> <b>Your Key:</b>\n<code>{key}</code>\n\n"
        f"<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> Deducted: ₹{price}\n"
        f"<tg-emoji emoji-id='5967456680940671207'>📦</tg-emoji> Remaining Stock: {len(keys)}\n"
        f"<tg-emoji emoji-id='6278102040438640835'>📦</tg-emoji> Time: {time_info['easy_time']}\n\n"
        f"<tg-emoji emoji-id='6264989131621798851'>📢</tg-emoji> <b>ALL FILES UPDATE</b>\n"
        f"@SUBHAJIT_UPDATES"
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
        f"<blockquote><tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> INSUFFICIENT BALANCE</blockquote>\n\n"
        f"┣ Product: {product['product']}\n"
        f"┣ Plan: {product['plan']}\n"
        f"┣ Price: ₹{price}\n"
        f"┣ Your Balance: ₹{balance}\n"
        f"┗ Need: ₹{need}"
    )
    
    keyboard = [
        [InlineKeyboardButton("VERIFY PAYMENT", callback_data="autobuyi")],
        [InlineKeyboardButton("CANCEL", callback_data="cancel")]
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
            f"<tg-emoji emoji-id='5348129380474306311'>✅</tg-emoji> Payment Success!\n\n"
            f"<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> Added ₹{amount}\n"
            f"<tg-emoji emoji-id='5346227465876423936'>💳</tg-emoji> New Balance: ₹{UserResources.get_balance(user_id)}",
            parse_mode="HTML"
        )
        
        admins = BotData.get("AllBotAdminss", [])
        for admin in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin,
                    text=(
                        f"<tg-emoji emoji-id='5348129380474306311'>✅</tg-emoji> New Payment Received!\n\n"
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
            "<tg-emoji emoji-id='6278116707751956084'>❌</tg-emoji> Payment Not Received\n\nPlease complete the payment and try again.",
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
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹0\n\n"
        "Use the keypad below to enter amount."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="num1"),
            InlineKeyboardButton("2", callback_data="num2"),
            InlineKeyboardButton("3", callback_data="num3")
        ],
        [
            InlineKeyboardButton("4", callback_data="num4"),
            InlineKeyboardButton("5", callback_data="num5"),
            InlineKeyboardButton("6", callback_data="num6")
        ],
        [
            InlineKeyboardButton("7", callback_data="num7"),
            InlineKeyboardButton("8", callback_data="num8"),
            InlineKeyboardButton("9", callback_data="num9")
        ],
        [
            InlineKeyboardButton("❌ CLEAR", callback_data="clearamt"),
            InlineKeyboardButton("0", callback_data="num0"),
            InlineKeyboardButton("✅ CONFIRM", callback_data="done")
        ],
        [
            InlineKeyboardButton("BACK", callback_data="backkkk")
        ]
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
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
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
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
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
        "<blockquote><tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> PAYMENT QR GENERATED</blockquote>\n"
        f"Scan the QR and complete payment.\n\nAmount: ₹{amount}"
    )
    
    keyboard = [
        [InlineKeyboardButton("VERIFY PAYMENT", callback_data="verify_addpay")],
        [InlineKeyboardButton("CANCEL", callback_data="cancel")]
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
        "<tg-emoji emoji-id='5346136537123801643'>👤</tg-emoji> YOUR PROFILE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<tg-emoji emoji-id='6008118472066732010'>📛</tg-emoji> Name: {first_name}\n"
        f"<tg-emoji emoji-id='5841693351249710667'>🆔</tg-emoji> User ID: {user_id}\n"
        f"<tg-emoji emoji-id='5348374038991357363'>💰</tg-emoji> Balance: ₹{balance}\n"
        f"<tg-emoji emoji-id='5348490024583185697'>📅</tg-emoji> Member Since: {member_since}\n"
        f"<tg-emoji emoji-id='6093562529978522804'>🛒</tg-emoji> Total Orders: {orders}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("BUY HACK", callback_data="shopnawkk"),
            InlineKeyboardButton("MY KEY", callback_data="orderksk")
        ],
        [InlineKeyboardButton("BACK", callback_data="backkkk")]
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
            "<tg-emoji emoji-id='6008118472066732010'>📦</tg-emoji> <b>MY ORDERS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "You haven't placed any orders yet.\n"
            "Tap <tg-emoji emoji-id='6093562529978522804'>🛒</tg-emoji> Shop Now to get started!"
        )
        keyboard = [[InlineKeyboardButton("BACK", callback_data="backkkk")]]
        
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
        keyboard = [[InlineKeyboardButton("BACK", callback_data="backkkk")]]
        
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
        "<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Your Balance: ₹" + str(balance) +
        "</blockquote>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("BUY HACK", callback_data="shopnawkk")
        ],
        [
            InlineKeyboardButton("MY KEY", callback_data="orderksk"),
            InlineKeyboardButton("PROFILE", callback_data="profilemmm")
        ],
        [
            InlineKeyboardButton("HOW TO USE", callback_data="spinj"),
            InlineKeyboardButton("SUPPORT", callback_data="supportj")
        ],
        [
            InlineKeyboardButton("ADD FUND", callback_data="addpayment")
        ],
        [
            InlineKeyboardButton("PAY PROOF", url="https://t.me/subhajit_feedback"),
            InlineKeyboardButton("DOWNLOAD APK", url="https://t.me/+hasTLSVjzaZjZGVl")
        ]
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
<tg-emoji emoji-id='5891120964468480450'>💬</tg-emoji> <b>Support — Seller</b> <tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji>
━━━━━━━━━━━━━━━━━━━━

Need help? We're here for you! <tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji>

📩 <b>Telegram:</b> <tg-emoji emoji-id='5776182936638329359'>⭐</tg-emoji>

<a href="https://t.me/UR_SUBHAJIT0">𝐒υʜᴀᎫιт</a> <tg-emoji emoji-id='6118314396440596568'>⭐</tg-emoji>

<tg-emoji emoji-id='5891120964468480450'>💡</tg-emoji> <i>Include your User ID (from Profile)
when contacting for faster help.</i>
"""
    
    keyboard = [
        [InlineKeyboardButton("WHATSAPP", url="https://wa.me/917908696630")],
        [InlineKeyboardButton("BACK", callback_data="backkkk")]
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
<tg-emoji emoji-id='5368653135101310687'>🎥</tg-emoji> <b>Watch the full tutorial video below</b>

<tg-emoji emoji-id='6222198028854367391'>👇</tg-emoji>
"""
    
    keyboard = [
        [InlineKeyboardButton("Watch Tutorial", url="https://t.me/hehehehhhsljg/162")],
        [InlineKeyboardButton("BACK", callback_data="backkkk")]
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
        "<tg-emoji emoji-id='6278116707751956084'>❌</tg-emoji> Cancelled",
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
                "⚠️ Use Format: `/ChangeAnyUserBal 123456789 100`\n\n"
                "Add - Before Amount To Deduct Balance Like `-10`\n\n"
                "Example:\n"
                "➕ Add: `/ChangeAnyUserBal 123456789 100`\n"
                "➖ Deduct: `/ChangeAnyUserBal 123456789 -50`",
                parse_mode="HTML"
            )
            return
        
        target_user = args[0].strip()
        amount = float(args[1].strip())
        
        current_balance = UserResources.get_balance(target_user)
        new_balance = current_balance + amount
        UserResources.set_balance(target_user, new_balance)
        
        time_info = get_indian_time()
        
        if amount > 0:
            action = "Added"
            emoji = "➕"
        else:
            action = "Deducted"
            emoji = "➖"
        
        await update.message.reply_text(
            f"<b>✅ Account Updated!</b>\n\n"
            f"{emoji} {action}: ₹{abs(amount)}\n"
            f"💳 Previous Balance: ₹{current_balance}\n"
            f"💳 New Balance: ₹{UserResources.get_balance(target_user)}",
            parse_mode="HTML"
        )
        
        admin_actions = BotData.get("AdmAC", [])
        admin_actions.append(
            f"<b>📆 Time:</b> {time_info['easy_time']}\n"
            f"👥 <b>By {update.effective_user.first_name}</b> [ID: <code>{user_id}</code>]\n"
            f"🔍<b> Action: </b> {action} {abs(amount)} Rs To {target_user} Account"
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
        [InlineKeyboardButton(" 𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗✅", callback_data="SHOPADMIN_P1")],
        [InlineKeyboardButton("PROXY SERVER [DR-CL]", callback_data="SHOPADMIN_P3")],
        [InlineKeyboardButton("𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀", callback_data="SHOPADMIN_P2")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin")]
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
# SHOPADD HANDLERS
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
    """Handle adding a key for a product - FIXED"""
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
        "1": "DRIP CLIENT APK MOD\n1 Days",
        "2": "DRIP CLIENT APK MOD\n3 Days",
        "3": "DRIP CLIENT APK MOD\n7 Days",
        "4": "DRIP CLIENT APK MOD\n15 Days",
        "5": "DRIP CLIENT APK MOD\n30 Days",
        "306": "🛒 PRIME HOOK\n1 Days",
        "307": "🛒 PRIME HOOK\n3 Days",
        "308": "🛒 PRIME HOOK\n7 Days",
        "309": "🛒 PRIME HOOK\n14 Days",
        "310": "🛒 PRIME HOOK\n21 Days",
        "101": "🛒 PROXY SERVER\n1 Days",
        "10": "🛒 PROXY SERVER\n3 Days",
        "11": "🛒 PROXY SERVER\n7 Days",
        "12": "🛒 PROXY SERVER\n15 Days",
    }

    title = title_map.get(option, key_name)

    context.user_data['waiting_for_key'] = True
    context.user_data['key_name'] = key_name
    context.user_data['key_title'] = title

    await query.message.reply_text(
        f"🛒 <b>{title}</b>\n\n"
        "Send key(s) to add (one per line for multiple).\n\n"
        "Type /done when finished or /cancel to stop.",
        parse_mode="HTML"
    )

# ============================================================
# BROADCAST SYSTEM (FIXED)
# ============================================================

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger broadcast flow - admin only"""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    if not is_admin(user_id):
        await query.message.reply_text("<b><i>🚫 You Are Not This Bot Admin</i></b>", parse_mode="HTML")
        return

    context.user_data['waiting_for_broadcast'] = True

    await query.message.reply_text(
        "📣 <b>Broadcast Message</b>\n\n"
        "Send the message you want to broadcast (text, photo, video, document — anything).\n"
        "It will be copied to every user who has used this bot.\n\n"
        "Type /cancel to stop.",
        parse_mode="HTML"
    )

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the broadcast to every stored user - admin only"""
    user_id = str(update.effective_user.id)

    context.user_data['waiting_for_broadcast'] = False

    if not is_admin(user_id):
        return

    all_users = UserData._data.get("users", {})
    user_ids = list(all_users.keys())
    total = len(user_ids)

    if total == 0:
        await update.message.reply_text("❌ No users found to broadcast to yet.")
        return

    status_msg = await update.message.reply_text(
        f"📣 <b>Broadcasting...</b>\n\n👥 Total: {total}\n✅ Sent: 0\n❌ Failed: 0",
        parse_mode="HTML"
    )

    sent = 0
    failed = 0
    blocked = 0

    for uid in user_ids:
        try:
            await context.bot.copy_message(
                chat_id=int(uid),
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            sent += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "not found" in err or "deactivated" in err:
                blocked += 1
            else:
                failed += 1

        if (sent + failed + blocked) % 25 == 0:
            try:
                await status_msg.edit_text(
                    f"📣 <b>Broadcasting...</b>\n\n👥 Total: {total}\n✅ Sent: {sent}\n🚫 Blocked: {blocked}\n❌ Failed: {failed}",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        await asyncio.sleep(0.05)

    try:
        await status_msg.edit_text(
            "✅ <b>Broadcast Completed</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: {total}\n"
            f"✅ Sent: {sent}\n"
            f"🚫 Blocked/Invalid: {blocked}\n"
            f"❌ Failed: {failed}",
            parse_mode="HTML"
        )
    except Exception:
        pass

# ============================================================
# UNIVERSAL TEXT/MEDIA HANDLER (for pending admin flows)
# ============================================================

async def universal_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes any incoming message to whichever admin flow is currently pending"""
    user_id = str(update.effective_user.id)

    # Broadcast flow accepts any message type (text/photo/video/etc.)
    if context.user_data.get('waiting_for_broadcast'):
        if not is_admin(user_id):
            context.user_data['waiting_for_broadcast'] = False
            return
        await broadcast_send(update, context)
        return

    text = (update.message.text or "").strip() if update.message and update.message.text else ""

    # Price update flow
    if context.user_data.get('waiting_for_price'):
        if not is_admin(user_id):
            context.user_data['waiting_for_price'] = False
            return
        if not text.isdigit():
            await update.message.reply_text("❌ Please send numbers only.")
            return
        price_key = context.user_data.get('price_key')
        title = context.user_data.get('price_title', '')
        BotData.set(price_key, int(text))
        context.user_data['waiting_for_price'] = False
        await update.message.reply_text(
            f"✅ <b>Price Updated</b>\n\n🛒 {title}\n💰 New Price: ₹{text}",
            parse_mode="HTML"
        )
        return

    # Key add flow
    if context.user_data.get('waiting_for_key'):
        if not is_admin(user_id):
            context.user_data['waiting_for_key'] = False
            return
        if not text:
            return
        key_name = context.user_data.get('key_name')
        title = context.user_data.get('key_title', '')
        new_keys = [k.strip() for k in text.split('\n') if k.strip()]
        if not new_keys:
            return
        existing = get_stock(key_name)
        existing.extend(new_keys)
        BotData.set(key_name, existing)
        await update.message.reply_text(
            f"✅ <b>{len(new_keys)} Key(s) Added</b>\n\n🛒 {title}\n📦 Total Stock: {len(existing)}\n\n"
            "Send more keys or /done to finish.",
            parse_mode="HTML"
        )
        return

# ============================================================
# MAIN (wires up start/admin/broadcast/text handling)
# ============================================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("cancel", cancel_command_handler))
    app.add_handler(CommandHandler("done", done_command_handler))

    app.add_handler(CallbackQueryHandler(broadcast_start, pattern="^broadcast$"))

    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, universal_input_handler))

    logger.info("Bot started polling")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
