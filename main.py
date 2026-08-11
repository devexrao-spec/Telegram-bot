# tusharbot.py - COMPLETE FIXED VERSION (USER-SPECIFIC PAYMENT)
import requests
import json
import time
from datetime import datetime
import threading
from pymongo import MongoClient

BOT_TOKEN = "8856781249:AAGdDzOkkxo5cSB2u_e65XWxhxbrgs5f3Ps"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

FAMPAY_API_KEY = "FAM_4F0288181BA4D5F83D16AF7EF1F06A1FA4362C5D"
FAMPAY_BASE_URL = "https://fampaygateway.site/api/"

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
        doc = {
            "user_id": str(user_id),
            "data": data,
            "timestamp": datetime.now()
        }
        self.collection.update_one(
            {"user_id": str(user_id)},
            {"$set": doc},
            upsert=True
        )
    
    def delete(self, user_id):
        self.collection.delete_one({"user_id": str(user_id)})
    
    def get_all(self):
        docs = self.collection.find()
        result = {}
        for doc in docs:
            user_id = doc.get("user_id")
            data = doc.get("data")
            if user_id and data:
                result[user_id] = data
        return result

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
    
    def get_user_payment(self, user_id, order_id):
        return self.collection.find_one({"user_id": str(user_id), "order_id": order_id})
    
    def get_user_payments(self, user_id):
        return list(self.collection.find({"user_id": str(user_id)}))

processed_payments_store = ProcessedPaymentsStore()

# ========== NEW: Payment Orders Store ==========
class PaymentOrdersStore:
    """
    This stores the mapping between order_id and user_id.
    When a payment is verified, we check this mapping to ensure
    the order belongs to the user who is verifying it.
    """
    def __init__(self):
        self.collection = mongo.get_collection('payment_orders')
    
    def create(self, order_id, user_id, amount, product_name=None):
        """Create a new payment order mapping"""
        doc = {
            "order_id": order_id,
            "user_id": str(user_id),
            "amount": amount,
            "product_name": product_name,
            "created_at": datetime.now(),
            "status": "pending"
        }
        self.collection.update_one(
            {"order_id": order_id},
            {"$set": doc},
            upsert=True
        )
        print(f"📝 Created payment order mapping: order={order_id} -> user={user_id}")
        return doc
    
    def get_user_by_order(self, order_id):
        """Get the user_id for a given order_id"""
        doc = self.collection.find_one({"order_id": order_id})
        if doc:
            return doc.get("user_id")
        return None
    
    def get_order(self, order_id):
        """Get full order data"""
        return self.collection.find_one({"order_id": order_id})
    
    def mark_verified(self, order_id):
        """Mark order as verified"""
        self.collection.update_one(
            {"order_id": order_id},
            {"$set": {"status": "verified", "verified_at": datetime.now()}}
        )
    
    def delete(self, order_id):
        """Delete an order mapping (for cancellation)"""
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
        user_id = doc.get("user_id")
        data = doc.get("data")
        if user_id and data:
            pending_payments[user_id] = data

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
    try:
        return requests.post(url, json={"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id}).json()
    except:
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
    "6": "1 Day",
    "7": "3 Days",
    "8": "7 Days",
    "9": "14 Days",
    "15": "28 Days",
}

# ====== FIXED: VERIFY PAYMENT - USER SPECIFIC ======
def verify_payment(user_id, order_id, msg_id=None):
    try:
        user_id = str(user_id)
        
        print(f"🔍 Verifying: User={user_id}, Order={order_id}")
        
        # ========== STEP 1: Check if order belongs to this user from payment_orders ==========
        order_owner = payment_orders_store.get_user_by_order(order_id)
        
        if not order_owner:
            print(f"❌ Order {order_id} not found in payment_orders mapping")
            if processed_payments_store.exists(order_id):
                print(f"❌ Order {order_id} already processed but no mapping found")
                pending_payments.pop(user_id, None)
                pending_payments_store.delete(user_id)
                return False, 0, None
            return False, 0, None
        
        # ========== STEP 2: Verify the user is the owner of this order ==========
        if str(order_owner) != str(user_id):
            print(f"❌ CRITICAL: Order {order_id} belongs to user {order_owner}, but {user_id} is trying to verify it!")
            return False, 0, None
        
        # ========== STEP 3: Check if already processed ==========
        if processed_payments_store.exists(order_id):
            print(f"❌ Order {order_id} already processed globally")
            pending_payments.pop(user_id, None)
            pending_payments_store.delete(user_id)
            return False, 0, None
        
        # ========== STEP 4: Check if user has pending payment ==========
        pending = pending_payments_store.get(user_id)
        if not pending:
            print(f"❌ No pending payment for user {user_id}")
            return False, 0, None
        
        if isinstance(pending, dict):
            stored_order_id = pending.get("order_id")
            stored_user_id = pending.get("user_id")
        else:
            stored_order_id = pending
            stored_user_id = user_id
            
        if stored_order_id != order_id:
            print(f"❌ Order mismatch: user {user_id} has {stored_order_id}, trying {order_id}")
            return False, 0, None
        
        # ========== STEP 5: Verify with API ==========
        url = f"{FAMPAY_BASE_URL}verify.php?order_id={order_id}&api_key={FAMPAY_API_KEY}"
        print(f"📡 Checking API for user {user_id}: {url}")
        
        try:
            response = requests.get(url, timeout=30)
        except requests.Timeout:
            print(f"⏰ Timeout for user {user_id}, order {order_id}")
            return False, 0, None
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"📊 API Response for user {user_id}: {data}")
            except:
                return False, 0, None
                
            if data.get("status") == "success":
                amount = float(data["data"]["amount"])
                actual_order_id = data["data"].get("order_id", order_id)
                
                # ========== STEP 6: Mark as processed for THIS SPECIFIC USER ==========
                processed_payments_store.add(actual_order_id, user_id, amount)
                
                # ========== STEP 7: Mark order as verified in payment_orders ==========
                payment_orders_store.mark_verified(actual_order_id)
                
                # ========== STEP 8: Add balance to THIS SPECIFIC USER ==========
                bal = Resources.another_res("Balance", user=user_id)
                bal.add(amount)
                print(f"✅ Added ₹{amount} to user {user_id}, new balance: ₹{bal.value()}")
                
                User.save_data(user_id, "last_order_id", "")
                User.save_data(user_id, "addpay_order_id", "")
                
                pending_payments.pop(user_id, None)
                pending_payments_store.delete(user_id)
                
                if msg_id:
                    try:
                        delete_message(user_id, msg_id)
                    except:
                        pass
                
                send_message(
                    user_id,
                    f"<tg-emoji emoji-id='5348129380474306311'>✅</tg-emoji> <b>Payment Success!</b>\n\n"
                    f"<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> Added: ₹{amount}\n"
                    f"<tg-emoji emoji-id='5346227465876423936'>💳</tg-emoji> New Balance: ₹{bal.value()}\n\n"
                    f"<i>Thank you for your payment!</i>",
                    "HTML"
                )
                
                admins = bot_data.get_data("AllBotAdminss") or []
                for admin in admins:
                    send_message(
                        admin,
                        f"<tg-emoji emoji-id='5348129380474306311'>✅</tg-emoji> New Payment Received!\n\n"
                        f"👤 User ID: <code>{user_id}</code>\n"
                        f"💰 Amount: ₹{amount}\n"
                        f"🧾 Order ID: <code>{actual_order_id}</code>\n"
                        f"💳 User Balance: ₹{bal.value()}",
                        "HTML"
                    )
                
                return True, amount, bal.value()
            else:
                print(f"⚠️ API said not success for user {user_id}")
                return False, 0, None
        else:
            print(f"⚠️ API status code: {response.status_code}")
            return False, 0, None
    except Exception as e:
        print(f"❌ Verify payment error for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, None

# ====== COMMANDS ======

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
            [{"text": "BUY HACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": "6093739864883207194", "style": "success"}],
            [
                {"text": "MY KEY", "callback_data": "/orderksk", "icon_custom_emoji_id": "5967456680940671207", "style": "success"},
                {"text": "PROFILE", "callback_data": "/profilemmm", "icon_custom_emoji_id": "5346136537123801643", "style": "success"}
            ],
            [
                {"text": "HOW TO USE", "callback_data": "/spinj", "icon_custom_emoji_id": "5345783284653636765", "style": "success"},
                {"text": "SUPPORT", "callback_data": "/supportj", "icon_custom_emoji_id": "5897567714674741148", "style": "success"}
            ],
            [{"text": "ADD FUND", "callback_data": "/addpayment", "icon_custom_emoji_id": "6278302366303260172", "style": "success"}],
            [
                {"text": "PAY PROOF", "url": "https://t.me/subhajit_feedback", "icon_custom_emoji_id": "5258134813302332906", "style": "success"},
                {"text": "DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl", "icon_custom_emoji_id": "6028115612163641653", "style": "success"}
            ]
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
<tg-emoji emoji-id="6093562529978522804">🛒</tg-emoji> <b>PANNEL STORE — SHOP</b>
━━━━━━━━━━━━━━━━━━━━

<tg-emoji emoji-id="6179339404906079822">📦</tg-emoji> Choose a product:
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": "DRIP CLIENT NON-ROOT", "callback_data": "/SHOP_P1", "icon_custom_emoji_id": "6323104647636589287", "style": "success"}],
            [{"text": "SILENT CHEATS ANDROID", "callback_data": "/SHOP_P2", "icon_custom_emoji_id": "6325561995995126107", "style": "success"}],
            [{"text": "PRIME HOOK", "callback_data": "/SHOP_P4", "icon_custom_emoji_id": "6210705396449944693", "style": "success"}],
            [{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]
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
            [{"text": "BUY HACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": "6093739864883207194", "style": "success"}],
            [
                {"text": "MY KEY", "callback_data": "/orderksk", "icon_custom_emoji_id": "5967456680940671207", "style": "success"},
                {"text": "PROFILE", "callback_data": "/profilemmm", "icon_custom_emoji_id": "5346136537123801643", "style": "success"}
            ],
            [
                {"text": "HOW TO USE", "callback_data": "/spinj", "icon_custom_emoji_id": "5345783284653636765", "style": "success"},
                {"text": "SUPPORT", "callback_data": "/supportj", "icon_custom_emoji_id": "5897567714674741148", "style": "success"}
            ],
            [{"text": "ADD FUND", "callback_data": "/addpayment", "icon_custom_emoji_id": "6278302366303260172", "style": "success"}],
            [
                {"text": "PAY PROOF", "url": "https://t.me/subhajit_feedback", "icon_custom_emoji_id": "5258134813302332906", "style": "success"},
                {"text": "DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl", "icon_custom_emoji_id": "6028115612163641653", "style": "success"}
            ]
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
        "<tg-emoji emoji-id='6323104647636589287'>📦</tg-emoji> "
        "𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗"
        "<tg-emoji emoji-id='6179339404906079822'>✅</tg-emoji> "
        "( 𝘉𝘌𝘚𝘛 𝘚𝘌𝘓𝘓𝘌𝘙"
        "<tg-emoji emoji-id='5841693351249710667'>💫</tg-emoji> )\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<i><tg-emoji emoji-id='5258134813302332906'>📦</tg-emoji> Extra 2% discount applied</i>\n"
        "Choose a plan <tg-emoji emoji-id='5258336354642697821'>👇</tg-emoji>"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": f"1 DAY - ₹{p1}", "callback_data": f"{buy_cmd} 1", "style": "success"}],
            [{"text": f"3 DAYS - ₹{p3}", "callback_data": f"{buy_cmd} 2", "style": "success"}],
            [{"text": f"7 DAYS - ₹{p7}", "callback_data": f"{buy_cmd} 3", "style": "success"}],
            [{"text": f"15 DAYS - ₹{p15}", "callback_data": f"{buy_cmd} 4", "style": "success"}],
            [{"text": f"30 DAYS - ₹{p30}", "callback_data": f"{buy_cmd} 5", "style": "success"}],
            [{"text": "BACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]
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
<tg-emoji emoji-id="6325561995995126107">📦</tg-emoji> SILENT CHEATS ANDROID
━━━━━━━━━━━━━━━━━━━━

Choose a plan <tg-emoji emoji-id="5258336354642697821">👇</tg-emoji>
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": f"1 Day - ₹{p1}", "callback_data": f"{buy_cmd} 6", "style": "success"}],
            [{"text": f"3 Days - ₹{p3}", "callback_data": f"{buy_cmd} 7", "style": "success"}],
            [{"text": f"7 Days - ₹{p7}", "callback_data": f"{buy_cmd} 8", "style": "success"}],
            [{"text": f"14 Days - ₹{p14}", "callback_data": f"{buy_cmd} 9", "style": "success"}],
            [{"text": f"28 Days - ₹{p28}", "callback_data": f"{buy_cmd} 15", "style": "success"}],
            [{"text": "BACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]
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
<tg-emoji emoji-id="6210705396449944693">🔥</tg-emoji> PRIME HOOK
━━━━━━━━━━━━━━━━━━━━

Choose a plan <tg-emoji emoji-id="5258336354642697821">👇</tg-emoji>
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": f"1 Day - ₹{p1}", "callback_data": f"{buy_cmd} 10", "style": "success"}],
            [{"text": f"3 Days - ₹{p3}", "callback_data": f"{buy_cmd} 11", "style": "success"}],
            [{"text": f"7 Days - ₹{p7}", "callback_data": f"{buy_cmd} 12", "style": "success"}],
            [{"text": f"14 Days - ₹{p14}", "callback_data": f"{buy_cmd} 13", "style": "success"}],
            [{"text": f"21 Days - ₹{p21}", "callback_data": f"{buy_cmd} 14", "style": "success"}],
            [{"text": "BACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]
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
        "1": ("drip_1d_price", "drip_1d_keys", "DRIP CLIENT APK MOD\n1 Day"),
        "2": ("drip_3d_price", "drip_3d_keys", "DRIP CLIENT APK MOD\n3 Days"),
        "3": ("drip_7d_price", "drip_7d_keys", "DRIP CLIENT APK MOD\n7 Days"),
        "4": ("drip_15d_price", "drip_15d_keys", "DRIP CLIENT APK MOD\n15 Days"),
        "5": ("drip_30d_price", "drip_30d_keys", "DRIP CLIENT APK MOD\n30 Days"),
        "6": ("SILENT_1d_price", "SILENT_1d_keys", "SILENT CHEATS ANDROID\n1 Day"),
        "7": ("SILENT_3d_price", "SILENT_3d_keys", "SILENT CHEATS ANDROID\n3 Days"),
        "8": ("SILENT_7d_price", "SILENT_7d_keys", "SILENT CHEATS ANDROID\n7 Days"),
        "9": ("SILENT_14d_price", "SILENT_14d_keys", "SILENT CHEATS ANDROID\n14 Days"),
        "10": ("HG_1d_price", "HG_1d_keys", "PRIME-HOOK\n1 Day"),
        "11": ("HG_3d_price", "HG_3d_keys", "PRIME-HOOK\n3 Days"),
        "12": ("HG_7d_price", "HG_7d_keys", "PRIME-HOOK\n7 Days"),
        "13": ("HG_14d_price", "HG_14d_keys", "PRIME-HOOK\n14 Days"),
        "14": ("HG_21d_price", "HG_21d_keys", "PRIME-HOOK\n21 Days"),
        "15": ("SILENT_28d_price", "SILENT_28d_keys", "SILENT CHEATS ANDROID\n28 Days"),
    }
    if params in product_map:
        price_key, key_key, title = product_map[params]
        User.save_data(user_id, "last_product1", title)
        User.save_data(user_id, "last_plan", params)
        cmd_buybahha(message, None, {"price": price_key, "key": key_key, "title": title})
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
        "1": ("drip_1d_reseller_price", "drip_1d_keys", "DRIP CLIENT APK MOD\n1 Day"),
        "2": ("drip_3d_reseller_price", "drip_3d_keys", "DRIP CLIENT APK MOD\n3 Days"),
        "3": ("drip_7d_reseller_price", "drip_7d_keys", "DRIP CLIENT APK MOD\n7 Days"),
        "4": ("drip_15d_reseller_price", "drip_15d_keys", "DRIP CLIENT APK MOD\n15 Days"),
        "5": ("drip_30d_reseller_price", "drip_30d_keys", "DRIP CLIENT APK MOD\n30 Days"),
        "6": ("SILENT_1d_reseller_price", "SILENT_1d_keys", "SILENT CHEATS ANDROID\n1 Day"),
        "7": ("SILENT_3d_reseller_price", "SILENT_3d_keys", "SILENT CHEATS ANDROID\n3 Days"),
        "8": ("SILENT_7d_reseller_price", "SILENT_7d_keys", "SILENT CHEATS ANDROID\n7 Days"),
        "9": ("SILENT_14d_reseller_price", "SILENT_14d_keys", "SILENT CHEATS ANDROID\n14 Days"),
        "10": ("HG_1d_reseller_price", "HG_1d_keys", "PRIME-HOOK\n1 Day"),
        "11": ("HG_3d_reseller_price", "HG_3d_keys", "PRIME-HOOK\n3 Days"),
        "12": ("HG_7d_reseller_price", "HG_7d_keys", "PRIME-HOOK\n7 Days"),
        "13": ("HG_14d_reseller_price", "HG_14d_keys", "PRIME-HOOK\n14 Days"),
        "14": ("HG_21d_reseller_price", "HG_21d_keys", "PRIME-HOOK\n21 Days"),
        "15": ("SILENT_28d_reseller_price", "SILENT_28d_keys", "SILENT CHEATS ANDROID\n28 Days"),
    }
    if params in product_map:
        price_key, key_key, title = product_map[params]
        cmd_buybahha(message, None, {"price": price_key, "key": key_key, "title": title})
    else:
        send_message(user_id, "Invalid Product ID")
    return True

@command("/buybahha")
def cmd_buybahha(message, params, options):
    user_id = message.get("from", {}).get("id")
    if not options:
        send_message(user_id, "Product configuration error.")
        return True
    price_key = options.get("price")
    key_key = options.get("key")
    title = options.get("title")
    if not price_key or not key_key or not title:
        send_message(user_id, "Product configuration error.")
        return True
    price = bot_data.get_data(price_key) or 0
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
        f"<tg-emoji emoji-id='6172208745582433583'>🛒</tg-emoji> {title}\n\n"
        f"<tg-emoji emoji-id='6005570495603282482'>🔑</tg-emoji> <b>Your Key:</b>\n<code>{key}</code>\n\n"
        f"<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> Deducted: ₹{price}\n"
        f"<tg-emoji emoji-id='5967456680940671207'>📦</tg-emoji> Remaining Stock: {len(keys)}\n"
        f"<tg-emoji emoji-id='6278102040438640835'>📦</tg-emoji> Time: {easy_time}\n\n"
        f"<tg-emoji emoji-id='6264989131621798851'>📢</tg-emoji> <b>ALL FILES UPDATE</b>\n"
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

# ====== FIXED: AUTOBUY1 - USER-SPECIFIC QR ======
@command("/autobuy1")
def cmd_autobuy1(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
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
    
    url = f"{FAMPAY_BASE_URL}create_order.php?amount={amount}&api_key={FAMPAY_API_KEY}"
    try:
        print(f"📡 Creating order for user {user_id}: {url}")
        response = requests.get(url, timeout=30)
        data = response.json()
    except Exception as e:
        send_message(user_id, f"API ERROR: {str(e)}")
        return True
        
    if not data or data.get("status") != "success":
        send_message(user_id, f"QR GENERATION FAILED")
        return True
        
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    # ========== CRITICAL: Store order_id -> user_id mapping ==========
    payment_orders_store.create(
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        product_name=pt
    )
    print(f"📝 Stored mapping: order {order_id} -> user {user_id}")
    
    User.save_data(user_id, "last_order_id", order_id)
    
    pending_data = {
        "order_id": order_id,
        "msg_id": message.get("message_id"),
        "user_id": str(user_id)
    }
    pending_payments[user_id] = pending_data
    pending_payments_store.set(user_id, pending_data)
    
    print(f"✅ Created order {order_id} for user {user_id}")
    
    caption = (
        f"<blockquote><tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> INSUFFICIENT BALANCE</blockquote>\n\n"
        f"┣ Product: {pt}\n"
        f"┣ Plan: {plan_display}\n"
        f"┣ Price: ₹{amount}\n"
        f"┣ Your Balance: ₹{balance}\n"
        f"┗ Need: ₹{need}\n\n"
        f"Scan the QR and complete payment.\n\n"
        f"<tg-emoji emoji-id='5327947823071664175'>🧾</tg-emoji> <b>Order ID:</b> <code>{order_id}</code>\n\n"
        f"<i>After payment, tap VERIFY PAYMENT button below.</i>"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "VERIFY PAYMENT", "callback_data": f"/verify_payment {order_id}", "icon_custom_emoji_id": "6278302366303260172", "style": "success"}],
            [{"text": "CANCEL", "callback_data": "/cancel", "icon_custom_emoji_id": "6278116707751956084", "style": "danger"}]
        ]
    }
    send_photo(user_id, qr_url, caption, "HTML", reply_markup)
    return True

# ====== FIXED: VERIFY PAYMENT COMMAND ======
@command("/verify_payment")
def cmd_verify_payment(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    msg_id = message.get("message_id")
    
    order_id = params
    
    if not order_id:
        send_message(user_id, "No order ID found.", "HTML")
        return True
    
    print(f"🔍 User {user_id} verifying order {order_id}")
    
    # ========== STEP 1: Check if order exists in payment_orders ==========
    order_data = payment_orders_store.get_order(order_id)
    if not order_data:
        send_message(user_id, "Invalid order ID.", "HTML")
        return True
    
    # ========== STEP 2: Check if order belongs to this user ==========
    order_owner = order_data.get("user_id")
    if str(order_owner) != str(user_id):
        send_message(user_id, "❌ This order does not belong to you!", "HTML")
        return True
    
    # ========== STEP 3: Check if already processed ==========
    if processed_payments_store.exists(order_id):
        send_message(user_id, "This payment has already been processed.", "HTML")
        pending_payments.pop(user_id, None)
        pending_payments_store.delete(user_id)
        return True
    
    # ========== STEP 4: Check if user has pending payment ==========
    pending = pending_payments_store.get(user_id)
    if not pending:
        send_message(user_id, "No pending payment found for you.", "HTML")
        return True
    
    if isinstance(pending, dict):
        stored_order_id = pending.get("order_id")
    else:
        stored_order_id = pending
        
    if stored_order_id != order_id:
        send_message(user_id, "This order ID does not match your pending payment.", "HTML")
        return True
    
    send_message(user_id, "<tg-emoji emoji-id='5348374038991357363'>⏳</tg-emoji> Checking payment status...", "HTML")
    
    success, amount, new_balance = verify_payment(user_id, order_id, msg_id)
    
    if not success:
        if processed_payments_store.exists(order_id):
            send_message(user_id, "This payment has already been processed.", "HTML")
        else:
            send_message(
                user_id,
                f"<tg-emoji emoji-id='6278116707751956084'>❌</tg-emoji> <b>Payment Not Found</b>\n\n"
                f"Please complete the payment first.\n"
                f"Order ID: <code>{order_id}</code>\n\n"
                f"After completing payment, tap verify again.",
                "HTML"
            )
    
    return True

# ====== FIXED: CANCEL COMMAND ======
@command("/cancel")
def cmd_cancel(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    msg_id = message.get("message_id")
    
    pending = pending_payments_store.get(user_id)
    if pending:
        if isinstance(pending, dict):
            order_id = pending.get("order_id")
        else:
            order_id = pending
        if order_id:
            payment_orders_store.delete(order_id)
            print(f"🗑️ Deleted order mapping for {order_id}")
    
    delete_message(user_id, msg_id)
    pending_payments.pop(user_id, None)
    pending_payments_store.delete(user_id)
    User.save_data(user_id, "last_order_id", "")
    User.save_data(user_id, "addpay_order_id", "")
    send_message(user_id, "<tg-emoji emoji-id='6278116707751956084'>❌</tg-emoji> Cancelled", "HTML")
    return True

current_amount = {}

@command("/addpayment")
def cmd_addpayment(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "1", "callback_data": "/num1", "style": "success"},
                {"text": "2", "callback_data": "/num2", "style": "success"},
                {"text": "3", "callback_data": "/num3", "style": "success"}
            ],
            [
                {"text": "4", "callback_data": "/num4", "style": "success"},
                {"text": "5", "callback_data": "/num5", "style": "success"},
                {"text": "6", "callback_data": "/num6", "style": "success"}
            ],
            [
                {"text": "7", "callback_data": "/num7", "style": "success"},
                {"text": "8", "callback_data": "/num8", "style": "success"},
                {"text": "9", "callback_data": "/num9", "style": "success"}
            ],
            [
                {"text": "CLEAR", "callback_data": "/clearamt", "style": "danger"},
                {"text": "0", "callback_data": "/num0", "style": "success"},
                {"text": "CONFIRM", "callback_data": "/done", "style": "success"}
            ],
            [{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]
        ]
    }
    text = (
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
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

# ====== FIXED: ADDPAYMENT QR - USER-SPECIFIC ======
def cmd_addpayment_qr(message):
    user_id = str(message.get("from", {}).get("id"))
    amount = User.get_data(user_id, "last_deposit_amount")
    if not amount:
        send_message(user_id, "Amount missing")
        return
    
    url = f"{FAMPAY_BASE_URL}create_order.php?amount={amount}&api_key={FAMPAY_API_KEY}"
    try:
        response = requests.get(url, timeout=30)
        data = response.json()
    except Exception as e:
        send_message(user_id, f"API ERROR: {str(e)}")
        return
        
    if data.get("status") != "success":
        send_message(user_id, f"QR GENERATION FAILED")
        return
        
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    # ========== CRITICAL: Store order_id -> user_id mapping ==========
    payment_orders_store.create(
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        product_name="Add Funds"
    )
    print(f"📝 Stored mapping: order {order_id} -> user {user_id} (addfunds)")
    
    User.save_data(user_id, "addpay_order_id", order_id)
    
    pending_data = {
        "order_id": order_id,
        "msg_id": message.get("message_id"),
        "user_id": str(user_id)
    }
    pending_payments[user_id] = pending_data
    pending_payments_store.set(user_id, pending_data)
    
    print(f"✅ Created order {order_id} for user {user_id} (addpayment)")
    
    caption = (
        f"<blockquote><tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> PAYMENT QR GENERATED</blockquote>\n"
        f"Scan the QR and complete payment.\n\n"
        f"Amount: ₹{amount}\n\n"
        f"<tg-emoji emoji-id='5327947823071664175'>🧾</tg-emoji> <b>Order ID:</b> <code>{order_id}</code>\n\n"
        f"<i>After payment, tap VERIFY PAYMENT button below.</i>"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "VERIFY PAYMENT", "callback_data": f"/verify_payment {order_id}", "icon_custom_emoji_id": "6278302366303260172", "style": "success"}],
            [{"text": "CANCEL", "callback_data": "/cancel", "icon_custom_emoji_id": "6278116707751956084", "style": "danger"}]
        ]
    }
    send_photo(user_id, qr_url, caption, "HTML", reply_markup)

@command("/verify_addpay")
def cmd_verify_addpay(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    order_id = User.get_data(user_id, "addpay_order_id")
    if not order_id:
        send_message(user_id, "No active payment found.")
        return True
    
    order_owner = payment_orders_store.get_user_by_order(order_id)
    if str(order_owner) != str(user_id):
        send_message(user_id, "This order does not belong to you!")
        User.save_data(user_id, "addpay_order_id", "")
        return True
    
    if processed_payments_store.exists(order_id):
        send_message(user_id, "This payment has already been processed.")
        User.save_data(user_id, "addpay_order_id", "")
        pending_payments.pop(user_id, None)
        pending_payments_store.delete(user_id)
        return True
    
    success, amount, new_balance = verify_payment(user_id, order_id, message.get("message_id"))
    
    if not success:
        send_message(user_id, "Payment Not Received")
    return True

@command("/orderksk")
def cmd_orderksk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    textn = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<tg-emoji emoji-id='6008118472066732010'>📦</tg-emoji> <b>MY ORDERS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "You haven't placed any orders yet.\n"
        "Tap <tg-emoji emoji-id='6093562529978522804'>🛒</tg-emoji> Shop Now to get started!"
    )
    adm_ac = User.get_data(user_id, "userhAC") or []
    if not adm_ac:
        reply_markup = {"inline_keyboard": [[{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]]}
        try:
            edit_message(user_id, msg_id, textn, "HTML", reply_markup)
        except:
            send_message(user_id, textn, "HTML", reply_markup)
    else:
        latest_10 = adm_ac[-10:][::-1]
        safe_list = [str(item) for item in latest_10 if item]
        if safe_list:
            text = "\n\n".join(safe_list)
            reply_markup = {"inline_keyboard": [[{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]]}
            try:
                edit_message(user_id, msg_id, text, reply_markup=reply_markup)
            except:
                send_message(user_id, text, reply_markup=reply_markup)
    return True

@command("/profilemmm")
def cmd_profilemmm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
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
        "<tg-emoji emoji-id='5346136537123801643'>👤</tg-emoji> YOUR PROFILE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<tg-emoji emoji-id='6008118472066732010'>📛</tg-emoji> Name: {first_name}\n"
        f"<tg-emoji emoji-id='5841693351249710667'>🆔</tg-emoji> User ID: {user_id}\n"
        f"<tg-emoji emoji-id='5348374038991357363'>💰</tg-emoji> Balance: ₹{balance}\n"
        f"<tg-emoji emoji-id='5348490024583185697'>📅</tg-emoji> Member Since: {member_since}\n"
        f"<tg-emoji emoji-id='6093562529978522804'>🛒</tg-emoji> Total Orders: {orders}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "BUY HACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": "6093739864883207194", "style": "success"},
                {"text": "MY KEYS", "callback_data": "/orderksk", "icon_custom_emoji_id": "5967456680940671207", "style": "success"}
            ],
            [{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]
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
    text = """
<tg-emoji emoji-id='5368653135101310687'>🎥</tg-emoji> <b>Watch the full tutorial video below</b>

<tg-emoji emoji-id='6222198028854367391'>👇</tg-emoji>
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": "Watch Tutorial", "url": "https://t.me/hehehehhhsljg/162", "icon_custom_emoji_id": "6179339404906079822", "style": "success"}],
            [{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]
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
<tg-emoji emoji-id='5891120964468480450'>💬</tg-emoji> <b>Support — Seller</b> <tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji>
━━━━━━━━━━━━━━━━━━━━

Need help? We're here for you! <tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji>

📩 <b>Telegram:</b> <tg-emoji emoji-id='5776182936638329359'>⭐</tg-emoji>

<a href="https://t.me/UR_SUBHAJIT0">𝐒υвʜᴀᎫιт</a> <tg-emoji emoji-id='6118314396440596568'>⭐</tg-emoji>

<tg-emoji emoji-id='5891120964468480450'>💡</tg-emoji> <i>Include your User ID (from Profile)
when contacting for faster help.</i>
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": "WHATSAPP", "url": "https://wa.me/917908696630", "icon_custom_emoji_id": "6109296665926047025", "style": "success"}],
            [{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

# ====== ADMIN COMMANDS ======

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
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
        return True
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
            [{"text": "📊 Shop setup", "callback_data": "/setshop_psue", "style": "success"}],
            [{"text": "💰 Add Reseller", "callback_data": "/addreseller", "style": "success"}, {"text": "⛔ Remove Reseller", "callback_data": "/removereseller", "style": "danger"}],
            [{"text": "📝 Reseller List", "callback_data": "/resellerlist", "style": "success"}]
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
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
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
    markup["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "/admin AP", "style": "danger"}])
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
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
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
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
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
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
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
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
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
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
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
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
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
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
        return True
    markup = {
        "inline_keyboard": [
            [{"text": "DRIP CLIENT MOD", "callback_data": "/SHOPADMIN_P1", "style": "success"}],
            [{"text": "SILENT CHEATS ANDROID", "callback_data": "/SHOPADMIN_P3", "style": "success"}],
            [{"text": "PRIME MOD", "callback_data": "/SHOPADMIN_P2", "style": "success"}],
            [{"text": "Back", "callback_data": "/admin AP", "style": "danger"}]
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
        stock = bot_data.get_data(f"drip_{day}d_keys") or []
        if not stock:
            st = "Out of Stock"
        elif len(stock) <= 2:
            st = f"Only {len(stock)} left!"
        else:
            st = "In Stock"
        return price, reseller, st
    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p15, r15, s15 = get_old(15)
    p30, r30, s30 = get_old(30)
    txt = (
        "DRIP CLIENT MOD\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"1D Reseller: ₹{r1}\n1D Price: ₹{p1}\n{s1}\n\n"
        f"3D Reseller: ₹{r3}\n3D Price: ₹{p3}\n{s3}\n\n"
        f"7D Reseller: ₹{r7}\n7D Price: ₹{p7}\n{s7}\n\n"
        f"15D Reseller: ₹{r15}\n15D Price: ₹{p15}\n{s15}\n\n"
        f"30D Reseller: ₹{r30}\n30D Price: ₹{p30}\n{s30}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\nSelect duration below:"
    )
    markup = {
        "inline_keyboard": [
            [{"text": "RESELLER 1D", "callback_data": "/SHOPADD_PM 6", "style": "success"}],
            [{"text": "1D Price", "callback_data": "/SHOPADD_PM 1", "style": "success"}, {"text": "Add 1D Key", "callback_data": "/SHOPADDKEY 1", "style": "success"}],
            [{"text": "RESELLER 3D", "callback_data": "/SHOPADD_PM 7", "style": "success"}],
            [{"text": "3D Price", "callback_data": "/SHOPADD_PM 2", "style": "success"}, {"text": "Add 3D Key", "callback_data": "/SHOPADDKEY 2", "style": "success"}],
            [{"text": "RESELLER 7D", "callback_data": "/SHOPADD_PM 8", "style": "success"}],
            [{"text": "7D Price", "callback_data": "/SHOPADD_PM 3", "style": "success"}, {"text": "Add 7D Key", "callback_data": "/SHOPADDKEY 3", "style": "success"}],
            [{"text": "RESELLER 15D", "callback_data": "/SHOPADD_PM 9", "style": "success"}],
            [{"text": "15D Price", "callback_data": "/SHOPADD_PM 4", "style": "success"}, {"text": "Add 15D Key", "callback_data": "/SHOPADDKEY 4", "style": "success"}],
            [{"text": "RESELLER 30D", "callback_data": "/SHOPADD_PM 10", "style": "success"}],
            [{"text": "30D Price", "callback_data": "/SHOPADD_PM 5", "style": "success"}, {"text": "Add 30D Key", "callback_data": "/SHOPADDKEY 5", "style": "success"}],
            [{"text": "Back", "callback_data": "/setshop_psue", "style": "danger"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

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
        stock = bot_data.get_data(f"HG_{day}d_keys") or []
        if not stock:
            st = "Out of Stock"
        elif len(stock) <= 2:
            st = f"Only {len(stock)} left!"
        else:
            st = "In Stock"
        return price, reseller, st
    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p14, r14, s14 = get_old(14)
    p21, r21, s21 = get_old(21)
    txt = (
        "PRIME MOD\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"1D Reseller: ₹{r1}\n1D Price: ₹{p1}\n{s1}\n\n"
        f"3D Reseller: ₹{r3}\n3D Price: ₹{p3}\n{s3}\n\n"
        f"7D Reseller: ₹{r7}\n7D Price: ₹{p7}\n{s7}\n\n"
        f"14D Reseller: ₹{r14}\n14D Price: ₹{p14}\n{s14}\n\n"
        f"21D Reseller: ₹{r21}\n21D Price: ₹{p21}\n{s21}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\nSelect duration below:"
    )
    markup = {
        "inline_keyboard": [
            [{"text": "RESELLER 1D", "callback_data": "/SHOPADD_PM 316", "style": "success"}],
            [{"text": "1D Price", "callback_data": "/SHOPADD_PM 311", "style": "success"}, {"text": "Add 1D Key", "callback_data": "/SHOPADDKEY 306", "style": "success"}],
            [{"text": "RESELLER 3D", "callback_data": "/SHOPADD_PM 317", "style": "success"}],
            [{"text": "3D Price", "callback_data": "/SHOPADD_PM 312", "style": "success"}, {"text": "Add 3D Key", "callback_data": "/SHOPADDKEY 307", "style": "success"}],
            [{"text": "RESELLER 7D", "callback_data": "/SHOPADD_PM 318", "style": "success"}],
            [{"text": "7D Price", "callback_data": "/SHOPADD_PM 313", "style": "success"}, {"text": "Add 7D Key", "callback_data": "/SHOPADDKEY 308", "style": "success"}],
            [{"text": "RESELLER 14D", "callback_data": "/SHOPADD_PM 319", "style": "success"}],
            [{"text": "14D Price", "callback_data": "/SHOPADD_PM 314", "style": "success"}, {"text": "Add 14D Key", "callback_data": "/SHOPADDKEY 309", "style": "success"}],
            [{"text": "RESELLER 21D", "callback_data": "/SHOPADD_PM 320", "style": "success"}],
            [{"text": "21D Price", "callback_data": "/SHOPADD_PM 315", "style": "success"}, {"text": "Add 21D Key", "callback_data": "/SHOPADDKEY 310", "style": "success"}],
            [{"text": "Back", "callback_data": "/setshop_psue", "style": "danger"}]
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
        stock = bot_data.get_data(f"SILENT_{day}d_keys") or []
        if not stock:
            st = "Out of Stock"
        elif len(stock) <= 2:
            st = f"Only {len(stock)} left!"
        else:
            st = "In Stock"
        return price, reseller, st
    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p14, r14, s14 = get_old(14)
    p28, r28, s28 = get_old(28)
    txt = (
        "SILENT CHEATS ANDROID\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"1D Reseller: ₹{r1}\n1D Price: ₹{p1}\n{s1}\n\n"
        f"3D Reseller: ₹{r3}\n3D Price: ₹{p3}\n{s3}\n\n"
        f"7D Reseller: ₹{r7}\n7D Price: ₹{p7}\n{s7}\n\n"
        f"14D Reseller: ₹{r14}\n14D Price: ₹{p14}\n{s14}\n\n"
        f"28D Reseller: ₹{r28}\n28D Price: ₹{p28}\n{s28}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\nSelect duration below:"
    )
    markup = {
        "inline_keyboard": [
            [{"text": "RESELLER 1D", "callback_data": "/SHOPADD_PM 221", "style": "success"}],
            [{"text": "1D Price", "callback_data": "/SHOPADD_PM 191", "style": "success"}, {"text": "Add 1D Key", "callback_data": "/SHOPADDKEY 101", "style": "success"}],
            [{"text": "RESELLER 3D", "callback_data": "/SHOPADD_PM 22", "style": "success"}],
            [{"text": "3D Price", "callback_data": "/SHOPADD_PM 19", "style": "success"}, {"text": "Add 3D Key", "callback_data": "/SHOPADDKEY 10", "style": "success"}],
            [{"text": "RESELLER 7D", "callback_data": "/SHOPADD_PM 23", "style": "success"}],
            [{"text": "7D Price", "callback_data": "/SHOPADD_PM 20", "style": "success"}, {"text": "Add 7D Key", "callback_data": "/SHOPADDKEY 11", "style": "success"}],
            [{"text": "RESELLER 14D", "callback_data": "/SHOPADD_PM 24", "style": "success"}],
            [{"text": "14D Price", "callback_data": "/SHOPADD_PM 21", "style": "success"}, {"text": "Add 14D Key", "callback_data": "/SHOPADDKEY 12", "style": "success"}],
            [{"text": "RESELLER 28D", "callback_data": "/SHOPADD_PM 225", "style": "success"}],
            [{"text": "28D Price", "callback_data": "/SHOPADD_PM 226", "style": "success"}, {"text": "Add 28D Key", "callback_data": "/SHOPADDKEY 13", "style": "success"}],
            [{"text": "Back", "callback_data": "/setshop_psue", "style": "danger"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/SHOPADDKEY")
def cmd_shopaddkey(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
        return True
    if not params:
        send_message(user_id, "Usage:\n/SHOPADDKEY 1 -> Drip 1d\n/SHOPADDKEY 2 -> Stricks 10d")
        return True
    key_map = {
        "1": ("drip_1d_keys", "DRIP CLIENT APK MOD\n1d Key"),
        "2": ("drip_3d_keys", "DRIP CLIENT APK MOD\n3d Key"),
        "3": ("drip_7d_keys", "DRIP CLIENT APK MOD\n7d Key"),
        "4": ("drip_15d_keys", "DRIP CLIENT APK MOD\n15d Key"),
        "5": ("drip_30d_keys", "DRIP CLIENT APK MOD\n30d Key"),
        "6": ("HG_1d_keys", "PRIME-HOOK-MOD\n1d Key"),
        "7": ("HG_7d_keys", "HG-CHEATS ANDROID\n7d Key"),
        "8": ("HG_10d_keys", "HG-CHEATS ANDROID\n10d Key"),
        "9": ("HG_30d_keys", "HG-CHEATS ANDROID\n30d Key"),
        "10": ("SILENT_3d_keys", "SILENT CHEATS ANDROID\n3d Key"),
        "11": ("SILENT_7d_keys", "SILENT CHEATS ANDROID\n7d Key"),
        "12": ("SILENT_14d_keys", "SILENT CHEATS ANDROID\n14d Key"),
        "13": ("SILENT_28d_keys", "SILENT CHEATS ANDROID\n28d Key"),
        "14": ("PRIME_5d_keys", "PRIME-HOOK-MOD APK\n5d Key"),
        "15": ("PRIME_10d_keys", "PRIME-HOOK-MOD APK\n10d Key"),
        "16": ("ROOT_10d_keys", "BR MOD ROOT\n10d Key"),
        "17": ("ROOT_20d_keys", "BR MOD ROOT\n20d Key"),
        "101": ("SILENT_1d_keys", "SILENT CHEATS ANDROID\n1d Key"),
        "306": ("HG_1d_keys", "PRIME MOD\n1d Key"),
        "307": ("HG_3d_keys", "PRIME MOD\n3d Key"),
        "308": ("HG_7d_keys", "PRIME MOD\n7d Key"),
        "309": ("HG_14d_keys", "PRIME MOD\n14d Key"),
        "310": ("HG_21d_keys", "PRIME MOD\n21d Key"),
    }
    if params in key_map:
        key_name, title = key_map[params]
        send_message(user_id, f"<b>{title}</b>\n\nSend key\n\nType /cancel to stop.", "HTML")
        pending_commands[user_id] = "/SHOPADDKEY1"
        pending_commands_store.set(user_id, "/SHOPADDKEY1")
        User.save_data(user_id, "shopaddkey_options", {"key": key_name, "title": title})
    else:
        send_message(user_id, "Invalid option.")
    return True

@command("/SHOPADDKEY1")
def cmd_shopaddkey1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    if text == "/cancel":
        send_message(user_id, "Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    opts = User.get_data(user_id, "shopaddkey_options")
    if not opts:
        send_message(user_id, "System Error: Key type missing.")
        return True
    key_name = opts.get("key")
    title = opts.get("title", "Product")
    if len(text) < 3:
        send_message(user_id, "Invalid Key. Send again or /cancel", "HTML")
        return True
    existing = bot_data.get_data(key_name) or []
    if isinstance(existing, str):
        existing = [existing]
    existing.append(text)
    bot_data.save_data(key_name, existing)
    send_message(
        user_id,
        f"Key Added Successfully\n\n{title}\nKey: <code>{text}</code>\nTotal Stock: {len(existing)}",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/SHOPADD_PM")
def cmd_shopadd_pm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not params:
        send_message(user_id, "Usage:\n/SHOPADD_PM <number>")
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
        "11": ("HG_1d_price", "HG-CHEATS ANDROID\n1 Days"),
        "12": ("HG_7d_price", "HG-CHEATS ANDROID\n7 Days"),
        "13": ("HG_10d_price", "HG-CHEATS ANDROID\n10 Days"),
        "14": ("HG_30d_price", "HG-CHEATS ANDROID\n30 Days"),
        "15": ("HG_1d_reseller_price", "RESELLER PANEL\nHG-CHEATS ANDROID\n1 Days"),
        "16": ("HG_7d_reseller_price", "RESELLER PANEL\nHG-CHEATS ANDROID\n7 Days"),
        "17": ("HG_10d_reseller_price", "RESELLER PANEL\nHG-CHEATS ANDROID\n10 Days"),
        "18": ("HG_30d_reseller_price", "RESELLER PANEL\nHG-CHEATS ANDROID\n30 Days"),
        "19": ("SILENT_3d_price", "SILENT CHEATS ANDROID\n3 Days"),
        "20": ("SILENT_7d_price", "SILENT CHEATS ANDROID\n7 Days"),
        "21": ("SILENT_14d_price", "SILENT CHEATS ANDROID\n14 Days"),
        "22": ("SILENT_3d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n3 Days"),
        "23": ("SILENT_7d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n7 Days"),
        "24": ("SILENT_14d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n14 Days"),
        "25": ("SILENT_28d_price", "SILENT CHEATS ANDROID\n28 Days"),
        "26": ("SILENT_28d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n28 Days"),
        "27": ("PRIME_5d_price", "PRIME-HOOK-MOD APK\n5 Days"),
        "28": ("PRIME_10d_price", "PRIME-HOOK-MOD APK\n10 Days"),
        "29": ("PRIME_5d_reseller_price", "RESELLER PANEL\nPRIME-HOOK-MOD APK\n5 Days"),
        "30": ("PRIME_10d_reseller_price", "RESELLER PANEL\nPRIME-HOOK-MOD APK\n10 Days"),
        "31": ("ROOT_10d_price", "BR MOD ROOT\n10 Days"),
        "32": ("ROOT_20d_price", "BR MOD ROOT\n20 Days"),
        "33": ("ROOT_10d_reseller_price", "RESELLER PANEL\nBR MOD ROOT\n10 Days"),
        "34": ("ROOT_20d_reseller_price", "RESELLER PANEL\nBR MOD ROOT\n20 Days"),
        "191": ("SILENT_1d_price", "SILENT CHEATS ANDROID\n1 Days"),
        "221": ("SILENT_1d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n1 Days"),
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
        "225": ("SILENT_28d_reseller_price", "RESELLER PANEL\nSILENT CHEATS ANDROID\n28 Days"),
        "226": ("SILENT_28d_price", "SILENT CHEATS ANDROID\n28 Days"),
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
        easy_time = get_easy_time()
        act = f"{title} Price = ₹{rate}"
        adm_ac = bot_data.get_data("AdmAC") or []
        adm_ac.append(
            f"Time: {easy_time}\n"
            f"By {message.get('from', {}).get('first_name', 'Admin')} [ID: <code>{user_id}</code>]\n"
            f"Action: {act}"
        )
        bot_data.save_data("AdmAC", adm_ac)
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
        send_message(user_id, "<b><i>🚫 You Are Not This Bot Admin</i></b>", "HTML")
        return True
    
    all_users = user_data_store.get_all_users()
    all_users = list(set(all_users))
    
    User.save_data(user_id, "broadcast_users", all_users)
    
    send_message(
        user_id, 
        f"📢 <b>BROADCAST MODE</b>\n\n"
        f"👥 Total Users: {len(all_users)}\n\n"
        f"Send ANY message.\n"
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
    
    users = User.get_data(user_id, "broadcast_users") or []
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
    print("Bot Started with MongoDB!")
    print(f"Connected to MongoDB: {DB_NAME}")
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
