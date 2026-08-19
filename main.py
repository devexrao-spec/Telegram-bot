# tusharbot.py - COMPLETE FIXED WITH CORRECT EMOJI
import requests
import json
import time
from datetime import datetime
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
        return list(self.collection.distinct("user_id"))

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
        self.collection.update_one({"order_id": order_id}, {"$set": doc}, upsert=True)
        print(f"💾 Stored processed payment: order={order_id}")
    
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
        self.collection.update_one({"order_id": order_id}, {"$set": doc}, upsert=True)
        print(f"📝 STORED: order={order_id} -> user={user_id}")
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

# ========== HELPER FUNCTIONS ==========
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

def get_easy_time():
    current = datetime.now()
    return current.strftime("%d %b, %I:%M %p").replace("AM", "am").replace("PM", "pm")

# ========== DATA STORE HELPERS ==========
def get_user_data(user_id, key, default=None):
    return user_data_store.get(user_id, key, default)

def set_user_data(user_id, key, value):
    user_data_store.set(user_id, key, value)

pending_commands = {}
pending_payments = {}

def load_initial_data():
    global pending_commands, pending_payments
    for doc in pending_commands_store.collection.find():
        pending_commands[doc["user_id"]] = doc["command"]
    for doc in pending_payments_store.collection.find():
        pending_payments[doc["user_id"]] = doc["data"]

load_initial_data()

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

# ============================================================
# ========== MAIN COMMANDS ==========
# ============================================================

@command("/start")
def cmd_start(message, params, options=None):
    user_id = message.get("from", {}).get("id")
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

@command("/shopnawkk")
def cmd_shopnawkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    mods = bot_data.get_data("mods_list") or ["drip", "SILENT", "HG"]
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
        for doc in bot_data.find():
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

@command("/SHOP_MOD")
def cmd_shop_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    mod_id = params
    if not mod_id:
        send_message(user_id, "Invalid Product")
        return True
    
    User.save_data(user_id, "current_mod", mod_id)
    
    plans = []
    plan_names = bot_data.get_data("plan_names") or {}
    
    for doc in bot_data.find():
        key = doc.get("key", "")
        if key.startswith(mod_id + "_") and "d_price" in key:
            try:
                parts = key.split("_")
                for part in parts:
                    if part.endswith("d") and part[:-1].isdigit():
                        day = int(part[:-1])
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
            # FIXED: Using correct premium emoji with full ID
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

@command("/buy_mod")
def cmd_buy_mod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not params:
        send_message(user_id, "❌ Invalid Product")
        return True
    
    # FIXED: Proper parsing for mod_id with underscores
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
        send_message(user_id, "❌ Product not available")
        return True
    
    keys = bot_data.get_data(keys_key) or []
    if len(keys) == 0:
        send_message(user_id, "❌ Out of Stock")
        return True
    
    resellers = bot_data.get_data("resellers_list") or []
    if str(user_id) in [str(u) for u in resellers]:
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
    
    # Check balance
    balance = Resources.another_res("Balance", user=user_id)
    if balance.value() < price:
        User.save_data(user_id, "last_deposit_amount", price)
        User.save_data(user_id, "last_product", title)
        cmd_autobuy1(message, None)
        return True
    
    # Deduct balance and give key
    balance.cut(price)
    Resources.another_res("Order", user=user_id).add(1)
    key = str(keys[0])
    keys.pop(0)
    bot_data.save_data(keys_key, keys)
    easy_time = get_easy_time()
    
    send_message(
        user_id,
        f"{emoji_tag(EMOJIS['buy'], '🛒')} {title}\n\n"
        f"{emoji_tag(EMOJIS['key'], '🔑')} <b>Your Key:</b>\n<code>{key}</code>\n\n"
        f"{emoji_tag(EMOJIS['money'], '💰')} Deducted: ₹{price}\n"
        f"{emoji_tag(EMOJIS['mykeys'], '📦')} Remaining Stock: {len(keys)}\n"
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
    )
    User.save_data(user_id, "userhAC", adm_ac)
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
    need = max(0, float(amount) - float(balance))
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
    pending_payments[user_id] = {"order_id": order_id, "user_id": str(user_id)}
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

@command("/verify_payment")
def cmd_verify_payment(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    order_id = params
    
    if not order_id:
        send_message(user_id, "No order ID found.", "HTML")
        return True
    
    order_data = payment_orders_store.get_order(order_id)
    if not order_data:
        send_message(user_id, "❌ Invalid Order ID.", "HTML")
        return True
    
    if order_data.get("status") == "verified":
        send_message(user_id, "✅ Payment already processed.", "HTML")
        pending_payments.pop(user_id, None)
        pending_payments_store.delete(user_id)
        return True
    
    send_message(user_id, f"{emoji_tag(EMOJIS['clock'], '⏳')} Checking payment...", "HTML")
    
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
        pending_payments.pop(user_id, None)
        pending_payments_store.delete(user_id)
        
        send_message(
            user_id,
            f"{emoji_tag(EMOJIS['success'], '✅')} <b>Payment Success!</b>\n\n"
            f"{emoji_tag(EMOJIS['money'], '💰')} Added: ₹{amount}\n"
            f"{emoji_tag(EMOJIS['balance'], '💰')} New Balance: ₹{bal.value()}",
            "HTML"
        )
        return True
    else:
        send_message(
            user_id,
            f"{emoji_tag(EMOJIS['danger'], '❌')} <b>Payment Not Found</b>\n\n"
            f"Order ID: <code>{order_id}</code>\n\n"
            f"Please complete payment and try again.",
            "HTML"
        )
        return True

@command("/cancel")
def cmd_cancel(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    msg_id = message.get("message_id")
    
    order_id = params or None
    
    if order_id:
        order_data = payment_orders_store.get_order(order_id)
        if order_data:
            payment_orders_store.delete(order_id)
    
    if msg_id:
        delete_message(user_id, msg_id)
    
    pending_payments.pop(user_id, None)
    pending_payments_store.delete(user_id)
    User.save_data(user_id, "last_order_id", "")
    send_message(user_id, f"{emoji_tag(EMOJIS['danger'], '❌')} Cancelled", "HTML")
    return True

# ========== ADD FUNDS ==========
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

# Number buttons handlers
for num in range(10):
    @command(f"/num{num}")
    def make_num_handler(n):
        def handler(message, params, options=None):
            user_id = message.get("from", {}).get("id")
            msg_id = message.get("message_id")
            amt = current_amount.get(user_id, "0")
            if n == 0:
                amt = "0" if amt == "0" else amt + "0"
            else:
                amt = str(n) if amt == "0" else amt + str(n)
            current_amount[user_id] = amt
            text = f"{emoji_tag(EMOJIS['money'], '💰')} ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below."
            edit_message(user_id, msg_id, text, "HTML", message.get("reply_markup"))
            return True
        return handler
    globals()[f"cmd_num{num}"] = make_num_handler(num)

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
    pending_payments[user_id] = {"order_id": order_id, "user_id": str(user_id)}
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

# ========== OTHER COMMANDS ==========

@command("/backkkk")
def cmd_backkkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
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
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/orderksk")
def cmd_orderksk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    adm_ac = User.get_data(user_id, "userhAC") or []
    if not adm_ac:
        textn = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{emoji_tag(EMOJIS['orders'], '📦')} <b>MY ORDERS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "You haven't placed any orders yet.\n"
            f"Tap {emoji_tag(EMOJIS['shop'], '🛒')} Shop Now!"
        )
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
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji_tag(EMOJIS['user'], '👤')} YOUR PROFILE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Name: {first_name}\n"
        f"🆔 User ID: {user_id}\n"
        f"{emoji_tag(EMOJIS['balance'], '💰')} Balance: ₹{balance}\n"
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
        send_message(user_id, "🚫 You Are Not This Bot Admin", "HTML")
        return True
    
    markup = {
        "inline_keyboard": [
            [{"text": "👑 Admins", "callback_data": "/TUSHAR_Admins", "style": "success"}],
            [{"text": "📣 Broadcast", "callback_data": "/broadcast", "style": "success"}],
            [{"text": "💰 Add Balance", "callback_data": "/ChangeAnyUserBal", "style": "success"}],
            [{"text": "📦 Manage Mods", "callback_data": "/manage_mods", "style": "success"}],
            [{"text": "💰 Add Reseller", "callback_data": "/addreseller", "style": "success"}],
            [{"text": "⛔ Remove Reseller", "callback_data": "/removereseller", "style": "danger"}],
            [{"text": "📝 Reseller List", "callback_data": "/resellerlist", "style": "success"}],
            [{"text": "🔙 Back", "callback_data": "/backkkk", "style": "danger"}]
        ]
    }
    
    txt = f"""<b>
👋 Welcome {message.get('from', {}).get('first_name', 'Admin')} 🎉

━━━━━━━━━━━━━━━
🤖 Admin Panel
━━━━━━━━━━━━━━━
</b>"""
    
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

# ========== MANAGE MODS ==========

@command("/manage_mods")
def cmd_manage_mods(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    mods = bot_data.get_data("mods_list") or ["drip", "SILENT", "HG"]
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
            display_name = bot_data.get_data(f"{mod}_display_name") or mod
        
        markup["inline_keyboard"].append([
            {"text": f"📦 {display_name}", "callback_data": f"/manage_mod {mod}", "style": "success"}
        ])
    
    markup["inline_keyboard"].append([
        {"text": "➕ ADD NEW MOD", "callback_data": "/add_new_mod", "style": "success"}
    ])
    markup["inline_keyboard"].append([
        {"text": "🔙 BACK", "callback_data": "/admin", "style": "danger"}
    ])
    
    txt = "<b>📦 MANAGE MODS</b>\n━━━━━━━━━━━━━━━━━━━━━━\nSelect a mod to manage:"
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
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    mod_id = params
    if not mod_id:
        send_message(user_id, "❌ Invalid")
        return True
    
    plans = []
    for doc in bot_data.find():
        key = doc.get("key", "")
        if key.startswith(mod_id + "_") and "d_price" in key:
            try:
                parts = key.split("_")
                for part in parts:
                    if part.endswith("d") and part[:-1].isdigit():
                        day = int(part[:-1])
                        plans.append(day)
                        break
            except:
                pass
    
    plans = sorted(list(set(plans)))
    plan_names = bot_data.get_data("plan_names") or {}
    
    markup = {"inline_keyboard": []}
    for day in plans:
        price = bot_data.get_data(f"{mod_id}_{day}d_price") or 0
        stock = len(bot_data.get_data(f"{mod_id}_{day}d_keys") or [])
        plan_key = f"{mod_id}_{day}"
        plan_display = plan_names.get(plan_key, f"{day} Day")
        markup["inline_keyboard"].append([
            {"text": f"📅 {plan_display} - ₹{price} | 🔑{stock}", "callback_data": f"/edit_plan {mod_id}_{day}", "style": "primary"}
        ])
    
    markup["inline_keyboard"].append([
        {"text": "➕ ADD NEW PLAN", "callback_data": f"/add_new_plan {mod_id}", "style": "success"}
    ])
    markup["inline_keyboard"].append([
        {"text": "🔙 BACK", "callback_data": "/manage_mods", "style": "danger"}
    ])
    
    display_name = mod_id.upper()
    if mod_id == "drip":
        display_name = "DRIP CLIENT"
    elif mod_id == "SILENT":
        display_name = "SILENT CHEATS"
    elif mod_id == "HG":
        display_name = "PRIME HOOK"
    else:
        display_name = bot_data.get_data(f"{mod_id}_display_name") or mod_id
    
    txt = f"<b>📦 Managing: {display_name}</b>\n━━━━━━━━━━━━━━━━━━━━━━\nTotal Plans: {len(plans)}\nSelect a plan to edit:"
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/edit_plan")
def cmd_edit_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
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
    
    markup = {
        "inline_keyboard": [
            [{"text": "💰 Edit Price", "callback_data": f"/edit_price {mod_id}_{day}", "style": "success"}],
            [{"text": "💰 Edit Reseller Price", "callback_data": f"/edit_reseller_price {mod_id}_{day}", "style": "success"}],
            [{"text": "🔑 Add Keys", "callback_data": f"/add_keys_plan {mod_id}_{day}", "style": "success"}],
            [{"text": "🗑️ Remove Plan", "callback_data": f"/remove_plan {mod_id}_{day}", "style": "danger"}],
            [{"text": "🔙 Back", "callback_data": f"/manage_mod {mod_id}", "style": "danger"}]
        ]
    }
    
    price = bot_data.get_data(f"{mod_id}_{day}d_price") or 0
    reseller = bot_data.get_data(f"{mod_id}_{day}d_reseller_price") or 0
    stock = len(bot_data.get_data(f"{mod_id}_{day}d_keys") or [])
    plan_names = bot_data.get_data("plan_names") or {}
    plan_key = f"{mod_id}_{day}"
    plan_display = plan_names.get(plan_key, f"{day} Day")
    
    txt = f"""
<b>📅 Editing Plan: {mod_id.upper()} - {plan_display}</b>
━━━━━━━━━━━━━━━━━━━━━━

💰 Price: ₹{price}
💰 Reseller: ₹{reseller}
🔑 Stock: {stock}

Select what to edit:
"""
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True

@command("/edit_price")
def cmd_edit_price(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    User.save_data(user_id, "editing_price", params)
    send_message(user_id, f"💰 Enter new price for {params}:\nSend number only.", "HTML")
    pending_commands[user_id] = "/edit_price_process"
    pending_commands_store.set(user_id, "/edit_price_process")
    return True

@command("/edit_price_process")
def cmd_edit_price_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    price_key = User.get_data(user_id, "editing_price")
    if not price_key:
        send_message(user_id, "❌ Error")
        return True
    
    try:
        price = float(text)
        if price <= 0:
            send_message(user_id, "❌ Price must be > 0")
            return True
        
        bot_data.save_data(f"{price_key}d_price", price)
        send_message(user_id, f"✅ Price updated: ₹{price}")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "editing_price", None)
    except:
        send_message(user_id, "❌ Invalid number!")
    return True

@command("/edit_reseller_price")
def cmd_edit_reseller_price(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    User.save_data(user_id, "editing_reseller_price", params)
    send_message(user_id, f"💰 Enter new reseller price for {params}:\nSend number only.", "HTML")
    pending_commands[user_id] = "/edit_reseller_price_process"
    pending_commands_store.set(user_id, "/edit_reseller_price_process")
    return True

@command("/edit_reseller_price_process")
def cmd_edit_reseller_price_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    price_key = User.get_data(user_id, "editing_reseller_price")
    if not price_key:
        send_message(user_id, "❌ Error")
        return True
    
    try:
        price = float(text)
        if price <= 0:
            send_message(user_id, "❌ Price must be > 0")
            return True
        
        bot_data.save_data(f"{price_key}d_reseller_price", price)
        send_message(user_id, f"✅ Reseller price updated: ₹{price}")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "editing_reseller_price", None)
    except:
        send_message(user_id, "❌ Invalid number!")
    return True

@command("/add_keys_plan")
def cmd_add_keys_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    if not params:
        send_message(user_id, "❌ Invalid")
        return True
    
    parts = params.split("_")
    if len(parts) != 2:
        send_message(user_id, "❌ Invalid format! Use: mod_id_day")
        return True
    
    mod_id = parts[0]
    day = parts[1]
    key_name = f"{mod_id}_{day}d_keys"
    
    User.save_data(user_id, "add_keys_key_name", key_name)
    User.save_data(user_id, "add_keys_mod", mod_id)
    User.save_data(user_id, "add_keys_day", day)
    
    stock = len(bot_data.get_data(key_name) or [])
    send_message(
        user_id,
        f"🔑 Add keys for {mod_id.upper()} - {day} Day\nCurrent Stock: {stock}\n\nSend keys one per line.\nType DONE to finish.",
        "HTML"
    )
    pending_commands[user_id] = "/add_keys_process_final"
    pending_commands_store.set(user_id, "/add_keys_process_final")
    return True

@command("/add_keys_process_final")
def cmd_add_keys_process_final(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    key_name = User.get_data(user_id, "add_keys_key_name")
    if not key_name:
        send_message(user_id, "❌ Error")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    if text.upper() == "DONE":
        mod = User.get_data(user_id, "add_keys_mod") or "Unknown"
        day = User.get_data(user_id, "add_keys_day") or "Unknown"
        stock = len(bot_data.get_data(key_name) or [])
        send_message(
            user_id,
            f"✅ All keys added!\n📦 Mod: {mod.upper()}\n📅 Day: {day}\n🔑 Total: {stock}",
            "HTML"
        )
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "add_keys_key_name", None)
        User.save_data(user_id, "add_keys_mod", None)
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
    send_message(
        user_id,
        f"✅ Added {added} key(s)\nTotal Stock: {len(existing)}\nSend more keys or type DONE.",
        "HTML"
    )
    return True

@command("/remove_plan")
def cmd_remove_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
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
    
    price_key = f"{mod_id}_{day}d_price"
    reseller_key = f"{mod_id}_{day}d_reseller_price"
    keys_key = f"{mod_id}_{day}d_keys"
    
    bot_data.delete(price_key)
    bot_data.delete(reseller_key)
    bot_data.delete(keys_key)
    
    send_message(user_id, f"✅ Plan {mod_id.upper()} - {day} Day removed!")
    cmd_manage_mod(message, mod_id, None)
    return True

@command("/add_new_plan")
def cmd_add_new_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    mod_id = params
    User.save_data(user_id, "add_plan_mod", mod_id)
    
    send_message(
        user_id,
        f"➕ Add new plan for {mod_id.upper()}\n\nFormat: DAYS|PRICE|RESELLER_PRICE\nExample: 7|250|200",
        "HTML"
    )
    pending_commands[user_id] = "/add_new_plan_process"
    pending_commands_store.set(user_id, "/add_new_plan_process")
    return True

@command("/add_new_plan_process")
def cmd_add_new_plan_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    mod_id = User.get_data(user_id, "add_plan_mod")
    if not mod_id:
        send_message(user_id, "❌ Error")
        return True
    
    parts = text.split("|")
    if len(parts) != 3:
        send_message(user_id, "❌ Format: DAYS|PRICE|RESELLER_PRICE")
        return True
    
    try:
        days = int(parts[0].strip())
        price = float(parts[1].strip())
        reseller_price = float(parts[2].strip())
    except:
        send_message(user_id, "❌ Invalid numbers!")
        return True
    
    if days <= 0 or price <= 0 or reseller_price <= 0:
        send_message(user_id, "❌ All values must be > 0!")
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
    
    send_message(
        user_id,
        f"✅ Plan added!\n📦 {mod_id.upper()}\n📅 {days} Days\n💰 ₹{price}\n💰 Reseller: ₹{reseller_price}",
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
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    send_message(
        user_id,
        "➕ Add New Mod\n\nSend mod name:\nExample: VIP MOD\n\nType /cancel to stop.",
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
        send_message(user_id, "❌ Cancelled")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    mod_name = text.strip()
    if not mod_name:
        send_message(user_id, "❌ Invalid name!")
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
        f"✅ Mod '{mod_name}' created!\n\nAdd plans using 'Add New Plan' button.",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

# ========== RESELLER COMMANDS ==========

@command("/addreseller")
def cmd_addreseller(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    send_message(user_id, "📩 Send reseller ID:", "HTML")
    pending_commands[user_id] = "/add_reseller_process"
    pending_commands_store.set(user_id, "/add_reseller_process")
    return True

@command("/add_reseller_process")
def cmd_add_reseller_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    target = message.get("text", "").strip()
    
    try:
        target = str(int(target))
    except:
        send_message(user_id, "❌ Invalid ID!")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    resellers = bot_data.get_data("resellers_list") or []
    if target in [str(u) for u in resellers]:
        send_message(user_id, "❌ Already a reseller")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    resellers.append(target)
    bot_data.save_data("resellers_list", resellers)
    send_message(user_id, f"✅ User <code>{target}</code> added as reseller", "HTML")
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

@command("/removereseller")
def cmd_removereseller(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    send_message(user_id, "📩 Send reseller ID to remove:", "HTML")
    pending_commands[user_id] = "/remove_reseller_process"
    pending_commands_store.set(user_id, "/remove_reseller_process")
    return True

@command("/remove_reseller_process")
def cmd_remove_reseller_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    target = message.get("text", "").strip()
    
    try:
        target = str(int(target))
    except:
        send_message(user_id, "❌ Invalid ID!")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    resellers = bot_data.get_data("resellers_list") or []
    if target not in [str(u) for u in resellers]:
        send_message(user_id, "❌ Not a reseller")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    resellers = [u for u in resellers if str(u) != target]
    bot_data.save_data("resellers_list", resellers)
    send_message(user_id, f"✅ User <code>{target}</code> removed from resellers", "HTML")
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
    
    text = "📝 Reseller List\n━━━━━━━━━━━━━━━\n"
    for i, r in enumerate(resellers, 1):
        text += f"{i}. <code>{r}</code>\n"
    text += f"\nTotal: {len(resellers)}"
    send_message(user_id, text, "HTML")
    return True

# ========== BROADCAST ==========

@command("/broadcast")
def cmd_broadcast(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if str(user_id) not in [str(a) for a in admins]:
        return True
    
    users = user_data_store.get_all_users()
    User.save_data(user_id, "broadcast_users", users)
    
    send_message(
        user_id,
        f"📢 BROADCAST MODE\n\n👥 Total Users: {len(users)}\n\nSend any message\nType /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/broadcast_send_media"
    pending_commands_store.set(user_id, "/broadcast_send_media")
    return True

@command("/broadcast_send_media")
def cmd_broadcast_send_media(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    
    if message.get("text", "").strip() == "/cancel":
        send_message(user_id, "❌ Cancelled")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    
    users = User.get_data(user_id, "broadcast_users") or []
    if not users:
        send_message(user_id, "No users")
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
        f"✅ Broadcast Complete\n✅ Success: {success}\n❌ Failed: {failed}",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True

# ========== MAIN ==========

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
    print(f"📋 Commands: {list(commands.keys())}")
    
    last_update_id = 0
    while True:
        try:
            updates = get_updates(last_update_id + 1)
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
