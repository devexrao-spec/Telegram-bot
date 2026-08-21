# tusharbot.py - COMPLETE FULL CODE WITH ALL FIXES
import requests
import json
import time
from datetime import datetime
import threading
from pymongo import MongoClient
import random
import string

BOT_TOKEN = "8565204943:AAEw7F-5NIwZjluyWT-PQYk70xHY3j01xAo"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ========== RESELLER API CONFIGURATION ==========
RESELLER_API_URL = "https://xyzcheats.com/api/reseller_v1.php"
RESELLER_API_KEY = "b25eb076f5c0412fa9f1eba94550d02e"
RESELLER_API_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'x-master-key': 'a7f3e8b2c9d1f4a6b8c2d5e9f1a3b6c8'
}

# ========== DURATION MAPPING - UPDATED ==========
DURATION_MAP = {
    "1": "1 DaYS NONROOT",
    "2": "3 DaYS NONROOT",
    "3": "7 DaYS NONROOT",
    "4": "15 DaYS NONROOT",
    "5": "30 DaYS NONROOT",
    "6": "1 DaYS NONROOT",
    "7": "3 DaYS NONROOT",
    "8": "7 DaYS NONROOT",
    "9": "14 DaYS NONROOT",
    "10": "1 DaYS NONROOT",
    "11": "3 DaYS NONROOT",
    "12": "7 DaYS NONROOT",
    "13": "14 DaYS NONROOT",
    "14": "21 DaYS NONROOT",
    "15": "28 DaYS NONROOT",
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
        collections = ['bot_data', 'user_data', 'pending_commands', 'pending_payments', 'processed_payments', 'payment_orders', 'products']
        for coll in collections:
            if coll not in self.db.list_collection_names():
                self.db.create_collection(coll)
        
        self.db.bot_data.create_index("key", unique=True)
        self.db.user_data.create_index([("user_id", 1), ("key", 1)], unique=True)
        self.db.pending_payments.create_index("user_id", unique=True)
        self.db.processed_payments.create_index("order_id", unique=True)
        self.db.payment_orders.create_index("order_id", unique=True)
        self.db.products.create_index("product_id", unique=True)
    
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

# ========== PRODUCT MANAGEMENT ==========

class ProductManager:
    def __init__(self):
        self.collection = mongo.get_collection('products')
    
    def get_all_products(self):
        return list(self.collection.find())
    
    def get_product(self, product_id):
        return self.collection.find_one({"product_id": product_id})
    
    def add_product(self, product_id, name, pid, needs_android=True):
        product = {
            "product_id": product_id,
            "name": name,
            "pid": pid,
            "needs_android": needs_android,
            "plans": [],
            "created_at": datetime.now()
        }
        self.collection.update_one(
            {"product_id": product_id},
            {"$set": product},
            upsert=True
        )
        return product
    
    def add_plan(self, product_id, plan_id, duration, price, reseller_price):
        plan = {
            "plan_id": plan_id,
            "duration": duration,
            "price": price,
            "reseller_price": reseller_price
        }
        self.collection.update_one(
            {"product_id": product_id},
            {"$push": {"plans": plan}}
        )
        return plan
    
    def update_product_pid(self, product_id, new_pid):
        self.collection.update_one(
            {"product_id": product_id},
            {"$set": {"pid": new_pid}}
        )
    
    def update_plan_price(self, product_id, plan_id, price, reseller_price=None):
        update_data = {"plans.$.price": price}
        if reseller_price is not None:
            update_data["plans.$.reseller_price"] = reseller_price
        
        self.collection.update_one(
            {"product_id": product_id, "plans.plan_id": plan_id},
            {"$set": update_data}
        )
    
    def remove_plan(self, product_id, plan_id):
        self.collection.update_one(
            {"product_id": product_id},
            {"$pull": {"plans": {"plan_id": plan_id}}}
        )
    
    def delete_product(self, product_id):
        self.collection.delete_one({"product_id": product_id})
    
    def toggle_android(self, product_id):
        product = self.get_product(product_id)
        if product:
            new_val = not product.get('needs_android', True)
            self.collection.update_one(
                {"product_id": product_id},
                {"$set": {"needs_android": new_val}}
            )
            return new_val
        return None

product_manager = ProductManager()

# ========== API FUNCTIONS - FIXED ==========

def generate_api_key(product_pid, duration, android_id=None, price=None):
    """Call reseller API to generate a key"""
    data = {
        'api_key': RESELLER_API_KEY,
        'action': 'buy',
        'product_id': str(product_pid),
        'duration': duration
    }
    
    # IMPORTANT: Send price
    if price:
        data['price'] = str(price)
        data['amount'] = str(price)
    
    if android_id:
        data['android_id'] = android_id
    
    print(f"📤 API Request: {data}")
    
    try:
        response = requests.post(
            RESELLER_API_URL,
            data=data,
            headers=RESELLER_API_HEADERS,
            timeout=30
        )
        
        print(f"📥 API Response: {response.text}")
        
        result = response.json()
        
        if result.get('status') == 'success':
            key = result.get('key') or result.get('data', {}).get('key')
            if key:
                return True, key
            else:
                return False, f"No key in response: {result}"
        else:
            error_msg = result.get('msg') or result.get('message') or 'Unknown error'
            return False, f"API Error: {error_msg}"
            
    except Exception as e:
        return False, f"API Error: {str(e)}"

def get_duration(plan_id):
    """Get duration string from mapping"""
    return DURATION_MAP.get(str(plan_id), "1 DaYS NONROOT")

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

def forward_message(chat_id, from_chat_id, message_id):
    url = f"{BASE_URL}/forwardMessage"
    payload = {
        "chat_id": chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id
    }
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

# ========== DEFAULT PRODUCTS SETUP ==========

def setup_default_products():
    """Add default products on first run"""
    
    products = {
        "abcd": {
            "name": "ABCD",
            "pid": "143",
            "needs_android": False,
            "plans": [
                {"plan_id": "1", "duration": "12 Hours", "price": 10, "reseller_price": 8},
            ]
        },
        "bala_v2": {
            "name": "BALA MODS XYZ V2",
            "pid": "136",
            "needs_android": False,
            "plans": [
                {"plan_id": "1", "duration": "1 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 10, "reseller_price": 8},
                {"plan_id": "2", "duration": "3 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 25, "reseller_price": 20},
                {"plan_id": "3", "duration": "6 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 45, "reseller_price": 38},
                {"plan_id": "4", "duration": "12 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 80, "reseller_price": 68},
                {"plan_id": "5", "duration": "1 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 150, "reseller_price": 130},
                {"plan_id": "6", "duration": "2 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 250, "reseller_price": 210},
                {"plan_id": "7", "duration": "3 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 350, "reseller_price": 300},
                {"plan_id": "8", "duration": "5 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 500, "reseller_price": 430},
            ]
        },
        "drip": {
            "name": "DRIP CLIENT MOD",
            "pid": "133",
            "needs_android": True,
            "plans": [
                {"plan_id": "1", "duration": "1 DaYS NONROOT", "price": 100, "reseller_price": 80},
                {"plan_id": "2", "duration": "3 DaYS NONROOT", "price": 250, "reseller_price": 200},
                {"plan_id": "3", "duration": "7 DaYS NONROOT", "price": 350, "reseller_price": 300},
                {"plan_id": "4", "duration": "15 DaYS NONROOT", "price": 560, "reseller_price": 480},
                {"plan_id": "5", "duration": "30 DaYS NONROOT", "price": 810, "reseller_price": 750},
            ]
        },
        "silent": {
            "name": "SILENT CHEATS ANDROID",
            "pid": "133",
            "needs_android": True,
            "plans": [
                {"plan_id": "1", "duration": "1 DaYS NONROOT", "price": 108, "reseller_price": 95},
                {"plan_id": "2", "duration": "3 DaYS NONROOT", "price": 260, "reseller_price": 220},
                {"plan_id": "3", "duration": "7 DaYS NONROOT", "price": 360, "reseller_price": 320},
                {"plan_id": "4", "duration": "14 DaYS NONROOT", "price": 560, "reseller_price": 480},
                {"plan_id": "5", "duration": "28 DaYS NONROOT", "price": 810, "reseller_price": 750},
            ]
        },
        "prime": {
            "name": "PRIME HOOK",
            "pid": "133",
            "needs_android": True,
            "plans": [
                {"plan_id": "1", "duration": "1 DaYS NONROOT", "price": 108, "reseller_price": 95},
                {"plan_id": "2", "duration": "3 DaYS NONROOT", "price": 200, "reseller_price": 180},
                {"plan_id": "3", "duration": "7 DaYS NONROOT", "price": 360, "reseller_price": 320},
                {"plan_id": "4", "duration": "14 DaYS NONROOT", "price": 600, "reseller_price": 550},
                {"plan_id": "5", "duration": "21 DaYS NONROOT", "price": 700, "reseller_price": 650},
            ]
        }
    }
    
    for product_id, data in products.items():
        existing = product_manager.get_product(product_id)
        if not existing:
            product_manager.add_product(
                product_id,
                data["name"],
                data["pid"],
                data["needs_android"]
            )
            for plan in data["plans"]:
                product_manager.add_plan(
                    product_id,
                    plan["plan_id"],
                    plan["duration"],
                    plan["price"],
                    plan["reseller_price"]
                )
            print(f"✅ Added: {data['name']}")

# ========== PROCESS PURCHASE ==========

def process_purchase(message, product_id, plan_id, price, product_name, duration, pid, android_id=None):
    user_id = message.get("from", {}).get("id")
    balance = Resources.another_res("Balance", user=user_id)
    
    if balance.value() < price:
        User.save_data(user_id, "last_deposit_amount", price)
        User.save_data(user_id, "last_product", product_name)
        cmd_autobuy1(message, None)
        return True
    
    balance.cut(price)
    Resources.another_res("Order", user=user_id).add(1)
    
    # Get duration from mapping
    api_duration = get_duration(plan_id)
    
    # Generate key with price
    success, result = generate_api_key(pid, api_duration, android_id, price)
    
    if success:
        easy_time = get_easy_time()
        send_message(
            user_id,
            f"🛒 {product_name}\n\n"
            f"🔑 <b>Your Key:</b>\n<code>{result}</code>\n\n"
            f"💰 Deducted: ₹{price}\n"
            f"⏳ Duration: {duration}\n"
            f"📦 Time: {easy_time}",
            "HTML"
        )
        
        adm_ac = User.get_data(user_id, "userhAC") or []
        adm_ac.append(
            f"📆 {easy_time}\n"
            f"👤 {message.get('from', {}).get('first_name', 'User')} [{user_id}]\n"
            f"📦 {product_name}\n"
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
        "🌟 <b>WELCOME TO HACK STORE</b> 🌙\n\n"
        "✨ Your ultimate destination for premium mods, cheats & clients!\n\n"
        "🚀 <b>PREMIUM FEATURES</b>\n"
        "⚡ Instant Key Delivery\n"
        "💳 Secure Auto-Payment System\n"
        "🛡 100% Anti-Ban Support\n\n"
        f"💰 Your Balance: ₹{balance}"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "🛒 BUY HACK", "callback_data": "/shopnawkk"}],
            [{"text": "🔑 MY KEY", "callback_data": "/orderksk"}, {"text": "👤 PROFILE", "callback_data": "/profilemmm"}],
            [{"text": "📖 HOW TO USE", "callback_data": "/spinj"}, {"text": "💬 SUPPORT", "callback_data": "/supportj"}],
            [{"text": "💰 ADD FUND", "callback_data": "/addpayment"}]
        ]
    }
    send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/shopnawkk")
def cmd_shopnawkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    products = product_manager.get_all_products()
    
    if not products:
        text = "⚠️ No products available. Contact admin."
        reply_markup = {"inline_keyboard": [[{"text": "🔙 BACK", "callback_data": "/backkkk"}]]}
        try:
            edit_message(user_id, msg_id, text, "HTML", reply_markup)
        except:
            send_message(user_id, text, "HTML", reply_markup)
        return True
    
    text = "🛒 <b>PANNEL STORE — SHOP</b>\n━━━━━━━━━━━━━━━━━━\n\n📦 Choose a product:"
    
    keyboard = []
    for product in products:
        keyboard.append([{"text": f"📦 {product.get('name')}", "callback_data": f"/shop_product {product.get('product_id')}"}])
    
    keyboard.append([{"text": "🔙 BACK", "callback_data": "/backkkk"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/shop_product")
def cmd_shop_product(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    if not params:
        send_message(user_id, "Invalid product")
        return True
    
    product = product_manager.get_product(params)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    resellers = bot_data.get_data("resellers_list") or []
    is_reseller = str(user_id) in [str(u) for u in resellers]
    
    text = f"📦 <b>{product.get('name')}</b>\n━━━━━━━━━━━━━━━━━━\n\nChoose a plan 👇"
    
    keyboard = []
    for plan in product.get('plans', []):
        price = plan.get('reseller_price') if is_reseller else plan.get('price')
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        keyboard.append([{"text": f"{duration} - ₹{price}", "callback_data": f"/buy_product {product.get('product_id')}|{plan_id}"}])
    
    keyboard.append([{"text": "🔙 BACK", "callback_data": "/shopnawkk"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/buy_product")
def cmd_buy_product(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    
    if not params or '|' not in params:
        send_message(user_id, "Invalid product selection")
        return True
    
    product_id, plan_id = params.split('|')
    
    product = product_manager.get_product(product_id)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    selected_plan = None
    for plan in product.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected_plan = plan
            break
    
    if not selected_plan:
        send_message(user_id, "Plan not found")
        return True
    
    resellers = bot_data.get_data("resellers_list") or []
    is_reseller = str(user_id) in [str(u) for u in resellers]
    
    price = selected_plan.get('reseller_price') if is_reseller else selected_plan.get('price')
    duration = selected_plan.get('duration')
    product_name = product.get('name')
    pid = product.get('pid')
    needs_android = product.get('needs_android', True)
    
    User.save_data(user_id, "last_product1", product_name)
    User.save_data(user_id, "last_plan", plan_id)
    User.save_data(user_id, "last_product_key", product_id)
    User.save_data(user_id, "last_price", price)
    User.save_data(user_id, "last_duration", duration)
    User.save_data(user_id, "last_pid", pid)
    
    if needs_android:
        send_message(
            user_id,
            f"🔐 <b>Android ID Required</b>\n\n"
            f"Product: {product_name}\n"
            f"Plan: {duration}\n"
            f"Price: ₹{price}\n\n"
            f"Please send your Android ID.\n"
            f"Type /cancel to cancel.",
            "HTML"
        )
        pending_commands[user_id] = "/process_android_id"
        pending_commands_store.set(user_id, "/process_android_id")
        return True
    else:
        return process_purchase(message, product_id, plan_id, price, product_name, duration, pid)

@command("/process_android_id")
def process_android_id(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    if len(text) != 16 or not all(c in '0123456789abcdefABCDEF' for c in text):
        send_message(
            user_id,
            "❌ Invalid Android ID.\n\n"
            "Should be 16 characters (hexadecimal).\n"
            "Example: <code>0b9b969bc2e7997b</code>",
            "HTML"
        )
        return True
    
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    
    product_id = User.get_data(user_id, "last_product_key")
    plan_id = User.get_data(user_id, "last_plan")
    price = User.get_data(user_id, "last_price")
    product_name = User.get_data(user_id, "last_product1")
    duration = User.get_data(user_id, "last_duration")
    pid = User.get_data(user_id, "last_pid")
    
    return process_purchase(message, product_id, plan_id, price, product_name, duration, pid, android_id=text)

@command("/autobuy1")
def cmd_autobuy1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    amount = User.get_data(user_id, "last_deposit_amount")
    pt = User.get_data(user_id, "last_product1") or "Unknown"
    if not amount:
        send_message(user_id, "Amount missing")
        return True
    balance = Resources.another_res("Balance", user=user_id).value()
    
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
        product_name=pt
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
        f"💰 <b>INSUFFICIENT BALANCE</b>\n\n"
        f"Product: {pt}\n"
        f"Price: ₹{amount}\n"
        f"Your Balance: ₹{balance}\n\n"
        f"Scan QR and complete payment.\n\n"
        f"🧾 <b>Order ID:</b>\n<code>{order_id}</code>"
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
    
    send_message(user_id, "⏳ Checking payment...", "HTML")
    
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
        return True
    else:
        send_message(
            user_id,
            f"❌ <b>Payment Not Found</b>\n\n"
            f"Order ID: <code>{order_id}</code>",
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
    send_message(user_id, "❌ Cancelled", "HTML")
    return True

@command("/backkkk")
def cmd_backkkk(message, params, options=None):
    return cmd_start(message, params, options)

@command("/orderksk")
def cmd_orderksk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    adm_ac = User.get_data(user_id, "userhAC") or []
    if not adm_ac:
        text = "📦 <b>MY ORDERS</b>\n━━━━━━━━━━━━━━━━━━\n\nYou haven't placed any orders yet."
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
        "👤 <b>YOUR PROFILE</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Name: {first_name}\n"
        f"🆔 User ID: {user_id}\n"
        f"💰 Balance: ₹{balance}\n"
        f"🛒 Total Orders: {orders}"
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
    text = "🎥 <b>Watch the full tutorial video below</b>"
    reply_markup = {
        "inline_keyboard": [
            [{"text": "▶️ Watch Tutorial", "url": "https://t.me/hehehehhhsljg/162"}],
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
💬 <b>Support — Seller</b> 🛡
━━━━━━━━━━━━━━━━━━

<a href="https://t.me/UR_SUBHAJIT0">𝐒υвʜᴀᎫιт</a> ⭐

💡 Include your User ID from Profile.
"""
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📱 WHATSAPP", "url": "https://wa.me/917908696630"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
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
    text = "💰 <b>ENTER AMOUNT</b>\n\n₹0"
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
    if amt != "0":
        amt += "0"
    current_amount[user_id] = amt
    text = f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num1")
def cmd_num1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "1" if amt == "0" else amt + "1"
    current_amount[user_id] = amt
    text = f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num2")
def cmd_num2(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "2" if amt == "0" else amt + "2"
    current_amount[user_id] = amt
    text = f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num3")
def cmd_num3(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "3" if amt == "0" else amt + "3"
    current_amount[user_id] = amt
    text = f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num4")
def cmd_num4(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "4" if amt == "0" else amt + "4"
    current_amount[user_id] = amt
    text = f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num5")
def cmd_num5(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "5" if amt == "0" else amt + "5"
    current_amount[user_id] = amt
    text = f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num6")
def cmd_num6(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "6" if amt == "0" else amt + "6"
    current_amount[user_id] = amt
    text = f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num7")
def cmd_num7(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "7" if amt == "0" else amt + "7"
    current_amount[user_id] = amt
    text = f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num8")
def cmd_num8(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "8" if amt == "0" else amt + "8"
    current_amount[user_id] = amt
    text = f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/num9")
def cmd_num9(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "9" if amt == "0" else amt + "9"
    current_amount[user_id] = amt
    text = f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/clearamt")
def cmd_clearamt(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    text = "💰 <b>ENTER AMOUNT</b>\n\n₹0"
    edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
    return True

@command("/done")
def cmd_done(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    amt = current_amount.get(user_id, "0")
    if not amt or amt == "0":
        send_message(user_id, "Enter amount first!", "HTML")
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
    
    caption = f"💰 <b>PAYMENT QR</b>\n\nAmount: ₹{amount}\n\n🧾 Order: <code>{order_id}</code>"
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ VERIFY", "callback_data": f"/verify_payment {order_id}"}],
            [{"text": "❌ CANCEL", "callback_data": f"/cancel {order_id}"}]
        ]
    }
    send_photo(user_id, qr_url, caption, "HTML", reply_markup)

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
        send_message(user_id, "🚫 Not Admin", "HTML")
        return True
    
    markup = {
        "inline_keyboard": [
            [{"text": "📦 Manage Products", "callback_data": "/admin_products"}],
            [{"text": "👑 Manage Admins", "callback_data": "/TUSHAR_Admins"}],
            [{"text": "📣 Broadcast", "callback_data": "/broadcast"}],
            [{"text": "💰 Add Balance", "callback_data": "/ChangeAnyUserBal"}],
            [{"text": "📝 Reseller Management", "callback_data": "/admin_resellers"}]
        ]
    }
    txt = f"👋 Welcome Admin!\n━━━━━━━━━━━━━━━\n🏪 ADMIN PANEL"
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/admin_products")
def cmd_admin_products(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    products = product_manager.get_all_products()
    
    text = "📦 <b>MANAGE PRODUCTS</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    if not products:
        text += "No products."
    else:
        for i, product in enumerate(products, 1):
            text += f"{i}. {product.get('name')}\n"
            text += f"   🔑 PID: {product.get('pid')}\n"
            text += f"   📱 Android: {'Required' if product.get('needs_android', True) else 'Not Required'}\n"
            plans = product.get('plans', [])
            if plans:
                text += "   📋 Plans:\n"
                for plan in plans:
                    text += f"      • {plan.get('duration')} - ₹{plan.get('price')}"
                    if plan.get('reseller_price'):
                        text += f" (Reseller: ₹{plan.get('reseller_price')})"
                    text += f"\n"
            text += "\n"
    
    markup = {
        "inline_keyboard": [
            [{"text": "➕ Add Product", "callback_data": "/add_product_btn"}],
            [{"text": "✏️ Edit Product", "callback_data": "/edit_product_btn"}],
            [{"text": "🗑️ Delete Product", "callback_data": "/delete_product_btn"}],
            [{"text": "🔙 Back", "callback_data": "/admin AP"}]
        ]
    }
    
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

# ========== ADD PRODUCT ==========

@command("/add_product_btn")
def cmd_add_product_btn(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    text = """
➕ <b>ADD PRODUCT</b>
━━━━━━━━━━━━━━━━━━

Format: <code>product_id|name|pid</code>
Example: <code>abcd|ABCD|143</code>

Type /cancel to stop.
"""
    send_message(user_id, text, "HTML")
    pending_commands[user_id] = "/add_product_process"
    pending_commands_store.set(user_id, "/add_product_process")
    return True

@command("/add_product_process")
def cmd_add_product_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    parts = text.split('|')
    if len(parts) < 3:
        send_message(user_id, "❌ Invalid! Use: product_id|name|pid", "HTML")
        return True
    
    product_id = parts[0].strip()
    name = parts[1].strip()
    pid = parts[2].strip()
    
    existing = product_manager.get_product(product_id)
    if existing:
        send_message(user_id, f"❌ Product '{product_id}' exists!", "HTML")
        return True
    
    product_manager.add_product(product_id, name, pid, True)
    
    markup = {
        "inline_keyboard": [
            [{"text": "📋 Add Plan", "callback_data": f"/add_plan_btn {product_id}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    send_message(
        user_id,
        f"✅ Product Added!\n\n📦 {name}\n🔑 PID: {pid}\n\nAdd plans:",
        "HTML",
        markup
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

# ========== ADD PLAN ==========

@command("/add_plan_btn")
def cmd_add_plan_btn(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "Product ID missing")
        return True
    
    product = product_manager.get_product(params)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    User.save_data(user_id, "add_plan_product", params)
    
    text = f"""
📋 <b>ADD PLAN to {product.get('name')}</b>
━━━━━━━━━━━━━━━━━━

Format: <code>plan_id|duration|price|reseller_price</code>
Example: <code>1|12 Hours|10|8</code>

Type /cancel to stop.
"""
    send_message(user_id, text, "HTML")
    pending_commands[user_id] = "/add_plan_process"
    pending_commands_store.set(user_id, "/add_plan_process")
    return True

@command("/add_plan_process")
def cmd_add_plan_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    product_id = User.get_data(user_id, "add_plan_product")
    if not product_id:
        send_message(user_id, "Product not found", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    parts = text.split('|')
    if len(parts) < 4:
        send_message(user_id, "❌ Invalid! Use: plan_id|duration|price|reseller_price", "HTML")
        return True
    
    plan_id = parts[0].strip()
    duration = parts[1].strip()
    try:
        price = float(parts[2].strip())
        reseller_price = float(parts[3].strip())
    except:
        send_message(user_id, "❌ Price must be numbers!", "HTML")
        return True
    
    product = product_manager.get_product(product_id)
    if not product:
        send_message(user_id, "Product not found", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    for plan in product.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            send_message(user_id, f"❌ Plan ID '{plan_id}' exists!", "HTML")
            return True
    
    product_manager.add_plan(product_id, plan_id, duration, price, reseller_price)
    
    markup = {
        "inline_keyboard": [
            [{"text": "➕ Add Another", "callback_data": f"/add_plan_btn {product_id}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    send_message(
        user_id,
        f"✅ Plan Added!\n\n📦 {product.get('name')}\n📋 {duration}\n💰 ₹{price}\n💰 Reseller: ₹{reseller_price}",
        "HTML",
        markup
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "add_plan_product", None)
    return True

# ========== EDIT PRODUCT ==========

@command("/edit_product_btn")
def cmd_edit_product_btn(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    products = product_manager.get_all_products()
    if not products:
        send_message(user_id, "No products to edit.", "HTML")
        return True
    
    keyboard = []
    for product in products:
        keyboard.append([{"text": f"✏️ {product.get('name')}", "callback_data": f"/edit_product_select {product.get('product_id')}"}])
    keyboard.append([{"text": "🔙 Back", "callback_data": "/admin_products"}])
    
    reply_markup = {"inline_keyboard": keyboard}
    try:
        edit_message(user_id, msg_id, "Select product to edit:", "HTML", reply_markup)
    except:
        send_message(user_id, "Select product to edit:", "HTML", reply_markup)
    return True

@command("/edit_product_select")
def cmd_edit_product_select(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    if not params:
        return True
    
    product = product_manager.get_product(params)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    User.save_data(user_id, "editing_product", params)
    
    text = f"""
✏️ <b>EDIT PRODUCT: {product.get('name')}</b>
━━━━━━━━━━━━━━━━━━

📦 ID: {product.get('product_id')}
🔑 PID: {product.get('pid')}
📱 Android: {'Required' if product.get('needs_android', True) else 'Not Required'}

📋 Plans:
"""
    for plan in product.get('plans', []):
        text += f"  • {plan.get('duration')} - ₹{plan.get('price')} (Reseller: ₹{plan.get('reseller_price')}) [ID: {plan.get('plan_id')}]\n"
    
    markup = {
        "inline_keyboard": [
            [{"text": "🔑 Change PID", "callback_data": f"/edit_pid_btn {params}"}],
            [{"text": "📋 Edit Plan", "callback_data": f"/edit_plan_btn {params}"}],
            [{"text": "🗑️ Remove Plan", "callback_data": f"/remove_plan_btn {params}"}],
            [{"text": "📱 Toggle Android", "callback_data": f"/toggle_android_btn {params}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

@command("/edit_pid_btn")
def cmd_edit_pid_btn(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "Product ID missing")
        return True
    
    User.save_data(user_id, "edit_pid_product", params)
    send_message(
        user_id,
        f"🔑 Send new PID for product: {params}\n\nType /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/edit_pid_process"
    pending_commands_store.set(user_id, "/edit_pid_process")
    return True

@command("/edit_pid_process")
def cmd_edit_pid_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "edit_pid_product", None)
        return True
    
    product_id = User.get_data(user_id, "edit_pid_product")
    if not product_id:
        send_message(user_id, "No product selected.", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    product = product_manager.get_product(product_id)
    if not product:
        send_message(user_id, "Product not found", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "edit_pid_product", None)
        return True
    
    product_manager.update_product_pid(product_id, text)
    
    markup = {
        "inline_keyboard": [
            [{"text": "🔙 Back to Edit", "callback_data": f"/edit_product_select {product_id}"}]
        ]
    }
    
    send_message(
        user_id,
        f"✅ PID Updated!\n\n📦 {product.get('name')}\n🔑 New PID: {text}",
        "HTML",
        markup
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "edit_pid_product", None)
    return True

@command("/edit_plan_btn")
def cmd_edit_plan_btn(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "Product ID missing")
        return True
    
    product = product_manager.get_product(params)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    if not product.get('plans'):
        send_message(user_id, "No plans for this product.", "HTML")
        return True
    
    User.save_data(user_id, "edit_plan_product", params)
    
    text = f"📋 Select plan to edit for {product.get('name')}"
    keyboard = []
    for plan in product.get('plans', []):
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        keyboard.append([{"text": f"{duration} [ID: {plan_id}]", "callback_data": f"/edit_plan_select {params}|{plan_id}"}])
    keyboard.append([{"text": "🔙 Back", "callback_data": f"/edit_product_select {params}"}])
    
    reply_markup = {"inline_keyboard": keyboard}
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/edit_plan_select")
def cmd_edit_plan_select(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    
    if not params or '|' not in params:
        return True
    
    product_id, plan_id = params.split('|')
    product = product_manager.get_product(product_id)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    selected_plan = None
    for plan in product.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected_plan = plan
            break
    
    if not selected_plan:
        send_message(user_id, "Plan not found")
        return True
    
    User.save_data(user_id, "edit_plan_data", {"product_id": product_id, "plan_id": plan_id})
    
    text = f"""
✏️ <b>EDIT PLAN</b>
━━━━━━━━━━━━━━━━━━
📦 Product: {product.get('name')}
📋 Plan: {selected_plan.get('duration')}
💰 Price: ₹{selected_plan.get('price')}
💰 Reseller: ₹{selected_plan.get('reseller_price')}

Send new price|reseller_price
Example: <code>150|130</code>

Type /cancel to stop.
"""
    send_message(user_id, text, "HTML")
    pending_commands[user_id] = "/edit_plan_process"
    pending_commands_store.set(user_id, "/edit_plan_process")
    return True

@command("/edit_plan_process")
def cmd_edit_plan_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "edit_plan_data", None)
        return True
    
    edit_data = User.get_data(user_id, "edit_plan_data")
    if not edit_data:
        send_message(user_id, "No plan selected.", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    parts = text.split('|')
    if len(parts) < 2:
        send_message(user_id, "❌ Invalid! Use: price|reseller_price", "HTML")
        return True
    
    try:
        price = float(parts[0].strip())
        reseller_price = float(parts[1].strip())
    except:
        send_message(user_id, "❌ Price must be numbers!", "HTML")
        return True
    
    product_id = edit_data.get("product_id")
    plan_id = edit_data.get("plan_id")
    
    product = product_manager.get_product(product_id)
    if not product:
        send_message(user_id, "Product not found", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    product_manager.update_plan_price(product_id, plan_id, price, reseller_price)
    
    markup = {
        "inline_keyboard": [
            [{"text": "🔙 Back", "callback_data": f"/edit_product_select {product_id}"}]
        ]
    }
    
    send_message(
        user_id,
        f"✅ Plan Updated!\n\n📦 {product.get('name')}\n💰 ₹{price}\n💰 Reseller: ₹{reseller_price}",
        "HTML",
        markup
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "edit_plan_data", None)
    return True

@command("/remove_plan_btn")
def cmd_remove_plan_btn(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "Product ID missing")
        return True
    
    product = product_manager.get_product(params)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    if not product.get('plans'):
        send_message(user_id, "No plans to remove.", "HTML")
        return True
    
    text = f"🗑️ Select plan to remove from {product.get('name')}"
    keyboard = []
    for plan in product.get('plans', []):
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        keyboard.append([{"text": f"❌ {duration}", "callback_data": f"/remove_plan_confirm {params}|{plan_id}"}])
    keyboard.append([{"text": "🔙 Back", "callback_data": f"/edit_product_select {params}"}])
    
    reply_markup = {"inline_keyboard": keyboard}
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/remove_plan_confirm")
def cmd_remove_plan_confirm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    
    if not params or '|' not in params:
        return True
    
    product_id, plan_id = params.split('|')
    product = product_manager.get_product(product_id)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    selected_plan = None
    for plan in product.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected_plan = plan
            break
    
    if not selected_plan:
        send_message(user_id, "Plan not found")
        return True
    
    product_manager.remove_plan(product_id, plan_id)
    
    markup = {
        "inline_keyboard": [
            [{"text": "🔙 Back", "callback_data": f"/edit_product_select {product_id}"}]
        ]
    }
    
    send_message(
        user_id,
        f"✅ Plan Removed!\n\n📦 {product.get('name')}\n📋 {selected_plan.get('duration')}",
        "HTML",
        markup
    )
    return True

@command("/toggle_android_btn")
def cmd_toggle_android_btn(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if not params:
        send_message(user_id, "Product ID missing")
        return True
    
    product = product_manager.get_product(params)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    new_val = product_manager.toggle_android(params)
    
    markup = {
        "inline_keyboard": [
            [{"text": "🔙 Back", "callback_data": f"/edit_product_select {params}"}]
        ]
    }
    
    send_message(
        user_id,
        f"✅ Android ID requirement updated!\n\n📦 {product.get('name')}\n📱 Android: {'Required' if new_val else 'Not Required'}",
        "HTML",
        markup
    )
    return True

# ========== DELETE PRODUCT ==========

@command("/delete_product_btn")
def cmd_delete_product_btn(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    products = product_manager.get_all_products()
    if not products:
        send_message(user_id, "No products to delete.", "HTML")
        return True
    
    keyboard = []
    for product in products:
        keyboard.append([{"text": f"🗑️ {product.get('name')}", "callback_data": f"/delete_product_confirm {product.get('product_id')}"}])
    keyboard.append([{"text": "🔙 Back", "callback_data": "/admin_products"}])
    
    reply_markup = {"inline_keyboard": keyboard}
    try:
        edit_message(user_id, msg_id, "Select product to delete:", "HTML", reply_markup)
    except:
        send_message(user_id, "Select product to delete:", "HTML", reply_markup)
    return True

@command("/delete_product_confirm")
def cmd_delete_product_confirm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    if not params:
        return True
    
    product = product_manager.get_product(params)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    markup = {
        "inline_keyboard": [
            [{"text": "✅ Yes, Delete", "callback_data": f"/delete_product_yes {params}"}],
            [{"text": "❌ No, Cancel", "callback_data": "/admin_products"}]
        ]
    }
    
    try:
        edit_message(
            user_id,
            msg_id,
            f"⚠️ <b>Delete {product.get('name')}?</b>\n\nThis will remove all plans!",
            "HTML",
            markup
        )
    except:
        send_message(
            user_id,
            f"⚠️ <b>Delete {product.get('name')}?</b>\n\nThis will remove all plans!",
            "HTML",
            markup
        )
    return True

@command("/delete_product_yes")
def cmd_delete_product_yes(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    
    if not params:
        return True
    
    product = product_manager.get_product(params)
    if product:
        product_manager.delete_product(params)
        send_message(
            user_id,
            f"✅ Product Deleted!\n\n📦 {product.get('name')} removed.",
            "HTML"
        )
    else:
        send_message(user_id, "Product not found", "HTML")
    return True

# ========== RESELLER MANAGEMENT ==========

@command("/admin_resellers")
def cmd_admin_resellers(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    markup = {
        "inline_keyboard": [
            [{"text": "➕ Add Reseller", "callback_data": "/addreseller_btn"}],
            [{"text": "📝 Reseller List", "callback_data": "/resellerlist_btn"}],
            [{"text": "🔙 Back", "callback_data": "/admin AP"}]
        ]
    }
    text = "💰 <b>RESELLER MANAGEMENT</b>"
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

@command("/addreseller_btn")
def cmd_addreseller_btn(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    send_message(user_id, "📩 Send user ID to add as reseller\n\nType /cancel to stop.", "HTML")
    pending_commands[user_id] = "/add_reseller_process"
    pending_commands_store.set(user_id, "/add_reseller_process")
    return True

@command("/add_reseller_process")
def cmd_add_reseller_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    try:
        target_user = str(int(text))
    except:
        send_message(user_id, "❌ Invalid User ID!", "HTML")
        return True
    
    resellers = bot_data.get_data("resellers_list") or []
    if target_user in [str(u) for u in resellers]:
        send_message(user_id, "User already a reseller.", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    resellers.append(target_user)
    bot_data.save_data("resellers_list", resellers)
    send_message(user_id, f"✅ User <code>{target_user}</code> added as Reseller.", "HTML")
    try:
        send_message(target_user, "🎉 You are now a Reseller!", "HTML")
    except:
        pass
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/resellerlist_btn")
def cmd_resellerlist_btn(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    resellers = bot_data.get_data("resellers_list") or []
    if not resellers:
        text = "No resellers found."
    else:
        text = "💰 <b>RESELLER LIST</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        count = 1
        for res in resellers:
            text += f"{count}. ID: <code>{res}</code>\n"
            count += 1
        text += f"\nTotal: {len(resellers)}"
    
    markup = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "/admin_resellers"}]]}
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

# ========== ADMIN MANAGEMENT ==========

@command("/TUSHAR_Admins")
def cmd_tushar_admins(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
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
    
    text = "👑 <b>ADMIN MANAGEMENT</b>"
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
        return True
    
    send_message(user_id, "📩 Send user ID to add as admin\n\nType /cancel to stop.", "HTML")
    pending_commands[user_id] = "/TUSHAR_AddAdmin1"
    pending_commands_store.set(user_id, "/TUSHAR_AddAdmin1")
    return True

@command("/TUSHAR_AddAdmin1")
def cmd_tushar_addadmin1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    try:
        new_admin = str(int(text))
    except:
        send_message(user_id, "❌ Invalid User ID!", "HTML")
        return True
    
    if new_admin in admins:
        send_message(user_id, "Admin already exists!", "HTML")
    else:
        admins.append(new_admin)
        bot_data.save_data("AllBotAdminss", admins)
        send_message(user_id, f"✅ Admin <code>{new_admin}</code> added!", "HTML")
    
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/ChangeAnyUserBal")
def cmd_change_balance(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    is_admin = str(user_id) in [str(a) for a in admins]
    if not is_admin:
        return True
    
    send_message(
        user_id,
        "💡 Send: <code>user_id amount</code>\nExample: <code>123456 100</code>\nUse - for deduct: <code>123456 -50</code>",
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
        return True
    
    parts = text.split(" ")
    if len(parts) < 2:
        send_message(user_id, "Invalid! Use: user_id amount", "HTML")
        return True
    
    target_user = parts[0]
    try:
        amount = float(parts[1])
    except:
        send_message(user_id, "Invalid amount!", "HTML")
        return True
    
    bal = Resources.another_res("Balance", user=target_user)
    bal.add(amount)
    
    send_message(
        user_id,
        f"✅ Added ₹{amount} to <code>{target_user}</code>\n💰 New Balance: ₹{bal.value()}",
        "HTML"
    )
    try:
        send_message(target_user, f"💰 Admin added ₹{amount} to your balance!", "HTML")
    except:
        pass
    
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/broadcast")
def cmd_broadcast(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    all_users = user_data_store.get_all_users()
    send_message(
        user_id,
        f"📢 <b>BROADCAST</b>\n━━━━━━━━━━━━━━━━━━\n👥 Users: {len(all_users)}\n\nSend message to broadcast.\nType /cancel to stop.",
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
        send_message(user_id, "No users!", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    from_chat_id = message.get("chat", {}).get("id")
    msg_id_to_forward = message.get("message_id")
    
    success = 0
    for target_user in users:
        try:
            forward_message(target_user, from_chat_id, msg_id_to_forward)
            success += 1
        except:
            try:
                if message.get("text"):
                    send_message(target_user, message.get("text", ""), "HTML")
                    success += 1
            except:
                pass
        time.sleep(0.1)
    
    send_message(
        user_id,
        f"✅ Broadcast done!\n📤 Sent: {success}/{len(users)}",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/setMyCommands")
def cmd_set_commands(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    commands_list = [{"command": "start", "description": "START"}]
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
    try:
        requests.post(url, json={"commands": commands_list})
        send_message(user_id, "✅ Commands set!", "HTML")
    except:
        send_message(user_id, "Error!", "HTML")
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
    print("🤖 Bot Started!")
    
    # Setup default products on first run
    setup_default_products()
    
    print(f"📡 API: {RESELLER_API_URL}")
    print(f"📋 Commands: {list(commands.keys())}")
    
    last_update_id = 0
    while True:
        try:
            updates = get_updates(last_update_id + 1)
            if updates:
                print(f"📥 {len(updates)} updates")
            for update in updates:
                if "update_id" in update:
                    last_update_id = update["update_id"]
                handle_update(update)
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("🛑 Bot stopped.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
