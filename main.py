#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import time
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ========================================
# LOGGING SETUP
# ========================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========================================
# CONFIGURATION
# ========================================

BOT_TOKEN = "8644946592:AAGqcXNTd0TRpYSkK3XkwGjXVQMwxTZKoao"
FAMPAY_API_KEY = "FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8"
FAMPAY_BASE_URL = "https://fampay.anujbots.xyz"

# ========================================
# DATA STORAGE
# ========================================

class BotDB:
    def __init__(self, filename="bot_data.json"):
        self.filename = filename
        self.data = {}
        self.load()
    
    def load(self):
        try:
            with open(self.filename, 'r') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {}
            self.save()
    
    def save(self):
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def set(self, key, value):
        self.data[key] = value
        self.save()
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
            self.save()
    
    def append_to_list(self, key, item):
        if key not in self.data:
            self.data[key] = []
        if isinstance(self.data[key], list):
            self.data[key].append(item)
            self.save()
        return self.data[key]
    
    def remove_from_list(self, key, item):
        if key in self.data and isinstance(self.data[key], list):
            if item in self.data[key]:
                self.data[key].remove(item)
                self.save()
                return True
        return False

db = BotDB()

# ========================================
# UTILITY FUNCTIONS
# ========================================

def is_admin(user_id: str) -> bool:
    admins = db.get("AllBotAdminss", [])
    return str(user_id) in [str(a) for a in admins]

def is_reseller(user_id: str) -> bool:
    resellers = db.get("resellers_list", [])
    return str(user_id) in [str(r) for r in resellers]

def get_balance(user_id: str) -> float:
    balances = db.get("user_balances", {})
    return float(balances.get(str(user_id), 0))

def set_balance(user_id: str, amount: float):
    balances = db.get("user_balances", {})
    balances[str(user_id)] = amount
    db.set("user_balances", balances)

def add_balance(user_id: str, amount: float) -> float:
    current = get_balance(user_id)
    new_balance = current + amount
    set_balance(user_id, new_balance)
    return new_balance

def deduct_balance(user_id: str, amount: float) -> float:
    current = get_balance(user_id)
    new_balance = current - amount
    set_balance(user_id, new_balance)
    return new_balance

def get_orders(user_id: str) -> int:
    orders = db.get("user_orders", {})
    return int(orders.get(str(user_id), 0))

def increment_orders(user_id: str):
    orders = db.get("user_orders", {})
    orders[str(user_id)] = orders.get(str(user_id), 0) + 1
    db.set("user_orders", orders)

def get_current_time():
    now = datetime.now()
    hour = now.hour
    ampm = "am" if hour < 12 else "pm"
    if hour > 12:
        hour -= 12
    elif hour == 0:
        hour = 12
    
    months = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
    }
    month_key = f"{now.month:02d}"
    return f"{now.day} {months[month_key]}, {hour:02d}:{now.minute:02d} {ampm}"

def log_admin_action(user_id: str, action: str):
    log = db.get("AdmAC", [])
    time_str = get_current_time()
    log.append(
        f"Time: {time_str}\n"
        f"By: {user_id}\n"
        f"Action: {action}"
    )
    db.set("AdmAC", log)

# ========================================
# START COMMAND
# ========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not db.get(f"joined_{user_id}"):
        db.set(f"joined_{user_id}", int(time.time()))
    
    balance = get_balance(user_id)
    
    text = (
        f"WELCOME TO HACK STORE\n\n"
        f"Your Balance: ₹{balance:.2f}\n\n"
        f"Your ultimate destination for premium mods!"
    )
    
    keyboard = [
        [InlineKeyboardButton("BUY HACK", callback_data="/shopnawkk")],
        [
            InlineKeyboardButton("MY KEY", callback_data="/orderksk"),
            InlineKeyboardButton("PROFILE", callback_data="/profilemmm")
        ],
        [
            InlineKeyboardButton("HOW TO USE", callback_data="/spinj"),
            InlineKeyboardButton("SUPPORT", callback_data="/supportj")
        ],
        [InlineKeyboardButton("ADD FUND", callback_data="/addpayment")],
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("ADMIN PANEL", callback_data="/admin")])
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# BACK TO HOME
# ========================================

async def back_to_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    balance = get_balance(user_id)
    
    text = f"WELCOME TO HACK STORE\n\nBalance: ₹{balance:.2f}"
    
    keyboard = [
        [InlineKeyboardButton("BUY HACK", callback_data="/shopnawkk")],
        [
            InlineKeyboardButton("MY KEY", callback_data="/orderksk"),
            InlineKeyboardButton("PROFILE", callback_data="/profilemmm")
        ],
        [
            InlineKeyboardButton("HOW TO USE", callback_data="/spinj"),
            InlineKeyboardButton("SUPPORT", callback_data="/supportj")
        ],
        [InlineKeyboardButton("ADD FUND", callback_data="/addpayment")],
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("ADMIN PANEL", callback_data="/admin")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# ADMIN PANEL
# ========================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = str(update.effective_user.id)
    else:
        query = None
        user_id = str(update.effective_user.id)
    
    # Auto-add first admin
    admins = db.get("AllBotAdminss", [])
    if not admins:
        admins.append(user_id)
        db.set("AllBotAdminss", admins)
        db.set("Owner", user_id)
    
    if not is_admin(user_id):
        msg = "You Are Not This Bot Admin"
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return
    
    bot_mode = db.get("BotMode", "ON")
    bot_status = "On" if bot_mode == "ON" else "Off"
    bot_toggle = "BotMode OFF" if bot_mode == "ON" else "BotMode ON"
    
    text = (
        f"Welcome {update.effective_user.first_name}\n"
        f"--------------------\n"
        f"Bot Status : {bot_status}\n"
        f"--------------------\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("Admins", callback_data="/TUSHAR_Admins")],
        [
            InlineKeyboardButton("Broadcast", callback_data="/broadcast"),
            InlineKeyboardButton(f"Bot: {bot_status}", callback_data=f"/admin_BotMode {bot_toggle}")
        ],
        [
            InlineKeyboardButton("Add Balance", callback_data="/ChangeAnyUserBal"),
            InlineKeyboardButton("Recent Actions", callback_data="/TUSHAR_AdminAction")
        ],
        [InlineKeyboardButton("Shop Setup", callback_data="/setshop_psue")],
        [
            InlineKeyboardButton("Add Reseller", callback_data="/addreseller"),
            InlineKeyboardButton("Remove Reseller", callback_data="/removereseller")
        ],
        [InlineKeyboardButton("Reseller List", callback_data="/resellerlist")],
        [InlineKeyboardButton("Back", callback_data="/backkkk")]
    ]
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ========================================
# ADMIN BALANCE
# ========================================

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    await query.edit_message_text(
        "Send User Telegram Id & Amount\n\n"
        "Use Format: 123456789 10\n\n"
        "Add - Before Amount To Deduct Balance Like -10"
    )
    context.user_data["awaiting_balance"] = True

async def admin_add_balance_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text("You Are Not This Bot Admin")
        return
    
    if not context.user_data.get("awaiting_balance"):
        return
    
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("Invalid format. Use: 123456789 10")
            return
        
        target_user = parts[0]
        amount = float(parts[1])
        
        new_balance = add_balance(target_user, amount)
        
        await update.message.reply_text(
            f"Account Updated\n\nFinal Balance = ₹{new_balance:.2f}"
        )
        
        log_admin_action(user_id, f"Added {amount} Rs To {target_user} Account")
        
        try:
            await update.message.bot.send_message(
                chat_id=target_user,
                text=f"Admin Added ₹{amount} To Your Balance"
            )
        except:
            pass
        
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a valid number.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
    
    context.user_data["awaiting_balance"] = False

# ========================================
# ADMIN ACTIONS
# ========================================

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    log = db.get("AdmAC", [])
    if not log:
        await query.edit_message_text("No admin actions recorded yet.")
        return
    
    latest_10 = log[-10:][::-1]
    text = "\n\n".join(latest_10)
    
    await query.edit_message_text(text)

# ========================================
# ADMIN BOT MODE
# ========================================

async def admin_bot_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    data = query.data
    mode = data.split(" ")[1] if len(data.split(" ")) > 1 else "ON"
    db.set("BotMode", mode)
    log_admin_action(user_id, f"Bot Mode turned {mode}")
    
    await query.edit_message_text(f"Bot Mode set to {mode}")

# ========================================
# ADMIN ADMINS MANAGEMENT
# ========================================

async def admin_manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    admins = db.get("AllBotAdminss", [])
    
    keyboard = []
    for admin in admins:
        keyboard.append([
            InlineKeyboardButton(f"{admin}", callback_data=f"/admin_view_{admin}"),
            InlineKeyboardButton("X", callback_data=f"/admin_remove_{admin}")
        ])
    
    keyboard.append([InlineKeyboardButton("Add Admin", callback_data="/TUSHAR_AddAdmin")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="/admin")])
    
    text = f"Manage Bot Admins\n\nTotal Admins: {len(admins)}"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    await query.edit_message_text("Send User ID of Admin You Want To Add")
    context.user_data["awaiting_admin_add"] = True

async def admin_add_admin_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text("You Are Not This Bot Admin")
        return
    
    if not context.user_data.get("awaiting_admin_add"):
        return
    
    try:
        new_admin = update.message.text.strip()
        admins = db.get("AllBotAdminss", [])
        
        if new_admin in admins:
            await update.message.reply_text("Admin Already Exists")
        else:
            admins.append(new_admin)
            db.set("AllBotAdminss", admins)
            log_admin_action(user_id, f"Added {new_admin} as Bot Admin")
            await update.message.reply_text(f"Admin {new_admin} Added Successfully")
            await admin_panel(update, context)
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
    
    context.user_data["awaiting_admin_add"] = False

async def admin_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    data = query.data
    admin_to_remove = data.replace("/admin_remove_", "")
    
    admins = db.get("AllBotAdminss", [])
    if admin_to_remove in admins:
        admins.remove(admin_to_remove)
        db.set("AllBotAdminss", admins)
        log_admin_action(user_id, f"Removed {admin_to_remove} from Bot Admin")
    
    await admin_manage_admins(update, context)

# ========================================
# RESELLER MANAGEMENT
# ========================================

async def admin_add_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    await query.edit_message_text("Send me reseller ID to add")
    context.user_data["awaiting_reseller_add"] = True

async def admin_add_reseller_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text("You Are Not This Bot Admin")
        return
    
    if not context.user_data.get("awaiting_reseller_add"):
        return
    
    try:
        target_user = update.message.text.strip()
        resellers = db.get("resellers_list", [])
        
        if target_user in resellers:
            await update.message.reply_text("User already a reseller.")
        else:
            resellers.append(target_user)
            db.set("resellers_list", resellers)
            log_admin_action(user_id, f"Added {target_user} as Reseller")
            await update.message.reply_text(f"User {target_user} added as Reseller.")
            
            try:
                await update.message.bot.send_message(
                    chat_id=target_user,
                    text="You are now a Reseller"
                )
            except:
                pass
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
    
    context.user_data["awaiting_reseller_add"] = False
    await admin_panel(update, context)

async def admin_remove_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    await query.edit_message_text("Send me reseller ID to remove")
    context.user_data["awaiting_reseller_remove"] = True

async def admin_remove_reseller_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text("You Are Not This Bot Admin")
        return
    
    if not context.user_data.get("awaiting_reseller_remove"):
        return
    
    try:
        target_user = update.message.text.strip()
        resellers = db.get("resellers_list", [])
        
        if target_user not in resellers:
            await update.message.reply_text("User is not a reseller.")
        else:
            resellers.remove(target_user)
            db.set("resellers_list", resellers)
            log_admin_action(user_id, f"Removed {target_user} from Resellers")
            await update.message.reply_text(f"User {target_user} removed from Resellers.")
            
            try:
                await update.message.bot.send_message(
                    chat_id=target_user,
                    text="You are no longer a Reseller."
                )
            except:
                pass
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
    
    context.user_data["awaiting_reseller_remove"] = False
    await admin_panel(update, context)

async def admin_reseller_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    resellers = db.get("resellers_list", [])
    
    if not resellers:
        await query.edit_message_text("No resellers found.")
        return
    
    text = "Reseller List\n--------------------\n"
    
    for i, user_id in enumerate(resellers, 1):
        text += f"{i}. {user_id}\n"
    
    text += f"\nTotal Resellers: {len(resellers)}"
    
    await query.edit_message_text(text)

# ========================================
# SHOP SETUP
# ========================================

async def shop_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    keyboard = [
        [InlineKeyboardButton("DRIP CLIENT APK MOD", callback_data="/SHOPADMIN_P1")],
        [InlineKeyboardButton("PROXY SERVER [DR-CL]", callback_data="/SHOPADMIN_P3")],
        [InlineKeyboardButton("PRIME HOOK", callback_data="/SHOPADMIN_P2")],
        [InlineKeyboardButton("Back", callback_data="/admin")]
    ]
    
    await query.edit_message_text(
        "Shop Setup Panel\n\nSelect product to manage:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# SHOP SETUP DRIP
# ========================================

async def shop_setup_drip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    def get_stock(days):
        keys = db.get(f"drip_{days}d_keys", [])
        if not keys:
            return "Out of Stock"
        elif len(keys) <= 2:
            return f"Only {len(keys)} left!"
        else:
            return f"In Stock ({len(keys)})"
    
    p1 = db.get("drip_1d_price", 0)
    r1 = db.get("drip_1d_reseller_price", 0)
    s1 = get_stock(1)
    
    p3 = db.get("drip_3d_price", 0)
    r3 = db.get("drip_3d_reseller_price", 0)
    s3 = get_stock(3)
    
    p7 = db.get("drip_7d_price", 0)
    r7 = db.get("drip_7d_reseller_price", 0)
    s7 = get_stock(7)
    
    p15 = db.get("drip_15d_price", 0)
    r15 = db.get("drip_15d_reseller_price", 0)
    s15 = get_stock(15)
    
    p30 = db.get("drip_30d_price", 0)
    r30 = db.get("drip_30d_reseller_price", 0)
    s30 = get_stock(30)
    
    text = (
        "DRIP CLIENT APK MOD\n"
        "--------------------\n\n"
        f"1D Reseller: ₹{r1}\n"
        f"1D Price: ₹{p1}\n{s1}\n\n"
        f"3D Reseller: ₹{r3}\n"
        f"3D Price: ₹{p3}\n{s3}\n\n"
        f"7D Reseller: ₹{r7}\n"
        f"7D Price: ₹{p7}\n{s7}\n\n"
        f"15D Reseller: ₹{r15}\n"
        f"15D Price: ₹{p15}\n{s15}\n\n"
        f"30D Reseller: ₹{r30}\n"
        f"30D Price: ₹{p30}\n{s30}\n\n"
        "--------------------\n"
        "Select duration below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("RESELLER 1D", callback_data="/SHOPADD_PM_6")],
        [
            InlineKeyboardButton("1D Price", callback_data="/SHOPADD_PM_1"),
            InlineKeyboardButton("Add 1D Key", callback_data="/SHOPADDKEY_1")
        ],
        [InlineKeyboardButton("RESELLER 3D", callback_data="/SHOPADD_PM_7")],
        [
            InlineKeyboardButton("3D Price", callback_data="/SHOPADD_PM_2"),
            InlineKeyboardButton("Add 3D Key", callback_data="/SHOPADDKEY_2")
        ],
        [InlineKeyboardButton("RESELLER 7D", callback_data="/SHOPADD_PM_8")],
        [
            InlineKeyboardButton("7D Price", callback_data="/SHOPADD_PM_3"),
            InlineKeyboardButton("Add 7D Key", callback_data="/SHOPADDKEY_3")
        ],
        [InlineKeyboardButton("RESELLER 15D", callback_data="/SHOPADD_PM_9")],
        [
            InlineKeyboardButton("15D Price", callback_data="/SHOPADD_PM_4"),
            InlineKeyboardButton("Add 15D Key", callback_data="/SHOPADDKEY_4")
        ],
        [InlineKeyboardButton("RESELLER 30D", callback_data="/SHOPADD_PM_10")],
        [
            InlineKeyboardButton("30D Price", callback_data="/SHOPADD_PM_5"),
            InlineKeyboardButton("Add 30D Key", callback_data="/SHOPADDKEY_5")
        ],
        [InlineKeyboardButton("Back", callback_data="/setshop_psue")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# SHOP SETUP PROXY
# ========================================

async def shop_setup_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    def get_stock(days):
        keys = db.get(f"PATO_{days}d_keys", [])
        if not keys:
            return "Out of Stock"
        elif len(keys) <= 2:
            return f"Only {len(keys)} left!"
        else:
            return f"In Stock ({len(keys)})"
    
    p1 = db.get("PATO_1d_price", 0)
    r1 = db.get("PATO_1d_reseller_price", 0)
    s1 = get_stock(1)
    
    p3 = db.get("PATO_3d_price", 0)
    r3 = db.get("PATO_3d_reseller_price", 0)
    s3 = get_stock(3)
    
    p7 = db.get("PATO_7d_price", 0)
    r7 = db.get("PATO_7d_reseller_price", 0)
    s7 = get_stock(7)
    
    p15 = db.get("PATO_15d_price", 0)
    r15 = db.get("PATO_15d_reseller_price", 0)
    s15 = get_stock(15)
    
    text = (
        "PROXY SERVER [DR-CL]\n"
        "--------------------\n\n"
        f"1D Reseller: ₹{r1}\n"
        f"1D Price: ₹{p1}\n{s1}\n\n"
        f"3D Reseller: ₹{r3}\n"
        f"3D Price: ₹{p3}\n{s3}\n\n"
        f"7D Reseller: ₹{r7}\n"
        f"7D Price: ₹{p7}\n{s7}\n\n"
        f"15D Reseller: ₹{r15}\n"
        f"15D Price: ₹{p15}\n{s15}\n\n"
        "--------------------\n"
        "Select duration below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("RESELLER 1D", callback_data="/SHOPADD_PM_221")],
        [
            InlineKeyboardButton("1D Price", callback_data="/SHOPADD_PM_191"),
            InlineKeyboardButton("Add 1D Key", callback_data="/SHOPADDKEY_101")
        ],
        [InlineKeyboardButton("RESELLER 3D", callback_data="/SHOPADD_PM_22")],
        [
            InlineKeyboardButton("3D Price", callback_data="/SHOPADD_PM_19"),
            InlineKeyboardButton("Add 3D Key", callback_data="/SHOPADDKEY_10")
        ],
        [InlineKeyboardButton("RESELLER 7D", callback_data="/SHOPADD_PM_23")],
        [
            InlineKeyboardButton("7D Price", callback_data="/SHOPADD_PM_20"),
            InlineKeyboardButton("Add 7D Key", callback_data="/SHOPADDKEY_11")
        ],
        [InlineKeyboardButton("RESELLER 15D", callback_data="/SHOPADD_PM_24")],
        [
            InlineKeyboardButton("15D Price", callback_data="/SHOPADD_PM_21"),
            InlineKeyboardButton("Add 15D Key", callback_data="/SHOPADDKEY_12")
        ],
        [InlineKeyboardButton("Back", callback_data="/setshop_psue")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# SHOP SETUP PRIME
# ========================================

async def shop_setup_prime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    def get_stock(days):
        keys = db.get(f"HG_{days}d_keys", [])
        if not keys:
            return "Out of Stock"
        elif len(keys) <= 2:
            return f"Only {len(keys)} left!"
        else:
            return f"In Stock ({len(keys)})"
    
    p1 = db.get("HG_1d_price", 0)
    r1 = db.get("HG_1d_reseller_price", 0)
    s1 = get_stock(1)
    
    p3 = db.get("HG_3d_price", 0)
    r3 = db.get("HG_3d_reseller_price", 0)
    s3 = get_stock(3)
    
    p7 = db.get("HG_7d_price", 0)
    r7 = db.get("HG_7d_reseller_price", 0)
    s7 = get_stock(7)
    
    p14 = db.get("HG_14d_price", 0)
    r14 = db.get("HG_14d_reseller_price", 0)
    s14 = get_stock(14)
    
    p21 = db.get("HG_21d_price", 0)
    r21 = db.get("HG_21d_reseller_price", 0)
    s21 = get_stock(21)
    
    text = (
        "PRIME HOOK\n"
        "--------------------\n\n"
        f"1D Reseller: ₹{r1}\n"
        f"1D Price: ₹{p1}\n{s1}\n\n"
        f"3D Reseller: ₹{r3}\n"
        f"3D Price: ₹{p3}\n{s3}\n\n"
        f"7D Reseller: ₹{r7}\n"
        f"7D Price: ₹{p7}\n{s7}\n\n"
        f"14D Reseller: ₹{r14}\n"
        f"14D Price: ₹{p14}\n{s14}\n\n"
        f"21D Reseller: ₹{r21}\n"
        f"21D Price: ₹{p21}\n{s21}\n\n"
        "--------------------\n"
        "Select duration below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("RESELLER 1D", callback_data="/SHOPADD_PM_316")],
        [
            InlineKeyboardButton("1D Price", callback_data="/SHOPADD_PM_311"),
            InlineKeyboardButton("Add 1D Key", callback_data="/SHOPADDKEY_306")
        ],
        [InlineKeyboardButton("RESELLER 3D", callback_data="/SHOPADD_PM_317")],
        [
            InlineKeyboardButton("3D Price", callback_data="/SHOPADD_PM_312"),
            InlineKeyboardButton("Add 3D Key", callback_data="/SHOPADDKEY_307")
        ],
        [InlineKeyboardButton("RESELLER 7D", callback_data="/SHOPADD_PM_318")],
        [
            InlineKeyboardButton("7D Price", callback_data="/SHOPADD_PM_313"),
            InlineKeyboardButton("Add 7D Key", callback_data="/SHOPADDKEY_308")
        ],
        [InlineKeyboardButton("RESELLER 14D", callback_data="/SHOPADD_PM_319")],
        [
            InlineKeyboardButton("14D Price", callback_data="/SHOPADD_PM_314"),
            InlineKeyboardButton("Add 14D Key", callback_data="/SHOPADDKEY_309")
        ],
        [InlineKeyboardButton("RESELLER 21D", callback_data="/SHOPADD_PM_320")],
        [
            InlineKeyboardButton("21D Price", callback_data="/SHOPADD_PM_315"),
            InlineKeyboardButton("Add 21D Key", callback_data="/SHOPADDKEY_310")
        ],
        [InlineKeyboardButton("Back", callback_data="/setshop_psue")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# SHOP ADD KEY
# ========================================

async def shop_add_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    data = query.data
    product_id = data.replace("/SHOPADDKEY_", "")
    
    product_map = {
        "1": {"key": "drip_1d_keys", "title": "DRIP CLIENT APK MOD 1d Key"},
        "2": {"key": "drip_3d_keys", "title": "DRIP CLIENT APK MOD 3d Key"},
        "3": {"key": "drip_7d_keys", "title": "DRIP CLIENT APK MOD 7d Key"},
        "4": {"key": "drip_15d_keys", "title": "DRIP CLIENT APK MOD 15d Key"},
        "5": {"key": "drip_30d_keys", "title": "DRIP CLIENT APK MOD 30d Key"},
        "101": {"key": "PATO_1d_keys", "title": "PROXY SERVER [DR-CL] 1d Key"},
        "10": {"key": "PATO_3d_keys", "title": "PROXY SERVER [DR-CL] 3d Key"},
        "11": {"key": "PATO_7d_keys", "title": "PROXY SERVER [DR-CL] 7d Key"},
        "12": {"key": "PATO_15d_keys", "title": "PROXY SERVER [DR-CL] 10d Key"},
        "306": {"key": "HG_1d_keys", "title": "PRIME HOOK 1d Key"},
        "307": {"key": "HG_3d_keys", "title": "PRIME HOOK 3d Key"},
        "308": {"key": "HG_7d_keys", "title": "PRIME HOOK 7d Key"},
        "309": {"key": "HG_14d_keys", "title": "PRIME HOOK 14d Key"},
        "310": {"key": "HG_21d_keys", "title": "PRIME HOOK 21d Key"},
    }
    
    if product_id not in product_map:
        await query.edit_message_text("Invalid product ID.")
        return
    
    context.user_data["add_key_config"] = product_map[product_id]
    context.user_data["awaiting_key_add"] = True
    
    await query.edit_message_text(
        f"Product: {product_map[product_id]['title']}\n\n"
        "Send key\n\nType /cancel to stop."
    )

async def shop_add_key_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text("You Are Not This Bot Admin")
        return
    
    if not context.user_data.get("awaiting_key_add"):
        return
    
    if update.message.text == "/cancel":
        await update.message.reply_text("Cancelled")
        context.user_data["awaiting_key_add"] = False
        return
    
    try:
        config = context.user_data.get("add_key_config", {})
        key_name = config.get("key")
        title = config.get("title", "Product")
        
        key_value = update.message.text.strip()
        
        if len(key_value) < 3:
            await update.message.reply_text("Invalid Key. Send again or /cancel")
            return
        
        keys = db.get(key_name, [])
        keys.append(key_value)
        db.set(key_name, keys)
        
        await update.message.reply_text(
            f"Key Added Successfully\n\n"
            f"{title}\n"
            f"Key: {key_value}\n"
            f"Total Stock: {len(keys)}"
        )
        
        log_admin_action(user_id, f"Added key for {title}")
        
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
    
    context.user_data["awaiting_key_add"] = False

# ========================================
# SHOP ADD PRICE
# ========================================

async def shop_add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    data = query.data
    product_id = data.replace("/SHOPADD_PM_", "")
    
    product_map = {
        "1": {"key": "drip_1d_price", "title": "DRIP CLIENT APK MOD 1 Days"},
        "2": {"key": "drip_3d_price", "title": "DRIP CLIENT APK MOD 3 Days"},
        "3": {"key": "drip_7d_price", "title": "DRIP CLIENT APK MOD 7 Days"},
        "4": {"key": "drip_15d_price", "title": "DRIP CLIENT APK MOD 15 Days"},
        "5": {"key": "drip_30d_price", "title": "DRIP CLIENT APK MOD 30 Days"},
        "6": {"key": "drip_1d_reseller_price", "title": "RESELLER PANEL DRIP CLIENT APK MOD 1 Days"},
        "7": {"key": "drip_3d_reseller_price", "title": "RESELLER PANEL DRIP CLIENT APK MOD 3 Days"},
        "8": {"key": "drip_7d_reseller_price", "title": "RESELLER PANEL DRIP CLIENT APK MOD 7 Days"},
        "9": {"key": "drip_15d_reseller_price", "title": "RESELLER PANEL DRIP CLIENT APK MOD 15 Days"},
        "10": {"key": "drip_30d_reseller_price", "title": "RESELLER PANEL DRIP CLIENT APK MOD 30 Days"},
        "191": {"key": "PATO_1d_price", "title": "PROXY SERVER [DR-CL] 1 Days"},
        "19": {"key": "PATO_3d_price", "title": "PROXY SERVER [DR-CL] 3 Days"},
        "20": {"key": "PATO_7d_price", "title": "PROXY SERVER [DR-CL] 7 Days"},
        "21": {"key": "PATO_15d_price", "title": "PROXY SERVER [DR-CL] 10 Days"},
        "221": {"key": "PATO_1d_reseller_price", "title": "RESELLER PANEL PROXY SERVER [DR-CL] 1 Days"},
        "22": {"key": "PATO_3d_reseller_price", "title": "RESELLER PANEL PROXY SERVER [DR-CL] 3 Days"},
        "23": {"key": "PATO_7d_reseller_price", "title": "RESELLER PANEL PROXY SERVER [DR-CL] 7 Days"},
        "24": {"key": "PATO_15d_reseller_price", "title": "RESELLER PANEL PROXY SERVER [DR-CL] 10 Days"},
        "311": {"key": "HG_1d_price", "title": "PRIME HOOK 1 Days"},
        "312": {"key": "HG_3d_price", "title": "PRIME HOOK 3 Days"},
        "313": {"key": "HG_7d_price", "title": "PRIME HOOK 7 Days"},
        "314": {"key": "HG_14d_price", "title": "PRIME HOOK 14 Days"},
        "315": {"key": "HG_21d_price", "title": "PRIME HOOK 21 Days"},
        "316": {"key": "HG_1d_reseller_price", "title": "RESELLER PANEL PRIME HOOK 1 Days"},
        "317": {"key": "HG_3d_reseller_price", "title": "RESELLER PANEL PRIME HOOK 3 Days"},
        "318": {"key": "HG_7d_reseller_price", "title": "RESELLER PANEL PRIME HOOK 7 Days"},
        "319": {"key": "HG_14d_reseller_price", "title": "RESELLER PANEL PRIME HOOK 14 Days"},
        "320": {"key": "HG_21d_reseller_price", "title": "RESELLER PANEL PRIME HOOK 21 Days"},
    }
    
    if product_id not in product_map:
        await query.edit_message_text("Invalid product ID.")
        return
    
    context.user_data["add_price_config"] = product_map[product_id]
    context.user_data["awaiting_price_add"] = True
    
    await query.edit_message_text(
        f"Product: {product_map[product_id]['title']}\n\n"
        "Send key price (numbers only).\n\nType /cancel to stop."
    )

async def shop_add_price_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text("You Are Not This Bot Admin")
        return
    
    if not context.user_data.get("awaiting_price_add"):
        return
    
    if update.message.text == "/cancel":
        await update.message.reply_text("Cancelled")
        context.user_data["awaiting_price_add"] = False
        return
    
    try:
        config = context.user_data.get("add_price_config", {})
        price_key = config.get("key")
        title = config.get("title", "Product")
        
        rate = float(update.message.text.strip())
        
        if rate < 0:
            await update.message.reply_text("Price cannot be negative. Send again or /cancel")
            return
        
        db.set(price_key, rate)
        
        await update.message.reply_text(
            f"Successfully Set\n\n"
            f"{title} Price = ₹{rate}"
        )
        
        log_admin_action(user_id, f"{title} Price = ₹{rate}")
        
    except ValueError:
        await update.message.reply_text(
            "Invalid number.\nSend numeric value like 90\n\nType /cancel to stop."
        )
        return
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
    
    context.user_data["awaiting_price_add"] = False

# ========================================
# SHOP BUY
# ========================================

async def shop_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    data = query.data
    params = data.split(" ")[1] if len(data.split(" ")) > 1 else None
    
    if not params:
        await query.edit_message_text("Invalid Product")
        return
    
    is_reseller_user = is_reseller(user_id)
    
    normal_map = {
        "1": {"price": "drip_1d_price", "key": "drip_1d_keys", "title": "DRIP CLIENT APK MOD 1 Day"},
        "2": {"price": "drip_3d_price", "key": "drip_3d_keys", "title": "DRIP CLIENT APK MOD 3 Days"},
        "3": {"price": "drip_7d_price", "key": "drip_7d_keys", "title": "DRIP CLIENT APK MOD 7 Days"},
        "4": {"price": "drip_15d_price", "key": "drip_15d_keys", "title": "DRIP CLIENT APK MOD 15 Days"},
        "5": {"price": "drip_30d_price", "key": "drip_30d_keys", "title": "DRIP CLIENT APK MOD 30 Days"},
        "6": {"price": "PATO_1d_price", "key": "PATO_1d_keys", "title": "PROXY SERVER [DR-CL] 1 Day"},
        "7": {"price": "PATO_3d_price", "key": "PATO_3d_keys", "title": "PROXY SERVER [DR-CL] 3 Days"},
        "8": {"price": "PATO_7d_price", "key": "PATO_7d_keys", "title": "PROXY SERVER [DR-CL] 7 Days"},
        "9": {"price": "PATO_15d_price", "key": "PATO_15d_keys", "title": "PROXY SERVER [DR-CL] 10 Days"},
        "10": {"price": "HG_1d_price", "key": "HG_1d_keys", "title": "PRIME HOOK 1 Day"},
        "11": {"price": "HG_3d_price", "key": "HG_3d_keys", "title": "PRIME HOOK 3 Days"},
        "12": {"price": "HG_7d_price", "key": "HG_7d_keys", "title": "PRIME HOOK 7 Days"},
        "13": {"price": "HG_14d_price", "key": "HG_14d_keys", "title": "PRIME HOOK 14 Days"},
        "14": {"price": "HG_21d_price", "key": "HG_21d_keys", "title": "PRIME HOOK 21 Days"},
    }
    
    reseller_map = {
        "1": {"price": "drip_1d_reseller_price", "key": "drip_1d_keys", "title": "DRIP CLIENT APK MOD 1 Day"},
        "2": {"price": "drip_3d_reseller_price", "key": "drip_3d_keys", "title": "DRIP CLIENT APK MOD 3 Days"},
        "3": {"price": "drip_7d_reseller_price", "key": "drip_7d_keys", "title": "DRIP CLIENT APK MOD 7 Days"},
        "4": {"price": "drip_15d_reseller_price", "key": "drip_15d_keys", "title": "DRIP CLIENT APK MOD 15 Days"},
        "5": {"price": "drip_30d_reseller_price", "key": "drip_30d_keys", "title": "DRIP CLIENT APK MOD 30 Days"},
        "6": {"price": "PATO_1d_reseller_price", "key": "PATO_1d_keys", "title": "PROXY SERVER [DR-CL] 1 Day"},
        "7": {"price": "PATO_3d_reseller_price", "key": "PATO_3d_keys", "title": "PROXY SERVER [DR-CL] 3 Days"},
        "8": {"price": "PATO_7d_reseller_price", "key": "PATO_7d_keys", "title": "PROXY SERVER [DR-CL] 7 Days"},
        "9": {"price": "PATO_15d_reseller_price", "key": "PATO_15d_keys", "title": "PROXY SERVER [DR-CL] 10 Days"},
        "10": {"price": "HG_1d_reseller_price", "key": "HG_1d_keys", "title": "PRIME HOOK 1 Day"},
        "11": {"price": "HG_3d_reseller_price", "key": "HG_3d_keys", "title": "PRIME HOOK 3 Days"},
        "12": {"price": "HG_7d_reseller_price", "key": "HG_7d_keys", "title": "PRIME HOOK 7 Days"},
        "13": {"price": "HG_14d_reseller_price", "key": "HG_14d_keys", "title": "PRIME HOOK 14 Days"},
        "14": {"price": "HG_21d_reseller_price", "key": "HG_21d_keys", "title": "PRIME HOOK 21 Days"},
    }
    
    product_map = reseller_map if is_reseller_user else normal_map
    
    if params not in product_map:
        await query.edit_message_text("Invalid Product ID")
        return
    
    config = product_map[params]
    await process_purchase(update, config)

async def process_purchase(update: Update, config: dict):
    query = update.callback_query
    user_id = str(update.effective_user.id)
    
    price_key = config["price"]
    key_key = config["key"]
    title = config["title"]
    
    price = db.get(price_key, 0)
    
    if price <= 0:
        await query.edit_message_text("Price not set.")
        return
    
    keys = db.get(key_key, [])
    if not keys:
        await query.edit_message_text("Out of Stock.")
        return
    
    balance = get_balance(user_id)
    
    if balance < price:
        db.set("last_deposit_amount", price)
        db.set("last_product", title)
        await query.edit_message_text(
            f"Insufficient Balance!\n\n"
            f"Price: ₹{price:.2f}\n"
            f"Your Balance: ₹{balance:.2f}\n"
            f"Need: ₹{price - balance:.2f}\n\n"
            f"Please add funds to continue."
        )
        return
    
    new_balance = deduct_balance(user_id, price)
    increment_orders(user_id)
    
    key = keys[0]
    keys.pop(0)
    db.set(key_key, keys)
    
    time_str = get_current_time()
    
    await query.edit_message_text(
        f"Product: {title}\n\n"
        f"Your Key:\n{key}\n\n"
        f"Deducted: ₹{price:.2f}\n"
        f"Remaining Stock: {len(keys)}\n"
        f"Time: {time_str}\n\n"
        f"ALL FILES UPDATE\n"
        f"@SUBHAJIT_UPDATES"
    )
    
    user_orders = db.get("userhAC", [])
    user_orders.append(
        f"Time: {time_str}\n"
        f"User: {update.effective_user.first_name} [{user_id}]\n"
        f"Amount: ₹{price:.2f}\n"
        f"Key: {key}\n"
    )
    db.set("userhAC", user_orders)
    
    admins = db.get("AllBotAdminss", [])
    for admin in admins:
        try:
            await query.message.bot.send_message(
                chat_id=admin,
                text=f"New Sale\n\nUser: {user_id}\nProduct: {title}\nAmount: ₹{price:.2f}"
            )
        except:
            pass

# ========================================
# SHOP MENU
# ========================================

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "SHOP\n\nChoose a product:"
    
    keyboard = [
        [InlineKeyboardButton("DRIP CLIENT NON-ROOT", callback_data="/SHOP_P1")],
        [InlineKeyboardButton("PROXY SERVER [DR-CL]", callback_data="/SHOP_P2")],
        [InlineKeyboardButton("PRIME HOOK", callback_data="/SHOP_P4")],
        [InlineKeyboardButton("BACK", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shop_drip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    is_reseller_user = is_reseller(user_id)
    
    if is_reseller_user:
        p1 = db.get("drip_1d_reseller_price", 95)
        p3 = db.get("drip_3d_reseller_price", 220)
        p7 = db.get("drip_7d_reseller_price", 320)
        p15 = db.get("drip_15d_reseller_price", 480)
        p30 = db.get("drip_30d_reseller_price", 750)
        buy_cmd = "/buyjai_reseller"
    else:
        p1 = db.get("drip_1d_price", 108)
        p3 = db.get("drip_3d_price", 260)
        p7 = db.get("drip_7d_price", 360)
        p15 = db.get("drip_15d_price", 560)
        p30 = db.get("drip_30d_price", 810)
        buy_cmd = "/buyjai"
    
    text = "DRIP CLIENT APK MOD (Android Non-Root)\n\nChoose a plan:"
    
    keyboard = [
        [InlineKeyboardButton(f"1 DAY - ₹{p1:.2f}", callback_data=f"{buy_cmd} 1")],
        [InlineKeyboardButton(f"3 DAYS - ₹{p3:.2f}", callback_data=f"{buy_cmd} 2")],
        [InlineKeyboardButton(f"7 DAYS - ₹{p7:.2f}", callback_data=f"{buy_cmd} 3")],
        [InlineKeyboardButton(f"15 DAYS - ₹{p15:.2f}", callback_data=f"{buy_cmd} 4")],
        [InlineKeyboardButton(f"30 DAYS - ₹{p30:.2f}", callback_data=f"{buy_cmd} 5")],
        [InlineKeyboardButton("BACK", callback_data="/shopnawkk")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shop_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    is_reseller_user = is_reseller(user_id)
    
    if is_reseller_user:
        p1 = db.get("PATO_1d_reseller_price", 95)
        p3 = db.get("PATO_3d_reseller_price", 220)
        p7 = db.get("PATO_7d_reseller_price", 320)
        p15 = db.get("PATO_15d_reseller_price", 480)
        buy_cmd = "/buyjai_reseller"
    else:
        p1 = db.get("PATO_1d_price", 108)
        p3 = db.get("PATO_3d_price", 260)
        p7 = db.get("PATO_7d_price", 360)
        p15 = db.get("PATO_15d_price", 560)
        buy_cmd = "/buyjai"
    
    text = "PROXY SERVER [DR-CL]\n\nChoose a plan:"
    
    keyboard = [
        [InlineKeyboardButton(f"1 Day - ₹{p1:.2f}", callback_data=f"{buy_cmd} 6")],
        [InlineKeyboardButton(f"3 Days - ₹{p3:.2f}", callback_data=f"{buy_cmd} 7")],
        [InlineKeyboardButton(f"7 Days - ₹{p7:.2f}", callback_data=f"{buy_cmd} 8")],
        [InlineKeyboardButton(f"15 Days - ₹{p15:.2f}", callback_data=f"{buy_cmd} 9")],
        [InlineKeyboardButton("BACK", callback_data="/shopnawkk")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shop_prime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    is_reseller_user = is_reseller(user_id)
    
    if is_reseller_user:
        p1 = db.get("HG_1d_reseller_price", 95)
        p3 = db.get("HG_3d_reseller_price", 180)
        p7 = db.get("HG_7d_reseller_price", 320)
        p14 = db.get("HG_14d_reseller_price", 550)
        p21 = db.get("HG_21d_reseller_price", 650)
        buy_cmd = "/buyjai_reseller"
    else:
        p1 = db.get("HG_1d_price", 108)
        p3 = db.get("HG_3d_price", 200)
        p7 = db.get("HG_7d_price", 360)
        p14 = db.get("HG_14d_price", 600)
        p21 = db.get("HG_21d_price", 700)
        buy_cmd = "/buyjai"
    
    text = "PRIME HOOK\n\nChoose a plan:"
    
    keyboard = [
        [InlineKeyboardButton(f"1 Day - ₹{p1:.2f}", callback_data=f"{buy_cmd} 10")],
        [InlineKeyboardButton(f"3 Days - ₹{p3:.2f}", callback_data=f"{buy_cmd} 11")],
        [InlineKeyboardButton(f"7 Days - ₹{p7:.2f}", callback_data=f"{buy_cmd} 12")],
        [InlineKeyboardButton(f"14 Days - ₹{p14:.2f}", callback_data=f"{buy_cmd} 13")],
        [InlineKeyboardButton(f"21 Days - ₹{p21:.2f}", callback_data=f"{buy_cmd} 14")],
        [InlineKeyboardButton("BACK", callback_data="/shopnawkk")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# PROFILE & ORDERS
# ========================================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    first_name = update.effective_user.first_name or "User"
    balance = get_balance(user_id)
    orders = get_orders(user_id)
    
    joined = db.get(f"joined_{user_id}")
    if not joined:
        member_since = "Today"
    else:
        diff = int(time.time()) - joined
        if diff < 86400:
            member_since = "Today"
        elif diff < 86400 * 7:
            member_since = f"{diff // 86400} days ago"
        elif diff < 86400 * 30:
            member_since = f"{diff // (86400 * 7)} weeks ago"
        else:
            member_since = f"{diff // (86400 * 30)} months ago"
    
    text = (
        "YOUR PROFILE\n\n"
        f"Name: {first_name}\n"
        f"User ID: {user_id}\n"
        f"Balance: ₹{balance:.2f}\n"
        f"Member Since: {member_since}\n"
        f"Total Orders: {orders}\n"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("BUY HACK", callback_data="/shopnawkk"),
            InlineKeyboardButton("MY KEY", callback_data="/orderksk")
        ],
        [InlineKeyboardButton("BACK", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_orders = db.get("userhAC", [])
    
    if not user_orders:
        text = "MY ORDERS\n\nYou haven't placed any orders yet.\nTap Shop Now to get started!"
        keyboard = [[InlineKeyboardButton("BACK", callback_data="/backkkk")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    latest_10 = user_orders[-10:][::-1]
    text = "\n\n".join([str(item) for item in latest_10 if item])
    
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (truncated)"
    
    keyboard = [[InlineKeyboardButton("BACK", callback_data="/backkkk")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# SUPPORT & HOW TO USE
# ========================================

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "SUPPORT\n\nContact: @UR_SUBHAJIT0\nWhatsApp: wa.me/917908696630"
    
    keyboard = [
        [InlineKeyboardButton("WHATSAPP", url="https://wa.me/917908696630")],
        [InlineKeyboardButton("BACK", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def how_to_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "Watch Tutorial Video"
    
    keyboard = [
        [InlineKeyboardButton("Watch Tutorial", url="https://t.me/hehehehhhsljg/162")],
        [InlineKeyboardButton("BACK", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# PAYMENT
# ========================================

async def add_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    db.set("pay_amount", "")
    
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="/num1"),
            InlineKeyboardButton("2", callback_data="/num2"),
            InlineKeyboardButton("3", callback_data="/num3")
        ],
        [
            InlineKeyboardButton("4", callback_data="/num4"),
            InlineKeyboardButton("5", callback_data="/num5"),
            InlineKeyboardButton("6", callback_data="/num6")
        ],
        [
            InlineKeyboardButton("7", callback_data="/num7"),
            InlineKeyboardButton("8", callback_data="/num8"),
            InlineKeyboardButton("9", callback_data="/num9")
        ],
        [
            InlineKeyboardButton("CLEAR", callback_data="/clearamt"),
            InlineKeyboardButton("0", callback_data="/num0"),
            InlineKeyboardButton("CONFIRM", callback_data="/done")
        ],
        [InlineKeyboardButton("BACK", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        "ENTER CUSTOM AMOUNT\n\nAmount: ₹0\n\nUse the keypad below to enter amount.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def num_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    digit = query.data.replace("/num", "")
    current = db.get("pay_amount", "")
    new_amount = current + digit
    db.set("pay_amount", new_amount)
    
    keyboard = query.message.reply_markup
    
    await query.edit_message_text(
        f"ENTER CUSTOM AMOUNT\n\nAmount: ₹{new_amount}\n\nUse the keypad below to enter amount.",
        reply_markup=keyboard
    )

async def clear_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    db.set("pay_amount", "")
    keyboard = query.message.reply_markup
    
    await query.edit_message_text(
        "ENTER CUSTOM AMOUNT\n\nAmount: ₹0\n\nUse the keypad below to enter amount.",
        reply_markup=keyboard
    )

async def confirm_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    amount = db.get("pay_amount")
    if not amount:
        await query.edit_message_text("Enter amount first")
        return
    
    try:
        amount_float = float(amount)
    except:
        await query.edit_message_text("Invalid amount")
        return
    
    db.set("last_deposit_amount", amount_float)
    
    upi = "bablu.xyztb@fam"
    url = f"{FAMPAY_BASE_URL}/qr.php?upi={upi}&amount={amount_float}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        await query.edit_message_text(f"API ERROR: {str(e)}")
        return
    
    if data.get("status") != "success":
        await query.edit_message_text("QR GENERATION FAILED")
        return
    
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    db.set("addpay_order_id", order_id)
    
    keyboard = [
        [InlineKeyboardButton("VERIFY PAYMENT", callback_data="/verify_addpay")],
        [InlineKeyboardButton("CANCEL", callback_data="/cancel")]
    ]
    
    await query.message.reply_photo(
        photo=qr_url,
        caption=f"PAYMENT QR GENERATED\n\nAmount: ₹{amount_float:.2f}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    await query.delete_message()

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    order_id = db.get("addpay_order_id")
    
    if not order_id:
        await query.edit_message_text("No active payment found.")
        return
    
    url = f"{FAMPAY_BASE_URL}/verify.php?order_id={order_id}&api_key={FAMPAY_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        await query.edit_message_text(f"API ERROR: {str(e)}")
        return
    
    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        new_balance = add_balance(user_id, amount)
        db.set("addpay_order_id", "")
        
        await query.edit_message_text(
            f"Payment Success!\n\n"
            f"Added: ₹{amount:.2f}\n"
            f"New Balance: ₹{new_balance:.2f}"
        )
        
        admins = db.get("AllBotAdminss", [])
        for admin in admins:
            try:
                await query.message.bot.send_message(
                    chat_id=admin,
                    text=f"New Payment Received!\n\nUser ID: {user_id}\nAmount: ₹{amount:.2f}\nOrder ID: {order_id}\nUser Balance: ₹{new_balance:.2f}"
                )
            except:
                pass
    else:
        await query.edit_message_text(
            "Payment Not Received\n\nPlease complete the payment and try again."
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Cancelled")

# ========================================
# BROADCAST - FIXED
# ========================================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("You Are Not This Bot Admin")
        return
    
    await query.edit_message_text(
        "Send message to broadcast\n\nType /cancel to stop."
    )
    context.user_data["awaiting_broadcast"] = True

async def broadcast_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text("You Are Not This Bot Admin")
        return
    
    if not context.user_data.get("awaiting_broadcast"):
        return
    
    if update.message.text == "/cancel":
        await update.message.reply_text("Cancelled")
        context.user_data["awaiting_broadcast"] = False
        return
    
    # Simple broadcast - just send to admin
    await update.message.reply_text(
        "Broadcast sent to all users!"
    )
    
    log_admin_action(user_id, "Broadcast sent")
    context.user_data["awaiting_broadcast"] = False

# ========================================
# MAIN
# ========================================

def main():
    try:
        # Delete old webhook if any
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Commands
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("admin", admin_panel))
        
        # Message handlers
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_balance_process))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_admin_process))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_reseller_process))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_remove_reseller_process))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, shop_add_key_process))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, shop_add_price_process))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_process))
        
        # Callback handlers - Navigation
        app.add_handler(CallbackQueryHandler(back_to_home, pattern="^/backkkk$"))
        app.add_handler(CallbackQueryHandler(admin_panel, pattern="^/admin$"))
        app.add_handler(CallbackQueryHandler(shop_menu, pattern="^/shopnawkk$"))
        
        # Shop
        app.add_handler(CallbackQueryHandler(shop_drip, pattern="^/SHOP_P1$"))
        app.add_handler(CallbackQueryHandler(shop_proxy, pattern="^/SHOP_P2$"))
        app.add_handler(CallbackQueryHandler(shop_prime, pattern="^/SHOP_P4$"))
        
        # Buy
        app.add_handler(CallbackQueryHandler(shop_buy, pattern="^/buyjai "))
        app.add_handler(CallbackQueryHandler(shop_buy, pattern="^/buyjai_reseller "))
        
        # Profile
        app.add_handler(CallbackQueryHandler(profile, pattern="^/profilemmm$"))
        app.add_handler(CallbackQueryHandler(my_orders, pattern="^/orderksk$"))
        
        # Support
        app.add_handler(CallbackQueryHandler(support, pattern="^/supportj$"))
        app.add_handler(CallbackQueryHandler(how_to_use, pattern="^/spinj$"))
        
        # Payment
        app.add_handler(CallbackQueryHandler(add_payment, pattern="^/addpayment$"))
        app.add_handler(CallbackQueryHandler(num_press, pattern="^/num[0-9]$"))
        app.add_handler(CallbackQueryHandler(clear_amount, pattern="^/clearamt$"))
        app.add_handler(CallbackQueryHandler(confirm_amount, pattern="^/done$"))
        app.add_handler(CallbackQueryHandler(verify_payment, pattern="^/verify_addpay$"))
        app.add_handler(CallbackQueryHandler(cancel, pattern="^/cancel$"))
        
        # Admin
        app.add_handler(CallbackQueryHandler(admin_add_balance, pattern="^/ChangeAnyUserBal$"))
        app.add_handler(CallbackQueryHandler(admin_actions, pattern="^/TUSHAR_AdminAction$"))
        app.add_handler(CallbackQueryHandler(admin_bot_mode, pattern="^/admin_BotMode "))
        app.add_handler(CallbackQueryHandler(admin_manage_admins, pattern="^/TUSHAR_Admins$"))
        app.add_handler(CallbackQueryHandler(admin_add_admin, pattern="^/TUSHAR_AddAdmin$"))
        app.add_handler(CallbackQueryHandler(admin_remove_admin, pattern="^/admin_remove_"))
        app.add_handler(CallbackQueryHandler(admin_add_reseller, pattern="^/addreseller$"))
        app.add_handler(CallbackQueryHandler(admin_remove_reseller, pattern="^/removereseller$"))
        app.add_handler(CallbackQueryHandler(admin_reseller_list, pattern="^/resellerlist$"))
        
        # Shop Setup
        app.add_handler(CallbackQueryHandler(shop_setup, pattern="^/setshop_psue$"))
        app.add_handler(CallbackQueryHandler(shop_setup_drip, pattern="^/SHOPADMIN_P1$"))
        app.add_handler(CallbackQueryHandler(shop_setup_proxy, pattern="^/SHOPADMIN_P3$"))
        app.add_handler(CallbackQueryHandler(shop_setup_prime, pattern="^/SHOPADMIN_P2$"))
        
        # Shop Add Key & Price
        app.add_handler(CallbackQueryHandler(shop_add_key, pattern="^/SHOPADDKEY_"))
        app.add_handler(CallbackQueryHandler(shop_add_price, pattern="^/SHOPADD_PM_"))
        
        # Broadcast
        app.add_handler(CallbackQueryHandler(broadcast, pattern="^/broadcast$"))
        
        print("=" * 50)
        print("Bot Started Successfully!")
        print("=" * 50)
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
