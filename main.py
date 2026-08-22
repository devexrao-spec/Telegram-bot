import json
import os
import time
import random
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== CONFIG ==========
BOT_TOKEN = "8565204943:AAEw7F-5NIwZjluyWT-PQYk70xHY3j01xAo"
ADMIN_ID = "8102646437"

# API Configuration
API_URL = "https://xyzcheats.com/api/reseller_v1.php"
MASTER_KEY = "a7f3e8b2c9d1f4a6b8c2d5e9f1a3b6c8"
API_KEY = "b25eb076f5c0412fa9f1eba94550d02e"

# ========== FILES ==========
FILES = ["balances.json", "orders.json", "temp.json", "users.json", "settings.json", "categories.json", "products.json"]
for f in FILES:
    if not os.path.exists(f):
        with open(f, "w") as file:
            json.dump({}, file)

# ========== DEFAULT SETTINGS ==========
with open("settings.json", "r") as f:
    settings = json.load(f)

if "proof_link" not in settings:
    settings["proof_link"] = "https://t.me/+je-4gsroGyVmYjA1"
if "howto_link" not in settings:
    settings["howto_link"] = "https://t.me/+je-4gsroGyVmYjA1"
if "support_user" not in settings:
    settings["support_user"] = "https://t.me/CLASSY_EZX"

with open("settings.json", "w") as f:
    json.dump(settings, f)

# ========== DEFAULT CATEGORIES ==========
with open("categories.json", "r") as f:
    categories = json.load(f)

if len(categories) == 0:
    categories = {
        "c1": {"name": "Non-Root Mobile"},
        "c2": {"name": "Root Mobile"},
        "c3": {"name": "PC / Computer"},
        "c4": {"name": "iOS / iPhone"},
        "c5": {"name": "8 Level ID"}
    }
    with open("categories.json", "w") as f:
        json.dump(categories, f)

# ========== API FUNCTIONS ==========
def api_buy_product(product_id, days):
    """
    Call the external API to buy a product
    Returns: (success, message, key)
    """
    # Try different duration formats like in your test file
    durations = [
        f"{days} Day",
        f"{days} Days",
        f"{days} DaYS",
        f"{days} DaYS NONROOT",
        f"{days}D",
        f"{days} Day NONROOT",
        f"{days}d",
        f"{days} Day Non-Root"
    ]
    
    for duration in durations:
        try:
            data = {
                'api_key': API_KEY,
                'action': 'buy',
                'product_id': str(product_id),
                'duration': duration,
                'price': '32'  # Default price, can be dynamic
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'x-master-key': MASTER_KEY
            }
            
            response = requests.post(API_URL, data=data, headers=headers, timeout=30)
            result = response.json()
            
            if result.get('status') == 'success':
                return True, "Success", result.get('key')
                
        except Exception as e:
            continue
    
    return False, "All duration formats failed", None

# ========== LOAD DATA FUNCTIONS ==========
def load_data():
    with open("balances.json", "r") as f:
        balances = json.load(f)
    with open("users.json", "r") as f:
        users = json.load(f)
    with open("orders.json", "r") as f:
        orders = json.load(f)
    with open("products.json", "r") as f:
        products = json.load(f)
    return balances, users, orders, products

def save_data(balances, users, orders, products):
    with open("balances.json", "w") as f:
        json.dump(balances, f)
    with open("users.json", "w") as f:
        json.dump(users, f)
    with open("orders.json", "w") as f:
        json.dump(orders, f)
    with open("products.json", "w") as f:
        json.dump(products, f)

def save_temp(user_id, key, value):
    with open("temp.json", "r") as f:
        temp = json.load(f)
    if str(user_id) not in temp:
        temp[str(user_id)] = {}
    temp[str(user_id)][key] = value
    with open("temp.json", "w") as f:
        json.dump(temp, f)

def get_temp(user_id):
    with open("temp.json", "r") as f:
        temp = json.load(f)
    return temp.get(str(user_id), {})

def clear_temp(user_id):
    with open("temp.json", "r") as f:
        temp = json.load(f)
    if str(user_id) in temp:
        del temp[str(user_id)]
    with open("temp.json", "w") as f:
        json.dump(temp, f)

# ========== TELEGRAM BOT ==========
app = Flask(__name__)

# ========== HELPER FUNCTIONS ==========
def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛒 Shop Now", callback_data="shop")],
        [InlineKeyboardButton("📦 My Orders", callback_data="orders"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("💰 Add Balance", callback_data="addbal"), InlineKeyboardButton("📄 Payment Proof", callback_data="proof")],
        [InlineKeyboardButton("📖 How to Use", callback_data="howto"), InlineKeyboardButton("💬 Support", callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel_keyboard():
    keyboard = [
        [InlineKeyboardButton("📁 Add Category", callback_data="addcat")],
        [InlineKeyboardButton("📦 Add Product", callback_data="addprod")],
        [InlineKeyboardButton("➕ Add Plan", callback_data="addplan")],
        [InlineKeyboardButton("✏️ Edit Plan", callback_data="editplan")],
        [InlineKeyboardButton("🗑️ Delete Plan", callback_data="delplan")],
        [InlineKeyboardButton("✏️ Edit Product", callback_data="editprod")],
        [InlineKeyboardButton("🗑️ Delete Product", callback_data="delprod")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("👥 User List", callback_data="userlist")],
        [InlineKeyboardButton("💰 Add User Balance", callback_data="adduserbal")],
        [InlineKeyboardButton("📄 Proof Link", callback_data="setproof")],
        [InlineKeyboardButton("📖 HowTo Link", callback_data="sethowto")],
        [InlineKeyboardButton("💬 Support Username", callback_data="setsupport")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_admin_keyboard():
    keyboard = [[InlineKeyboardButton("⬅️ Back to Admin", callback_data="backadmin")]]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_menu_keyboard():
    keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back")]]
    return InlineKeyboardMarkup(keyboard)

# ========== BOT COMMANDS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    balances, users, orders, products = load_data()
    
    if user_id not in balances:
        balances[user_id] = 0
    if user_id not in users:
        users[user_id] = {
            "name": user.first_name,
            "username": user.username or "",
            "join": time.strftime("%d %b %Y")
        }
    
    save_data(balances, users, orders, products)
    
    msg = f"""👑 ———— <b>NOX BHAI STORE</b> ———— 👑

🧡 Yo — ꨄ <b>{user.first_name}</b>, Welcome Back!!

🔥 ———— WHY CHOOSE US ———— 🔥

🔑 Genuine Premium Keys
⚡ Instant Auto Delivery
🛡️ Secure UPI Payments
💎 Unbeatable Prices
👊 Real 24/7 Support
——————————————————————
💰 Let's get you a key!

💲 <b>Your Balance: ₹{balances[user_id]}.00</b>"""
    
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=get_main_menu_keyboard())

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin")
        return
    
    users = load_data()[1]
    msg = f"""👑 <b>Admin Panel</b>

👥 Total Users: {len(users)}
📄 Proof: {settings['proof_link']}
📖 HowTo: {settings['howto_link']}
💬 Support: {settings['support_user']}"""
    
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=get_admin_panel_keyboard())

# ========== CALLBACK QUERY HANDLER ==========
async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    chat_id = query.message.chat.id
    message_id = query.message.message_id
    data = query.data
    
    balances, users, orders, products = load_data()
    
    # ========== USER BUTTONS ==========
    if data == "addbal":
        await send_add_balance(query, user_id)
    
    elif data == "profile":
        await send_profile(query, user_id)
    
    elif data == "orders":
        await send_orders(query, user_id)
    
    elif data == "shop":
        await send_categories(query)
    
    elif data == "proof":
        await send_proof(query)
    
    elif data == "howto":
        await send_howto(query)
    
    elif data == "support":
        await send_support(query)
    
    # ========== CATEGORY PRODUCTS ==========
    elif data.startswith("cat_"):
        cid = data.replace("cat_", "")
        await send_products(query, cid)
    
    # ========== BUY PRODUCT (SHOW PLANS) ==========
    elif data.startswith("buy_"):
        pid = data.replace("buy_", "")
        await send_product_plans(query, pid)
    
    # ========== BUY SPECIFIC PLAN ==========
    elif data.startswith("plan_"):
        parts = data.split("_")
        pid = parts[1]
        plan_index = int(parts[2])
        await buy_plan(query, user_id, pid, plan_index)
    
    # ========== ADMIN PANEL BUTTONS ==========
    elif data == "addcat" and user_id == ADMIN_ID:
        save_temp(user_id, "waiting", "newcat")
        await query.edit_message_text(
            "📁 <b>Category Ka Naam Bhejo</b>\n\nExample: Non-Root Mobile",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data == "addprod" and user_id == ADMIN_ID:
        await send_select_category_for_product(query)
    
    elif data.startswith("addtoprod_") and user_id == ADMIN_ID:
        cid = data.replace("addtoprod_", "")
        save_temp(user_id, "addprod_cat", cid)
        save_temp(user_id, "waiting", "prod_name")
        await query.edit_message_text(
            "📦 <b>Product Ka Naam Bhejo</b>\n\nExample: SILENT CHEATS SAFE",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data == "addplan" and user_id == ADMIN_ID:
        await send_select_product_for_add_plan(query)
    
    elif data.startswith("addplanprod_") and user_id == ADMIN_ID:
        pid = data.replace("addplanprod_", "")
        save_temp(user_id, "addplan_pid", pid)
        save_temp(user_id, "waiting", "plan_days")
        await query.edit_message_text(
            "📅 <b>Kitne Days ka plan hai?</b>\n\nExample: 1, 3, 7, 30",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data == "editplan" and user_id == ADMIN_ID:
        await send_select_product_for_edit_plan(query)
    
    elif data.startswith("editplanprod_") and user_id == ADMIN_ID:
        pid = data.replace("editplanprod_", "")
        await send_plans_for_edit(query, pid)
    
    elif data.startswith("editplan_") and user_id == ADMIN_ID:
        parts = data.split("_")
        pid = parts[1]
        plan_index = int(parts[2])
        save_temp(user_id, "edit_pid", pid)
        save_temp(user_id, "edit_plan_index", plan_index)
        
        products = load_data()[3]
        plan = products[pid]['plans'][plan_index]
        keys_count = len(plan.get('keys', []))
        
        msg = f"""✏️ <b>Edit Plan</b>

Current: {plan['days']} Days - ₹{plan['price']}
Product ID: {plan.get('product_id', 'N/A')}
Keys: {keys_count}

Kya edit karna hai?"""
        keyboard = [
            [InlineKeyboardButton("📅 Days", callback_data=f"editplandays_{pid}_{plan_index}")],
            [InlineKeyboardButton("💰 Price", callback_data=f"editplanprice_{pid}_{plan_index}")],
            [InlineKeyboardButton("🔑 Product ID", callback_data=f"editplanpid_{pid}_{plan_index}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="backadmin")]
        ]
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("editplandays_") and user_id == ADMIN_ID:
        parts = data.split("_")
        pid = parts[1]
        plan_index = int(parts[2])
        save_temp(user_id, "edit_pid", pid)
        save_temp(user_id, "edit_plan_index", plan_index)
        save_temp(user_id, "waiting", "edit_plan_days")
        await query.edit_message_text(
            "📅 <b>Naya Days Bhejo</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data.startswith("editplanprice_") and user_id == ADMIN_ID:
        parts = data.split("_")
        pid = parts[1]
        plan_index = int(parts[2])
        save_temp(user_id, "edit_pid", pid)
        save_temp(user_id, "edit_plan_index", plan_index)
        save_temp(user_id, "waiting", "edit_plan_price")
        await query.edit_message_text(
            "💰 <b>Naya Price Bhejo</b>\n\nExample: 199",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data.startswith("editplanpid_") and user_id == ADMIN_ID:
        parts = data.split("_")
        pid = parts[1]
        plan_index = int(parts[2])
        save_temp(user_id, "edit_pid", pid)
        save_temp(user_id, "edit_plan_index", plan_index)
        save_temp(user_id, "waiting", "edit_plan_pid")
        await query.edit_message_text(
            "🔑 <b>Naya Product ID Bhejo</b>\n\nExample: 62",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data == "delplan" and user_id == ADMIN_ID:
        await send_select_product_for_delete_plan(query)
    
    elif data.startswith("delplanprod_") and user_id == ADMIN_ID:
        pid = data.replace("delplanprod_", "")
        await send_plans_for_delete(query, pid)
    
    elif data.startswith("delplan_") and user_id == ADMIN_ID:
        parts = data.split("_")
        pid = parts[1]
        plan_index = int(parts[2])
        
        products = load_data()[3]
        plan = products[pid]['plans'][plan_index]
        del products[pid]['plans'][plan_index]
        products[pid]['plans'] = list(products[pid]['plans'])
        save_data(*load_data()[:3], products)
        
        await query.edit_message_text(
            f"🗑️ <b>Plan Delete Ho Gaya:</b> {plan['days']} Days - ₹{plan['price']}",
            parse_mode="HTML",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    elif data == "editprod" and user_id == ADMIN_ID:
        await send_select_product_for_edit(query)
    
    elif data.startswith("editprod_") and user_id == ADMIN_ID:
        pid = data.replace("editprod_", "")
        save_temp(user_id, "edit_pid", pid)
        products = load_data()[3]
        p = products[pid]
        msg = f"✏️ <b>Edit Product</b>\n\nName: {p['name']}\nPlans: {len(p['plans'])}"
        keyboard = [
            [InlineKeyboardButton("📝 Name", callback_data=f"edit_name_{pid}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="backadmin")]
        ]
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("edit_name_") and user_id == ADMIN_ID:
        pid = data.replace("edit_name_", "")
        save_temp(user_id, "edit_pid", pid)
        save_temp(user_id, "waiting", "edit_name")
        await query.edit_message_text(
            "📝 <b>Naya Name Bhejo</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data == "delprod" and user_id == ADMIN_ID:
        await send_select_product_for_delete(query)
    
    elif data.startswith("delprod_") and user_id == ADMIN_ID:
        pid = data.replace("delprod_", "")
        products = load_data()[3]
        if pid not in products:
            await query.edit_message_text(
                "❌ Product nahi mila!",
                parse_mode="HTML",
                reply_markup=get_back_to_admin_keyboard()
            )
            return
        p = products[pid]
        del products[pid]
        save_data(*load_data()[:3], products)
        await query.edit_message_text(
            f"🗑️ <b>Product Delete Ho Gaya!</b>\n\nName: {p['name']}\nCategory: {p['cat']}\nPlans: {len(p['plans'])}",
            parse_mode="HTML",
            reply_markup=get_back_to_admin_keyboard()
        )
    
    elif data == "broadcast" and user_id == ADMIN_ID:
        save_temp(user_id, "waiting", "broadcast_text")
        await query.edit_message_text(
            "📢 <b>Broadcast Message</b>\n\nMessage bhejo (Text, Photo, Video, Voice, Document)\n\n<b>Note:</b> Photo/Video/Voice/Document ke saath caption bhi bhej sakte ho",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data == "userlist" and user_id == ADMIN_ID:
        users = load_data()[1]
        msg = f"👥 <b>Total Users:</b> {len(users)}\n\n"
        i = 1
        for uid, u in users.items():
            msg += f"{i}. {u['name']}"
            if u['username']:
                msg += f" (@{u['username']})"
            msg += f"\n   🆔 <code>{uid}</code>\n   📅 {u['join']}\n\n"
            i += 1
            if i > 20:
                msg += f"\n... aur {len(users)-20} users"
                break
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_back_to_admin_keyboard())
    
    elif data == "adduserbal" and user_id == ADMIN_ID:
        save_temp(user_id, "waiting", "adduserbal_id")
        await query.edit_message_text(
            "💰 <b>Add Balance to User</b>\n\nUser ID bhejo (jo profile me dikhta hai)\n\nExample: 8154859186",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data == "setproof" and user_id == ADMIN_ID:
        save_temp(user_id, "waiting", "proof")
        await query.edit_message_text(
            "📄 <b>Payment Proof Link Bhejo</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data == "sethowto" and user_id == ADMIN_ID:
        save_temp(user_id, "waiting", "howto")
        await query.edit_message_text(
            "📖 <b>How To Use Link Bhejo</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data == "setsupport" and user_id == ADMIN_ID:
        save_temp(user_id, "waiting", "support")
        await query.edit_message_text(
            "💬 <b>Support Username Bhejo</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")]])
        )
    
    elif data == "backadmin":
        users = load_data()[1]
        msg = f"👑 <b>Admin Panel</b>\n\n👥 Total Users: {len(users)}"
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_admin_panel_keyboard())
    
    elif data == "back":
        user = query.from_user
        balances = load_data()[0]
        await query.edit_message_text(
            f"👑 ———— <b>NOX BHAI STORE</b> ———— 👑\n\n🧡 Yo — ꨄ <b>{user.first_name}</b>, Welcome Back!!\n\n🔥 ———— WHY CHOOSE US ———— 🔥\n\n🔑 Genuine Premium Keys\n⚡ Instant Auto Delivery\n🛡️ Secure UPI Payments\n💎 Unbeatable Prices\n👊 Real 24/7 Support\n——————————————————————\n💰 Let's get you a key!\n\n💲 <b>Your Balance: ₹{balances.get(user_id, 0)}.00</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    
    elif data == "backcat":
        await send_categories(query)

# ========== USER FUNCTIONS ==========
async def send_add_balance(query, user_id):
    balances = load_data()[0]
    bal = balances.get(user_id, 0)
    msg = f"💸 <b>Add Balance</b>\n\nCurrent balance: ₹{bal}.00\nPick a quick amount below, or enter a custom amount.\nMin: ₹1.00 • Max: ₹5,000.00\n⚠️ QR 5 Minute me expire ho jayega"
    keyboard = [
        [InlineKeyboardButton("₹50", callback_data="pay_50"), InlineKeyboardButton("₹100", callback_data="pay_100"), InlineKeyboardButton("₹200", callback_data="pay_200")],
        [InlineKeyboardButton("₹500", callback_data="pay_500"), InlineKeyboardButton("₹1000", callback_data="pay_1000"), InlineKeyboardButton("₹2000", callback_data="pay_2000")],
        [InlineKeyboardButton("✏️ Custom Amount", callback_data="custom")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back")]
    ]
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_profile(query, user_id):
    balances, users, orders = load_data()[:3]
    user = users.get(user_id, {})
    balance = balances.get(user_id, 0)
    total_orders = sum(1 for o in orders.values() if o.get('user') == user_id and o.get('status') == "Delivered")
    
    msg = f"—\n👤 <b>YOUR PROFILE</b>\n—\n\n👹 <b>Name:</b> {user.get('name', 'User')}\n🆔 <b>User ID:</b> <code>{user_id}</code>\n📅 <b>Member Since:</b> {user.get('join', time.strftime('%d %b %Y'))}\n🏷️ <b>Account Type:</b> 👤 Regular\n💰 <b>Balance:</b> ₹{balance}.00\n🛒 <b>Total Orders:</b> {total_orders}\n—"
    keyboard = [
        [InlineKeyboardButton("🛒 Shop Now", callback_data="shop"), InlineKeyboardButton("📦 My Orders", callback_data="orders")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back")]
    ]
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_orders(query, user_id):
    orders = load_data()[2]
    my_orders = {k: v for k, v in orders.items() if v.get('user') == user_id}
    
    if not my_orders:
        msg = "📄 <b>RECIPT</b>\n\nYou haven't made any purchases yet."
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_back_to_menu_keyboard())
        return
    
    msg = "📦 <b>My Orders</b>\n\n"
    i = 1
    for oid, o in reversed(my_orders.items()):
        msg += f"{i}. <b>{o.get('product_name', 'Unknown')}</b>\n 📅 Plan: {o.get('days', 0)} Days\n 💰 Price: ₹{o.get('price', 0)}\n 📅 Date: {o.get('date', 'N/A')}\n 🆔 Order: <code>{oid}</code>\n 🔑 Key: <code>{o.get('key', 'N/A')}</code>\n Status: ✅ {o.get('status', 'Unknown')}\n\n"
        i += 1
    
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_back_to_menu_keyboard())

async def send_categories(query):
    with open("categories.json", "r") as f:
        categories = json.load(f)
    
    msg = "🛒 <b>PRODUCT STORE — SHOP</b>\n\n📱 Select your device type:"
    keyboard = []
    for cid, cat in categories.items():
        keyboard.append([InlineKeyboardButton(cat['name'], callback_data=f"cat_{cid}")])
    keyboard.append([InlineKeyboardButton("📲 Back", callback_data="back")])
    
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_products(query, cid):
    with open("products.json", "r") as f:
        products = json.load(f)
    with open("categories.json", "r") as f:
        categories = json.load(f)
    
    cat_name = categories.get(cid, {}).get('name', 'Category')
    msg = f"🛒 <b>{cat_name}</b>\n\nSelect product:"
    keyboard = []
    
    for pid, p in products.items():
        if p.get('cat') == cid:
            plan_count = len(p.get('plans', []))
            keyboard.append([InlineKeyboardButton(f"{p['name']} ({plan_count} plans)", callback_data=f"buy_{pid}")])
    
    if not keyboard:
        msg += "\n\n❌ Is category me abhi koi product nahi hai"
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="backcat")])
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_product_plans(query, pid):
    products = load_data()[3]
    
    if pid not in products:
        await query.edit_message_text("❌ Product nahi mila", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="backcat")]]))
        return
    
    p = products[pid]
    plans = p.get('plans', [])
    
    if not plans:
        await query.edit_message_text(f"❌ <b>{p['name']}</b>\n\nIs product ke liye koi plan nahi hai.\nAdmin se contact karo.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Shop", callback_data="backcat")]]))
        return
    
    plans = sorted(plans, key=lambda x: x['days'])
    msg = f"📦 <b>{p['name']}</b>\n\n<b>Choose a plan</b>\n"
    keyboard = []
    
    for idx, plan in enumerate(plans):
        day_text = f"{plan['days']} Day{'s' if plan['days'] > 1 else ''}"
        product_id = plan.get('product_id', 'N/A')
        msg += f"\n• {day_text} — ₹{plan['price']} (ID: {product_id})"
        keyboard.append([InlineKeyboardButton(f"{day_text} - ₹{plan['price']}", callback_data=f"plan_{pid}_{idx}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Shop", callback_data="backcat")])
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_plan(query, user_id, pid, plan_index):
    balances, users, orders, products = load_data()
    
    if pid not in products:
        await query.edit_message_text("❌ Product nahi mila", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="backcat")]]))
        return
    
    p = products[pid]
    plans = p.get('plans', [])
    
    if plan_index >= len(plans):
        await query.edit_message_text("❌ Plan nahi mila", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="backcat")]]))
        return
    
    plan = plans[plan_index]
    bal = balances.get(user_id, 0)
    
    if bal < plan['price']:
        await query.edit_message_text(
            f"❌ <b>Insufficient Balance</b>\n\nPlan: {plan['days']} Days\nPrice: ₹{plan['price']}\nYour Balance: ₹{bal}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Add Balance", callback_data="addbal")],
                [InlineKeyboardButton("⬅️ Back", callback_data="backcat")]
            ])
        )
        return
    
    # Check if product_id exists in plan
    if 'product_id' not in plan:
        await query.edit_message_text(
            "❌ <b>Invalid Plan!</b>\n\nIs plan mein Product ID nahi hai.\nAdmin se contact karo.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="backcat")]])
        )
        return
    
    # Use API to buy with duration testing
    success, message, key = api_buy_product(plan['product_id'], plan['days'])
    
    if not success:
        await query.edit_message_text(
            f"❌ <b>API Error!</b>\n\n{message}\n\nProduct ID: {plan['product_id']}\nDays: {plan['days']}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="backcat")]])
        )
        return
    
    # Deduct balance
    balances[user_id] -= plan['price']
    
    # Create order
    order_id = f"ORD{int(time.time())}{random.randint(100, 999)}"
    orders[order_id] = {
        "user": user_id,
        "product_id": pid,
        "product_name": p['name'],
        "plan": plan,
        "price": plan['price'],
        "days": plan['days'],
        "status": "Delivered",
        "date": time.strftime("%d %b %Y %H:%M"),
        "key": key
    }
    
    save_data(balances, users, orders, products)
    
    msg = f"""✅ <b>Order Delivered!</b>

Product: {p['name']}
Plan: {plan['days']} Days
Price: ₹{plan['price']}
Order ID: <code>{order_id}</code>
Date: {time.strftime("%d %b %Y %H:%M")}

🔑 <b>Your Key:</b>
<code>{key}</code>"""
    
    keyboard = [
        [InlineKeyboardButton("📦 My Orders", callback_data="orders")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back")]
    ]
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_proof(query):
    with open("settings.json", "r") as f:
        settings = json.load(f)
    link = settings.get('proof_link', '')
    msg = f"📄 <b>Payment Proof Channel</b>\n\nYaha sabhi payment proof milenge\n🔗 <a href='{link}'>Click Here</a>"
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_back_to_menu_keyboard())

async def send_howto(query):
    with open("settings.json", "r") as f:
        settings = json.load(f)
    link = settings.get('howto_link', '')
    msg = f"📖 <b>How to Use</b>\n\n1. Add Balance\n2. Shop Now\n3. Key Instant Milega\nVideo Tutorial:\n🔗 <a href='{link}'>Watch Now</a>"
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_back_to_menu_keyboard())

async def send_support(query):
    with open("settings.json", "r") as f:
        settings = json.load(f)
    user = settings.get('support_user', '')
    msg = f"💬 <b>Support</b>\n\nKoi dikkat ho to message karo\n🔗 <a href='https://t.me/{user.lstrip('@')}'>{user}</a>\n\n24/7 Available"
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_back_to_menu_keyboard())

# ========== ADMIN SELECT FUNCTIONS ==========
async def send_select_category_for_product(query):
    with open("categories.json", "r") as f:
        categories = json.load(f)
    
    if not categories:
        await query.edit_message_text("❌ <b>Koi Category nahi hai!</b>\n\nPehle '📁 Add Category' se category add karo.", parse_mode="HTML", reply_markup=get_back_to_admin_keyboard())
        return
    
    msg = "📁 <b>Kis Category me Product Add karna hai?</b>"
    keyboard = []
    for cid, cat in categories.items():
        keyboard.append([InlineKeyboardButton(cat['name'], callback_data=f"addtoprod_{cid}")])
    keyboard.append([InlineKeyboardButton("⬅️ Cancel", callback_data="backadmin")])
    
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_select_product_for_add_plan(query):
    products = load_data()[3]
    if not products:
        await query.edit_message_text("❌ <b>Koi Product nahi hai!</b>\n\nPehle '📦 Add Product' se product add karo.", parse_mode="HTML", reply_markup=get_back_to_admin_keyboard())
        return
    
    msg = "➕ <b>Kis Product me Plan Add karna hai?</b>"
    keyboard = []
    for pid, p in products.items():
        plan_count = len(p.get('plans', []))
        keyboard.append([InlineKeyboardButton(f"{p['name']} ({plan_count} plans)", callback_data=f"addplanprod_{pid}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="backadmin")])
    
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_select_product_for_edit_plan(query):
    products = load_data()[3]
    if not products:
        await query.edit_message_text("❌ <b>Koi Product nahi hai!</b>", parse_mode="HTML", reply_markup=get_back_to_admin_keyboard())
        return
    
    msg = "✏️ <b>Kis Product ka Plan Edit karna hai?</b>"
    keyboard = []
    for pid, p in products.items():
        plan_count = len(p.get('plans', []))
        keyboard.append([InlineKeyboardButton(f"{p['name']} ({plan_count} plans)", callback_data=f"editplanprod_{pid}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="backadmin")])
    
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_plans_for_edit(query, pid):
    products = load_data()[3]
    if pid not in products:
        await query.edit_message_text("❌ Product nahi mila!", reply_markup=get_back_to_admin_keyboard())
        return
    
    p = products[pid]
    if not p.get('plans'):
        await query.edit_message_text(f"❌ <b>Is product me koi plan nahi hai!</b>\n\nPehle '➕ Add Plan' se plan add karo.", parse_mode="HTML", reply_markup=get_back_to_admin_keyboard())
        return
    
    msg = f"✏️ <b>Edit Plan - {p['name']}</b>\n\nKis plan ko edit karna hai?"
    keyboard = []
    for idx, plan in enumerate(p['plans']):
        product_id = plan.get('product_id', 'N/A')
        keyboard.append([InlineKeyboardButton(f"{plan['days']} Days - ₹{plan['price']} (ID: {product_id})", callback_data=f"editplan_{pid}_{idx}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="backadmin")])
    
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_select_product_for_delete_plan(query):
    products = load_data()[3]
    if not products:
        await query.edit_message_text("❌ <b>Koi Product nahi hai!</b>", parse_mode="HTML", reply_markup=get_back_to_admin_keyboard())
        return
    
    msg = "🗑️ <b>Kis Product ka Plan Delete karna hai?</b>"
    keyboard = []
    for pid, p in products.items():
        plan_count = len(p.get('plans', []))
        keyboard.append([InlineKeyboardButton(f"{p['name']} ({plan_count} plans)", callback_data=f"delplanprod_{pid}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="backadmin")])
    
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_plans_for_delete(query, pid):
    products = load_data()[3]
    if pid not in products:
        await query.edit_message_text("❌ Product nahi mila!", reply_markup=get_back_to_admin_keyboard())
        return
    
    p = products[pid]
    if not p.get('plans'):
        await query.edit_message_text(f"❌ <b>Is product me koi plan nahi hai!</b>", parse_mode="HTML", reply_markup=get_back_to_admin_keyboard())
        return
    
    msg = f"🗑️ <b>Delete Plan - {p['name']}</b>\n\nKis plan ko delete karna hai?"
    keyboard = []
    for idx, plan in enumerate(p['plans']):
        keyboard.append([InlineKeyboardButton(f"❌ {plan['days']} Days - ₹{plan['price']}", callback_data=f"delplan_{pid}_{idx}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="backadmin")])
    
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_select_product_for_delete(query):
    products = load_data()[3]
    if not products:
        await query.edit_message_text("❌ <b>Koi Product nahi hai!</b>\n\nPehle '📦 Add Product' se product add karo.", parse_mode="HTML", reply_markup=get_back_to_admin_keyboard())
        return
    
    msg = "🗑️ <b>Kis Product ko Delete karna hai?</b>\n\n⚠️ <b>Warning:</b> Product delete karne se uske saare plans aur keys bhi delete ho jayenge!"
    keyboard = []
    for pid, p in products.items():
        plan_count = len(p.get('plans', []))
        keyboard.append([InlineKeyboardButton(f"❌ {p['name']} ({plan_count} plans)", callback_data=f"delprod_{pid}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="backadmin")])
    
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_select_product_for_edit(query):
    products = load_data()[3]
    if not products:
        await query.edit_message_text("❌ <b>Koi Product nahi hai!</b>", parse_mode="HTML", reply_markup=get_back_to_admin_keyboard())
        return
    
    msg = "✏️ <b>Kis Product ko Edit karna hai?</b>"
    keyboard = []
    for pid, p in products.items():
        keyboard.append([InlineKeyboardButton(f"{p['name']} ({len(p.get('plans', []))} plans)", callback_data=f"editprod_{pid}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="backadmin")])
    
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

# ========== MESSAGE HANDLER ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if not text:
        return
    
    temp = get_temp(user_id)
    waiting = temp.get('waiting', '')
    
    # ---- ADD CATEGORY ----
    if waiting == "newcat" and user_id == ADMIN_ID:
        with open("categories.json", "r") as f:
            categories = json.load(f)
        cid = f"c{int(time.time())}"
        categories[cid] = {"name": text}
        with open("categories.json", "w") as f:
            json.dump(categories, f)
        clear_temp(user_id)
        await update.message.reply_text(f"✅ Category Add ho gayi: {text}")
        await admin(update, context)
        return
    
    # ---- ADD PRODUCT NAME ----
    elif waiting == "prod_name" and user_id == ADMIN_ID:
        cid = temp.get('addprod_cat')
        if not cid:
            await update.message.reply_text("❌ Error: Category not found!")
            clear_temp(user_id)
            return
        
        products = load_data()[3]
        pid = f"p{int(time.time())}"
        products[pid] = {
            "name": text,
            "cat": cid,
            "plans": []
        }
        save_data(*load_data()[:3], products)
        clear_temp(user_id)
        
        await update.message.reply_text(f"✅ Product Add ho gaya!\n\nName: {text}\n\nAb /admin se '➕ Add Plan' karke plans add karo.")
        await admin(update, context)
        return
    
    # ---- ADD PLAN DAYS ----
    elif waiting == "plan_days" and user_id == ADMIN_ID:
        try:
            days = int(text)
            save_temp(user_id, "plan_days", days)
            save_temp(user_id, "waiting", "plan_price")
            await update.message.reply_text("💰 <b>Is plan ka Price kya hai?</b>\n\nExample: 90", parse_mode="HTML")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number for days!")
        return
    
    # ---- ADD PLAN PRICE ----
    elif waiting == "plan_price" and user_id == ADMIN_ID:
        try:
            price = int(text)
            save_temp(user_id, "plan_price", price)
            save_temp(user_id, "waiting", "plan_product_id")
            await update.message.reply_text("🔑 <b>Is plan ka Product ID kya hai?</b>\n\nExample: 62", parse_mode="HTML")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number for price!")
        return
    
    # ---- ADD PLAN PRODUCT ID ----
    elif waiting == "plan_product_id" and user_id == ADMIN_ID:
        product_id = text.strip()
        pid = temp.get('addplan_pid')
        days = temp.get('plan_days')
        price = temp.get('plan_price')
        
        if not pid or not days or not price:
            await update.message.reply_text("❌ Error: Missing product, days or price!")
            clear_temp(user_id)
            return
        
        products = load_data()[3]
        products[pid]['plans'].append({
            "days": days,
            "price": price,
            "product_id": product_id
        })
        save_data(*load_data()[:3], products)
        clear_temp(user_id)
        
        await update.message.reply_text(f"✅ Plan Add Ho Gaya!\n\nDays: {days}\nPrice: ₹{price}\nProduct ID: {product_id}")
        await admin(update, context)
        return
    
    # ---- EDIT NAME ----
    elif waiting == "edit_name" and user_id == ADMIN_ID:
        pid = temp.get('edit_pid')
        if not pid:
            await update.message.reply_text("❌ Error: Product not found!")
            clear_temp(user_id)
            return
        
        products = load_data()[3]
        products[pid]['name'] = text
        save_data(*load_data()[:3], products)
        clear_temp(user_id)
        await update.message.reply_text(f"✅ Name Update: {text}")
        await admin(update, context)
        return
    
    # ---- EDIT PLAN DAYS ----
    elif waiting == "edit_plan_days" and user_id == ADMIN_ID:
        try:
            days = int(text)
            pid = temp.get('edit_pid')
            plan_index = temp.get('edit_plan_index')
            
            if pid is None or plan_index is None:
                await update.message.reply_text("❌ Error: Missing product or plan!")
                clear_temp(user_id)
                return
            
            products = load_data()[3]
            products[pid]['plans'][plan_index]['days'] = days
            save_data(*load_data()[:3], products)
            clear_temp(user_id)
            await update.message.reply_text(f"✅ Days Update: {days}")
            await admin(update, context)
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number!")
        return
    
    # ---- EDIT PLAN PRICE ----
    elif waiting == "edit_plan_price" and user_id == ADMIN_ID:
        try:
            price = int(text)
            pid = temp.get('edit_pid')
            plan_index = temp.get('edit_plan_index')
            
            if pid is None or plan_index is None:
                await update.message.reply_text("❌ Error: Missing product or plan!")
                clear_temp(user_id)
                return
            
            products = load_data()[3]
            products[pid]['plans'][plan_index]['price'] = price
            save_data(*load_data()[:3], products)
            clear_temp(user_id)
            await update.message.reply_text(f"✅ Price Update: ₹{price}")
            await admin(update, context)
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number!")
        return
    
    # ---- EDIT PLAN PRODUCT ID ----
    elif waiting == "edit_plan_pid" and user_id == ADMIN_ID:
        product_id = text.strip()
        pid = temp.get('edit_pid')
        plan_index = temp.get('edit_plan_index')
        
        if pid is None or plan_index is None:
            await update.message.reply_text("❌ Error: Missing product or plan!")
            clear_temp(user_id)
            return
        
        products = load_data()[3]
        products[pid]['plans'][plan_index]['product_id'] = product_id
        save_data(*load_data()[:3], products)
        clear_temp(user_id)
        await update.message.reply_text(f"✅ Product ID Update: {product_id}")
        await admin(update, context)
        return
    
    # ---- ADD USER BALANCE - USER ID ----
    elif waiting == "adduserbal_id" and user_id == ADMIN_ID:
        target_id = text.strip()
        users = load_data()[1]
        
        if target_id not in users:
            await update.message.reply_text(f"❌ User ID <code>{target_id}</code> nahi mila!\n\n/users se list dekh lo.", parse_mode="HTML")
            return
        
        save_temp(user_id, "adduserbal_target", target_id)
        save_temp(user_id, "waiting", "adduserbal_amount")
        await update.message.reply_text(f"💰 <b>Add Balance to {users[target_id]['name']}</b>\n\nKitna amount add karna hai?\n\nExample: 100", parse_mode="HTML")
        return
    
    # ---- ADD USER BALANCE - AMOUNT ----
    elif waiting == "adduserbal_amount" and user_id == ADMIN_ID:
        try:
            amount = int(text)
            if amount <= 0:
                await update.message.reply_text("❌ Amount 0 se zyada hona chahiye!")
                return
            
            target_id = temp.get('adduserbal_target')
            if not target_id:
                await update.message.reply_text("❌ Error: Target user not found!")
                clear_temp(user_id)
                return
            
            balances, users = load_data()[:2]
            old_bal = balances.get(target_id, 0)
            balances[target_id] = old_bal + amount
            save_data(balances, users, *load_data()[2:])
            
            clear_temp(user_id)
            await update.message.reply_text(f"✅ <b>Balance Added!</b>\n\nUser: {users[target_id]['name']}\n🆔 <code>{target_id}</code>\n💰 Added: ₹{amount}\n💲 New Balance: ₹{balances[target_id]}", parse_mode="HTML")
            await admin(update, context)
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number!")
        return
    
    # ---- SETTINGS ----
    elif waiting == "proof" and user_id == ADMIN_ID:
        with open("settings.json", "r") as f:
            settings = json.load(f)
        settings['proof_link'] = text
        with open("settings.json", "w") as f:
            json.dump(settings, f)
        clear_temp(user_id)
        await update.message.reply_text(f"✅ Payment Proof Link Update: {text}")
        await admin(update, context)
        return
    
    elif waiting == "howto" and user_id == ADMIN_ID:
        with open("settings.json", "r") as f:
            settings = json.load(f)
        settings['howto_link'] = text
        with open("settings.json", "w") as f:
            json.dump(settings, f)
        clear_temp(user_id)
        await update.message.reply_text(f"✅ How To Use Link Update: {text}")
        await admin(update, context)
        return
    
    elif waiting == "support" and user_id == ADMIN_ID:
        with open("settings.json", "r") as f:
            settings = json.load(f)
        settings['support_user'] = text
        with open("settings.json", "w") as f:
            json.dump(settings, f)
        clear_temp(user_id)
        await update.message.reply_text(f"✅ Support Username Update: {text}")
        await admin(update, context)
        return
    
    # ---- BROADCAST TEXT ----
    elif waiting == "broadcast_text" and user_id == ADMIN_ID:
        users = load_data()[1]
        sent = 0
        failed = 0
        
        for uid in users.keys():
            try:
                await context.bot.send_message(chat_id=uid, text=f"📢 <b>Announcement</b>\n\n{text}", parse_mode="HTML")
                sent += 1
            except:
                failed += 1
            time.sleep(0.05)
        
        clear_temp(user_id)
        await update.message.reply_text(f"✅ <b>Broadcast Complete!</b>\n\nTotal Users: {len(users)}\n✅ Sent: {sent}\n❌ Failed: {failed}", parse_mode="HTML")
        await admin(update, context)
        return

# ========== FLASK WEBHOOK ==========
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    await application.process_update(update)
    return 'OK'

# ========== MAIN ==========
if __name__ == "__main__":
    # Initialize application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CallbackQueryHandler(callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000)
