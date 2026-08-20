# tusharbot.py - COMPLETE FIXED WITH PREMIUM EMOJIS & KEY ADD FIX
import requests
import json
import time
from datetime import datetime
import threading
from pymongo import MongoClient

BOT_TOKEN = "8388786589:AAFlxWhA0Jyg72HNsQydRlIqkkTedX54qjs"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# MongoDB Connection
MONGO_URI = "mongodb+srv://crasher3210_db_user:devex5656@cluster0.9y5axka.mongodb.net/?appName=Cluster0&compressors=zlib"
DB_NAME = "telegram_bot1"

# ========== CORRECT PREMIUM EMOJI IDs (19-digit) ==========
EMOJIS = {
    "cart": "5382194935057372936",      # 🛒 - FIXED!
    "back": "6039539366177541657",      # 🔙
    "shop": "6093739864883207194",      # 🏪
    "key": "5967456680940671207",       # 🔑
    "profile": "5346136537123801643",   # 👤
    "howto": "5345783284653636765",     # 📖
    "support": "5897567714674741148",   # 💬
    "addfund": "6278302366303260172",   # 💳
    "payproof": "5258134813302332906",  # 📄
    "download": "6028115612163641653",  # 📥
    "balance": "5348392971207194994",   # 💰
    "success": "5348129380474306311",   # ✅
    "danger": "6278116707751956084",    # ❌
    "warning": "5447644880824181073",   # ⚠️
    "info": "5195033767969839232",      # ℹ️
    "lightbulb": "5420323339723881652", # 💡
    "clock": "5116553153419936517",     # ⏳
    "package": "6179339404906079822",   # 📦
    "drip_emoji": "6323104647636589287", # DRIP
    "silent_emoji": "6325561995995126107", # SILENT
    "hg_emoji": "6210705396449944693",   # HG
    "orders": "6008118472066732010",     # 📦 Orders
    "video": "5258601973167539896",      # 🎥
    "money": "6089104607328342288",      # 💰
    "time": "6278102040438640835",       # ⏰
    "announce": "6264989131621798851",   # 📢
    "buy": "6172208745582433583",        # 🛒
    "stock": "5278467510604160626",      # 📦
    "user": "5317006024517912643",       # 👤
    "mykeys": "6176966310920983412",     # 📦
}

def emoji_tag(emoji_id, char="🛒"):
    """Helper to create premium emoji tags with correct format"""
    return f'<tg-emoji emoji-id="{emoji_id}">{char}</tg-emoji>'

class MongoDB:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = MongoClient(MONGO_URI)
            cls._instance.db = cls._instance.client[DB_NAME]
            cls._instance._initialize_collections()
        return cls._instance
    
    def _initialize_collections(self):
        collections = ['bot_data', 'user_data', 'pending_commands', 'pending_payments', 'processed_payments', 'payment_orders']
        for coll in collections:
            if coll not in self.db.list_collection_names():
                self.db.create_collection(coll)
        
        self.db.bot_data.create_index("key", unique=True)
        self.db.user_data.create_index([("user_id", 1), ("key", 1)], unique=True)
        self.db.pending_payments.create_index("user_id", unique=True)
        self.db.processed_payments.create_index("order_id", unique=True)
        self.db.payment_orders.create_index("order_id", unique=True)
        self.db.payment_orders.create_index("user_id")
        self.db.payment_orders.create_index("status")
    
    def get_collection(self, name):
        return self.db[name]

mongo = MongoDB()

class DataStore:
    def __init__(self):
        self.collection = mongo.get_collection('bot_data')
    
    def get(self, key, default=None):
        doc = self.collection.find_one({"key": key})
        return doc.get("value") if doc else default
    
    def set(self, key, value):
        self.collection.update_one(
            {"key": key},
            {"$set": {"value": value}},
            upsert=True
        )
    
    def get_data(self, key):
        return self.get(key)
    
    def save_data(self, key, value):
        self.set(key, value)
    
    def delete(self, key):
        self.collection.delete_one({"key": key})
    
    def find(self, query={}):
        return list(self.collection.find(query))

bot_data = DataStore()

class UserDataStore:
    def __init__(self):
        self.collection = mongo.get_collection('user_data')
    
    def get(self, user_id, key, default=None):
        doc = self.collection.find_one({"user_id": str(user_id), "key": key})
        return doc.get("value") if doc else default
    
    def set(self, user_id, key, value):
        self.collection.update_one(
            {"user_id": str(user_id), "key": key},
            {"$set": {"value": value}},
            upsert=True
        )
    
    def delete(self, user_id, key):
        self.collection.delete_one({"user_id": str(user_id), "key": key})
    
    def get_all_users(self):
        users = self.collection.distinct("user_id")
        return list(users)

user_data_store = UserDataStore()

class PendingCommandsStore:
    def __init__(self):
        self.collection = mongo.get_collection('pending_commands')
    
    def get(self, user_id, default=None):
        doc = self.collection.find_one({"user_id": str(user_id)})
        return doc.get("command") if doc else default
    
    def set(self, user_id, command):
        self.collection.update_one(
            {"user_id": str(user_id)},
            {"$set": {"command": command}},
            upsert=True
        )
    
    def delete(self, user_id):
        self.collection.delete_one({"user_id": str(user_id)})

pending_commands_store = PendingCommandsStore()

class PendingPaymentsStore:
    def __init__(self):
        self.collection = mongo.get_collection('pending_payments')
    
    def get(self, user_id):
        doc = self.collection.find_one({"user_id": str(user_id)})
        return doc.get("data") if doc else None
    
    def set(self, user_id, data):
        self.collection.update_one(
            {"user_id": str(user_id)},
            {"$set": {"data": data}},
            upsert=True
        )
    
    def delete(self, user_id):
        self.collection.delete_one({"user_id": str(user_id)})
    
    def get_all(self):
        docs = self.collection.find()
        return {doc["user_id"]: doc["data"] for doc in docs}

pending_payments_store = PendingPaymentsStore()

class ProcessedPaymentsStore:
    def __init__(self):
        self.collection = mongo.get_collection('processed_payments')
    
    def add(self, order_id, user_id, amount):
        doc = {
            "order_id": order_id,
            "user_id": str(user_id),
            "amount": amount,
            "processed_at": datetime.now()
        }
        self.collection.update_one(
            {"order_id": order_id},
            {"$set": doc},
            upsert=True
        )
        print(f"💾 Stored processed payment: order={order_id}, user={user_id}, amount={amount}")
    
    def exists(self, order_id):
        return self.collection.find_one({"order_id": order_id}) is not None

processed_payments_store = ProcessedPaymentsStore()

class PaymentOrdersStore:
    def __init__(self):
        self.collection = mongo.get_collection('payment_orders')
    
    def create(self, order_id, user_id, amount, product_name=None, plan=None):
        doc = {
            "order_id": order_id,
            "user_id": str(user_id),
            "amount": float(amount),
            "product_name": product_name,
            "plan": plan,
            "created_at": datetime.now(),
            "status": "pending"
        }
        self.collection.update_one(
            {"order_id": order_id},
            {"$set": doc},
            upsert=True
        )
        print(f"📝 STORED: order={order_id} -> user={user_id}")
        return doc
    
    def get_user_by_order(self, order_id):
        doc = self.collection.find_one({"order_id": order_id})
        return doc.get("user_id") if doc else None
    
    def get_order(self, order_id):
        return self.collection.find_one({"order_id": order_id})
    
    def mark_verified(self, order_id):
        self.collection.update_one(
            {"order_id": order_id},
            {"$set": {"status": "verified", "verified_at": datetime.now()}}
        )
    
    def delete(self, order_id):
        self.collection.delete_one({"order_id": order_id})
        print(f"🗑️ Deleted order mapping for {order_id}")

payment_orders_store = PaymentOrdersStore()

def get_user_data(user_id, key, default=None):
    return user_data_store.get(user_id, key, default)

def set_user_data(user_id, key, value):
    user_data_store.set(user_id, key, value)

user_data = {}
pending_commands = {}
pending_payments = {}

def load_initial_data():
    global pending_commands, pending_payments
    for doc in pending_commands_store.collection.find():
        pending_commands[doc["user_id"]] = doc["command"]
    for doc in pending_payments_store.collection.find():
        pending_payments[doc["user_id"]] = doc["data"]

load_initial_data()

def send_message(chat_id, text, parse_mode="HTML", reply_markup=None, disable_web_page_preview=True):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": disable_web_page_preview}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(url, json=payload).json()
    except Exception as e:
        print(f"Send error: {e}")
        return None

def send_photo(chat_id, photo, caption=None, parse_mode="HTML", reply_markup=None):
    url = f"{BASE_URL}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo, "parse_mode": parse_mode}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(url, json=payload).json()
    except:
        return None

def edit_message(chat_id, message_id, text, parse_mode="HTML", reply_markup=None):
    url = f"{BASE_URL}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(url, json=payload).json()
    except Exception as e:
        print(f"Edit error: {e}")
        return None

def delete_message(chat_id, message_id):
    url = f"{BASE_URL}/deleteMessage"
    try:
        return requests.post(url, json={"chat_id": chat_id, "message_id": message_id}).json()
    except:
        return None

def answer_callback(callback_id, text=None, show_alert=False):
    url = f"{BASE_URL}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = show_alert
    try:
        return requests.post(url, json=payload).json()
    except:
        return None

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    try:
        response = requests.get(url, params={"offset": offset} if offset else {})
        return response.json().get("result", [])
    except:
        return []

def forward_message(chat_id, from_chat_id, message_id):
    url = f"{BASE_URL}/forwardMessage"
    payload = {"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
    try:
        return requests.post(url, json=payload).json()
    except Exception as e:
        print(f"Forward error: {e}")
        return None

class User:
    @staticmethod
    def get_data(user_id, key):
        return get_user_data(user_id, key)
    
    @staticmethod
    def save_data(user_id, key, value):
        set_user_data(user_id, key, value)
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id][key] = value

class Resources:
    @staticmethod
    def another_res(resource_type, user=None):
        class Resource:
            def __init__(self, res_type, user_id):
                self.res_type = res_type
                self.user_id = user_id
                self.store_key = f"{res_type}_{user_id}"
            
            def value(self):
                return bot_data.get(self.store_key, 0)
            
            def add(self, amount):
                current = self.value()
                bot_data.set(self.store_key, current + amount)
                return self
            
            def cut(self, amount):
                current = self.value()
                bot_data.set(self.store_key, max(0, current - amount))
                return self
        return Resource(resource_type, user)

def get_easy_time():
    current = datetime.now()
    date = current.strftime("%Y-%m-%d")
    time_str = current.strftime("%H:%M")
    year, month, day = date.split("-")
    hour, minute = time_str.split(":")
    hour = int(hour)
    ampm = "am"
    if hour >= 12:
        ampm = "pm"
    if hour > 12:
        hour -= 12
    if hour == 0:
        hour = 12
    MONTHS = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun", "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
    return f"{int(day)} {MONTHS[month]}, {hour:02}:{minute} {ampm}"

commands = {}

def command(name):
    def decorator(func):
        commands[name] = func
        return func
    return decorator

PLAN_NAMES = {
    "1": "1 Day",
    "2": "3 Days",
    "3": "7 Days",
    "4": "15 Days",
    "5": "30 Days",
    "6": "1 Day",
    "7": "3 Days",
    "8": "7 Days",
    "9": "14 Days",
    "10": "1 Day",
    "11": "3 Days",
    "12": "7 Days",
    "13": "14 Days",
    "14": "21 Days",
    "15": "28 Days",
}

# ========== CHECK MAINTENANCE MODE ==========
def check_maintenance(user_id, message):
    maintenance_mode = bot_data.get_data("maintenance_mode") or False
    if maintenance_mode:
        admins = bot_data.get_data("AllBotAdminss") or []
        is_admin = str(user_id) in [str(a) for a in admins]
        if not is_admin:
            text = (
                f"{emoji_tag(EMOJIS['warning'], '⚠️')} MAINTENANCE MODE ACTIVE {emoji_tag(EMOJIS['danger'], '🔴')}\n\n"
                f"{emoji_tag(EMOJIS['info'], 'ℹ️')} The bot is currently undergoing server upgrades.\n"
                f"{emoji_tag(EMOJIS['lightbulb'], '💡')} Purchases, balance operations, and other services may be temporarily unavailable.\n"
                f"{emoji_tag(EMOJIS['clock'], '⏳')} Please check back later."
            )
            send_message(user_id, text, "HTML")
            return True
    return False

# ============================================================
# ========== USER COMMANDS ==========
# ============================================================

@command("/start")
@command("/Start")
@command("/START")
def cmd_start(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    if not User.get_data(user_id, "joined_date"):
        User.save_data(user_id, "joined_date", message.get("date"))
    balance = Resources.another_res("Balance", user=user_id).value()
    text = (
        f"{emoji_tag(EMOJIS['shop'], '🛒')} <b>Buy Hack :</b> All key purchase & instantly delivery\n"
        f"{emoji_tag(EMOJIS['user'], '👤')} <b>Profile :</b> Check your account information\n"
        f"{emoji_tag(EMOJIS['money'], '💰')} <b>Add Fund :</b> Deposit balance & secure service\n"
        f"{emoji_tag(EMOJIS['mykeys'], '📦')} <b>My Key :</b> Check all key purchase history\n"
        f"{emoji_tag(EMOJIS['video'], '🎥')} <b>How To Use :</b> View tutorial and work this bot\n"
        f"{emoji_tag(EMOJIS['support'], '💬')} <b>Support :</b> Bot problem fixed for support admin\n"
        f"{emoji_tag(EMOJIS['download'], '📥')} <b>Download Apk :</b> Download latest apk for safety\n"
        f"{emoji_tag(EMOJIS['balance'], '💰')} Your Balance: ₹{balance}"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "BUY HACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": EMOJIS['shop'], "style": "success"}],
            [
                {"text": "MY KEY", "callback_data": "/orderksk", "icon_custom_emoji_id": EMOJIS['key'], "style": "success"},
                {"text": "PROFILE", "callback_data": "/profilemmm", "icon_custom_emoji_id": EMOJIS['profile'], "style": "success"}
            ],
            [
                {"text": "HOW TO USE", "callback_data": "/spinj", "icon_custom_emoji_id": EMOJIS['howto'], "style": "success"},
                {"text": "SUPPORT", "callback_data": "/supportj", "icon_custom_emoji_id": EMOJIS['support'], "style": "success"}
            ],
            [{"text": "ADD FUND", "callback_data": "/addpayment", "icon_custom_emoji_id": EMOJIS['addfund'], "style": "success"}],
            [
                {"text": "PAY PROOF", "url": "https://t.me/subhajit_feedback", "icon_custom_emoji_id": EMOJIS['payproof'], "style": "success"},
                {"text": "DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl", "icon_custom_emoji_id": EMOJIS['download'], "style": "success"}
            ]
        ]
    }
    send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/shopnawkk")
def cmd_shopnawkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    
    mods = bot_data.get_data("mods_list") or []
    default_mods = ["drip", "SILENT", "HG"]
    
    for dm in default_mods:
        if dm not in mods:
            mods.append(dm)
    bot_data.save_data("mods_list", mods)
    
    markup = {"inline_keyboard": []}
    
    for mod_id in mods:
        display_name = mod_id.upper()
        emoji_id = EMOJIS['package']
        if mod_id == "drip":
            display_name = "DRIP CLIENT NON-ROOT"
            emoji_id = EMOJIS['drip_emoji']
        elif mod_id == "SILENT":
            display_name = "SILENT CHEATS ANDROID"
            emoji_id = EMOJIS['silent_emoji']
        elif mod_id == "HG":
            display_name = "PRIME HOOK"
            emoji_id = EMOJIS['hg_emoji']
        else:
            display_name = bot_data.get_data(f"{mod_id}_display_name") or mod_id.replace("_", " ").title()
            custom_emoji = bot_data.get_data(f"{mod_id}_emoji")
            if custom_emoji:
                emoji_id = custom_emoji
        
        has_plan = False
        all_keys = bot_data.collection.find()
        for doc in all_keys:
            key = doc.get("key", "")
            if key.startswith(mod_id + "_") and "d_price" in key:
                has_plan = True
                break
        
        if has_plan:
            markup["inline_keyboard"].append([
                {"text": f"📦 {display_name}", "callback_data": f"/SHOP_MOD {mod_id}", "icon_custom_emoji_id": emoji_id, "style": "success"}
            ])
    
    if not markup["inline_keyboard"]:
        markup["inline_keyboard"].append([
            {"text": "No Products Available", "callback_data": "/backkkk", "style": "danger"}
        ])
    
    markup["inline_keyboard"].append([
        {"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": EMOJIS['back'], "style": "danger"}
    ])
    
    text = f"""
━━━━━━━━━━━━━━━━━━━━
{emoji_tag(EMOJIS['shop'], '🛒')} <b>PANNEL STORE — SHOP</b>
━━━━━━━━━━━━━━━━━━━━

{emoji_tag(EMOJIS['package'], '📦')} Choose a product:
"""
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

# ========== FIXED SHOP_MOD ==========
@command("/SHOP_MOD")
def cmd_shop_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    
    mod_id = params
    if not mod_id:
        send_message(user_id, "Invalid Product")
        return True
    
    User.save_data(user_id, "current_mod", mod_id)
    
    all_keys = bot_data.collection.find()
    plans = []
    plan_names = bot_data.get_data("plan_names") or {}
    
    for doc in all_keys:
        key = doc.get("key", "")
        if key.startswith(mod_id + "_") and "d_price" in key:
            try:
                parts = key.split("_")
                for part in parts:
                    if "d" in part and part.replace("d", "").isdigit():
                        day = int(part.replace("d", ""))
                        plans.append(day)
                        break
            except:
                pass
    
    plans = sorted(list(set(plans)))
    
    if not plans:
        send_message(user_id, "❌ No plans available for this product")
        return True
    
    resellers = bot_data.get_data("resellers_list") or []
    is_reseller = str(user_id) in [str(u) for u in resellers]
    
    markup = {"inline_keyboard": []}
    
    for day in plans:
        price_key = f"{mod_id}_{day}d_price"
        if is_reseller:
            reseller_key = f"{mod_id}_{day}d_reseller_price"
            price = bot_data.get_data(reseller_key) or bot_data.get_data(price_key) or 0
        else:
            price = bot_data.get_data(price_key) or 0
        
        if price and price > 0:
            plan_key = f"{mod_id}_{day}"
            plan_display = plan_names.get(plan_key, f"{day} Day{'s' if day > 1 else ''}")
            markup["inline_keyboard"].append([
                {"text": f"{plan_display} - ₹{price} {emoji_tag(EMOJIS['cart'], '🛒')}", 
                 "callback_data": f"/buy_mod {mod_id}_{day}", 
                 "style": "success"}
            ])
    
    if not markup["inline_keyboard"]:
        send_message(user_id, "❌ No valid plans available")
        return True
    
    markup["inline_keyboard"].append([
        {"text": "BACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": EMOJIS['back'], "style": "danger"}
    ])
    
    display_name = mod_id.upper()
    if mod_id == "drip":
        display_name = "DRIP CLIENT NON-ROOT"
    elif mod_id == "SILENT":
        display_name = "SILENT CHEATS ANDROID"
    elif mod_id == "HG":
        display_name = "PRIME HOOK"
    else:
        display_name = bot_data.get_data(f"{mod_id}_display_name") or mod_id.replace("_", " ").title()
    
    txt = f"""
━━━━━━━━━━━━━━━━━━━━
📦 {display_name}
━━━━━━━━━━━━━━━━━━━━

Choose a plan 👇
"""
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

# ========== FIXED BUY_MOD ==========
@command("/buy_mod")
def cmd_buy_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    if not params:
        send_message(user_id, "❌ Invalid Product")
        return True
    
    # FIXED: Better parsing for mod_id with underscores
    parts = params.split("_")
    if len(parts) < 2:
        send_message(user_id, "❌ Invalid Product Format")
        return True
    
    # Last part is day
    day_str = parts[-1]
    try:
        day = int(day_str)
    except:
        send_message(user_id, "❌ Invalid Day")
        return True
    
    # Rest is mod_id (join back with underscores)
    mod_id = "_".join(parts[:-1])
    
    price_key = f"{mod_id}_{day}d_price"
    keys_key = f"{mod_id}_{day}d_keys"
    
    price = bot_data.get_data(price_key)
    if not price or price <= 0:
        send_message(user_id, f"❌ Product not available\n\nMod: {mod_id}\nDay: {day}")
        return True
    
    keys = bot_data.get_data(keys_key) or []
    if len(keys) == 0:
        send_message(user_id, "❌ Out of Stock")
        return True
    
    resellers = bot_data.get_data("resellers_list") or []
    is_reseller = str(user_id) in [str(u) for u in resellers]
    if is_reseller:
        reseller_key = f"{mod_id}_{day}d_reseller_price"
        if bot_data.get_data(reseller_key):
            price = bot_data.get_data(reseller_key)
    
    display_name = mod_id.upper()
    if mod_id == "drip":
        display_name = "DRIP CLIENT NON-ROOT"
    elif mod_id == "SILENT":
        display_name = "SILENT CHEATS ANDROID"
    elif mod_id == "HG":
        display_name = "PRIME HOOK"
    else:
        display_name = bot_data.get_data(f"{mod_id}_display_name") or mod_id.replace("_", " ").title()
    
    plan_names = bot_data.get_data("plan_names") or {}
    plan_key = f"{mod_id}_{day}"
    plan_display = plan_names.get(plan_key, f"{day} Day{'s' if day > 1 else ''}")
    
    title = f"{display_name}\n{plan_display}"
    
    User.save_data(user_id, "last_product1", title)
    User.save_data(user_id, "last_plan", str(day))
    
    cmd_buybahha(message, None, {"price": price, "key": keys_key, "title": title})
    return True

@command("/buybahha")
def cmd_buybahha(message, params, options):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    if not options:
        send_message(user_id, "Product configuration error.")
        return True
    price = options.get("price")
    key_key = options.get("key")
    title = options.get("title")
    if not price or not key_key or not title:
        send_message(user_id, "Product configuration error.")
        return True
    try:
        price = float(price)
    except:
        send_message(user_id, "Invalid price.")
        return True
    if price <= 0:
        send_message(user_id, "Price not set.")
        return True
    keys = bot_data.get_data(key_key) or []
    if len(keys) == 0:
        send_message(user_id, "Out of Stock.")
        return True
    balance = Resources.another_res("Balance", user=user_id)
    if balance.value() < price:
        User.save_data(user_id, "last_deposit_amount", price)
        User.save_data(user_id, "last_product", title)
        cmd_autobuy1(message, None)
        return True
    balance.cut(price)
    Resources.another_res("Order", user=user_id).add(1)
    key = str(keys[0])
    keys.pop(0)
    bot_data.save_data(key_key, keys)
    easy_time = get_easy_time()
    send_message(
        user_id,
        f"{emoji_tag(EMOJIS['buy'], '🛒')} {title}\n\n"
        f"{emoji_tag(EMOJIS['key'], '🔑')} <b>Your Key:</b>\n<code>{key}</code>\n\n"
        f"{emoji_tag(EMOJIS['money'], '💰')} Deducted: ₹{price}\n"
        f"{emoji_tag(EMOJIS['mykeys'], '📦')} Remaining Stock: {len(keys)}\n"
        f"{emoji_tag(EMOJIS['time'], '⏰')} Time: {easy_time}\n\n"
        f"{emoji_tag(EMOJIS['announce'], '📢')} <b>ALL FILES UPDATE</b>\n"
        f"@SUBHAJIT_UPDATES",
        "HTML"
    )
    adm_ac = User.get_data(user_id, "userhAC") or []
    adm_ac.append(
        f"📆 {easy_time}\n"
        f"👤 {message.get('from', {}).get('first_name', 'User')} [{user_id}]\n"
        f"💰 ₹{price}\n"
        f"🔑 {key}\n"
    )
    User.save_data(user_id, "userhAC", adm_ac)
    return True

@command("/autobuy1")
def cmd_autobuy1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    amount = User.get_data(user_id, "last_deposit_amount")
    pt = User.get_data(user_id, "last_product1") or "Unknown"
    plan = User.get_data(user_id, "last_plan") or "Unknown"
    if not amount:
        send_message(user_id, "Amount missing")
        return True
    balance = Resources.another_res("Balance", user=user_id).value()
    need = float(amount) - float(balance)
    if need < 0:
        need = 0
    plan_display = PLAN_NAMES.get(str(plan), plan)
    upi = "bablu.xyztb@fam"
    url = f"https://fampay.anujbots.xyz/qr.php?upi={upi}&amount={amount}"
    try:
        response = requests.get(url)
        data = response.json()
    except:
        send_message(user_id, "API ERROR")
        return True
    if not data or data.get("status") != "success":
        send_message(user_id, "QR GENERATION FAILED")
        return True
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    payment_orders_store.create(
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        product_name=pt,
        plan=plan_display
    )
    print(f"✅ STORED: Order {order_id} -> User {user_id}")
    
    User.save_data(user_id, "last_order_id", order_id)
    User.save_data(user_id, "payment_processed", False)
    pending_payments[user_id] = {
        "order_id": order_id,
        "msg_id": message.get("message_id"),
        "user_id": str(user_id)
    }
    pending_payments_store.set(user_id, pending_payments[user_id])
    
    caption = (
        f"{emoji_tag(EMOJIS['money'], '💰')} INSUFFICIENT BALANCE\n\n"
        f"┣ Product: {pt}\n"
        f"┣ Plan: {plan_display}\n"
        f"┣ Price: ₹{amount}\n"
        f"┣ Your Balance: ₹{balance}\n"
        f"┗ Need: ₹{need}\n\n"
        f"Scan the QR and complete payment.\n\n"
        f"{emoji_tag(EMOJIS['info'], 'ℹ️')} <b>Order ID:</b>\n"
        f"<code>{order_id}</code>\n\n"
        f"<i>After payment, tap VERIFY PAYMENT button below.</i>"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ VERIFY PAYMENT", "callback_data": f"/verify_payment {order_id}", "icon_custom_emoji_id": EMOJIS['addfund'], "style": "success"}],
            [{"text": "❌ CANCEL", "callback_data": f"/cancel {order_id}", "icon_custom_emoji_id": EMOJIS['danger'], "style": "danger"}]
        ]
    }
    send_photo(user_id, qr_url, caption, "HTML", reply_markup)
    return True

@command("/verify_payment")
def cmd_verify_payment(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    
    order_id = params
    
    if not order_id:
        send_message(user_id, "No order ID found.", "HTML")
        return True
    
    print(f"🔍 User {user_id} verifying order {order_id}")
    
    order_data = payment_orders_store.get_order(order_id)
    if not order_data:
        send_message(user_id, "❌ Invalid Order ID. Please generate QR again.", "HTML")
        return True
    
    order_owner = order_data.get("user_id")
    if str(order_owner) != str(user_id):
        send_message(
            user_id,
            f"❌ <b>SECURITY ERROR!</b>\n\n"
            f"This order <code>{order_id}</code> belongs to user: <code>{order_owner}</code>\n"
            f"You are: <code>{user_id}</code>\n\n"
            f"<b>You cannot verify someone else's payment!</b>",
            "HTML"
        )
        return True
    
    if order_data.get("status") == "verified":
        send_message(user_id, "✅ This payment has already been processed.", "HTML")
        pending_payments.pop(user_id, None)
        pending_payments_store.delete(user_id)
        return True
    
    pending = pending_payments_store.get(user_id)
    if not pending:
        send_message(user_id, "No pending payment found for you.", "HTML")
        return True
    
    send_message(user_id, f"{emoji_tag(EMOJIS['clock'], '⏳')} Checking payment status...", "HTML")
    
    url = f"https://fampay.anujbots.xyz/verify.php?order_id={order_id}&api_key=FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8"
    
    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        send_message(user_id, f"❌ API ERROR: {str(e)}")
        return True
    
    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        
        bal = Resources.another_res("Balance", user=user_id)
        bal.add(amount)
        print(f"✅ Added ₹{amount} to user {user_id}")
        
        payment_orders_store.mark_verified(order_id)
        processed_payments_store.add(order_id, user_id, amount)
        
        User.save_data(user_id, "last_order_id", "")
        User.save_data(user_id, "addpay_order_id", "")
        User.save_data(user_id, "payment_processed", True)
        pending_payments.pop(user_id, None)
        pending_payments_store.delete(user_id)
        
        if msg_id:
            try:
                delete_message(user_id, msg_id)
            except:
                pass
        
        send_message(
            user_id,
            f"{emoji_tag(EMOJIS['success'], '✅')} <b>Payment Success!</b>\n\n"
            f"{emoji_tag(EMOJIS['money'], '💰')} Added: ₹{amount}\n"
            f"{emoji_tag(EMOJIS['balance'], '💰')} New Balance: ₹{bal.value()}",
            "HTML"
        )
        
        admins = bot_data.get_data("AllBotAdminss") or []
        for admin in admins:
            send_message(
                admin,
                f"{emoji_tag(EMOJIS['success'], '✅')} New Payment Received!\n\n"
                f"👤 User ID: <code>{user_id}</code>\n"
                f"💰 Amount: ₹{amount}\n"
                f"🧾 Order ID: <code>{order_id}</code>\n"
                f"💳 User Balance: ₹{bal.value()}",
                "HTML"
            )
        
        return True
    else:
        send_message(
            user_id,
            f"{emoji_tag(EMOJIS['danger'], '❌')} <b>Payment Not Found</b>\n\n"
            f"Order ID: <code>{order_id}</code>\n\n"
            f"Please complete the payment and try again.",
            "HTML"
        )
        return True

@command("/cancel")
def cmd_cancel(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    
    if params:
        order_id = params
    else:
        pending = pending_payments_store.get(user_id)
        if pending:
            order_id = pending.get("order_id") if isinstance(pending, dict) else pending
        else:
            order_id = None
    
    if order_id:
        order_data = payment_orders_store.get_order(order_id)
        if order_data:
            order_owner = order_data.get("user_id")
            if str(order_owner) == str(user_id):
                payment_orders_store.delete(order_id)
            else:
                send_message(user_id, "❌ You cannot cancel someone else's order!", "HTML")
                return True
    
    delete_message(user_id, msg_id)
    pending_payments.pop(user_id, None)
    pending_payments_store.delete(user_id)
    User.save_data(user_id, "last_order_id", "")
    User.save_data(user_id, "addpay_order_id", "")
    User.save_data(user_id, "payment_processed", False)
    send_message(user_id, f"{emoji_tag(EMOJIS['danger'], '❌')} Cancelled", "HTML")
    return True

# ============================================================
# ========== ADD FUNDS COMMANDS ==========
# ============================================================

current_amount = {}

@command("/addpayment")
def cmd_addpayment(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    reply_markup = {
        "inline_keyboard": [
            [{"text": "1", "callback_data": "/num1", "style": "success"}, {"text": "2", "callback_data": "/num2", "style": "success"}, {"text": "3", "callback_data": "/num3", "style": "success"}],
            [{"text": "4", "callback_data": "/num4", "style": "success"}, {"text": "5", "callback_data": "/num5", "style": "success"}, {"text": "6", "callback_data": "/num6", "style": "success"}],
            [{"text": "7", "callback_data": "/num7", "style": "success"}, {"text": "8", "callback_data": "/num8", "style": "success"}, {"text": "9", "callback_data": "/num9", "style": "success"}],
            [{"text": "CLEAR", "callback_data": "/clearamt", "style": "danger"}, {"text": "0", "callback_data": "/num0", "style": "success"}, {"text": "CONFIRM", "callback_data": "/done", "style": "success"}],
            [{"text": "BACK", "callback_data": "/backkkk", "style": "danger"}]
        ]
    }
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹0\n\nUse the keypad below."
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/num0")
def cmd_num0(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "0" if amt == "0" else amt + "0"
    current_amount[user_id] = amt
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num1")
def cmd_num1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "1" if amt == "0" else amt + "1"
    current_amount[user_id] = amt
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num2")
def cmd_num2(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "2" if amt == "0" else amt + "2"
    current_amount[user_id] = amt
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num3")
def cmd_num3(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "3" if amt == "0" else amt + "3"
    current_amount[user_id] = amt
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num4")
def cmd_num4(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "4" if amt == "0" else amt + "4"
    current_amount[user_id] = amt
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num5")
def cmd_num5(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "5" if amt == "0" else amt + "5"
    current_amount[user_id] = amt
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num6")
def cmd_num6(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "6" if amt == "0" else amt + "6"
    current_amount[user_id] = amt
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num7")
def cmd_num7(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "7" if amt == "0" else amt + "7"
    current_amount[user_id] = amt
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num8")
def cmd_num8(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "8" if amt == "0" else amt + "8"
    current_amount[user_id] = amt
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num9")
def cmd_num9(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "9" if amt == "0" else amt + "9"
    current_amount[user_id] = amt
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/clearamt")
def cmd_clearamt(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹0\n\nUse the keypad below."
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/done")
def cmd_done(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    amt = current_amount.get(user_id, "0")
    if not amt or amt == "0":
        send_message(user_id, "Enter amount first")
        return True
    User.save_data(user_id, "last_deposit_amount", float(amt))
    cmd_addpayment_qr(message)
    return True

def cmd_addpayment_qr(message):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return
    amount = User.get_data(user_id, "last_deposit_amount")
    if not amount:
        send_message(user_id, "Amount missing")
        return
    upi = "bablu.xyztb@fam"
    url = f"https://fampay.anujbots.xyz/qr.php?upi={upi}&amount={amount}"
    try:
        response = requests.get(url)
        data = response.json()
    except:
        send_message(user_id, "API ERROR")
        return
    if data.get("status") != "success":
        send_message(user_id, "QR GENERATION FAILED")
        return
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    payment_orders_store.create(
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        product_name="Add Funds"
    )
    
    User.save_data(user_id, "addpay_order_id", order_id)
    User.save_data(user_id, "payment_processed", False)
    pending_payments[user_id] = {
        "order_id": order_id,
        "msg_id": message.get("message_id"),
        "user_id": str(user_id)
    }
    pending_payments_store.set(user_id, pending_payments[user_id])
    
    caption = (
        f"{emoji_tag(EMOJIS['money'], '💰')} PAYMENT QR GENERATED\n"
        f"Scan the QR and complete payment.\n\n"
        f"Amount: ₹{amount}\n\n"
        f"{emoji_tag(EMOJIS['info'], 'ℹ️')} <b>Order ID:</b>\n<code>{order_id}</code>\n\n"
        f"<i>After payment, tap VERIFY PAYMENT button below.</i>"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ VERIFY PAYMENT", "callback_data": f"/verify_payment {order_id}", "style": "success"}],
            [{"text": "❌ CANCEL", "callback_data": f"/cancel {order_id}", "style": "danger"}]
        ]
    }
    send_photo(user_id, qr_url, caption, "HTML", reply_markup)

# ============================================================
# ========== OTHER USER COMMANDS ==========
# ============================================================

@command("/backkkk")
def cmd_backkkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    balance = Resources.another_res("Balance", user=user_id).value()
    text = (
        f"{emoji_tag(EMOJIS['shop'], '🛒')} <b>Buy Hack :</b> All key purchase & instantly delivery\n"
        f"{emoji_tag(EMOJIS['user'], '👤')} <b>Profile :</b> Check your account information\n"
        f"{emoji_tag(EMOJIS['money'], '💰')} <b>Add Fund :</b> Deposit balance & secure service\n"
        f"{emoji_tag(EMOJIS['mykeys'], '📦')} <b>My Key :</b> Check all key purchase history\n"
        f"{emoji_tag(EMOJIS['video'], '🎥')} <b>How To Use :</b> View tutorial and work this bot\n"
        f"{emoji_tag(EMOJIS['support'], '💬')} <b>Support :</b> Bot problem fixed for support admin\n"
        f"{emoji_tag(EMOJIS['download'], '📥')} <b>Download Apk :</b> Download latest apk for safety\n"
        f"{emoji_tag(EMOJIS['balance'], '💰')} Your Balance: ₹{balance}"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "BUY HACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": EMOJIS['shop'], "style": "success"}],
            [
                {"text": "MY KEY", "callback_data": "/orderksk", "icon_custom_emoji_id": EMOJIS['key'], "style": "success"},
                {"text": "PROFILE", "callback_data": "/profilemmm", "icon_custom_emoji_id": EMOJIS['profile'], "style": "success"}
            ],
            [
                {"text": "HOW TO USE", "callback_data": "/spinj", "icon_custom_emoji_id": EMOJIS['howto'], "style": "success"},
                {"text": "SUPPORT", "callback_data": "/supportj", "icon_custom_emoji_id": EMOJIS['support'], "style": "success"}
            ],
            [{"text": "ADD FUND", "callback_data": "/addpayment", "icon_custom_emoji_id": EMOJIS['addfund'], "style": "success"}],
            [
                {"text": "PAY PROOF", "url": "https://t.me/subhajit_feedback", "icon_custom_emoji_id": EMOJIS['payproof'], "style": "success"},
                {"text": "DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl", "icon_custom_emoji_id": EMOJIS['download'], "style": "success"}
            ]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/orderksk")
def cmd_orderksk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    textn = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji_tag(EMOJIS['orders'], '📦')} <b>MY ORDERS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "You haven't placed any orders yet.\n"
        f"Tap {emoji_tag(EMOJIS['shop'], '🛒')} Shop Now!"
    )
    adm_ac = User.get_data(user_id, "userhAC") or []
    if not adm_ac:
        reply_markup = {"inline_keyboard": [[{"text": "BACK", "callback_data": "/backkkk", "style": "danger"}]]}
        try:
            edit_message(user_id, msg_id, textn, "HTML", reply_markup)
        except:
            send_message(user_id, textn, "HTML", reply_markup)
    else:
        latest_10 = adm_ac[-10:][::-1]
        safe_list = [str(item) for item in latest_10 if item]
        if safe_list:
            text = "\n\n".join(safe_list)
            reply_markup = {"inline_keyboard": [[{"text": "BACK", "callback_data": "/backkkk", "style": "danger"}]]}
            try:
                edit_message(user_id, msg_id, text, reply_markup=reply_markup)
            except:
                send_message(user_id, text, reply_markup=reply_markup)
    return True

@command("/profilemmm")
def cmd_profilemmm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    first_name = message.get("from", {}).get("first_name", "User")
    balance = Resources.another_res("Balance", user=user_id).value()
    orders = Resources.another_res("Order", user=user_id).value()
    joined = User.get_data(user_id, "joined_date")
    
    if not joined:
        member_since = "Today"
    else:
        diff = message.get("date", 0) - int(joined)
        if diff < 86400:
            member_since = "Today"
        elif diff < 86400 * 7:
            member_since = str(diff // 86400) + " days ago"
        elif diff < 86400 * 30:
            member_since = str(diff // (86400 * 7)) + " weeks ago"
        else:
            member_since = str(diff // (86400 * 30)) + " months ago"
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji_tag(EMOJIS['user'], '👤')} YOUR PROFILE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Name: {first_name}\n"
        f"🆔 User ID: {user_id}\n"
        f"{emoji_tag(EMOJIS['balance'], '💰')} Balance: ₹{balance}\n"
        f"📅 Member Since: {member_since}\n"
        f"{emoji_tag(EMOJIS['orders'], '📦')} Total Orders: {orders}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": "BUY HACK", "callback_data": "/shopnawkk", "style": "success"}, {"text": "MY KEYS", "callback_data": "/orderksk", "style": "success"}],
            [{"text": "BACK", "callback_data": "/backkkk", "style": "danger"}]
        ]
    }
    
    try:
        if msg_id:
            delete_message(user_id, msg_id)
    except:
        pass
    
    send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/spinj")
def cmd_spinj(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    text = f"""
{emoji_tag(EMOJIS['video'], '🎥')} <b>Watch the full tutorial video below</b>

👇
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": "Watch Tutorial", "url": "https://t.me/hehehehhhsljg/162", "style": "success"}],
            [{"text": "BACK", "callback_data": "/backkkk", "style": "danger"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/supportj")
def cmd_supportj(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if check_maintenance(user_id, message):
        return True
    msg_id = message.get("message_id")
    text = """
━━━━━━━━━━━━━━━━━━━━
💬 <b>Support — Seller</b> 🛡
━━━━━━━━━━━━━━━━━━━━

Need help? We're here for you! ⚡

📩 <b>Telegram:</b> ⭐

<a href="https://t.me/UR_SUBHAJIT0">𝐒υвʜᴀᎫιт</a> ⭐

💡 <i>Include your User ID when contacting.</i>
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": "WHATSAPP", "url": "https://wa.me/917908696630", "style": "success"}],
            [{"text": "BACK", "callback_data": "/backkkk", "style": "danger"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

# ============================================================
# ========== ADMIN COMMANDS ==========
# ============================================================

@command("/admin")
def cmd_admin(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if not admins:
        admins = [str(user_id)]
        bot_data.save_data("AllBotAdminss", admins)
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    
    maintenance_mode = bot_data.get_data("maintenance_mode") or False
    maint_status = "🔴 OFF"
    maint_callback = "/maintenance_on"
    if maintenance_mode:
        maint_status = "🟢 ON"
        maint_callback = "/maintenance_off"
    
    bot_mode = bot_data.get_data("BotMode") or "ON"
    bot_sta = "🟢 On"
    bot_change = "BotMode OFF"
    if bot_mode == "OFF":
        bot_sta = "🔴 Off"
        bot_change = "BotMode ON"
    
    markup = {
        "inline_keyboard": [
            [{"text": "👑 Admins", "callback_data": "/TUSHAR_Admins", "style": "success"}],
            [{"text": "📣 Broadcast", "callback_data": "/broadcast", "style": "success"}, {"text": f"🤖 Bot: {bot_sta}", "callback_data": f"/admin {bot_change}", "style": "success"}],
            [{"text": "💰 Add Balance", "callback_data": "/ChangeAnyUserBal", "style": "success"}, {"text": "📝 Recent Admin Actions", "callback_data": "/TUSHAR_AdminAction", "style": "success"}],
            [{"text": "📦 Manage Mods", "callback_data": "/manage_mods", "style": "success"}],
            [{"text": "🔧 Maintenance", "callback_data": maint_callback, "style": "danger"}, {"text": f"Status: {maint_status}", "callback_data": "none", "style": "primary"}],
            [{"text": "💰 Add Reseller", "callback_data": "/addreseller", "style": "success"}, {"text": "⛔ Remove Reseller", "callback_data": "/removereseller", "style": "danger"}],
            [{"text": "📝 Reseller List", "callback_data": "/resellerlist", "style": "success"}]
        ]
    }
    txt = f"""<b>
👋 Welcome {message.get('from', {}).get('first_name', 'Admin')} 🎉

━━━━━━━━━━━━━━━
🤖 Bot Status : {bot_sta}
🔧 Maintenance : {maint_status}
━━━━━━━━━━━━━━━
</b>"""
    if str(message.get("text")) == "/admin":
        send_message(user_id, txt, "HTML", markup)
    else:
        try:
            edit_message(user_id, msg_id, txt, "HTML", markup)
        except:
            send_message(user_id, txt, "HTML", markup)
    return True

# ============================================================
# ========== MAINTENANCE COMMANDS ==========
# ============================================================

@command("/maintenance_on")
def cmd_maintenance_on(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    
    bot_data.save_data("maintenance_mode", True)
    send_message(user_id, "✅ Maintenance Mode Activated!", "HTML")
    
    cmd_admin(message, params, options)
    return True

@command("/maintenance_off")
def cmd_maintenance_off(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    
    bot_data.save_data("maintenance_mode", False)
    send_message(user_id, "✅ Maintenance Mode Deactivated!", "HTML")
    
    cmd_admin(message, params, options)
    return True

@command("/TUSHAR_Admins")
def cmd_tushar_admins(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    if params and params in admins:
        admins.remove(params)
        bot_data.save_data("AllBotAdminss", admins)
    markup = {"inline_keyboard": []}
    for admin in admins:
        markup["inline_keyboard"].append([
            {"text": admin, "callback_data": f"/TUSHAR_Admins {admin}", "style": "success"},
            {"text": "❌", "callback_data": f"/TUSHAR_Admins {admin}", "style": "danger"}
        ])
    markup["inline_keyboard"].append([{"text": "➕ Add Admin", "callback_data": "/TUSHAR_AddAdmin", "style": "success"}])
    markup["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "/admin", "style": "danger"}])
    text = "<b>Here You Can Manage Your Admins</b>"
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

@command("/TUSHAR_AddAdmin")
def cmd_tushar_addadmin(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    send_message(user_id, "<b>Send UserID of Admin You Want To Add</b>", "HTML")
    pending_commands[user_id] = "/TUSHAR_AddAdmin1"
    pending_commands_store.set(user_id, "/TUSHAR_AddAdmin1")
    return True

@command("/TUSHAR_AddAdmin1")
def cmd_tushar_addadmin1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    new_admin = message.get("text")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    if new_admin in admins:
        send_message(user_id, "Admin Already Exists")
    else:
        admins.append(new_admin)
        bot_data.save_data("AllBotAdminss", admins)
        send_message(user_id, f"✅ Admin <code>{new_admin}</code> Added Successfully", "HTML")
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/TUSHAR_AdminAction")
def cmd_tushar_adminaction(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    adm_ac = bot_data.get_data("AdmAC") or []
    latest_10 = adm_ac[-10:][::-1]
    if latest_10:
        send_message(user_id, "\n\n".join(latest_10), "HTML")
    else:
        send_message(user_id, "No admin actions recorded yet.")
    return True

@command("/ChangeAnyUserBal")
def cmd_change_balance(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    send_message(
        user_id,
        f"<b>💡 Send User Telegram Id & Amount\n\n⚠️ Use Format: <code>{user_id} 10</code>\n\nAdd - Before Amount To Deduct Balance Like -10</b>",
        "HTML"
    )
    pending_commands[user_id] = "/ChangeAnyUserBal2"
    pending_commands_store.set(user_id, "/ChangeAnyUserBal2")
    return True

@command("/ChangeAnyUserBal2")
def cmd_change_balance2(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    parts = text.split(" ")
    if len(parts) < 2:
        send_message(user_id, "Invalid format. Use: user_id amount")
        return True
    target_user = parts[0]
    try:
        amount = float(parts[1])
    except:
        send_message(user_id, "Invalid amount")
        return True
    bal = Resources.another_res("Balance", user=target_user)
    bal.add(amount)
    easy_time = get_easy_time()
    adm_ac = bot_data.get_data("AdmAC") or []
    adm_ac.append(
        f"📆 Time: {easy_time}\n"
        f"👥 By {message.get('from', {}).get('first_name', 'Admin')} [ID: {user_id}]\n"
        f"🔍 Action: Added {amount} Rs To {target_user}"
    )
    bot_data.save_data("AdmAC", adm_ac)
    send_message(
        user_id,
        f"<b>💰 Account Of <a href='tg://user?id={target_user}'>{target_user}</a> Was Increased By {amount}\n\nFinal Balance = {bal.value()}</b>",
        "HTML"
    )
    send_message(
        target_user,
        f"<b>💰 Admin Gave You A Increase In Balance By {amount}</b>",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

# ============================================================
# ========== MANAGE MODS ==========
# ============================================================

@command("/manage_mods")
def cmd_manage_mods(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    mods = bot_data.get_data("mods_list") or []
    default_mods = ["drip", "SILENT", "HG"]
    
    for dm in default_mods:
        if dm not in mods:
            mods.append(dm)
    bot_data.save_data("mods_list", mods)
    
    markup = {"inline_keyboard": []}
    
    for mod in mods:
        display_name = mod.upper()
        if mod == "drip":
            display_name = "DRIP CLIENT"
        elif mod == "SILENT":
            display_name = "SILENT CHEATS"
        elif mod == "HG":
            display_name = "PRIME HOOK"
        else:
            display_name = bot_data.get_data(f"{mod}_display_name") or mod.replace("_", " ").title()
        
        if mod in default_mods:
            markup["inline_keyboard"].append([
                {"text": f"📦 {display_name}", "callback_data": f"/manage_mod {mod}", "style": "success"}
            ])
        else:
            markup["inline_keyboard"].append([
                {"text": f"📦 {display_name}", "callback_data": f"/manage_mod {mod}", "style": "success"},
                {"text": "🗑️", "callback_data": f"/delete_mod {mod}", "style": "danger"}
            ])
    
    markup["inline_keyboard"].append([
        {"text": "➕ ADD NEW MOD", "callback_data": "/add_new_mod", "style": "success"}
    ])
    markup["inline_keyboard"].append([
        {"text": "🔙 BACK", "callback_data": "/admin", "style": "danger"}
    ])
    
    txt = """
<b>📦 MANAGE MODS</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Select a mod to manage or add new:</b>
"""
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/manage_mod")
def cmd_manage_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    mod_id = params
    if not mod_id:
        send_message(user_id, "❌ Invalid Mod")
        return True
    
    User.save_data(user_id, "current_mod", mod_id)
    
    all_keys = bot_data.collection.find()
    plans = []
    for doc in all_keys:
        key = doc.get("key", "")
        if key.startswith(mod_id + "_") and "d_price" in key:
            try:
                parts = key.split("_")
                for part in parts:
                    if "d" in part and part.replace("d", "").isdigit():
                        day = int(part.replace("d", ""))
                        plans.append(day)
                        break
            except:
                pass
    
    plans = sorted(list(set(plans)))
    
    display_name = mod_id.upper()
    if mod_id == "drip":
        display_name = "DRIP CLIENT"
    elif mod_id == "SILENT":
        display_name = "SILENT CHEATS"
    elif mod_id == "HG":
        display_name = "PRIME HOOK"
    else:
        display_name = bot_data.get_data(f"{mod_id}_display_name") or mod_id.replace("_", " ").title()
    
    markup = {"inline_keyboard": []}
    plan_names = bot_data.get_data("plan_names") or {}
    
    for day in plans:
        price_key = f"{mod_id}_{day}d_price"
        reseller_key = f"{mod_id}_{day}d_reseller_price"
        keys_key = f"{mod_id}_{day}d_keys"
        price = bot_data.get_data(price_key) or 0
        reseller = bot_data.get_data(reseller_key) or 0
        stock = len(bot_data.get_data(keys_key) or [])
        plan_key = f"{mod_id}_{day}"
        plan_display = plan_names.get(plan_key, f"{day} Day{'s' if day > 1 else ''}")
        markup["inline_keyboard"].append([
            {"text": f"📅 {plan_display} - ₹{price} | R: ₹{reseller} | 🔑{stock}", "callback_data": f"/edit_plan {mod_id}_{day}", "style": "primary"}
        ])
    
    markup["inline_keyboard"].append([
        {"text": "➕ ADD NEW PLAN", "callback_data": f"/add_new_plan {mod_id}", "style": "success"}
    ])
    
    if mod_id not in ["drip", "SILENT", "HG"]:
        markup["inline_keyboard"].append([
            {"text": "✏️ CHANGE MOD NAME", "callback_data": f"/rename_mod {mod_id}", "style": "success"}
        ])
        markup["inline_keyboard"].append([
            {"text": "🎨 CHANGE MOD EMOJI", "callback_data": f"/change_mod_emoji {mod_id}", "style": "success"}
        ])
    
    markup["inline_keyboard"].append([
        {"text": "🔙 BACK", "callback_data": "/manage_mods", "style": "danger"}
    ])
    
    txt = f"""
<b>📦 Managing: {display_name}</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Total Plans: {len(plans)}</b>

<b>Select a plan to edit:</b>
"""
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/change_mod_emoji")
def cmd_change_mod_emoji(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    mod_id = params
    if not mod_id:
        send_message(user_id, "❌ Invalid Mod")
        return True
    
    User.save_data(user_id, "change_emoji_mod", mod_id)
    
    current_emoji = bot_data.get_data(f"{mod_id}_emoji") or "None"
    
    send_message(
        user_id,
        f"<b>🎨 Change Emoji For {mod_id.upper()}</b>\n\n"
        f"Current Emoji ID: <code>{current_emoji}</code>\n\n"
        f"Send new emoji ID.\n"
        f"Example: <code>6323104647636589287</code>\n\n"
        f"Type /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/change_mod_emoji_process"
    pending_commands_store.set(user_id, "/change_mod_emoji_process")
    return True

@command("/change_mod_emoji_process")
def cmd_change_mod_emoji_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    mod_id = User.get_data(user_id, "change_emoji_mod")
    if not mod_id:
        send_message(user_id, "❌ Error", "HTML")
        return True
    
    emoji_id = text.strip()
    if not emoji_id or not emoji_id.isdigit():
        send_message(user_id, "❌ Invalid Emoji ID! Send only numbers.", "HTML")
        return True
    
    bot_data.save_data(f"{mod_id}_emoji", emoji_id)
    
    send_message(
        user_id,
        f"✅ <b>Emoji Updated!</b>\n\n"
        f"{mod_id.upper()} → Emoji ID: <code>{emoji_id}</code>",
        "HTML"
    )
    
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "change_emoji_mod", None)
    return True

@command("/edit_plan")
def cmd_edit_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "❌ Invalid")
        return True
    
    parts = params.split("_")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid")
        return True
    
    mod_id = parts[0]
    try:
        day = int(parts[1])
    except:
        send_message(user_id, "❌ Invalid")
        return True
    
    User.save_data(user_id, "editing_plan", f"{mod_id}_{day}")
    
    price_key = f"{mod_id}_{day}d_price"
    reseller_key = f"{mod_id}_{day}d_reseller_price"
    keys_key = f"{mod_id}_{day}d_keys"
    
    current_price = bot_data.get_data(price_key) or 0
    current_reseller = bot_data.get_data(reseller_key) or 0
    current_stock = len(bot_data.get_data(keys_key) or [])
    
    plan_names = bot_data.get_data("plan_names") or {}
    plan_key = f"{mod_id}_{day}"
    current_plan_name = plan_names.get(plan_key, f"{day} Day{'s' if day > 1 else ''}")
    
    markup = {
        "inline_keyboard": [
            [{"text": "💰 Edit Price", "callback_data": f"/edit_price {mod_id}_{day}", "style": "success"}],
            [{"text": "💰 Edit Reseller Price", "callback_data": f"/edit_reseller_price {mod_id}_{day}", "style": "success"}],
            [{"text": "🔑 Add Keys", "callback_data": f"/add_keys_plan {mod_id}_{day}", "style": "success"}],
            [{"text": "🗑️ Remove This Plan", "callback_data": f"/remove_plan {mod_id}_{day}", "style": "danger"}],
            [{"text": "✏️ Edit Plan Name", "callback_data": f"/edit_plan_name {mod_id}_{day}", "style": "success"}],
            [{"text": "🔙 Back", "callback_data": f"/manage_mod {mod_id}", "style": "danger"}]
        ]
    }
    
    txt = f"""
<b>📅 Editing Plan: {mod_id.upper()} - {current_plan_name}</b>
━━━━━━━━━━━━━━━━━━━━━━

💰 Current Price: ₹{current_price}
💰 Current Reseller: ₹{current_reseller}
🔑 Keys Stock: {current_stock}

━━━━━━━━━━━━━━━━━━━━━━
<b>Select what to edit:</b>
"""
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/edit_plan_name")
def cmd_edit_plan_name(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "❌ Invalid")
        return True
    
    parts = params.split("_")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid")
        return True
    
    mod_id = parts[0]
    day = parts[1]
    
    User.save_data(user_id, "editing_plan_name", f"{mod_id}_{day}")
    
    plan_names = bot_data.get_data("plan_names") or {}
    plan_key = f"{mod_id}_{day}"
    current_name = plan_names.get(plan_key, f"{day} Day{'s' if int(day) > 1 else ''}")
    
    send_message(
        user_id,
        f"<b>✏️ Enter New Name For {mod_id.upper()} Plan</b>\n\n"
        f"Current: {current_name}\n\n"
        f"Example: <code>1 Week</code> or <code>Monthly</code>\n\n"
        f"Type /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/edit_plan_name_process"
    pending_commands_store.set(user_id, "/edit_plan_name_process")
    return True

@command("/edit_plan_name_process")
def cmd_edit_plan_name_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    plan_key = User.get_data(user_id, "editing_plan_name")
    if not plan_key:
        send_message(user_id, "❌ Error", "HTML")
        return True
    
    new_name = text.strip()
    if not new_name:
        send_message(user_id, "❌ Invalid name!", "HTML")
        return True
    
    plan_names = bot_data.get_data("plan_names") or {}
    plan_names[plan_key] = new_name
    bot_data.save_data("plan_names", plan_names)
    
    send_message(
        user_id,
        f"✅ <b>Plan Name Updated!</b>\n\n"
        f"{plan_key} → {new_name}",
        "HTML"
    )
    
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "editing_plan_name", None)
    return True

@command("/edit_price")
def cmd_edit_price(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "❌ Invalid")
        return True
    
    parts = params.split("_")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid")
        return True
    
    mod_id = parts[0]
    day = parts[1]
    
    User.save_data(user_id, "editing_price_key", f"{mod_id}_{day}")
    
    current_price = bot_data.get_data(f"{mod_id}_{day}d_price") or 0
    
    send_message(
        user_id,
        f"<b>💰 Enter New Price For {mod_id.upper()}</b>\n\n"
        f"Current: ₹{current_price}\n\n"
        f"Send number only.\n"
        f"Type /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/edit_price_process"
    pending_commands_store.set(user_id, "/edit_price_process")
    return True

@command("/edit_price_process")
def cmd_edit_price_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    price_key = User.get_data(user_id, "editing_price_key")
    if not price_key:
        send_message(user_id, "❌ Error", "HTML")
        return True
    
    try:
        price = float(text)
        if price <= 0:
            send_message(user_id, "❌ Price must be greater than 0!", "HTML")
            return True
        
        key = f"{price_key}d_price"
        bot_data.save_data(key, price)
        
        send_message(
            user_id,
            f"✅ <b>Price Updated!</b>\n\n"
            f"₹{price}",
            "HTML"
        )
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "editing_price_key", None)
    except:
        send_message(user_id, "❌ Invalid number!", "HTML")
    return True

@command("/edit_reseller_price")
def cmd_edit_reseller_price(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "❌ Invalid")
        return True
    
    parts = params.split("_")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid")
        return True
    
    mod_id = parts[0]
    day = parts[1]
    
    User.save_data(user_id, "editing_reseller_key", f"{mod_id}_{day}")
    
    current_price = bot_data.get_data(f"{mod_id}_{day}d_reseller_price") or 0
    
    send_message(
        user_id,
        f"<b>💰 Enter New Reseller Price For {mod_id.upper()}</b>\n\n"
        f"Current: ₹{current_price}\n\n"
        f"Send number only.\n"
        f"Type /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/edit_reseller_price_process"
    pending_commands_store.set(user_id, "/edit_reseller_price_process")
    return True

@command("/edit_reseller_price_process")
def cmd_edit_reseller_price_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    price_key = User.get_data(user_id, "editing_reseller_key")
    if not price_key:
        send_message(user_id, "❌ Error", "HTML")
        return True
    
    try:
        price = float(text)
        if price <= 0:
            send_message(user_id, "❌ Price must be greater than 0!", "HTML")
            return True
        
        key = f"{price_key}d_reseller_price"
        bot_data.save_data(key, price)
        
        send_message(
            user_id,
            f"✅ <b>Reseller Price Updated!</b>\n\n"
            f"₹{price}",
            "HTML"
        )
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "editing_reseller_key", None)
    except:
        send_message(user_id, "❌ Invalid number!", "HTML")
    return True

# ========== FIXED KEY ADD COMMANDS ==========
@command("/add_keys_plan")
def cmd_add_keys_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    
    if not params:
        send_message(user_id, "❌ Invalid")
        return True
    
    # FIXED: Better parsing for mod_id with underscores
    parts = params.split("_")
    if len(parts) < 2:
        send_message(user_id, "❌ Invalid format! Use: mod_id_day")
        return True
    
    # Last part is day
    day_str = parts[-1]
    try:
        day_num = int(day_str)
    except:
        send_message(user_id, "❌ Invalid day format!")
        return True
    
    # Rest is mod_id (join back with underscores)
    mod_id = "_".join(parts[:-1])
    
    key_name = f"{mod_id}_{day_num}d_keys"
    
    existing = bot_data.get_data(key_name)
    if existing is None:
        bot_data.save_data(key_name, [])
        existing = []
    
    current_stock = len(existing)
    
    User.save_data(user_id, "add_keys_key_name", key_name)
    User.save_data(user_id, "add_keys_mod_id", mod_id)
    User.save_data(user_id, "add_keys_day", day_num)
    
    send_message(
        user_id,
        f"<b>🔑 Add Keys For {mod_id.upper()} - {day_num} Day</b>\n\n"
        f"Current Stock: {current_stock}\n\n"
        f"Send keys one per line.\n"
        f"Type <b>DONE</b> to finish.\n"
        f"Type /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/add_keys_process_final"
    pending_commands_store.set(user_id, "/add_keys_process_final")
    return True

@command("/add_keys_process_final")
def cmd_add_keys_process_final(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "add_keys_key_name", None)
        User.save_data(user_id, "add_keys_mod_id", None)
        User.save_data(user_id, "add_keys_day", None)
        return True
    
    key_name = User.get_data(user_id, "add_keys_key_name")
    if not key_name:
        send_message(user_id, "❌ Error: No key name found", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    if text.upper() == "DONE":
        mod_id = User.get_data(user_id, "add_keys_mod_id") or "Unknown"
        day = User.get_data(user_id, "add_keys_day") or "Unknown"
        existing = bot_data.get_data(key_name) or []
        send_message(
            user_id, 
            f"✅ <b>All Keys Added!</b>\n\n"
            f"📦 Mod: {mod_id.upper()}\n"
            f"📅 Day: {day}\n"
            f"🔑 Total Keys: {len(existing)}\n"
            f"📂 Key Name: <code>{key_name}</code>",
            "HTML"
        )
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "add_keys_key_name", None)
        User.save_data(user_id, "add_keys_mod_id", None)
        User.save_data(user_id, "add_keys_day", None)
        return True
    
    existing = bot_data.get_data(key_name) or []
    if isinstance(existing, str):
        existing = [existing]
    
    keys = text.strip().split('\n')
    added = 0
    for k in keys:
        k = k.strip()
        if k:
            existing.append(k)
            added += 1
    
    bot_data.save_data(key_name, existing)
    
    # Verify the keys were saved
    verify_keys = bot_data.get_data(key_name) or []
    
    send_message(
        user_id,
        f"✅ <b>Added {added} Key(s)</b>\n\n"
        f"Total Stock: {len(verify_keys)}\n"
        f"📂 Key Name: <code>{key_name}</code>\n\n"
        f"Send more keys or type <b>DONE</b> to finish.",
        "HTML"
    )
    return True

@command("/remove_plan")
def cmd_remove_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "❌ Invalid")
        return True
    
    parts = params.split("_")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid")
        return True
    
    mod_id = parts[0]
    try:
        day = int(parts[1])
    except:
        send_message(user_id, "❌ Invalid")
        return True
    
    markup = {
        "inline_keyboard": [
            [{"text": "✅ YES, REMOVE", "callback_data": f"/confirm_remove_plan {mod_id}_{day}", "style": "danger"}],
            [{"text": "❌ NO, CANCEL", "callback_data": f"/edit_plan {mod_id}_{day}", "style": "success"}]
        ]
    }
    
    plan_names = bot_data.get_data("plan_names") or {}
    plan_key = f"{mod_id}_{day}"
    plan_display = plan_names.get(plan_key, f"{day} Day{'s' if day > 1 else ''}")
    
    send_message(
        user_id,
        f"⚠️ <b>Remove Plan: {mod_id.upper()} - {plan_display}</b>\n\n"
        f"Are you sure you want to remove this plan?\n\n"
        f"This will delete ALL keys for this plan!",
        "HTML",
        reply_markup=markup
    )
    return True

@command("/confirm_remove_plan")
def cmd_confirm_remove_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "❌ Invalid")
        return True
    
    parts = params.split("_")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid")
        return True
    
    mod_id = parts[0]
    try:
        day = int(parts[1])
    except:
        send_message(user_id, "❌ Invalid")
        return True
    
    price_key = f"{mod_id}_{day}d_price"
    reseller_key = f"{mod_id}_{day}d_reseller_price"
    keys_key = f"{mod_id}_{day}d_keys"
    
    bot_data.collection.delete_one({"key": price_key})
    bot_data.collection.delete_one({"key": reseller_key})
    bot_data.collection.delete_one({"key": keys_key})
    
    plan_names = bot_data.get_data("plan_names") or {}
    plan_key = f"{mod_id}_{day}"
    if plan_key in plan_names:
        del plan_names[plan_key]
        bot_data.save_data("plan_names", plan_names)
    
    send_message(
        user_id,
        f"✅ <b>Plan Removed!</b>",
        "HTML"
    )
    
    cmd_manage_mod(message, mod_id, None)
    return True

@command("/add_new_plan")
def cmd_add_new_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    mod_id = params
    if not mod_id:
        send_message(user_id, "❌ Invalid Mod")
        return True
    
    User.save_data(user_id, "add_plan_mod", mod_id)
    
    send_message(
        user_id,
        f"<b>➕ Add New Plan For {mod_id.upper()}</b>\n\n"
        f"Send details in this format:\n\n"
        f"<code>DAYS|PRICE|RESELLER_PRICE</code>\n\n"
        f"Example: <code>7|250|200</code>\n\n"
        f"Type /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/add_new_plan_process"
    pending_commands_store.set(user_id, "/add_new_plan_process")
    return True

@command("/add_new_plan_process")
def cmd_add_new_plan_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    mod_id = User.get_data(user_id, "add_plan_mod")
    if not mod_id:
        send_message(user_id, "❌ Error", "HTML")
        return True
    
    parts = text.split("|")
    if len(parts) != 3:
        send_message(
            user_id,
            "❌ Invalid format!\n\n"
            "Use: <code>DAYS|PRICE|RESELLER_PRICE</code>\n"
            "Example: <code>7|250|200</code>",
            "HTML"
        )
        return True
    
    try:
        days = int(parts[0].strip())
        price = float(parts[1].strip())
        reseller_price = float(parts[2].strip())
    except:
        send_message(user_id, "❌ Invalid numbers!", "HTML")
        return True
    
    if days <= 0 or price <= 0 or reseller_price <= 0:
        send_message(user_id, "❌ ALL values must be greater than 0!", "HTML")
        return True
    
    price_key = f"{mod_id}_{days}d_price"
    reseller_key = f"{mod_id}_{days}d_reseller_price"
    keys_key = f"{mod_id}_{days}d_keys"
    
    bot_data.save_data(price_key, price)
    bot_data.save_data(reseller_key, reseller_price)
    bot_data.save_data(keys_key, [])
    
    mods = bot_data.get_data("mods_list") or []
    if mod_id not in mods:
        mods.append(mod_id)
        bot_data.save_data("mods_list", mods)
        print(f"✅ Added new mod '{mod_id}' to mods_list")
    
    plan_names = bot_data.get_data("plan_names") or {}
    plan_key = f"{mod_id}_{days}"
    plan_names[plan_key] = f"{days} Day{'s' if days > 1 else ''}"
    bot_data.save_data("plan_names", plan_names)
    
    send_message(
        user_id,
        f"✅ <b>Plan Added Successfully!</b>\n\n"
        f"📦 Mod: {mod_id.upper()}\n"
        f"📅 Days: {days}\n"
        f"💰 Price: ₹{price}\n"
        f"💰 Reseller: ₹{reseller_price}\n"
        f"🔑 Keys: 0\n\n"
        f"<b>✅ Now available in shop!</b>",
        "HTML"
    )
    
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "add_plan_mod", None)
    return True

@command("/add_new_mod")
def cmd_add_new_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    send_message(
        user_id,
        "<b>➕ Add New Mod</b>\n\n"
        "Send mod name:\n"
        "Example: <code>VIP MOD</code> or <code>MEGA CHEATS</code>\n\n"
        "You can also add emoji later using 'Change Mod Emoji' option.\n\n"
        "<b>✅ Mod will appear in shop automatically!</b>\n\n"
        "Type /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/add_new_mod_process"
    pending_commands_store.set(user_id, "/add_new_mod_process")
    return True

@command("/add_new_mod_process")
def cmd_add_new_mod_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    mod_name = text.strip()
    if not mod_name:
        send_message(user_id, "❌ Invalid name!", "HTML")
        return True
    
    mod_id = mod_name.replace(" ", "_").upper()
    
    mods = bot_data.get_data("mods_list") or []
    if mod_id not in mods:
        mods.append(mod_id)
        bot_data.save_data("mods_list", mods)
    
    bot_data.save_data(f"{mod_id}_display_name", mod_name)
    bot_data.save_data(f"{mod_id}_emoji", EMOJIS['package'])
    
    send_message(
        user_id,
        f"✅ <b>Mod '{mod_name}' Created!</b>\n\n"
        f"Now add plans using 'Add New Plan' button.\n"
        f"Change emoji using 'Change Mod Emoji' button.\n\n"
        f"<b>✅ Mod will appear in shop automatically!</b>",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/rename_mod")
def cmd_rename_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    mod_id = params
    if not mod_id:
        send_message(user_id, "❌ Invalid Mod")
        return True
    
    default_mods = ["drip", "SILENT", "HG"]
    if mod_id in default_mods:
        send_message(
            user_id,
            f"⚠️ <b>{mod_id.upper()} is a default mod!</b>\n\n"
            f"You cannot rename default mods.",
            "HTML"
        )
        return True
    
    User.save_data(user_id, "rename_mod_id", mod_id)
    current_name = bot_data.get_data(f"{mod_id}_display_name") or mod_id
    
    send_message(
        user_id,
        f"<b>✏️ Enter New Name For Mod</b>\n\n"
        f"Current: {current_name}\n\n"
        f"Type /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/rename_mod_process"
    pending_commands_store.set(user_id, "/rename_mod_process")
    return True

@command("/rename_mod_process")
def cmd_rename_mod_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    mod_id = User.get_data(user_id, "rename_mod_id")
    if not mod_id:
        send_message(user_id, "❌ Error", "HTML")
        return True
    
    new_name = text.strip()
    if not new_name:
        send_message(user_id, "❌ Invalid name!", "HTML")
        return True
    
    bot_data.save_data(f"{mod_id}_display_name", new_name)
    
    send_message(
        user_id,
        f"✅ <b>Mod Name Updated!</b>\n\n"
        f"{mod_id} → {new_name}",
        "HTML"
    )
    
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "rename_mod_id", None)
    return True

@command("/delete_mod")
def cmd_delete_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    mod_id = params
    if not mod_id:
        send_message(user_id, "❌ Invalid Mod")
        return True
    
    default_mods = ["drip", "SILENT", "HG"]
    if mod_id in default_mods:
        send_message(
            user_id,
            f"⚠️ <b>{mod_id.upper()} is a default mod!</b>\n\n"
            f"You cannot delete default mods.",
            "HTML"
        )
        return True
    
    User.save_data(user_id, "delete_mod_id", mod_id)
    
    markup = {
        "inline_keyboard": [
            [{"text": "✅ YES, DELETE", "callback_data": f"/confirm_delete_mod {mod_id}", "style": "danger"}],
            [{"text": "❌ NO, CANCEL", "callback_data": "/manage_mods", "style": "success"}]
        ]
    }
    
    display_name = bot_data.get_data(f"{mod_id}_display_name") or mod_id
    
    send_message(
        user_id,
        f"⚠️ <b>Delete Mod: {display_name}</b>\n\n"
        f"Are you sure you want to delete this mod?\n\n"
        f"This will remove ALL plans and keys for this mod!",
        "HTML",
        reply_markup=markup
    )
    return True

@command("/confirm_delete_mod")
def cmd_confirm_delete_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    mod_id = params
    if not mod_id:
        send_message(user_id, "❌ Invalid")
        return True
    
    all_keys = bot_data.collection.find()
    deleted = 0
    for doc in all_keys:
        key = doc.get("key", "")
        if key.startswith(mod_id + "_"):
            bot_data.collection.delete_one({"key": key})
            deleted += 1
    
    mods = bot_data.get_data("mods_list") or []
    if mod_id in mods:
        mods.remove(mod_id)
        bot_data.save_data("mods_list", mods)
    
    bot_data.collection.delete_one({"key": f"{mod_id}_display_name"})
    bot_data.collection.delete_one({"key": f"{mod_id}_product_name"})
    bot_data.collection.delete_one({"key": f"{mod_id}_emoji"})
    
    plan_names = bot_data.get_data("plan_names") or {}
    to_delete = []
    for key in plan_names:
        if key.startswith(mod_id + "_"):
            to_delete.append(key)
    for key in to_delete:
        del plan_names[key]
    bot_data.save_data("plan_names", plan_names)
    
    send_message(
        user_id,
        f"✅ <b>Mod Deleted!</b>\n\n"
        f"Removed {deleted} entries.",
        "HTML"
    )
    
    User.save_data(user_id, "delete_mod_id", None)
    return True

@command("/addreseller")
def cmd_addreseller(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    send_message(user_id, "📩 Send me id reseller", "HTML")
    pending_commands[user_id] = "/add_reseller_process"
    pending_commands_store.set(user_id, "/add_reseller_process")
    return True

@command("/add_reseller_process")
def cmd_add_reseller_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    target_user = message.get("text", "").strip()
    try:
        target_user = str(int(target_user))
    except:
        send_message(user_id, "Invalid User ID.")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    resellers = bot_data.get_data("resellers_list") or []
    if target_user in [str(u) for u in resellers]:
        send_message(user_id, "User already a reseller.")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    resellers.append(target_user)
    bot_data.save_data("resellers_list", resellers)
    send_message(user_id, f"User <code>{target_user}</code> added as Reseller.", "HTML")
    try:
        send_message(target_user, "You are now a Reseller", "HTML")
    except:
        pass
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/removereseller")
def cmd_removereseller(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    send_message(user_id, "Send me reseller id to remove", "HTML")
    pending_commands[user_id] = "/remove_reseller_process"
    pending_commands_store.set(user_id, "/remove_reseller_process")
    return True

@command("/remove_reseller_process")
def cmd_remove_reseller_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    target_user = message.get("text", "").strip()
    try:
        target_user = str(int(target_user))
    except:
        send_message(user_id, "Invalid User ID.")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    resellers = bot_data.get_data("resellers_list") or []
    if target_user not in [str(u) for u in resellers]:
        send_message(user_id, "User is not a reseller.")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    resellers = [u for u in resellers if str(u) != target_user]
    bot_data.save_data("resellers_list", resellers)
    send_message(user_id, f"User <code>{target_user}</code> removed from Resellers.", "HTML")
    try:
        send_message(target_user, "You are no longer a Reseller.", "HTML")
    except:
        pass
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/resellerlist")
def cmd_resellerlist(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    resellers = bot_data.get_data("resellers_list") or []
    if not resellers:
        send_message(user_id, "No resellers found.")
        return True
    text = "Reseller List\n━━━━━━━━━━━━━━━━━━\n\n"
    count = 1
    for res in resellers:
        text += f"{count}. ID: <code>{res}</code>\n"
        count += 1
    text += f"\n━━━━━━━━━━━━━━━━━━\nTotal Resellers: {len(resellers)}"
    send_message(user_id, text, "HTML")
    return True

# ============================================================
# ========== BROADCAST & MAIN ==========
# ============================================================

@command("/broadcast")
def cmd_broadcast(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    
    all_users = user_data_store.get_all_users()
    for doc in pending_payments_store.collection.find({}, {"user_id": 1}):
        if doc.get("user_id") not in all_users:
            all_users.append(doc.get("user_id"))
    
    admins_list = bot_data.get_data("AllBotAdminss") or []
    for admin in admins_list:
        if admin not in all_users:
            all_users.append(admin)
    
    all_users = list(set(all_users))
    User.save_data(user_id, "broadcast_users", all_users)
    
    send_message(
        user_id, 
        f"📢 <b>BROADCAST MODE</b>\n\n"
        f"👥 Total Users: {len(all_users)}\n\n"
        f"Send ANY message\n"
        f"Type /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/broadcast_send_media"
    pending_commands_store.set(user_id, "/broadcast_send_media")
    return True

@command("/broadcast_send_media")
def cmd_broadcast_send_media(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    if message.get("text") and message.get("text", "").strip() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "broadcast_users", None)
        return True
    
    users = User.get_data(user_id, "broadcast_users") or []
    if not users:
        send_message(user_id, "No users to broadcast.", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    from_chat_id = message.get("chat", {}).get("id")
    msg_id_to_forward = message.get("message_id")
    
    success = 0
    failed = 0
    
    for target_user in users:
        try:
            forward_message(target_user, from_chat_id, msg_id_to_forward)
            success += 1
        except:
            failed += 1
        time.sleep(0.1)
    
    send_message(
        user_id, 
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"📤 Success: {success}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {len(users)}",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "broadcast_users", None)
    return True

@command("/setMyCommands")
def cmd_set_commands(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    commands_list = [{"command": "start", "description": "START TO BUY"}]
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
    try:
        response = requests.post(url, json={"commands": commands_list})
        send_message(user_id, str(response.json()))
    except:
        send_message(user_id, "Error setting commands")
    return True

def handle_update(update):
    if "callback_query" in update:
        callback = update["callback_query"]
        data = callback.get("data", "")
        user_id = callback.get("from", {}).get("id")
        msg_id = callback.get("message", {}).get("message_id")
        answer_callback(callback.get("id"))
        parts = data.split(" ")
        cmd = parts[0]
        params = " ".join(parts[1:]) if len(parts) > 1 else None
        msg = {
            "message_id": msg_id,
            "from": callback.get("from", {}),
            "chat": {"id": user_id},
            "date": int(time.time()),
            "text": data,
            "reply_markup": callback.get("message", {}).get("reply_markup")
        }
        if cmd in commands:
            try:
                commands[cmd](msg, params)
            except Exception as e:
                print(f"Callback error: {e}")
        return
    if "message" in update:
        msg = update["message"]
        user_id = msg.get("from", {}).get("id")
        text = msg.get("text", "")
        if user_id in pending_commands:
            pending_cmd = pending_commands[user_id]
            if pending_cmd in commands:
                try:
                    commands[pending_cmd](msg, None)
                except Exception as e:
                    print(f"Pending command error: {e}")
                return
        if text.startswith("/"):
            parts = text.split(" ")
            cmd = parts[0]
            params = " ".join(parts[1:]) if len(parts) > 1 else None
            if cmd in commands:
                try:
                    commands[cmd](msg, params)
                except Exception as e:
                    print(f"Command error: {e}")

def main():
    print("🤖 Bot Started with MongoDB!")
    print(f"📁 Connected to MongoDB: {DB_NAME}")
    print(f"📋 Registered commands: {list(commands.keys())}")
    
    last_update_id = 0
    while True:
        try:
            updates = get_updates(last_update_id + 1)
            if updates:
                print(f"📨 Received {len(updates)} updates")
            for update in updates:
                if "update_id" in update:
                    last_update_id = update["update_id"]
                handle_update(update)
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("🛑 Bot stopped.")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
