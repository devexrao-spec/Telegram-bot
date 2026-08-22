import requests
import json
import time
from datetime import datetime
from pymongo import MongoClient

BOT_TOKEN = "8565204943:AAEw7F-5NIwZjluyWT-PQYk70xHY3j01xAo"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# MongoDB
MONGO_URI = "mongodb+srv://crasher3210_db_user:devex5656@cluster0.9y5axka.mongodb.net/?appName=Cluster0&compressors=zlib"
client = MongoClient(MONGO_URI)
db = client["telegram_bot1"]

# Collections
bot_data = db['bot_data']
user_data = db['user_data']
pending_cmd = db['pending_commands']
pending_pay = db['pending_payments']
payment_orders = db['payment_orders']
products = db['products']

# ========== HELPER FUNCTIONS ==========
def get_data(key, default=None):
    d = bot_data.find_one({"key": key})
    return d.get("value") if d else default

def set_data(key, value):
    bot_data.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

def get_user(user_id, key, default=None):
    d = user_data.find_one({"user_id": str(user_id), "key": key})
    return d.get("value") if d else default

def set_user(user_id, key, value):
    user_data.update_one({"user_id": str(user_id), "key": key}, {"$set": {"value": value}}, upsert=True)

def get_products():
    return list(products.find())

def get_product(pid):
    return products.find_one({"product_id": pid})

def add_product(pid, name, api_pid, needs_android):
    products.update_one({"product_id": pid}, {"$set": {"product_id": pid, "name": name, "pid": api_pid, "needs_android": needs_android, "plans": []}}, upsert=True)

def add_plan(pid, plan_id, duration, price, reseller):
    products.update_one({"product_id": pid}, {"$push": {"plans": {"plan_id": plan_id, "duration": duration, "price": price, "reseller_price": reseller}}})

def del_product(pid):
    products.delete_one({"product_id": pid})

def update_pid(pid, new_pid):
    products.update_one({"product_id": pid}, {"$set": {"pid": new_pid}})

def update_plan(pid, plan_id, price, reseller):
    products.update_one({"product_id": pid, "plans.plan_id": plan_id}, {"$set": {"plans.$.price": price, "plans.$.reseller_price": reseller}})

def remove_plan(pid, plan_id):
    products.update_one({"product_id": pid}, {"$pull": {"plans": {"plan_id": plan_id}}})

def toggle_android(pid):
    p = get_product(pid)
    if p:
        new_val = not p.get('needs_android', True)
        products.update_one({"product_id": pid}, {"$set": {"needs_android": new_val}})
        return new_val
    return None

# ========== API ==========
API_URL = "https://xyzcheats.com/api/reseller_v1.php"
API_KEY = "b25eb076f5c0412fa9f1eba94550d02e"
API_HEADERS = {'Content-Type': 'application/x-www-form-urlencoded', 'x-master-key': 'a7f3e8b2c9d1f4a6b8c2d5e9f1a3b6c8'}

def gen_key(pid, duration, android_id=None, price=None):
    data = {'api_key': API_KEY, 'action': 'buy', 'product_id': str(pid), 'duration': duration}
    if price:
        data['price'] = str(price)
        data['amount'] = str(price)
    if android_id:
        data['android_id'] = android_id
    try:
        r = requests.post(API_URL, data=data, headers=API_HEADERS, timeout=30)
        res = r.json()
        if res.get('status') == 'success' or res.get('success'):
            key = res.get('key') or res.get('data', {}).get('key') or res.get('license_key')
            if key:
                return True, key
        return False, res.get('msg', 'Unknown error')
    except Exception as e:
        return False, str(e)

# ========== TELEGRAM ==========
def send_msg(chat_id, text, parse_mode="HTML", reply_markup=None):
    p = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        p["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(f"{BASE_URL}/sendMessage", json=p).json()
    except:
        return None

def send_photo(chat_id, photo, caption=None, parse_mode="HTML", reply_markup=None):
    p = {"chat_id": chat_id, "photo": photo, "parse_mode": parse_mode}
    if caption:
        p["caption"] = caption
    if reply_markup:
        p["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(f"{BASE_URL}/sendPhoto", json=p).json()
    except:
        return None

def edit_msg(chat_id, msg_id, text, parse_mode="HTML", reply_markup=None):
    p = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        p["reply_markup"] = json.dumps(reply_markup)
    try:
        return requests.post(f"{BASE_URL}/editMessageText", json=p).json()
    except:
        return None

def del_msg(chat_id, msg_id):
    try:
        return requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}).json()
    except:
        return None

def answer_cb(cb_id):
    try:
        return requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}).json()
    except:
        return None

def get_updates(offset=None):
    try:
        r = requests.get(f"{BASE_URL}/getUpdates", params={"offset": offset} if offset else {})
        return r.json().get("result", [])
    except:
        return []

def forward_msg(chat_id, from_chat_id, msg_id):
    try:
        return requests.post(f"{BASE_URL}/forwardMessage", json={"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": msg_id}).json()
    except:
        return None

def get_time():
    return datetime.now().strftime("%d %b, %I:%M %p")

# ========== RESOURCES ==========
class Resources:
    @staticmethod
    def res(res_type, user=None):
        class R:
            def __init__(self, t, uid):
                self.t = t
                self.uid = uid
                self.k = f"{t}_{uid}"
            def value(self):
                return get_data(self.k, 0)
            def add(self, amt):
                set_data(self.k, self.value() + amt)
                return self
            def cut(self, amt):
                set_data(self.k, max(0, self.value() - amt))
                return self
        return R(res_type, user)

# ========== COMMANDS ==========
commands = {}
pending = {}
pending_payments = {}
current_amount = {}

def command(name):
    def deco(func):
        commands[name] = func
        return func
    return deco

# ========== PURCHASE ==========
def process_purchase(msg, pid, plan_id, price, pname, duration, api_pid, android_id=None):
    uid = msg.get("from", {}).get("id")
    bal = Resources.res("Balance", uid)
    
    if bal.value() < price:
        set_user(uid, "last_deposit_amount", price)
        set_user(uid, "last_product", pname)
        cmd_autobuy1(msg, None)
        return True
    
    bal.cut(price)
    Resources.res("Order", uid).add(1)
    
    success, result = gen_key(api_pid, duration, android_id, price)
    
    if success:
        send_msg(uid, f"🛒 {pname}\n\n🔑 <b>Your Key:</b>\n<code>{result}</code>\n\n💰 Deducted: ₹{price}\n⏳ Duration: {duration}\n📦 Time: {get_time()}", "HTML")
        hist = get_user(uid, "userhAC") or []
        hist.append(f"📆 {get_time()}\n👤 {msg.get('from', {}).get('first_name', 'User')} [{uid}]\n💰 ₹{price}\n🔑 {result}")
        set_user(uid, "userhAC", hist)
        return True
    else:
        bal.add(price)
        send_msg(uid, f"❌ Key Failed\n\nError: {result}\n\n₹{price} refunded.", "HTML")
        return True

# ========== DEFAULT PRODUCTS ==========
def setup_products():
    prods = {
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
    for pid, data in prods.items():
        if not get_product(pid):
            add_product(pid, data["name"], data["pid"], data["needs_android"])
            for plan in data["plans"]:
                add_plan(pid, plan["plan_id"], plan["duration"], plan["price"], plan["reseller_price"])
            print(f"✅ Added: {data['name']}")

# ========== USER COMMANDS ==========

@command("/start")
def cmd_start(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    if not get_user(uid, "joined_date"):
        set_user(uid, "joined_date", msg.get("date"))
    bal = Resources.res("Balance", uid).value()
    text = f"🌟 <b>WELCOME TO HACK STORE</b> 🌙\n\n✨ Premium mods, cheats & clients!\n\n🚀 Instant Key Delivery\n💳 Secure Payment\n🛡 Anti-Ban Support\n\n💰 Balance: ₹{bal}"
    kb = {
        "inline_keyboard": [
            [{"text": "🛒 BUY HACK", "callback_data": "/shop"}],
            [{"text": "🔑 MY KEY", "callback_data": "/keys"}, {"text": "👤 PROFILE", "callback_data": "/profile"}],
            [{"text": "📖 HOW TO USE", "callback_data": "/tutorial"}, {"text": "💬 SUPPORT", "callback_data": "/support"}],
            [{"text": "💰 ADD FUND", "callback_data": "/addfund"}],
            [{"text": "📥 DOWNLOAD", "url": "https://t.me/+hasTLSVjzaZjZGVl"}]
        ]
    }
    send_msg(uid, text, "HTML", kb)
    return True

@command("/shop")
def cmd_shop(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    prods = get_products()
    if not prods:
        text = "⚠️ No products."
        kb = {"inline_keyboard": [[{"text": "🔙 BACK", "callback_data": "/back"}]]}
        try:
            edit_msg(uid, mid, text, "HTML", kb)
        except:
            send_msg(uid, text, "HTML", kb)
        return True
    
    text = "🛒 <b>SHOP</b>\n━━━━━━━━━━━━━━━━━━\n\n📦 Choose:"
    kb = {"inline_keyboard": []}
    for p in prods:
        kb["inline_keyboard"].append([{"text": f"📦 {p.get('name')}", "callback_data": f"/p_{p.get('product_id')}"}])
    kb["inline_keyboard"].append([{"text": "🔙 BACK", "callback_data": "/back"}])
    
    try:
        edit_msg(uid, mid, text, "HTML", kb)
    except:
        send_msg(uid, text, "HTML", kb)
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
        send_msg(uid, "Not found")
        return True
    
    resellers = get_data("resellers_list") or []
    is_reseller = str(uid) in [str(u) for u in resellers]
    
    text = f"📦 <b>{p.get('name')}</b>\n━━━━━━━━━━━━━━━━━━\n\nChoose plan 👇"
    kb = {"inline_keyboard": []}
    for plan in p.get('plans', []):
        price = plan.get('reseller_price') if is_reseller else plan.get('price')
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        kb["inline_keyboard"].append([{"text": f"{duration} - ₹{price}", "callback_data": f"/b_{pid}_{plan_id}"}])
    kb["inline_keyboard"].append([{"text": "🔙 BACK", "callback_data": "/shop"}])
    
    try:
        edit_msg(uid, mid, text, "HTML", kb)
    except:
        send_msg(uid, text, "HTML", kb)
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
    if len(parts) >= 3:
        pid = parts[1]
        plan_id = parts[2]
    else:
        send_msg(uid, "Invalid")
        return True
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found")
        return True
    
    selected = None
    for plan in p.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected = plan
            break
    
    if not selected:
        send_msg(uid, "Plan not found")
        return True
    
    resellers = get_data("resellers_list") or []
    is_reseller = str(uid) in [str(u) for u in resellers]
    
    price = selected.get('reseller_price') if is_reseller else selected.get('price')
    duration = selected.get('duration')
    pname = p.get('name')
    api_pid = p.get('pid')
    needs_android = p.get('needs_android', True)
    
    set_user(uid, "last_product", pname)
    set_user(uid, "last_plan", plan_id)
    set_user(uid, "last_product_key", pid)
    set_user(uid, "last_price", price)
    set_user(uid, "last_duration", duration)
    set_user(uid, "last_pid", api_pid)
    
    if needs_android:
        send_msg(uid, f"🔐 <b>Android ID Required</b>\n\nProduct: {pname}\nPlan: {duration}\nPrice: ₹{price}\n\nSend Android ID (16 hex chars)\nType /cancel", "HTML")
        pending[uid] = "/process_android"
        pending_cmd.update_one({"user_id": str(uid)}, {"$set": {"command": "/process_android"}}, upsert=True)
        return True
    else:
        return process_purchase(msg, pid, plan_id, price, pname, duration, api_pid)

@command("/process_android")
def cmd_process_android(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_msg(uid, "❌ Cancelled", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    if len(text) != 16 or not all(c in '0123456789abcdefABCDEF' for c in text):
        send_msg(uid, "❌ Invalid! 16 hex chars. Example: 0b9b969bc2e7997b", "HTML")
        return True
    
    pending.pop(uid, None)
    pending_cmd.delete_one({"user_id": str(uid)})
    
    pid = get_user(uid, "last_product_key")
    plan_id = get_user(uid, "last_plan")
    price = get_user(uid, "last_price")
    pname = get_user(uid, "last_product")
    duration = get_user(uid, "last_duration")
    api_pid = get_user(uid, "last_pid")
    
    return process_purchase(msg, pid, plan_id, price, pname, duration, api_pid, android_id=text)

@command("/autobuy1")
def cmd_autobuy1(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    amount = get_user(uid, "last_deposit_amount")
    pt = get_user(uid, "last_product") or "Unknown"
    if not amount:
        send_msg(uid, "Amount missing")
        return True
    bal = Resources.res("Balance", uid).value()
    
    upi = "bablu.xyztb@fam"
    url = f"https://fampay.anujbots.xyz/qr.php?upi={upi}&amount={amount}"
    try:
        r = requests.get(url)
        data = r.json()
    except:
        send_msg(uid, "API ERROR")
        return True
    if data.get("status") != "success":
        send_msg(uid, "QR FAILED")
        return True
    
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    payment_orders.update_one({"order_id": order_id}, {"$set": {"order_id": order_id, "user_id": str(uid), "amount": amount, "product_name": pt, "created_at": datetime.now(), "status": "pending"}}, upsert=True)
    set_user(uid, "last_order_id", order_id)
    pending_payments[uid] = {"order_id": order_id, "msg_id": msg.get("message_id"), "user_id": str(uid)}
    pending_pay.update_one({"user_id": str(uid)}, {"$set": {"data": pending_payments[uid]}}, upsert=True)
    
    caption = f"💰 <b>INSUFFICIENT BALANCE</b>\n\nProduct: {pt}\nPrice: ₹{amount}\nBalance: ₹{bal}\n\nScan QR:\n🧾 Order: <code>{order_id}</code>"
    kb = {"inline_keyboard": [[{"text": "✅ VERIFY", "callback_data": f"/v_{order_id}"}], [{"text": "❌ CANCEL", "callback_data": f"/c_{order_id}"}]]}
    send_photo(uid, qr_url, caption, "HTML", kb)
    return True

@command("/v")
def cmd_verify(msg, params, options=None):
    uid = str(msg.get("from", {}).get("id"))
    mid = msg.get("message_id")
    
    cmd = msg.get("text", "")
    if "/v_" in cmd:
        order_id = cmd.replace("/v_", "")
    else:
        order_id = params
    
    if not order_id:
        send_msg(uid, "No order ID", "HTML")
        return True
    
    order = payment_orders.find_one({"order_id": order_id})
    if not order:
        send_msg(uid, "❌ Invalid order", "HTML")
        return True
    
    if str(order.get("user_id")) != str(uid):
        send_msg(uid, "❌ Not your order!", "HTML")
        return True
    
    send_msg(uid, "⏳ Checking...", "HTML")
    
    url = f"https://fampay.anujbots.xyz/verify.php?order_id={order_id}&api_key=FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8"
    try:
        r = requests.get(url)
        data = r.json()
    except:
        send_msg(uid, "❌ API ERROR", "HTML")
        return True
    
    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        bal = Resources.res("Balance", uid)
        bal.add(amount)
        payment_orders.update_one({"order_id": order_id}, {"$set": {"status": "verified"}})
        set_user(uid, "last_order_id", "")
        pending_payments.pop(uid, None)
        pending_pay.delete_one({"user_id": str(uid)})
        if mid:
            try:
                del_msg(uid, mid)
            except:
                pass
        send_msg(uid, f"✅ Payment Success!\n\n💰 Added: ₹{amount}\n💳 New Balance: ₹{bal.value()}", "HTML")
        return True
    else:
        send_msg(uid, f"❌ Payment Not Found\n\nOrder: <code>{order_id}</code>", "HTML")
        return True

@command("/c")
def cmd_cancel(msg, params, options=None):
    uid = str(msg.get("from", {}).get("id"))
    mid = msg.get("message_id")
    
    cmd = msg.get("text", "")
    if "/c_" in cmd:
        order_id = cmd.replace("/c_", "")
    else:
        order_id = params
    
    if not order_id:
        p = pending_pay.find_one({"user_id": str(uid)})
        if p:
            order_id = p.get("data", {}).get("order_id")
    
    if order_id:
        payment_orders.delete_one({"order_id": order_id})
    
    if mid:
        try:
            del_msg(uid, mid)
        except:
            pass
    
    pending_payments.pop(uid, None)
    pending_pay.delete_one({"user_id": str(uid)})
    pending.pop(uid, None)
    pending_cmd.delete_one({"user_id": str(uid)})
    send_msg(uid, "❌ Cancelled", "HTML")
    return True

@command("/back")
def cmd_back(msg, params, options=None):
    return cmd_start(msg, params, options)

@command("/keys")
def cmd_keys(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    hist = get_user(uid, "userhAC") or []
    if not hist:
        text = "📦 <b>MY ORDERS</b>\n━━━━━━━━━━━━━━━━━━\n\nNo orders yet."
    else:
        text = "📦 <b>MY ORDERS</b>\n━━━━━━━━━━━━━━━━━━\n\n" + "\n\n".join(hist[-10:][::-1])
    kb = {"inline_keyboard": [[{"text": "🔙 BACK", "callback_data": "/back"}]]}
    try:
        edit_msg(uid, mid, text, "HTML", kb)
    except:
        send_msg(uid, text, "HTML", kb)
    return True

@command("/profile")
def cmd_profile(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    name = msg.get("from", {}).get("first_name", "User")
    bal = Resources.res("Balance", uid).value()
    orders = Resources.res("Order", uid).value()
    text = f"👤 <b>PROFILE</b>\n━━━━━━━━━━━━━━━━━━\n\n📛 Name: {name}\n🆔 ID: {uid}\n💰 Balance: ₹{bal}\n🛒 Orders: {orders}"
    kb = {"inline_keyboard": [[{"text": "🛒 BUY", "callback_data": "/shop"}, {"text": "🔑 KEYS", "callback_data": "/keys"}], [{"text": "🔙 BACK", "callback_data": "/back"}]]}
    send_msg(uid, text, "HTML", kb)
    return True

@command("/tutorial")
def cmd_tutorial(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = "🎥 <b>TUTORIAL</b>\n\nWatch: https://t.me/hehehehhhsljg/162"
    kb = {"inline_keyboard": [[{"text": "▶️ Watch", "url": "https://t.me/hehehehhhsljg/162"}], [{"text": "🔙 BACK", "callback_data": "/back"}]]}
    send_msg(uid, text, "HTML", kb)
    return True

@command("/support")
def cmd_support(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = "💬 <b>SUPPORT</b>\n\n<a href='https://t.me/UR_SUBHAJIT0'>Contact</a>"
    kb = {"inline_keyboard": [[{"text": "📱 WhatsApp", "url": "https://wa.me/917908696630"}], [{"text": "🔙 BACK", "callback_data": "/back"}]]}
    send_msg(uid, text, "HTML", kb)
    return True

# ========== ADD FUND ==========

@command("/addfund")
def cmd_addfund(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    current_amount[uid] = "0"
    kb = {
        "inline_keyboard": [
            [{"text": "1", "callback_data": "/n1"}, {"text": "2", "callback_data": "/n2"}, {"text": "3", "callback_data": "/n3"}],
            [{"text": "4", "callback_data": "/n4"}, {"text": "5", "callback_data": "/n5"}, {"text": "6", "callback_data": "/n6"}],
            [{"text": "7", "callback_data": "/n7"}, {"text": "8", "callback_data": "/n8"}, {"text": "9", "callback_data": "/n9"}],
            [{"text": "CLEAR", "callback_data": "/clr"}, {"text": "0", "callback_data": "/n0"}, {"text": "✅", "callback_data": "/done"}],
            [{"text": "🔙 BACK", "callback_data": "/back"}]
        ]
    }
    text = "💰 <b>ENTER AMOUNT</b>\n\n₹0"
    try:
        edit_msg(uid, mid, text, "HTML", kb)
    except:
        send_msg(uid, text, "HTML", kb)
    return True

@command("/n0")
def cmd_n0(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    if amt != "0":
        amt += "0"
    current_amount[uid] = amt
    edit_msg(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n1")
def cmd_n1(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "1" if amt == "0" else amt + "1"
    current_amount[uid] = amt
    edit_msg(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n2")
def cmd_n2(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "2" if amt == "0" else amt + "2"
    current_amount[uid] = amt
    edit_msg(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n3")
def cmd_n3(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "3" if amt == "0" else amt + "3"
    current_amount[uid] = amt
    edit_msg(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n4")
def cmd_n4(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "4" if amt == "0" else amt + "4"
    current_amount[uid] = amt
    edit_msg(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n5")
def cmd_n5(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "5" if amt == "0" else amt + "5"
    current_amount[uid] = amt
    edit_msg(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n6")
def cmd_n6(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "6" if amt == "0" else amt + "6"
    current_amount[uid] = amt
    edit_msg(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n7")
def cmd_n7(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "7" if amt == "0" else amt + "7"
    current_amount[uid] = amt
    edit_msg(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n8")
def cmd_n8(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "8" if amt == "0" else amt + "8"
    current_amount[uid] = amt
    edit_msg(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/n9")
def cmd_n9(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    amt = current_amount.get(uid, "0")
    amt = "9" if amt == "0" else amt + "9"
    current_amount[uid] = amt
    edit_msg(uid, mid, f"💰 <b>ENTER AMOUNT</b>\n\n₹{amt}", "HTML", msg.get("reply_markup"))
    return True

@command("/clr")
def cmd_clr(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    current_amount[uid] = "0"
    edit_msg(uid, mid, "💰 <b>ENTER AMOUNT</b>\n\n₹0", "HTML", msg.get("reply_markup"))
    return True

@command("/done")
def cmd_done(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    amt = current_amount.get(uid, "0")
    if not amt or amt == "0":
        send_msg(uid, "Enter amount!", "HTML")
        return True
    set_user(uid, "last_deposit_amount", float(amt))
    
    upi = "bablu.xyztb@fam"
    url = f"https://fampay.anujbots.xyz/qr.php?upi={upi}&amount={amt}"
    try:
        r = requests.get(url)
        data = r.json()
    except:
        send_msg(uid, "API ERROR")
        return True
    if data.get("status") != "success":
        send_msg(uid, "QR FAILED")
        return True
    
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    payment_orders.update_one({"order_id": order_id}, {"$set": {"order_id": order_id, "user_id": str(uid), "amount": float(amt), "product_name": "Add Funds", "created_at": datetime.now(), "status": "pending"}}, upsert=True)
    pending_payments[uid] = {"order_id": order_id, "msg_id": msg.get("message_id"), "user_id": str(uid)}
    pending_pay.update_one({"user_id": str(uid)}, {"$set": {"data": pending_payments[uid]}}, upsert=True)
    
    caption = f"💰 <b>PAYMENT QR</b>\n\nAmount: ₹{amt}\n\n🧾 Order: <code>{order_id}</code>"
    kb = {"inline_keyboard": [[{"text": "✅ VERIFY", "callback_data": f"/v_{order_id}"}], [{"text": "❌ CANCEL", "callback_data": f"/c_{order_id}"}]]}
    send_photo(uid, qr_url, caption, "HTML", kb)
    return True

# ========== ADMIN COMMANDS ==========

@command("/admin")
def cmd_admin(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    admins = get_data("AllBotAdminss") or []
    if not admins:
        admins = [str(uid)]
        set_data("AllBotAdminss", admins)
    
    if str(uid) not in admins:
        send_msg(uid, "🚫 Not Admin", "HTML")
        return True
    
    kb = {
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
        edit_msg(uid, mid, text, "HTML", kb)
    except:
        send_msg(uid, text, "HTML", kb)
    return True

@command("/admin_products")
def cmd_admin_products(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    prods = get_products()
    text = "📦 <b>PRODUCTS</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    if not prods:
        text += "No products."
    else:
        for i, p in enumerate(prods, 1):
            text += f"{i}. {p.get('name')}\n   PID: {p.get('pid')}\n   Android: {'✅' if p.get('needs_android', True) else '❌'}\n"
            for plan in p.get('plans', []):
                text += f"   • {plan.get('duration')} - ₹{plan.get('price')}\n"
            text += "\n"
    
    kb = {
        "inline_keyboard": [
            [{"text": "➕ Add", "callback_data": "/add_prod"}],
            [{"text": "✏️ Edit", "callback_data": "/edit_prod"}],
            [{"text": "🗑️ Delete", "callback_data": "/del_prod"}],
            [{"text": "🔙 Back", "callback_data": "/admin"}]
        ]
    }
    
    try:
        edit_msg(uid, mid, text, "HTML", kb)
    except:
        send_msg(uid, text, "HTML", kb)
    return True

@command("/add_prod")
def cmd_add_prod(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    text = "➕ <b>ADD PRODUCT</b>\n━━━━━━━━━━━━━━━━━━\n\nFormat: <code>id|name|pid|android</code>\nExample: <code>my_mod|MY MOD|143|false</code>\n\nandroid: true/false\n\nType /cancel"
    send_msg(uid, text, "HTML")
    pending[uid] = "/add_prod_process"
    pending_cmd.update_one({"user_id": str(uid)}, {"$set": {"command": "/add_prod_process"}}, upsert=True)
    return True

@command("/add_prod_process")
def cmd_add_prod_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "")
    
    if text.lower() == "/cancel":
        send_msg(uid, "❌ Cancelled", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    parts = text.split('|')
    if len(parts) < 3:
        send_msg(uid, "❌ Invalid! Use: id|name|pid|android", "HTML")
        return True
    
    pid = parts[0].strip()
    name = parts[1].strip()
    api_pid = parts[2].strip()
    needs_android = parts[3].strip().lower() == 'true' if len(parts) > 3 else True
    
    if get_product(pid):
        send_msg(uid, f"❌ '{pid}' exists!", "HTML")
        return True
    
    add_product(pid, name, api_pid, needs_android)
    
    kb = {
        "inline_keyboard": [
            [{"text": "📋 Add Plan", "callback_data": f"/add_plan_{pid}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    send_msg(uid, f"✅ Product Added!\n\n📦 {name}\n🔑 PID: {api_pid}\n📱 Android: {'Required' if needs_android else 'Not Required'}\n\nAdd plans:", "HTML", kb)
    pending.pop(uid, None)
    pending_cmd.delete_one({"user_id": str(uid)})
    return True

@command("/add_plan")
def cmd_add_plan(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    cmd = msg.get("text", "")
    if "/add_plan_" in cmd:
        pid = cmd.replace("/add_plan_", "")
    else:
        pid = params
    
    if not pid:
        send_msg(uid, "Product ID missing")
        return True
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found")
        return True
    
    set_user(uid, "add_plan_prod", pid)
    text = f"📋 <b>ADD PLAN to {p.get('name')}</b>\n━━━━━━━━━━━━━━━━━━\n\nFormat: <code>id|duration|price|reseller</code>\nExample: <code>1|1 Day|10|8</code>\n\nType /cancel"
    send_msg(uid, text, "HTML")
    pending[uid] = "/add_plan_process"
    pending_cmd.update_one({"user_id": str(uid)}, {"$set": {"command": "/add_plan_process"}}, upsert=True)
    return True

@command("/add_plan_process")
def cmd_add_plan_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "")
    
    if text.lower() == "/cancel":
        send_msg(uid, "❌ Cancelled", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        set_user(uid, "add_plan_prod", None)
        return True
    
    pid = get_user(uid, "add_plan_prod")
    if not pid:
        send_msg(uid, "Product not found", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    parts = text.split('|')
    if len(parts) < 4:
        send_msg(uid, "❌ Invalid! Use: id|duration|price|reseller", "HTML")
        return True
    
    plan_id = parts[0].strip()
    duration = parts[1].strip()
    try:
        price = float(parts[2].strip())
        reseller = float(parts[3].strip())
    except:
        send_msg(uid, "❌ Numbers only!", "HTML")
        return True
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        set_user(uid, "add_plan_prod", None)
        return True
    
    for plan in p.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            send_msg(uid, f"❌ Plan '{plan_id}' exists!", "HTML")
            return True
    
    add_plan(pid, plan_id, duration, price, reseller)
    
    kb = {
        "inline_keyboard": [
            [{"text": "➕ Add Another", "callback_data": f"/add_plan_{pid}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    send_msg(uid, f"✅ Plan Added!\n\n📦 {p.get('name')}\n📋 {duration}\n💰 ₹{price}\n💰 Reseller: ₹{reseller}", "HTML", kb)
    pending.pop(uid, None)
    pending_cmd.delete_one({"user_id": str(uid)})
    set_user(uid, "add_plan_prod", None)
    return True

@command("/edit_prod")
def cmd_edit_prod(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    prods = get_products()
    if not prods:
        send_msg(uid, "No products.", "HTML")
        return True
    
    kb = {"inline_keyboard": []}
    for p in prods:
        pid = p.get('product_id')
        kb["inline_keyboard"].append([{"text": f"✏️ {p.get('name')}", "callback_data": f"/edit_{pid}"}])
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "/admin_products"}])
    
    try:
        edit_msg(uid, mid, "Select product to edit:", "HTML", kb)
    except:
        send_msg(uid, "Select product to edit:", "HTML", kb)
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
    pid = cmd.replace("/edit_", "")
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found")
        return True
    
    text = f"✏️ <b>{p.get('name')}</b>\n━━━━━━━━━━━━━━━━━━\n\n📦 ID: {pid}\n🔑 PID: {p.get('pid')}\n📱 Android: {'Required' if p.get('needs_android', True) else 'Not Required'}\n\n📋 Plans:"
    for plan in p.get('plans', []):
        text += f"\n• {plan.get('duration')} - ₹{plan.get('price')} (Reseller: ₹{plan.get('reseller_price')}) [ID: {plan.get('plan_id')}]"
    
    kb = {
        "inline_keyboard": [
            [{"text": "🔑 Change PID", "callback_data": f"/chg_pid_{pid}"}],
            [{"text": "📋 Edit Plan", "callback_data": f"/ed_plan_{pid}"}],
            [{"text": "🗑️ Remove Plan", "callback_data": f"/rm_plan_{pid}"}],
            [{"text": "📱 Toggle Android", "callback_data": f"/tog_android_{pid}"}],
            [{"text": "🔙 Back", "callback_data": "/admin_products"}]
        ]
    }
    
    try:
        edit_msg(uid, mid, text, "HTML", kb)
    except:
        send_msg(uid, text, "HTML", kb)
    return True

@command("/chg_pid")
def cmd_chg_pid(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    cmd = msg.get("text", "")
    if "/chg_pid_" in cmd:
        pid = cmd.replace("/chg_pid_", "")
    else:
        pid = params
    
    if not pid:
        send_msg(uid, "Product ID missing")
        return True
    
    set_user(uid, "chg_pid_prod", pid)
    send_msg(uid, f"🔑 Send new PID for {pid}\n\nType /cancel", "HTML")
    pending[uid] = "/chg_pid_process"
    pending_cmd.update_one({"user_id": str(uid)}, {"$set": {"command": "/chg_pid_process"}}, upsert=True)
    return True

@command("/chg_pid_process")
def cmd_chg_pid_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_msg(uid, "❌ Cancelled", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        set_user(uid, "chg_pid_prod", None)
        return True
    
    pid = get_user(uid, "chg_pid_prod")
    if not pid:
        send_msg(uid, "No product", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        set_user(uid, "chg_pid_prod", None)
        return True
    
    update_pid(pid, text)
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"/edit_{pid}"}]]}
    send_msg(uid, f"✅ PID Updated!\n\n📦 {p.get('name')}\n🔑 New PID: {text}", "HTML", kb)
    pending.pop(uid, None)
    pending_cmd.delete_one({"user_id": str(uid)})
    set_user(uid, "chg_pid_prod", None)
    return True

@command("/ed_plan")
def cmd_ed_plan(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    cmd = msg.get("text", "")
    if "/ed_plan_" in cmd:
        pid = cmd.replace("/ed_plan_", "")
    else:
        pid = params
    
    if not pid:
        send_msg(uid, "Product ID missing")
        return True
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found")
        return True
    
    if not p.get('plans'):
        send_msg(uid, "No plans", "HTML")
        return True
    
    kb = {"inline_keyboard": []}
    for plan in p.get('plans', []):
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        kb["inline_keyboard"].append([{"text": f"{duration} [ID: {plan_id}]", "callback_data": f"/ed_plan_sel_{pid}_{plan_id}"}])
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": f"/edit_{pid}"}])
    
    try:
        edit_msg(uid, mid, "Select plan to edit:", "HTML", kb)
    except:
        send_msg(uid, "Select plan to edit:", "HTML", kb)
    return True

@command("/ed_plan_sel")
def cmd_ed_plan_sel(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    cmd = msg.get("text", "")
    parts = cmd.split("_")
    if len(parts) >= 4:
        pid = parts[3]
        plan_id = parts[4]
    else:
        send_msg(uid, "Invalid")
        return True
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found")
        return True
    
    selected = None
    for plan in p.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected = plan
            break
    
    if not selected:
        send_msg(uid, "Plan not found")
        return True
    
    set_user(uid, "ed_plan_data", {"product_id": pid, "plan_id": plan_id})
    text = f"✏️ <b>EDIT PLAN</b>\n━━━━━━━━━━━━━━━━━━\n📦 {p.get('name')}\n📋 {selected.get('duration')}\n💰 Price: ₹{selected.get('price')}\n💰 Reseller: ₹{selected.get('reseller_price')}\n\nSend: <code>price|reseller</code>\nExample: <code>150|130</code>\n\nType /cancel"
    send_msg(uid, text, "HTML")
    pending[uid] = "/ed_plan_process"
    pending_cmd.update_one({"user_id": str(uid)}, {"$set": {"command": "/ed_plan_process"}}, upsert=True)
    return True

@command("/ed_plan_process")
def cmd_ed_plan_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_msg(uid, "❌ Cancelled", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        set_user(uid, "ed_plan_data", None)
        return True
    
    ed_data = get_user(uid, "ed_plan_data")
    if not ed_data:
        send_msg(uid, "No plan", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    parts = text.split('|')
    if len(parts) < 2:
        send_msg(uid, "❌ Use: price|reseller", "HTML")
        return True
    
    try:
        price = float(parts[0].strip())
        reseller = float(parts[1].strip())
    except:
        send_msg(uid, "❌ Numbers only!", "HTML")
        return True
    
    pid = ed_data.get("product_id")
    plan_id = ed_data.get("plan_id")
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        set_user(uid, "ed_plan_data", None)
        return True
    
    update_plan(pid, plan_id, price, reseller)
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"/edit_{pid}"}]]}
    send_msg(uid, f"✅ Plan Updated!\n\n📦 {p.get('name')}\n💰 ₹{price}\n💰 Reseller: ₹{reseller}", "HTML", kb)
    pending.pop(uid, None)
    pending_cmd.delete_one({"user_id": str(uid)})
    set_user(uid, "ed_plan_data", None)
    return True

@command("/rm_plan")
def cmd_rm_plan(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    cmd = msg.get("text", "")
    if "/rm_plan_" in cmd:
        pid = cmd.replace("/rm_plan_", "")
    else:
        pid = params
    
    if not pid:
        send_msg(uid, "Product ID missing")
        return True
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found")
        return True
    
    if not p.get('plans'):
        send_msg(uid, "No plans", "HTML")
        return True
    
    kb = {"inline_keyboard": []}
    for plan in p.get('plans', []):
        plan_id = plan.get('plan_id')
        duration = plan.get('duration')
        kb["inline_keyboard"].append([{"text": f"❌ {duration}", "callback_data": f"/rm_plan_confirm_{pid}_{plan_id}"}])
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": f"/edit_{pid}"}])
    
    try:
        edit_msg(uid, mid, "Select plan to remove:", "HTML", kb)
    except:
        send_msg(uid, "Select plan to remove:", "HTML", kb)
    return True

@command("/rm_plan_confirm")
def cmd_rm_plan_confirm(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    cmd = msg.get("text", "")
    parts = cmd.split("_")
    if len(parts) >= 4:
        pid = parts[3]
        plan_id = parts[4]
    else:
        send_msg(uid, "Invalid")
        return True
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found")
        return True
    
    selected = None
    for plan in p.get('plans', []):
        if str(plan.get('plan_id')) == str(plan_id):
            selected = plan
            break
    
    if not selected:
        send_msg(uid, "Plan not found")
        return True
    
    remove_plan(pid, plan_id)
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"/edit_{pid}"}]]}
    send_msg(uid, f"✅ Plan Removed!\n\n📦 {p.get('name')}\n📋 {selected.get('duration')}", "HTML", kb)
    return True

@command("/tog_android")
def cmd_tog_android(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    cmd = msg.get("text", "")
    if "/tog_android_" in cmd:
        pid = cmd.replace("/tog_android_", "")
    else:
        pid = params
    
    if not pid:
        send_msg(uid, "Product ID missing")
        return True
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found")
        return True
    
    new_val = toggle_android(pid)
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"/edit_{pid}"}]]}
    send_msg(uid, f"✅ Android: {'Required' if new_val else 'Not Required'}", "HTML", kb)
    return True

@command("/del_prod")
def cmd_del_prod(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    prods = get_products()
    if not prods:
        send_msg(uid, "No products.", "HTML")
        return True
    
    kb = {"inline_keyboard": []}
    for p in prods:
        pid = p.get('product_id')
        kb["inline_keyboard"].append([{"text": f"🗑️ {p.get('name')}", "callback_data": f"/del_confirm_{pid}"}])
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "/admin_products"}])
    
    try:
        edit_msg(uid, mid, "Select product to delete:", "HTML", kb)
    except:
        send_msg(uid, "Select product to delete:", "HTML", kb)
    return True

@command("/del_confirm")
def cmd_del_confirm(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    
    cmd = msg.get("text", "")
    if "/del_confirm_" in cmd:
        pid = cmd.replace("/del_confirm_", "")
    else:
        pid = params
    
    if not pid:
        return True
    
    p = get_product(pid)
    if not p:
        send_msg(uid, "Not found")
        return True
    
    kb = {"inline_keyboard": [[{"text": "✅ Yes", "callback_data": f"/del_yes_{pid}"}], [{"text": "❌ No", "callback_data": "/admin_products"}]]}
    try:
        edit_msg(uid, mid, f"⚠️ Delete {p.get('name')}?", "HTML", kb)
    except:
        send_msg(uid, f"⚠️ Delete {p.get('name')}?", "HTML", kb)
    return True

@command("/del_yes")
def cmd_del_yes(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    
    cmd = msg.get("text", "")
    if "/del_yes_" in cmd:
        pid = cmd.replace("/del_yes_", "")
    else:
        pid = params
    
    if not pid:
        return True
    
    p = get_product(pid)
    if p:
        del_product(pid)
        send_msg(uid, f"✅ Deleted {p.get('name')}", "HTML")
    else:
        send_msg(uid, "Not found", "HTML")
    return True

# ========== RESELLERS ==========

@command("/admin_resellers")
def cmd_admin_resellers(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    kb = {
        "inline_keyboard": [
            [{"text": "➕ Add Reseller", "callback_data": "/add_res"}],
            [{"text": "📝 List", "callback_data": "/list_res"}],
            [{"text": "🔙 Back", "callback_data": "/admin"}]
        ]
    }
    try:
        edit_msg(uid, mid, "💰 <b>RESELLERS</b>", "HTML", kb)
    except:
        send_msg(uid, "💰 <b>RESELLERS</b>", "HTML", kb)
    return True

@command("/add_res")
def cmd_add_res(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    send_msg(uid, "📩 Send user ID\n\nType /cancel", "HTML")
    pending[uid] = "/add_res_process"
    pending_cmd.update_one({"user_id": str(uid)}, {"$set": {"command": "/add_res_process"}}, upsert=True)
    return True

@command("/add_res_process")
def cmd_add_res_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    
    if text.lower() == "/cancel":
        send_msg(uid, "❌ Cancelled", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    try:
        target = str(int(text))
    except:
        send_msg(uid, "❌ Invalid ID!", "HTML")
        return True
    
    resellers = get_data("resellers_list") or []
    if target in [str(u) for u in resellers]:
        send_msg(uid, "Already reseller", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    resellers.append(target)
    set_data("resellers_list", resellers)
    send_msg(uid, f"✅ Added <code>{target}</code>", "HTML")
    try:
        send_msg(target, "🎉 You are now a Reseller!", "HTML")
    except:
        pass
    pending.pop(uid, None)
    pending_cmd.delete_one({"user_id": str(uid)})
    return True

@command("/list_res")
def cmd_list_res(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    resellers = get_data("resellers_list") or []
    if not resellers:
        text = "No resellers."
    else:
        text = "💰 <b>RESELLERS</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for i, r in enumerate(resellers, 1):
            text += f"{i}. <code>{r}</code>\n"
    
    kb = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "/admin_resellers"}]]}
    try:
        edit_msg(uid, mid, text, "HTML", kb)
    except:
        send_msg(uid, text, "HTML", kb)
    return True

# ========== ADMINS ==========

@command("/admin_admins")
def cmd_admin_admins(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    mid = msg.get("message_id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    kb = {"inline_keyboard": []}
    for a in admins:
        kb["inline_keyboard"].append([{"text": a, "callback_data": f"/rm_admin_{a}"}, {"text": "❌", "callback_data": f"/rm_admin_{a}"}])
    kb["inline_keyboard"].append([{"text": "➕ Add", "callback_data": "/add_admin"}])
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "/admin"}])
    
    text = "👑 <b>ADMINS</b>\n━━━━━━━━━━━━━━━━━━"
    try:
        edit_msg(uid, mid, text, "HTML", kb)
    except:
        send_msg(uid, text, "HTML", kb)
    return True

@command("/add_admin")
def cmd_add_admin(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    send_msg(uid, "📩 Send user ID\n\nType /cancel", "HTML")
    pending[uid] = "/add_admin_process"
    pending_cmd.update_one({"user_id": str(uid)}, {"$set": {"command": "/add_admin_process"}}, upsert=True)
    return True

@command("/add_admin_process")
def cmd_add_admin_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "").strip()
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    if text.lower() == "/cancel":
        send_msg(uid, "❌ Cancelled", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    try:
        target = str(int(text))
    except:
        send_msg(uid, "❌ Invalid ID!", "HTML")
        return True
    
    if target in admins:
        send_msg(uid, "Already admin", "HTML")
    else:
        admins.append(target)
        set_data("AllBotAdminss", admins)
        send_msg(uid, f"✅ Added <code>{target}</code>", "HTML")
    
    pending.pop(uid, None)
    pending_cmd.delete_one({"user_id": str(uid)})
    return True

@command("/rm_admin")
def cmd_rm_admin(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    cmd = msg.get("text", "")
    if "/rm_admin_" in cmd:
        target = cmd.replace("/rm_admin_", "")
    else:
        target = params
    
    if target and target in admins:
        admins.remove(target)
        set_data("AllBotAdminss", admins)
        send_msg(uid, f"✅ Removed <code>{target}</code>", "HTML")
    
    cmd_admin_admins(msg, params, options)
    return True

# ========== BROADCAST ==========

@command("/admin_broadcast")
def cmd_admin_broadcast(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    users = user_data.distinct("user_id")
    send_msg(uid, f"📢 <b>BROADCAST</b>\n━━━━━━━━━━━━━━━━━━\n👥 Users: {len(users)}\n\nSend message\nType /cancel", "HTML")
    pending[uid] = "/admin_broadcast_send"
    pending_cmd.update_one({"user_id": str(uid)}, {"$set": {"command": "/admin_broadcast_send"}}, upsert=True)
    return True

@command("/admin_broadcast_send")
def cmd_admin_broadcast_send(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    if msg.get("text") and msg.get("text", "").strip() == "/cancel":
        send_msg(uid, "❌ Cancelled", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    users = user_data.distinct("user_id")
    if not users:
        send_msg(uid, "No users!", "HTML")
        pending.pop(uid, None)
        pending_cmd.delete_one({"user_id": str(uid)})
        return True
    
    from_chat_id = msg.get("chat", {}).get("id")
    msg_id_to_forward = msg.get("message_id")
    
    success = 0
    for target in users:
        try:
            forward_msg(target, from_chat_id, msg_id_to_forward)
            success += 1
        except:
            try:
                if msg.get("text"):
                    send_msg(target, msg.get("text", ""), "HTML")
                    success += 1
            except:
                pass
        time.sleep(0.1)
    
    send_msg(uid, f"✅ Broadcast done!\n📤 Sent: {success}/{len(users)}", "HTML")
    pending.pop(uid, None)
    pending_cmd.delete_one({"user_id": str(uid)})
    return True

# ========== ADD BALANCE ==========

@command("/admin_balance")
def cmd_admin_balance(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    send_msg(uid, "💡 Send: <code>user_id amount</code>\nExample: <code>123456 100</code>\nUse - for deduct: <code>123456 -50</code>", "HTML")
    pending[uid] = "/admin_balance_process"
    pending_cmd.update_one({"user_id": str(uid)}, {"$set": {"command": "/admin_balance_process"}}, upsert=True)
    return True

@command("/admin_balance_process")
def cmd_admin_balance_process(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    text = msg.get("text", "")
    admins = get_data("AllBotAdminss") or []
    if str(uid) not in admins:
        return True
    
    parts = text.split(" ")
    if len(parts) < 2:
        send_msg(uid, "Invalid! Use: user_id amount", "HTML")
        return True
    
    target = parts[0]
    try:
        amount = float(parts[1])
    except:
        send_msg(uid, "Invalid amount!", "HTML")
        return True
    
    bal = Resources.res("Balance", target)
    bal.add(amount)
    
    send_msg(uid, f"✅ Added ₹{amount} to <code>{target}</code>\n💰 New Balance: ₹{bal.value()}", "HTML")
    try:
        send_msg(target, f"💰 Admin added ₹{amount} to your balance!", "HTML")
    except:
        pass
    
    pending.pop(uid, None)
    pending_cmd.delete_one({"user_id": str(uid)})
    return True

@command("/setMyCommands")
def cmd_set_commands(msg, params, options=None):
    uid = msg.get("from", {}).get("id")
    cmds = [{"command": "start", "description": "START"}]
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands", json={"commands": cmds})
        send_msg(uid, "✅ Done!", "HTML")
    except:
        send_msg(uid, "Error!", "HTML")
    return True

def handle_update(update):
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        uid = cb.get("from", {}).get("id")
        mid = cb.get("message", {}).get("message_id")
        answer_cb(cb.get("id"))
        
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
        
        if uid in pending:
            pending_cmd = pending[uid]
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
    print(f"📡 API: {API_URL}")
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
