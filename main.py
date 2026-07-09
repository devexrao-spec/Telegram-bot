#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests  # ✅ This is installed
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
    ConversationHandler
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

db = BotDB()

# ========================================
# UTILITY FUNCTIONS
# ========================================

def is_admin(user_id: str) -> bool:
    admins = db.get("AllBotAdminss", [])
    return str(user_id) in [str(a) for a in admins]

def get_balance(user_id: str) -> float:
    balances = db.get("user_balances", {})
    return float(balances.get(str(user_id), 0))

def add_balance(user_id: str, amount: float) -> float:
    balances = db.get("user_balances", {})
    current = float(balances.get(str(user_id), 0))
    new_balance = current + amount
    balances[str(user_id)] = new_balance
    db.set("user_balances", balances)
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

# ========================================
# START COMMAND
# ========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    balance = get_balance(user_id)
    
    text = (
        "<b>ðŸ‘‹ Welcome to Hack Store!</b>\n\n"
        f"ðŸ’° Your Balance: â‚¹{balance:.2f}\n\n"
        "Use /shop to buy products\n"
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
# SIMPLE ADMIN PANEL
# ========================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        user_id = str(update.effective_user.id)
    else:
        user_id = str(update.effective_user.id)
    
    # Auto-add first admin
    admins = db.get("AllBotAdminss", [])
    if not admins:
        admins.append(user_id)
        db.set("AllBotAdminss", admins)
    
    if not is_admin(user_id):
        msg = "ðŸš« You are not admin"
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return
    
    keyboard = [
        [InlineKeyboardButton("ðŸ’° Add Balance", callback_data="/ChangeAnyUserBal")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="/backkkk")]
    ]
    
    text = "âš™ï¸ <b>Admin Panel</b>"
    
    if query:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

# ========================================
# ADMIN ADD BALANCE
# ========================================

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await query.edit_message_text("ðŸš« You are not admin")
        return
    
    await query.edit_message_text(
        "Send: <code>user_id amount</code>\nExample: <code>123456789 100</code>",
        parse_mode="HTML"
    )
    context.user_data["awaiting_balance"] = True

async def admin_add_balance_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not is_admin(user_id):
        await update.message.reply_text("ðŸš« You are not admin")
        return
    
    if not context.user_data.get("awaiting_balance"):
        return
    
    try:
        parts = update.message.text.split()
        target_user = parts[0]
        amount = float(parts[1])
        
        new_balance = add_balance(target_user, amount)
        
        await update.message.reply_text(
            f"âœ… Added â‚¹{amount:.2f} to {target_user}\nNew Balance: â‚¹{new_balance:.2f}"
        )
        
        try:
            await update.message.bot.send_message(
                chat_id=target_user,
                text=f"ðŸ’° Admin added â‚¹{amount:.2f} to your balance"
            )
        except:
            pass
        
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
    
    text = f"ðŸ‘‹ Welcome Back!\n\nðŸ’° Balance: â‚¹{balance:.2f}"
    
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
# SIMPLE SHOP
# ========================================

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("ðŸ›’ Buy Product - â‚¹100", callback_data="/buy 100")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        "ðŸ›’ <b>Shop</b>\n\nSelect a product:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========================================
# BUY PRODUCT
# ========================================

async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    price = float(query.data.split(" ")[1])
    
    balance = get_balance(user_id)
    
    if balance < price:
        await query.edit_message_text(
            f"âŒ Insufficient balance!\nNeed: â‚¹{price:.2f}\nHave: â‚¹{balance:.2f}"
        )
        return
    
    new_balance = add_balance(user_id, -price)
    
    await query.edit_message_text(
        f"âœ… Purchase Successful!\n\n"
        f"Deducted: â‚¹{price:.2f}\n"
        f"Remaining Balance: â‚¹{new_balance:.2f}\n\n"
        f"Your Key: <code>TEST-KEY-12345</code>",
        parse_mode="HTML"
    )

# ========================================
# PAYMENT
# ========================================

async def add_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("100", callback_data="/pay 100")],
        [InlineKeyboardButton("200", callback_data="/pay 200")],
        [InlineKeyboardButton("500", callback_data="/pay 500")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="/backkkk")]
    ]
    
    await query.edit_message_text(
        "ðŸ’° <b>Add Funds</b>\n\nSelect amount to add:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    amount = float(query.data.split(" ")[1])
    
    # Generate QR
    upi = "bablu.xyztb@fam"
    url = f"{FAMPAY_BASE_URL}/qr.php?upi={upi}&amount={amount}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        await query.edit_message_text(f"âŒ Error: {str(e)}")
        return
    
    if data.get("status") != "success":
        await query.edit_message_text("âŒ QR Generation Failed")
        return
    
    qr_url = data["data"]["qr_url"]
    order_id = data["data"]["order_id"]
    
    db.set("addpay_order_id", order_id)
    
    keyboard = [
        [InlineKeyboardButton("âœ… Verify Payment", callback_data="/verify")],
        [InlineKeyboardButton("ðŸ”™ Back", callback_data="/backkkk")]
    ]
    
    await query.message.reply_photo(
        photo=qr_url,
        caption=f"ðŸ’° Pay â‚¹{amount:.2f}\nScan QR to pay",
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
        await query.edit_message_text(f"âŒ Error: {str(e)}")
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
    else:
        await query.edit_message_text("âŒ Payment not received yet.\nPlease try again.")

# ========================================
# CANCEL
# ========================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("âŒ Cancelled")

# ========================================
# MAIN
# ========================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(back_to_home, pattern="^/backkkk$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^/admin$"))
    app.add_handler(CallbackQueryHandler(shop_menu, pattern="^/shopnawkk$"))
    app.add_handler(CallbackQueryHandler(buy_product, pattern="^/buy "))
    app.add_handler(CallbackQueryHandler(add_payment, pattern="^/addpayment$"))
    app.add_handler(CallbackQueryHandler(pay, pattern="^/pay "))
    app.add_handler(CallbackQueryHandler(verify_payment, pattern="^/verify$"))
    app.add_handler(CallbackQueryHandler(admin_add_balance, pattern="^/ChangeAnyUserBal$"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="^/cancel$"))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_balance_process))
    
    print("=" * 50)
    print("ðŸ¤– Bot Started Successfully!")
    print("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
