# tusharbot.py - COMPLETE HYBRID (API Key + Local Products)
import requests
import json
import time
import re
from datetime import datetime
from pymongo import MongoClient

BOT_TOKEN = "8388786589:AAFlxWhA0Jyg72HNsQydRlIqkkTedX54qjs"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ========== API CONFIGURATION ==========
API_URL = "https://xyzcheats.com/api/reseller_v1.php"
API_KEY = "b25eb076f5c0412fa9f1eba94550d02e"

# MongoDB Connection
MONGO_URI = "mongodb+srv://crasher3210_db_user:devex5656@cluster0.9y5axka.mongodb.net/?appName=Cluster0&compressors=zlib"
DB_NAME = "telegram_bot1"

# ========== FAMPAY CONFIGURATION ==========
FAMPAY_UPI = "bablu.xyztb@fam"  # <-- Yahan apna UPI ID daal dijiye
FAMPAY_API_KEY = "FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8" # <-- Yahan apni FamPay API Key daal dijiye
FAMPAY_QR_URL = "https://fampay.anujbots.xyz/qr.php"
FAMPAY_VERIFY_URL = "https://fampay.anujbots.xyz/verify.php"

# ========== PREMIUM EMOJI IDs ==========
EMOJIS = {
    "cart": "5382194935057372936",
    "back": "6039539366177541657",
    "shop": "6093739864883207194",
    "key": "5967456680940671207",
    "profile": "5346136537123801643",
    "howto": "5345783284653636765",
    "support": "5897567714674741148",
    "addfund": "6278302366303260172",
    "payproof": "5258134813302332906",
    "download": "6028115612163641653",
    "balance": "5348392971207194994",
    "success": "5348129380474306311",
    "danger": "6278116707751956084",
    "warning": "5447644880824181073",
    "info": "5195033767969839232",
    "lightbulb": "5420323339723881652",
    "clock": "5116553153419936517",
    "package": "6179339404906079822",
    "drip_emoji": "6323104647636589287",
    "silent_emoji": "6325561995995126107",
    "hg_emoji": "6210705396449944693",
    "orders": "6008118472066732010",
    "video": "5258601973167539896",
    "money": "6089104607328342288",
    "time": "6278102040438640835",
    "announce": "6264989131621798851",
    "buy": "6172208745582433583",
    "user": "5317006024517912643",
    "mykeys": "6176966310920983412",
    "edit": "5345783284653636765",
    "calendar": "5116553153419936517",
}

def emoji_tag(emoji_id, char=""):
    if char:
        return f'<tg-emoji emoji-id="{emoji_id}">{char}</tg-emoji>'
    return f'<tg-emoji emoji-id="{emoji_id}"></tg-emoji>'

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
        collections = ['bot_data', 'user_data', 'pending_commands', 'pending_payments', 
                      'processed_payments', 'payment_orders', 'products', 'plans']
        for coll in collections:
            if coll not in self.db.list_collection_names():
                self.db.create_collection(coll)
        
        self.db.bot_data.create_index("key", unique=True)
        self.db.user_data.create_index([("user_id", 1), ("key", 1)], unique=True)
        self.db.products.create_index("product_id", unique=True)
        self.db.plans.create_index([("product_id", 1), ("plan_id", 1)], unique=True)
    
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
        self.collection.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)
    
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
        self.collection.update_one({"user_id": str(user_id), "key": key}, {"$set": {"value": value}}, upsert=True)
    
    def delete(self, user_id, key):
        self.collection.delete_one({"user_id": str(user_id), "key": key})
    
    def get_all_users(self):
        return list(self.collection.distinct("user_id"))

user_data_store = UserDataStore()

class PendingCommandsStore:
    def __init__(self):
        self.collection = mongo.get_collection('pending_commands')
    
    def get(self, user_id, default=None):
        doc = self.collection.find_one({"user_id": str(user_id)})
        return doc.get("command") if doc else default
    
    def set(self, user_id, command):
        self.collection.update_one({"user_id": str(user_id)}, {"$set": {"command": command}}, upsert=True)
    
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
        self.collection.update_one({"user_id": str(user_id)}, {"$set": {"data": data}}, upsert=True)
    
    def delete(self, user_id):
        self.collection.delete_one({"user_id": str(user_id)})

pending_payments_store = PendingPaymentsStore()

class ProcessedPaymentsStore:
    def __init__(self):
        self.collection = mongo.get_collection('processed_payments')
    
    def add(self, order_id, user_id, amount):
        doc = {"order_id": order_id, "user_id": str(user_id), "amount": amount, "processed_at": datetime.now()}
        self.collection.update_one({"order_id": order_id}, {"$set": doc}, upsert=True)

processed_payments_store = ProcessedPaymentsStore()

class PaymentOrdersStore:
    def __init__(self):
        self.collection = mongo.get_collection('payment_orders')
    
    def create(self, order_id, user_id, amount, product_name=None, plan=None):
        doc = {"order_id": order_id, "user_id": str(user_id), "amount": float(amount), 
               "product_name": product_name, "plan": plan, "created_at": datetime.now(), "status": "pending"}
        self.collection.update_one({"order_id": order_id}, {"$set": doc}, upsert=True)
        return doc
    
    def get_order(self, order_id):
        return self.collection.find_one({"order_id": order_id})
    
    def mark_verified(self, order_id):
        self.collection.update_one({"order_id": order_id}, {"$set": {"status": "verified", "verified_at": datetime.now()}})
    
    def delete(self, order_id):
        self.collection.delete_one({"order_id": order_id})

payment_orders_store = PaymentOrdersStore()

# ========== PRODUCT & PLAN STORE (Local MongoDB) ==========
class ProductStore:
    def __init__(self):
        self.collection = mongo.get_collection('products')
    
    def get_all(self):
        return list(self.collection.find())
    
    def get(self, product_id):
        return self.collection.find_one({"product_id": str(product_id)})
    
    def create(self, product_id, name, emoji=None):
        doc = {"product_id": str(product_id), "name": name, "emoji": emoji or EMOJIS['package']}
        self.collection.update_one({"product_id": str(product_id)}, {"$set": doc}, upsert=True)
        return doc
    
    def delete(self, product_id):
        self.collection.delete_one({"product_id": str(product_id)})
        plan_store = PlanStore()
        plan_store.delete_by_product(product_id)

class PlanStore:
    def __init__(self):
        self.collection = mongo.get_collection('plans')
    
    def get_all(self, product_id=None):
        if product_id:
            return list(self.collection.find({"product_id": str(product_id)}))
        return list(self.collection.find())
    
    def get(self, product_id, plan_id):
        return self.collection.find_one({"product_id": str(product_id), "plan_id": str(plan_id)})
    
    def create(self, product_id, plan_id, days, price):
        doc = {"product_id": str(product_id), "plan_id": str(plan_id), "days": int(days), "price": float(price)}
        self.collection.update_one({"product_id": str(product_id), "plan_id": str(plan_id)}, {"$set": doc}, upsert=True)
        return doc
    
    def delete(self, product_id, plan_id):
        self.collection.delete_one({"product_id": str(product_id), "plan_id": str(plan_id)})
    
    def delete_by_product(self, product_id):
        self.collection.delete_many({"product_id": str(product_id)})

product_store = ProductStore()
plan_store = PlanStore()

# ========== API FUNCTIONS (FIXED: POST & BUY) ==========
def call_api(action, data=None):
    """API call karne ke liye generic function (POST Request)"""
    try:
        params = {"api_key": API_KEY, "action": action}
        if data:
            params.update(data)
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(API_URL, data=params, headers=headers, timeout=30)
        result = response.json()
        print(f"📡 API Response [{action}]: {result}")
        return result
    except Exception as e:
        print(f"❌ API Error [{action}]: {e}")
        return {"status": "error", "msg": str(e)}

def fetch_key_from_api(product_id, plan_id, user_id):
    """API se Key GENERATE aur FETCH karna"""
    # 'buy' action use kar rahe hain taaki naya key generate ho
    result = call_api("buy", {
        "product_id": str(product_id),
        "duration": str(plan_id), 
        "android_id": str(user_id) 
    })
    
    if result.get("status") == "success":
        return result.get("key") or result.get("data", {}).get("key") 
    return None

def check_api_connection():
    """API connection check"""
    result = call_api("ping")
    return result.get("status") == "success"

# ========== TELEGRAM FUNCTIONS ==========
def send_message(chat_id, text, parse_mode="HTML", reply_markup=None, disable_web_page_preview=True):
    url = f"{BASE_URL}/sendMessage"
    text = re.sub(r'<tg-emoji[^>]*>\s*</tg-emoji>', '', text)
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
    text = re.sub(r'<tg-emoji[^>]*>\s*</tg-emoji>', '', text)
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

# ========== HELPERS ==========
def get_user_data(user_id, key, default=None):
    return user_data_store.get(user_id, key, default)

def set_user_data(user_id, key, value):
    user_data_store.set(user_id, key, value)

def get_easy_time():
    current = datetime.now()
    return current.strftime("%d %b, %I:%M %p").replace("AM", "am").replace("PM", "pm")

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

pending_commands = {}
pending_payments = {}

def load_initial_data():
    global pending_commands, pending_payments
    for doc in pending_commands_store.collection.find():
        pending_commands[doc["user_id"]] = doc["command"]
    for doc in pending_payments_store.collection.find():
        pending_payments[doc["user_id"]] = doc["data"]

load_initial_data()

commands = {}

def command(name):
    def decorator(func):
        commands[name] = func
        return func
    return decorator

# ============================================================
# ========== /START ==========
# ============================================================

@command("/start")
def cmd_start(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    print(f"✅ /start received from {user_id}")
    
    if not User.get_data(user_id, "joined_date"):
        User.save_data(user_id, "joined_date", message.get("date"))
    
    balance = Resources.another_res("Balance", user=user_id).value()
    
    text = f"""<b>
{emoji_tag(EMOJIS['shop'], '🛒')} Buy Hack :</b> All key purchase & instantly delivery
<b>
{emoji_tag(EMOJIS['user'], '👤')} Profile :</b> Check your account information
<b>
{emoji_tag(EMOJIS['money'], '💰')} Add Fund :</b> Deposit balance & secure service
<b>
{emoji_tag(EMOJIS['mykeys'], '📦')} My Key :</b> Check all key purchase history
<b>
{emoji_tag(EMOJIS['video'], '🎥')} How To Use :</b> View tutorial and work this bot
<b>
{emoji_tag(EMOJIS['support'], '💬')} Support :</b> Bot problem fixed for support admin
<b>
{emoji_tag(EMOJIS['download'], '📥')} Download Apk :</b> Download latest apk for safety

{emoji_tag(EMOJIS['balance'], '💰')} Your Balance: ₹{balance}
</b>"""
    
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

# ============================================================
# ========== SHOP - LOCAL PRODUCTS ==========
# ============================================================

@command("/shopnawkk")
def cmd_shopnawkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    products = product_store.get_all()
    
    if not products:
        send_message(user_id, "❌ No products available. Add products from admin panel.", "HTML")
        return True
    
    markup = {"inline_keyboard": []}
    
    for product in products:
        product_id = product.get("product_id")
        product_name = product.get("name", "Unknown Product")
        emoji_id = product.get("emoji", EMOJIS['package'])
        
        markup["inline_keyboard"].append([
            {"text": f"📦 {product_name}", "callback_data": f"/SHOP_MOD {product_id}", "icon_custom_emoji_id": emoji_id, "style": "success"}
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

@command("/SHOP_MOD")
def cmd_shop_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    product_id = params
    if not product_id:
        send_message(user_id, "Invalid Product")
        return True
    
    User.save_data(user_id, "current_product", product_id)
    
    plans = plan_store.get_all(product_id)
    
    if not plans:
        send_message(user_id, "❌ No plans available for this product. Add plans from admin panel.", "HTML")
        return True
    
    product = product_store.get(product_id)
    product_name = product.get("name", "Product") if product else "Product"
    
    markup = {"inline_keyboard": []}
    
    for plan in plans:
        plan_id = plan.get("plan_id")
        days = plan.get("days", 0)
        price = plan.get("price", 0)
        plan_display = f"{days} Day{'s' if days > 1 else ''}"
        
        markup["inline_keyboard"].append([
            {"text": f"{plan_display} - ₹{price} {emoji_tag(EMOJIS['cart'], '🛒')}", 
             "callback_data": f"/buy_mod {product_id}_{plan_id}", 
             "style": "success"}
        ])
    
    if not markup["inline_keyboard"]:
        send_message(user_id, "❌ No valid plans available")
        return True
    
    markup["inline_keyboard"].append([
        {"text": "BACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": EMOJIS['back'], "style": "danger"}
    ])
    
    txt = f"""
━━━━━━━━━━━━━━━━━━━━
📦 {product_name}
━━━━━━━━━━━━━━━━━━━━

Choose a plan 👇
"""
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

# ============================================================
# ========== BUY - API KEY GENERATE & FETCH ==========
# ============================================================

@command("/buy_mod")
def cmd_buy_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not params:
        send_message(user_id, "❌ Invalid Product")
        return True
    
    parts = params.split("_")
    if len(parts) < 2:
        send_message(user_id, "❌ Invalid Product Format")
        return True
    
    product_id = parts[0]
    plan_id = parts[1] if len(parts) > 1 else None
    
    if not plan_id:
        send_message(user_id, "❌ Invalid Plan")
        return True
    
    plan = plan_store.get(product_id, plan_id)
    if not plan:
        send_message(user_id, "❌ Plan not found")
        return True
    
    price = plan.get("price", 0)
    days = plan.get("days", 0)
    plan_display = f"{days} Day{'s' if days > 1 else ''}"
    
    product = product_store.get(product_id)
    product_name = product.get("name", "Product") if product else "Product"
    
    title = f"{product_name}\n{plan_display}"
    
    User.save_data(user_id, "last_product1", title)
    User.save_data(user_id, "last_plan", str(days))
    User.save_data(user_id, "last_product_id", product_id)
    User.save_data(user_id, "last_plan_id", plan_id)
    
    balance = Resources.another_res("Balance", user=user_id)
    
    if balance.value() < price:
        User.save_data(user_id, "last_deposit_amount", price)
        User.save_data(user_id, "last_product", title)
        cmd_autobuy1(message, None)
        return True
    
    balance.cut(price)
    Resources.another_res("Order", user=user_id).add(1)
    
    send_message(user_id, f"{emoji_tag(EMOJIS['clock'], '⏳')} Generating your key from server...", "HTML")
    
    key = fetch_key_from_api(product_id, plan_id, user_id)
    
    if not key:
        balance.add(price)
        send_message(
            user_id,
            f"{emoji_tag(EMOJIS['danger'], '❌')} <b>Key Generation Failed!</b>\n\n"
            f"Server response error. Amount has been refunded.\n"
            f"Please try again later or contact support.",
            "HTML"
        )
        return True
    
    easy_time = get_easy_time()
    
    send_message(
        user_id,
        f"{emoji_tag(EMOJIS['buy'], '🛒')} {title}\n\n"
        f"{emoji_tag(EMOJIS['key'], '🔑')} <b>Your Generated Key:</b>\n<code>{key}</code>\n\n"
        f"{emoji_tag(EMOJIS['money'], '💰')} Deducted: ₹{price}\n"
        f"{emoji_tag(EMOJIS['time'], '⏰')} Time: {easy_time}\n\n"
        f"{emoji_tag(EMOJIS['announce'], '📢')} <b>ALL FILES UPDATE</b>\n@SUBHAJIT_UPDATES",
        "HTML"
    )
    
    adm_ac = User.get_data(user_id, "userhAC") or []
    adm_ac.append(
        f"📆 {easy_time}\n"
        f"👤 {message.get('from', {}).get('first_name', 'User')} [{user_id}]\n"
        f"💰 ₹{price}\n"
        f"🔑 {key}\n"
        f"📦 {product_name}\n"
        f"📅 {days} Days"
    )
    User.save_data(user_id, "userhAC", adm_ac)
    
    return True

# ============================================================
# ========== AUTOBUY (Insufficient Balance) ==========
# ============================================================

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
    need = max(0, float(amount) - float(balance))
    plan_display = f"{plan} Days" if plan.isdigit() else plan
    
    url = f"{FAMPAY_QR_URL}?upi={FAMPAY_UPI}&amount={amount}"
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
        f"{emoji_tag(EMOJIS['info'], 'ℹ️')} <b>Order ID:</b>\n<code>{order_id}</code>\n\n"
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

# ============================================================
# ========== VERIFY PAYMENT ==========
# ============================================================

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
        send_message(user_id, "❌ Invalid Order ID. Please generate QR again.", "HTML")
        return True
    
    if order_data.get("status") == "verified":
        send_message(user_id, "✅ This payment has already been processed.", "HTML")
        pending_payments.pop(user_id, None)
        pending_payments_store.delete(user_id)
        return True
    
    send_message(user_id, f"{emoji_tag(EMOJIS['clock'], '⏳')} Checking payment status...", "HTML")
    
    url = f"{FAMPAY_VERIFY_URL}?order_id={order_id}&api_key={FAMPAY_API_KEY}"
    
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
            f"{emoji_tag(EMOJIS['balance'], '💰')} New Balance: ₹{bal.value()}\n\n"
            f"Now go to shop and buy your product! 🛒",
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
        return True@command("/cancel")
def cmd_cancel(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
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
            payment_orders_store.delete(order_id)
    
    delete_message(user_id, msg_id)
    pending_payments.pop(user_id, None)
    pending_payments_store.delete(user_id)
    User.save_data(user_id, "last_order_id", "")
    User.save_data(user_id, "addpay_order_id", "")
    User.save_data(user_id, "payment_processed", False)
    send_message(user_id, f"{emoji_tag(EMOJIS['danger'], '❌')} Cancelled", "HTML")
    return True

# ============================================================
# ========== ADD FUNDS ==========
# ============================================================

current_amount = {}

@command("/addpayment")
def cmd_addpayment(message, params, options=None):
    user_id = message.get("from", {}).get("id")
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

for n in range(10):
    @command(f"/num{n}")
    def make_handler(num):
        def handler(message, params, options=None):
            user_id = message.get("from", {}).get("id")
            msg_id = message.get("message_id")
            amt = current_amount.get(user_id, "0")
            if num == 0:
                amt = "0" if amt == "0" else amt + "0"
            else:
                amt = str(num) if amt == "0" else amt + str(num)
            current_amount[user_id] = amt
            text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
            edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
            return True
        return handler
    globals()[f"cmd_num{n}"] = make_handler(n)

@command("/clearamt")
def cmd_clearamt(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹0\n\nUse the keypad below."
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
    
    url = f"{FAMPAY_QR_URL}?upi={FAMPAY_UPI}&amount={amount}"
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
# ========== ADMIN PANEL WITH FULL PRODUCT/PLAN MANAGEMENT ==========
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
    
    api_status = "✅ Connected" if check_api_connection() else "❌ Disconnected"
    
    markup = {
        "inline_keyboard": [
            [{"text": "👑 Admins", "callback_data": "/TUSHAR_Admins", "style": "success"}],
            [{"text": "📣 Broadcast", "callback_data": "/broadcast", "style": "success"}],
            [{"text": "💰 Add Balance", "callback_data": "/ChangeAnyUserBal", "style": "success"}],
            [{"text": "📦 Add Product", "callback_data": "/add_product", "style": "success"}],
            [{"text": "📦 Manage Products", "callback_data": "/manage_products", "style": "success"}],
            [{"text": "➕ Add Plan", "callback_data": "/add_plan", "style": "success"}],
            [{"text": "📝 Manage Plans", "callback_data": "/manage_plans", "style": "success"}],
            [{"text": f"🔗 API: {api_status}", "callback_data": "/check_api", "style": "primary"}],
            [{"text": "🔙 Back", "callback_data": "/backkkk", "style": "danger"}]
        ]
    }
    txt = f"""<b>
👋 Welcome {message.get('from', {}).get('first_name', 'Admin')} 🎉

━━━━━━━━━━━━━━━
🤖 Admin Panel
🔗 API Status : {api_status}
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
# ========== ADD PRODUCT (FIXED: SUPPORTS PID|NAME) ==========
# ============================================================

@command("/add_product")
def cmd_add_product(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    send_message(
        user_id, 
        f"{emoji_tag(EMOJIS['package'], '📦')} <b>Add New Product</b>\n\n"
        f"Send format:\n"
        f"<code>PID | PRODUCT_NAME</code> (For API matching)\n"
        f"OR just send name (Auto ID will generate)\n\n"
        f"Example: <code>153 | BALA MOD XYZ V1</code>", 
        "HTML"
    )
    pending_commands[user_id] = "/add_product_process"
    pending_commands_store.set(user_id, "/add_product_process")
    return True

@command("/add_product_process")
def cmd_add_product_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    if not text:
        send_message(user_id, "❌ Invalid name!", "HTML")
        return True
    
    # Check if user provided PID | NAME format
    if "|" in text:
        parts = text.split("|")
        if len(parts) == 2:
            product_id = parts[0].strip()
            product_name = parts[1].strip()
        else:
            send_message(user_id, "❌ Invalid format! Use: <code>PID | NAME</code>", "HTML")
            return True
    else:
        # Generate Auto ID if no PID given
        product_id = f"p{int(time.time())}"
        product_name = text
    
    product_store.create(product_id, product_name)
    
    send_message(
        user_id, 
        f"✅ Product <b>{product_name}</b> added successfully!\n\n🆔 PID: <code>{product_id}</code>\n\nNow add plans for this product using /add_plan", 
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

# ============================================================
# ========== MANAGE PRODUCTS ==========
# ============================================================

@command("/manage_products")
def cmd_manage_products(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    products = product_store.get_all()
    
    if not products:
        send_message(user_id, "❌ No products available. Add using /add_product", "HTML")
        return True
    
    markup = {"inline_keyboard": []}
    for product in products:
        product_id = product.get("product_id")
        name = product.get("name", "Unknown")
        plans = plan_store.get_all(product_id)
        plan_count = len(plans)
        markup["inline_keyboard"].append([
            {"text": f"📦 {name} ({plan_count} plans)", "callback_data": f"/view_product {product_id}", "style": "primary"}
        ])
        markup["inline_keyboard"].append([
            {"text": f"🗑️ Delete {name}", "callback_data": f"/delete_product {product_id}", "style": "danger"}
        ])
    
    markup["inline_keyboard"].append([
        {"text": "🔙 Back to Admin", "callback_data": "/admin", "style": "danger"}
    ])
    
    txt = f"""<b>📦 Manage Products</b>
━━━━━━━━━━━━━━━━━━━━━━

Total Products: {len(products)}

Select a product to manage or delete:
"""
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/view_product")
def cmd_view_product(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    product_id = params
    if not product_id:
        send_message(user_id, "❌ Invalid Product")
        return True
    
    product = product_store.get(product_id)
    if not product:
        send_message(user_id, "❌ Product not found")
        return True
    
    plans = plan_store.get_all(product_id)
    
    markup = {"inline_keyboard": []}
    
    if plans:
        for plan in plans:
            plan_id = plan.get("plan_id")
            days = plan.get("days", 0)
            price = plan.get("price", 0)
            markup["inline_keyboard"].append([
                {"text": f"📅 {days} Days - ₹{price}", "callback_data": f"/edit_plan {product_id}_{plan_id}", "style": "primary"}
            ])
            markup["inline_keyboard"].append([
                {"text": f"🗑️ Delete Plan", "callback_data": f"/delete_plan {product_id}_{plan_id}", "style": "danger"}
            ])
    else:
        markup["inline_keyboard"].append([
            {"text": "No Plans Available", "callback_data": "none", "style": "secondary"}
        ])
    
    markup["inline_keyboard"].append([
        {"text": "➕ Add Plan", "callback_data": f"/add_plan_for {product_id}", "style": "success"}
    ])
    markup["inline_keyboard"].append([
        {"text": "🔙 Back", "callback_data": "/manage_products", "style": "danger"}
    ])
    
    txt = f"""<b>📦 Product: {product.get('name', 'Unknown')}</b>
━━━━━━━━━━━━━━━━━━━━━━

🆔 ID: <code>{product_id}</code>
📅 Total Plans: {len(plans)}

Select a plan to edit or add new:
"""
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/delete_product")
def cmd_delete_product(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    product_id = params
    if not product_id:
        send_message(user_id, "❌ Invalid")
        return True
    
    product = product_store.get(product_id)
    if not product:
        send_message(user_id, "❌ Product not found")
        return True
    
    product_store.delete(product_id)
    send_message(user_id, f"✅ Product <b>{product.get('name', 'Unknown')}</b> deleted successfully!", "HTML")
    return True

# ============================================================
# ========== ADD PLAN ==========
# ============================================================

@command("/add_plan")
@command("/add_plan_for")
def cmd_add_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    # Check if product_id is passed
    product_id = params
    if not product_id:
        # Show product list to select
        products = product_store.get_all()
        if not products:
            send_message(user_id, "❌ No products available. First add a product using /add_product", "HTML")
            return True
        
        markup = {"inline_keyboard": []}
        for product in products:
            pid = product.get("product_id")
            name = product.get("name", "Unknown")
            markup["inline_keyboard"].append([
                {"text": f"📦 {name}", "callback_data": f"/add_plan_for {pid}", "style": "success"}
            ])
        markup["inline_keyboard"].append([
            {"text": "🔙 Back", "callback_data": "/admin", "style": "danger"}
        ])
        
        send_message(user_id, f"{emoji_tag(EMOJIS['package'], '➕')} <b>Select Product to Add Plan</b>", "HTML", markup)
        return True
    
    User.save_data(user_id, "add_plan_product_id", product_id)
    send_message(user_id, f"{emoji_tag(EMOJIS['calendar'], '📅')} <b>Add New Plan</b>\n\nSend plan details in format:\n<code>DAYS|PRICE</code>\n\nExample: <code>7|250</code>\n\nType /cancel to stop.", "HTML")
    pending_commands[user_id] = "/add_plan_process"
    pending_commands_store.set(user_id, "/add_plan_process")
    return True

@command("/add_plan_process")
def cmd_add_plan_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    parts = text.split("|")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid format! Use: DAYS|PRICE\nExample: 7|250", "HTML")
        return True
    
    try:
        days = int(parts[0].strip())
        price = float(parts[1].strip())
    except:
        send_message(user_id, "❌ Invalid numbers!", "HTML")
        return True
    
    if days <= 0 or price <= 0:
        send_message(user_id, "❌ Values must be greater than 0!", "HTML")
        return True
    
    product_id = User.get_data(user_id, "add_plan_product_id")
    if not product_id:
        send_message(user_id, "❌ Error: No product selected", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    plan_id = f"pl{int(time.time())}"
    plan_store.create(product_id, plan_id, days, price)
    
    product = product_store.get(product_id)
    product_name = product.get("name", "Unknown") if product else "Unknown"
    
    send_message(
        user_id,
        f"✅ <b>Plan Added Successfully!</b>\n\n"
        f"📦 Product: {product_name}\n"
        f"📅 Days: {days}\n"
        f"💰 Price: ₹{price}\n"
        f"🆔 Plan ID: <code>{plan_id}</code>",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

# ============================================================
# ========== MANAGE PLANS ==========
# ============================================================

@command("/manage_plans")
def cmd_manage_plans(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    products = product_store.get_all()
    if not products:
        send_message(user_id, "❌ No products available", "HTML")
        return True
    
    markup = {"inline_keyboard": []}
    for product in products:
        pid = product.get("product_id")
        name = product.get("name", "Unknown")
        plans = plan_store.get_all(pid)
        plan_count = len(plans)
        markup["inline_keyboard"].append([
            {"text": f"📦 {name} ({plan_count} plans)", "callback_data": f"/view_product {pid}", "style": "primary"}
        ])
    
    markup["inline_keyboard"].append([
        {"text": "🔙 Back to Admin", "callback_data": "/admin", "style": "danger"}
    ])
    
    txt = f"""<b>📝 Manage Plans</b>
━━━━━━━━━━━━━━━━━━━━━━

Select a product to view its plans:
"""
    try:
        edit_message(user_id, message.get("message_id"), txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/edit_plan")
def cmd_edit_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    if not params:
        send_message(user_id, "❌ Invalid")
        return True
    
    parts = params.split("_")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid format!")
        return True
    
    product_id = parts[0]
    plan_id = parts[1]
    
    plan = plan_store.get(product_id, plan_id)
    if not plan:
        send_message(user_id, "❌ Plan not found")
        return True
    
    User.save_data(user_id, "edit_plan_product_id", product_id)
    User.save_data(user_id, "edit_plan_plan_id", plan_id)
    
    send_message(
        user_id,
        f"""<b>✏️ Edit Plan</b>
━━━━━━━━━━━━━━━━━━━━━━

Current: {plan.get('days', 0)} Days - ₹{plan.get('price', 0)}

Send new details in format:
<code>DAYS|PRICE</code>

Example: <code>10|300</code>

Type /cancel to stop.""",
        "HTML"
    )
    pending_commands[user_id] = "/edit_plan_process"
    pending_commands_store.set(user_id, "/edit_plan_process")
    return True

@command("/edit_plan_process")
def cmd_edit_plan_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    parts = text.split("|")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid format! Use: DAYS|PRICE", "HTML")
        return True
    
    try:
        days = int(parts[0].strip())
        price = float(parts[1].strip())
    except:
        send_message(user_id, "❌ Invalid numbers!", "HTML")
        return True
    
    if days <= 0 or price <= 0:
        send_message(user_id, "❌ Values must be greater than 0!", "HTML")
        return True
    
    product_id = User.get_data(user_id, "edit_plan_product_id")
    plan_id = User.get_data(user_id, "edit_plan_plan_id")
    
    if not product_id or not plan_id:
        send_message(user_id, "❌ Error", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    plan_store.delete(product_id, plan_id)
    plan_store.create(product_id, plan_id, days, price)
    
    send_message(
        user_id,
        f"✅ <b>Plan Updated!</b>\n\n"
        f"📅 Days: {days}\n"
        f"💰 Price: ₹{price}",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/delete_plan")
def cmd_delete_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    if not params:
        send_message(user_id, "❌ Invalid")
        return True    
    parts = params.split("_")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid format!")
        return True
    
    product_id = parts[0]
    plan_id = parts[1]
    
    plan = plan_store.get(product_id, plan_id)
    if not plan:
        send_message(user_id, "❌ Plan not found")
        return True
    
    plan_store.delete(product_id, plan_id)
    send_message(user_id, f"✅ Plan deleted: {plan.get('days', 0)} Days - ₹{plan.get('price', 0)}", "HTML")
    return True

# ============================================================
# ========== CHECK API ==========
# ============================================================

@command("/check_api")
def cmd_check_api(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    if check_api_connection():
        send_message(user_id, f"{emoji_tag(EMOJIS['success'], '✅')} API is connected successfully!\n\nURL: {API_URL}", "HTML")
    else:
        send_message(user_id, f"{emoji_tag(EMOJIS['danger'], '❌')} API is not responding!\n\nURL: {API_URL}\n\nPlease check your API key and endpoint.", "HTML")
    return True

# ============================================================
# ========== TUSHAR ADMINS ==========
# ============================================================

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

# ============================================================
# ========== CHANGE USER BALANCE ==========
# ============================================================

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
    send_message(
        user_id,
        f"<b>💰 Account Of <a href='tg://user?id={target_user}'>{target_user}</a> Was Increased By {amount}\n\nFinal Balance = {bal.value()}</b>",
        "HTML"
    )
    send_message(
        target_user,
        f"<b>💰 Admin Added ₹{amount} to your balance!</b>\n\nNew Balance: ₹{bal.value()}",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

# ============================================================
# ========== BROADCAST ==========
# ============================================================

@command("/broadcast")
def cmd_broadcast(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    
    all_users = user_data_store.get_all_users()
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
    
    if message.get("text", "").strip() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    users = User.get_data(user_id, "broadcast_users") or []
    if not users:
        send_message(user_id, "No users", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    from_chat = message.get("chat", {}).get("id")
    msg_id = message.get("message_id")
    
    success = 0
    failed = 0
    
    for target in users:
        try:
            forward_message(target, from_chat, msg_id)
            success += 1
        except:
            failed += 1
        time.sleep(0.1)
    
    send_message(
        user_id,
        f"✅ <b>Broadcast Complete</b>\n✅ Success: {success}\n❌ Failed: {failed}",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

# ============================================================
# ========== MAIN ==========
# ============================================================

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
    print("🤖 Bot Started with Hybrid System (API Key + Local Products)!")
    print(f"📁 Connected to MongoDB: {DB_NAME}")
    print(f"🔗 API URL: {API_URL}")
    print(f"📋 Registered commands: {list(commands.keys())}")
    
    if check_api_connection():
        print("✅ API Connected Successfully!")
    else:
        print("❌ API Connection Failed! Key fetch might not work.")
    
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
