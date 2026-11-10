# ALLWORK.py - COMPLETE DYNAMIC PRODUCT SYSTEM
import requests
import json
import time
from datetime import datetime
import threading
from pymongo import MongoClient

BOT_TOKEN = "8485830461:AAEGCqN0jI-C49mphJNFCnXVnnlDihPJXYI"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

MONGO_URI = "mongodb+srv://crasher3210_db_user:devex5656@cluster0.9y5axka.mongodb.net/?appName=Cluster0&compressors=zlib"
DB_NAME = "telegram_bot1"


# ═══════════════════════════════════════════════════════
#  MONGODB
# ═══════════════════════════════════════════════════════
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
        cols = [
            'bot_data', 'user_data', 'pending_commands',
            'pending_payments', 'processed_payments',
            'payment_orders', 'products',
        ]
        existing = self.db.list_collection_names()
        for c in cols:
            if c not in existing:
                self.db.create_collection(c)

        self.db.bot_data.create_index("key", unique=True)
        self.db.user_data.create_index([("user_id", 1), ("key", 1)], unique=True)
        self.db.pending_payments.create_index("user_id", unique=True)
        self.db.processed_payments.create_index("order_id", unique=True)
        self.db.processed_payments.create_index("user_id")
        self.db.payment_orders.create_index("order_id", unique=True)
        self.db.payment_orders.create_index("user_id")
        self.db.payment_orders.create_index("status")
        self.db.products.create_index("pid", unique=True)

    def get_collection(self, name):
        return self.db[name]


mongo = MongoDB()


# ═══════════════════════════════════════════════════════
#  STORES
# ═══════════════════════════════════════════════════════
class DataStore:
    def __init__(self):
        self.collection = mongo.get_collection('bot_data')

    def get(self, key, default=None):
        doc = self.collection.find_one({"key": key})
        return doc.get("value") if doc else default

    def set(self, key, value):
        self.collection.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

    get_data = get
    save_data = set

    def get_all(self):
        return {d["key"]: d["value"] for d in self.collection.find()}


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
            {"$set": {"value": value}}, upsert=True
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
        self.collection.update_one(
            {"order_id": order_id},
            {"$set": {
                "order_id": order_id, "user_id": str(user_id),
                "amount": amount, "processed_at": datetime.now()
            }}, upsert=True
        )

    def exists(self, order_id):
        return self.collection.find_one({"order_id": order_id}) is not None


processed_payments_store = ProcessedPaymentsStore()


class PaymentOrdersStore:
    def __init__(self):
        self.collection = mongo.get_collection('payment_orders')

    def create(self, order_id, user_id, amount, product_name=None, plan=None):
        self.collection.update_one(
            {"order_id": order_id},
            {"$set": {
                "order_id": order_id, "user_id": str(user_id),
                "amount": float(amount), "product_name": product_name,
                "plan": plan, "created_at": datetime.now(), "status": "pending"
            }}, upsert=True
        )

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


# ═══════════════════════════════════════════════════════
#  DYNAMIC PRODUCTS STORE
# ═══════════════════════════════════════════════════════
class ProductsStore:
    """
    Schema:
    {
      pid: int,
      name: str,
      slug: str,
      active: bool,
      plans: [ {days: int, price: float, reseller_price: float, stock: [str]} ],
      created_at
    }
    """
    def __init__(self):
        self.collection = mongo.get_collection('products')

    def create(self, pid, name, slug):
        doc = {
            "pid": int(pid),
            "name": name,
            "slug": slug.strip().lower().replace(" ", "_"),
            "active": True,
            "plans": [],
            "created_at": datetime.now()
        }
        self.collection.update_one({"pid": int(pid)}, {"$setOnInsert": doc}, upsert=True)
        return doc

    def get(self, pid):
        return self.collection.find_one({"pid": int(pid)})

    def get_by_slug(self, slug):
        return self.collection.find_one({"slug": slug})

    def get_all(self, active_only=True):
        q = {"active": True} if active_only else {}
        return list(self.collection.find(q).sort("pid", 1))

    def delete(self, pid):
        self.collection.delete_one({"pid": int(pid)})

    def set_active(self, pid, active):
        self.collection.update_one({"pid": int(pid)}, {"$set": {"active": bool(active)}})

    def add_plan(self, pid, days, price, reseller_price=None):
        doc = self.get(pid)
        if not doc:
            return False, "product not found"
        plans = doc.get("plans", [])
        plans = [p for p in plans if p.get("days") != int(days)]
        plans.append({
            "days": int(days),
            "price": float(price),
            "reseller_price": float(reseller_price if reseller_price is not None else price),
            "stock": []
        })
        plans.sort(key=lambda p: p["days"])
        self.collection.update_one({"pid": int(pid)}, {"$set": {"plans": plans}})
        return True, "plan added"

    def remove_plan(self, pid, days):
        doc = self.get(pid)
        if not doc:
            return False, "product not found"
        plans = [p for p in doc.get("plans", []) if p.get("days") != int(days)]
        self.collection.update_one({"pid": int(pid)}, {"$set": {"plans": plans}})
        return True, "plan removed"

    def set_price(self, pid, days, price, reseller=False):
        doc = self.get(pid)
        if not doc:
            return False, "product not found"
        plans = doc.get("plans", [])
        for p in plans:
            if p.get("days") == int(days):
                if reseller:
                    p["reseller_price"] = float(price)
                else:
                    p["price"] = float(price)
                self.collection.update_one({"pid": int(pid)}, {"$set": {"plans": plans}})
                return True, "price updated"
        return False, f"plan {days}d not found"

    def add_stock(self, pid, days, keys):
        doc = self.get(pid)
        if not doc:
            return False, "product not found"
        plans = doc.get("plans", [])
        for p in plans:
            if p.get("days") == int(days):
                stock = p.get("stock", [])
                stock.extend(keys)
                p["stock"] = stock
                self.collection.update_one({"pid": int(pid)}, {"$set": {"plans": plans}})
                return True, len(stock)
        return False, f"plan {days}d not found"

    def pop_stock(self, pid, days):
        doc = self.get(pid)
        if not doc:
            return None
        plans = doc.get("plans", [])
        for p in plans:
            if p.get("days") == int(days):
                stock = p.get("stock", [])
                if not stock:
                    return None
                key = stock.pop(0)
                p["stock"] = stock
                self.collection.update_one({"pid": int(pid)}, {"$set": {"plans": plans}})
                return key
        return None

    def stock_count(self, pid, days):
        doc = self.get(pid)
        if not doc:
            return 0
        for p in doc.get("plans", []):
            if p.get("days") == int(days):
                return len(p.get("stock", []))
        return 0


products_store = ProductsStore()


# ═══════════════════════════════════════════════════════
#  SEED DEFAULT PRODUCTS (first run only)
# ═══════════════════════════════════════════════════════
def seed_default_products():
    if products_store.get_all(active_only=False):
        return
    defaults = [
        {
            "pid": 1, "name": "DRIP CLIENT NON-ROOT", "slug": "drip",
            "plans": [
                {"days": 1, "price": 108, "reseller_price": 95},
                {"days": 3, "price": 260, "reseller_price": 220},
                {"days": 7, "price": 360, "reseller_price": 320},
                {"days": 15, "price": 560, "reseller_price": 480},
                {"days": 30, "price": 810, "reseller_price": 750},
            ]
        },
        {
            "pid": 2, "name": "SILENT CHEATS ANDROID", "slug": "silent",
            "plans": [
                {"days": 1, "price": 108, "reseller_price": 95},
                {"days": 3, "price": 260, "reseller_price": 220},
                {"days": 7, "price": 360, "reseller_price": 320},
                {"days": 14, "price": 560, "reseller_price": 480},
                {"days": 28, "price": 810, "reseller_price": 750},
            ]
        },
        {
            "pid": 4, "name": "PRIME HOOK", "slug": "prime",
            "plans": [
                {"days": 1, "price": 108, "reseller_price": 95},
                {"days": 3, "price": 200, "reseller_price": 180},
                {"days": 7, "price": 360, "reseller_price": 320},
                {"days": 14, "price": 600, "reseller_price": 550},
                {"days": 21, "price": 700, "reseller_price": 650},
            ]
        },
    ]
    for d in defaults:
        products_store.create(d["pid"], d["name"], d["slug"])
        for pl in d["plans"]:
            products_store.add_plan(
                d["pid"], pl["days"], pl["price"], pl["reseller_price"]
            )


seed_default_products()


# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════
def get_user_data(user_id, key, default=None):
    return user_data_store.get(user_id, key, default)


def set_user_data(user_id, key, value):
    user_data_store.set(user_id, key, value)


pending_commands = {}
pending_payments = {}


def load_initial_data():
    for doc in pending_commands_store.collection.find():
        pending_commands[doc["user_id"]] = doc["command"]
    for doc in pending_payments_store.collection.find():
        pending_payments[doc["user_id"]] = doc["data"]


load_initial_data()


# ═══════════════════════════════════════════════════════
#  TELEGRAM API
# ═══════════════════════════════════════════════════════
def send_message(chat_id, text, parse_mode="HTML", reply_markup=None, disable_web_page_preview=True):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode,
               "disable_web_page_preview": disable_web_page_preview}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(url, json=payload).json()
    except Exception as e:
        print(f"send_message error: {e}")
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
    except Exception as e:
        print(f"send_photo error: {e}")
        return None


def forward_message(chat_id, from_chat_id, message_id):
    url = f"{BASE_URL}/forwardMessage"
    try:
        return requests.post(url, json={
            "chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id
        }).json()
    except:
        return None


def edit_message(chat_id, message_id, text, parse_mode="HTML", reply_markup=None):
    url = f"{BASE_URL}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id,
               "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(url, json=payload).json()
    except Exception as e:
        print(f"edit_message error: {e}")
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
        return requests.get(url, params={"offset": offset} if offset else {}).json().get("result", [])
    except:
        return []


# ═══════════════════════════════════════════════════════
#  USER + RESOURCES
# ═══════════════════════════════════════════════════════
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
                self.store_key = f"{res_type}_{user_id}"

            def value(self):
                return bot_data.get(self.store_key, 0)

            def add(self, amount):
                bot_data.set(self.store_key, self.value() + amount)
                return self

            def cut(self, amount):
                bot_data.set(self.store_key, max(0, self.value() - amount))
                return self

        return Resource(resource_type, user)


def get_easy_time():
    now = datetime.now()
    months = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
              "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
              "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
    h = now.hour
    ampm = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{now.day} {months[now.strftime('%m')]}, {h12:02}:{now.minute:02} {ampm}"


# ═══════════════════════════════════════════════════════
#  COMMAND REGISTRY
# ═══════════════════════════════════════════════════════
commands = {}


def command(name):
    def deco(fn):
        commands[name] = fn
        return fn
    return deco


def _is_admin(user_id):
    admins = bot_data.get_data("AllBotAdminss") or []
    return str(user_id) in [str(a) for a in admins]


def _is_reseller(user_id):
    resellers = bot_data.get_data("resellers_list") or []
    return str(user_id) in [str(u) for u in resellers]


# ═══════════════════════════════════════════════════════
#  START / NAVIGATION
# ═══════════════════════════════════════════════════════
def _main_menu_text(user_id):
    balance = Resources.another_res("Balance", user=user_id).value()
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
        "<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Your Balance: ₹" + str(balance) +
        "</blockquote>"
    )


def _main_menu_kb():
    return {
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


@command("/start")
@command("/Start")
@command("/START")
def cmd_start(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not User.get_data(user_id, "joined_date"):
        User.save_data(user_id, "joined_date", message.get("date"))
    send_message(user_id, _main_menu_text(user_id), "HTML", _main_menu_kb())
    return True


@command("/backkkk")
def cmd_backkkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    try:
        edit_message(user_id, msg_id, _main_menu_text(user_id), "HTML", _main_menu_kb())
    except:
        send_message(user_id, _main_menu_text(user_id), "HTML", _main_menu_kb())
    return True


# ═══════════════════════════════════════════════════════
#  SHOP (dynamic)
# ═══════════════════════════════════════════════════════
@command("/shopnawkk")
def cmd_shopnawkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<tg-emoji emoji-id='6093562529978522804'>🛒</tg-emoji> <b>PANNEL STORE — SHOP</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<tg-emoji emoji-id='6179339404906079822'>📦</tg-emoji> Choose a product:"
    )
    products = products_store.get_all(active_only=True)
    kb = []
    for p in products:
        if not p.get("plans"):
            continue
        kb.append([{"text": p["name"], "callback_data": f"/SHOP_P {p['pid']}", "style": "success"}])
    kb.append([{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}])
    markup = {"inline_keyboard": kb}
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True


@command("/SHOP_P")
def cmd_shop_p(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    if not params:
        return True
    try:
        pid = int(params)
    except:
        return True
    p = products_store.get(pid)
    if not p or not p.get("active"):
        send_message(user_id, "Product not available")
        return True
    is_reseller = _is_reseller(user_id)
    text = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='6323104647636589287'>📦</tg-emoji> <b>{p['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Choose a plan <tg-emoji emoji-id='5258336354642697821'>👇</tg-emoji>"
    )
    kb = []
    for pl in p.get("plans", []):
        days = pl["days"]
        price = pl["reseller_price"] if is_reseller else pl["price"]
        stock = len(pl.get("stock", []))
        label = f"{days} DAY{'S' if days > 1 else ''} - ₹{int(price)}"
        if stock == 0:
            label += " (out of stock)"
        kb.append([{"text": label, "callback_data": f"/BUY_P {pid} {days}", "style": "success"}])
    kb.append([{"text": "BACK", "callback_data": "/shopnawkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}])
    markup = {"inline_keyboard": kb}
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True


@command("/BUY_P")
def cmd_buy_p(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not params:
        send_message(user_id, "Invalid")
        return True
    parts = params.split()
    if len(parts) != 2:
        send_message(user_id, "Invalid")
        return True
    try:
        pid, days = int(parts[0]), int(parts[1])
    except:
        send_message(user_id, "Invalid")
        return True

    p = products_store.get(pid)
    if not p:
        send_message(user_id, "Product not found")
        return True

    plan = next((pl for pl in p.get("plans", []) if pl["days"] == days), None)
    if not plan:
        send_message(user_id, "Plan not found")
        return True

    is_reseller = _is_reseller(user_id)
    price = float(plan["reseller_price"] if is_reseller else plan["price"])
    if price <= 0:
        send_message(user_id, "Price not set.")
        return True

    if products_store.stock_count(pid, days) == 0:
        send_message(user_id, "Out of Stock.")
        return True

    balance = Resources.another_res("Balance", user=user_id)
    title = f"{p['name']}\n{days} Day{'s' if days > 1 else ''}"

    if balance.value() < price:
        User.save_data(user_id, "last_deposit_amount", price)
        User.save_data(user_id, "last_product1", title)
        User.save_data(user_id, "last_product", title)
        User.save_data(user_id, "last_pid", pid)
        User.save_data(user_id, "last_days", days)
        cmd_autobuy1(message, None)
        return True

    balance.cut(price)
    Resources.another_res("Order", user=user_id).add(1)
    key = products_store.pop_stock(pid, days)
    if not key:
        balance.add(price)
        send_message(user_id, "Stock ran out — refunded")
        return True

    easy_time = get_easy_time()
    send_message(
        user_id,
        f"<tg-emoji emoji-id='6172208745582433583'>🛒</tg-emoji> {title}\n\n"
        f"<tg-emoji emoji-id='6005570495603282482'>🔑</tg-emoji> <b>Your Key:</b>\n<code>{key}</code>\n\n"
        f"<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> Deducted: ₹{int(price)}\n"
        f"<tg-emoji emoji-id='5967456680940671207'>📦</tg-emoji> Remaining Stock: {products_store.stock_count(pid, days)}\n"
        f"<tg-emoji emoji-id='6278102040438640835'>📦</tg-emoji> Time: {easy_time}\n\n"
        f"<tg-emoji emoji-id='6264989131621798851'>📢</tg-emoji> <b>ALL FILES UPDATE</b>\n@SUBHAJIT_UPDATES",
        "HTML"
    )
    adm_ac = User.get_data(user_id, "userhAC") or []
    adm_ac.append(
        f"📆 {easy_time}\n"
        f"👤 {message.get('from', {}).get('first_name', 'User')} [{user_id}]\n"
        f"💰 ₹{int(price)}\n"
        f"🔑 {key}\n"
    )
    User.save_data(user_id, "userhAC", adm_ac)
    return True


# ═══════════════════════════════════════════════════════
#  PAYMENT / QR / VERIFY
# ═══════════════════════════════════════════════════════
@command("/autobuy1")
def cmd_autobuy1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    amount = User.get_data(user_id, "last_deposit_amount")
    pt = User.get_data(user_id, "last_product1") or "Unknown"
    if not amount:
        send_message(user_id, "Amount missing")
        return True
    balance = Resources.another_res("Balance", user=user_id).value()
    need = float(amount) - float(balance)
    if need < 0:
        need = 0

    upi = "bablu.xyztb@fam"
    url = f"https://fampay.anujbots.xyz/qr.php?upi={upi}&amount={amount}"
    try:
        data = requests.get(url).json()
    except:
        send_message(user_id, "API ERROR")
        return True
    if not data or data.get("status") != "success":
        send_message(user_id, "QR GENERATION FAILED")
        return True
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]

    payment_orders_store.create(order_id, user_id, amount, product_name=pt, plan="")
    User.save_data(user_id, "last_order_id", order_id)
    User.save_data(user_id, "payment_processed", False)
    pending_payments[user_id] = {"order_id": order_id, "msg_id": message.get("message_id"), "user_id": str(user_id)}
    pending_payments_store.set(user_id, pending_payments[user_id])

    caption = (
        f"<blockquote><tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> INSUFFICIENT BALANCE</blockquote>\n\n"
        f"┣ Product: {pt}\n"
        f"┣ Price: ₹{amount}\n"
        f"┣ Your Balance: ₹{balance}\n"
        f"┗ Need: ₹{need}\n\n"
        f"Scan QR and complete payment.\n\n"
        f"<tg-emoji emoji-id='5327947823071664175'>🧾</tg-emoji> <b>Order ID:</b>\n"
        f"<code>{order_id}</code>\n\n"
        f"<i>After payment, tap VERIFY PAYMENT.</i>"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ VERIFY PAYMENT", "callback_data": f"/verify_payment {order_id}", "icon_custom_emoji_id": "6278302366303260172", "style": "success"}],
            [{"text": "❌ CANCEL", "callback_data": f"/cancel {order_id}", "icon_custom_emoji_id": "6278116707751956084", "style": "danger"}]
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
        send_message(user_id, "No order ID found.")
        return True

    order_data = payment_orders_store.get_order(order_id)
    if not order_data:
        send_message(user_id, "❌ Invalid Order ID. Generate QR again.")
        return True
    if str(order_data.get("user_id")) != user_id:
        send_message(user_id, "❌ This order does not belong to you!")
        return True
    if order_data.get("status") == "verified":
        send_message(user_id, "✅ Already processed.")
        pending_payments.pop(user_id, None)
        pending_payments_store.delete(user_id)
        return True

    pending = pending_payments_store.get(user_id)
    stored = pending.get("order_id") if isinstance(pending, dict) else pending
    if stored != order_id:
        send_message(user_id, "Order ID mismatch.")
        return True

    send_message(user_id, "⏳ Checking payment...")

    verify_url = f"https://fampay.anujbots.xyz/verify.php?order_id={order_id}&api_key=FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8"
    try:
        data = requests.get(verify_url).json()
    except Exception as e:
        send_message(user_id, f"❌ API ERROR: {e}")
        return True

    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        bal = Resources.another_res("Balance", user=user_id)
        bal.add(amount)
        payment_orders_store.mark_verified(order_id)
        processed_payments_store.add(order_id, user_id, amount)
        User.save_data(user_id, "payment_processed", True)
        pending_payments.pop(user_id, None)
        pending_payments_store.delete(user_id)
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
        for admin in bot_data.get_data("AllBotAdminss") or []:
            send_message(
                admin,
                f"✅ New Payment!\n\n"
                f"👤 User: <code>{user_id}</code>\n"
                f"💰 ₹{amount}\n"
                f"🧾 <code>{order_id}</code>",
                "HTML"
            )
        return True
    else:
        send_message(
            user_id,
            f"❌ <b>Payment Not Found</b>\n\nOrder ID: <code>{order_id}</code>\n\nComplete payment and try again.",
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
        order_id = pending.get("order_id") if isinstance(pending, dict) else pending
    if order_id:
        od = payment_orders_store.get_order(order_id)
        if od and str(od.get("user_id")) == user_id:
            payment_orders_store.delete(order_id)
        elif od:
            send_message(user_id, "❌ Cannot cancel someone else's order!")
            return True
    try:
        delete_message(user_id, msg_id)
    except:
        pass
    pending_payments.pop(user_id, None)
    pending_payments_store.delete(user_id)
    User.save_data(user_id, "last_order_id", "")
    send_message(user_id, "❌ Cancelled")
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True


# ═══════════════════════════════════════════════════════
#  ADD FUND
# ═══════════════════════════════════════════════════════
current_amount = {}


def _addfund_kb():
    return {
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


def _addfund_text(amt):
    return (
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        f"Amount: ₹{amt}\n\n"
        "Use the keypad below to enter amount."
    )


@command("/addpayment")
def cmd_addpayment(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    try:
        edit_message(user_id, msg_id, _addfund_text("0"), "HTML", _addfund_kb())
    except:
        send_message(user_id, _addfund_text("0"), "HTML", _addfund_kb())
    return True


def _digit_handler(digit):
    def handler(message, params, options=None):
        user_id = message.get("from", {}).get("id")
        msg_id = message.get("message_id")
        amt = current_amount.get(user_id, "0")
        amt = digit if amt == "0" else amt + digit
        current_amount[user_id] = amt
        edit_message(user_id, msg_id, _addfund_text(amt), "HTML", _addfund_kb())
        return True
    return handler


for _d in range(10):
    commands[f"/num{_d}"] = _digit_handler(str(_d))


@command("/clearamt")
def cmd_clearamt(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    edit_message(user_id, msg_id, _addfund_text("0"), "HTML", _addfund_kb())
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
        data = requests.get(url).json()
    except:
        send_message(user_id, "API ERROR")
        return
    if data.get("status") != "success":
        send_message(user_id, "QR GENERATION FAILED")
        return
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]

    payment_orders_store.create(order_id, user_id, amount, product_name="Add Funds", plan="")
    User.save_data(user_id, "addpay_order_id", order_id)
    User.save_data(user_id, "payment_processed", False)
    pending_payments[user_id] = {"order_id": order_id, "msg_id": message.get("message_id"), "user_id": str(user_id)}
    pending_payments_store.set(user_id, pending_payments[user_id])

    caption = (
        f"<blockquote><tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> PAYMENT QR GENERATED</blockquote>\n"
        f"Scan the QR and complete payment.\n\n"
        f"Amount: ₹{amount}\n\n"
        f"<tg-emoji emoji-id='5327947823071664175'>🧾</tg-emoji> <b>Order ID:</b>\n"
        f"<code>{order_id}</code>\n\n"
        f"<i>After payment, tap VERIFY PAYMENT.</i>"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ VERIFY PAYMENT", "callback_data": f"/verify_payment {order_id}", "icon_custom_emoji_id": "6278302366303260172", "style": "success"}],
            [{"text": "❌ CANCEL", "callback_data": f"/cancel {order_id}", "icon_custom_emoji_id": "6278116707751956084", "style": "danger"}]
        ]
    }
    send_photo(user_id, qr_url, caption, "HTML", reply_markup)


# ═══════════════════════════════════════════════════════
#  PROFILE / ORDERS / STATIC
# ═══════════════════════════════════════════════════════
@command("/orderksk")
def cmd_orderksk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    adm_ac = User.get_data(user_id, "userhAC") or []
    if not adm_ac:
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<tg-emoji emoji-id='6008118472066732010'>📦</tg-emoji> <b>MY ORDERS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "You haven't placed any orders yet.\n"
            "Tap <tg-emoji emoji-id='6093562529978522804'>🛒</tg-emoji> Shop to start!"
        )
    else:
        text = "\n\n".join(str(x) for x in adm_ac[-10:][::-1])
    kb = {"inline_keyboard": [[{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]]}
    try:
        edit_message(user_id, msg_id, text, "HTML", kb)
    except:
        send_message(user_id, text, "HTML", kb)
    return True


@command("/profilemmm")
def cmd_profilemmm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    name = message.get("from", {}).get("first_name", "User")
    balance = Resources.another_res("Balance", user=user_id).value()
    orders = Resources.another_res("Order", user=user_id).value()
    joined = User.get_data(user_id, "joined_date")
    if not joined:
        member = "Today"
    else:
        diff = message.get("date", 0) - int(joined)
        if diff < 86400:
            member = "Today"
        elif diff < 86400 * 7:
            member = f"{diff // 86400} days ago"
        elif diff < 86400 * 30:
            member = f"{diff // (86400 * 7)} weeks ago"
        else:
            member = f"{diff // (86400 * 30)} months ago"

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<tg-emoji emoji-id='5346136537123801643'>👤</tg-emoji> YOUR PROFILE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<tg-emoji emoji-id='6008118472066732010'>📛</tg-emoji> Name: {name}\n"
        f"<tg-emoji emoji-id='5841693351249710667'>🆔</tg-emoji> User ID: {user_id}\n"
        f"<tg-emoji emoji-id='5348374038991357363'>💰</tg-emoji> Balance: ₹{balance}\n"
        f"<tg-emoji emoji-id='5348490024583185697'>📅</tg-emoji> Member Since: {member}\n"
        f"<tg-emoji emoji-id='6093562529978522804'>🛒</tg-emoji> Total Orders: {orders}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    kb = {
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
    send_message(user_id, text, "HTML", kb)
    return True


@command("/spinj")
def cmd_spinj(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    text = "<tg-emoji emoji-id='5368653135101310687'>🎥</tg-emoji> <b>Watch the full tutorial video below</b>\n\n<tg-emoji emoji-id='6222198028854367391'>👇</tg-emoji>"
    kb = {
        "inline_keyboard": [
            [{"text": "Watch Tutorial", "url": "https://t.me/hehehehhhsljg/162", "icon_custom_emoji_id": "6179339404906079822", "style": "success"}],
            [{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", kb)
    except:
        send_message(user_id, text, "HTML", kb)
    return True


@command("/supportj")
def cmd_supportj(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<tg-emoji emoji-id='5891120964468480450'>💬</tg-emoji> <b>Support</b> <tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📩 <b>Telegram:</b> <a href='https://t.me/UR_SUBHAJIT0'>𝐒υвʜᴀᎫιт</a>\n\n"
        "<i>Include your User ID (from Profile) when contacting.</i>"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "WHATSAPP", "url": "https://wa.me/917908696630", "icon_custom_emoji_id": "6109296665926047025", "style": "success"}],
            [{"text": "BACK", "callback_data": "/backkkk", "icon_custom_emoji_id": "6039539366177541657", "style": "danger"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, text, "HTML", kb)
    except:
        send_message(user_id, text, "HTML", kb)
    return True


# ═══════════════════════════════════════════════════════
#  ADMIN PANEL
# ═══════════════════════════════════════════════════════
@command("/admin")
def cmd_admin(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = bot_data.get_data("AllBotAdminss") or []
    if not admins:
        admins = [str(user_id)]
        bot_data.save_data("AllBotAdminss", admins)
    if not _is_admin(user_id):
        send_message(user_id, "<b>🚫 Not an admin</b>", "HTML")
        return True

    mode = bot_data.get_data("BotMode") or "ON"
    sta = "🟢 On" if mode == "ON" else "🔴 Off"
    chg = "BotMode OFF" if mode == "ON" else "BotMode ON"

    markup = {
        "inline_keyboard": [
            [{"text": "👑 Admins", "callback_data": "/TUSHAR_Admins", "style": "success"}],
            [{"text": "📣 Broadcast", "callback_data": "/broadcast", "style": "success"},
             {"text": f"🤖 Bot: {sta}", "callback_data": f"/admin {chg}", "style": "success"}],
            [{"text": "💰 Add Balance", "callback_data": "/ChangeAnyUserBal", "style": "success"},
             {"text": "📝 Recent", "callback_data": "/TUSHAR_AdminAction", "style": "success"}],
            [{"text": "🆕 PRODUCTS (PID)", "callback_data": "/PM_LIST", "style": "success"}],
            [{"text": "💰 Add Reseller", "callback_data": "/addreseller", "style": "success"},
             {"text": "⛔ Remove", "callback_data": "/removereseller", "style": "danger"}],
            [{"text": "📝 Reseller List", "callback_data": "/resellerlist", "style": "success"}]
        ]
    }
    txt = f"<b>👋 Welcome {message.get('from', {}).get('first_name', 'Admin')} 🎉\n\n━━━━━━━━━━━━━━━\n🤖 Bot: {sta}\n━━━━━━━━━━━━━━━</b>"
    if str(message.get("text")) == "/admin":
        send_message(user_id, txt, "HTML", markup)
    else:
        try:
            edit_message(user_id, msg_id, txt, "HTML", markup)
        except:
            send_message(user_id, txt, "HTML", markup)
    return True


@command("/TUSHAR_Admins")
def cmd_admins(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    if not _is_admin(user_id):
        send_message(user_id, "🚫 Not admin")
        return True
    admins = bot_data.get_data("AllBotAdminss") or []
    if params and params in admins:
        admins.remove(params)
        bot_data.save_data("AllBotAdminss", admins)
    markup = {"inline_keyboard": []}
    for a in admins:
        markup["inline_keyboard"].append([
            {"text": a, "callback_data": f"/TUSHAR_Admins {a}", "style": "success"},
            {"text": "❌", "callback_data": f"/TUSHAR_Admins {a}", "style": "danger"}
        ])
    markup["inline_keyboard"].append([{"text": "➕ Add Admin", "callback_data": "/TUSHAR_AddAdmin", "style": "success"}])
    markup["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "/admin AP", "style": "danger"}])
    try:
        edit_message(user_id, msg_id, "<b>Manage Admins</b>", "HTML", markup)
    except:
        send_message(user_id, "<b>Manage Admins</b>", "HTML", markup)
    return True


@command("/TUSHAR_AddAdmin")
def cmd_addadmin(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id):
        return True
    send_message(user_id, "<b>Send UserID of new Admin</b>", "HTML")
    pending_commands[user_id] = "/TUSHAR_AddAdmin1"
    pending_commands_store.set(user_id, "/TUSHAR_AddAdmin1")
    return True


@command("/TUSHAR_AddAdmin1")
def cmd_addadmin1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id):
        return True
    new = message.get("text", "").strip()
    admins = bot_data.get_data("AllBotAdminss") or []
    if new in admins:
        send_message(user_id, "Already admin")
    else:
        admins.append(new)
        bot_data.save_data("AllBotAdminss", admins)
        send_message(user_id, f"✅ Admin <code>{new}</code> added", "HTML")
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True


@command("/TUSHAR_AdminAction")
def cmd_adminaction(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id):
        return True
    ac = bot_data.get_data("AdmAC") or []
    send_message(user_id, "\n\n".join(ac[-10:][::-1]) if ac else "No actions yet.", "HTML")
    return True


@command("/ChangeAnyUserBal")
def cmd_changebal(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id):
        return True
    send_message(user_id, f"Send: <code>USER_ID AMOUNT</code>\n\nExample: <code>{user_id} 100</code>\n\nAdd - before amount to deduct.", "HTML")
    pending_commands[user_id] = "/ChangeAnyUserBal2"
    pending_commands_store.set(user_id, "/ChangeAnyUserBal2")
    return True


@command("/ChangeAnyUserBal2")
def cmd_changebal2(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id):
        return True
    parts = (message.get("text") or "").split()
    if len(parts) < 2:
        send_message(user_id, "Invalid format")
        return True
    target = parts[0]
    try:
        amount = float(parts[1])
    except:
        send_message(user_id, "Invalid amount")
        return True
    bal = Resources.another_res("Balance", user=target)
    bal.add(amount)
    bot_data.save_data("AdmAC", (bot_data.get_data("AdmAC") or []) + [
        f"📆 {get_easy_time()}\n👥 By {message.get('from', {}).get('first_name', 'Admin')} [{user_id}]\nAction: {amount:+.0f} → {target}"
    ])
    send_message(user_id, f"✅ {target} balance: ₹{bal.value()}", "HTML")
    send_message(target, f"💰 Balance updated: {amount:+.0f}\nNew: ₹{bal.value()}", "HTML")
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True


@command("/addreseller")
def cmd_addreseller(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id):
        return True
    send_message(user_id, "Send reseller user ID")
    pending_commands[user_id] = "/add_reseller_process"
    pending_commands_store.set(user_id, "/add_reseller_process")
    return True


@command("/add_reseller_process")
def cmd_add_reseller_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    target = (message.get("text") or "").strip()
    try:
        target = str(int(target))
    except:
        send_message(user_id, "Invalid ID")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    resellers = bot_data.get_data("resellers_list") or []
    if target in [str(u) for u in resellers]:
        send_message(user_id, "Already reseller")
    else:
        resellers.append(target)
        bot_data.save_data("resellers_list", resellers)
        send_message(user_id, f"✅ {target} added as reseller", "HTML")
        try:
            send_message(target, "You are now a Reseller")
        except:
            pass
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True


@command("/removereseller")
def cmd_removereseller(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id):
        return True
    send_message(user_id, "Send reseller ID to remove")
    pending_commands[user_id] = "/remove_reseller_process"
    pending_commands_store.set(user_id, "/remove_reseller_process")
    return True


@command("/remove_reseller_process")
def cmd_remove_reseller_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    target = (message.get("text") or "").strip()
    try:
        target = str(int(target))
    except:
        send_message(user_id, "Invalid ID")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    resellers = bot_data.get_data("resellers_list") or []
    if target not in [str(u) for u in resellers]:
        send_message(user_id, "Not a reseller")
    else:
        resellers = [u for u in resellers if str(u) != target]
        bot_data.save_data("resellers_list", resellers)
        send_message(user_id, f"✅ {target} removed", "HTML")
        try:
            send_message(target, "You are no longer a Reseller")
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
        send_message(user_id, "No resellers")
        return True
    text = "Reseller List\n━━━━━━━━━━━━━━━━━━\n\n"
    for i, r in enumerate(resellers, 1):
        text += f"{i}. <code>{r}</code>\n"
    text += f"\n━━━━━━━━━━━━━━━━━━\nTotal: {len(resellers)}"
    send_message(user_id, text, "HTML")
    return True


# ═══════════════════════════════════════════════════════
#  PRODUCT MANAGER (PID) — ADMIN
# ═══════════════════════════════════════════════════════
@command("/PM_LIST")
def cmd_pm_list(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    if not _is_admin(user_id):
        send_message(user_id, "🚫 Not admin")
        return True

    products = products_store.get_all(active_only=False)
    if not products:
        txt = "📦 <b>No products yet.</b>\n\nTap ➕ NEW PRODUCT to create one."
    else:
        lines = ["📦 <b>PRODUCTS</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
        for p in products:
            plans_txt = ", ".join(f"{pl['days']}d ₹{int(pl['price'])} ({len(pl.get('stock', []))}k)" for pl in p.get("plans", [])) or "no plans"
            status = "🟢" if p.get("active") else "🔴"
            lines.append(f"{status} <b>PID {p['pid']}</b> — {p['name']}\n   {plans_txt}\n")
        txt = "\n".join(lines)

    kb = []
    for p in products:
        kb.append([{
            "text": f"{'🟢' if p.get('active') else '🔴'} PID {p['pid']} — {p['name']}",
            "callback_data": f"/PM_VIEW {p['pid']}",
            "style": "success" if p.get("active") else "danger"
        }])
    kb.append([{"text": "➕ NEW PRODUCT", "callback_data": "/PM_NEW", "style": "success"}])
    kb.append([{"text": "🔙 Back", "callback_data": "/admin AP", "style": "danger"}])
    markup = {"inline_keyboard": kb}
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True


@command("/PM_NEW")
def cmd_pm_new(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id):
        return True
    send_message(
        user_id,
        "🆕 <b>NEW PRODUCT</b>\n\n"
        "Send: <code>PID | NAME | SLUG</code>\n\n"
        "Example:\n<code>101 | NEXUS MOD | nexus</code>\n\n"
        "PID = unique number\nSLUG = short prefix (no spaces)\n\n"
        "Type /cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/PM_NEW_SAVE"
    pending_commands_store.set(user_id, "/PM_NEW_SAVE")
    return True


@command("/PM_NEW_SAVE")
def cmd_pm_new_save(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    txt = (message.get("text") or "").strip()
    if txt == "/cancel":
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        send_message(user_id, "❌ Cancelled")
        return True
    parts = [x.strip() for x in txt.split("|")]
    if len(parts) != 3:
        send_message(user_id, "❌ Format: <code>PID | NAME | SLUG</code>", "HTML")
        return True
    try:
        pid = int(parts[0])
    except:
        send_message(user_id, "❌ PID must be integer")
        return True
    name, slug = parts[1], parts[2].lower().replace(" ", "_")
    if products_store.get(pid):
        send_message(user_id, f"❌ PID {pid} already exists")
        return True
    if products_store.get_by_slug(slug):
        send_message(user_id, f"❌ Slug <code>{slug}</code> already exists", "HTML")
        return True
    products_store.create(pid, name, slug)
    send_message(
        user_id,
        f"✅ <b>Product created</b>\n\n"
        f"PID: <code>{pid}</code>\nName: {name}\nSlug: <code>{slug}</code>\n\n"
        f"Now add plans via that product.",
        "HTML"
    )
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    return True


@command("/PM_VIEW")
def cmd_pm_view(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    if not _is_admin(user_id) or not params:
        return True
    try:
        pid = int(params)
    except:
        return True
    p = products_store.get(pid)
    if not p:
        send_message(user_id, f"❌ PID {pid} not found")
        return True

    plans = p.get("plans", [])
    if plans:
        plans_txt = "\n".join(
            f"  • {pl['days']}d — ₹{int(pl['price'])} (R ₹{int(pl['reseller_price'])}) — stock: {len(pl['stock'])}"
            for pl in plans
        )
    else:
        plans_txt = "  (no plans yet)"

    status = "🟢 ACTIVE" if p.get("active") else "🔴 DISABLED"
    txt = (
        f"⚙️ <b>PID {p['pid']} — {p['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Slug: <code>{p['slug']}</code>\n"
        f"Status: {status}\n\n"
        f"<b>Plans:</b>\n{plans_txt}"
    )
    kb = [
        [{"text": "➕ ADD PLAN", "callback_data": f"/PM_ADDPLAN {pid}", "style": "success"}],
        [{"text": "🔑 ADD KEYS", "callback_data": f"/PM_ADDKEYS {pid}", "style": "success"}],
    ]
    if plans:
        kb.append([{"text": "💲 EDIT PRICE", "callback_data": f"/PM_EDITPRICE {pid}", "style": "success"}])
        kb.append([{"text": "🗑 REMOVE PLAN", "callback_data": f"/PM_RMPLAN {pid}", "style": "danger"}])
    kb.append([{
        "text": "🔴 DISABLE" if p.get("active") else "🟢 ENABLE",
        "callback_data": f"/PM_TOGGLE {pid}",
        "style": "danger" if p.get("active") else "success"
    }])
    kb.append([{"text": "❌ DELETE PRODUCT", "callback_data": f"/PM_DELETE {pid}", "style": "danger"}])
    kb.append([{"text": "🔙 Back", "callback_data": "/PM_LIST", "style": "danger"}])
    markup = {"inline_keyboard": kb}
    try:
        edit_message(user_id, msg_id, txt, "HTML", markup)
    except:
        send_message(user_id, txt, "HTML", markup)
    return True


@command("/PM_ADDPLAN")
def cmd_pm_addplan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id) or not params:
        return True
    send_message(
        user_id,
        f"➕ <b>ADD PLAN — PID {params}</b>\n\n"
        "Send: <code>DAYS | PRICE | RESELLER_PRICE</code>\n\n"
        "Example: <code>7 | 360 | 320</code>\n\n"
        "(reseller price optional)\n\nType /cancel to stop.",
        "HTML"
    )
    User.save_data(user_id, "pm_ctx_pid", int(params))
    pending_commands[user_id] = "/PM_ADDPLAN_SAVE"
    pending_commands_store.set(user_id, "/PM_ADDPLAN_SAVE")
    return True


@command("/PM_ADDPLAN_SAVE")
def cmd_pm_addplan_save(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    txt = (message.get("text") or "").strip()
    if txt == "/cancel":
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        send_message(user_id, "❌ Cancelled")
        return True
    pid = User.get_data(user_id, "pm_ctx_pid")
    if not pid:
        send_message(user_id, "❌ Context lost")
        return True
    parts = [x.strip() for x in txt.split("|")]
    if len(parts) < 2:
        send_message(user_id, "❌ Format: <code>DAYS | PRICE | RESELLER</code>", "HTML")
        return True
    try:
        days = int(parts[0])
        price = float(parts[1])
        rprice = float(parts[2]) if len(parts) > 2 else price
    except:
        send_message(user_id, "❌ Invalid numbers")
        return True
    ok, msg = products_store.add_plan(pid, days, price, rprice)
    send_message(user_id, f"✅ Plan added: <b>{days}d</b> ₹{int(price)} (R ₹{int(rprice)})" if ok else f"❌ {msg}", "HTML")
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "pm_ctx_pid", None)
    return True


@command("/PM_EDITPRICE")
def cmd_pm_editprice(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id) or not params:
        return True
    send_message(
        user_id,
        f"💲 <b>EDIT PRICE — PID {params}</b>\n\n"
        "Send: <code>DAYS | NEW_PRICE | [R]</code>\n\n"
        "Examples:\n<code>7 | 400</code> → retail\n<code>7 | 350 | R</code> → reseller\n\nType /cancel to stop.",
        "HTML"
    )
    User.save_data(user_id, "pm_ctx_pid", int(params))
    pending_commands[user_id] = "/PM_EDITPRICE_SAVE"
    pending_commands_store.set(user_id, "/PM_EDITPRICE_SAVE")
    return True


@command("/PM_EDITPRICE_SAVE")
def cmd_pm_editprice_save(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    txt = (message.get("text") or "").strip()
    if txt == "/cancel":
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        send_message(user_id, "❌ Cancelled")
        return True
    pid = User.get_data(user_id, "pm_ctx_pid")
    if not pid:
        send_message(user_id, "❌ Context lost")
        return True
    parts = [x.strip() for x in txt.split("|")]
    try:
        days = int(parts[0])
        price = float(parts[1])
        reseller = len(parts) > 2 and parts[2].upper() == "R"
    except:
        send_message(user_id, "❌ Invalid format")
        return True
    ok, msg = products_store.set_price(pid, days, price, reseller=reseller)
    send_message(user_id, f"✅ {msg}: PID {pid} {days}d = ₹{int(price)}" if ok else f"❌ {msg}", "HTML")
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "pm_ctx_pid", None)
    return True


@command("/PM_ADDKEYS")
def cmd_pm_addkeys(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id) or not params:
        return True
    p = products_store.get(int(params))
    if not p:
        return True
    if not p.get("plans"):
        send_message(user_id, "❌ Add a plan first")
        return True
    send_message(
        user_id,
        f"🔑 <b>ADD KEYS — PID {params} ({p['name']})</b>\n\n"
        "Send: <code>DAYS | KEY1 ; KEY2 ; KEY3</code>\n\n"
        "Example: <code>7 | ABC123 ; DEF456 ; GHI789</code>\n\nType /cancel to stop.",
        "HTML"
    )
    User.save_data(user_id, "pm_ctx_pid", int(params))
    pending_commands[user_id] = "/PM_ADDKEYS_SAVE"
    pending_commands_store.set(user_id, "/PM_ADDKEYS_SAVE")
    return True


@command("/PM_ADDKEYS_SAVE")
def cmd_pm_addkeys_save(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    txt = (message.get("text") or "").strip()
    if txt == "/cancel":
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        send_message(user_id, "❌ Cancelled")
        return True
    pid = User.get_data(user_id, "pm_ctx_pid")
    if not pid:
        send_message(user_id, "❌ Context lost")
        return True
    if "|" not in txt:
        send_message(user_id, "❌ Format: <code>DAYS | KEY1 ; KEY2</code>", "HTML")
        return True
    days_part, keys_part = txt.split("|", 1)
    try:
        days = int(days_part.strip())
    except:
        send_message(user_id, "❌ DAYS invalid")
        return True
    keys = [k.strip() for k in keys_part.split(";") if k.strip()]
    if not keys:
        send_message(user_id, "❌ No keys")
        return True
    ok, result = products_store.add_stock(pid, days, keys)
    send_message(user_id, f"✅ Added {len(keys)} keys → total {result}" if ok else f"❌ {result}", "HTML")
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "pm_ctx_pid", None)
    return True


@command("/PM_RMPLAN")
def cmd_pm_rmplan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id) or not params:
        return True
    p = products_store.get(int(params))
    if not p:
        return True
    kb = []
    for pl in p.get("plans", []):
        kb.append([{
            "text": f"🗑 {pl['days']}d — ₹{int(pl['price'])}",
            "callback_data": f"/PM_RMPLAN_DO {params} {pl['days']}",
            "style": "danger"
        }])
    kb.append([{"text": "🔙 Back", "callback_data": f"/PM_VIEW {params}", "style": "danger"}])
    send_message(user_id, f"🗑 <b>REMOVE PLAN — PID {params}</b>", "HTML", {"inline_keyboard": kb})
    return True


@command("/PM_RMPLAN_DO")
def cmd_pm_rmplan_do(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id) or not params:
        return True
    parts = params.split()
    try:
        pid, days = int(parts[0]), int(parts[1])
    except:
        return True
    ok, msg = products_store.remove_plan(pid, days)
    send_message(user_id, f"✅ {msg}" if ok else f"❌ {msg}")
    return True


@command("/PM_TOGGLE")
def cmd_pm_toggle(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id) or not params:
        return True
    p = products_store.get(int(params))
    if not p:
        return True
    new_state = not p.get("active", True)
    products_store.set_active(int(params), new_state)
    send_message(user_id, f"✅ PID {params} — {'enabled' if new_state else 'disabled'}")
    return True


@command("/PM_DELETE")
def cmd_pm_delete(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id) or not params:
        return True
    pid = int(params)
    products_store.delete(pid)
    send_message(user_id, f"🗑 PID {pid} deleted")
    return True


# ═══════════════════════════════════════════════════════
#  BROADCAST
# ═══════════════════════════════════════════════════════
@command("/broadcast")
def cmd_broadcast(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id):
        return True
    all_users = user_data_store.get_all_users()
    for doc in mongo.get_collection('pending_payments').find({}, {"user_id": 1}):
        if doc.get("user_id") not in all_users:
            all_users.append(doc.get("user_id"))
    for admin in bot_data.get_data("AllBotAdminss") or []:
        if admin not in all_users:
            all_users.append(admin)
    all_users = list(set(all_users))
    User.save_data(user_id, "broadcast_users", all_users)
    send_message(
        user_id,
        f"📢 <b>BROADCAST</b>\n\n👥 {len(all_users)} users\n\nSend any message to forward.\n\n/cancel to stop.",
        "HTML"
    )
    pending_commands[user_id] = "/broadcast_send_media"
    pending_commands_store.set(user_id, "/broadcast_send_media")
    return True


@command("/broadcast_send_media")
def cmd_broadcast_send(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    if not _is_admin(user_id):
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    if (message.get("text") or "").strip() == "/cancel":
        send_message(user_id, "❌ Cancelled")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        User.save_data(user_id, "broadcast_users", None)
        return True
    users = User.get_data(user_id, "broadcast_users") or []
    if not users:
        send_message(user_id, "No users. Use /broadcast again.")
        pending_commands.pop(user_id, None)
        pending_commands_store.delete(user_id)
        return True
    from_chat = message.get("chat", {}).get("id")
    msg_id = message.get("message_id")
    success = failed = 0
    for target in users:
        try:
            forward_message(target, from_chat, msg_id)
            success += 1
        except:
            failed += 1
        time.sleep(0.05)
    send_message(user_id, f"✅ Done\n📤 Sent: {success}\n❌ Failed: {failed}", "HTML")
    pending_commands.pop(user_id, None)
    pending_commands_store.delete(user_id)
    User.save_data(user_id, "broadcast_users", None)
    return True


# ═══════════════════════════════════════════════════════
#  UPDATE HANDLER
# ═══════════════════════════════════════════════════════
def handle_update(update):
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        user_id = cb.get("from", {}).get("id")
        msg_id = cb.get("message", {}).get("message_id")
        answer_callback(cb.get("id"))
        parts = data.split(" ")
        cmd = parts[0]
        params = " ".join(parts[1:]) if len(parts) > 1 else None
        msg = {
            "message_id": msg_id,
            "from": cb.get("from", {}),
            "chat": {"id": user_id},
            "date": int(time.time()),
            "text": data,
            "reply_markup": cb.get("message", {}).get("reply_markup"),
        }
        if cmd in commands:
            try:
                commands[cmd](msg, params)
            except Exception as e:
                print(f"Callback error [{cmd}]: {e}")
        return

    if "message" in update:
        msg = update["message"]
        user_id = msg.get("from", {}).get("id")
        text = msg.get("text", "")
        if user_id in pending_commands:
            pc = pending_commands[user_id]
            if pc in commands:
                try:
                    commands[pc](msg, None)
                except Exception as e:
                    print(f"Pending cmd error [{pc}]: {e}")
                return
        if text.startswith("/"):
            parts = text.split(" ")
            cmd = parts[0]
            params = " ".join(parts[1:]) if len(parts) > 1 else None
            if cmd in commands:
                try:
                    commands[cmd](msg, params)
                except Exception as e:
                    print(f"Command error [{cmd}]: {e}")


def main():
    print("Bot started.")
    print(f"MongoDB: {DB_NAME}")
    print(f"Commands: {len(commands)}")
    last_update_id = 0
    while True:
        try:
            updates = get_updates(last_update_id + 1)
            for u in updates:
                if "update_id" in u:
                    last_update_id = u["update_id"]
                handle_update(u)
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("Stopped.")
            break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
