# tusharbot.py - SIMPLE WORKING
import requests
import json
import time
from datetime import datetime
from pymongo import MongoClient

BOT_TOKEN = "8565204943:AAEw7F-5NIwZjluyWT-PQYk70xHY3j01xAo"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ========== MONGODB ==========
MONGO_URI = "mongodb+srv://crasher3210_db_user:devex5656@cluster0.9y5axka.mongodb.net/?appName=Cluster0&compressors=zlib"
DB_NAME = "telegram_bot1"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
bot_data_col = db['bot_data']
user_data_col = db['user_data']
pending_commands_col = db['pending_commands']
pending_payments_col = db['pending_payments']
payment_orders_col = db['payment_orders']
products_col = db['products']

# ========== DATA FUNCTIONS ==========
def get_data(key, default=None):
    doc = bot_data_col.find_one({"key": key})
    return doc.get("value") if doc else default

def set_data(key, value):
    bot_data_col.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

def get_user_data(user_id, key, default=None):
    doc = user_data_col.find_one({"user_id": str(user_id), "key": key})
    return doc.get("value") if doc else default

def set_user_data(user_id, key, value):
    user_data_col.update_one({"user_id": str(user_id), "key": key}, {"$set": {"value": value}}, upsert=True)

def get_products():
    return list(products_col.find())

def get_product(product_id):
    return products_col.find_one({"product_id": product_id})

def add_product(product_id, name, pid, needs_android):
    products_col.update_one(
        {"product_id": product_id},
        {"$set": {"product_id": product_id, "name": name, "pid": pid, "needs_android": needs_android, "plans": []}},
        upsert=True
    )

def add_plan(product_id, plan_id, duration, price, reseller_price):
    products_col.update_one(
        {"product_id": product_id},
        {"$push": {"plans": {"plan_id": plan_id, "duration": duration, "price": price, "reseller_price": reseller_price}}}
    )

def delete_product(product_id):
    products_col.delete_one({"product_id": product_id})

def update_pid(product_id, new_pid):
    products_col.update_one({"product_id": product_id}, {"$set": {"pid": new_pid}})

def update_plan(product_id, plan_id, price, reseller_price):
    products_col.update_one(
        {"product_id": product_id, "plans.plan_id": plan_id},
        {"$set": {"plans.$.price": price, "plans.$.reseller_price": reseller_price}}
    )

def remove_plan(product_id, plan_id):
    products_col.update_one({"product_id": product_id}, {"$pull": {"plans": {"plan_id": plan_id}}})

# ========== API ==========
RESELLER_API_URL = "https://xyzcheats.com/api/reseller_v1.php"
RESELLER_API_KEY = "b25eb076f5c0412fa9f1eba94550d02e"
RESELLER_API_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'x-master-key': 'a7f3e8b2c9d1f4a6b8c2d5e9f1a3b6c8'
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
pending_commands = {}
pending_payments = {}
current_amount = {}

def command(name):
    def decorator(func):
        commands[name] = func
        return func
    return decorator

# ========== PROCESS PURCHASE ==========
def process_purchase(message, product_id, plan_id, price, product_name, duration, pid, android_id=None):
    user_id = message.get("from", {}).get("id")
    balance = Resources.another_res("Balance", user=user_id)
    
    if balance.value() < price:
        set_user_data(user_id, "last_deposit_amount", price)
        set_user_data(user_id, "last_product", product_name)
        cmd_autobuy1(message, None)
        return True
    
    balance.cut(price)
    Resources.another_res("Order", user=user_id).add(1)
    
    success, result = generate_api_key(pid, duration, android_id, price)
    
    if success:
        send_message(
            user_id,
            f"🛒 {product_name}\n\n🔑 <b>Your Key:</b>\n<code>{result}</code>\n\n💰 Deducted: ₹{price}\n⏳ Duration: {duration}\n📦 Time: {get_easy_time()}",
            "HTML"
        )
        adm_ac = get_user_data(user_id, "userhAC") or []
        adm_ac.append(f"📆 {get_easy_time()}\n👤 {message.get('from', {}).get('first_name', 'User')} [{user_id}]\n💰 ₹{price}\n🔑 {result}")
        set_user_data(user_id, "userhAC", adm_ac)
        return True
    else:
        balance.add(price)
        send_message(
            user_id,
            f"❌ <b>Key Generation Failed</b>\n\nError: {result}\n\nYour balance of ₹{price} has been refunded.",
            "HTML"
        )
        return True

# ========== DEFAULT PRODUCTS ==========
def setup_default_products():
    products = {
        "abcd": {"name": "ABCD", "pid": "143", "needs_android": False, "plans": [{"plan_id": "1", "duration": "12 Hours", "price": 10, "reseller_price": 8}]},
        "bala_v2": {"name": "BALA MODS XYZ V2", "pid": "136", "needs_android": False, "plans": [
            {"plan_id": "1", "duration": "1 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 10, "reseller_price": 8},
            {"plan_id": "2", "duration": "3 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 25, "reseller_price": 20},
            {"plan_id": "3", "duration": "6 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 45, "reseller_price": 38},
            {"plan_id": "4", "duration": "12 Hours [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 80, "reseller_price": 68},
            {"plan_id": "5", "duration": "1 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 150, "reseller_price": 130},
            {"plan_id": "6", "duration": "2 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 250, "reseller_price": 210},
            {"plan_id": "7", "duration": "3 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 350, "reseller_price": 300},
            {"plan_id": "8", "duration": "5 Day [BALA MODS XYZ V2 (Auto - No HWID)]", "price": 500, "reseller_price": 430},
        ]},
        "drip": {"name": "DRIP CLIENT MOD", "pid": "133", "needs_android": True, "plans": [
            {"plan_id": "1", "duration": "1 DaYS NONROOT", "price": 108, "reseller_price": 95},
            {"plan_id": "2", "duration": "3 DaYS NONROOT", "price": 260, "reseller_price": 220},
            {"plan_id": "3", "duration": "7 DaYS NONROOT", "price": 360, "reseller_price": 320},
            {"plan_id": "4", "duration": "15 DaYS NONROOT", "price": 560, "reseller_price": 480},
            {"plan_id": "5", "duration": "30 DaYS NONROOT", "price": 810, "reseller_price": 750},
        ]},
        "silent": {"name": "SILENT CHEATS ANDROID", "pid": "133", "needs_android": True, "plans": [
            {"plan_id": "1", "duration": "1 DaYS NONROOT", "price": 108, "reseller_price": 95},
            {"plan_id": "2", "duration": "3 DaYS NONROOT", "price": 260, "reseller_price": 220},
            {"plan_id": "3", "duration": "7 DaYS NONROOT", "price": 360, "reseller_price": 320},
            {"plan_id": "4", "duration": "14 DaYS NONROOT", "price": 560, "reseller_price": 480},
            {"plan_id": "5", "duration": "28 DaYS NONROOT", "price": 810, "reseller_price": 750},
        ]},
        "prime": {"name": "PRIME HOOK", "pid": "133", "needs_android": True, "plans": [
            {"plan_id": "1", "duration": "1 DaYS NONROOT", "price": 108, "reseller_price": 95},
            {"plan_id": "2", "duration": "3 DaYS NONROOT", "price": 200, "reseller_price": 180},
            {"plan_id": "3", "duration": "7 DaYS NONROOT", "price": 360, "reseller_price": 320},
            {"plan_id": "4", "duration": "14 DaYS NONROOT", "price": 600, "reseller_price": 550},
            {"plan_id": "5", "duration": "21 DaYS NONROOT", "price": 700, "reseller_price": 650},
        ]}
    }
    
    for pid, data in products.items():
        if not get_product(pid):
            add_product(pid, data["name"], data["pid"], data["needs_android"])
            for plan in data["plans"]:
                add_plan(pid, plan["plan_id"], plan["duration"], plan["price"], plan["reseller_price"])
            print(f"✅ Added: {data['name']}")

# ========== USER COMMANDS ==========

@command("/start")
def cmd_start(message, params, options=None):
    user_id = message.get("from", {}).get("id")
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
            [{"text": "💰 ADD FUND", "callback_data": "/addpayment"}],
            [{"text": "📥 DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl"}]
        ]
    }
    send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/shopnawkk")
def cmd_shopnawkk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    products = get_products()
    
    if not products:
        text = "⚠️ No products available."
        reply_markup = {"inline_keyboard": [[{"text": "🔙 BACK", "callback_data": "/backkkk"}]]}
        try:
            edit_message(user_id, msg_id, text, "HTML", reply_markup)
        except:
            send_message(user_id, text, "HTML", reply_markup)
        return True
    
    text = "🛒 <b>PANNEL STORE — SHOP</b>\n━━━━━━━━━━━━━━━━━━\n\n📦 Choose a product:"
    
    keyboard = []
    for product in products:
        pid = product.get('product_id')
        keyboard.append([{"text": f"📦 {product.get('name')}", "callback_data": f"/p_{pid}"}])
    
    keyboard.append([{"text": "🔙 BACK", "callback_data": "/backkkk"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/p_abcd")
@command("/p_bala_v2")
@command("/p_drip")
@command("/p_silent")
@command("/p_prime")
def cmd_show_plans(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    cmd = message.get("text", "")
    product_id = cmd.replace("/p_", "")
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    resellers = get_data("resellers_list") or []
    is_reseller = str(user_id) in [str(u) for u in resellers]
    
    text = f"📦 <b>{product.get('name')}</b>\n━━━━━━━━━━━━━━━━━━\n\nChoose a plan 👇"
    
    keyboard = []
    for plan in product.get('plans', []):
        price = plan.get('reseller_price') if is_reseller else plan.get('price')
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        keyboard.append([{"text": f"{duration} - ₹{price}", "callback_data": f"/b_{product_id}_{plan_id}"}])
    
    keyboard.append([{"text": "🔙 BACK", "callback_data": "/shopnawkk"}])
    reply_markup = {"inline_keyboard": keyboard}
    
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
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
def cmd_buy(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    
    cmd = message.get("text", "")
    parts = cmd.split("_")
    if len(parts) >= 3:
        product_id = parts[1]
        plan_id = parts[2]
    else:
        send_message(user_id, "Invalid")
        return True
    
    product = get_product(product_id)
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
    
    resellers = get_data("resellers_list") or []
    is_reseller = str(user_id) in [str(u) for u in resellers]
    
    price = selected_plan.get('reseller_price') if is_reseller else selected_plan.get('price')
    duration = selected_plan.get('duration')
    product_name = product.get('name')
    pid = product.get('pid')
    needs_android = product.get('needs_android', True)
    
    set_user_data(user_id, "last_product", product_name)
    set_user_data(user_id, "last_plan", plan_id)
    set_user_data(user_id, "last_product_key", product_id)
    set_user_data(user_id, "last_price", price)
    set_user_data(user_id, "last_duration", duration)
    set_user_data(user_id, "last_pid", pid)
    
    if needs_android:
        send_message(
            user_id,
            f"🔐 <b>Android ID Required</b>\n\nProduct: {product_name}\nPlan: {duration}\nPrice: ₹{price}\n\nSend Android ID:\nType /cancel to cancel.",
            "HTML"
        )
        pending_commands[user_id] = "/process_android"
        pending_commands_col.update_one({"user_id": str(user_id)}, {"$set": {"command": "/process_android"}}, upsert=True)
        return True
    else:
        return process_purchase(message, product_id, plan_id, price, product_name, duration, pid)

@command("/process_android")
def cmd_process_android(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    if len(text) != 16 or not all(c in '0123456789abcdefABCDEF' for c in text):
        send_message(user_id, "❌ Invalid! 16 hex chars. Example: 0b9b969bc2e7997b", "HTML")
        return True
    
    pending_commands.pop(user_id, None)
    pending_commands_col.delete_one({"user_id": str(user_id)})
    
    product_id = get_user_data(user_id, "last_product_key")
    plan_id = get_user_data(user_id, "last_plan")
    price = get_user_data(user_id, "last_price")
    product_name = get_user_data(user_id, "last_product")
    duration = get_user_data(user_id, "last_duration")
    pid = get_user_data(user_id, "last_pid")
    
    return process_purchase(message, product_id, plan_id, price, product_name, duration, pid, android_id=text)

@command("/autobuy1")
def cmd_autobuy1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    amount = get_user_data(user_id, "last_deposit_amount")
    pt = get_user_data(user_id, "last_product") or "Unknown"
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
    
    payment_orders_col.update_one(
        {"order_id": order_id},
        {"$set": {"order_id": order_id, "user_id": str(user_id), "amount": amount, "product_name": pt, "created_at": datetime.now(), "status": "pending"}},
        upsert=True
    )
    
    set_user_data(user_id, "last_order_id", order_id)
    pending_payments[user_id] = {"order_id": order_id, "msg_id": message.get("message_id"), "user_id": str(user_id)}
    pending_payments_col.update_one({"user_id": str(user_id)}, {"$set": {"data": pending_payments[user_id]}}, upsert=True)
    
    caption = f"💰 <b>INSUFFICIENT BALANCE</b>\n\nProduct: {pt}\nPrice: ₹{amount}\nYour Balance: ₹{balance}\n\nScan QR:\n🧾 Order: <code>{order_id}</code>"
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ VERIFY", "callback_data": f"/v_{order_id}"}],
            [{"text": "❌ CANCEL", "callback_data": f"/c_{order_id}"}]
        ]
    }
    send_photo(user_id, qr_url, caption, "HTML", reply_markup)
    return True

@command("/v")
def cmd_verify(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    msg_id = message.get("message_id")
    
    cmd = message.get("text", "")
    if "/v_" in cmd:
        order_id = cmd.replace("/v_", "")
    else:
        order_id = params
    
    if not order_id:
        send_message(user_id, "No order ID.", "HTML")
        return True
    
    order_data = payment_orders_col.find_one({"order_id": order_id})
    if not order_data:
        send_message(user_id, "❌ Invalid Order.", "HTML")
        return True
    
    if str(order_data.get("user_id")) != str(user_id):
        send_message(user_id, "❌ Not your order!", "HTML")
        return True
    
    send_message(user_id, "⏳ Checking...", "HTML")
    
    url = f"https://fampay.anujbots.xyz/verify.php?order_id={order_id}&api_key=FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8"
    
    try:
        response = requests.get(url)
        data = response.json()
    except:
        send_message(user_id, "❌ API ERROR", "HTML")
        return True
    
    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        bal = Resources.another_res("Balance", user=user_id)
        bal.add(amount)
        
        payment_orders_col.update_one({"order_id": order_id}, {"$set": {"status": "verified"}})
        
        set_user_data(user_id, "last_order_id", "")
        pending_payments.pop(user_id, None)
        pending_payments_col.delete_one({"user_id": str(user_id)})
        
        if msg_id:
            try:
                delete_message(user_id, msg_id)
            except:
                pass
        
        send_message(user_id, f"✅ Payment Success!\n\n💰 Added: ₹{amount}\n💳 New Balance: ₹{bal.value()}", "HTML")
        return True
    else:
        send_message(user_id, f"❌ Payment Not Found\n\nOrder: <code>{order_id}</code>", "HTML")
        return True

@command("/c")
def cmd_cancel(message, params, options=None):
    user_id = str(message.get("from", {}).get("id"))
    msg_id = message.get("message_id")
    
    cmd = message.get("text", "")
    if "/c_" in cmd:
        order_id = cmd.replace("/c_", "")
    else:
        order_id = params
    
    if not order_id:
        pending = pending_payments_col.find_one({"user_id": str(user_id)})
        if pending:
            order_id = pending.get("data", {}).get("order_id")
    
    if order_id:
        payment_orders_col.delete_one({"order_id": order_id})
    
    if msg_id:
        try:
            delete_message(user_id, msg_id)
        except:
            pass
    
    pending_payments.pop(user_id, None)
    pending_payments_col.delete_one({"user_id": str(user_id)})
    pending_commands.pop(user_id, None)
    pending_commands_col.delete_one({"user_id": str(user_id)})
    send_message(user_id, "❌ Cancelled", "HTML")
    return True

@command("/backkkk")
def cmd_backkkk(message, params, options=None):
    return cmd_start(message, params, options)

@command("/orderksk")
def cmd_orderksk(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    adm_ac = get_user_data(user_id, "userhAC") or []
    if not adm_ac:
        text = "📦 <b>MY ORDERS</b>\n━━━━━━━━━━━━━━━━━━\n\nNo orders yet."
    else:
        text = "📦 <b>MY ORDERS</b>\n━━━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(adm_ac[-10:][::-1])
    
    reply_markup = {"inline_keyboard": [[{"text": "🔙 BACK", "callback_data": "/backkkk"}]]}
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/profilemmm")
def cmd_profilemmm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    first_name = message.get("from", {}).get("first_name", "User")
    balance = Resources.another_res("Balance", user=user_id).value()
    orders = Resources.another_res("Order", user=user_id).value()
    
    text = (
        "👤 <b>PROFILE</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Name: {first_name}\n"
        f"🆔 ID: {user_id}\n"
        f"💰 Balance: ₹{balance}\n"
        f"🛒 Orders: {orders}"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": "🛒 BUY", "callback_data": "/shopnawkk"}, {"text": "🔑 KEYS", "callback_data": "/orderksk"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
        ]
    }
    send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/spinj")
def cmd_spinj(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = "🎥 <b>Tutorial</b>\n\nWatch: https://t.me/hehehehhhsljg/162"
    reply_markup = {
        "inline_keyboard": [
            [{"text": "▶️ Watch", "url": "https://t.me/hehehehhhsljg/162"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
        ]
    }
    send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/supportj")
def cmd_supportj(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = "💬 <b>Support</b>\n\n<a href='https://t.me/UR_SUBHAJIT0'>Contact</a>"
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📱 WhatsApp", "url": "https://wa.me/917908696630"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
        ]
    }
    send_message(user_id, text, "HTML", reply_markup)
    return True

# ========== NUMBER PAD ==========

@command("/addpayment")
def cmd_addpayment(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    reply_markup = {
        "inline_keyboard": [
            [{"text": "1", "callback_data": "/n1"}, {"text": "2", "callback_data": "/n2"}, {"text": "3", "callback_data": "/n3"}],
            [{"text": "4", "callback_data": "/n4"}, {"text": "5", "callback_data": "/n5"}, {"text": "6", "callback_data": "/n6"}],
            [{"text": "7", "callback_data": "/n7"}, {"text": "8", "callback_data": "/n8"}, {"text": "9", "callback_data": "/n9"}],
            [{"text": "CLEAR", "callback_data": "/clr"}, {"text": "0", "callback_data": "/n0"}, {"text": "✅", "callback_data": "/done"}],
            [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
        ]
    }
    text = "💰 <b>ENTER AMOUNT</b>\n\n₹0"
    try:
        edit_message(user_id, msg_id, text, "HTML", reply_markup)
    except:
        send_message(user_id, text, "HTML", reply_markup)
    return True

@command("/n0")
def cmd_n0(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    if amt != "0":
        amt += "0"
    current_amount[user_id] = amt
    edit_message(user_id, msg_id, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", message.get("reply_markup"))
    return True

@command("/n1")
def cmd_n1(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "1" if amt == "0" else amt + "1"
    current_amount[user_id] = amt
    edit_message(user_id, msg_id, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", message.get("reply_markup"))
    return True

@command("/n2")
def cmd_n2(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "2" if amt == "0" else amt + "2"
    current_amount[user_id] = amt
    edit_message(user_id, msg_id, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", message.get("reply_markup"))
    return True

@command("/n3")
def cmd_n3(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "3" if amt == "0" else amt + "3"
    current_amount[user_id] = amt
    edit_message(user_id, msg_id, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", message.get("reply_markup"))
    return True

@command("/n4")
def cmd_n4(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "4" if amt == "0" else amt + "4"
    current_amount[user_id] = amt
    edit_message(user_id, msg_id, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", message.get("reply_markup"))
    return True

@command("/n5")
def cmd_n5(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "5" if amt == "0" else amt + "5"
    current_amount[user_id] = amt
    edit_message(user_id, msg_id, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", message.get("reply_markup"))
    return True

@command("/n6")
def cmd_n6(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "6" if amt == "0" else amt + "6"
    current_amount[user_id] = amt
    edit_message(user_id, msg_id, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", message.get("reply_markup"))
    return True

@command("/n7")
def cmd_n7(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "7" if amt == "0" else amt + "7"
    current_amount[user_id] = amt
    edit_message(user_id, msg_id, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", message.get("reply_markup"))
    return True

@command("/n8")
def cmd_n8(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "8" if amt == "0" else amt + "8"
    current_amount[user_id] = amt
    edit_message(user_id, msg_id, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", message.get("reply_markup"))
    return True

@command("/n9")
def cmd_n9(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    amt = current_amount.get(user_id, "0")
    amt = "9" if amt == "0" else amt + "9"
    current_amount[user_id] = amt
    edit_message(user_id, msg_id, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", message.get("reply_markup"))
    return True

@command("/clr")
def cmd_clr(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    current_amount[user_id] = "0"
    edit_message(user_id, msg_id, "💰 <b>ENTER AMOUNT</b>\n\n₹0", "HTML", message.get("reply_markup"))
    return True

@command("/done")
def cmd_done(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    amt = current_amount.get(user_id, "0")
    if not amt or amt == "0":
        send_message(user_id, "Enter amount!", "HTML")
        return True
    set_user_data(user_id, "last_deposit_amount", float(amt))
    
    # Generate QR
    upi = "bablu.xyztb@fam"
    url = f"https://fampay.anujbots.xyz/qr.php?upi={upi}&amount={amt}"
    try:
        response = requests.get(url)
        data = response.json()
    except:
        send_message(user_id, "API ERROR")
        return True
    if data.get("status") != "success":
        send_message(user_id, "QR FAILED")
        return True
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    payment_orders_col.update_one(
        {"order_id": order_id},
        {"$set": {"order_id": order_id, "user_id": str(user_id), "amount": float(amt), "product_name": "Add Funds", "created_at": datetime.now(), "status": "pending"}},
        upsert=True
    )
    
    pending_payments[user_id] = {"order_id": order_id, "msg_id": message.get("message_id"), "user_id": str(user_id)}
    pending_payments_col.update_one({"user_id": str(user_id)}, {"$set": {"data": pending_payments[user_id]}}, upsert=True)
    
    caption = f"💰 <b>PAYMENT QR</b>\n\nAmount: ₹{amt}\n\n🧾 Order: <code>{order_id}</code>"
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ VERIFY", "callback_data": f"/v_{order_id}"}],
            [{"text": "❌ CANCEL", "callback_data": f"/c_{order_id}"}]
        ]
    }
    send_photo(user_id, qr_url, caption, "HTML", reply_markup)
    return True

# ========== ADMIN COMMANDS ==========

@command("/admin")
def cmd_admin(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    admins = get_data("AllBotAdminss") or []
    if not admins:
        admins = [str(user_id)]
        set_data("AllBotAdminss", admins)
    
    if str(user_id) not in admins:
        send_message(user_id, "🚫 Not Admin", "HTML")
        return True
    
    markup = {
        "inline_keyboard": [
            [{"text": "📦 Products", "callback_data": "/admin_products"}],
            [{"text": "👑 Admins", "callback_data": "/admin_admins"}],
            [{"text": "📣 Broadcast", "callback_data": "/admin_broadcast"}],
            [{"text": "💰 Add Balance", "callback_data": "/admin_balance"}],
            [{"text": "📝 Resellers", "callback_data": "/admin_resellers"}]
        ]
    }
    text = "👋 <b>ADMIN PANEL</b>\n━━━━━━━━━━━━━━━━━━"
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

@command("/admin_products")
def cmd_admin_products(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    products = get_products()
    
    text = "📦 <b>PRODUCTS</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    if not products:
        text += "No products."
    else:
        for i, p in enumerate(products, 1):
            text += f"{i}. {p.get('name')}\n   PID: {p.get('pid')}\n   Android: {'✅' if p.get('needs_android', True) else '❌'}\n"
            for plan in p.get('plans', []):
                text += f"   • {plan.get('duration')} - ₹{plan.get('price')}\n"
            text += "\n"
    
    markup = {
        "inline_keyboard": [
            [{"text": "➕ Add", "callback_data": "/add_prod"}],
            [{"text": "✏️ Edit", "callback_data": "/edit_prod"}],
            [{"text": "🗑️ Delete", "callback_data": "/del_prod"}],
            [{"text": "🔙 Back", "callback_data": "/admin"}]
        ]
    }
    
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

@command("/add_prod")
def cmd_add_prod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    text = "➕ <b>ADD PRODUCT</b>\n━━━━━━━━━━━━━━━━━━\n\nFormat: <code>id|name|pid|android</code>\nExample: <code>my_mod|MY MOD|143|false</code>\n\nandroid: true/false\n\nType /cancel"
    send_message(user_id, text, "HTML")
    pending_commands[user_id] = "/add_prod_process"
    pending_commands_col.update_one({"user_id": str(user_id)}, {"$set": {"command": "/add_prod_process"}}, upsert=True)
    return True

@command("/add_prod_process")
def cmd_add_prod_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    parts = text.split('|')
    if len(parts) < 3:
        send_message(user_id, "❌ Invalid! Use: id|name|pid|android", "HTML")
        return True
    
    pid = parts[0].strip()
    name = parts[1].strip()
    api_pid = parts[2].strip()
    needs_android = parts[3].strip().lower() == 'true' if len(parts) > 3 else True
    
    if get_product(pid):
        send_message(user_id, f"❌ '{pid}' exists!", "HTML")
        return True
    
    add_product(pid, name, api_pid, needs_android)
    
    markup = {
        "inline_keyboard": [
            [{"text": "📋 Add Plan", "callback_data": f"/add_plan_{pid}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    send_message(user_id, f"✅ Product Added!\n\n📦 {name}\n🔑 PID: {api_pid}\n📱 Android: {'Required' if needs_android else 'Not Required'}\n\nAdd plans:", "HTML", markup)
    pending_commands.pop(user_id, None)
    pending_commands_col.delete_one({"user_id": str(user_id)})
    return True

@command("/add_plan")
def cmd_add_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    cmd = message.get("text", "")
    if "/add_plan_" in cmd:
        product_id = cmd.replace("/add_plan_", "")
    else:
        product_id = params
    
    if not product_id:
        send_message(user_id, "Product ID missing")
        return True
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Product not found")
        return True
    
    set_user_data(user_id, "add_plan_prod", product_id)
    
    text = f"📋 <b>ADD PLAN to {product.get('name')}</b>\n━━━━━━━━━━━━━━━━━━\n\nFormat: <code>id|duration|price|reseller</code>\nExample: <code>1|1 Day|10|8</code>\n\nType /cancel"
    send_message(user_id, text, "HTML")
    pending_commands[user_id] = "/add_plan_process"
    pending_commands_col.update_one({"user_id": str(user_id)}, {"$set": {"command": "/add_plan_process"}}, upsert=True)
    return True

@command("/add_plan_process")
def cmd_add_plan_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        set_user_data(user_id, "add_plan_prod", None)
        return True
    
    product_id = get_user_data(user_id, "add_plan_prod")
    if not product_id:
        send_message(user_id, "Product not found", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    parts = text.split('|')
    if len(parts) < 4:
        send_message(user_id, "❌ Invalid! Use: id|duration|price|reseller", "HTML")
        return True
    
    plan_id = parts[0].strip()
    duration = parts[1].strip()
    try:
        price = float(parts[2].strip())
        reseller = float(parts[3].strip())
    except:
        send_message(user_id, "❌ Numbers only!", "HTML")
        return True
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Product not found", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        set_user_data(user_id, "add_plan_prod", None)
        return True
    
    for plan in product.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            send_message(user_id, f"❌ Plan '{plan_id}' exists!", "HTML")
            return True
    
    add_plan(product_id, plan_id, duration, price, reseller)
    
    markup = {
        "inline_keyboard": [
            [{"text": "➕ Add Another", "callback_data": f"/add_plan_{product_id}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    send_message(user_id, f"✅ Plan Added!\n\n📦 {product.get('name')}\n📋 {duration}\n💰 ₹{price}\n💰 Reseller: ₹{reseller}", "HTML", markup)
    pending_commands.pop(user_id, None)
    pending_commands_col.delete_one({"user_id": str(user_id)})
    set_user_data(user_id, "add_plan_prod", None)
    return True

@command("/edit_prod")
def cmd_edit_prod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    products = get_products()
    if not products:
        send_message(user_id, "No products.", "HTML")
        return True
    
    keyboard = []
    for p in products:
        pid = p.get('product_id')
        keyboard.append([{"text": f"✏️ {p.get('name')}", "callback_data": f"/edit_{pid}"}])
    keyboard.append([{"text": "🔙 Back", "callback_data": "/admin_products"}])
    
    try:
        edit_message(user_id, msg_id, "Select product to edit:", "HTML", {"inline_keyboard": keyboard})
    except:
        send_message(user_id, "Select product to edit:", "HTML", {"inline_keyboard": keyboard})
    return True

@command("/edit_abcd")
@command("/edit_bala_v2")
@command("/edit_drip")
@command("/edit_silent")
@command("/edit_prime")
def cmd_edit_select(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    cmd = message.get("text", "")
    product_id = cmd.replace("/edit_", "")
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Not found")
        return True
    
    text = f"✏️ <b>{product.get('name')}</b>\n━━━━━━━━━━━━━━━━━━\n\n📦 ID: {product_id}\n🔑 PID: {product.get('pid')}\n📱 Android: {'Required' if product.get('needs_android', True) else 'Not Required'}\n\n📋 Plans:"
    for plan in product.get('plans', []):
        text += f"\n• {plan.get('duration')} - ₹{plan.get('price')} (Reseller: ₹{plan.get('reseller_price')}) [ID: {plan.get('plan_id')}]"
    
    markup = {
        "inline_keyboard": [
            [{"text": "🔑 Change PID", "callback_data": f"/chg_pid_{product_id}"}],
            [{"text": "📋 Edit Plan", "callback_data": f"/ed_plan_{product_id}"}],
            [{"text": "🗑️ Remove Plan", "callback_data": f"/rm_plan_{product_id}"}],
            [{"text": "📱 Toggle Android", "callback_data": f"/tog_android_{product_id}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

@command("/chg_pid")
def cmd_chg_pid(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    cmd = message.get("text", "")
    if "/chg_pid_" in cmd:
        product_id = cmd.replace("/chg_pid_", "")
    else:
        product_id = params
    
    if not product_id:
        send_message(user_id, "Product ID missing")
        return True
    
    set_user_data(user_id, "chg_pid_prod", product_id)
    send_message(user_id, f"🔑 Send new PID for {product_id}\n\nType /cancel", "HTML")
    pending_commands[user_id] = "/chg_pid_process"
    pending_commands_col.update_one({"user_id": str(user_id)}, {"$set": {"command": "/chg_pid_process"}}, upsert=True)
    return True

@command("/chg_pid_process")
def cmd_chg_pid_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        set_user_data(user_id, "chg_pid_prod", None)
        return True
    
    product_id = get_user_data(user_id, "chg_pid_prod")
    if not product_id:
        send_message(user_id, "No product", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Not found", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        set_user_data(user_id, "chg_pid_prod", None)
        return True
    
    update_pid(product_id, text)
    
    markup = {
        "inline_keyboard": [
            [{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}]
        ]
    }
    
    send_message(user_id, f"✅ PID Updated!\n\n📦 {product.get('name')}\n🔑 New PID: {text}", "HTML", markup)
    pending_commands.pop(user_id, None)
    pending_commands_col.delete_one({"user_id": str(user_id)})
    set_user_data(user_id, "chg_pid_prod", None)
    return True

@command("/ed_plan")
def cmd_ed_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    cmd = message.get("text", "")
    if "/ed_plan_" in cmd:
        product_id = cmd.replace("/ed_plan_", "")
    else:
        product_id = params
    
    if not product_id:
        send_message(user_id, "Product ID missing")
        return True
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Not found")
        return True
    
    if not product.get('plans'):
        send_message(user_id, "No plans", "HTML")
        return True
    
    keyboard = []
    for plan in product.get('plans', []):
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        keyboard.append([{"text": f"{duration} [ID: {plan_id}]", "callback_data": f"/ed_plan_sel_{product_id}_{plan_id}"}])
    keyboard.append([{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}])
    
    try:
        edit_message(user_id, msg_id, f"Select plan to edit:", "HTML", {"inline_keyboard": keyboard})
    except:
        send_message(user_id, f"Select plan to edit:", "HTML", {"inline_keyboard": keyboard})
    return True

@command("/ed_plan_sel")
def cmd_ed_plan_sel(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    
    cmd = message.get("text", "")
    parts = cmd.split("_")
    if len(parts) >= 4:
        product_id = parts[3]
        plan_id = parts[4]
    else:
        send_message(user_id, "Invalid")
        return True
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Not found")
        return True
    
    selected = None
    for plan in product.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected = plan
            break
    
    if not selected:
        send_message(user_id, "Plan not found")
        return True
    
    set_user_data(user_id, "ed_plan_data", {"product_id": product_id, "plan_id": plan_id})
    
    text = f"✏️ <b>EDIT PLAN</b>\n━━━━━━━━━━━━━━━━━━\n📦 {product.get('name')}\n📋 {selected.get('duration')}\n💰 Price: ₹{selected.get('price')}\n💰 Reseller: ₹{selected.get('reseller_price')}\n\nSend: <code>price|reseller</code>\nExample: <code>150|130</code>\n\nType /cancel"
    send_message(user_id, text, "HTML")
    pending_commands[user_id] = "/ed_plan_process"
    pending_commands_col.update_one({"user_id": str(user_id)}, {"$set": {"command": "/ed_plan_process"}}, upsert=True)
    return True

@command("/ed_plan_process")
def cmd_ed_plan_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        set_user_data(user_id, "ed_plan_data", None)
        return True
    
    ed_data = get_user_data(user_id, "ed_plan_data")
    if not ed_data:
        send_message(user_id, "No plan", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    parts = text.split('|')
    if len(parts) < 2:
        send_message(user_id, "❌ Use: price|reseller", "HTML")
        return True
    
    try:
        price = float(parts[0].strip())
        reseller = float(parts[1].strip())
    except:
        send_message(user_id, "❌ Numbers only!", "HTML")
        return True
    
    product_id = ed_data.get("product_id")
    plan_id = ed_data.get("plan_id")
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Not found", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        set_user_data(user_id, "ed_plan_data", None)
        return True
    
    update_plan(product_id, plan_id, price, reseller)
    
    markup = {
        "inline_keyboard": [
            [{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}]
        ]
    }
    
    send_message(user_id, f"✅ Plan Updated!\n\n📦 {product.get('name')}\n💰 ₹{price}\n💰 Reseller: ₹{reseller}", "HTML", markup)
    pending_commands.pop(user_id, None)
    pending_commands_col.delete_one({"user_id": str(user_id)})
    set_user_data(user_id, "ed_plan_data", None)
    return True

@command("/rm_plan")
def cmd_rm_plan(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    cmd = message.get("text", "")
    if "/rm_plan_" in cmd:
        product_id = cmd.replace("/rm_plan_", "")
    else:
        product_id = params
    
    if not product_id:
        send_message(user_id, "Product ID missing")
        return True
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Not found")
        return True
    
    if not product.get('plans'):
        send_message(user_id, "No plans", "HTML")
        return True
    
    keyboard = []
    for plan in product.get('plans', []):
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        keyboard.append([{"text": f"❌ {duration}", "callback_data": f"/rm_plan_confirm_{product_id}_{plan_id}"}])
    keyboard.append([{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}])
    
    try:
        edit_message(user_id, msg_id, f"Select plan to remove:", "HTML", {"inline_keyboard": keyboard})
    except:
        send_message(user_id, f"Select plan to remove:", "HTML", {"inline_keyboard": keyboard})
    return True

@command("/rm_plan_confirm")
def cmd_rm_plan_confirm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    
    cmd = message.get("text", "")
    parts = cmd.split("_")
    if len(parts) >= 4:
        product_id = parts[3]
        plan_id = parts[4]
    else:
        send_message(user_id, "Invalid")
        return True
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Not found")
        return True
    
    selected = None
    for plan in product.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected = plan
            break
    
    if not selected:
        send_message(user_id, "Plan not found")
        return True
    
    remove_plan(product_id, plan_id)
    
    markup = {
        "inline_keyboard": [
            [{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}]
        ]
    }
    
    send_message(user_id, f"✅ Plan Removed!\n\n📦 {product.get('name')}\n📋 {selected.get('duration')}", "HTML", markup)
    return True

@command("/tog_android")
def cmd_tog_android(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    cmd = message.get("text", "")
    if "/tog_android_" in cmd:
        product_id = cmd.replace("/tog_android_", "")
    else:
        product_id = params
    
    if not product_id:
        send_message(user_id, "Product ID missing")
        return True
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Not found")
        return True
    
    current = product.get('needs_android', True)
    new_val = not current
    products_col.update_one({"product_id": product_id}, {"$set": {"needs_android": new_val}})
    
    markup = {
        "inline_keyboard": [
            [{"text": "🔙 Back", "callback_data": f"/edit_{product_id}"}]
        ]
    }
    
    send_message(user_id, f"✅ Android: {'Required' if new_val else 'Not Required'}", "HTML", markup)
    return True

@command("/del_prod")
def cmd_del_prod(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    products = get_products()
    if not products:
        send_message(user_id, "No products.", "HTML")
        return True
    
    keyboard = []
    for p in products:
        pid = p.get('product_id')
        keyboard.append([{"text": f"🗑️ {p.get('name')}", "callback_data": f"/del_confirm_{pid}"}])
    keyboard.append([{"text": "🔙 Back", "callback_data": "/admin_products"}])
    
    try:
        edit_message(user_id, msg_id, "Select product to delete:", "HTML", {"inline_keyboard": keyboard})
    except:
        send_message(user_id, "Select product to delete:", "HTML", {"inline_keyboard": keyboard})
    return True

@command("/del_confirm")
def cmd_del_confirm(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    
    cmd = message.get("text", "")
    if "/del_confirm_" in cmd:
        product_id = cmd.replace("/del_confirm_", "")
    else:
        product_id = params
    
    if not product_id:
        return True
    
    product = get_product(product_id)
    if not product:
        send_message(user_id, "Not found")
        return True
    
    markup = {
        "inline_keyboard": [
            [{"text": "✅ Yes", "callback_data": f"/del_yes_{product_id}"}],
            [{"text": "❌ No", "callback_data": "/admin_products"}]
        ]
    }
    
    try:
        edit_message(user_id, msg_id, f"⚠️ Delete {product.get('name')}?", "HTML", markup)
    except:
        send_message(user_id, f"⚠️ Delete {product.get('name')}?", "HTML", markup)
    return True

@command("/del_yes")
def cmd_del_yes(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    
    cmd = message.get("text", "")
    if "/del_yes_" in cmd:
        product_id = cmd.replace("/del_yes_", "")
    else:
        product_id = params
    
    if not product_id:
        return True
    
    product = get_product(product_id)
    if product:
        delete_product(product_id)
        send_message(user_id, f"✅ Deleted {product.get('name')}", "HTML")
    else:
        send_message(user_id, "Not found", "HTML")
    return True

# ========== RESELLERS ==========

@command("/admin_resellers")
def cmd_admin_resellers(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    markup = {
        "inline_keyboard": [
            [{"text": "➕ Add Reseller", "callback_data": "/add_res"}],
            [{"text": "📝 List", "callback_data": "/list_res"}],
            [{"text": "🔙 Back", "callback_data": "/admin"}]
        ]
    }
    try:
        edit_message(user_id, msg_id, "💰 <b>RESELLERS</b>", "HTML", markup)
    except:
        send_message(user_id, "💰 <b>RESELLERS</b>", "HTML", markup)
    return True

@command("/add_res")
def cmd_add_res(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    send_message(user_id, "📩 Send user ID\n\nType /cancel", "HTML")
    pending_commands[user_id] = "/add_res_process"
    pending_commands_col.update_one({"user_id": str(user_id)}, {"$set": {"command": "/add_res_process"}}, upsert=True)
    return True

@command("/add_res_process")
def cmd_add_res_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    try:
        target = str(int(text))
    except:
        send_message(user_id, "❌ Invalid ID!", "HTML")
        return True
    
    resellers = get_data("resellers_list") or []
    if target in [str(u) for u in resellers]:
        send_message(user_id, "Already reseller", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    resellers.append(target)
    set_data("resellers_list", resellers)
    send_message(user_id, f"✅ Added <code>{target}</code>", "HTML")
    try:
        send_message(target, "🎉 You are now a Reseller!", "HTML")
    except:
        pass
    pending_commands.pop(user_id, None)
    pending_commands_col.delete_one({"user_id": str(user_id)})
    return True

@command("/list_res")
def cmd_list_res(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    resellers = get_data("resellers_list") or []
    if not resellers:
        text = "No resellers."
    else:
        text = "💰 <b>RESELLERS</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for i, r in enumerate(resellers, 1):
            text += f"{i}. <code>{r}</code>\n"
    
    markup = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "/admin_resellers"}]]}
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

# ========== ADMINS ==========

@command("/admin_admins")
def cmd_admin_admins(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    msg_id = message.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    markup = {"inline_keyboard": []}
    for a in admins:
        markup["inline_keyboard"].append([
            {"text": a, "callback_data": f"/rm_admin_{a}"},
            {"text": "❌", "callback_data": f"/rm_admin_{a}"}
        ])
    markup["inline_keyboard"].append([{"text": "➕ Add", "callback_data": "/add_admin"}])
    markup["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "/admin"}])
    
    text = "👑 <b>ADMINS</b>\n━━━━━━━━━━━━━━━━━━"
    try:
        edit_message(user_id, msg_id, text, "HTML", markup)
    except:
        send_message(user_id, text, "HTML", markup)
    return True

@command("/add_admin")
def cmd_add_admin(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    send_message(user_id, "📩 Send user ID\n\nType /cancel", "HTML")
    pending_commands[user_id] = "/add_admin_process"
    pending_commands_col.update_one({"user_id": str(user_id)}, {"$set": {"command": "/add_admin_process"}}, upsert=True)
    return True

@command("/add_admin_process")
def cmd_add_admin_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "").strip()
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    if text.lower() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    try:
        target = str(int(text))
    except:
        send_message(user_id, "❌ Invalid ID!", "HTML")
        return True
    
    if target in admins:
        send_message(user_id, "Already admin", "HTML")
    else:
        admins.append(target)
        set_data("AllBotAdminss", admins)
        send_message(user_id, f"✅ Added <code>{target}</code>", "HTML")
    
    pending_commands.pop(user_id, None)
    pending_commands_col.delete_one({"user_id": str(user_id)})
    return True

@command("/rm_admin")
def cmd_rm_admin(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    cmd = message.get("text", "")
    if "/rm_admin_" in cmd:
        target = cmd.replace("/rm_admin_", "")
    else:
        target = params
    
    if target and target in admins:
        admins.remove(target)
        set_data("AllBotAdminss", admins)
        send_message(user_id, f"✅ Removed <code>{target}</code>", "HTML")
    
    cmd_admin_admins(message, params, options)
    return True

# ========== BROADCAST ==========

@command("/admin_broadcast")
def cmd_admin_broadcast(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    users = user_data_col.distinct("user_id")
    send_message(
        user_id,
        f"📢 <b>BROADCAST</b>\n━━━━━━━━━━━━━━━━━━\n👥 Users: {len(users)}\n\nSend message\nType /cancel",
        "HTML"
    )
    pending_commands[user_id] = "/admin_broadcast_send"
    pending_commands_col.update_one({"user_id": str(user_id)}, {"$set": {"command": "/admin_broadcast_send"}}, upsert=True)
    return True

@command("/admin_broadcast_send")
def cmd_admin_broadcast_send(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    if message.get("text") and message.get("text", "").strip() == "/cancel":
        send_message(user_id, "❌ Cancelled", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    users = user_data_col.distinct("user_id")
    if not users:
        send_message(user_id, "No users!", "HTML")
        pending_commands.pop(user_id, None)
        pending_commands_col.delete_one({"user_id": str(user_id)})
        return True
    
    from_chat_id = message.get("chat", {}).get("id")
    msg_id_to_forward = message.get("message_id")
    
    success = 0
    for target in users:
        try:
            forward_message(target, from_chat_id, msg_id_to_forward)
            success += 1
        except:
            try:
                if message.get("text"):
                    send_message(target, message.get("text", ""), "HTML")
                    success += 1
            except:
                pass
        time.sleep(0.1)
    
    send_message(user_id, f"✅ Broadcast done!\n📤 Sent: {success}/{len(users)}", "HTML")
    pending_commands.pop(user_id, None)
    pending_commands_col.delete_one({"user_id": str(user_id)})
    return True

# ========== ADD BALANCE ==========

@command("/admin_balance")
def cmd_admin_balance(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    send_message(
        user_id,
        "💡 Send: <code>user_id amount</code>\nExample: <code>123456 100</code>\nUse - for deduct: <code>123456 -50</code>",
        "HTML"
    )
    pending_commands[user_id] = "/admin_balance_process"
    pending_commands_col.update_one({"user_id": str(user_id)}, {"$set": {"command": "/admin_balance_process"}}, upsert=True)
    return True

@command("/admin_balance_process")
def cmd_admin_balance_process(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    admins = get_data("AllBotAdminss") or []
    if str(user_id) not in admins:
        return True
    
    parts = text.split(" ")
    if len(parts) < 2:
        send_message(user_id, "Invalid! Use: user_id amount", "HTML")
        return True
    
    target = parts[0]
    try:
        amount = float(parts[1])
    except:
        send_message(user_id, "Invalid amount!", "HTML")
        return True
    
    bal = Resources.another_res("Balance", user=target)
    bal.add(amount)
    
    send_message(user_id, f"✅ Added ₹{amount} to <code>{target}</code>\n💰 New Balance: ₹{bal.value()}", "HTML")
    try:
        send_message(target, f"💰 Admin added ₹{amount} to your balance!", "HTML")
    except:
        pass
    
    pending_commands.pop(user_id, None)
    pending_commands_col.delete_one({"user_id": str(user_id)})
    return True

@command("/setMyCommands")
def cmd_set_commands(message, params, options=None):
    user_id = message.get("from", {}).get("id")
    cmds = [{"command": "start", "description": "START"}]
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands", json={"commands": cmds})
        send_message(user_id, "✅ Done!", "HTML")
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
