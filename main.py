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

def get_joined_date(user_id: str):
    joined = db.get("user_joined", {})
    return joined.get(str(user_id))

def set_joined_date(user_id: str, date: int):
    joined = db.get("user_joined", {})
    joined[str(user_id)] = date
    db.set("user_joined", joined)

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
        f"<b>ðŸ“† Time:</b> {time_str}\n"
        f"ðŸ‘¥ <b>Action:</b> {action}\n"
        f"ðŸ”<b> By:</b> <code>{user_id}</code>"
    )
    db.set("AdmAC", log)

# ========================================
# START COMMAND
# ========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not get_joined_date(user_id):
        set_joined_date(user_id, int(time.time()))
    
    first_name = update.effective_user.first_name or "User"
    balance = get_balance(user_id)
    
    text = (
        "<b>ðŸ‘‹ WELCOME TO HACK STORE</b>\n\n"
        f"ðŸ’° Your Balance: â‚¹{balance:.2f}\n\n"
        "Your ultimate destination for premium mods, cheats & clients!"
    )
    
    keyboard = [
        [InlineKeyboardButton("ðŸ›’ BUY HACK", callback_data="/shopnawkk")],
        [
            InlineKeyboardButton("ðŸ“¦ MY KEY", callback_data="/orderksk"),
            InlineKeyboardButton("ðŸ‘¤ PROFILE", callback_data="/profilemmm")
        ],
        [
            InlineKeyboardButton("ðŸ“– HOW TO USE", callback_data="/spinj"),
            InlineKeyboardButton("ðŸ’¬ SUPPORT", callback_data="/supportj")
        ],
        [InlineKeyboardButton("ðŸ’° ADD FUND", callback_data="/addpayment")],
        [
            InlineKeyboardButton("ðŸ“¤ PAY PROOF", url="https://t.me/subhajit_feedback"),
            InlineKeyboardButton("ðŸ“² DOWNLOAD APK", url="https://t.me/+hasTLSVjzaZjZGVl")
        ]
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("âš™ï¸ ADMIN PANEL", callback_data="/admin")])
    
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
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
    
    text = (
        "<b>ðŸ‘‹ WELCOME TO HACK STORE</b>\n\n"
        f"ðŸ’° Your Balance: â‚¹{balance:.2f}"
    )
    
    keyboard = [
        [InlineKeyboardButton("ðŸ›’ BUY HACK", callback_data="/shopnawkk")],
        [
            InlineKeyboardButton("ðŸ“¦ MY KEY", callback_data="/orderksk"),
            InlineKeyboardButton("ðŸ‘¤ PROFILE", callback_data="/profilemmm")
        ],
        [
            InlineKeyboardButton("ðŸ“– HOW TO USE", callback_data="/spinj"),
            InlineKeyboardButton("ðŸ’¬ SUPPORT", callback_data="/supportj")
        ],
        [InlineKeyboardButton("ðŸ’° ADD FUND", callback_data="/addpayment")],
        [
            InlineKeyboardButton("ðŸ“¤ PAY PROOF", url="https://t.me/subhajit_feedback"),
            InlineKeyboardButton("ðŸ“² DOWNLOAD APK", url="https://t.me/+hasTLSVjzaZjZGVl")
        ]
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("âš™ï¸ ADMIN PANEL", callback_data="/admin")])
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
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
        msg = "<b><i>ðŸš« You Are Not This Bot Admin</i></b>"
        if query:
            await query.edit_message_text(msg, parse_mode="html")
        else:
            await update.message.reply_text(msg, parse_mode="html")
        return
    
    bot_mode = db.get("BotMode", "ON")
    bot_status = "ðŸŸ¢ On" if bot_mode == "ON" else "ðŸ”´ Off"
    bot_toggle = "BotMode OFF" if bot_mode == "ON" else "BotMode ON"
    
    text = (
        f"<b>ðŸ‘‹ Welcome {update.effective_user.first_name} ðŸŽ‰</b>\n\n"
        f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        f"ðŸ¤– Bot Status : {bot_status}\n"
        f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("ðŸ‘‘ Manage Admins", callback_data="/TUSHAR_Admins")],
        [
            InlineKeyboardButton("ðŸ“£ Broadcast", callback_data="/broadcast"),
            InlineKeyboardButton(f"ðŸ¤– Bot: {bot_status}", callback_data=f"/admin_BotMode {bot_toggle}")
        ],
        [
            InlineKeyboardButton("ðŸ’° Add Balance", callback_data="/ChangeAnyUserBal"),
            InlineKeyboardButton("ðŸ“ Recent Actions", callback_data="/TUSHAR_AdminAction")
        ],
        [InlineKeyboardButton("ðŸ“Š Shop Setup", callback_data="/setshop_psue")],
        [
            InlineKeyboardButton("ðŸ’° Add Reseller", callback_data="/addreseller"),
            InlineKeyboardButton("â›” Remove Reseller", callback_data="/removereseller")
        ],
        [InlineKeyboardButton("ðŸ“ Reseller List", callback_data="/resellerlist")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="/backkkk")]
    ]
    
    if query:
        await query.edit_message_text(
            text,
            parse_mode="html",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode="html",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ========================================
# ADMIN ADD BALANCE
# ========================================

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    await query.edit_message_text(
        "<b>ðŸ’¡ Send User Telegram Id & Amount\n\nâš ï¸ Use Format: <code>123456789 10</code>\n\nAdd - Before Amount To Deduct Balance Like -10</b>",
        parse_mode="html"
    )
    context.user_data["awaiting_balance"] = True

async def admin_add_balance_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    if not context.user_data.get("awaiting_balance"):
        return
    
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text(
                "âŒ Invalid format. Use: <code>123456789 10</code>",
                parse_mode="html"
            )
            return
        
        target_user = parts[0]
        amount = float(parts[1])
        
        new_balance = add_balance(target_user, amount)
        
        await update.message.reply_text(
            f"<b>ðŸ’´ Account Updated\n\nðŸ’° Final Balance = â‚¹{new_balance:.2f}</b>",
            parse_mode="html"
        )
        
        log_admin_action(user_id, f"Added {amount} Rs To {target_user} Account")
        
        try:
            await update.message.bot.send_message(
                chat_id=target_user,
                text=f"<b>ðŸ’° Admin Added â‚¹{amount} To Your Balance</b>",
                parse_mode="html"
            )
        except:
            pass
        
    except ValueError:
        await update.message.reply_text(
            "âŒ Invalid amount. Please enter a valid number.",
            parse_mode="html"
        )
    except Exception as e:
        await update.message.reply_text(f"âŒ Error: {str(e)}")
    
    context.user_data["awaiting_balance"] = False

# ========================================
# ADMIN ACTIONS
# ========================================

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    log = db.get("AdmAC", [])
    if not log:
        await query.edit_message_text("No admin actions recorded yet.")
        return
    
    latest_10 = log[-10:][::-1]
    text = "\n\n".join(latest_10)
    
    await query.edit_message_text(
        text,
        parse_mode="html"
    )

# ========================================
# ADMIN BOT MODE
# ========================================

async def admin_bot_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    data = query.data
    mode = data.split(" ")[1] if len(data.split(" ")) > 1 else "ON"
    db.set("BotMode", mode)
    log_admin_action(user_id, f"Bot Mode turned {mode}")
    
    await query.edit_message_text(
        f"<b>âœ… Bot Mode set to {mode}</b>",
        parse_mode="html"
    )

# ========================================
# ADMIN ADMINS MANAGEMENT
# ========================================

async def admin_manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    admins = db.get("AllBotAdminss", [])
    
    keyboard = []
    for admin in admins:
        keyboard.append([
            InlineKeyboardButton(f"ðŸ‘¤ {admin}", callback_data=f"/admin_view_{admin}"),
            InlineKeyboardButton("âŒ", callback_data=f"/admin_remove_{admin}")
        ])
    
    keyboard.append([InlineKeyboardButton("âž• Add Admin", callback_data="/TUSHAR_AddAdmin")])
    keyboard.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="/admin")])
    
    text = "<b>ðŸ‘‘ Manage Bot Admins</b>\n\nTotal Admins: " + str(len(admins))
    
    await query.edit_message_text(
        text,
        parse_mode="html",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    await query.edit_message_text(
        "<b>ðŸ’¡ Send User ID of Admin You Want To Add</b>",
        parse_mode="html"
    )
    context.user_data["awaiting_admin_add"] = True

async def admin_add_admin_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    if not context.user_data.get("awaiting_admin_add"):
        return
    
    try:
        new_admin = update.message.text.strip()
        admins = db.get("AllBotAdminss", [])
        
        if new_admin in admins:
            await update.message.reply_text("âš ï¸ Admin Already Exists")
        else:
            admins.append(new_admin)
            db.set("AllBotAdminss", admins)
            log_admin_action(user_id, f"Added {new_admin} as Bot Admin")
            await update.message.reply_text(f"âœ… Admin {new_admin} Added Successfully")
    except Exception as e:
        await update.message.reply_text(f"âŒ Error: {str(e)}")
    
    context.user_data["awaiting_admin_add"] = False
    await admin_panel(update, context)

async def admin_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
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
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    await query.edit_message_text(
        "ðŸ“© Send me reseller ID to add",
        parse_mode="html"
    )
    context.user_data["awaiting_reseller_add"] = True

async def admin_add_reseller_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    if not context.user_data.get("awaiting_reseller_add"):
        return
    
    try:
        target_user = update.message.text.strip()
        resellers = db.get("resellers_list", [])
        
        if target_user in resellers:
            await update.message.reply_text("âš ï¸ User already a reseller.")
        else:
            resellers.append(target_user)
            db.set("resellers_list", resellers)
            log_admin_action(user_id, f"Added {target_user} as Reseller")
            await update.message.reply_text(f"âœ… User <code>{target_user}</code> added as Reseller.", parse_mode="html")
            
            try:
                await update.message.bot.send_message(
                    chat_id=target_user,
                    text="ðŸŽ‰ You are now a Reseller ðŸ‘‘"
                )
            except:
                pass
    except Exception as e:
        await update.message.reply_text(f"âŒ Error: {str(e)}")
    
    context.user_data["awaiting_reseller_add"] = False
    await admin_panel(update, context)

async def admin_remove_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    await query.edit_message_text(
        "ðŸ“© Send me reseller ID to remove",
        parse_mode="html"
    )
    context.user_data["awaiting_reseller_remove"] = True

async def admin_remove_reseller_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    if not context.user_data.get("awaiting_reseller_remove"):
        return
    
    try:
        target_user = update.message.text.strip()
        resellers = db.get("resellers_list", [])
        
        if target_user not in resellers:
            await update.message.reply_text("âš ï¸ User is not a reseller.")
        else:
            resellers.remove(target_user)
            db.set("resellers_list", resellers)
            log_admin_action(user_id, f"Removed {target_user} from Resellers")
            await update.message.reply_text(f"âœ… User <code>{target_user}</code> removed from Resellers.", parse_mode="html")
            
            try:
                await update.message.bot.send_message(
                    chat_id=target_user,
                    text="âŒ You are no longer a Reseller."
                )
            except:
                pass
    except Exception as e:
        await update.message.reply_text(f"âŒ Error: {str(e)}")
    
    context.user_data["awaiting_reseller_remove"] = False
    await admin_panel(update, context)

async def admin_reseller_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    resellers = db.get("resellers_list", [])
    
    if not resellers:
        await query.edit_message_text("ðŸ“­ No resellers found.")
        return
    
    text = "ðŸ‘‘ <b>Reseller List</b>\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n\n"
    
    for i, user_id in enumerate(resellers, 1):
        text += f"{i}. ðŸ†” <code>{user_id}</code>\n"
    
    text += f"\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
    text += f"\nðŸ“Š Total Resellers: {len(resellers)}"
    
    await query.edit_message_text(text, parse_mode="html")

# ========================================
# SHOP SETUP
# ========================================

async def shop_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("ðŸ›’ DRIP CLIENT APK MOD", callback_data="/SHOPADMIN_P1")],
        [InlineKeyboardButton("ðŸ›’ PROXY SERVER [DR-CL]", callback_data="/SHOPADMIN_P3")],
        [InlineKeyboardButton("ðŸ›’ PRIME HOOK", callback_data="/SHOPADMIN_P2")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="/admin")]
    ]
    
    await query.edit_message_text(
        "<b>ðŸ“Š Shop Setup Panel</b>\n\nSelect product to manage:",
        parse_mode="html",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shop_setup_drip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    def get_stock(days):
        keys = db.get(f"drip_{days}d_keys", [])
        if not keys:
            return "âŒ Out of Stock"
        elif len(keys) <= 2:
            return f"âš ï¸ Only {len(keys)} left!"
        else:
            return f"âœ… In Stock ({len(keys)})"
    
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
        "ðŸŽ® ðŸ›’ DRIP CLIENT APK MOD\n"
        "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n\n"
        f"ðŸ‘‘ 1D Reseller: â‚¹{r1}\n"
        f"ðŸ’° 1D Price: â‚¹{p1}\nðŸ“¦ {s1}\n\n"
        f"ðŸ‘‘ 3D Reseller: â‚¹{r3}\n"
        f"ðŸ’° 3D Price: â‚¹{p3}\nðŸ“¦ {s3}\n\n"
        f"ðŸ‘‘ 7D Reseller: â‚¹{r7}\n"
        f"ðŸ’° 7D Price: â‚¹{p7}\nðŸ“¦ {s7}\n\n"
        f"ðŸ‘‘ 15D Reseller: â‚¹{r15}\n"
        f"ðŸ’° 15D Price: â‚¹{p15}\nðŸ“¦ {s15}\n\n"
        f"ðŸ‘‘ 30D Reseller: â‚¹{r30}\n"
        f"ðŸ’° 30D Price: â‚¹{p30}\nðŸ“¦ {s30}\n\n"
        "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        "ðŸ‘‡ Select duration below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 1D", callback_data="/SHOPADD_PM 6")],
        [
            InlineKeyboardButton("1D Price", callback_data="/SHOPADD_PM 1"),
            InlineKeyboardButton("Add 1D Key", callback_data="/SHOPADDKEY 1")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 3D", callback_data="/SHOPADD_PM 7")],
        [
            InlineKeyboardButton("3D Price", callback_data="/SHOPADD_PM 2"),
            InlineKeyboardButton("Add 3D Key", callback_data="/SHOPADDKEY 2")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 7D", callback_data="/SHOPADD_PM 8")],
        [
            InlineKeyboardButton("7D Price", callback_data="/SHOPADD_PM 3"),
            InlineKeyboardButton("Add 7D Key", callback_data="/SHOPADDKEY 3")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 15D", callback_data="/SHOPADD_PM 9")],
        [
            InlineKeyboardButton("15D Price", callback_data="/SHOPADD_PM 4"),
            InlineKeyboardButton("Add 15D Key", callback_data="/SHOPADDKEY 4")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 30D", callback_data="/SHOPADD_PM 10")],
        [
            InlineKeyboardButton("30D Price", callback_data="/SHOPADD_PM 5"),
            InlineKeyboardButton("Add 30D Key", callback_data="/SHOPADDKEY 5")
        ],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="/setshop_psue")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="html",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shop_setup_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    def get_stock(days):
        keys = db.get(f"PATO_{days}d_keys", [])
        if not keys:
            return "âŒ Out of Stock"
        elif len(keys) <= 2:
            return f"âš ï¸ Only {len(keys)} left!"
        else:
            return f"âœ… In Stock ({len(keys)})"
    
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
        "ðŸŽ® PROXY SERVER [DR-CL]\n"
        "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n\n"
        f"ðŸ‘‘ 1D Reseller: â‚¹{r1}\n"
        f"ðŸ’° 1D Price: â‚¹{p1}\nðŸ“¦ {s1}\n\n"
        f"ðŸ‘‘ 3D Reseller: â‚¹{r3}\n"
        f"ðŸ’° 3D Price: â‚¹{p3}\nðŸ“¦ {s3}\n\n"
        f"ðŸ‘‘ 7D Reseller: â‚¹{r7}\n"
        f"ðŸ’° 7D Price: â‚¹{p7}\nðŸ“¦ {s7}\n\n"
        f"ðŸ‘‘ 15D Reseller: â‚¹{r15}\n"
        f"ðŸ’° 15D Price: â‚¹{p15}\nðŸ“¦ {s15}\n\n"
        "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        "ðŸ‘‡ Select duration below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 1D", callback_data="/SHOPADD_PM 221")],
        [
            InlineKeyboardButton("1D Price", callback_data="/SHOPADD_PM 191"),
            InlineKeyboardButton("Add 1D Key", callback_data="/SHOPADDKEY 101")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 3D", callback_data="/SHOPADD_PM 22")],
        [
            InlineKeyboardButton("3D Price", callback_data="/SHOPADD_PM 19"),
            InlineKeyboardButton("Add 3D Key", callback_data="/SHOPADDKEY 10")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 7D", callback_data="/SHOPADD_PM 23")],
        [
            InlineKeyboardButton("7D Price", callback_data="/SHOPADD_PM 20"),
            InlineKeyboardButton("Add 7D Key", callback_data="/SHOPADDKEY 11")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 15D", callback_data="/SHOPADD_PM 24")],
        [
            InlineKeyboardButton("15D Price", callback_data="/SHOPADD_PM 21"),
            InlineKeyboardButton("Add 15D Key", callback_data="/SHOPADDKEY 12")
        ],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="/setshop_psue")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="html",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shop_setup_prime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    def get_stock(days):
        keys = db.get(f"HG_{days}d_keys", [])
        if not keys:
            return "âŒ Out of Stock"
        elif len(keys) <= 2:
            return f"âš ï¸ Only {len(keys)} left!"
        else:
            return f"âœ… In Stock ({len(keys)})"
    
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
        "ðŸ“¦ PRIME HOOK\n"
        "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n\n"
        f"ðŸ‘‘ 1D Reseller: â‚¹{r1}\n"
        f"ðŸ’° 1D Price: â‚¹{p1}\nðŸ“¦ {s1}\n\n"
        f"ðŸ‘‘ 3D Reseller: â‚¹{r3}\n"
        f"ðŸ’° 3D Price: â‚¹{p3}\nðŸ“¦ {s3}\n\n"
        f"ðŸ‘‘ 7D Reseller: â‚¹{r7}\n"
        f"ðŸ’° 7D Price: â‚¹{p7}\nðŸ“¦ {s7}\n\n"
        f"ðŸ‘‘ 14D Reseller: â‚¹{r14}\n"
        f"ðŸ’° 14D Price: â‚¹{p14}\nðŸ“¦ {s14}\n\n"
        f"ðŸ‘‘ 21D Reseller: â‚¹{r21}\n"
        f"ðŸ’° 21D Price: â‚¹{p21}\nðŸ“¦ {s21}\n\n"
        "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        "ðŸ‘‡ Select duration below:"
    )
    
    keyboard = [
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 1D", callback_data="/SHOPADD_PM 316")],
        [
            InlineKeyboardButton("1D Price", callback_data="/SHOPADD_PM 311"),
            InlineKeyboardButton("Add 1D Key", callback_data="/SHOPADDKEY 306")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 3D", callback_data="/SHOPADD_PM 317")],
        [
            InlineKeyboardButton("3D Price", callback_data="/SHOPADD_PM 312"),
            InlineKeyboardButton("Add 3D Key", callback_data="/SHOPADDKEY 307")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 7D", callback_data="/SHOPADD_PM 318")],
        [
            InlineKeyboardButton("7D Price", callback_data="/SHOPADD_PM 313"),
            InlineKeyboardButton("Add 7D Key", callback_data="/SHOPADDKEY 308")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 14D", callback_data="/SHOPADD_PM 319")],
        [
            InlineKeyboardButton("14D Price", callback_data="/SHOPADD_PM 314"),
            InlineKeyboardButton("Add 14D Key", callback_data="/SHOPADDKEY 309")
        ],
        [InlineKeyboardButton("ðŸ‘‘ RESELLER 21D", callback_data="/SHOPADD_PM 320")],
        [
            InlineKeyboardButton("21D Price", callback_data="/SHOPADD_PM 315"),
            InlineKeyboardButton("Add 21D Key", callback_data="/SHOPADDKEY 310")
        ],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="/setshop_psue")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="html",
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
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    data = query.data
    product_id = data.replace("/SHOPADDKEY ", "") if " " in data else data.replace("/SHOPADDKEY", "")
    
    product_map = {
        "1": {"key": "drip_1d_keys", "title": "DRIP CLIENT APK MOD\n1d Key"},
        "2": {"key": "drip_3d_keys", "title": "DRIP CLIENT APK MOD\n3d Key"},
        "3": {"key": "drip_7d_keys", "title": "DRIP CLIENT APK MOD\n7d Key"},
        "4": {"key": "drip_15d_keys", "title": "DRIP CLIENT APK MOD\n15d Key"},
        "5": {"key": "drip_30d_keys", "title": "DRIP CLIENT APK MOD\n30d Key"},
        "101": {"key": "PATO_1d_keys", "title": "PROXY SERVER [DR-CL]\n1d Key"},
        "10": {"key": "PATO_3d_keys", "title": "PROXY SERVER [DR-CL]\n3d Key"},
        "11": {"key": "PATO_7d_keys", "title": "PROXY SERVER [DR-CL]\n7d Key"},
        "12": {"key": "PATO_15d_keys", "title": "PROXY SERVER [DR-CL]\n10d Key"},
        "306": {"key": "HG_1d_keys", "title": "PRIME HOOK\n1d Key"},
        "307": {"key": "HG_3d_keys", "title": "PRIME HOOK\n3d Key"},
        "308": {"key": "HG_7d_keys", "title": "PRIME HOOK\n7d Key"},
        "309": {"key": "HG_14d_keys", "title": "PRIME HOOK\n14d Key"},
        "310": {"key": "HG_21d_keys", "title": "PRIME HOOK\n21d Key"},
    }
    
    if product_id not in product_map:
        await query.edit_message_text("âŒ Invalid product ID.")
        return
    
    context.user_data["add_key_config"] = product_map[product_id]
    context.user_data["awaiting_key_add"] = True
    
    await query.edit_message_text(
        f"ðŸ›’ <b>{product_map[product_id]['title']}</b>\n\n"
        "Send key\n\nType /cancel to stop.",
        parse_mode="html"
    )

async def shop_add_key_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    if not context.user_data.get("awaiting_key_add"):
        return
    
    if update.message.text == "/cancel":
        await update.message.reply_text("<b>âŒ Cancelled</b>", parse_mode="html")
        context.user_data["awaiting_key_add"] = False
        return
    
    try:
        config = context.user_data.get("add_key_config", {})
        key_name = config.get("key")
        title = config.get("title", "Product")
        
        key_value = update.message.text.strip()
        
        if len(key_value) < 3:
            await update.message.reply_text("âŒ Invalid Key. Send again or /cancel")
            return
        
        keys = db.get(key_name, [])
        keys.append(key_value)
        db.set(key_name, keys)
        
        await update.message.reply_text(
            f"âœ… <b>Key Added Successfully</b>\n\n"
            f"{title}\n"
            f"ðŸ”‘ <code>{key_value}</code>\n"
            f"ðŸ“¦ Total Stock: {len(keys)}",
            parse_mode="html"
        )
        
        log_admin_action(user_id, f"Added key for {title}")
        
    except Exception as e:
        await update.message.reply_text(f"âŒ Error: {str(e)}")
    
    context.user_data["awaiting_key_add"] = False

# ========================================
# SHOP ADD PRICE
# ========================================

async def shop_add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    data = query.data
    product_id = data.replace("/SHOPADD_PM ", "") if " " in data else data.replace("/SHOPADD_PM", "")
    
    product_map = {
        "1": {"key": "drip_1d_price", "title": "DRIP CLIENT APK MOD\n1 Days"},
        "2": {"key": "drip_3d_price", "title": "DRIP CLIENT APK MOD\n3 Days"},
        "3": {"key": "drip_7d_price", "title": "DRIP CLIENT APK MOD\n7 Days"},
        "4": {"key": "drip_15d_price", "title": "DRIP CLIENT APK MOD\n15 Days"},
        "5": {"key": "drip_30d_price", "title": "DRIP CLIENT APK MOD\n30 Days"},
        "6": {"key": "drip_1d_reseller_price", "title": "RESELLER PANEL\nDRIP CLIENT APK MOD\n1 Days"},
        "7": {"key": "drip_3d_reseller_price", "title": "RESELLER PANEL\nDRIP CLIENT APK MOD\n3 Days"},
        "8": {"key": "drip_7d_reseller_price", "title": "RESELLER PANEL\nDRIP CLIENT APK MOD\n7 Days"},
        "9": {"key": "drip_15d_reseller_price", "title": "RESELLER PANEL\nDRIP CLIENT APK MOD\n15 Days"},
        "10": {"key": "drip_30d_reseller_price", "title": "RESELLER PANEL\nDRIP CLIENT APK MOD\n30 Days"},
        "191": {"key": "PATO_1d_price", "title": "PROXY SERVER [DR-CL]\n1 Days"},
        "19": {"key": "PATO_3d_price", "title": "PROXY SERVER [DR-CL]\n3 Days"},
        "20": {"key": "PATO_7d_price", "title": "PROXY SERVER [DR-CL]\n7 Days"},
        "21": {"key": "PATO_15d_price", "title": "PROXY SERVER [DR-CL]\n10 Days"},
        "221": {"key": "PATO_1d_reseller_price", "title": "RESELLER PANEL\nPROXY SERVER [DR-CL]\n1 Days"},
        "22": {"key": "PATO_3d_reseller_price", "title": "RESELLER PANEL\nPROXY SERVER [DR-CL]\n3 Days"},
        "23": {"key": "PATO_7d_reseller_price", "title": "RESELLER PANEL\nPROXY SERVER [DR-CL]\n7 Days"},
        "24": {"key": "PATO_15d_reseller_price", "title": "RESELLER PANEL\nPROXY SERVER [DR-CL]\n10 Days"},
        "311": {"key": "HG_1d_price", "title": "PRIME HOOK\n1 Days"},
        "312": {"key": "HG_3d_price", "title": "PRIME HOOK\n3 Days"},
        "313": {"key": "HG_7d_price", "title": "PRIME HOOK\n7 Days"},
        "314": {"key": "HG_14d_price", "title": "PRIME HOOK\n14 Days"},
        "315": {"key": "HG_21d_price", "title": "PRIME HOOK\n21 Days"},
        "316": {"key": "HG_1d_reseller_price", "title": "RESELLER PANEL\nPRIME HOOK\n1 Days"},
        "317": {"key": "HG_3d_reseller_price", "title": "RESELLER PANEL\nPRIME HOOK\n3 Days"},
        "318": {"key": "HG_7d_reseller_price", "title": "RESELLER PANEL\nPRIME HOOK\n7 Days"},
        "319": {"key": "HG_14d_reseller_price", "title": "RESELLER PANEL\nPRIME HOOK\n14 Days"},
        "320": {"key": "HG_21d_reseller_price", "title": "RESELLER PANEL\nPRIME HOOK\n21 Days"},
    }
    
    if product_id not in product_map:
        await query.edit_message_text("âŒ Invalid product ID.")
        return
    
    context.user_data["add_price_config"] = product_map[product_id]
    context.user_data["awaiting_price_add"] = True
    
    await query.edit_message_text(
        f"ðŸ›’ <b>{product_map[product_id]['title']}</b>\n\n"
        "Send key price (numbers only).\n\nType /cancel to stop.",
        parse_mode="html"
    )

async def shop_add_price_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    if not context.user_data.get("awaiting_price_add"):
        return
    
    if update.message.text == "/cancel":
        await update.message.reply_text("<b>âŒ Cancelled</b>", parse_mode="html")
        context.user_data["awaiting_price_add"] = False
        return
    
    try:
        config = context.user_data.get("add_price_config", {})
        price_key = config.get("key")
        title = config.get("title", "Product")
        
        rate = float(update.message.text.strip())
        
        if rate < 0:
            await update.message.reply_text("âŒ Price cannot be negative. Send again or /cancel")
            return
        
        db.set(price_key, rate)
        
        await update.message.reply_text(
            f"âœ… <b>Successfully Set</b>\n\n"
            f"{title} Price = â‚¹{rate}",
            parse_mode="html"
        )
        
        log_admin_action(user_id, f"{title} Price = â‚¹{rate}")
        
    except ValueError:
        await update.message.reply_text(
            "âŒ Invalid number.\nSend numeric value like 90\n\nType /cancel to stop."
        )
        return
    except Exception as e:
        await update.message.reply_text(f"âŒ Error: {str(e)}")
    
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
        await query.edit_message_text("âŒ Invalid Product")
        return
    
    is_reseller_user = is_reseller(user_id)
    
    normal_map = {
        "1": {"price": "drip_1d_price", "key": "drip_1d_keys", "title": "DRIP CLIENT APK MOD\n1 Day"},
        "2": {"price": "drip_3d_price", "key": "drip_3d_keys", "title": "DRIP CLIENT APK MOD\n3 Days"},
        "3": {"price": "drip_7d_price", "key": "drip_7d_keys", "title": "DRIP CLIENT APK MOD\n7 Days"},
        "4": {"price": "drip_15d_price", "key": "drip_15d_keys", "title": "DRIP CLIENT APK MOD\n15 Days"},
        "5": {"price": "drip_30d_price", "key": "drip_30d_keys", "title": "DRIP CLIENT APK MOD\n30 Days"},
        "6": {"price": "PATO_1d_price", "key": "PATO_1d_keys", "title": "PROXY SERVER [DR-CL]\n1 Day"},
        "7": {"price": "PATO_3d_price", "key": "PATO_3d_keys", "title": "PROXY SERVER [DR-CL]\n3 Days"},
        "8": {"price": "PATO_7d_price", "key": "PATO_7d_keys", "title": "PROXY SERVER [DR-CL]\n7 Days"},
        "9": {"price": "PATO_15d_price", "key": "PATO_15d_keys", "title": "PROXY SERVER [DR-CL]\n10 Days"},
        "10": {"price": "HG_1d_price", "key": "HG_1d_keys", "title": "PRIME HOOK\n1 Day"},
        "11": {"price": "HG_3d_price", "key": "HG_3d_keys", "title": "PRIME HOOK\n3 Days"},
        "12": {"price": "HG_7d_price", "key": "HG_7d_keys", "title": "PRIME HOOK\n7 Days"},
        "13": {"price": "HG_14d_price", "key": "HG_14d_keys", "title": "PRIME HOOK\n14 Days"},
        "14": {"price": "HG_21d_price", "key": "HG_21d_keys", "title": "PRIME HOOK\n21 Days"},
    }
    
    reseller_map = {
        "1": {"price": "drip_1d_reseller_price", "key": "drip_1d_keys", "title": "DRIP CLIENT APK MOD\n1 Day"},
        "2": {"price": "drip_3d_reseller_price", "key": "drip_3d_keys", "title": "DRIP CLIENT APK MOD\n3 Days"},
        "3": {"price": "drip_7d_reseller_price", "key": "drip_7d_keys", "title": "DRIP CLIENT APK MOD\n7 Days"},
        "4": {"price": "drip_15d_reseller_price", "key": "drip_15d_keys", "title": "DRIP CLIENT APK MOD\n15 Days"},
        "5": {"price": "drip_30d_reseller_price", "key": "drip_30d_keys", "title": "DRIP CLIENT APK MOD\n30 Days"},
        "6": {"price": "PATO_1d_reseller_price", "key": "PATO_1d_keys", "title": "PROXY SERVER [DR-CL]\n1 Day"},
        "7": {"price": "PATO_3d_reseller_price", "key": "PATO_3d_keys", "title": "PROXY SERVER [DR-CL]\n3 Days"},
        "8": {"price": "PATO_7d_reseller_price", "key": "PATO_7d_keys", "title": "PROXY SERVER [DR-CL]\n7 Days"},
        "9": {"price": "PATO_15d_reseller_price", "key": "PATO_15d_keys", "title": "PROXY SERVER [DR-CL]\n10 Days"},
        "10": {"price": "HG_1d_reseller_price", "key": "HG_1d_keys", "title": "PRIME HOOK\n1 Day"},
        "11": {"price": "HG_3d_reseller_price", "key": "HG_3d_keys", "title": "PRIME HOOK\n3 Days"},
        "12": {"price": "HG_7d_reseller_price", "key": "HG_7d_keys", "title": "PRIME HOOK\n7 Days"},
        "13": {"price": "HG_14d_reseller_price", "key": "HG_14d_keys", "title": "PRIME HOOK\n14 Days"},
        "14": {"price": "HG_21d_reseller_price", "key": "HG_21d_keys", "title": "PRIME HOOK\n21 Days"},
    }
    
    product_map = reseller_map if is_reseller_user else normal_map
    
    if params not in product_map:
        await query.edit_message_text("âŒ Invalid Product ID")
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
        await query.edit_message_text("âŒ Price not set.")
        return
    
    keys = db.get(key_key, [])
    if not keys:
        await query.edit_message_text("âŒ Out of Stock.")
        return
    
    balance = get_balance(user_id)
    
    if balance < price:
        db.set("last_deposit_amount", price)
        db.set("last_product", title)
        await query.edit_message_text(
            f"<b>âŒ Insufficient Balance!</b>\n\n"
            f"Price: â‚¹{price:.2f}\n"
            f"Your Balance: â‚¹{balance:.2f}\n"
            f"Need: â‚¹{price - balance:.2f}\n\n"
            f"Please add funds to continue.",
            parse_mode="HTML"
        )
        return
    
    new_balance = deduct_balance(user_id, price)
    increment_orders(user_id)
    
    key = keys[0]
    keys.pop(0)
    db.set(key_key, keys)
    
    time_str = get_current_time()
    
    await query.edit_message_text(
        f"ðŸ›’ {title}\n\n"
        f"<b>Your Key:</b>\n"
        f"<code>{key}</code>\n\n"
        f"ðŸ’° Deducted: â‚¹{price:.2f}\n"
        f"ðŸ“¦ Remaining Stock: {len(keys)}\n"
        f"ðŸ“¦ Time: {time_str}",
        parse_mode="HTML"
    )
    
    user_orders = db.get("userhAC", [])
    user_orders.append(
        f"ðŸ“† {time_str}\n"
        f"ðŸ‘¤ {update.effective_user.first_name} [{user_id}]\n"
        f"ðŸ’° â‚¹{price:.2f}\n"
        f"ðŸ”‘ {key}\n"
    )
    db.set("userhAC", user_orders)
    
    admins = db.get("AllBotAdminss", [])
    for admin in admins:
        try:
            await query.message.bot.send_message(
                chat_id=admin,
                text=f"ðŸ›’ New Sale\n\nðŸ‘¤ {user_id}\nðŸ“¦ {title}\nðŸ’° â‚¹{price:.2f}"
            )
        except:
            pass

# ========================================
# SHOP MENU
# ========================================

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "ðŸ›’ <b>SHOP</b>\n\nChoose a product:"
    
    keyboard = [
        [InlineKeyboardButton("ðŸ›’ DRIP CLIENT", callback_data="/SHOP_P1")],
        [InlineKeyboardButton("ðŸ›’ PROXY SERVER", callback_data="/SHOP_P2")],
        [InlineKeyboardButton("ðŸ”¥ PRIME HOOK", callback_data="/SHOP_P4")],
        [InlineKeyboardButton("ðŸ”™ BACK", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
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
    
    text = "DRIP CLIENT APK MOD\n\nChoose a plan:"
    
    keyboard = [
        [InlineKeyboardButton(f"1 DAY - â‚¹{p1:.2f}", callback_data=f"{buy_cmd} 1")],
        [InlineKeyboardButton(f"3 DAYS - â‚¹{p3:.2f}", callback_data=f"{buy_cmd} 2")],
        [InlineKeyboardButton(f"7 DAYS - â‚¹{p7:.2f}", callback_data=f"{buy_cmd} 3")],
        [InlineKeyboardButton(f"15 DAYS - â‚¹{p15:.2f}", callback_data=f"{buy_cmd} 4")],
        [InlineKeyboardButton(f"30 DAYS - â‚¹{p30:.2f}", callback_data=f"{buy_cmd} 5")],
        [InlineKeyboardButton("ðŸ”™ BACK", callback_data="/shopnawkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
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
        [InlineKeyboardButton(f"1 Day - â‚¹{p1:.2f}", callback_data=f"{buy_cmd} 6")],
        [InlineKeyboardButton(f"3 Days - â‚¹{p3:.2f}", callback_data=f"{buy_cmd} 7")],
        [InlineKeyboardButton(f"7 Days - â‚¹{p7:.2f}", callback_data=f"{buy_cmd} 8")],
        [InlineKeyboardButton(f"15 Days - â‚¹{p15:.2f}", callback_data=f"{buy_cmd} 9")],
        [InlineKeyboardButton("ðŸ”™ BACK", callback_data="/shopnawkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
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
        [InlineKeyboardButton(f"1 Day - â‚¹{p1:.2f}", callback_data=f"{buy_cmd} 10")],
        [InlineKeyboardButton(f"3 Days - â‚¹{p3:.2f}", callback_data=f"{buy_cmd} 11")],
        [InlineKeyboardButton(f"7 Days - â‚¹{p7:.2f}", callback_data=f"{buy_cmd} 12")],
        [InlineKeyboardButton(f"14 Days - â‚¹{p14:.2f}", callback_data=f"{buy_cmd} 13")],
        [InlineKeyboardButton(f"21 Days - â‚¹{p21:.2f}", callback_data=f"{buy_cmd} 14")],
        [InlineKeyboardButton("ðŸ”™ BACK", callback_data="/shopnawkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
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
    
    text = (
        "ðŸ‘¤ YOUR PROFILE\n\n"
        f"Name: {first_name}\n"
        f"User ID: {user_id}\n"
        f"Balance: â‚¹{balance:.2f}\n"
        f"Total Orders: {orders}\n"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("ðŸ›’ SHOP", callback_data="/shopnawkk"),
            InlineKeyboardButton("ðŸ“¦ MY KEY", callback_data="/orderksk")
        ],
        [InlineKeyboardButton("ðŸ”™ BACK", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_orders = db.get("userhAC", [])
    
    if not user_orders:
        text = "No orders yet."
        keyboard = [[InlineKeyboardButton("ðŸ”™ BACK", callback_data="/backkkk")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    latest_10 = user_orders[-10:][::-1]
    text = "\n\n".join([str(item) for item in latest_10 if item])
    
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (truncated)"
    
    keyboard = [[InlineKeyboardButton("ðŸ”™ BACK", callback_data="/backkkk")]]
    
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
    
    text = "ðŸ’¬ Support\n\nContact: @UR_SUBHAJIT0\nWhatsApp: wa.me/917908696630"
    
    keyboard = [
        [InlineKeyboardButton("ðŸ’¬ WHATSAPP", url="https://wa.me/917908696630")],
        [InlineKeyboardButton("ðŸ”™ BACK", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def how_to_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "ðŸŽ¥ Watch Tutorial Video"
    
    keyboard = [
        [InlineKeyboardButton("ðŸŽ¥ Watch Tutorial", url="https://t.me/hehehehhhsljg/162")],
        [InlineKeyboardButton("ðŸ”™ BACK", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
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
            InlineKeyboardButton("âŒ CLEAR", callback_data="/clearamt"),
            InlineKeyboardButton("0", callback_data="/num0"),
            InlineKeyboardButton("âœ… CONFIRM", callback_data="/done")
        ],
        [InlineKeyboardButton("ðŸ”™ BACK", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        "ðŸ’° ENTER AMOUNT\n\nAmount: â‚¹0",
        parse_mode="HTML",
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
        f"ðŸ’° ENTER AMOUNT\n\nAmount: â‚¹{new_amount}",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def clear_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    db.set("pay_amount", "")
    keyboard = query.message.reply_markup
    
    await query.edit_message_text(
        "ðŸ’° ENTER AMOUNT\n\nAmount: â‚¹0",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def confirm_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    amount = db.get("pay_amount")
    if not amount:
        await query.edit_message_text("âŒ Enter amount first")
        return
    
    try:
        amount_float = float(amount)
    except:
        await query.edit_message_text("âŒ Invalid amount")
        return
    
    db.set("last_deposit_amount", amount_float)
    
    upi = "bablu.xyztb@fam"
    url = f"{FAMPAY_BASE_URL}/qr.php?upi={upi}&amount={amount_float}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        await query.edit_message_text(f"âŒ API Error: {str(e)}")
        return
    
    if data.get("status") != "success":
        await query.edit_message_text("âŒ QR Generation Failed")
        return
    
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    db.set("addpay_order_id", order_id)
    
    keyboard = [
        [InlineKeyboardButton("âœ… VERIFY", callback_data="/verify_addpay")],
        [InlineKeyboardButton("âŒ CANCEL", callback_data="/cancel")]
    ]
    
    await query.message.reply_photo(
        photo=qr_url,
        caption=f"ðŸ’° Payment QR\n\nAmount: â‚¹{amount_float:.2f}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    await query.delete_message()

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    order_id = db.get("addpay_order_id")
    
    if not order_id:
        await query.edit_message_text("âŒ No active payment")
        return
    
    url = f"{FAMPAY_BASE_URL}/verify.php?order_id={order_id}&api_key={FAMPAY_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        await query.edit_message_text(f"âŒ API Error: {str(e)}")
        return
    
    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        new_balance = add_balance(user_id, amount)
        db.set("addpay_order_id", "")
        
        await query.edit_message_text(
            f"âœ… Payment Success!\n\n"
            f"Added: â‚¹{amount:.2f}\n"
            f"New Balance: â‚¹{new_balance:.2f}",
            parse_mode="HTML"
        )
        
        admins = db.get("AllBotAdminss", [])
        for admin in admins:
            try:
                await query.message.bot.send_message(
                    chat_id=admin,
                    text=f"âœ… New Payment!\n\nUser: {user_id}\nAmount: â‚¹{amount:.2f}"
                )
            except:
                pass
    else:
        await query.edit_message_text(
            "âŒ Payment Not Received\n\nPlease try again.",
            parse_mode="HTML"
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("âŒ Cancelled")

# ========================================
# BROADCAST
# ========================================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    await query.edit_message_text(
        "<b>ðŸ“£ Send message to broadcast</b>\n\nType /cancel to stop.",
        parse_mode="html"
    )
    context.user_data["awaiting_broadcast"] = True

async def broadcast_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "<b><i>ðŸš« You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        return
    
    if not context.user_data.get("awaiting_broadcast"):
        return
    
    if update.message.text == "/cancel":
        await update.message.reply_text("<b>âŒ Cancelled</b>", parse_mode="html")
        context.user_data["awaiting_broadcast"] = False
        return
    
    await update.message.reply_text(
        "<b>âœ… Broadcast sent!</b>",
        parse_mode="html"
    )
    
    log_admin_action(user_id, "Broadcast sent")
    context.user_data["awaiting_broadcast"] = False

# ========================================
# MAIN
# ========================================

def main():
    try:
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
        
        # Callback handlers
        app.add_handler(CallbackQueryHandler(back_to_home, pattern="^/backkkk$"))
        app.add_handler(CallbackQueryHandler(admin_panel, pattern="^/admin$"))
        app.add_handler(CallbackQueryHandler(shop_menu, pattern="^/shopnawkk$"))
        
        app.add_handler(CallbackQueryHandler(shop_drip, pattern="^/SHOP_P1$"))
        app.add_handler(CallbackQueryHandler(shop_proxy, pattern="^/SHOP_P2$"))
        app.add_handler(CallbackQueryHandler(shop_prime, pattern="^/SHOP_P4$"))
        
        app.add_handler(CallbackQueryHandler(shop_buy, pattern="^/buyjai "))
        app.add_handler(CallbackQueryHandler(shop_buy, pattern="^/buyjai_reseller "))
        
        app.add_handler(CallbackQueryHandler(profile, pattern="^/profilemmm$"))
        app.add_handler(CallbackQueryHandler(my_orders, pattern="^/orderksk$"))
        
        app.add_handler(CallbackQueryHandler(support, pattern="^/supportj$"))
        app.add_handler(CallbackQueryHandler(how_to_use, pattern="^/spinj$"))
        
        app.add_handler(CallbackQueryHandler(add_payment, pattern="^/addpayment$"))
        app.add_handler(CallbackQueryHandler(num_press, pattern="^/num[0-9]$"))
        app.add_handler(CallbackQueryHandler(clear_amount, pattern="^/clearamt$"))
        app.add_handler(CallbackQueryHandler(confirm_amount, pattern="^/done$"))
        app.add_handler(CallbackQueryHandler(verify_payment, pattern="^/verify_addpay$"))
        app.add_handler(CallbackQueryHandler(cancel, pattern="^/cancel$"))
        
        app.add_handler(CallbackQueryHandler(admin_add_balance, pattern="^/ChangeAnyUserBal$"))
        app.add_handler(CallbackQueryHandler(admin_actions, pattern="^/TUSHAR_AdminAction$"))
        app.add_handler(CallbackQueryHandler(admin_bot_mode, pattern="^/admin_BotMode "))
        app.add_handler(CallbackQueryHandler(admin_manage_admins, pattern="^/TUSHAR_Admins$"))
        app.add_handler(CallbackQueryHandler(admin_add_admin, pattern="^/TUSHAR_AddAdmin$"))
        app.add_handler(CallbackQueryHandler(admin_remove_admin, pattern="^/admin_remove_"))
        app.add_handler(CallbackQueryHandler(admin_add_reseller, pattern="^/addreseller$"))
        app.add_handler(CallbackQueryHandler(admin_remove_reseller, pattern="^/removereseller$"))
        app.add_handler(CallbackQueryHandler(admin_reseller_list, pattern="^/resellerlist$"))
        
        app.add_handler(CallbackQueryHandler(shop_setup, pattern="^/setshop_psue$"))
        app.add_handler(CallbackQueryHandler(shop_setup_drip, pattern="^/SHOPADMIN_P1$"))
        app.add_handler(CallbackQueryHandler(shop_setup_proxy, pattern="^/SHOPADMIN_P3$"))
        app.add_handler(CallbackQueryHandler(shop_setup_prime, pattern="^/SHOPADMIN_P2$"))
        
        app.add_handler(CallbackQueryHandler(shop_add_key, pattern="^/SHOPADDKEY"))
        app.add_handler(CallbackQueryHandler(shop_add_price, pattern="^/SHOPADD_PM"))
        
        app.add_handler(CallbackQueryHandler(broadcast, pattern="^/broadcast$"))
        
        print("=" * 50)
        print("ðŸ¤– Bot Started Successfully!")
        print("=" * 50)
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
