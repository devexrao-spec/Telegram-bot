import telebot
import requests

# --------------------- BOT CONFIG ---------------------
API_TOKEN = '8565204943:AAHxmBVVHcEXYqtb32dyVCbCiUb740NDIOo'
bot = telebot.TeleBot(API_TOKEN)

FORCE_JOIN_CHANNEL = '@fflike1'
CHANNEL_LINK = 'https://t.me/nothing'
BUTTON_NAME = 'fflike1'
OWNER_ID = 8102646437

# --------------------- FORCE JOIN CHECK ---------------------
def is_user_member(user_id):
    if user_id == OWNER_ID:
        return True
    try:
        member = bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# --------------------- HANDLERS ---------------------
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id

    if user_id == OWNER_ID:
        bot.reply_to(
            message,
            "👑 Wᴇʟᴄᴏᴍᴇ Mᴀsᴛᴇʀ!\n\n"
            "✅ Uɴʟɪᴍɪᴛᴇᴅ Aᴄᴄᴇss Aᴄᴛɪᴠᴇ\n"
            "✅ Fᴏʀᴄᴇ Jᴏɪɴ Dɪsᴀʙʟᴇᴅ\n"
            "✅ Nᴏ Lɪᴍɪᴛs ᴏɴ Lɪᴋᴇs\n\n"
            "🎮 Cᴏᴍᴍᴀɴᴅ: `/like {region} {uid}`\n"
            "Exᴀᴍᴘʟᴇ: `/like ind 1055975097`",
            parse_mode='Markdown'
        )
        return

    if not is_user_member(user_id):
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        join_button = telebot.types.InlineKeyboardButton(f"🔗 JOIN {BUTTON_NAME}", url=CHANNEL_LINK)
        verify_button = telebot.types.InlineKeyboardButton("✅ VERIFY", callback_data="verify_membership")
        markup.add(join_button, verify_button)

        bot.reply_to(
            message,
            "🚫 Aᴄᴄᴇss Dᴇɴɪᴇᴅ!\n\n"
            "Yᴏᴜ Mᴜsᴛ Jᴏɪɴ Oᴜʀ Oғғɪᴄɪᴀʟ Cʜᴀɴɴᴇʟ Fɪʀsᴛ Tᴏ Usᴇ Tʜɪs Bᴏᴛ.\n\n"
            f"📢 Cʜᴀɴɴᴇʟ: {CHANNEL_LINK}\n\n"
            "✅ Aғᴛᴇʀ Jᴏɪɴɪɴɢ, Tᴀᴘ Tʜᴇ *Vᴇʀɪғʏ* Bᴜᴛᴛᴏɴ Bᴇʟᴏᴡ.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return

    bot.reply_to(
        message,
        "✅ Wᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ Bᴏᴛ!\n\n"
        "🎮 Cᴏᴍᴍᴀɴᴅs:\n"
        "`/like {region} {uid}`\n\n"
        "📝 Exᴀᴍᴘʟᴇ:\n"
        "`/like ind 1055975097`\n\n"
        "🌍 Sᴜᴘᴘᴏʀᴛᴇᴅ Rᴇɢɪᴏɴs: ind, id, sg, my, ph, ᴇᴛᴄ.",
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == "verify_membership")
def handle_verify(call):
    user_id = call.from_user.id

    if is_user_member(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        start_button = telebot.types.InlineKeyboardButton("🚀 START USING BOT", callback_data="start_using")
        markup.add(start_button)

        bot.edit_message_text(
            "✅ Vᴇʀɪғɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇssғᴜʟ!\n\n"
            "Yᴏᴜ ʜᴀᴠᴇ sᴜᴄᴄᴇssғᴜʟʟʏ ᴊᴏɪɴᴇᴅ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ.\n\n"
            "Cʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ sᴛᴀʀᴛ ᴜsɪɴɢ ᴛʜᴇ ʙᴏᴛ 👇",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
        bot.answer_callback_query(call.id, "✅ Verified! Now you can use the bot.")
    else:
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        join_button = telebot.types.InlineKeyboardButton(f"🔗 JOIN {BUTTON_NAME}", url=CHANNEL_LINK)
        verify_button = telebot.types.InlineKeyboardButton("✅ VERIFY AGAIN", callback_data="verify_membership")
        markup.add(join_button, verify_button)

        bot.edit_message_text(
            "🚫 Aᴄᴄᴇss Dᴇɴɪᴇᴅ!\n\n"
            "Yᴏᴜ Hᴀᴠᴇɴ'ᴛ Jᴏɪɴᴇᴅ Yᴇᴛ.\n\n"
            f"📢 Pʟᴇᴀsᴇ Jᴏɪɴ Fɪʀsᴛ: {CHANNEL_LINK}\n\n"
            "✅ Aғᴛᴇʀ Jᴏɪɴɪɴɢ, Tᴀᴘ *Vᴇʀɪғʏ Aɢᴀɪɴ*.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
        bot.answer_callback_query(call.id, "❌ Please join the channel first!")

@bot.callback_query_handler(func=lambda call: call.data == "start_using")
def handle_start_using(call):
    bot.edit_message_text(
        "✅ *Rᴇᴀᴅʏ Tᴏ Usᴇ!*\n\n"
        "🎮 *Usᴀɢᴇ:*\n"
        "`/like ind 1055975097`\n\n"
        "🌍 *Sᴜᴘᴘᴏʀᴛᴇᴅ Rᴇɢɪᴏɴs:*\n"
        "• 🇮🇳 `ind` → Iɴᴅɪᴀ\n"
        "• 🇮🇩 `id` → Iɴᴅᴏɴᴇsɪᴀ\n"
        "• 🇸🇬 `sg` → Sɪɴɢᴀᴘᴏʀᴇ\n"
        "• 🇲🇾 `my` → Mᴀʟᴀʏsɪᴀ\n"
        "• 🇵🇭 `ph` → Pʜɪʟɪᴘᴘɪɴᴇs\n\n"
        "💡 *Exᴀᴍᴘʟᴇ:*\n"
        "`/like sg 1234567890`",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )
    bot.answer_callback_query(call.id, "🎉 Bot is ready to use!")

@bot.message_handler(commands=['like'])
def handle_like(message):
    user_id = message.from_user.id

    if not is_user_member(user_id):
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        join_button = telebot.types.InlineKeyboardButton(f"🔗 JOIN {BUTTON_NAME}", url=CHANNEL_LINK)
        verify_button = telebot.types.InlineKeyboardButton("✅ VERIFY", callback_data="verify_membership")
        markup.add(join_button, verify_button)

        bot.reply_to(
            message,
            "🚫 Aᴄᴄᴇss Dᴇɴɪᴇᴅ!\n\n"
            "Yᴏᴜ Mᴜsᴛ Jᴏɪɴ Oᴜʀ Oғғɪᴄɪᴀʟ Cʜᴀɴɴᴇʟ Fɪʀsᴛ Tᴏ Usᴇ Tʜɪs Bᴏᴛ.\n\n"
            f"📢 Cʜᴀɴɴᴇʟ: {CHANNEL_LINK}\n\n"
            "✅ Aғᴛᴇʀ Jᴏɪɴɪɴɢ, Tᴀᴘ Tʜᴇ *Vᴇʀɪғʏ* Bᴜᴛᴛᴏɴ Bᴇʟᴏᴡ.",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return

    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(
            message,
            "❌ Usᴀɢᴇ: `/like {region} {uid}`\n"
            "Exᴀᴍᴘʟᴇ: `/like ind 1055975097`",
            parse_mode='Markdown'
        )
        return

    region = args[1]
    uid = args[2]

    if user_id == OWNER_ID:
        sent_msg = bot.reply_to(
            message,
            "👑 *Pʀᴏᴄᴇssɪɴɢ Oᴡɴᴇʀ Rᴇǫᴜᴇsᴛ ᴡɪᴛʜ Uɴʟɪᴍɪᴛᴇᴅ Aᴄᴄᴇss...*",
            parse_mode='Markdown'
        )
    else:
        sent_msg = bot.reply_to(
            message,
            "⏳ *Pʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ...*",
            parse_mode='Markdown'
        )

    api_url = f"http://187.127.175.208:5002/like?uid={uid}&server_name={region}"

    try:
        response = requests.get(api_url)
        data = response.json()

        name = data.get('PlayerNickname', 'N/A')
        likes_before = data.get('LikesbeforeCommand', '0')
        likes_given = data.get('LikesGivenByAPI', '0')
        likes_after = data.get('LikesafterCommand', '0')
        remaining = data.get('remains', 'N/A')

        if user_id == OWNER_ID:
            remaining = "♾️ UNLIMITED"

        template = (
            f"🎉 Lɪᴋᴇ Sᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ 👍\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 Nᴀᴍᴇ: {name}\n"
            f"🕹️ Uɪᴅ: {uid}\n"
            f"🌐 Rᴇɢɪᴏɴ: {region.upper()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"❤️ Lɪᴋᴇꜱ Bᴇꜰᴏʀᴇ: {likes_before}\n"
            f"🩵 Lɪᴋᴇꜱ Gɪᴠᴇɴ: {likes_given}\n"
            f"💚 Lɪᴋᴇꜱ Aꜰᴛᴇʀ: {likes_after}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Rᴇᴍᴀɪɴɪɴɢ: {remaining}"
        )
        if user_id == OWNER_ID:
            template += "\n━━━━━━━━━━━━━━━━━━━━━\n👑 OWNER UNLIMITED ACCESS 👑"

        bot.edit_message_text(template, chat_id=message.chat.id, message_id=sent_msg.message_id)

    except Exception as e:
        bot.edit_message_text(
            f"❌ Eʀʀᴏʀ Cᴏɴɴᴇᴄᴛɪᴏɴ ᴛᴏ API\n`{str(e)}`",
            chat_id=message.chat.id,
            message_id=sent_msg.message_id,
            parse_mode='Markdown'
        )

# --------------------- STARTUP NOTIFICATION ---------------------
if __name__ == "__main__":
    print("🤖 MAXX LIKE BOT IS RUNNING 🏃‍♀️")
    print(f"👑 Owner ID: {OWNER_ID} (Unlimited Access)")
    print(f"📢 Force Join Channel: {FORCE_JOIN_CHANNEL}")
    
    try:
        bot.send_message(OWNER_ID, "🤖 MAXX LIKE BOT IS RUNNING 🏃‍♀️")
    except Exception as e:
        print(f"Could not send startup message to owner: {e}")
    
    bot.infinity_polling()
