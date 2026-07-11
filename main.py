#!/usr/bin/env python3
"""
TEST BOT - Sirf Premium Emoji Check Karne Ke Liye
"""

import telebot
from telebot import types

# ======================================================================
# CONFIG
# ======================================================================
BOT_TOKEN = "8644946592:AAGqcXNTd0TRpYSkK3XkwGjXVQMwxTZKoao"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

print("🤖 Test Bot Starting...")

# ======================================================================
# /start COMMAND
# ======================================================================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    
    # Premium Emoji Test
    text = """
<b>🌟 PREMIUM EMOJI TEST 🌟</b>

<b>1️⃣ Premium Emoji (Sirf Premium Users):</b>
<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Star
<tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji> Moon
<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> Sparkle
<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> Rocket
<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Lightning
<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Card
<tg-emoji emoji-id='5346160971192747426'>🛡️</tg-emoji> Shield
<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Money

<b>2️⃣ Normal Emoji (Sabko Dikhega):</b>
🌟 ⭐ 🔥 💎
✅ ❌ ⚠️ 💰
📦 🛒 🎥 📱
💬 👤 🔙 ➡️
🚀 ⚡ 🛡️ 💳

<b>3️⃣ Mixed Emoji:</b>
<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Welcome ⭐
<tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji> Night 🌙
<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> Launch 🚀

━━━━━━━━━━━━━━━━━━━━
👇 Buttons Test:
    """
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Buttons with premium emoji
    btn1 = types.InlineKeyboardButton(
        "<tg-emoji emoji-id='6093739864883207194'>🛒</tg-emoji> BUY", 
        callback_data="buy"
    )
    btn2 = types.InlineKeyboardButton(
        "<tg-emoji emoji-id='5967456680940671207'>📦</tg-emoji> KEYS", 
        callback_data="keys"
    )
    btn3 = types.InlineKeyboardButton(
        "<tg-emoji emoji-id='5346136537123801643'>👤</tg-emoji> PROFILE", 
        callback_data="profile"
    )
    btn4 = types.InlineKeyboardButton(
        "🔙 BACK", 
        callback_data="back"
    )
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    
    bot.send_message(
        chat_id=user_id,
        text=text,
        parse_mode="HTML",
        reply_markup=markup
    )

# ======================================================================
# /test COMMAND - Sirf Normal Emoji
# ======================================================================

@bot.message_handler(commands=['test'])
def test_command(message):
    text = """
✅ <b>NORMAL EMOJI TEST</b>

Ye sabhi emoji <b>sabko dikhenge</b>:

🌟 ⭐ 🔥 💎 
✅ ❌ ⚠️ 💰
📦 🛒 🎥 📱
💬 👤 🔙 ➡️
🚀 ⚡ 🛡️ 💳
❤️ 💙 💚 💛
🎉 🎊 🎈 🎁

<b>🔑 Key Features:</b>
⚡ Instant Delivery
💳 Secure Payment
🛡️ 100% Safe
💰 Best Prices

<b>✅ All emojis working!</b>
    """
    
    bot.reply_to(message, text, parse_mode="HTML")

# ======================================================================
# /premium COMMAND - Sirf Premium Emoji
# ======================================================================

@bot.message_handler(commands=['premium'])
def premium_command(message):
    text = """
<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> <b>PREMIUM EMOJI TEST</b>

Ye emoji <b>sirf Premium users</b> ko dikhenge:

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Premium Star
<tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji> Premium Moon
<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> Premium Sparkle
<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> Premium Rocket
<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Premium Lightning
<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Premium Card
<tg-emoji emoji-id='5346160971192747426'>🛡️</tg-emoji> Premium Shield
<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Premium Money

<b>✅ Premium emoji test complete!</b>
    """
    
    bot.reply_to(message, text, parse_mode="HTML")

# ======================================================================
# /mixed COMMAND - Premium + Normal Mix
# ======================================================================

@bot.message_handler(commands=['mixed'])
def mixed_command(message):
    text = """
<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> <b>MIXED EMOJI TEST</b>

<b>Premium + Normal Mix:</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Premium Star ⭐ Normal Star
<tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji> Premium Moon 🌙 Normal Moon
<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> Premium Sparkle ✨ Normal Sparkle
<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> Premium Rocket 🚀 Normal Rocket

<b>Normal Users:</b> Sirf normal emoji dikhenge
<b>Premium Users:</b> Dono dikhenge (premium + normal)

━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id='6179339404906079822'>✅</tg-emoji> Test Complete!
    """
    
    bot.reply_to(message, text, parse_mode="HTML")

# ======================================================================
# CALLBACK HANDLER
# ======================================================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    try:
        bot.answer_callback_query(call.id)
    except:
        pass
    
    if call.data == "buy":
        text = """
<tg-emoji emoji-id='6093739864883207194'>🛒</tg-emoji> <b>BUY PRODUCT</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Premium Product
💰 Price: ₹108

<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Instant Delivery
<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Secure Payment

🔑 <b>Your Key:</b>
<code>ABC123XYZ</code>

<tg-emoji emoji-id='6179339404906079822'>✅</tg-emoji> Purchase Successful!
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="back"))
        
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )
    
    elif call.data == "keys":
        text = """
<tg-emoji emoji-id='5967456680940671207'>📦</tg-emoji> <b>MY KEYS</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> No keys yet!

<tg-emoji emoji-id='6093739864883207194'>🛒</tg-emoji> Buy a product to get keys!

━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Balance: ₹0
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="back"))
        
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )
    
    elif call.data == "profile":
        text = f"""
<tg-emoji emoji-id='5346136537123801643'>👤</tg-emoji> <b>PROFILE</b>

📛 Name: {call.from_user.first_name}
🆔 ID: <code>{user_id}</code>
<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Balance: ₹0
<tg-emoji emoji-id='5967456680940671207'>📦</tg-emoji> Orders: 0

━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Premium User: No
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="back"))
        
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )
    
    elif call.data == "back":
        start_command(call.message)

# ======================================================================
# MAIN
# ======================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 TEST BOT STARTED!")
    print("=" * 50)
    print("📌 Commands:")
    print("  /start    - Premium + Normal Emoji")
    print("  /test     - Sirf Normal Emoji")
    print("  /premium  - Sirf Premium Emoji")
    print("  /mixed    - Premium + Normal Mix")
    print("=" * 50)
    print("🔄 Polling...")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=30)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)
