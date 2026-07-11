#!/usr/bin/env python3
"""
TEST BOT - Premium Emoji Everywhere (Text + Buttons) + Profile Photo
"""

import telebot
from telebot import types
import time
import requests
from io import BytesIO

# ======================================================================
# CONFIG
# ======================================================================
BOT_TOKEN = "8644946592:AAGqcXNTd0TRpYSkK3XkwGjXVQMwxTZKoao"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

print("🤖 Premium Emoji Test Bot Starting...")

# ======================================================================
# /start COMMAND - Premium Emoji in TEXT + BUTTONS
# ======================================================================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    
    # TEXT mein premium emoji
    text = f"""
<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> <b>WELCOME {first_name}</b> <tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji>

<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> Premium Store

<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> Features:
<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Instant Delivery
<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Secure Payment
<tg-emoji emoji-id='5346160971192747426'>🛡️</tg-emoji> Anti-Ban

<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Balance: ₹0

━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id='5258336354642697821'>👇</tg-emoji> Select:
    """
    
    # BUTTONS mein premium emoji
    markup = types.InlineKeyboardMarkup(row_width=2)
    
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
        "<tg-emoji emoji-id='5345783284653636765'>🎥</tg-emoji> TUTORIAL", 
        callback_data="tutorial"
    )
    btn5 = types.InlineKeyboardButton(
        "<tg-emoji emoji-id='5897567714674741148'>💬</tg-emoji> SUPPORT", 
        callback_data="support"
    )
    btn6 = types.InlineKeyboardButton(
        "<tg-emoji emoji-id='6278302366303260172'>💰</tg-emoji> ADD FUND", 
        callback_data="addfund"
    )
    
    markup.add(btn1)
    markup.add(btn2, btn3)
    markup.add(btn4, btn5)
    markup.add(btn6)
    
    bot.send_message(
        chat_id=user_id,
        text=text,
        parse_mode="HTML",
        reply_markup=markup
    )

# ======================================================================
# /premium COMMAND - Only Premium Emoji
# ======================================================================

@bot.message_handler(commands=['premium'])
def premium_command(message):
    user_id = message.from_user.id
    
    text = """
<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> <b>PREMIUM EMOJI TEST</b> <tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji>

<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> All emojis are premium!

<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> Premium Rocket
<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Premium Lightning
<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Premium Card
<tg-emoji emoji-id='5346160971192747426'>🛡️</tg-emoji> Premium Shield
<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Premium Money

<tg-emoji emoji-id='6179339404906079822'>✅</tg-emoji> Premium Test Complete!
    """
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "<tg-emoji emoji-id='6039539366177541657'>🔙</tg-emoji> BACK", 
            callback_data="back"
        )
    )
    
    bot.reply_to(
        message, 
        text, 
        parse_mode="HTML", 
        reply_markup=markup
    )

# ======================================================================
# /normal COMMAND - Only Normal Emoji (For Comparison)
# ======================================================================

@bot.message_handler(commands=['normal'])
def normal_command(message):
    text = """
🌟 <b>NORMAL EMOJI TEST</b> 🌙

✨ All emojis are normal!

🚀 Normal Rocket
⚡ Normal Lightning
💳 Normal Card
🛡️ Normal Shield
💰 Normal Money

✅ Normal Test Complete!
    """
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "🔙 BACK", 
            callback_data="back"
        )
    )
    
    bot.reply_to(
        message, 
        text, 
        parse_mode="HTML", 
        reply_markup=markup
    )

# ======================================================================
# GET USER PROFILE PHOTO
# ======================================================================

def get_profile_photo(user_id):
    """Get user's profile photo URL"""
    try:
        photos = bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            # Get largest photo (last in list)
            file_id = photos.photos[0][-1].file_id
            file_info = bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
            return file_url
        return None
    except Exception as e:
        print(f"Error getting photo: {e}")
        return None

# ======================================================================
# SHOW PROFILE WITH PHOTO
# ======================================================================

def show_profile(chat_id, message_id, user_id, user_first_name):
    """Show profile with photo at top and details below"""
    
    # Get profile photo URL
    photo_url = get_profile_photo(user_id)
    
    # Profile text with premium emojis
    text = f"""
<tg-emoji emoji-id='5346136537123801643'>👤</tg-emoji> <b>PROFILE</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Name: {user_first_name}
<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Balance: ₹0
<tg-emoji emoji-id='5967456680940671207'>📦</tg-emoji> Orders: 0
<tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji> Member Since: Today

━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id='5346160971192747426'>🛡️</tg-emoji> Premium: No
    """
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "<tg-emoji emoji-id='6039539366177541657'>🔙</tg-emoji> BACK", 
            callback_data="back"
        )
    )
    
    try:
        if photo_url:
            # Send profile photo as separate message (with caption)
            bot.send_photo(
                chat_id=chat_id,
                photo=photo_url,
                caption=text,
                parse_mode="HTML",
                reply_markup=markup
            )
            
            # Delete the old message (where button was clicked)
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
        else:
            # If no photo, just edit the existing message
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="HTML",
                reply_markup=markup
            )
    except Exception as e:
        print(f"Error showing profile: {e}")
        # Fallback: edit message with text only
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )

# ======================================================================
# CALLBACK HANDLER - Premium Emoji in ALL messages
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
<tg-emoji emoji-id='6093739864883207194'>🛒</tg-emoji> <b>PURCHASE</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Premium Product
<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Price: ₹108

<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Instant Delivery
<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Secure Payment

<tg-emoji emoji-id='6179339404906079822'>✅</tg-emoji> <b>Success!</b>

🔑 <b>Key:</b>
<code>ABC123XYZ</code>
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "<tg-emoji emoji-id='6039539366177541657'>🔙</tg-emoji> BACK", 
                callback_data="back"
            )
        )
        
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

<tg-emoji emoji-id='6093739864883207194'>🛒</tg-emoji> Buy a product!

━━━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Balance: ₹0
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "<tg-emoji emoji-id='6039539366177541657'>🔙</tg-emoji> BACK", 
                callback_data="back"
            )
        )
        
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup
        )
    
    elif call.data == "profile":
        # Call the profile function with photo
        show_profile(
            chat_id=user_id,
            message_id=call.message.message_id,
            user_id=user_id,
            user_first_name=call.from_user.first_name or "User"
        )
    
    elif call.data == "tutorial":
        text = """
<tg-emoji emoji-id='5345783284653636765'>🎥</tg-emoji> <b>HOW TO USE</b>

<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Step 1: Buy product
<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> Step 2: Get key
<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Step 3: Use key

<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> <a href="https://t.me/hehehehhhsljg/162">Watch Tutorial</a>
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "<tg-emoji emoji-id='6039539366177541657'>🔙</tg-emoji> BACK", 
                callback_data="back"
            )
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
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "<tg-emoji emoji-id='6039539366177541657'>🔙</tg-emoji> BACK", 
                callback_data="back"
            )
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
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("<tg-emoji emoji-id='5258134813302332906'>1️⃣</tg-emoji>", callback_data="num1"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='5258134813302332906'>2️⃣</tg-emoji>", callback_data="num2"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='5258134813302332906'>3️⃣</tg-emoji>", callback_data="num3"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='5258134813302332906'>4️⃣</tg-emoji>", callback_data="num4"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='5258134813302332906'>5️⃣</tg-emoji>", callback_data="num5"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='5258134813302332906'>6️⃣</tg-emoji>", callback_data="num6"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='5258134813302332906'>7️⃣</tg-emoji>", callback_data="num7"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='5258134813302332906'>8️⃣</tg-emoji>", callback_data="num8"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='5258134813302332906'>9️⃣</tg-emoji>", callback_data="num9"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='6278116707751956084'>❌</tg-emoji> CLEAR", callback_data="clear"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='5258134813302332906'>0️⃣</tg-emoji>", callback_data="num0"),
            types.InlineKeyboardButton("<tg-emoji emoji-id='6179339404906079822'>✅</tg-emoji> DONE", callback_data="done")
        )
        markup.add(
            types.InlineKeyboardButton(
                "<tg-emoji emoji-id='6039539366177541657'>🔙</tg-emoji> BACK", 
                callback_data="back"
            )
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
    
    elif call.data.startswith("num"):
        bot.answer_callback_query(
            call.id, 
            text="<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> Number added!", 
            show_alert=False
        )
    
    elif call.data == "clear":
        bot.answer_callback_query(
            call.id, 
            text="<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> Cleared!", 
            show_alert=False
        )
    
    elif call.data == "done":
        bot.answer_callback_query(
            call.id, 
            text="<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Processing payment...", 
            show_alert=True
        )

# ======================================================================
# MAIN
# ======================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 PREMIUM EMOJI TEST BOT STARTED!")
    print("=" * 60)
    print("📌 Commands:")
    print("  /start    - Premium emoji everywhere (text + buttons)")
    print("  /premium  - Only premium emoji")
    print("  /normal   - Only normal emoji (for comparison)")
    print("=" * 60)
    print("📱 Premium Users → Sab emoji dikhenge")
    print("📱 Normal Users → Sirf normal emoji dikhenge")
    print("=" * 60)
    print("📸 Profile Photo → Jab PROFILE dabayenge toh photo dikhegi")
    print("=" * 60)
    print("🔄 Polling...")
    print("=" * 60)
    
    while True:
        try:
            bot.infinity_polling(timeout=30)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)
