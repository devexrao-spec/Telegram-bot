# tusharbot.py - FULLY WORKING
import requests
import json
import time
from datetime import datetime
import threading
from pymongo import MongoClient

BOT_TOKEN = "8565204943:AAEw7F-5NIwZjluyWT-PQYk70xHY3j01xAo"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ========== ADMIN ID ==========
ADMIN_IDS = ["8102646437"]

# ========== MONGODB ==========
MONGO_URI = "mongodb+srv://crasher3210_db_user:devex5656@cluster0.9y5axka.mongodb.net/?appName=Cluster0&compressors=zlib"
DB_NAME = "telegram_bot1"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
bot_data = db['bot_data']
user_data = db['user_data']
pending_commands = db['pending_commands']
pending_payments = db['pending_payments']
payment_orders = db['payment_orders']
products = db['products']

# ========== DATA FUNCTIONS ==========
def get_data(key, default=None):
    doc = bot_data.find_one({"key": key})
    return doc.get("value") if doc else default

def set_data(key, value):
    bot_data.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

def get_user(user_id, key, default=None):
    doc = user_data.find_one({"user_id": str(user_id), "key": key})
    return doc.get("value") if doc else default

def set_user(user_id, key, value):
    user_data.update_one({"user_id": str(user_id), "key": key}, {"$set": {"value": value}}, upsert=True)

def get_products():
    return list(products.find())

def get_product(product_id):
    return products.find_one({"product_id": product_id})

def add_product(product_id, name, pid, needs_android, emoji_id=None):
    products.update_one(
        {"product_id": product_id},
        {"$set": {"product_id": product_id, "name": name, "pid": pid, "needs_android": needs_android, "emoji_id": emoji_id, "plans": []}},
        upsert=True
    )

def add_plan(product_id, plan_id, duration, price, reseller_price):
    products.update_one(
        {"product_id": product_id},
        {"$push": {"plans": {"plan_id": plan_id, "duration": duration, "price": price, "reseller_price": reseller_price}}}
    )

def update_pid(product_id, new_pid):
    products.update_one({"product_id": product_id}, {"$set": {"pid": new_pid}})

def update_emoji(product_id, emoji_id):
    products.update_one({"product_id": product_id}, {"$set": {"emoji_id": emoji_id}})

def update_plan_price(product_id, plan_id, price, reseller_price):
    products.update_one(
        {"product_id": product_id, "plans.plan_id": plan_id},
        {"$set": {"plans.$.price": price, "plans.$.reseller_price": reseller_price}}
    )

def remove_plan(product_id, plan_id):
    products.update_one({"product_id": product_id}, {"$pull": {"plans": {"plan_id": plan_id}}})

def delete_product(product_id):
    products.delete_one({"product_id": product_id})

def toggle_android(product_id):
    p = get_product(product_id)
    if p:
        new_val = not p.get('needs_android', True)
        products.update_one({"product_id": product_id}, {"$set": {"needs_android": new_val}})
        return new_val
    return None

# ========== RESELLER API ==========
RESELLER_API_URL = "https://xyzcheats.com/api/reseller_v1.php"
RESELLER_API_KEY = "b25eb076f5c0412fa9f1eba94550d02e"
RESELLER_API_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'x-master-key': 'a7f3e8b2c9d1f4a6b8c2d5e9f1a3b6c8'
}

DURATION_MAP = {
    "1": "1 DaYS NONROOT", "2": "3 DaYS NONROOT", "3": "7 DaYS NONROOT",
    "4": "15 DaYS NONROOT", "5": "30 DaYS NONROOT", "6": "1 DaYS NONROOT",
    "7": "3 DaYS NONROOT", "8": "7 DaYS NONROOT", "9": "14 DaYS NONROOT",
    "10": "1 DaYS NONROOT", "11": "3 DaYS NONROOT", "12": "7 DaYS NONROOT",
    "13": "14 DaYS NONROOT", "14": "21 DaYS NONROOT", "15": "28 DaYS NONROOT",
}

def generate_api_key(product_pid, duration, android_id=None, price=None):
    data = {
        'api_key': RESELLER_API_KEY,
        'action': 'buy',
        'product_id': str(product_pid),
        'duration': duration
    }
    if price:
        data['price'] = str(price)
        data['amount'] = str(price)
    if android_id:
        data['android_id'] = android_id
    
    try:
        response = requests.post(RESELLER_API_URL, data=data, headers=RESELLER_API_HEADERS, timeout=30)
        result = response.json()
        if result.get('status') == 'success' or result.get('success') == True:
            key = result.get('key') or result.get('data', {}).get('key') or result.get('license_key')
            if key:
                return True, key
        return False, result.get('msg', 'Unknown error')
    except Exception as e:
        return False, str(e)

def get_duration(plan_id):
    return DURATION_MAP.get(str(plan_id), "1 DaYS NONROOT")

# ========== TELEGRAM ==========
def send_message(chat_id, text, parse_mode="HTML", reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(f"{BASE_URL}/sendMessage", json=payload).json()
    except:
        return None

def send_photo(chat_id, photo, caption=None, parse_mode="HTML", reply_markup=None):
    payload = {"chat_id": chat_id, "photo": photo, "parse_mode": parse_mode}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(f"{BASE_URL}/sendPhoto", json=payload).json()
    except:
        return None

def edit_message(chat_id, message_id, text, parse_mode="HTML", reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(f"{BASE_URL}/editMessageText", json=payload).json()
    except:
        return None

def delete_message(chat_id, message_id):
    try:
        return requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id}).json()
    except:
        return None

def answer_callback(callback_id):
    try:
        return requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": callback_id}).json()
    except:
        return None

def get_updates(offset=None):
    try:
        response = requests.get(f"{BASE_URL}/getUpdates", params={"offset": offset} if offset else {})
        return response.json().get("result", [])
    except:
        return []

def forward_message(chat_id, from_chat_id, message_id):
    try:
        return requests.post(f"{BASE_URL}/forwardMessage", json={"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id}).json()
    except:
        return None

def get_easy_time():
    return datetime.now().strftime("%d %b, %I:%M %p")

# ========== HELPERS ==========
class Resources:
    @staticmethod
    def another_res(resource_type, user=None):
        class Resource:
            def __init__(self, res_type, user_id):
                self.res_type = res_type
                self.user_id = user_id
                self.key = f"{res_type}_{user_id}"
            
            def value(self):
                return get_data(self.key, 0)
            
            def add(self, amount):
                set_data(self.key, self.value() + amount)
                return self
            
            def cut(self, amount):
                set_data(self.key, max(0, self.value() - amount))
                return self
        return Resource(resource_type, user)

commands = {}
pending_cmds = {}
pending_pays = {}
current_amount = {}

def command(name):
    def decorator(func):
        commands[name] = func
        return func
    return decorator

# ========== PROCESS PURCHASE ==========
def process_purchase(msg, product_id, plan_id, price, product_name, duration, pid, android_id=None):
    uid = msg.get("from", {}).get("id")
    balance = Resources.another_res("Balance", uid)
    
    if balance.value() < price:
        set_user(uid, "last_deposit_amount", price)
        set_user(uid, "last_product", product_name)
        cmd_autobuy1(msg, None)
        return True
    
    balance.cut(price)
    Resources.another_res("Order", uid).add(1)
    
    api_duration = get_duration(plan_id)
    success, result = generate_api_key(pid, api_duration, android_id, price)
    
    if success:
        send_message(
            uid,
            f"🛒 {product_name}\n\n"
            f"🔑 <b>Your Key:</b>\n<code>{result}</code>\n\n"
            f"💰 Deducted: ₹{price}\n"
            f"⏳ Duration: {duration}\n"
            f"📦 Time: {get_easy_time()}",
            "HTML"
        )
        hist = get_user(uid, "userhAC") or []
        hist.append(f"📆 {get_easy_time()}\n👤 {msg.get('from', {}).get('first_name', 'User')} [{uid}]\n💰 ₹{price}\n🔑 {result}")
        set_user(uid, "userhAC", hist)
        return True
    else:
        balance.add(price)
        send_message(
            uid,
            f"❌ <b>Key Generation Failed</b>\n\nError: {result}\n\nYour balance of ₹{price} has been refunded.",
            "HTML"
        )
        return True

# ========== DEFAULT PRODUCTS ==========
def setup_products():
    prods = {
        "abcd": {"name": "ABCD", "pid": "143", "needs_android": False, "emoji_id": "5345976085735558094", "plans": [{"plan_id": "1", "duration": "12 Hours", "price": 10, "reseller_price": 8}]},
        "bala_v2": {"name": "BALA MODS XYZ V2", "pid": "136", "needs_android": False, "emoji_id": "5348292765325212780", "plans": [
            {"plan_id": "1", "duration": "1 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 10, "reseller_price": 8},
            {"plan_id": "2", "duration": "3 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 25, "reseller_price": 20},
            {"plan_id": "3", "duration": "6 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 45, "reseller_price": 38},
            {"plan_id": "4", "duration": "12 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 80, "reseller_price": 68},
            {"plan_id": "5", "duration": "1 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 150, "reseller_price": 130},
            {"plan_id": "6", "duration": "2 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 250, "reseller_price": 210},
            {"plan_id": "7", "duration": "3 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 350, "reseller_price": 300},
            {"plan_id": "8", "duration": "5 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 500, "reseller_price": 430}]},
        "drip": {"name": "DRIP CLIENT MOD", "pid": "133", "needs_android": True, "emoji_id": "6323104647636589287", "plans": [
            {"plan_id": "1", "duration": "1 DaYS NONROOT", "price": 108, "reseller_price": 95},
            {"plan_id": "2", "duration": "3 DaYS NONROOT", "price": 260, "reseller_price": 220},
            {"plan_id": "3", "duration": "7 DaYS NONROOT", "price": 360, "reseller_price": 320},
            {"plan_id": "4", "duration": "15 DaYS NONROOT", "price": 560, "reseller_price": 480},
            {"plan_id": "5", "duration": "30 DaYS NONROOT", "price": 810, "reseller_price": 750}]},
        "silent": {"name": "SILENT CHEATS ANDROID", "pid": "133", "needs_android": True, "emoji_id": "6325561995995126107", "plans": [
            {"plan_id": "1", "duration": "1 DaYS NONROOT", "price": 108, "reseller_price": 95},
            {"plan_id": "2", "duration": "3 DaYS NONROOT", "price": 260, "reseller_price": 220},
            {"plan_id": "3", "duration": "7 DaYS NONROOT", "price": 360, "reseller_price": 320},
            {"plan_id": "4", "duration": "14 DaYS NONROOT", "price": 560, "reseller_price": 480},
            {"plan_id": "5", "duration": "28 DaYS NONROOT", "price": 810, "reseller_price": 750}]},
        "prime": {"name": "PRIME HOOK", "pid": "133", "needs_android": True, "emoji_id": "6210705396449944693", "plans": [
            {"plan_id": "1", "duration": "1 DaYS NONROOT", "price": 108, "reseller_price": 95},
            {"plan_id": "2", "duration": "3 DaYS NONROOT", "price": 200, "reseller_price": 180},
            {"plan_id": "3", "duration": "7 DaYS NONROOT", "price": 360, "reseller_price": 320},
            {"plan_id": "4", "duration": "14 DaYS NONROOT", "price": 600, "reseller_price": 550},
            {"plan_id": "5", "duration": "21 DaYS NONROOT", "price": 700, "reseller_price": 650}]}
    }
    
    for pid, data in prods.items():
        if not get_product(pid):
            add_product(pid, data["name"], data["pid"], data["needs_android"], data.get("emoji_id"))
            for plan in data["plans"]:
                add_plan(pid, plan["plan_id"], plan["duration"], plan["price"], plan["reseller_price"])
            print(f"✅ Added: {data['name']}")

# ========== USER COMMANDS ==========

@command("/start")
def cmd_start(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    if not get_user(uid, "joined_date"):
        set_user(uid, "joined_date", msg.get("date"))
    balance = Resources.another_res("Balance", uid).value()
    is_admin = str(uid) in ADMIN_IDS
    
    text = f"🌟 <b>WELCOME TO HACK STORE</b> 🌙\n\n✨ Premium mods, cheats & clients!\n\n🚀 Instant Key Delivery\n💳 Secure Payment\n🛡 Anti-Ban Support\n\n💰 Balance: ₹{balance}"
    
    keyboard = [
        [{"text": "🛒 BUY HACK", "callback_data": "/shopnawkk"}],
        [{"text": "🔑 MY KEY", "callback_data": "/orderksk"}, {"text": "👤 PROFILE", "callback_data": "/profilemmm"}],
        [{"text": "📖 HOW TO USE", "callback_data": "/spinj"}, {"text": "💬 SUPPORT", "callback_data": "/supportj"}],
        [{"text": "💰 ADD FUND", "callback_data": "/addpayment"}],
        [{"text": "📥 DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl"}]
    ]
    
    if is_admin:
        keyboard.append([{"text": "👑 ADMIN PANEL", "callback_data": "/admin"}])
    
    send_message(uid, text, "HTML", {"inline_keyboard": keyboard})
    return True

@command("/shopnawkk")
def cmd_shopnawkk(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    prods = get_products()
    
    if not prods:
        text = "⚠️ No products available."
        kb = {"inline_keyboard": [[{"text": "🔙 BACK", "callback_data": "/backkkk"}]]}
        try:
            edit_message(uid, mid, text, "HTML", kb)
        except:
            send_message(uid, text, "HTML", kb)
        return True
    
    text = "🛒 <b>PANNEL STORE — SHOP</b>\n━━━━━━━━━━━━━━━━━━\n\n📦 Choose a product:"
    kb = {"inline_keyboard": []}
    
    for p in prods:
        pid = p.get('product_id')
        emoji = p.get('emoji_id')
        if emoji:
            display = f"<tg-emoji emoji-id='{emoji}'>📦</tg-emoji> {p.get('name')}"
        else:
            display = f"📦 {p.get('name')}"
        kb["inline_keyboard"].append([{"text": display, "callback_data": f"/p_{pid}"}])
    
    kb["inline_keyboard"].append([{"text": "🔙 BACK", "callback_data": "/backkkk"}])
    
    try:
        edit_message(uid, mid, text, "HTML", kb)
    except:
        send_message(uid, text, "HTML", kb)
    return True

@command("/p_abcd")
@command("/p_bala_v2")
@command("/p_drip")
@command("/p_silent")
@command("/p_prime")
def cmd_show_plans(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    cmd = msg.get("text", "")
    pid = cmd.replace("/p_", "")
    
    p = get_product(pid)
    if not p:
        send_message(uid, "Product not found")
        return True
    
    resellers = get_data("resellers_list") or []
    is_reseller = str(uid) in [str(u) for u in resellers]
    
    text = f"📦 <b>{p.get('name')}</b>\n━━━━━━━━━━━━━━━━━━\n\nChoose a plan 👇"
    kb = {"inline_keyboard": []}
    
    for plan in p.get('plans', []):
        price = plan.get('reseller_price') if is_reseller else plan.get('price')
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        kb["inline_keyboard"].append([{"text": f"{duration} - ₹{price}", "callback_data": f"/b_{pid}_{plan_id}"}])
    
    kb["inline_keyboard"].append([{"text": "🔙 BACK", "callback_data": "/shopnawkk"}])
    
    try:
        edit_message(uid, mid, text, "HTML", kb)
    except:
        send_message(uid, text, "HTML", kb)
    return True

@command("/b_abcd_1")
@command("/b_bala_v2_1")
@command("/b_bala_v2_2")
@command("/b_bala_v2_3")
@command("/b_bala_v2_4")
@command("/b_bala_v2_5")
@command("/b_bala_v2_6")
@command("/b_bala_v2_7")
@command("/b_bala_v2_8")
@command("/b_drip_1")
@command("/b_drip_2")
@command("/b_drip_3")
@command("/b_drip_4")
@command("/b_drip_5")
@command("/b_silent_1")
@command("/b_silent_2")
@command("/b_silent_3")
@command("/b_silent_4")
@command("/b_silent_5")
@command("/b_prime_1")
@command("/b_prime_2")
@command("/b_prime_3")
@command("/b_prime_4")
@command("/b_prime_5")
def cmd_buy(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    cmd = msg.get("text", "")
    parts = cmd.split("_")
    
    if len(parts) < 3:
        send_message(uid, "Invalid product selection")
        return True
    
    pid = parts[1]
    plan_id = parts[2]
    
    p = get_product(pid)
    if not p:
        send_message(uid, "Product not found")
        return True
    
    selected = None
    for plan in p.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected = plan
            break
    
    if not selected:
        send_message(uid, "Plan not found")
        return True
    
    resellers = get_data("resellers_list") or []
    is_reseller = str(uid) in [str(u) for u in resellers]
    
    price = selected.get('reseller_price') if is_reseller else selected.get('price')
    duration = selected.get('duration')
    name = p.get('name')
    api_pid = p.get('pid')
    needs_android = p.get('needs_android', True)
    
    set_user(uid, "last_product1", name)
    set_user(uid, "last_plan", plan_id)
    set_user(uid, "last_product_key", pid)
    set_user(uid, "last_price", price)
    set_user(uid, "last_duration", duration)
    set_user(uid, "last_pid", api_pid)
    
    if needs_android:
        send_message(
            uid,
            f"🔐 <b>Android ID Required</b>\n\nProduct: {name}\nPlan: {duration}\nPrice: ₹{price}\n\nSend Android ID (16 hex chars)\nType /cancel",
            "HTML"
        )
        pending_cmds[uid] = "/process_android"
        pending_commands.update_one({"user_id": str(uid)}, {"$set": {"command": "/process_android"}}, upsert=True)
        return True
    else:
        return process_purchase(msg, pid, plan_id, price, name, duration, api_pid)

@command("/process_android")
def cmd_process_android(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(uid, "❌ Cancelled", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    if len(text) != 16 or not all(c in '0123456789abcdefABCDEF' for c in text):
        send_message(uid, "❌ Invalid! 16 hex chars. Example: 0b9b969bc2e7997b", "HTML")
        return True
    
    pending_cmds.pop(uid, None)
    pending_commands.delete_one({"user_id": str(uid)})
    
    pid = get_user(uid, "last_product_key")
    plan_id = get_user(uid, "last_plan")
    price = get_user(uid, "last_price")
    name = get_user(uid, "last_product1")
    duration = get_user(uid, "last_duration")
    api_pid = get_user(uid, "last_pid")
    
    return process_purchase(msg, pid, plan_id, price, name, duration, api_pid, android_id=text)

@command("/autobuy1")
def cmd_autobuy1(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    amount = get_user(uid, "last_deposit_amount")
    pt = get_user(uid, "last_product1") or "Unknown"
    plan = get_user(uid, "last_plan") or "Unknown"
    if not amount:
        send_message(uid, "Amount missing")
        return True
    
    balance = Resources.another_res("Balance", uid).value()
    need = float(amount) - float(balance)
    if need < 0:
        need = 0
    plan_display = {"6": "1 Day", "7": "3 Days", "8": "7 Days", "9": "14 Days", "15": "28 Days"}.get(str(plan), plan)
    
    upi = "bablu.xyztb@fam"
    url = f"https://fampay.anujbots.xyz/qr.php?upi={upi}&amount={amount}"
    try:
        r = requests.get(url)
        data = r.json()
    except:
        send_message(uid, "API ERROR")
        return True
    if not data or data.get("status") != "success":
        send_message(uid, "QR GENERATION FAILED")
        return True
    
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    payment_orders.update_one(
        {"order_id": order_id},
        {"$set": {"order_id": order_id, "user_id": str(uid), "amount": amount, "product_name": pt, "plan": plan_display, "created_at": datetime.now(), "status": "pending"}},
        upsert=True
    )
    
    set_user(uid, "last_order_id", order_id)
    pending_pays[uid] = {"order_id": order_id, "msg_id": msg.get("message_id"), "user_id": str(uid)}
    pending_payments.update_one({"user_id": str(uid)}, {"$set": {"data": pending_pays[uid]}}, upsert=True)
    
    caption = f"💰 <b>INSUFFICIENT BALANCE</b>\n\nProduct: {pt}\nPlan: {plan_display}\nPrice: ₹{amount}\nBalance: ₹{balance}\nNeed: ₹{need}\n\nScan QR:\n🧾 Order: <code>{order_id}</code>"
    kb = {"inline_keyboard": [[{"text": "✅ VERIFY", "callback_data": f"/v_{order_id}"}], [{"text": "❌ CANCEL", "callback_data": f"/c_{order_id}"}]]}
    send_photo(uid, qr_url, caption, "HTML", kb)
    return True

@command("/v")
def cmd_verify(msg, params, options=None):
    uid = str(msg.get("from", {}).get("id"))
    mid = msg.get("message_id")
    cmd = msg.get("text", "")
    order_id = cmd.replace("/v_", "") if "/v_" in cmd else params
    
    if not order_id:
        send_message(uid, "No order ID", "HTML")
        return True
    
    order = payment_orders.find_one({"order_id": order_id})
    if not order:
        send_message(uid, "❌ Invalid order", "HTML")
        return True
    
    if str(order.get("user_id")) != str(uid):
        send_message(uid, "❌ Not your order!", "HTML")
        return True
    
    if order.get("status") == "verified":
        send_message(uid, "✅ Already verified!", "HTML")
        return True
    
    send_message(uid, "⏳ Checking payment...", "HTML")
    
    url = f"https://fampay.anujbots.xyz/verify.php?order_id={order_id}&api_key=FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8"
    try:
        r = requests.get(url)
        data = r.json()
    except:
        send_message(uid, "❌ API ERROR", "HTML")
        return True
    
    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        bal = Resources.another_res("Balance", uid)
        bal.add(amount)
        
        payment_orders.update_one({"order_id": order_id}, {"$set": {"status": "verified", "verified_at": datetime.now()}})
        set_user(uid, "last_order_id", "")
        pending_pays.pop(uid, None)
        pending_payments.delete_one({"user_id": str(uid)})
        
        if mid:
            try:
                delete_message(uid, mid)
            except:
                pass
        
        send_message(uid, f"✅ <b>Payment Success!</b>\n\n💰 Added: ₹{amount}\n💳 New Balance: ₹{bal.value()}", "HTML")
        return True
    else:
        send_message(uid, f"❌ <b>Payment Not Found</b>\n\nOrder: <code>{order_id}</code>", "HTML")
        return True

@command("/c")
def cmd_cancel(msg, params, options=None):
    uid = str(msg.get("from", {}).get("id"))
    mid = msg.get("message_id")
    cmd = msg.get("text", "")
    order_id = cmd.replace("/c_", "") if "/c_" in cmd else params
    
    if not order_id:
        p = pending_payments.find_one({"user_id": str(uid)})
        if p:
            order_id = p.get("data", {}).get("order_id")
    
    if order_id:
        payment_orders.delete_one({"order_id": order_id})
    
    if mid:
        try:
            delete_message(uid, mid)
        except:
            pass
    
    pending_pays.pop(uid, None)
    pending_payments.delete_one({"user_id": str(uid)})
    pending_cmds.pop(uid, None)
    pending_commands.delete_one({"user_id": str(uid)})
    send_message(uid, "❌ Cancelled", "HTML")
    return True

@command("/backkkk")
def cmd_backkkk(msg, params, options=None):
    return cmd_start(msg, params, options)

@command("/orderksk")
def cmd_orderksk(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    hist = get_user(uid, "userhAC") or []
    
    if not hist:
        text = "📦 <b>MY ORDERS</b>\n━━━━━━━━━━━━━━━━━━\n\nNo orders yet."
    else:
        text = "📦 <b>MY ORDERS</b>\n━━━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(hist[-10:][::-1])
    
    kb = {"inline_keyboard": [[{"text": "🔙 BACK", "callback_data": "/backkkk"}]]}
    try:
        edit_message(uid, mid, text, "HTML", kb)
    except:
        send_message(uid, text, "HTML", kb)
    return True

@command("/profilemmm")
def cmd_profilemmm(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    name = msg.get("from", {}).get("first_name", "User")
    balance = Resources.another_res("Balance", uid).value()
    orders = Resources.another_res("Order", uid).value()
    
    text = f"👤 <b>YOUR PROFILE</b>\n━━━━━━━━━━━━━━━━━━\n\n📛 Name: {name}\n🆔 ID: {uid}\n💰 Balance: ₹{balance}\n🛒 Orders: {orders}"
    kb = {"inline_keyboard": [[{"text": "🛒 BUY", "callback_data": "/shopnawkk"}, {"text": "🔑 KEYS", "callback_data": "/orderksk"}], [{"text": "🔙 BACK", "callback_data": "/backkkk"}]]}
    send_message(uid, text, "HTML", kb)
    return True

@command("/spinj")
def cmd_spinj(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = "🎥 <b>Watch Tutorial</b>\n\nhttps://t.me/hehehehhhsljg/162"
    kb = {"inline_keyboard": [[{"text": "▶️ Watch", "url": "https://t.me/hehehehhhsljg/162"}], [{"text": "🔙 BACK", "callback_data": "/backkkk"}]]}
    send_message(uid, text, "HTML", kb)
    return True

@command("/supportj")
def cmd_supportj(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = "💬 <b>Support</b>\n\n<a href='https://t.me/UR_SUBHAJIT0'>Contact</a>"
    kb = {"inline_keyboard": [[{"text": "📱 WhatsApp", "url": "https://wa.me/917908696630"}], [{"text": "🔙 BACK", "callback_data": "/backkkk"}]]}
    send_message(uid, text, "HTML", kb)
    return True

# ========== NUMBER PAD ==========

@command("/addpayment")
def cmd_addpayment(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    current_amount[uid] = "0"
    kb = {
        "inline_keyboard": [
            [{"text": "1", "callback_data": "/n1"}, {"text": "2", "callback_data": "/n2"}, {"text": "3", "callback_data": "/n3"}],
            [{"text": "4", "callback_data": "/n4"}, {"text": "5", "callback_data": "/n5"}, {"text": "6", "callback_data": "/n6"}],
            [{"text": "7", "callback_data": "/n7"}, {"text": "8", "callback_data": "/n8"}, {"text": "9", "callback_data": "/n9"}],
            [{"text": "CLEAR", "callback_data": "/clr"}, {"text": "0", "callback_data": "/n0"}, {"text": "✅", "callback_data": "/done"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
        ]
    }
    try:
        edit_message(uid, mid, "💰 <b>ENTER AMOUNT</b>\n\n₹0", "HTML", kb)
    except:
        send_message(uid, "💰 <b>ENTER AMOUNT</b>\n\n₹0", "HTML", kb)
    return True

@command("/n0")
def cmd_n0(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    if amt != "0":
        amt += "0"
    current_amount[uid] = amt
    edit_message(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n1")
def cmd_n1(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "1" if amt == "0" else amt + "1"
    current_amount[uid] = amt
    edit_message(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n2")
def cmd_n2(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "2" if amt == "0" else amt + "2"
    current_amount[uid] = amt
    edit_message(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n3")
def cmd_n3(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "3" if amt == "0" else amt + "3"
    current_amount[uid] = amt
    edit_message(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n4")
def cmd_n4(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "4" if amt == "0" else amt + "4"
    current_amount[uid] = amt
    edit_message(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n5")
def cmd_n5(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "5" if amt == "0" else amt + "5"
    current_amount[uid] = amt
    edit_message(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n6")
def cmd_n6(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "6" if amt == "0" else amt + "6"
    current_amount[uid] = amt
    edit_message(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n7")
def cmd_n7(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "7" if amt == "0" else amt + "7"
    current_amount[uid] = amt
    edit_message(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n8")
def cmd_n8(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "8" if amt == "0" else amt + "8"
    current_amount[uid] = amt
    edit_message(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n9")
def cmd_n9(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "9" if amt == "0" else amt + "9"
    current_amount[uid] = amt
    edit_message(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/clr")
def cmd_clr(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    current_amount[uid] = "0"
    edit_message(uid, mid, "💰 <b>ENTER AMOUNT</b>\n\n₹0", "HTML", msg.get("reply_markup"))
    return True

@command("/done")
def cmd_done(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    amt = current_amount.get(uid, "0")
    if not amt or amt == "0":
        send_message(uid, "Enter amount!", "HTML")
        return True
    
    set_user(uid, "last_deposit_amount", float(amt))
    
    upi = "bablu.xyztb@fam"
    url = f"https://fampay.anujbots.xyz/qr.php?upi={upi}&amount={amt}"
    try:
        r = requests.get(url)
        data = r.json()
    except:
        send_message(uid, "API ERROR")
        return True
    if data.get("status") != "success":
        send_message(uid, "QR FAILED")
        return True
    
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    payment_orders.update_one(
        {"order_id": order_id},
        {"$set": {"order_id": order_id, "user_id": str(uid), "amount": float(amt), "product_name": "Add Funds", "created_at": datetime.now(), "status": "pending"}},
        upsert=True
    )
    
    pending_pays[uid] = {"order_id": order_id, "msg_id": msg.get("message_id"), "user_id": str(uid)}
    pending_payments.update_one({"user_id": str(uid)}, {"$set": {"data": pending_pays[uid]}}, upsert=True)
    
    caption = f"💰 <b>PAYMENT QR</b>\n\nAmount: ₹{amt}\n\n🧾 Order: <code>{order_id}</code>"
    kb = {"inline_keyboard": [[{"text": "✅ VERIFY", "callback_data": f"/v_{order_id}"}], [{"text": "❌ CANCEL", "callback_data": f"/c_{order_id}"}]]}
    send_photo(uid, qr_url, caption, "HTML", kb)
    return True

# ========== ADMIN COMMANDS ==========

@command("/admin")
def cmd_admin(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    if str(uid) not in ADMIN_IDS:
        send_message(uid, "🚫 Not Admin", "HTML")
        return True
    
    kb = {
        "inline_keyboard": [
            [{"text": "📦 Manage Products", "callback_data": "/admin_products"}],
            [{"text": "👑 Manage Admins", "callback_data": "/admin_admins"}],
            [{"text": "📣 Broadcast", "callback_data": "/broadcast"}],
            [{"text": "💰 Add Balance", "callback_data": "/addbalance"}],
            [{"text": "📝 Reseller Management", "callback_data": "/admin_resellers"}]
        ]
    }
    text = "👋 <b>ADMIN PANEL</b>\n━━━━━━━━━━━━━━━━━━"
    try:
        edit_message(uid, mid, text, "HTML", kb)
    except:
        send_message(uid, text, "HTML", kb)
    return True

# ========== PRODUCT MANAGEMENT ADMIN ==========

@command("/admin_products")
def cmd_admin_products(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    prods = get_products()
    text = "📦 <b>MANAGE PRODUCTS</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    
    if not prods:
        text += "No products."
    else:
        for i, p in enumerate(prods, 1):
            text += f"{i}. {p.get('name')}\n"
            text += f"   🔑 PID: {p.get('pid')}\n"
            text += f"   📱 Android: {'Required' if p.get('needs_android', True) else 'Not Required'}\n"
            text += f"   🎨 Emoji: {p.get('emoji_id', 'None')}\n"
            for plan in p.get('plans', []):
                text += f"   • {plan.get('duration')} - ₹{plan.get('price')}"
                if plan.get('reseller_price'):
                    text += f" (Reseller: ₹{plan.get('reseller_price')})"
                text += f" [ID: {plan.get('plan_id')}]\n"
            text += "\n"
    
    kb = {
        "inline_keyboard": [
            [{"text": "➕ Add Product", "callback_data": "/add_prod"}],
            [{"text": "✏️ Edit Product", "callback_data": "/edit_prod"}],
            [{"text": "🗑️ Delete Product", "callback_data": "/del_prod"}],
            [{"text": "🔙 Back", "callback_data": "/admin"}]
        ]
    }
    
    try:
        edit_message(uid, mid, text, "HTML", kb)
    except:
        send_message(uid, text, "HTML", kb)
    return True

# ========== ADD PRODUCT ==========

@command("/add_prod")
def cmd_add_prod(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    text = """
➕ <b>ADD PRODUCT</b>
━━━━━━━━━━━━━━━━━━

Format: <code>product_id|name|pid|needs_android|emoji_id</code>
Example: <code>my_mod|MY MOD|143|false|5345976085735558094</code>

needs_android: true/false
emoji_id: optional

Type /cancel
"""
    send_message(uid, text, "HTML")
    pending_cmds[uid] = "/add_prod_process"
    pending_commands.update_one({"user_id": str(uid)}, {"$set": {"command": "/add_prod_process"}}, upsert=True)
    return True

@command("/add_prod_process")
def cmd_add_prod_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "")
    
    if text.lower() == "/cancel":
        send_message(uid, "❌ Cancelled", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    parts = text.split('|')
    if len(parts) < 3:
        send_message(uid, "❌ Invalid! Use: product_id|name|pid|needs_android|emoji_id", "HTML")
        return True
    
    product_id = parts[0].strip()
    name = parts[1].strip()
    pid = parts[2].strip()
    needs_android = parts[3].strip().lower() == 'true' if len(parts) > 3 else True
    emoji_id = parts[4].strip() if len(parts) > 4 and parts[4].strip() else None
    
    if get_product(product_id):
        send_message(uid, f"❌ Product '{product_id}' exists!", "HTML")
        return True
    
    add_product(product_id, name, pid, needs_android, emoji_id)
    
    kb = {
        "inline_keyboard": [
            [{"text": "📋 Add Plan", "callback_data": f"/add_plan_{product_id}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    send_message(
        uid,
        f"✅ Product Added!\n\n📦 {name}\n🔑 PID: {pid}\n📱 Android: {'Required' if needs_android else 'Not Required'}\n🎨 Emoji: {emoji_id or 'None'}\n\nAdd plans:",
        "HTML",
        kb
    )
    pending_cmds.pop(uid, None)
    pending_commands.delete_one({"user_id": str(uid)})
    return True

# ========== ADD PLAN ==========

@command("/add_plan")
def cmd_add_plan(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    cmd = msg.get("text", "")
    product_id = cmd.replace("/add_plan_", "") if "/add_plan_" in cmd else params
    
    if not product_id:
        send_message(uid, "Product ID missing")
        return True
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found")
        return True
    
    set_user(uid, "add_plan_prod", product_id)
    
    text = f"""
📋 <b>ADD PLAN to {p.get('name')}</b>
━━━━━━━━━━━━━━━━━━

Format: <code>plan_id|duration|price|reseller_price</code>
Example: <code>1|1 DaYS NONROOT|108|95</code>

Type /cancel
"""
    send_message(uid, text, "HTML")
    pending_cmds[uid] = "/add_plan_process"
    pending_commands.update_one({"user_id": str(uid)}, {"$set": {"command": "/add_plan_process"}}, upsert=True)
    return True

@command("/add_plan_process")
def cmd_add_plan_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "")
    
    if text.lower() == "/cancel":
        send_message(uid, "❌ Cancelled", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        set_user(uid, "add_plan_prod", None)
        return True
    
    product_id = get_user(uid, "add_plan_prod")
    if not product_id:
        send_message(uid, "Product not found", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    parts = text.split('|')
    if len(parts) < 4:
        send_message(uid, "❌ Invalid! Use: plan_id|duration|price|reseller_price", "HTML")
        return True
    
    plan_id = parts[0].strip()
    duration = parts[1].strip()
    try:
        price = float(parts[2].strip())
        reseller_price = float(parts[3].strip())
    except:
        send_message(uid, "❌ Price must be numbers!", "HTML")
        return True
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        set_user(uid, "add_plan_prod", None)
        return True
    
    for plan in p.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            send_message(uid, f"❌ Plan ID '{plan_id}' exists!", "HTML")
            return True
    
    add_plan(product_id, plan_id, duration, price, reseller_price)
    
    kb = {
        "inline_keyboard": [
            [{"text": "➕ Add Another", "callback_data": f"/add_plan_{product_id}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    send_message(
        uid,
        f"✅ Plan Added!\n\n📦 {p.get('name')}\n📋 {duration}\n💰 ₹{price}\n💰 Reseller: ₹{reseller_price}",
        "HTML",
        kb
    )
    pending_cmds.pop(uid, None)
    pending_commands.delete_one({"user_id": str(uid)})
    set_user(uid, "add_plan_prod", None)
    return True

# ========== EDIT PRODUCT ==========

@command("/edit_prod")
def cmd_edit_prod(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    prods = get_products()
    if not prods:
        send_message(uid, "No products to edit.", "HTML")
        return True
    
    kb = {"inline_keyboard": []}
    for p in prods:
        pid = p.get('product_id')
        kb["inline_keyboard"].append([{"text": f"✏️ {p.get('name')}", "callback_data": f"/edit_{pid}"}])
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "/admin_products"}])
    
    try:
        edit_message(uid, mid, "Select product to edit:", "HTML", kb)
    except:
        send_message(uid, "Select product to edit:", "HTML", kb)
    return True

@command("/edit_abcd")
@command("/edit_bala_v2")
@command("/edit_drip")
@command("/edit_silent")
@command("/edit_prime")
def cmd_edit_select(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    cmd = msg.get("text", "")
    product_id = cmd.replace("/edit_", "")
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found")
        return True
    
    set_user(uid, "editing_product", product_id)
    
    text = f"""
✏️ <b>EDIT PRODUCT: {p.get('name')}</b>
━━━━━━━━━━━━━━━━━━

📦 ID: {p.get('product_id')}
🔑 PID: {p.get('pid')}
📱 Android: {'Required' if p.get('needs_android', True) else 'Not Required'}
🎨 Emoji: {p.get('emoji_id', 'None')}

📋 Plans:
"""
    for plan in p.get('plans', []):
        text += f"  • {plan.get('duration')} - ₹{plan.get('price')} (Reseller: ₹{plan.get('reseller_price')}) [ID: {plan.get('plan_id')}]\n"
    
    kb = {
        "inline_keyboard": [
            [{"text": "🔑 Change PID", "callback_data": f"/editpid_{product_id}"}],
            [{"text": "🎨 Change Emoji", "callback_data": f"/editemoji_{product_id}"}],
            [{"text": "📋 Edit Plan", "callback_data": f"/editplan_{product_id}"}],
            [{"text": "🗑️ Remove Plan", "callback_data": f"/rmplan_{product_id}"}],
            [{"text": "📱 Toggle Android", "callback_data": f"/togandroid_{product_id}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    try:
        edit_message(uid, mid, text, "HTML", kb)
    except:
        send_message(uid, text, "HTML", kb)
    return True

# ========== CHANGE PID ==========

@command("/editpid")
def cmd_editpid(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    cmd = msg.get("text", "")
    product_id = cmd.replace("/editpid_", "") if "/editpid_" in cmd else params
    
    if not product_id:
        send_message(uid, "Product ID missing")
        return True
    
    set_user(uid, "edit_pid_prod", product_id)
    send_message(uid, f"🔑 Send new PID for {product_id}\n\nType /cancel", "HTML")
    pending_cmds[uid] = "/editpid_process"
    pending_commands.update_one({"user_id": str(uid)}, {"$set": {"command": "/editpid_process"}}, upsert=True)
    return True

@command("/editpid_process")
def cmd_editpid_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(uid, "❌ Cancelled", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        set_user(uid, "edit_pid_prod", None)
        return True
    
    product_id = get_user(uid, "edit_pid_prod")
    if not product_id:
        send_message(uid, "No product", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        set_user(uid, "edit_pid_prod", None)
        return True
    
    update_pid(product_id, text)
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}]]}
    send_message(uid, f"✅ PID Updated!\n\n📦 {p.get('name')}\n🔑 New PID: {text}", "HTML", kb)
    pending_cmds.pop(uid, None)
    pending_commands.delete_one({"user_id": str(uid)})
    set_user(uid, "edit_pid_prod", None)
    return True

# ========== CHANGE EMOJI ==========

@command("/editemoji")
def cmd_editemoji(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    cmd = msg.get("text", "")
    product_id = cmd.replace("/editemoji_", "") if "/editemoji_" in cmd else params
    
    if not product_id:
        send_message(uid, "Product ID missing")
        return True
    
    set_user(uid, "edit_emoji_prod", product_id)
    send_message(uid, f"🎨 Send new Emoji ID for {product_id}\n\nExample: 5345976085735558094\n\nType /cancel", "HTML")
    pending_cmds[uid] = "/editemoji_process"
    pending_commands.update_one({"user_id": str(uid)}, {"$set": {"command": "/editemoji_process"}}, upsert=True)
    return True

@command("/editemoji_process")
def cmd_editemoji_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(uid, "❌ Cancelled", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        set_user(uid, "edit_emoji_prod", None)
        return True
    
    product_id = get_user(uid, "edit_emoji_prod")
    if not product_id:
        send_message(uid, "No product", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        set_user(uid, "edit_emoji_prod", None)
        return True
    
    update_emoji(product_id, text)
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}]]}
    send_message(uid, f"✅ Emoji Updated!\n\n📦 {p.get('name')}\n🎨 New Emoji: {text}", "HTML", kb)
    pending_cmds.pop(uid, None)
    pending_commands.delete_one({"user_id": str(uid)})
    set_user(uid, "edit_emoji_prod", None)
    return True

# ========== EDIT PLAN ==========

@command("/editplan")
def cmd_editplan(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    cmd = msg.get("text", "")
    product_id = cmd.replace("/editplan_", "") if "/editplan_" in cmd else params
    
    if not product_id:
        send_message(uid, "Product ID missing")
        return True
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found")
        return True
    
    if not p.get('plans'):
        send_message(uid, "No plans for this product.", "HTML")
        return True
    
    set_user(uid, "edit_plan_prod", product_id)
    
    text = f"📋 Select plan to edit for {p.get('name')}"
    kb = {"inline_keyboard": []}
    for plan in p.get('plans', []):
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        kb["inline_keyboard"].append([{"text": f"{duration} [ID: {plan_id}]", "callback_data": f"/editplan_select_{product_id}_{plan_id}"}])
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}])
    
    try:
        edit_message(uid, mid, text, "HTML", kb)
    except:
        send_message(uid, text, "HTML", kb)
    return True

@command("/editplan_select")
def cmd_editplan_select(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    cmd = msg.get("text", "")
    parts = cmd.split("_")
    if len(parts) >= 4:
        product_id = parts[3]
        plan_id = parts[4]
    else:
        send_message(uid, "Invalid selection")
        return True
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found")
        return True
    
    selected = None
    for plan in p.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected = plan
            break
    
    if not selected:
        send_message(uid, "Plan not found")
        return True
    
    set_user(uid, "edit_plan_data", {"product_id": product_id, "plan_id": plan_id})
    
    text = f"""
✏️ <b>EDIT PLAN</b>
━━━━━━━━━━━━━━━━━━
📦 Product: {p.get('name')}
📋 Plan: {selected.get('duration')}
💰 Price: ₹{selected.get('price')}
💰 Reseller: ₹{selected.get('reseller_price')}

Send: <code>price|reseller_price</code>
Example: <code>150|130</code>

Type /cancel
"""
    send_message(uid, text, "HTML")
    pending_cmds[uid] = "/editplan_process"
    pending_commands.update_one({"user_id": str(uid)}, {"$set": {"command": "/editplan_process"}}, upsert=True)
    return True

@command("/editplan_process")
def cmd_editplan_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(uid, "❌ Cancelled", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        set_user(uid, "edit_plan_data", None)
        return True
    
    edit_data = get_user(uid, "edit_plan_data")
    if not edit_data:
        send_message(uid, "No plan", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    parts = text.split('|')
    if len(parts) < 2:
        send_message(uid, "❌ Use: price|reseller_price", "HTML")
        return True
    
    try:
        price = float(parts[0].strip())
        reseller_price = float(parts[1].strip())
    except:
        send_message(uid, "❌ Numbers only!", "HTML")
        return True
    
    product_id = edit_data.get("product_id")
    plan_id = edit_data.get("plan_id")
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        set_user(uid, "edit_plan_data", None)
        return True
    
    update_plan_price(product_id, plan_id, price, reseller_price)
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}]]}
    send_message(uid, f"✅ Plan Updated!\n\n📦 {p.get('name')}\n💰 ₹{price}\n💰 Reseller: ₹{reseller_price}", "HTML", kb)
    pending_cmds.pop(uid, None)
    pending_commands.delete_one({"user_id": str(uid)})
    set_user(uid, "edit_plan_data", None)
    return True

# ========== REMOVE PLAN ==========

@command("/rmplan")
def cmd_rmplan(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    cmd = msg.get("text", "")
    product_id = cmd.replace("/rmplan_", "") if "/rmplan_" in cmd else params
    
    if not product_id:
        send_message(uid, "Product ID missing")
        return True
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found")
        return True
    
    if not p.get('plans'):
        send_message(uid, "No plans to remove.", "HTML")
        return True
    
    text = f"🗑️ Select plan to remove from {p.get('name')}"
    kb = {"inline_keyboard": []}
    for plan in p.get('plans', []):
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        kb["inline_keyboard"].append([{"text": f"❌ {duration}", "callback_data": f"/rmplan_confirm_{product_id}_{plan_id}"}])
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}])
    
    try:
        edit_message(uid, mid, text, "HTML", kb)
    except:
        send_message(uid, text, "HTML", kb)
    return True

@command("/rmplan_confirm")
def cmd_rmplan_confirm(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    cmd = msg.get("text", "")
    parts = cmd.split("_")
    if len(parts) >= 4:
        product_id = parts[3]
        plan_id = parts[4]
    else:
        send_message(uid, "Invalid selection")
        return True
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found")
        return True
    
    selected = None
    for plan in p.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected = plan
            break
    
    if not selected:
        send_message(uid, "Plan not found")
        return True
    
    remove_plan(product_id, plan_id)
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}]]}
    send_message(uid, f"✅ Plan Removed!\n\n📦 {p.get('name')}\n📋 {selected.get('duration')}", "HTML", kb)
    return True

# ========== TOGGLE ANDROID ==========

@command("/togandroid")
def cmd_togandroid(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    cmd = msg.get("text", "")
    product_id = cmd.replace("/togandroid_", "") if "/togandroid_" in cmd else params
    
    if not product_id:
        send_message(uid, "Product ID missing")
        return True
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found")
        return True
    
    new_val = toggle_android(product_id)
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}]]}
    send_message(uid, f"✅ Android: {'Required' if new_val else 'Not Required'}", "HTML", kb)
    return True

# ========== DELETE PRODUCT ==========

@command("/del_prod")
def cmd_del_prod(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    prods = get_products()
    if not prods:
        send_message(uid, "No products to delete.", "HTML")
        return True
    
    kb = {"inline_keyboard": []}
    for p in prods:
        pid = p.get('product_id')
        kb["inline_keyboard"].append([{"text": f"🗑️ {p.get('name')}", "callback_data": f"/del_confirm_{pid}"}])
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "/admin_products"}])
    
    try:
        edit_message(uid, mid, "Select product to delete:", "HTML", kb)
    except:
        send_message(uid, "Select product to delete:", "HTML", kb)
    return True

@command("/del_confirm")
def cmd_del_confirm(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    cmd = msg.get("text", "")
    product_id = cmd.replace("/del_confirm_", "") if "/del_confirm_" in cmd else params
    
    if not product_id:
        return True
    
    p = get_product(product_id)
    if not p:
        send_message(uid, "Product not found")
        return True
    
    kb = {"inline_keyboard": [[{"text": "✅ Yes", "callback_data": f"/del_yes_{product_id}"}], [{"text": "❌ No", "callback_data": "/admin_products"}]]}
    
    try:
        edit_message(uid, mid, f"⚠️ Delete {p.get('name')}?", "HTML", kb)
    except:
        send_message(uid, f"⚠️ Delete {p.get('name')}?", "HTML", kb)
    return True

@command("/del_yes")
def cmd_del_yes(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    cmd = msg.get("text", "")
    product_id = cmd.replace("/del_yes_", "") if "/del_yes_" in cmd else params
    
    if not product_id:
        return True
    
    p = get_product(product_id)
    if p:
        delete_product(product_id)
        send_message(uid, f"✅ Deleted {p.get('name')}", "HTML")
    else:
        send_message(uid, "Product not found", "HTML")
    return True

# ========== RESELLER MANAGEMENT ==========

@command("/admin_resellers")
def cmd_admin_resellers(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    kb = {
        "inline_keyboard": [
            [{"text": "➕ Add Reseller", "callback_data": "/addreseller"}],
            [{"text": "📝 Reseller List", "callback_data": "/resellerlist"}],
            [{"text": "🔙 Back", "callback_data": "/admin"}]
        ]
    }
    
    try:
        edit_message(uid, mid, "💰 <b>RESELLER MANAGEMENT</b>", "HTML", kb)
    except:
        send_message(uid, "💰 <b>RESELLER MANAGEMENT</b>", "HTML", kb)
    return True

@command("/addreseller")
def cmd_addreseller(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    send_message(uid, "📩 Send user ID\n\nType /cancel", "HTML")
    pending_cmds[uid] = "/addreseller_process"
    pending_commands.update_one({"user_id": str(uid)}, {"$set": {"command": "/addreseller_process"}}, upsert=True)
    return True

@command("/addreseller_process")
def cmd_addreseller_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(uid, "❌ Cancelled", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    try:
        target = str(int(text))
    except:
        send_message(uid, "❌ Invalid ID!", "HTML")
        return True
    
    resellers = get_data("resellers_list") or []
    if target in [str(u) for u in resellers]:
        send_message(uid, "Already reseller", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    resellers.append(target)
    set_data("resellers_list", resellers)
    send_message(uid, f"✅ Added <code>{target}</code>", "HTML")
    try:
        send_message(target, "🎉 You are now a Reseller!", "HTML")
    except:
        pass
    pending_cmds.pop(uid, None)
    pending_commands.delete_one({"user_id": str(uid)})
    return True

@command("/resellerlist")
def cmd_resellerlist(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    resellers = get_data("resellers_list") or []
    if not resellers:
        text = "No resellers found."
    else:
        text = "💰 <b>RESELLER LIST</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for i, r in enumerate(resellers, 1):
            text += f"{i}. <code>{r}</code>\n"
        text += f"\nTotal: {len(resellers)}"
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "/admin_resellers"}]]}
    try:
        edit_message(uid, mid, text, "HTML", kb)
    except:
        send_message(uid, text, "HTML", kb)
    return True

# ========== ADMIN MANAGEMENT ==========

@command("/admin_admins")
def cmd_admin_admins(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    text = "👑 <b>ADMIN MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for admin in ADMIN_IDS:
        text += f"• <code>{admin}</code> (Main Admin)\n"
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "/admin"}]]}
    
    try:
        edit_message(uid, mid, text, "HTML", kb)
    except:
        send_message(uid, text, "HTML", kb)
    return True

# ========== ADD BALANCE ==========

@command("/addbalance")
def cmd_addbalance(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    send_message(uid, "💡 Send: <code>user_id amount</code>\nExample: <code>123456 100</code>\nUse - for deduct: <code>123456 -50</code>", "HTML")
    pending_cmds[uid] = "/addbalance_process"
    pending_commands.update_one({"user_id": str(uid)}, {"$set": {"command": "/addbalance_process"}}, upsert=True)
    return True

@command("/addbalance_process")
def cmd_addbalance_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    parts = text.split(" ")
    if len(parts) < 2:
        send_message(uid, "Invalid! Use: user_id amount", "HTML")
        return True
    
    target = parts[0]
    try:
        amount = float(parts[1])
    except:
        send_message(uid, "Invalid amount!", "HTML")
        return True
    
    bal = Resources.another_res("Balance", target)
    bal.add(amount)
    
    send_message(uid, f"✅ Added ₹{amount} to <code>{target}</code>\n💰 New Balance: ₹{bal.value()}", "HTML")
    try:
        send_message(target, f"💰 Admin added ₹{amount} to your balance!", "HTML")
    except:
        pass
    
    pending_cmds.pop(uid, None)
    pending_commands.delete_one({"user_id": str(uid)})
    return True

# ========== BROADCAST ==========

@command("/broadcast")
def cmd_broadcast(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    if str(uid) not in ADMIN_IDS:
        return True
    
    users = user_data.distinct("user_id")
    send_message(uid, f"📢 <b>BROADCAST</b>\n━━━━━━━━━━━━━━━━━━\n👥 Users: {len(users)}\n\nSend message\nType /cancel", "HTML")
    pending_cmds[uid] = "/broadcast_send"
    pending_commands.update_one({"user_id": str(uid)}, {"$set": {"command": "/broadcast_send"}}, upsert=True)
    return True

@command("/broadcast_send")
def cmd_broadcast_send(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    if str(uid) not in ADMIN_IDS:
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    if msg.get("text") and msg.get("text", "").strip() == "/cancel":
        send_message(uid, "❌ Cancelled", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    users = user_data.distinct("user_id")
    if not users:
        send_message(uid, "No users!", "HTML")
        pending_cmds.pop(uid, None)
        pending_commands.delete_one({"user_id": str(uid)})
        return True
    
    from_chat_id = msg.get("chat", {}).get("id")
    msg_id_to_forward = msg.get("message_id")
    
    success = 0
    for target in users:
        try:
            forward_message(target, from_chat_id, msg_id_to_forward)
            success += 1
        except:
            try:
                if msg.get("text"):
                    send_message(target, msg.get("text", ""), "HTML")
                    success += 1
            except:
                pass
        time.sleep(0.1)
    
    send_message(uid, f"✅ Broadcast done!\n📤 Sent: {success}/{len(users)}", "HTML")
    pending_cmds.pop(uid, None)
    pending_commands.delete_one({"user_id": str(uid)})
    return True

@command("/setMyCommands")
def cmd_set_commands(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    cmds = [{"command": "start", "description": "START"}]
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands", json={"commands": cmds})
        send_message(uid, "✅ Done!", "HTML")
    except:
        send_message(uid, "Error!", "HTML")
    return True

def handle_update(update):
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        uid = cb.get("from", {}).get("id")
        mid = cb.get("message", {}).get("message_id")
        answer_callback(cb.get("id"))
        
        parts = data.split(" ")
        cmd = parts[0]
        params = " ".join(parts[1:]) if len(parts) > 1 else None
        
        msg = {
            "message_id": mid,
            "from": cb.get("from", {}),
            "chat": {"id": uid},
            "date": int(time.time()),
            "text": data,
            "reply_markup": cb.get("message", {}).get("reply_markup")
        }
        
        if cmd in commands:
            try:
                commands[cmd](msg, params)
            except Exception as e:
                print(f"Callback error: {e}")
        return
    
    if "message" in update:
        msg = update["message"]
        uid = msg.get("from", {}).get("id")
        text = msg.get("text", "")
        
        if uid in pending_cmds:
            pending_cmd = pending_cmds[uid]
            if pending_cmd in commands:
                try:
                    commands[pending_cmd](msg, None)
                except Exception as e:
                    print(f"Pending error: {e}")
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
    setup_products()
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
