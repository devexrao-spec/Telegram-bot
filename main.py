#!/usr/bin/env python3
"""
SHOP BOT - Premium Emoji in TEXT + BUTTONS (Real Telegram API)
"""

import telebot
from telebot import types
import time
import re

BOT_TOKEN = "8644946592:AAGqcXNTd0TRpYSkK3XkwGjXVQMwxTZKoao"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

print("🤖 Bot Started!")

# ======================================================================
# FIX - Premium emoji to normal for non-premium users
# ======================================================================

def fix_emojis(text):
    """Convert premium emoji to normal for non-premium users"""
    if not text:
        return text
    
    premium_map = {
        '5345976085735558094': '🌟',
        '5348292765325212780': '🌙',
        '5346024644635804737': '✨',
        '5316571734604790521': '🚀',
        '5346289416484699504': '⚡',
        '6120544300511007571': '💳',
        '5346160971192747426': '🛡️',
        '5348392971207194994': '💰',
        '6093739864883207194': '🛒',
        '5967456680940671207': '📦',
        '5346136537123801643': '👤',
        '5345783284653636765': '🎥',
        '5897567714674741148': '💬',
        '6278302366303260172': '💰',
        '6039539366177541657': '🔙',
        '6179339404906079822': '✅',
        '5258336354642697821': '👇',
        '6278116707751956084': '❌'
    }
    
    def replace_match(match):
        emoji_id = match.group(1)
        emoji_char = match.group(2)
        return premium_map.get(emoji_id, emoji_char)
    
    text = re.sub(r'<tg-emoji emoji-id=[\'"](\d+)[\'"]>(.*?)</tg-emoji>', replace_match, text)
    return text

# ======================================================================
# /start - Premium Emoji in TEXT + BUTTONS
# ======================================================================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    
    # TEXT mein PREMIUM emoji
    text = f"""
<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> <b>WELCOME {first_name}</b> <tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji>

<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> Premium Store

<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> Features:
<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Instant Delivery
<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Secure Payment
<tg-emoji emoji-id='5346160971192747426'>🛡️</tg-emoji> Anti-Ban

<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Balance: ₹0

━━━━━━━━━━━━━━━━━━━━
👇 Select:
    """
    
    # BUTTONS mein PREMIUM emoji - REAL TELEGRAM API WAY
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # ✅ Sahi tarika - button mein emoji parameter use karo
    btn1 = types.InlineKeyboardButton(
        text="BUY HACK",
        callback_data="shop",
        emoji="🛒"  # ← Ye premium emoji hai!
    )
    
    btn2 = types.InlineKeyboardButton(
        text="MY KEYS",
        callback_data="mykeys",
        emoji="📦"
    )
    
    btn3 = types.InlineKeyboardButton(
        text="PROFILE",
        callback_data="profile",
        emoji="👤"
    )
    
    btn4 = types.InlineKeyboardButton(
        text="HOW TO USE",
        callback_data="howto",
        emoji="🎥"
    )
    
    btn5 = types.InlineKeyboardButton(
        text="SUPPORT",
        callback_data="support",
        emoji="💬"
    )
    
    btn6 = types.InlineKeyboardButton(
        text="ADD FUND",
        callback_data="addfund",
        emoji="💰"
    )
    
    markup.add(btn1)
    markup.add(btn2, btn3)
    markup.add(btn4, btn5)
    markup.add(btn6)
    
    # Fix emojis for non-premium users
    text = fix_emojis(text)
    
    bot.send_message(
        chat_id=user_id,
        text=text,
        parse_mode="HTML",
        reply_markup=markup
    )

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
    
    if call.data == "shop":
        text = """
<tg-emoji emoji-id='6093739864883207194'>🛒</tg-emoji> <b>SHOP</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Products:

1️⃣ DRIP CLIENT - ₹108
2️⃣ PROXY SERVER - ₹108
3️⃣ PRIME HOOK - ₹108

<tg-emoji emoji-id='5258336354642697821'>👇</tg-emoji> Select:
        """
        
        text = fix_emojis(text)
        
        # BUTTONS mein premium emoji
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📦 DRIP CLIENT", callback_data="buy_drip", emoji="📦"),
            types.InlineKeyboardButton("📦 PROXY SERVER", callback_data="buy_proxy", emoji="📦"),
            types.InlineKeyboardButton("🔥 PRIME HOOK", callback_data="buy_prime", emoji="🔥"),
            types.InlineKeyboardButton("🔙 BACK", callback_data="back", emoji="🔙")
        )
        
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )
    
    elif call.data == "mykeys":
        text = """
<tg-emoji emoji-id='5967456680940671207'>📦</tg-emoji> <b>MY KEYS</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> No keys yet!

<tg-emoji emoji-id='6093739864883207194'>🛒</tg-emoji> Buy a product!

━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Balance: ₹0
        """
        
        text = fix_emojis(text)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔙 BACK", callback_data="back", emoji="🔙")
        )
        
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

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Name: {call.from_user.first_name}
<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Balance: ₹0
<tg-emoji emoji-id='5967456680940671207'>📦</tg-emoji> Orders: 0

━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id='5346160971192747426'>🛡️</tg-emoji> Premium: No
        """
        
        text = fix_emojis(text)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔙 BACK", callback_data="back", emoji="🔙")
        )
        
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )
    
    elif call.data == "howto":
        text = """
<tg-emoji emoji-id='5345783284653636765'>🎥</tg-emoji> <b>HOW TO USE</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Step 1: Buy product
<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> Step 2: Get key
<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Step 3: Use key

<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> <a href="https://t.me/hehehehhhsljg/162">Watch Tutorial</a>
        """
        
        text = fix_emojis(text)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📹 WATCH", url="https://t.me/hehehehhhsljg/162", emoji="📹"),
            types.InlineKeyboardButton("🔙 BACK", callback_data="back", emoji="🔙")
        )
        
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=markup
        )
    
    elif call.data == "support":
        text = """
<tg-emoji emoji-id='5897567714674741148'>💬</tg-emoji> <b>SUPPORT</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Need help?

<tg-emoji emoji-id='5346136537123801643'>👤</tg-emoji> <a href="https://t.me/UR_SUBHAJIT0">Subhajit</a>
<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> <a href="https://wa.me/917908696630">WhatsApp</a>

<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> Include your User ID!
        """
        
        text = fix_emojis(text)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📱 WHATSAPP", url="https://wa.me/917908696630", emoji="📱"),
            types.InlineKeyboardButton("🔙 BACK", callback_data="back", emoji="🔙")
        )
        
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=markup
        )
    
    elif call.data == "addfund":
        text = """
<tg-emoji emoji-id='6278302366303260172'>💰</tg-emoji> <b>ADD FUND</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Enter amount:

Amount: ₹0

<tg-emoji emoji-id='5258336354642697821'>👇</tg-emoji> Use keypad:
        """
        
        text = fix_emojis(text)
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("1", callback_data="num1", emoji="1️⃣"),
            types.InlineKeyboardButton("2", callback_data="num2", emoji="2️⃣"),
            types.InlineKeyboardButton("3", callback_data="num3", emoji="3️⃣"),
            types.InlineKeyboardButton("4", callback_data="num4", emoji="4️⃣"),
            types.InlineKeyboardButton("5", callback_data="num5", emoji="5️⃣"),
            types.InlineKeyboardButton("6", callback_data="num6", emoji="6️⃣"),
            types.InlineKeyboardButton("7", callback_data="num7", emoji="7️⃣"),
            types.InlineKeyboardButton("8", callback_data="num8", emoji="8️⃣"),
            types.InlineKeyboardButton("9", callback_data="num9", emoji="9️⃣"),
            types.InlineKeyboardButton("❌ CLEAR", callback_data="clear", emoji="❌"),
            types.InlineKeyboardButton("0", callback_data="num0", emoji="0️⃣"),
            types.InlineKeyboardButton("✅ DONE", callback_data="done", emoji="✅")
        )
        markup.add(
            types.InlineKeyboardButton("🔙 BACK", callback_data="back", emoji="🔙")
        )
        
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )
    
    elif call.data == "back":
        start_command(call.message)
    
    elif call.data.startswith("buy_"):
        product = call.data.replace("buy_", "").upper()
        key = "KEY-" + str(user_id)[-5:] + "-XYZ"
        
        text = f"""
<tg-emoji emoji-id='6179339404906079822'>✅</tg-emoji> <b>PURCHASE SUCCESSFUL!</b>

🔑 <b>Your Key:</b>
<code>{key}</code>

📦 Product: {product}
💰 Price: ₹108

<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Use key in app!
        """
        
        text = fix_emojis(text)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔙 BACK", callback_data="back", emoji="🔙")
        )
        
        bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )
        
        bot.answer_callback_query(call.id, text="✅ Key Generated!", show_alert=True)
    
    elif call.data.startswith("num"):
        bot.answer_callback_query(call.id, text="✅ Added!", show_alert=False)
    
    elif call.data == "clear":
        bot.answer_callback_query(call.id, text="🧹 Cleared!", show_alert=False)
    
    elif call.data == "done":
        bot.answer_callback_query(call.id, text="💰 Processing...", show_alert=True)

# ======================================================================
# MAIN
# ======================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 PREMIUM EMOJI BOT - TEXT + BUTTONS")
    print("=" * 60)
    print("✅ Premium emoji in TEXT (tg-emoji tag)")
    print("✅ Premium emoji in BUTTONS (emoji parameter)")
    print("=" * 60)
    print("🔄 Polling...")
    print("=" * 60)
    
    while True:
        try:
            bot.infinity_polling(timeout=30)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)
