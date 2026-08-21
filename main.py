# tusharbot.py - COMPLETE WITH RESELLER API INTEGRATION (FULL FIXED)
import requests
import json
import time
from datetime import datetime
import threading
from pymongo import MongoClient

BOT_TOKEN = "8565204943:AAEw7F-5NIwZjluyWT-PQYk70xHY3j01xAo"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ========== RESELLER API CONFIGURATION ==========
RESELLER_API_URL = "https://xyzcheats.com/api/reseller_v1.php"
RESELLER_API_KEY = "b25eb076f5c0412fa9f1eba94550d02e"
RESELLER_API_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'x-master-key': 'a7f3e8b2c9d1f4a6b8c2d5e9f1a3b6c8'
}

# ========== PRODUCT PID MAPPING ==========
PRODUCT_PID_MAP = {
    "drip_1d": "133",
    "drip_3d": "133",
    "drip_7d": "133",
    "drip_15d": "136",
    "drip_30d": "136",
    "silent_1d": "133",
    "silent_3d": "133",
    "silent_7d": "133",
    "silent_14d": "136",
    "silent_28d": "136",
    "hg_1d": "133",
    "hg_3d": "133",
    "hg_7d": "133",
    "hg_14d": "136",
    "hg_21d": "136",
}

DURATION_MAP = {
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

PRODUCT_NEEDS_ANDROID_ID = {
    "drip_1d": True,
    "drip_3d": True,
    "drip_7d": True,
    "drip_15d": True,
    "drip_30d": True,
    "silent_1d": True,
    "silent_3d": True,
    "silent_7d": True,
    "silent_14d": True,
    "silent_28d": True,
    "hg_1d": True,
    "hg_3d": True,
    "hg_7d": True,
    "hg_14d": True,
    "hg_21d": True,
}

# ================================================

# MongoDB Connection
MONGO_URI = "mongodb+srv://crasher3210_db_user:devex5656@cluster0.9y5axka.mongodb.net/?appName=Cluster0&compressors=zlib"
DB_NAME = "telegram_bot1"

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
        self.db.processed_payments.create_index("user_id")
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
    
    def get_all_for_user(self, user_id):
        docs = self.collection.find({"user_id": str(user_id)})
        return {doc["key"]: doc["value"] for doc in docs}
    
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
        return doc
    
    def get_order(self, order_id):
        return self.collection.find_one({"order_id": order_id})
    
    def mark_verified(self, order_id):
        self.collection.update_one(
            {"order_id": order_id},
            {"$set": {"status": "verified", "verified_at": datetime.now()}}
        )
    
    def delete(self, order_id):
        self.collection.delete_one({"order_id": order_id})

payment_orders_store = PaymentOrdersStore()

# ========== RESELLER API FUNCTIONS ==========

def generate_api_key(product_pid, duration, android_id=None):
    data = {
        'api_key': RESELLER_API_KEY,
        'action': 'buy',
        'product_id': str(product_pid),
        'duration': duration
    }
    if android_id:
        data['android_id'] = android_id
    
    try:
        response = requests.post(
            RESELLER_API_URL,
            data=data,
            headers=RESELLER_API_HEADERS,
            timeout=15
        )
        result = response.json()
        print(f"🔑 API Response: {result}")
        
        if result.get('status') == 'success' or result.get('success') == True:
            key = result.get('key') or result.get('data', {}).get('key') or result.get('license_key')
            if key:
                return True, key
            return False, "API returned success but no key found"
        else:
            error_msg = result.get('message') or result.get('error') or 'Unknown API error'
            return False, error_msg
    except Exception as e:
        return False, f"API Error: {str(e)}"

def get_product_pid(product_key):
    return PRODUCT_PID_MAP.get(product_key)

def get_duration(plan_number):
    return DURATION_MAP.get(str(plan_number), "1 Day")

def needs_android_id(product_key):
    return PRODUCT_NEEDS_ANDROID_ID.get(product_key, True)

# ================================================

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

class User:
    @staticmethod
    def get_data(user_id, key):
        return get_user_data(user_id, key)
    
    @staticmethod
    def save_data(user_id, key, value):
        set_user_data(user_id, key, value)

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
    "6": "1 Day",
    "7": "3 Days",
    "8": "7 Days",
    "9": "14 Days",
    "15": "28 Days",
}

# ========== COMMANDS ==========

@command("/start")
@command("/Start")
@command("/START")
def cmd_start(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not User.get_data(user_id, "joined_date"):
        User.save_data(user_id, "joined_date", message.get("date"))
    balance = Resources.another_res("Balance", user=user_id).value()
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
    reply_markup = {
        "inline_keyboard": [
            [{"text": "🛒 BUY HACK", "callback_data": "/shopnawkk"}],
            [{"text": "🔑 MY KEY", "callback_data": "/orderksk"}, {"text": "👤 PROFILE", "callback_data": "/profilemmm"}],
            [{"text": "📖 HOW TO USE", "callback_data": "/spinj"}, {"text": "💬 SUPPORT", "callback_data": "/supportj"}],
            [{"text": "💰 ADD FUND", "callback_data": "/addpayment"}],
            [{"text": "📤 PAY PROOF", "url": "https://t.me/subhajit_feedback"}, {"text": "📥 DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl"}]
        ]
    }
    send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/shopnawkk")
def cmd_shopnawkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    text = """
━━━━━━━━━━━━━━━━━━━━
🛒 <b>PANNEL STORE — SHOP</b>
━━━━━━━━━━━━━━━━━━━━

📦 Choose a product:
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": "DRIP CLIENT NON-ROOT", "callback_data": "/SHOP_P1"}],
            [{"text": "SILENT CHEATS ANDROID", "callback_data": "/SHOP_P2"}],
            [{"text": "PRIME HOOK", "callback_data": "/SHOP_P4"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/backkkk")
def cmd_backkkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    balance = Resources.another_res("Balance", user=user_id).value()
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
    reply_markup = {
        "inline_keyboard": [
            [{"text": "🛒 BUY HACK", "callback_data": "/shopnawkk"}],
            [{"text": "🔑 MY KEY", "callback_data": "/orderksk"}, {"text": "👤 PROFILE", "callback_data": "/profilemmm"}],
            [{"text": "📖 HOW TO USE", "callback_data": "/spinj"}, {"text": "💬 SUPPORT", "callback_data": "/supportj"}],
            [{"text": "💰 ADD FUND", "callback_data": "/addpayment"}],
            [{"text": "📤 PAY PROOF", "url": "https://t.me/subhajit_feedback"}, {"text": "📥 DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/SHOP_P1")
def cmd_shop_p1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    resellers = bot_data.get_data("resellers_list") or []
    is_reseller = str(user_id) in [str(u) for u in resellers]
    p1 = bot_data.get_data("drip_1d_price") or 108
    p3 = bot_data.get_data("drip_3d_price") or 260
    p7 = bot_data.get_data("drip_7d_price") or 360
    p15 = bot_data.get_data("drip_15d_price") or 560
    p30 = bot_data.get_data("drip_30d_price") or 810
    if is_reseller:
        p1 = bot_data.get_data("drip_1d_reseller_price") or 95
        p3 = bot_data.get_data("drip_3d_reseller_price") or 220
        p7 = bot_data.get_data("drip_7d_reseller_price") or 320
        p15 = bot_data.get_data("drip_15d_reseller_price") or 480
        p30 = bot_data.get_data("drip_30d_reseller_price") or 750
    buy_cmd = "/buyjai_reseller" if is_reseller else "/buyjai"
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📦 𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗 ✅ (𝘉𝘌𝘚𝘛 𝘚𝘌𝘓𝘓𝘌𝘙 💫)\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📦 Extra 2% discount applied\n"
        "Choose a plan 👇"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": f"1 DAY - ₹{p1}", "callback_data": f"{buy_cmd} 1"}],
            [{"text": f"3 DAYS - ₹{p3}", "callback_data": f"{buy_cmd} 2"}],
            [{"text": f"7 DAYS - ₹{p7}", "callback_data": f"{buy_cmd} 3"}],
            [{"text": f"15 DAYS - ₹{p15}", "callback_data": f"{buy_cmd} 4"}],
            [{"text": f"30 DAYS - ₹{p30}", "callback_data": f"{buy_cmd} 5"}],
            [{"text": "🔙 BACK", "callback_data": "/shopnawkk"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/SHOP_P2")
def cmd_shop_p2(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    resellers = bot_data.get_data("resellers_list") or []
    is_reseller = str(user_id) in [str(u) for u in resellers]
    p1 = bot_data.get_data("SILENT_1d_price") or 108
    p3 = bot_data.get_data("SILENT_3d_price") or 260
    p7 = bot_data.get_data("SILENT_7d_price") or 360
    p14 = bot_data.get_data("SILENT_14d_price") or 560
    p28 = bot_data.get_data("SILENT_28d_price") or 810
    if is_reseller:
        p1 = bot_data.get_data("SILENT_1d_reseller_price") or 95
        p3 = bot_data.get_data("SILENT_3d_reseller_price") or 220
        p7 = bot_data.get_data("SILENT_7d_reseller_price") or 320
        p14 = bot_data.get_data("SILENT_14d_reseller_price") or 480
        p28 = bot_data.get_data("SILENT_28d_reseller_price") or 750
    buy_cmd = "/buyjai_reseller" if is_reseller else "/buyjai"
    text = """
━━━━━━━━━━━━━━━━━━━━
📦 SILENT CHEATS ANDROID
━━━━━━━━━━━━━━━━━━━━

Choose a plan 👇
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": f"1 Day - ₹{p1}", "callback_data": f"{buy_cmd} 6"}],
            [{"text": f"3 Days - ₹{p3}", "callback_data": f"{buy_cmd} 7"}],
            [{"text": f"7 Days - ₹{p7}", "callback_data": f"{buy_cmd} 8"}],
            [{"text": f"14 Days - ₹{p14}", "callback_data": f"{buy_cmd} 9"}],
            [{"text": f"28 Days - ₹{p28}", "callback_data": f"{buy_cmd} 15"}],
            [{"text": "🔙 BACK", "callback_data": "/shopnawkk"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/SHOP_P4")
def cmd_shop_p4(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    resellers = bot_data.get_data("resellers_list") or []
    is_reseller = str(user_id) in [str(u) for u in resellers]
    p1 = bot_data.get_data("HG_1d_price") or 108
    p3 = bot_data.get_data("HG_3d_price") or 200
    p7 = bot_data.get_data("HG_7d_price") or 360
    p14 = bot_data.get_data("HG_14d_price") or 600
    p21 = bot_data.get_data("HG_21d_price") or 700
    if is_reseller:
        p1 = bot_data.get_data("HG_1d_reseller_price") or 95
        p3 = bot_data.get_data("HG_3d_reseller_price") or 180
        p7 = bot_data.get_data("HG_7d_reseller_price") or 320
        p14 = bot_data.get_data("HG_14d_reseller_price") or 550
        p21 = bot_data.get_data("HG_21d_reseller_price") or 650
    buy_cmd = "/buyjai_reseller" if is_reseller else "/buyjai"
    text = """
━━━━━━━━━━━━━━━━━━━━
🔥 PRIME HOOK
━━━━━━━━━━━━━━━━━━━━

Choose a plan 👇
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": f"1 Day - ₹{p1}", "callback_data": f"{buy_cmd} 10"}],
            [{"text": f"3 Days - ₹{p3}", "callback_data": f"{buy_cmd} 11"}],
            [{"text": f"7 Days - ₹{p7}", "callback_data": f"{buy_cmd} 12"}],
            [{"text": f"14 Days - ₹{p14}", "callback_data": f"{buy_cmd} 13"}],
            [{"text": f"21 Days - ₹{p21}", "callback_data": f"{buy_cmd} 14"}],
            [{"text": "🔙 BACK", "callback_data": "/shopnawkk"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/buyjai")
def cmd_buyjai(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not params:
        send_message(user_id, "Invalid Product")
        return True
    
    product_map = {
        "1": ("drip_1d_price", "drip_1d", "DRIP CLIENT APK MOD\n1 Day"),
        "2": ("drip_3d_price", "drip_3d", "DRIP CLIENT APK MOD\n3 Days"),
        "3": ("drip_7d_price", "drip_7d", "DRIP CLIENT APK MOD\n7 Days"),
        "4": ("drip_15d_price", "drip_15d", "DRIP CLIENT APK MOD\n15 Days"),
        "5": ("drip_30d_price", "drip_30d", "DRIP CLIENT APK MOD\n30 Days"),
        "6": ("SILENT_1d_price", "silent_1d", "SILENT CHEATS ANDROID\n1 Day"),
        "7": ("SILENT_3d_price", "silent_3d", "SILENT CHEATS ANDROID\n3 Days"),
        "8": ("SILENT_7d_price", "silent_7d", "SILENT CHEATS ANDROID\n7 Days"),
        "9": ("SILENT_14d_price", "silent_14d", "SILENT CHEATS ANDROID\n14 Days"),
        "10": ("HG_1d_price", "hg_1d", "PRIME-HOOK\n1 Day"),
        "11": ("HG_3d_price", "hg_3d", "PRIME-HOOK\n3 Days"),
        "12": ("HG_7d_price", "hg_7d", "PRIME-HOOK\n7 Days"),
        "13": ("HG_14d_price", "hg_14d", "PRIME-HOOK\n14 Days"),
        "14": ("HG_21d_price", "hg_21d", "PRIME-HOOK\n21 Days"),
        "15": ("SILENT_28d_price", "silent_28d", "SILENT CHEATS ANDROID\n28 Days"),
    }
    
    if params in product_map:
        price_key, product_key, title = product_map[params]
        price = bot_data.get_data(price_key) or 0
        try:
            price = float(price)
        except:
            send_message(user_id, "Invalid price.")
            return True
        
        if price <= 0:
            send_message(user_id, "Price not set.")
            return True
        
        # Store purchase data
        User.save_data(user_id, "last_product1", title)
        User.save_data(user_id, "last_plan", params)
        User.save_data(user_id, "last_product_key", product_key)
        User.save_data(user_id, "last_price", price)
        
        # Check if product needs Android ID
        if needs_android_id(product_key):
            send_message(
                user_id,
                f"🔐 <b>Android ID Required</b>\n\n"
                f"This product requires your device's Android ID.\n\n"
                f"Please send your Android ID to continue.\n"
                f"Type /cancel to cancel.",
                "HTML"
            )
            pending_commands[user_id] = "/process_android_id"
            pending_commands_store.set(user_id, "/process_android_id")
            return True
        else:
            return process_purchase(message, product_key, params, price, title)
    else:
        send_message(user_id, "Invalid Product ID")
    return True

@command("/buyjai_reseller")
def cmd_buyjai_reseller(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not params:
        send_message(user_id, "Invalid Product")
        return True
    
    product_map = {
        "1": ("drip_1d_reseller_price", "drip_1d", "DRIP CLIENT APK MOD\n1 Day"),
        "2": ("drip_3d_reseller_price", "drip_3d", "DRIP CLIENT APK MOD\n3 Days"),
        "3": ("drip_7d_reseller_price", "drip_7d", "DRIP CLIENT APK MOD\n7 Days"),
        "4": ("drip_15d_reseller_price", "drip_15d", "DRIP CLIENT APK MOD\n15 Days"),
        "5": ("drip_30d_reseller_price", "drip_30d", "DRIP CLIENT APK MOD\n30 Days"),
        "6": ("SILENT_1d_reseller_price", "silent_1d", "SILENT CHEATS ANDROID\n1 Day"),
        "7": ("SILENT_3d_reseller_price", "silent_3d", "SILENT CHEATS ANDROID\n3 Days"),
        "8": ("SILENT_7d_reseller_price", "silent_7d", "SILENT CHEATS ANDROID\n7 Days"),
        "9": ("SILENT_14d_reseller_price", "silent_14d", "SILENT CHEATS ANDROID\n14 Days"),
        "10": ("HG_1d_reseller_price", "hg_1d", "PRIME-HOOK\n1 Day"),
        "11": ("HG_3d_reseller_price", "hg_3d", "PRIME-HOOK\n3 Days"),
        "12": ("HG_7d_reseller_price", "hg_7d", "PRIME-HOOK\n7 Days"),
        "13": ("HG_14d_reseller_price", "hg_14d", "PRIME-HOOK\n14 Days"),
        "14": ("HG_21d_reseller_price", "hg_21d", "PRIME-HOOK\n21 Days"),
        "15": ("SILENT_28d_reseller_price", "silent_28d", "SILENT CHEATS ANDROID\n28 Days"),
    }
    
    if params in product_map:
        price_key, product_key, title = product_map[params]
        price = bot_data.get_data(price_key) or 0
        try:
            price = float(price)
        except:
            send_message(user_id, "Invalid price.")
            return True
        
        if price <= 0:
            send_message(user_id, "Price not set.")
            return True
        
        User.save_data(user_id, "last_product1", title)
        User.save_data(user_id, "last_plan", params)
        User.save_data(user_id, "last_product_key", product_key)
        User.save_data(user_id, "last_price", price)
        
        if needs_android_id(product_key):
            send_message(
                user_id,
                f"🔐 <b>Android ID Required</b>\n\n"
                f"This product requires your device's Android ID.\n\n"
                f"Please send your Android ID to continue.\n"
                f"Type /cancel to cancel.",
                "HTML"
            )
            pending_commands[user_id] = "/process_android_id"
            pending_commands_store.set(user_id, "/process_android_id")
            return True
        else:
            return process_purchase(message, product_key, params, price, title)
    else:
        send_message(user_id, "Invalid Product ID")
    return True

@command("/process_android_id")
def process_android_id(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "last_product_key", None)
        return True
    
    # Validate Android ID
    if len(text) != 16 or not all(c in '0123456789abcdefABCDEF' for c in text):
        send_message(
            user_id,
            "❌ Invalid Android ID.\n\n"
            "Android ID should be 16 characters (hexadecimal).\n"
            "Example: <code>0b9b969bc2e7997b</code>\n\n"
            "Please send again or type /cancel to cancel.",
            "HTML"
        )
        return True
    
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    
    product_key = User.get_data(user_id, "last_product_key")
    plan = User.get_data(user_id, "last_plan")
    price = User.get_data(user_id, "last_price")
    title = User.get_data(user_id, "last_product1")
    
    if not product_key or not plan or not price:
        send_message(user_id, "No pending purchase found. Please start again.", "HTML")
        return True
    
    return process_purchase(message, product_key, plan, price, title, android_id=text)

def process_purchase(message, product_key, plan, price, title, android_id=None):
    user_id = message.get("from", {}).get("id")
    balance = Resources.another_res("Balance", user=user_id)
    
    if balance.value() < price:
        User.save_data(user_id, "last_deposit_amount", price)
        User.save_data(user_id, "last_product", title)
        cmd_autobuy1(message, None)
        return True
    
    # Deduct balance
    balance.cut(price)
    Resources.another_res("Order", user=user_id).add(1)
    
    # Generate key via API
    pid = get_product_pid(product_key)
    duration = get_duration(plan)
    
    if not pid:
        send_message(user_id, "❌ Product PID not configured. Contact admin.", "HTML")
        balance.add(price)
        return True
    
    success, result = generate_api_key(pid, duration, android_id)
    
    if success:
        easy_time = get_easy_time()
        send_message(
            user_id,
            f"🛒 {title}\n\n"
            f"🔑 <b>Your Key:</b>\n<code>{result}</code>\n\n"
            f"💰 Deducted: ₹{price}\n"
            f"⏳ Duration: {duration}\n"
            f"📦 Time: {easy_time}\n\n"
            f"📢 <b>ALL FILES UPDATE</b>\n"
            f"@SUBHAJIT_UPDATES",
            "HTML"
        )
        
        adm_ac = User.get_data(user_id, "userhAC") or []
        adm_ac.append(
            f"📆 {easy_time}\n"
            f"👤 {message.get('from', {}).get('first_name', 'User')} [{user_id}]\n"
            f"💰 ₹{price}\n"
            f"🔑 {result}\n"
            f"📱 Android ID: {android_id or 'N/A'}"
        )
        User.save_data(user_id, "userhAC", adm_ac)
        return True
    else:
        balance.add(price)
        send_message(
            user_id,
            f"❌ <b>Key Generation Failed</b>\n\n"
            f"Error: {result}\n\n"
            f"Your balance of ₹{price} has been refunded.\n"
            f"Please try again later or contact support.",
            "HTML"
        )
        return True

@command("/autobuy1")
def cmd_autobuy1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
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
    
    User.save_data(user_id, "last_order_id", order_id)
    User.save_data(user_id, "payment_processed", False)
    pending_payments[user_id] = {
        "order_id": order_id,
        "msg_id": message.get("message_id"),
        "user_id": str(user_id)
    }
    pending_payments_store.set(user_id, pending_payments[user_id])
    
    caption = (
        f"<blockquote>💰 INSUFFICIENT BALANCE</blockquote>\n\n"
        f"┣ Product: {pt}\n"
        f"┣ Plan: {plan_display}\n"
        f"┣ Price: ₹{amount}\n"
        f"┣ Your Balance: ₹{balance}\n"
        f"┗ Need: ₹{need}\n\n"
        f"Scan the QR and complete payment.\n\n"
        f"🧾 <b>Order ID:</b>\n"
        f"<code>{order_id}</code>\n\n"
        f"<i>After payment, tap VERIFY PAYMENT button below.</i>"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ VERIFY PAYMENT", "callback_data": f"/verify_payment {order_id}"}],
            [{"text": "❌ CANCEL", "callback_data": f"/cancel {order_id}"}]
        ]
    }
    send_photo(user_id, qr_url, caption, "HTML", reply_markup)
    return True

@command("/verify_payment")
def cmd_verify_payment(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    msg_id = message.get("message_id")
    order_id = params
    
    if not order_id:
        send_message(user_id, "No order ID found.", "HTML")
        return True
    
    order_data = payment_orders_store.get_order(order_id)
    if not order_data:
        send_message(user_id, "❌ Invalid Order ID.", "HTML")
        return True
    
    if str(order_data.get("user_id")) != str(user_id):
        send_message(user_id, "❌ This order does not belong to you!", "HTML")
        return True
    
    if order_data.get("status") == "verified":
        send_message(user_id, "✅ This payment has already been processed.", "HTML")
        return True
    
    send_message(user_id, "⏳ Checking payment status...", "HTML")
    
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
        
        payment_orders_store.mark_verified(order_id)
        processed_payments_store.add(order_id, user_id, amount)
        
        User.save_data(user_id, "last_order_id", "")
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
            f"✅ <b>Payment Success!</b>\n\n"
            f"💰 Added: ₹{amount}\n"
            f"💳 New Balance: ₹{bal.value()}",
            "HTML"
        )
        
        # Check if there's a pending purchase
        product_key = User.get_data(user_id, "last_product_key")
        if product_key:
            send_message(
                user_id,
                f"💰 Your balance has been updated!\n"
                f"Tap BUY HACK again to complete your purchase.",
                "HTML"
            )
        return True
    else:
        send_message(
            user_id,
            f"❌ <b>Payment Not Found</b>\n\n"
            f"Order ID: <code>{order_id}</code>\n\n"
            f"Please complete the payment and try again.",
            "HTML"
        )
        return True

@command("/cancel")
def cmd_cancel(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    msg_id = message.get("message_id")
    
    order_id = params
    if not order_id:
        pending = pending_payments_store.get(user_id)
        if pending:
            order_id = pending.get("order_id") if isinstance(pending, dict) else pending
    
    if order_id:
        order_data = payment_orders_store.get_order(order_id)
        if order_data and str(order_data.get("user_id")) == str(user_id):
            payment_orders_store.delete(order_id)
    
    if msg_id:
        try:
            delete_message(user_id, msg_id)
        except:
            pass
    
    pending_payments.pop(user_id, None)
    pending_payments_store.delete(user_id)
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "last_order_id", "")
    User.save_data(user_id, "payment_processed", False)
    User.save_data(user_id, "last_product_key", None)
    send_message(user_id, "❌ Cancelled", "HTML")
    return True

@command("/orderksk")
def cmd_orderksk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    adm_ac = User.get_data(user_id, "userhAC") or []
    if not adm_ac:
        text = "━━━━━━━━━━━━━━━━━━━━\n📦 <b>MY ORDERS</b>\n━━━━━━━━━━━━━━━━━━━━\n\nYou haven't placed any orders yet."
        reply_markup = {"inline_keyboard": [[{"text": "🔙 BACK", "callback_data": "/backkkk"}]]}
        try:
            edit_message(user_id, msg_id, text, "HTML", reply_markup)
        except:
            send_message(user_id, text, "HTML", reply_markup)
    else:
        latest_10 = adm_ac[-10:][::-1]
        text = "\n\n".join([str(item) for item in latest_10 if item])
        reply_markup = {"inline_keyboard": [[{"text": "🔙 BACK", "callback_data": "/backkkk"}]]}
        try:
            edit_message(user_id, msg_id, text, "HTML", reply_markup)
        except:
            send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/profilemmm")
def cmd_profilemmm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    first_name = message.get("from", {}).get("first_name", "User")
    balance = Resources.another_res("Balance", user=user_id).value()
    orders = Resources.another_res("Order", user=user_id).value()
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👤 YOUR PROFILE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Name: {first_name}\n"
        f"🆔 User ID: {user_id}\n"
        f"💰 Balance: ₹{balance}\n"
        f"🛒 Total Orders: {orders}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": "🛒 BUY HACK", "callback_data": "/shopnawkk"}, {"text": "🔑 MY KEYS", "callback_data": "/orderksk"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
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
    msg_id = message.get("message_id")
    text = "🎥 <b>Watch the full tutorial video below</b>\n\n👇"
    reply_markup = {
        "inline_keyboard": [
            [{"text": "Watch Tutorial", "url": "https://t.me/hehehehhhsljg/162"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
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
    msg_id = message.get("message_id")
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
    reply_markup = {
        "inline_keyboard": [
            [{"text": "WHATSAPP", "url": "https://wa.me/917908696630"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

# ========== ADMIN COMMANDS ==========

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
        send_message(user_id, "<b>🚫 You Are Not This Bot Admin</b>", "HTML")
        return True
    bot_mode = bot_data.get_data("BotMode") or "ON"
    bot_sta = "🟢 On"
    bot_change = "BotMode OFF"
    if bot_mode == "OFF":
        bot_sta = "🔴 Off"
        bot_change = "BotMode ON"
    markup = {
        "inline_keyboard": [
            [{"text": "👑 Admins", "callback_data": "/TUSHAR_Admins"}],
            [{"text": "📣 Broadcast", "callback_data": "/broadcast"}, {"text": f"🤖 Bot: {bot_sta}", "callback_data": f"/admin {bot_change}"}],
            [{"text": "💰 Add Balance", "callback_data": "/ChangeAnyUserBal"}, {"text": "📝 Recent Actions", "callback_data": "/TUSHAR_AdminAction"}],
            [{"text": "📊 Shop setup", "callback_data": "/setshop_psue"}],
            [{"text": "💰 Add Reseller", "callback_data": "/addreseller"}, {"text": "⛔ Remove Reseller", "callback_data": "/removereseller"}],
            [{"text": "📝 Reseller List", "callback_data": "/resellerlist"}]
        ]
    }
    txt = f"""<b>
👋 Welcome {message.get('from', {}).get('first_name', 'Admin')} 🎉

━━━━━━━━━━━━━━━
🤖 Bot Status : {bot_sta}
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

@command("/TUSHAR_Admins")
def cmd_tushar_admins(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "<b>🚫 You Are Not This Bot Admin</b>", "HTML")
        return True
    if params and params in admins:
        admins.remove(params)
        bot_data.save_data("AllBotAdminss", admins)
    markup = {"inline_keyboard": []}
    for admin in admins:
        markup["inline_keyboard"].append([
            {"text": admin, "callback_data": f"/TUSHAR_Admins {admin}"},
            {"text": "❌", "callback_data": f"/TUSHAR_Admins {admin}"}
        ])
    markup["inline_keyboard"].append([{"text": "➕ Add Admin", "callback_data": "/TUSHAR_AddAdmin"}])
    markup["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "/admin AP"}])
    text = "<b>Here You Can Manage Your Admins</b>"
    if options:
        text = options
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
        send_message(user_id, "<b>🚫 You Are Not This Bot Admin</b>", "HTML")
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
        send_message(user_id, "<b>🚫 You Are Not This Bot Admin</b>", "HTML")
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
        send_message(user_id, "<b>🚫 You Are Not This Bot Admin</b>", "HTML")
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
        send_message(user_id, "<b>🚫 You Are Not This Bot Admin</b>", "HTML")
        return True
    send_message(
        user_id,
        f"<b>💡 Send User Telegram Id & Amount\n\n⚠️ Use Format : <code>{user_id} 10</code>\n\nAdd - Before Amount To Deduct Balance Like -10</b>",
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
        send_message(user_id, "<b>🚫 You Are Not This Bot Admin</b>", "HTML")
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
    act = f"Added {amount} Rs To {target_user} Account"
    adm_ac = bot_data.get_data("AdmAC") or []
    adm_ac.append(
        f"<b>📆 Time:</b> {easy_time}\n"
        f"👥 <b>By {message.get('from', {}).get('first_name', 'Admin')}</b> [ID: <code>{user_id}</code>]\n"
        f"🔍<b> Action: </b> {act}"
    )
    bot_data.save_data("AdmAC", adm_ac)
    send_message(
        user_id,
        f"<b>💴 Account Of <a href='tg://user?id={target_user}'>{target_user}</a> Was Increased By {amount}\n\n💰 Final Balance = {bal.value()}</b>",
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

@command("/addreseller")
def cmd_addreseller(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "<b>🚫 You Are Not This Bot Admin</b>", "HTML")
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

@command("/setshop_psue")
def cmd_setshop_psue(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "<b>🚫 You Are Not This Bot Admin</b>", "HTML")
        return True
    markup = {
        "inline_keyboard": [
            [{"text": "DRIP CLIENT MOD", "callback_data": "/SHOPADMIN_P1"}],
            [{"text": "SILENT CHEATS ANDROID", "callback_data": "/SHOPADMIN_P3"}],
            [{"text": "PRIME MOD", "callback_data": "/SHOPADMIN_P2"}],
            [{"text": "Back", "callback_data": "/admin AP"}]
        ]
    }
    txt = f"""<b>
Welcome {message.get('from', {}).get('first_name', 'Admin')}

━━━━━━━━━━━━━━━
SHOP MOOD
━━━━━━━━━━━━━━━
</b>"""
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/SHOPADMIN_P1")
def cmd_shopadmin_p1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    def get_old(day):
        price = bot_data.get_data(f"drip_{day}d_price") or 0
        reseller = bot_data.get_data(f"drip_{day}d_reseller_price") or 0
        return price, reseller
    
    p1, r1 = get_old(1)
    p3, r3 = get_old(3)
    p7, r7 = get_old(7)
    p15, r15 = get_old(15)
    p30, r30 = get_old(30)
    
    txt = (
        "DRIP CLIENT MOD\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"1D Reseller: ₹{r1}\n1D Price: ₹{p1}\n\n"
        f"3D Reseller: ₹{r3}\n3D Price: ₹{p3}\n\n"
        f"7D Reseller: ₹{r7}\n7D Price: ₹{p7}\n\n"
        f"15D Reseller: ₹{r15}\n15D Price: ₹{p15}\n\n"
        f"30D Reseller: ₹{r30}\n30D Price: ₹{p30}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\nSelect duration below:"
    )
    markup = {
        "inline_keyboard": [
            [{"text": "RESELLER 1D", "callback_data": "/SHOPADD_PM 6"}],
            [{"text": "1D Price", "callback_data": "/SHOPADD_PM 1"}],
            [{"text": "RESELLER 3D", "callback_data": "/SHOPADD_PM 7"}],
            [{"text": "3D Price", "callback_data": "/SHOPADD_PM 2"}],
            [{"text": "RESELLER 7D", "callback_data": "/SHOPADD_PM 8"}],
            [{"text": "7D Price", "callback_data": "/SHOPADD_PM 3"}],
            [{"text": "RESELLER 15D", "callback_data": "/SHOPADD_PM 9"}],
            [{"text": "15D Price", "callback_data": "/SHOPADD_PM 4"}],
            [{"text": "RESELLER 30D", "callback_data": "/SHOPADD_PM 10"}],
            [{"text": "30D Price", "callback_data": "/SHOPADD_PM 5"}],
            [{"text": "Back", "callback_data": "/setshop_psue"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

# [SHOPADMIN_P2 and SHOPADMIN_P3 simplified - similar structure]

@command("/SHOPADMIN_P2")
def cmd_shopadmin_p2(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    def get_old(day):
        price = bot_data.get_data(f"HG_{day}d_price") or 0
        reseller = bot_data.get_data(f"HG_{day}d_reseller_price") or 0
        return price, reseller
    
    p1, r1 = get_old(1)
    p3, r3 = get_old(3)
    p7, r7 = get_old(7)
    p14, r14 = get_old(14)
    p21, r21 = get_old(21)
    
    txt = (
        "PRIME MOD\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"1D Reseller: ₹{r1}\n1D Price: ₹{p1}\n\n"
        f"3D Reseller: ₹{r3}\n3D Price: ₹{p3}\n\n"
        f"7D Reseller: ₹{r7}\n7D Price: ₹{p7}\n\n"
        f"14D Reseller: ₹{r14}\n14D Price: ₹{p14}\n\n"
        f"21D Reseller: ₹{r21}\n21D Price: ₹{p21}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\nSelect duration below:"
    )
    markup = {
        "inline_keyboard": [
            [{"text": "RESELLER 1D", "callback_data": "/SHOPADD_PM 316"}],
            [{"text": "1D Price", "callback_data": "/SHOPADD_PM 311"}],
            [{"text": "RESELLER 3D", "callback_data": "/SHOPADD_PM 317"}],
            [{"text": "3D Price", "callback_data": "/SHOPADD_PM 312"}],
            [{"text": "RESELLER 7D", "callback_data": "/SHOPADD_PM 318"}],
            [{"text": "7D Price", "callback_data": "/SHOPADD_PM 313"}],
            [{"text": "RESELLER 14D", "callback_data": "/SHOPADD_PM 319"}],
            [{"text": "14D Price", "callback_data": "/SHOPADD_PM 314"}],
            [{"text": "RESELLER 21D", "callback_data": "/SHOPADD_PM 320"}],
            [{"text": "21D Price", "callback_data": "/SHOPADD_PM 315"}],
            [{"text": "Back", "callback_data": "/setshop_psue"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/SHOPADMIN_P3")
def cmd_shopadmin_p3(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    def get_old(day):
        price = bot_data.get_data(f"SILENT_{day}d_price") or 0
        reseller = bot_data.get_data(f"SILENT_{day}d_reseller_price") or 0
        return price, reseller
    
    p1, r1 = get_old(1)
    p3, r3 = get_old(3)
    p7, r7 = get_old(7)
    p14, r14 = get_old(14)
    p28, r28 = get_old(28)
    
    txt = (
        "SILENT CHEATS ANDROID\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"1D Reseller: ₹{r1}\n1D Price: ₹{p1}\n\n"
        f"3D Reseller: ₹{r3}\n3D Price: ₹{p3}\n\n"
        f"7D Reseller: ₹{r7}\n7D Price: ₹{p7}\n\n"
        f"14D Reseller: ₹{r14}\n14D Price: ₹{p14}\n\n"
        f"28D Reseller: ₹{r28}\n28D Price: ₹{p28}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\nSelect duration below:"
    )
    markup = {
        "inline_keyboard": [
            [{"text": "RESELLER 1D", "callback_data": "/SHOPADD_PM 221"}],
            [{"text": "1D Price", "callback_data": "/SHOPADD_PM 191"}],
            [{"text": "RESELLER 3D", "callback_data": "/SHOPADD_PM 22"}],
            [{"text": "3D Price", "callback_data": "/SHOPADD_PM 19"}],
            [{"text": "RESELLER 7D", "callback_data": "/SHOPADD_PM 23"}],
            [{"text": "7D Price", "callback_data": "/SHOPADD_PM 20"}],
            [{"text": "RESELLER 14D", "callback_data": "/SHOPADD_PM 24"}],
            [{"text": "14D Price", "callback_data": "/SHOPADD_PM 21"}],
            [{"text": "RESELLER 28D", "callback_data": "/SHOPADD_PM 225"}],
            [{"text": "28D Price", "callback_data": "/SHOPADD_PM 226"}],
            [{"text": "Back", "callback_data": "/setshop_psue"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/SHOPADD_PM")
def cmd_shopadd_pm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not params:
        send_message(user_id, "Usage: /SHOPADD_PM <number>")
        return True
    
    products = {
        "1": ("drip_1d_price", "DRIP CLIENT APK MOD\n1 Days"),
        "2": ("drip_3d_price", "DRIP CLIENT APK MOD\n3 Days"),
        "3": ("drip_7d_price", "DRIP CLIENT APK MOD\n7 Days"),
        "4": ("drip_15d_price", "DRIP CLIENT APK MOD\n15 Days"),
        "5": ("drip_30d_price", "DRIP CLIENT APK MOD\n30 Days"),
        "6": ("drip_1d_reseller_price", "RESELLER PANEL\nDRIP CLIENT APK MOD\n1 Days"),
        "7": ("drip_3d_reseller_price", "RESELLER PANEL\nDRIP CLIENT APK MOD\n3 Days"),
        "8": ("drip_7d_reseller_price", "RESELLER PANEL\nDRIP CLIENT APK MOD\n7 Days"),
        "9": ("drip_15d_reseller_price", "RESELLER PANEL\nDRIP CLIENT APK MOD\n15 Days"),
        "10": ("drip_30d_reseller_price", "RESELLER PANEL\nDRIP CLIENT APK MOD\n30 Days"),
        "19": ("SILENT_3d_price", "SILENT CHEATS ANDROID\n3 Days"),
        "20": ("SILENT_7d_price", "SILENT CHEATS ANDROID\n7 Days"),
        "21": ("SILENT_14d_price", "SILENT CHEATS ANDROID\n14 Days"),
        "22": ("SILENT_3d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n3 Days"),
        "23": ("SILENT_7d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n7 Days"),
        "24": ("SILENT_14d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n14 Days"),
        "191": ("SILENT_1d_price", "SILENT CHEATS ANDROID\n1 Days"),
        "221": ("SILENT_1d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n1 Days"),
        "225": ("SILENT_28d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n28 Days"),
        "226": ("SILENT_28d_price", "SILENT CHEATS ANDROID\n28 Days"),
        "311": ("HG_1d_price", "HG-CHEATS ANDROID\n1 Days"),
        "312": ("HG_3d_price", "HG-CHEATS ANDROID\n3 Days"),
        "313": ("HG_7d_price", "HG-CHEATS ANDROID\n7 Days"),
        "314": ("HG_14d_price", "HG-CHEATS ANDROID\n14 Days"),
        "315": ("HG_21d_price", "HG-CHEATS ANDROID\n21 Days"),
        "316": ("HG_1d_reseller_price", "RESELLER PANEL\nHG-CHEATS ANDROID\n1 Days"),
        "317": ("HG_3d_reseller_price", "RESELLER PANEL\nHG-CHEATS ANDROID\n3 Days"),
        "318": ("HG_7d_reseller_price", "RESELLER PANEL\nHG-CHEATS ANDROID\n7 Days"),
        "319": ("HG_14d_reseller_price", "RESELLER PANEL\nHG-CHEATS ANDROID\n14 Days"),
        "320": ("HG_21d_reseller_price", "RESELLER PANEL\nHG-CHEATS ANDROID\n21 Days"),
    }
    
    if params in products:
        data_name, title = products[params]
        User.save_data(user_id, "shopaddpm_options", {"key": data_name, "title": title})
        send_message(
            user_id,
            f"<b>{title}</b>\n\nSend key price (numbers only).\n\nType /cancel to stop.",
            "HTML"
        )
        pending_commands[user_id] = "/SHOPADD_PM2"
        pending_commands_store.set(user_id, "/SHOPADD_PM2")
    else:
        send_message(user_id, "Invalid option number.")
    return True

@command("/SHOPADD_PM2")
def cmd_shopadd_pm2(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    if text == "/cancel":
        send_message(user_id, "Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    opts = User.get_data(user_id, "shopaddpm_options")
    if not opts:
        send_message(user_id, "System Error")
        return True
    try:
        rate = float(text)
        price_key = opts.get("key")
        title = opts.get("title")
        bot_data.save_data(price_key, rate)
        send_message(
            user_id,
            f"Successfully Set\n\n{title} Price = ₹{rate}",
            "HTML"
        )
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
    except:
        send_message(
            user_id,
            "Invalid number.\nSend numeric value like 90\n\nType /cancel to stop.",
            "HTML"
        )
    return True

@command("/broadcast")
def cmd_broadcast(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        send_message(user_id, "<b>🚫 You Are Not This Bot Admin</b>", "HTML")
        return True
    
    all_users = user_data_store.get_all_users()
    send_message(
        user_id, 
        f"📢 <b>BROADCAST MODE</b>\n\n"
        f"👥 Total Users: {len(all_users)}\n\n"
        f"Send ANY message (text, photo, video, document).\n"
        f"<b>Your message will be FORWARDED to all users.</b>\n\n"
        f"Type /cancel to cancel.",
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
        return True
    
    users = user_data_store.get_all_users()
    if not users:
        send_message(user_id, "No users to broadcast to.", "HTML")
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
        except Exception as e:
            print(f"Forward error to {target_user}: {e}")
            try:
                if message.get("text"):
                    send_message(target_user, message.get("text", ""), "HTML")
                elif message.get("photo"):
                    send_photo(target_user, message["photo"][-1]["file_id"], caption=message.get("caption", ""))
                success += 1
            except:
                failed += 1
        time.sleep(0.1)
    
    send_message(
        user_id, 
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"📤 Sent to: {success}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {len(users)}",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

# ========== NUMBER PAD COMMANDS ==========

current_amount = {}

@command("/addpayment")
def cmd_addpayment(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    reply_markup = {
        "inline_keyboard": [
            [{"text": "1", "callback_data": "/num1"}, {"text": "2", "callback_data": "/num2"}, {"text": "3", "callback_data": "/num3"}],
            [{"text": "4", "callback_data": "/num4"}, {"text": "5", "callback_data": "/num5"}, {"text": "6", "callback_data": "/num6"}],
            [{"text": "7", "callback_data": "/num7"}, {"text": "8", "callback_data": "/num8"}, {"text": "9", "callback_data": "/num9"}],
            [{"text": "CLEAR", "callback_data": "/clearamt"}, {"text": "0", "callback_data": "/num0"}, {"text": "CONFIRM", "callback_data": "/done"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
        ]
    }
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹0\n\n"
        "Use the keypad below to enter amount."
    )
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/num0")
def cmd_num0(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt == "0":
        amt = "0"
    else:
        amt += "0"
    current_amount[user_id] = amt
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num1")
def cmd_num1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt == "0":
        amt = "1"
    else:
        amt += "1"
    current_amount[user_id] = amt
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num2")
def cmd_num2(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt == "0":
        amt = "2"
    else:
        amt += "2"
    current_amount[user_id] = amt
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num3")
def cmd_num3(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt == "0":
        amt = "3"
    else:
        amt += "3"
    current_amount[user_id] = amt
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num4")
def cmd_num4(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt == "0":
        amt = "4"
    else:
        amt += "4"
    current_amount[user_id] = amt
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num5")
def cmd_num5(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt == "0":
        amt = "5"
    else:
        amt += "5"
    current_amount[user_id] = amt
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num6")
def cmd_num6(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt == "0":
        amt = "6"
    else:
        amt += "6"
    current_amount[user_id] = amt
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num7")
def cmd_num7(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt == "0":
        amt = "7"
    else:
        amt += "7"
    current_amount[user_id] = amt
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num8")
def cmd_num8(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt == "0":
        amt = "8"
    else:
        amt += "8"
    current_amount[user_id] = amt
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num9")
def cmd_num9(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt == "0":
        amt = "9"
    else:
        amt += "9"
    current_amount[user_id] = amt
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/clearamt")
def cmd_clearamt(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    text = (
        "<blockquote>"
        "💰 ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹0\n\n"
        "Use the keypad below to enter amount."
    )
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/done")
def cmd_done(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    amt = current_amount.get(user_id, "0")
    if not amt or amt == "0":
        send_message(user_id, "Enter amount first")
        return True
    User.save_data(user_id, "last_deposit_amount", float(amt))
    cmd_addpayment_qr(message)
    return True

def cmd_addpayment_qr(message):
    user_id = message.get("from", {}).get("id")
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
        f"<blockquote>💰 PAYMENT QR GENERATED</blockquote>\n"
        f"Scan the QR and complete payment.\n\n"
        f"Amount: ₹{amount}\n\n"
        f"🧾 <b>Order ID:</b>\n"
        f"<code>{order_id}</code>\n\n"
        f"<i>After payment, tap VERIFY PAYMENT button below.</i>"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ VERIFY PAYMENT", "callback_data": f"/verify_payment {order_id}"}],
            [{"text": "❌ CANCEL", "callback_data": f"/cancel {order_id}"}]
        ]
    }
    send_photo(user_id, qr_url, caption, "HTML", reply_markup)

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
    print("Bot Started with MongoDB & Reseller API Integration!")
    print(f"Connected to MongoDB: {DB_NAME}")
    print(f"API Endpoint: {RESELLER_API_URL}")
    print(f"Registered commands: {list(commands.keys())}")
    
    last_update_id = 0
    while True:
        try:
            updates = get_updates(last_update_id + 1)
            if updates:
                print(f"Received {len(updates)} updates")
            for update in updates:
                if "update_id" in update:
                    last_update_id = update["update_id"]
                handle_update(update)
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("Bot stopped.")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
