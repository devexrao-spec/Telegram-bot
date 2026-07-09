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
    balance = get_balance(user_id)
    
    text = (
        "<b>ðŸ‘‹ Welcome to Hack Store!</b>\n\n"
        f"ðŸ’° Your Balance: â‚¹{balance:.2f}\n\n"
        "Use /admin for admin panel"
    )
    
    keyboard = [
        [InlineKeyboardButton("ðŸ›’ SHOP", callback_data="/shopnawkk")],
        [InlineKeyboardButton("ðŸ’° ADD FUND", callback_data="/addpayment")],
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("âš™ï¸ ADMIN", callback_data="/admin")])
    
    await update.message.reply_text(
        text,
        parse_mode="HTML",
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
# BACK TO HOME
# ========================================

async def back_to_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    balance = get_balance(user_id)
    
    text = (
        "<b>ðŸ‘‹ Welcome Back!</b>\n\n"
        f"ðŸ’° Balance: â‚¹{balance:.2f}"
    )
    
    keyboard = [
        [InlineKeyboardButton("ðŸ›’ SHOP", callback_data="/shopnawkk")],
        [InlineKeyboardButton("ðŸ’° ADD FUND", callback_data="/addpayment")],
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("âš™ï¸ ADMIN", callback_data="/admin")])
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
# ADMIN BOT MODE TOGGLE
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
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="/admin")]
    ]
    
    await query.edit_message_text(
        "<b>ðŸ“Š Shop Setup Panel</b>\n\nSelect product to manage:",
        parse_mode="html",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# SHOP MENU
# ========================================

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "ðŸ›’ <b>Shop</b>\n\nSelect a product:"
    
    keyboard = [
        [InlineKeyboardButton("ðŸ”™ BACK", callback_data="/backkkk")]
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
    
    text = (
        "ðŸ‘¤ YOUR PROFILE\n\n"
        f"Name: {first_name}\n"
        f"User ID: {user_id}\n"
        f"Balance: â‚¹{balance:.2f}\n"
    )
    
    keyboard = [[InlineKeyboardButton("ðŸ”™ BACK", callback_data="/backkkk")]]
    
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
    
    text = "ðŸ’¬ Support\n\nContact: @UR_SUBHAJIT0"
    
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
    
    text = "ðŸŽ¥ Tutorial\n\nWatch tutorial video"
    
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
        "ðŸ’° ENTER CUSTOM AMOUNT\n\nAmount: â‚¹0\n\nUse keypad below",
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
        f"ðŸ’° ENTER CUSTOM AMOUNT\n\nAmount: â‚¹{new_amount}\n\nUse keypad below",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def clear_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    db.set("pay_amount", "")
    keyboard = query.message.reply_markup
    
    await query.edit_message_text(
        "ðŸ’° ENTER CUSTOM AMOUNT\n\nAmount: â‚¹0\n\nUse keypad below",
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
        await query.edit_message_text(f"âŒ API ERROR: {str(e)}")
        return
    
    if data.get("status") != "success":
        await query.edit_message_text("âŒ QR GENERATION FAILED")
        return
    
    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]
    
    db.set("addpay_order_id", order_id)
    
    keyboard = [
        [InlineKeyboardButton("âœ… VERIFY PAYMENT", callback_data="/verify_addpay")],
        [InlineKeyboardButton("âŒ CANCEL", callback_data="/cancel")]
    ]
    
    await query.message.reply_photo(
        photo=qr_url,
        caption=f"ðŸ’° PAYMENT QR GENERATED\n\nAmount: â‚¹{amount_float:.2f}",
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
        await query.edit_message_text("âŒ No active payment found.")
        return
    
    url = f"{FAMPAY_BASE_URL}/verify.php?order_id={order_id}&api_key={FAMPAY_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        await query.edit_message_text(f"âŒ API ERROR: {str(e)}")
        return
    
    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        new_balance = add_balance(user_id, amount)
        db.set("addpay_order_id", "")
        
        await query.edit_message_text(
            f"âœ… Payment Success!\n\nAdded: â‚¹{amount:.2f}\nNew Balance: â‚¹{new_balance:.2f}",
            parse_mode="HTML"
        )
        
        # Notify admins
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
            "âŒ Payment Not Received\n\nPlease complete the payment and try again.",
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
    """Main entry point"""
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # ========== COMMAND HANDLERS ==========
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("admin", admin_panel))
        
        # ========== MESSAGE HANDLERS ==========
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_balance_process))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_admin_process))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_reseller_process))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_remove_reseller_process))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_process))
        
        # ========== CALLBACK QUERY HANDLERS ==========
        # Navigation
        app.add_handler(CallbackQueryHandler(back_to_home, pattern="^/backkkk$"))
        app.add_handler(CallbackQueryHandler(admin_panel, pattern="^/admin$"))
        app.add_handler(CallbackQueryHandler(shop_menu, pattern="^/shopnawkk$"))
        
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
        
        # Broadcast
        app.add_handler(CallbackQueryHandler(broadcast, pattern="^/broadcast$"))
        
        # ========== START BOT ==========
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
