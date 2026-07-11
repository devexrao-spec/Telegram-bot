#!/usr/bin/env python3
"""
shop_bot.py - FULLY WORKING VERSION
All premium emojis fixed - uses Unicode emojis instead of tg-emoji tags
"""

import os
import json
import threading
import re
from datetime import datetime

import requests
import telebot
from telebot import types
from telebot.formatting import apply_html_entities

import firebase_admin
from firebase_admin import credentials, db

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# ======================================================================
# CONFIG
# ======================================================================
BOT_TOKEN = "8644946592:AAGqcXNTd0TRpYSkK3XkwGjXVQMwxTZKoao"
FIREBASE_DB_URL = "https://subhajit-selling-bot-default-rtdb.asia-southeast1.firebasedatabase.app/"
FIREBASE_CRED_PATH = "serviceAccountKey.json"

bot_client = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ======================================================================
# FIREBASE INIT
# ======================================================================
if not firebase_admin._apps:
    if os.path.exists(FIREBASE_CRED_PATH):
        cred = credentials.Certificate(FIREBASE_CRED_PATH)
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
        print("✅ Firebase Connected Successfully!")
    else:
        print(f"❌ ERROR: serviceAccountKey.json not found at {FIREBASE_CRED_PATH}")
        print("⚠️ Bot will run in LIMITED mode (no data save)")

def _safe_ref(path):
    try:
        return db.reference(path)
    except Exception:
        return None

# ======================================================================
# EMOJI FIX - REMOVE tg-emoji TAGS
# ======================================================================
def fix_emojis(text):
    """Remove tg-emoji tags and keep only the emoji characters"""
    if not text:
        return text
    # Remove <tg-emoji> tags but keep emoji content
    text = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text, flags=re.DOTALL)
    return text

# Monkey patch bot methods to auto-fix emojis
original_send = bot_client.send_message
original_edit = bot_client.edit_message_text
original_send_photo = bot_client.send_photo
original_send_video = bot_client.send_video
original_send_audio = bot_client.send_audio
original_send_document = bot_client.send_document
original_send_animation = bot_client.send_animation

def patched_send(chat_id, text, *args, **kwargs):
    if text:
        text = fix_emojis(text)
    return original_send(chat_id, text, *args, **kwargs)

def patched_edit(text, *args, **kwargs):
    if text:
        text = fix_emojis(text)
    return original_edit(text, *args, **kwargs)

def patched_send_photo(chat_id, photo, caption=None, *args, **kwargs):
    if caption:
        caption = fix_emojis(caption)
    return original_send_photo(chat_id, photo, caption=caption, *args, **kwargs)

def patched_send_video(chat_id, video, caption=None, *args, **kwargs):
    if caption:
        caption = fix_emojis(caption)
    return original_send_video(chat_id, video, caption=caption, *args, **kwargs)

def patched_send_audio(chat_id, audio, caption=None, *args, **kwargs):
    if caption:
        caption = fix_emojis(caption)
    return original_send_audio(chat_id, audio, caption=caption, *args, **kwargs)

def patched_send_document(chat_id, document, caption=None, *args, **kwargs):
    if caption:
        caption = fix_emojis(caption)
    return original_send_document(chat_id, document, caption=caption, *args, **kwargs)

def patched_send_animation(chat_id, animation, caption=None, *args, **kwargs):
    if caption:
        caption = fix_emojis(caption)
    return original_send_animation(chat_id, animation, caption=caption, *args, **kwargs)

bot_client.send_message = patched_send
bot_client.edit_message_text = patched_edit
bot_client.send_photo = patched_send_photo
bot_client.send_video = patched_send_video
bot_client.send_audio = patched_send_audio
bot_client.send_document = patched_send_document
bot_client.send_animation = patched_send_animation

# ======================================================================
# RUNTIME COMPATIBILITY LAYER
# ======================================================================
class ReturnCommand(Exception):
    pass

class _BotData:
    ROOT = "bot_data"

    def getData(self, key):
        ref = _safe_ref(f"{self.ROOT}/{key}")
        if ref is None:
            return None
        try:
            return ref.get()
        except Exception:
            return None

    def saveData(self, key, value):
        ref = _safe_ref(f"{self.ROOT}/{key}")
        if ref is None:
            return
        try:
            ref.set(value)
        except Exception:
            pass

    def runCommand(self, cmd_name, options=None):
        run_command_now(cmd_name, options)

    def handleNextCommand(self, cmd_name, options=None):
        uid = CURRENT_USER.get()
        if uid is None:
            return
        ref = _safe_ref(f"pending_next/{uid}")
        if ref is None:
            return
        ref.set({"cmd": cmd_name, "options": json.dumps(options) if options is not None else None,
                  "options_raw": options if isinstance(options, (str, int, float, bool)) else None})

    def sendMessage(self, chat_id, text, parse_mode=None, reply_markup=None, **kw):
        _bot_send(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup, **kw)

    def broadcast(self, code, callback_url=None):
        def _job():
            ref = _safe_ref("users")
            users = {}
            try:
                users = ref.get() or {}
            except Exception:
                users = {}
            total = len(users)
            success = 0
            errors = 0
            for uid in users.keys():
                try:
                    exec(code, {"bot": make_bot_proxy(uid), "u": uid})
                    success += 1
                except Exception:
                    errors += 1
            run_command_now("/broadResult", _BroadcastOptions(total, success, errors))
        threading.Thread(target=_job, daemon=True).start()
        return {"status": "started"}

    def info(self):
        try:
            return bot_client.get_me()
        except Exception:
            return None

class _BroadcastResultData:
    def __init__(self, total, success, errors):
        self.total = total
        self.total_success = success
        self.total_errors = errors

class _BroadcastOptions:
    def __init__(self, total, success, errors):
        self.json = _BroadcastResultData(total, success, errors)

Bot = _BotData()

class _UserData:
    def __init__(self, uid):
        self.uid = str(uid)

    def getData(self, key):
        ref = _safe_ref(f"users/{self.uid}/{key}")
        if ref is None:
            return None
        try:
            return ref.get()
        except Exception:
            return None

    def saveData(self, key, value):
        ref = _safe_ref(f"users/{self.uid}/{key}")
        if ref is None:
            return
        try:
            ref.set(value)
        except Exception:
            pass

class _DateAndTime:
    @staticmethod
    def now(tz="Asia/Kolkata"):
        dt = datetime.now(ZoneInfo(tz))
        return {
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M:%S"),
        }

class _Resource:
    def __init__(self, name, user):
        self.name = name
        self.user = str(user)
        self.ref = _safe_ref(f"resources/{self.name}/{self.user}")

    def value(self):
        if self.ref is None:
            return 0
        try:
            v = self.ref.get()
            return v if v is not None else 0
        except Exception:
            return 0

    def add(self, amount):
        new_val = float(self.value()) + float(amount)
        if self.ref is not None:
            try:
                self.ref.set(new_val)
            except Exception:
                pass
        return new_val

    def cut(self, amount):
        new_val = float(self.value()) - float(amount)
        if self.ref is not None:
            try:
                self.ref.set(new_val)
            except Exception:
                pass
        return new_val

class _Resources:
    @staticmethod
    def anotherRes(name, user):
        return _Resource(name, user)

class _Webhook:
    BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://example.com")

    @classmethod
    def getUrlFor(cls, path, u):
        return f"{cls.BASE_URL}{path}?u={u}"

class _Libs:
    DateAndTime = _DateAndTime
    Resources = _Resources
    Webhook = _Webhook

libs = _Libs()

class _HTTP:
    @staticmethod
    def get(url, **kw):
        return requests.get(url, timeout=kw.pop("timeout", 20), **kw)

    @staticmethod
    def post(url, **kw):
        return requests.post(url, timeout=kw.pop("timeout", 20), **kw)

HTTP = _HTTP()

InlineKeyboardMarkup = types.InlineKeyboardMarkup
InlineKeyboardButton = types.InlineKeyboardButton

def _dict_markup_to_telebot(markup_dict):
    kb = types.InlineKeyboardMarkup()
    for row in markup_dict.get("inline_keyboard", []):
        buttons = []
        for btn in row:
            kwargs = {"text": btn.get("text", "")}
            if "callback_data" in btn:
                kwargs["callback_data"] = btn["callback_data"]
            if "url" in btn:
                kwargs["url"] = btn["url"]
            buttons.append(types.InlineKeyboardButton(**kwargs))
        kb.add(*buttons)
    return kb

def _normalize_markup(reply_markup):
    if reply_markup is None:
        return None
    if isinstance(reply_markup, dict):
        return _dict_markup_to_telebot(reply_markup)
    return reply_markup

def _bot_send(chat_id, text, parse_mode=None, reply_markup=None, disable_web_page_preview=None, **kw):
    try:
        if text:
            text = fix_emojis(text)
        return bot_client.send_message(
            chat_id,
            text,
            parse_mode=_fix_parse_mode(parse_mode),
            reply_markup=_normalize_markup(reply_markup),
            disable_web_page_preview=disable_web_page_preview,
        )
    except Exception as e:
        print(f"[bot.sendMessage error] chat={chat_id}: {e}")
        return None

def _fix_parse_mode(parse_mode):
    if parse_mode is None:
        return None
    return parse_mode.upper() if parse_mode.lower() == "html" else parse_mode

class BotProxy:
    def __init__(self, default_chat_id):
        self.default_chat_id = default_chat_id

    def replyText(self, chat_id, text, parse_mode=None, reply_markup=None, **kw):
        return _bot_send(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup, **kw)

    def sendMessage(self, *args, **kwargs):
        chat_id = kwargs.pop("chat_id", None)
        if chat_id is None and args and not isinstance(args[0], str):
            chat_id = args[0]
            args = args[1:]
        if chat_id is None:
            chat_id = self.default_chat_id

        text = kwargs.pop("text", None)
        if text is None and args:
            text = args[0]
        text = text or ""

        parse_mode = kwargs.pop("parse_mode", None)
        reply_markup = kwargs.pop("reply_markup", None)
        disable_web_page_preview = kwargs.pop("disable_web_page_preview", None)
        return _bot_send(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup,
                          disable_web_page_preview=disable_web_page_preview)

    def editMessageText(self, chat_id=None, message_id=None, text="", parse_mode=None,
                         reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        if text:
            text = fix_emojis(text)
        return bot_client.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode=_fix_parse_mode(parse_mode),
            reply_markup=_normalize_markup(reply_markup),
        )

    def deleteMessage(self, chat_id=None, message_id=None, **kw):
        chat_id = chat_id or self.default_chat_id
        return bot_client.delete_message(chat_id, message_id)

    def sendPhoto(self, chat_id=None, photo=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        if caption:
            caption = fix_emojis(caption)
        return bot_client.send_photo(chat_id, photo, caption=caption,
                                      parse_mode=_fix_parse_mode(parse_mode),
                                      reply_markup=_normalize_markup(reply_markup))

    def sendVideo(self, chat_id=None, video=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        if caption:
            caption = fix_emojis(caption)
        return bot_client.send_video(chat_id, video, caption=caption,
                                      parse_mode=_fix_parse_mode(parse_mode),
                                      reply_markup=_normalize_markup(reply_markup))

    def sendAudio(self, chat_id=None, audio=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        if caption:
            caption = fix_emojis(caption)
        return bot_client.send_audio(chat_id, audio, caption=caption,
                                      parse_mode=_fix_parse_mode(parse_mode),
                                      reply_markup=_normalize_markup(reply_markup))

    def sendDocument(self, chat_id=None, document=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        if caption:
            caption = fix_emojis(caption)
        return bot_client.send_document(chat_id, document, caption=caption,
                                         parse_mode=_fix_parse_mode(parse_mode),
                                         reply_markup=_normalize_markup(reply_markup))

    def sendSticker(self, chat_id=None, sticker=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        return bot_client.send_sticker(chat_id, sticker, reply_markup=_normalize_markup(reply_markup))

    def sendAnimation(self, chat_id=None, animation=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        if caption:
            caption = fix_emojis(caption)
        return bot_client.send_animation(chat_id, animation, caption=caption,
                                          parse_mode=_fix_parse_mode(parse_mode),
                                          reply_markup=_normalize_markup(reply_markup))

    def answerCallbackQuery(self, callback_query_id, text=None, show_alert=False, **kw):
        return bot_client.answer_callback_query(callback_query_id, text=text, show_alert=show_alert)

def make_bot_proxy(default_chat_id):
    return BotProxy(default_chat_id)

# ======================================================================
# CONTEXT - For handleNextCommand
# ======================================================================
import contextvars
CURRENT_USER = contextvars.ContextVar("CURRENT_USER", default=None)

class _MessageProxy:
    def __init__(self, chat, message_id, from_user, text, date=None, real_message=None):
        self.chat = chat
        self.message_id = message_id
        self.from_user = from_user
        self.text = text
        self.date = date
        self._real = real_message

    def __getattr__(self, item):
        if self._real is not None:
            return getattr(self._real, item)
        raise AttributeError(item)

class _FakeChat:
    def __init__(self, chat_id):
        self.id = chat_id

class _FakeUser:
    def __init__(self, uid):
        self.id = int(uid)
        self.first_name = "User"

def _build_ctx(uid, message_proxy, params, options):
    return {
        "bot": make_bot_proxy(message_proxy.chat.id),
        "User": _UserData(uid),
        "u": str(uid),
        "message": message_proxy,
        "params": params,
        "options": options,
    }

def _get_pending(uid):
    ref = _safe_ref(f"pending_next/{uid}")
    if ref is None:
        return None
    try:
        data = ref.get()
    except Exception:
        data = None
    if not data:
        return None
    opts = data.get("options_raw")
    if opts is None and data.get("options"):
        try:
            opts = json.loads(data["options"])
        except Exception:
            opts = None
    return {"cmd": data.get("cmd"), "options": opts}

def _clear_pending(uid):
    ref = _safe_ref(f"pending_next/{uid}")
    if ref is not None:
        try:
            ref.delete()
        except Exception:
            pass

def _invoke(cmd_name, uid, message_proxy, params, options):
    fn = COMMANDS.get(cmd_name)
    if fn is None:
        return
    token = CURRENT_USER.set(str(uid))
    try:
        ctx = _build_ctx(uid, message_proxy, params, options)
        fn(ctx)
    except ReturnCommand:
        pass
    except Exception as e:
        print(f"[command error] {cmd_name} for user {uid}: {e}")
    finally:
        CURRENT_USER.reset(token)

def run_command_now(cmd_name, options=None):
    uid = CURRENT_USER.get()
    if uid is None:
        return
    proxy = _MessageProxy(chat=_FakeChat(int(uid)), message_id=None,
                           from_user=_FakeUser(uid), text=cmd_name)
    _invoke(cmd_name, uid, proxy, "", options)

def _mark_known_user(uid):
    ref = _safe_ref(f"users/{uid}/known")
    if ref is not None:
        try:
            ref.set(True)
        except Exception:
            pass

# ======================================================================
# ALL COMMANDS - WITH FIXED EMOJIS (No tg-emoji tags)
# ======================================================================

def cmd__ChangeAnyUserBal(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break
    if is_Admin != True:
        bot.replyText(
            u,
            "🚫 You Are Not This Bot Admin",
            parse_mode="html"
        )
        raise ReturnCommand()

    bot.replyText( chat_id = message.chat.id,
        text = f"""💡 Send User Telegram Id & Amount

    ⚠️ Use Format : <code>{message.chat.id} 10</code>

    Add - Before Amount To Deduct Balance Like -10""",
    parse_mode = "html")

    Bot.handleNextCommand("/ChangeAnyUserBal2")

def cmd__ChangeAnyUserBal2(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break
    if is_Admin != True:
        bot.replyText(
            u,
            "🚫 You Are Not This Bot Admin",
            parse_mode="html"
        )
        raise ReturnCommand()

    now = libs.DateAndTime.now("Asia/Kolkata")
    date = now["date"]  
    time = now["time"][:5] 
    year, month, day = date.split("-")
    hour, minute = time.split(":")
    hour = int(hour)
    ampm = "am"
    if hour >= 12:
        ampm = "pm"
    if hour > 12:
        hour -= 12
    if hour == 0:
        hour = 12

    MONTHS = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr","05": "May", "06": "Jun", "07": "Jul", "08": "Aug","09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}

    EasyTime = f"{int(day)} {MONTHS[month]}, {hour:02}:{minute} {ampm}"

    AdmAC=Bot.getData("AdmAC") or []

    P=message.text.split(" ")
    usr=P[0]
    amt=P[1]
    user = f"""<a href="tg://user?id={usr}">{usr}</a>"""

    libs.Resources.anotherRes('Balance', user=usr).add(float(amt))

    bot.replyText(u,f"""💴 Account Of {user} Was Increased By {amt}

    💰 Final Balance = {libs.Resources.anotherRes('Balance', user=usr).value()}""")
 
    ADBT=Bot.getData("ADBT") or "0"
    if ADBT!="0":
        bot.replyText(usr,f"""{ADBT}""")
    
    r=Bot.getData("PerRefer") or 0
    act=f"Added {amt} Rs To {usr} Account"
    AdmAC.append(f"📆 Time: {EasyTime}\n👥 By {message.from_user.first_name} [ID: <code>{u}</code>]\n🔍 Action: {act}")

    Bot.saveData("AdmAC",AdmAC)

    bot.replyText(usr,f"""💰 Admin Gave You A Increase In Balance By {amt}""")

# ======================================================================
# ALL OTHER COMMANDS - Using only Unicode emojis (no tg-emoji)
# ======================================================================

def cmd__SHOPADDKEY(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break

    if is_Admin != True:
        bot.replyText(u, "🚫 You Are Not This Bot Admin", parse_mode="html")
        raise ReturnCommand()

    if not params:
        bot.sendMessage(
            "Usage:\n\n"
            "/SHOPADDKEY 1 → Drip 1d\n"
            "/SHOPADDKEY 2 → Stricks 10d"
        )
        raise ReturnCommand()

    if params == "1":
        bot.sendMessage(
            "🛒 DRIP CLIENT APK MOD\n\n"
            "Send 1d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "drip_1d_keys", "title": "🛒 DRIP CLIENT APK MOD\n1d Key"})
        raise ReturnCommand()
    elif params == "2":
        bot.sendMessage(
            "🛒 DRIP CLIENT APK MOD\n\n"
            "Send 3d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "drip_3d_keys", "title": "🛒 DRIP CLIENT APK MOD\n3d Key"})
        raise ReturnCommand()
    elif params == "3":
        bot.sendMessage(
            "🛒 DRIP CLIENT APK MOD\n\n"
            "Send 7d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "drip_7d_keys", "title": "🛒 DRIP CLIENT APK MOD\n7d Key"})
        raise ReturnCommand()
    elif params == "4":
        bot.sendMessage(
            "🛒 DRIP CLIENT APK MOD\n\n"
            "Send 15d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "drip_15d_keys", "title": "🛒 DRIP CLIENT APK MOD\n15d Key"})
        raise ReturnCommand()
    elif params == "5":
        bot.sendMessage(
            "🛒 DRIP CLIENT APK MOD\n\n"
            "Send 30d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "drip_30d_keys", "title": "🛒 DRIP CLIENT APK MOD\n30d Key"})
        raise ReturnCommand()
    elif params == "6":
        bot.sendMessage(
            "🛒 PRIME-HOOK-MOD\n\n"
            "Send 1d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "HG_1d_keys", "title": "🛒 PRIME-HOOK-MOD\n1d Key"})
        raise ReturnCommand()
    elif params == "7":
        bot.sendMessage(
            "🛒 PRIME-HOOK-MOD\n\n"
            "Send 7d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "HG_7d_keys", "title": "🛒 HG-CHEATS ANDROID\n7d Key"})
        raise ReturnCommand()
    elif params == "8":
        bot.sendMessage(
            "🛒 PRIME-HOOK-MOD\n\n"
            "Send 10d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "HG_10d_keys", "title": "🛒 HG-CHEATS ANDROID\n10d Key"})
        raise ReturnCommand()
    elif params == "9":
        bot.sendMessage(
            "🛒 PRIME-HOOK-MOD\n\n"
            "Send 30d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "HG_30d_keys", "title": "🛒 HG-CHEATS ANDROID\n30d Key"})
        raise ReturnCommand()
    elif params == "101":
        bot.sendMessage(
            "🛒 PROXY SERVER [DR-CL]\n\n"
            "Send 1d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "PATO_1d_keys", "title": "🛒 PROXY SERVER [DR-CL]\n1d Key"})
        raise ReturnCommand()
    elif params == "10":
        bot.sendMessage(
            "🛒 PROXY SERVER [DR-CL]\n\n"
            "Send 3d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "PATO_3d_keys", "title": "🛒 PROXY SERVER [DR-CL]\n3d Key"})
        raise ReturnCommand()
    elif params == "11":
        bot.sendMessage(
            "🛒 PROXY SERVER [DR-CL]\n\n"
            "Send 7d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "PATO_7d_keys", "title": "🛒 PROXY SERVER [DR-CL]\n7d Key"})
        raise ReturnCommand()
    elif params == "12":
        bot.sendMessage(
            "🛒 PROXY SERVER [DR-CL]\n\n"
            "Send 15d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "PATO_15d_keys", "title": "🛒 PROXY SERVER [DR-CL]\n10d Key"})
        raise ReturnCommand()
    elif params == "13":
        bot.sendMessage(
            "🛒 PRIME-HOOK-MOD APK\n\n"
            "Send 5d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "PRIME_5d_keys", "title": "🛒 PRIME-HOOK-MOD APK\n5d Key"})
        raise ReturnCommand()
    elif params == "14":
        bot.sendMessage(
            "🛒 PRIME-HOOK-MOD APK\n\n"
            "Send 10d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "PRIME_10d_keys", "title": "🛒 PRIME-HOOK-MOD APK\n10d Key"})
        raise ReturnCommand()
    elif params == "15":
        bot.sendMessage(
            "🛒 BR MOD ROOT\n\n"
            "Send 10d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "ROOT_10d_keys", "title": "🛒 BR MOD ROOT\n10d Key"})
        raise ReturnCommand()
    elif params == "306":
        bot.sendMessage(
            "🛒 PRIME MOD 💀\n\n"
            "Send 1d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "HG_1d_keys", "title": "🛒 PRIME MOD 💀\n1d Key"})
        raise ReturnCommand()
    elif params == "307":
        bot.sendMessage(
            "🛒 PRIME MOD 💀\n\n"
            "Send 3d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "HG_3d_keys", "title": "🛒 PRIME MOD 💀\n3d Key"})
        raise ReturnCommand()
    elif params == "308":
        bot.sendMessage(
            "🛒 PRIME MOD 💀\n\n"
            "Send 7d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "HG_7d_keys", "title": "🛒 PRIME MOD 💀\n7d Key"})
        raise ReturnCommand()
    elif params == "309":
        bot.sendMessage(
            "🛒 PRIME MOD 💀\n\n"
            "Send 14d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "HG_14d_keys", "title": "🛒 PRIME MOD 💀\n14d Key"})
        raise ReturnCommand()
    elif params == "310":
        bot.sendMessage(
            "🛒 PRIME MOD 💀\n\n"
            "Send 21d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "HG_21d_keys", "title": "🛒 PRIME MOD 💀\n21d Key"})
        raise ReturnCommand()
    elif params == "16":
        bot.sendMessage(
            "🛒 BR MOD ROOT\n\n"
            "Send 20d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )
        Bot.handleNextCommand("/SHOPADDKEY1", options={"key": "ROOT_20d_keys", "title": "🛒 BR MOD ROOT\n20d Key"})
        raise ReturnCommand()
    else:
        bot.sendMessage("❌ Invalid option.\nUse:\n/setprice 1\n/setprice 2")

def cmd__SHOPADDKEY1(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    if message.text == "/cancel":
        bot.sendMessage("❌ Cancelled", parse_mode="html")
        raise ReturnCommand()

    if not options or "key" not in options:
        bot.sendMessage("❌ System Error: Key type missing.")
        raise ReturnCommand()

    try:
        key_value = message.text.strip()

        if len(key_value) < 3:
            bot.sendMessage("❌ Invalid Key.")
            Bot.handleNextCommand("/SHOPADDKEY1", options=options)
            raise ReturnCommand()

        stock_key = options["key"]
        title = options.get("title", "Product")

        existing_data = Bot.getData(stock_key)

        if not existing_data:
            keys_list = []
        elif isinstance(existing_data, str):
            keys_list = [existing_data]
        else:
            keys_list = existing_data

        keys_list.append(key_value)
        Bot.saveData(stock_key, keys_list)

        bot.sendMessage(
            f"✅ Key Added Successfully\n\n"
            f"{title}\n"
            f"🔑 <code>{key_value}</code>\n"
            f"📦 Total Stock: {len(keys_list)}",
            parse_mode="html"
        )

    except Exception as e:
        bot.sendMessage(f"❌ Error: {e}")

def cmd__SHOPADD_PM(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    if not params:
        bot.sendMessage("❌ Usage:\n/SHOPADD_PM <number>")
        raise ReturnCommand()

    products = {
        "1":  ("drip_1d_price",  "DRIP CLIENT APK MOD\n1 Days"),
        "2":  ("drip_3d_price",  "DRIP CLIENT APK MOD\n3 Days"),
        "3":  ("drip_7d_price",  "DRIP CLIENT APK MOD\n7 Days"),
        "4":  ("drip_15d_price",  "DRIP CLIENT APK MOD\n15 Days"),
        "5":  ("drip_30d_price",  "DRIP CLIENT APK MOD\n30 Days"),
        "6":  ("drip_1d_reseller_price",  "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n1 Days"),
        "7":  ("drip_3d_reseller_price",  "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n3 Days"),
        "8":  ("drip_7d_reseller_price",  "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n7 Days"),
        "9":  ("drip_15d_reseller_price",  "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n15 Days"),
        "10": ("drip_30d_reseller_price",  "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n30 Days"),
        "11": ("HG_1d_price",  "🛒 HG-CHEATS ANDROID\n1 Days"),
        "12": ("HG_7d_price",  "🛒 HG-CHEATS ANDROID\n7 Days"),
        "13": ("HG_10d_price",  "🛒 HG-CHEATS ANDROID\n10 Days"),
        "14": ("HG_30d_price",  "🛒 HG-CHEATS ANDROID\n30 Days"),
        "15": ("HG_1d_reseller_price",  "👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n1 Days"),
        "16": ("HG_7d_reseller_price",  "👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n7 Days"),
        "17": ("HG_10d_reseller_price",  "👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n10 Days"),
        "18": ("HG_30d_reseller_price",  "👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n30 Days"),
        "191": ("PATO_1d_price",  "🛒 PROXY SERVER [DR-CL]\n1 Days"),
        "19": ("PATO_3d_price",  "🛒 PROXY SERVER [DR-CL]\n3 Days"),
        "20": ("PATO_7d_price",  "🛒 PROXY SERVER [DR-CL]\n7 Days"),
        "21": ("PATO_15d_price",  "🛒 PROXY SERVER [DR-CL]\n10 Days"),
        "221": ("PATO_1d_reseller_price",  "👑 RESELLER PANEL\n🛒 PROXY SERVER [DR-CL]\n1 Days"),
        "22": ("PATO_3d_reseller_price",  "👑 RESELLER PANEL\n🛒 PROXY SERVER [DR-CL]\n3 Days"),
        "23": ("PATO_7d_reseller_price",  "👑 RESELLER PANEL\n🛒 PROXY SERVER [DR-CL]\n7 Days"),
        "24": ("PATO_15d_reseller_price",  "👑 RESELLER PANEL\n🛒 PROXY SERVER [DR-CL]\n10 Days"),
        "25": ("PRIME_5d_price",  "🛒 PRIME-HOOK-MOD APK\n5 Days"),
        "26": ("PRIME_10d_price",  "🛒 PRIME-HOOK-MOD APK\n10 Days"),
        "27": ("PRIME_5d_reseller_price",  "👑 RESELLER PANEL\n🛒 PRIME-HOOK-MOD APK\n5 Days"),
        "28": ("PRIME_10d_reseller_price",  "👑 RESELLER PANEL\n🛒 PRIME-HOOK-MOD APK\n10 Days"),
        "29": ("ROOT_10d_price",  "🛒 BR MOD ROOT\n10 Days"),
        "30": ("ROOT_20d_price",  "🛒 BR MOD ROOT\n20 Days"),
        "31": ("ROOT_10d_reseller_price",  "👑 RESELLER PANEL\n🛒 BR MOD ROOT\n10 Days"),
        "32": ("ROOT_20d_reseller_price",  "👑 RESELLER PANEL\n🛒 BR MOD ROOT\n20 Days"),
        "311": ("HG_1d_price", "🛒 HG-CHEATS ANDROID\n1 Days"),
        "312": ("HG_3d_price", "🛒 HG-CHEATS ANDROID\n3 Days"),
        "313": ("HG_7d_price", "🛒 HG-CHEATS ANDROID\n7 Days"),
        "314": ("HG_14d_price", "🛒 HG-CHEATS ANDROID\n14 Days"),
        "315": ("HG_21d_price", "🛒 HG-CHEATS ANDROID\n21 Days"),
        "316": ("HG_1d_reseller_price", "👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n1 Days"),
        "317": ("HG_3d_reseller_price", "👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n3 Days"),
        "318": ("HG_7d_reseller_price", "👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n7 Days"),
        "319": ("HG_14d_reseller_price", "👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n14 Days"),
        "320": ("HG_21d_reseller_price", "👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n21 Days"),
    }

    if params in products:
        data_name, title = products[params]
        Bot.runCommand("/SHOPADD_PM1", options={"key": data_name, "title": title})
        raise ReturnCommand()
    else:
        bot.sendMessage("❌ Invalid option number.")

def cmd__SHOPADD_PM1(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    key_name = options.get("key")
    title = options.get("title")

    if not key_name or not key_name:
        bot.sendMessage("❌ Product configuration error.")
        raise ReturnCommand()

    bot.sendMessage(
        f"🛒 {title}\n\n"
        "Send key price (numbers only).\n\n"
        "Type /cancel to stop.",
        parse_mode="html"
    )

    Bot.handleNextCommand("/SHOPADD_PM2", options={"key": key_name, "title": title})

def cmd__SHOPADD_PM2(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    now = libs.DateAndTime.now("Asia/Kolkata")
    date = now["date"]  
    time = now["time"][:5] 
    year, month, day = date.split("-")
    hour, minute = time.split(":")
    hour = int(hour)
    ampm = "am"
    if hour >= 12:
        ampm = "pm"
    if hour > 12:
        hour -= 12
    if hour == 0:
        hour = 12

    MONTHS = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
    }

    EasyTime = f"{int(day)} {MONTHS[month]}, {hour:02}:{minute} {ampm}"
    AdmAC = Bot.getData("AdmAC") or []

    if message.text == "/cancel":
        bot.sendMessage("❌ Cancelled", parse_mode="html")
        raise ReturnCommand()

    try:
        rate = float(message.text)
        price_key = options["key"]
        title = options["title"]

        Bot.saveData(price_key, rate)

        bot.sendMessage(
            f"✅ Successfully Set\n\n"
            f"{title} Price = ₹{rate}",
            parse_mode="html"
        )
        act = f"{title} Price = ₹{rate}"
        AdmAC.append(
            f"📆 Time: {EasyTime}\n"
            f"👥 By {message.from_user.first_name} "
            f"[ID: <code>{u}</code>]\n"
            f"🔍 Action: {act}"
        )
        Bot.saveData("AdmAC", AdmAC)

    except:
        bot.sendMessage(
            "❌ Invalid number.\n"
            "Send numeric value like 90\n\n"
            "Type /cancel to stop."
        )
        Bot.handleNextCommand("/SHOPADD_PM2", options=options)

def cmd__SHOPADMIN_P1(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('👑 RESELLER 1D', callback_data='/SHOPADD_PM 6'))
    markup.add(InlineKeyboardButton('1D Price', callback_data='/SHOPADD_PM 1'), InlineKeyboardButton('Add 1D Key', callback_data='/SHOPADDKEY 1'))
    markup.add(InlineKeyboardButton('👑 RESELLER 3D', callback_data='/SHOPADD_PM 7'))
    markup.add(InlineKeyboardButton('3D Price', callback_data='/SHOPADD_PM 2'), InlineKeyboardButton('Add 3D Key', callback_data='/SHOPADDKEY 2'))
    markup.add(InlineKeyboardButton('👑 RESELLER 7D', callback_data='/SHOPADD_PM 8'))
    markup.add(InlineKeyboardButton('7D Price', callback_data='/SHOPADD_PM 3'), InlineKeyboardButton('Add 7D Key', callback_data='/SHOPADDKEY 3'))
    markup.add(InlineKeyboardButton('👑 RESELLER 15D', callback_data='/SHOPADD_PM 9'))
    markup.add(InlineKeyboardButton('15D Price', callback_data='/SHOPADD_PM 4'), InlineKeyboardButton('Add 15D Key', callback_data='/SHOPADDKEY 4'))
    markup.add(InlineKeyboardButton('👑 RESELLER 30D', callback_data='/SHOPADD_PM 10'))
    markup.add(InlineKeyboardButton('30D Price', callback_data='/SHOPADD_PM 5'), InlineKeyboardButton('Add 30D Key', callback_data='/SHOPADDKEY 5'))
    markup.add(InlineKeyboardButton('🔙 Back', callback_data='/setshop_psue'))

    def get_old(day):
        price = Bot.getData("drip_" + str(day) + "d_price") or 0
        reseller = Bot.getData("drip_" + str(day) + "d_reseller_price") or 0
        stock = Bot.getData("drip_" + str(day) + "d_keys") or []
        if not stock:
            st = "❌ Out of Stock"
        elif len(stock) <= 2:
            st = "⚠️ Only " + str(len(stock)) + " left!"
        else:
            st = "✅ In Stock"
        return price, reseller, st

    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p15, r15, s15 = get_old(15)
    p30, r30, s30 = get_old(30)

    TXT = (
        "🎮 🛒 DRIP CLIENT MOD✅\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 1D Reseller: ₹{r1}\n💰 1D Price: ₹{p1}\n📦 {s1}\n\n"
        f"👑 3D Reseller: ₹{r3}\n💰 3D Price: ₹{p3}\n📦 {s3}\n\n"
        f"👑 7D Reseller: ₹{r7}\n💰 7D Price: ₹{p7}\n📦 {s7}\n\n"
        f"👑 15D Reseller: ₹{r15}\n💰 15D Price: ₹{p15}\n📦 {s15}\n\n"
        f"👑 30D Reseller: ₹{r30}\n💰 30D Price: ₹{p30}\n📦 {s30}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 Select duration below:"
    )

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=TXT,
        reply_markup=markup
    )

def cmd__SHOPADMIN_P2(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('👑 RESELLER 1D', callback_data='/SHOPADD_PM 316'))
    markup.add(InlineKeyboardButton('1D Price', callback_data='/SHOPADD_PM 311'), InlineKeyboardButton('Add 1D Key', callback_data='/SHOPADDKEY 306'))
    markup.add(InlineKeyboardButton('👑 RESELLER 3D', callback_data='/SHOPADD_PM 317'))
    markup.add(InlineKeyboardButton('3D Price', callback_data='/SHOPADD_PM 312'), InlineKeyboardButton('Add 3D Key', callback_data='/SHOPADDKEY 307'))
    markup.add(InlineKeyboardButton('👑 RESELLER 7D', callback_data='/SHOPADD_PM 318'))
    markup.add(InlineKeyboardButton('7D Price', callback_data='/SHOPADD_PM 313'), InlineKeyboardButton('Add 7D Key', callback_data='/SHOPADDKEY 308'))
    markup.add(InlineKeyboardButton('👑 RESELLER 14D', callback_data='/SHOPADD_PM 319'))
    markup.add(InlineKeyboardButton('14D Price', callback_data='/SHOPADD_PM 314'), InlineKeyboardButton('Add 14D Key', callback_data='/SHOPADDKEY 309'))
    markup.add(InlineKeyboardButton('👑 RESELLER 21D', callback_data='/SHOPADD_PM 320'))
    markup.add(InlineKeyboardButton('21D Price', callback_data='/SHOPADD_PM 315'), InlineKeyboardButton('Add 21D Key', callback_data='/SHOPADDKEY 310'))
    markup.add(InlineKeyboardButton('🔙 Back', callback_data='/setshop_psue'))

    def get_old(day):
        price = Bot.getData("HG_" + str(day) + "d_price") or 0
        reseller = Bot.getData("HG_" + str(day) + "d_reseller_price") or 0
        stock = Bot.getData("HG_" + str(day) + "d_keys") or []
        if not stock:
            st = "❌ Out of Stock"
        elif len(stock) <= 2:
            st = "⚠️ Only " + str(len(stock)) + " left!"
        else:
            st = "✅ In Stock"
        return price, reseller, st

    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p10, r10, s10 = get_old(14)
    p21, r21, s21 = get_old(21)

    TXT = (
        "📦 PRIME MOD 💀\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 1D Reseller: ₹{r1}\n💰 1D Price: ₹{p1}\n📦 {s1}\n\n"
        f"👑 3D Reseller: ₹{r3}\n💰 3D Price: ₹{p3}\n📦 {s3}\n\n"
        f"👑 7D Reseller: ₹{r7}\n💰 7D Price: ₹{p7}\n📦 {s7}\n\n"
        f"👑 14D Reseller: ₹{r10}\n💰 14D Price: ₹{p10}\n📦 {s10}\n\n"
        f"👑 21D Reseller: ₹{r21}\n💰 21D Price: ₹{p21}\n📦 {s21}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 Select duration below:"
    )

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=TXT,
        reply_markup=markup
    )

def cmd__SHOPADMIN_P3(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('👑 RESELLER 1D', callback_data='/SHOPADD_PM 221'))
    markup.add(InlineKeyboardButton('1D Price', callback_data='/SHOPADD_PM 191'), InlineKeyboardButton('Add 1D Key', callback_data='/SHOPADDKEY 101'))
    markup.add(InlineKeyboardButton('👑 RESELLER 3D', callback_data='/SHOPADD_PM 22'))
    markup.add(InlineKeyboardButton('3D Price', callback_data='/SHOPADD_PM 19'), InlineKeyboardButton('Add 3D Key', callback_data='/SHOPADDKEY 10'))
    markup.add(InlineKeyboardButton('👑 RESELLER 7D', callback_data='/SHOPADD_PM 23'))
    markup.add(InlineKeyboardButton('7D Price', callback_data='/SHOPADD_PM 20'), InlineKeyboardButton('Add 7D Key', callback_data='/SHOPADDKEY 11'))
    markup.add(InlineKeyboardButton('👑 RESELLER 15D', callback_data='/SHOPADD_PM 24'))
    markup.add(InlineKeyboardButton('15D Price', callback_data='/SHOPADD_PM 21'), InlineKeyboardButton('Add 15D Key', callback_data='/SHOPADDKEY 12'))
    markup.add(InlineKeyboardButton('🔙 Back', callback_data='/setshop_psue'))

    def get_old(day):
        price = Bot.getData("PATO_" + str(day) + "d_price") or 0
        reseller = Bot.getData("PATO_" + str(day) + "d_reseller_price") or 0
        stock = Bot.getData("PATO_" + str(day) + "d_keys") or []
        if not stock:
            st = "❌ Out of Stock"
        elif len(stock) <= 2:
            st = "⚠️ Only " + str(len(stock)) + " left!"
        else:
            st = "✅ In Stock"
        return price, reseller, st

    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p15, r15, s15 = get_old(15)

    TXT = (
        "🎮 PROXY SERVER [DR-CL]\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 1D Reseller: ₹{r1}\n💰 1D Price: ₹{p1}\n📦 {s1}\n\n"
        f"👑 3D Reseller: ₹{r3}\n💰 3D Price: ₹{p3}\n📦 {s3}\n\n"
        f"👑 7D Reseller: ₹{r7}\n💰 7D Price: ₹{p7}\n📦 {s7}\n\n"
        f"👑 15D Reseller: ₹{r15}\n💰 15D Price: ₹{p15}\n📦 {s15}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 Select duration below:"
    )

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=TXT,
        reply_markup=markup
    )

def cmd__SHOPADMIN_P4(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('👑 RESELLER 5D', callback_data='/SHOPADD_PM 27'))
    markup.add(InlineKeyboardButton('5D Price', callback_data='/SHOPADD_PM 25'), InlineKeyboardButton('Add 5D Key', callback_data='/SHOPADDKEY 13'))
    markup.add(InlineKeyboardButton('👑 RESELLER 10D', callback_data='/SHOPADD_PM 28'))
    markup.add(InlineKeyboardButton('10D Price', callback_data='/SHOPADD_PM 26'), InlineKeyboardButton('Add 10D Key', callback_data='/SHOPADDKEY 14'))
    markup.add(InlineKeyboardButton('🔙 Back', callback_data='/setshop_psue'))

    def get_old(day):
        price = Bot.getData("PRIME_" + str(day) + "d_price") or 0
        reseller = Bot.getData("PRIME_" + str(day) + "d_reseller_price") or 0
        stock = Bot.getData("PRIME_" + str(day) + "d_keys") or []
        if not stock:
            st = "❌ Out of Stock"
        elif len(stock) <= 2:
            st = "⚠️ Only " + str(len(stock)) + " left!"
        else:
            st = "✅ In Stock"
        return price, reseller, st

    p5, r5, s5 = get_old(5)
    p10, r10, s10 = get_old(10)

    TXT = (
        "🎮 🛒 PRIME-HOOK-MOD APK\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 5D Reseller: ₹{r5}\n💰 5D Price: ₹{p5}\n📦 {s5}\n\n"
        f"👑 10D Reseller: ₹{r10}\n💰 10D Price: ₹{p10}\n📦 {s10}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 Select duration below:"
    )

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=TXT,
        reply_markup=markup
    )

def cmd__SHOPADMIN_P5(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('👑 RESELLER 10D', callback_data='/SHOPADD_PM 31'))
    markup.add(InlineKeyboardButton('10D Price', callback_data='/SHOPADD_PM 29'), InlineKeyboardButton('Add 10D Key', callback_data='/SHOPADDKEY 15'))
    markup.add(InlineKeyboardButton('👑 RESELLER 20D', callback_data='/SHOPADD_PM 32'))
    markup.add(InlineKeyboardButton('20D Price', callback_data='/SHOPADD_PM 30'), InlineKeyboardButton('Add 20D Key', callback_data='/SHOPADDKEY 16'))
    markup.add(InlineKeyboardButton('🔙 Back', callback_data='/setshop_psue'))

    def get_old(day):
        price = Bot.getData("ROOT_" + str(day) + "d_price") or 0
        reseller = Bot.getData("ROOT_" + str(day) + "d_reseller_price") or 0
        stock = Bot.getData("ROOT_" + str(day) + "d_keys") or []
        if not stock:
            st = "❌ Out of Stock"
        elif len(stock) <= 2:
            st = "⚠️ Only " + str(len(stock)) + " left!"
        else:
            st = "✅ In Stock"
        return price, reseller, st

    p10, r10, s10 = get_old(10)
    p20, r20, s20 = get_old(20)

    TXT = (
        "🎮 🛒 BR MOD ROOT\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 10D Reseller: ₹{r10}\n💰 10D Price: ₹{p10}\n📦 {s10}\n\n"
        f"👑 20D Reseller: ₹{r20}\n💰 20D Price: ₹{p20}\n📦 {s20}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 Select duration below:"
    )

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=TXT,
        reply_markup=markup
    )

def cmd__SHOP_P1(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    resellers = Bot.getData("resellers_list") or []
    is_reseller = u in resellers

    p1 = Bot.getData("drip_1d_price") or 108
    p3 = Bot.getData("drip_3d_price") or 260
    p7 = Bot.getData("drip_7d_price") or 360
    p15 = Bot.getData("drip_15d_price") or 560
    p30 = Bot.getData("drip_30d_price") or 810

    rp1 = Bot.getData("drip_1d_reseller_price") or 95
    rp3 = Bot.getData("drip_3d_reseller_price") or 220
    rp7 = Bot.getData("drip_7d_reseller_price") or 320
    rp15 = Bot.getData("drip_15d_reseller_price") or 480
    rp30 = Bot.getData("drip_30d_reseller_price") or 750

    if is_reseller:
        p1, p3, p7, p15, p30 = rp1, rp3, rp7, rp15, rp30

    buy_command = "/buyjai_reseller" if is_reseller else "/buyjai"

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📦 DRIP CLIENT MOD✅ (BEST SELLER 💫)\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📦 Extra 2% discount applied\n"
        "Choose a plan 👇"
    )

    keyboard = [
        [{"text": f"1 DAY - ₹{p1}", "callback_data": f"{buy_command} 1"}],
        [{"text": f"3 DAYS - ₹{p3}", "callback_data": f"{buy_command} 2"}],
        [{"text": f"7 DAYS - ₹{p7}", "callback_data": f"{buy_command} 3"}],
        [{"text": f"15 DAYS - ₹{p15}", "callback_data": f"{buy_command} 4"}],
        [{"text": f"30 DAYS - ₹{p30}", "callback_data": f"{buy_command} 5"}],
        [{"text": "BACK", "callback_data": "/shopnawkk"}]
    ]

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=text,
        reply_markup={"inline_keyboard": keyboard}
    )

def cmd__SHOP_P2(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    resellers = Bot.getData("resellers_list") or []
    is_reseller = u in resellers

    p1 = Bot.getData("PATO_1d_price") or 108
    p7 = Bot.getData("PATO_3d_price") or 360
    p10 = Bot.getData("PATO_7d_price") or 560
    p30 = Bot.getData("PATO_15d_price") or 810

    rp1 = Bot.getData("PATO_1d_reseller_price") or 95
    rp7 = Bot.getData("PATO_3d_reseller_price") or 320
    rp10 = Bot.getData("PATO_7d_reseller_price") or 520
    rp30 = Bot.getData("PATO_15d_reseller_price") or 750

    if is_reseller:
        p1, p7, p10, p30 = rp1, rp7, rp10, rp30

    buy_command = "/buyjai_reseller" if is_reseller else "/buyjai"

    text = """
    ━━━━━━━━━━━━━━━━━━━━
    📦 PROXY SERVER [DR-CL]
    ━━━━━━━━━━━━━━━━━━━━

    Choose a plan 👇
    """

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=text,
        reply_markup={
            "inline_keyboard": [
                [{"text": f"1 Day - ₹{p1}", "callback_data": f"{buy_command} 6"}],
                [{"text": f"3 Days - ₹{p7}", "callback_data": f"{buy_command} 7"}],
                [{"text": f"7 Days - ₹{p10}", "callback_data": f"{buy_command} 8"}],
                [{"text": f"15 Days - ₹{p30}", "callback_data": f"{buy_command} 9"}],
                [{"text": "BACK", "callback_data": "/shopnawkk"}]
            ]
        }
    )

def cmd__SHOP_P3(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    resellers = Bot.getData("resellers_list") or []
    is_reseller = u in resellers

    p3 = Bot.getData("PATO_3d_price") or 260
    p7 = Bot.getData("PATO_7d_price") or 360
    p15 = Bot.getData("PATO_15d_price") or 560

    rp3= Bot.getData("PATO_3d_reseller_price") or 220
    rp7 = Bot.getData("PATO_7d_reseller_price") or 320
    rp15 = Bot.getData("PATO_15d_reseller_price") or 320

    if is_reseller:
        p3 = rp3
        p7 = rp7
        p15 = rp15

    buy_command = "/buyjai_reseller" if is_reseller else "/buyjai"

    text = """
    ━━━━━━━━━━━━━━━━━━━━
    🏷 PATO BLUE APK MOD
    ━━━━━━━━━━━━━━━━━━━━

    Choose a plan 👇
    """

    keyboard = [
        [{"text": f"3 Days - ₹{p3}", "callback_data": f"{buy_command} 10"}],
        [{"text": f"7 Days - ₹{p7}", "callback_data": f"{buy_command} 11"}],
        [{"text": f"15 Days - ₹{p15}", "callback_data": f"{buy_command} 12"}],
        [{"text": "🔙 Back To Menu", "callback_data": "/shopnawkk"}]
    ]

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=text,
        reply_markup={"inline_keyboard": keyboard}
    )

def cmd__SHOP_P4(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    resellers = Bot.getData("resellers_list") or []
    is_reseller = u in resellers

    p1 = Bot.getData("HG_1d_price") or 108
    p3 = Bot.getData("HG_3d_price") or 200
    p7 = Bot.getData("HG_7d_price") or 360
    p14 = Bot.getData("HG_14d_price") or 600
    p21 = Bot.getData("HG_21d_price") or 700

    rp1 = Bot.getData("HG_1d_reseller_price") or 95
    rp3 = Bot.getData("HG_3d_reseller_price") or 180
    rp7 = Bot.getData("HG_7d_reseller_price") or 320
    rp14 = Bot.getData("HG_14d_reseller_price") or 550
    rp21 = Bot.getData("HG_21d_reseller_price") or 650

    if is_reseller:
        p1, p3, p7, p14, p21 = rp1, rp3, rp7, rp14, rp21

    buy_command = "/buyjai_reseller" if is_reseller else "/buyjai"

    text = """
    ━━━━━━━━━━━━━━━━━━━━
    🔥 PRIME HOOK
    ━━━━━━━━━━━━━━━━━━━━

    Choose a plan 👇
    """

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=text,
        reply_markup={
            "inline_keyboard": [
                [{"text": f"1 Day - ₹{p1}", "callback_data": f"{buy_command} 10"}],
                [{"text": f"3 Days - ₹{p3}", "callback_data": f"{buy_command} 11"}],
                [{"text": f"7 Days - ₹{p7}", "callback_data": f"{buy_command} 12"}],
                [{"text": f"14 Days - ₹{p14}", "callback_data": f"{buy_command} 13"}],
                [{"text": f"21 Days - ₹{p21}", "callback_data": f"{buy_command} 14"}],
                [{"text": "BACK", "callback_data": "/shopnawkk"}]
            ]
        }
    )

def cmd__SHOP_P5(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    resellers = Bot.getData("resellers_list") or []
    is_reseller = u in resellers

    p10 = Bot.getData("ROOT_10d_price") or 560
    p20 = Bot.getData("ROOT_20d_price") or 810

    rp10 = Bot.getData("ROOT_10d_reseller_price") or 320
    rp20 = Bot.getData("ROOT_20d_reseller_price") or 750

    if is_reseller:
        p10 = rp10
        p20 = rp20

    buy_command = "/buyjai_reseller" if is_reseller else "/buyjai"

    text = """
    ━━━━━━━━━━━━━━━━━━━━
    🏷 BR MOD ROOT
    ━━━━━━━━━━━━━━━━━━━━

    Choose a plan 👇
    """

    keyboard = [
        [{"text": f"10 Days - ₹{p10}", "callback_data": f"{buy_command} 15"}],
        [{"text": f"20 Days - ₹{p20}", "callback_data": f"{buy_command} 16"}],
        [{"text": "🔙 Back To Menu", "callback_data": "/shopnawkk"}]
    ]

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=text,
        reply_markup={"inline_keyboard": keyboard}
    )

def cmd__START(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    joined = User.getData("joined_date")
    if not joined:
        User.saveData("joined_date", message.date)

    balance = libs.Resources.anotherRes("Balance", user=u).value()

    text = (
        "🌟 WELCOME TO HACK STORE 🌙\n\n"
        "✨ Your ultimate destination for premium mods, cheats & clients!\n\n"
        "🚀 PREMIUM FEATURES\n\n"
        "⚡ Instant Key Delivery\n"
        "💳 Secure Auto-Payment System\n"
        "🛡 100% Anti-Ban Support\n\n"
        f"💰 Your Balance: ₹{balance}"
    )

    bot.sendMessage(
        chat_id=u,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup={
            "inline_keyboard": [
                [{"text": "BUY HACK", "callback_data": "/shopnawkk"}],
                [{"text": "MY KEY", "callback_data": "/orderksk"}, {"text": "PROFILE", "callback_data": "/profilemmm"}],
                [{"text": "HOW TO USE", "callback_data": "/spinj"}, {"text": "SUPPORT", "callback_data": "/supportj"}],
                [{"text": "ADD FUND", "callback_data": "/addpayment"}],
                [{"text": "PAY PROOF", "url": "https://t.me/subhajit_feedback"}, {"text": "DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl"}]
            ]
        }
    )

def cmd__Start(ctx):
    cmd__START(ctx)

def cmd__TUSHAR_AddAdmin(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break
    if is_Admin != True:
        bot.replyText(u, "🚫 You Are Not This Bot Admin", parse_mode="html")
        raise ReturnCommand()

    bot.replyText(chat_id=message.chat.id,text="Send UserID of Admin You Want To Add",parse_mode="html")
    User.saveData("EDMsgID",message.message_id) 
    Bot.handleNextCommand("/TUSHAR_AddAdmin1")

def cmd__TUSHAR_AddAdmin1(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break
    if is_Admin != True:
        bot.replyText(u, "🚫 You Are Not This Bot Admin", parse_mode="html")
        raise ReturnCommand()

    check_user = AllBotAdminss.count(message.text)
    if check_user > 0:
        T="Admin Already Exists"
    else:
        AllBotAdminss.append(message.text)
        Bot.saveData("AllBotAdminss", AllBotAdminss)
        T="Admin Added Successfully"

    Bot.runCommand("/TUSHAR_Admins",options=f"{T}")

    now = libs.DateAndTime.now("Asia/Kolkata")
    date = now["date"]  
    time = now["time"][:5] 
    year, month, day = date.split("-")
    hour, minute = time.split(":")
    hour = int(hour)
    ampm = "am"
    if hour >= 12:
        ampm = "pm"
    if hour > 12:
        hour -= 12
    if hour == 0:
        hour = 12

    MONTHS = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr","05": "May", "06": "Jun", "07": "Jul", "08": "Aug","09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}

    EasyTime = f"{int(day)} {MONTHS[month]}, {hour:02}:{minute} {ampm}"

    AdmAC=Bot.getData("AdmAC") or []
    act=f"Added {message.text} as Bot Admin"
    AdmAC.append(f"📆 Time: {EasyTime}\n👥 By {message.from_user.first_name} [ID: <code>{u}</code>]\n🔍 Action: {act}")
    Bot.saveData("AdmAC",AdmAC)

    Bot.sendMessage(f"{T}")

def cmd__TUSHAR_AdminAction(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break
    if is_Admin != True:
        bot.replyText(u, "🚫 You Are Not This Bot Admin", parse_mode="html")
        raise ReturnCommand()

    AdmAC=Bot.getData("AdmAC") or []
    x=int(len(AdmAC)) 
    latest_10 = AdmAC[-10:][::-1]
    bot.sendMessage("\n\n".join(latest_10))

def cmd__TUSHAR_Admins(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break
    if is_Admin != True:
        bot.replyText(u, "🚫 You Are Not This Bot Admin", parse_mode="html")
        raise ReturnCommand()

    now = libs.DateAndTime.now("Asia/Kolkata")
    date = now["date"]  
    time = now["time"][:5] 
    year, month, day = date.split("-")
    hour, minute = time.split(":")
    hour = int(hour)
    ampm = "am"
    if hour >= 12:
        ampm = "pm"
    if hour > 12:
        hour -= 12
    if hour == 0:
        hour = 12

    MONTHS = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr","05": "May", "06": "Jun", "07": "Jul", "08": "Aug","09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}

    EasyTime = f"{int(day)} {MONTHS[month]}, {hour:02}:{minute} {ampm}"

    AdmAC=Bot.getData("AdmAC") or []

    if str(params)!="None":
        AllBotAdminss.remove(params)
        act=f"Removed {params} from Bot Admin"
        AdmAC.append(f"📆 Time: {EasyTime}\n👥 By {message.from_user.first_name} [ID: <code>{u}</code>]\n🔍 Action: {act}")
        Bot.saveData("AdmAC",AdmAC)

    markup = InlineKeyboardMarkup()
    for admin in AllBotAdminss:
        markup.add(InlineKeyboardButton(text=admin,callback_data="/TUSHAR_Admins "+str(admin)), InlineKeyboardButton(text="❌",callback_data="/TUSHAR_Admins "+str(admin)))
    markup.add(InlineKeyboardButton(text='➕Add Admin',callback_data='/TUSHAR_AddAdmin'))
    markup.add(InlineKeyboardButton(text='🔙Back',callback_data='/admin AP'))

    Bot.saveData("AllBotAdminss",AllBotAdminss)

    e="y"
    T="Here You Can Manage Your Admins"
    if options:
        T=options

    MD=User.getData("EDMsgID") 

    try:
        bot.editMessageText(chat_id=u,message_id=message.message_id,text=T,reply_markup=markup,parse_mode="Html")
        if options:
            e="n"
    except:
        pass
 
    try:
        bot.editMessageText(chat_id=u,message_id=MD,text=T)
        if options:
            e="n"
    except:
        pass

    if e=="n":
        Bot.runCommand ("/admin")

def cmd__add_reseller_process(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    try:
        target_user = str(int(message.text))
    except:
        bot.sendMessage("❌ Invalid User ID.")
        raise ReturnCommand()

    resellers = Bot.getData("resellers_list") or []
    if target_user in [str(u) for u in resellers]:
        bot.sendMessage("⚠️ User already a reseller.")
        raise ReturnCommand()

    resellers.append(target_user)
    Bot.saveData("resellers_list", resellers)

    bot.sendMessage(f"✅ User <code>{target_user}</code> added as Reseller.", parse_mode="html")

    try:
        bot.sendMessage(chat_id=target_user, text="🎉 You are now a Reseller 👑")
    except:
        pass

def cmd__addpayment(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    User.saveData("pay_amount", "")

    try:
        bot.editMessageText(
            chat_id=u,
            message_id=message.message_id,
            text=(
                "💰 ENTER CUSTOM AMOUNT\n\n"
                "Amount: ₹0\n\n"
                "Use the keypad below to enter amount."
            ),
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "1", "callback_data": "/num1"}, {"text": "2", "callback_data": "/num2"}, {"text": "3", "callback_data": "/num3"}],
                    [{"text": "4", "callback_data": "/num4"}, {"text": "5", "callback_data": "/num5"}, {"text": "6", "callback_data": "/num6"}],
                    [{"text": "7", "callback_data": "/num7"}, {"text": "8", "callback_data": "/num8"}, {"text": "9", "callback_data": "/num9"}],
                    [{"text": "❌ CLEAR", "callback_data": "/clearamt"}, {"text": "0", "callback_data": "/num0"}, {"text": "✅ CONFIRM", "callback_data": "/done"}],
                    [{"text": "BACK", "callback_data": "/backkkk"}]
                ]
            }
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

    raise ReturnCommand()

def cmd__addpayment_qr(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amount = User.getData("last_deposit_amount")

    if not amount:
        bot.sendMessage("❌ Amount missing")
        raise ReturnCommand()

    upi = "bablu.xyztb@fam"
    url = "https://fampay.anujbots.xyz/qr.php?upi=" + upi + "&amount=" + str(amount)

    try:
        resp = HTTP.get(url)
        data = resp.json()
    except:
        bot.sendMessage("❌ API ERROR")
        raise ReturnCommand()

    if data.get("status") != "success":
        bot.sendMessage("❌ QR GENERATION FAILED")
        raise ReturnCommand()

    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]

    User.saveData("addpay_order_id", order_id)

    bot.sendPhoto(
        photo=qr_url,
        caption="💰 PAYMENT QR GENERATED\nScan the QR and complete payment.\n\nAmount: ₹" + str(amount),
        parse_mode="HTML",
        reply_markup={
            "inline_keyboard": [
                [{"text": "VERIFY PAYMENT", "callback_data": "/verify_addpay"}],
                [{"text": "CANCEL", "callback_data": "/cancel"}]
            ]
        }
    )

    raise ReturnCommand()

def cmd__addreseller(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False

    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break

    if is_Admin != True:
        bot.replyText(u, "🚫 You Are Not This Bot Admin", parse_mode="html")
        raise ReturnCommand()
    
    bot.sendMessage("📩 Send me id reseller")
    Bot.handleNextCommand("/add_reseller_process")

def cmd__admin(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    if AllBotAdminss == []:
        MAIN_ADMIN = u
        AllBotAdminss.append(MAIN_ADMIN)
        Bot.saveData("AllBotAdminss", AllBotAdminss)
        Bot.saveData("Owner", u)
        is_Admin = True
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break
    if is_Admin != True:
        bot.replyText(u, "🚫 You Are Not This Bot Admin", parse_mode="html")
        raise ReturnCommand()

    now = libs.DateAndTime.now("Asia/Kolkata")
    date = now["date"]  
    time = now["time"][:5] 
    year, month, day = date.split("-")
    hour, minute = time.split(":")
    hour = int(hour)
    ampm = "am"
    if hour >= 12:
        ampm = "pm"
    if hour > 12:
        hour -= 12
    if hour == 0:
        hour = 12

    MONTHS = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr","05": "May", "06": "Jun", "07": "Jul", "08": "Aug","09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}

    EasyTime = f"{int(day)} {MONTHS[month]}, {hour:02}:{minute} {ampm}"

    AdmAC=Bot.getData("AdmAC") or []

    if "BotMode" in str(params):
        P=params.split(" ")
        Bot.saveData("BotMode",str(P[1]))
        act=f"But Mode Turned {P[1]}"
        AdmAC.append(f"📆 Time: {EasyTime}\n👥 By {message.from_user.first_name} [ID: <code>{u}</code>]\n🔍 Action: {act}")
        Bot.saveData("AdmAC",AdmAC)

    BOT_MODE = Bot.getData("BotMode") or "ON"
    botSta = "🟢 On"
    botStatChngeBut = "BotMode OFF"
    if BOT_MODE == "OFF":
        botSta = "🔴 Off"
        botStatChngeBut = "BotMode ON"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text='👑 Admins', callback_data='/TUSHAR_Admins'))
    markup.add(InlineKeyboardButton(text='📣 Broadcast', callback_data='/broadcast'), InlineKeyboardButton(text='🤖 Bot: ' + str(botSta), callback_data='/admin ' + botStatChngeBut))
    markup.add(InlineKeyboardButton(text='💰 Add Balance', callback_data='/ChangeAnyUserBal'), InlineKeyboardButton(text='📝 Recent Admin Actions', callback_data='/TUSHAR_AdminAction'))
    markup.add(InlineKeyboardButton(text='📊 Shop setup', callback_data='/setshop_psue'))
    markup.add(InlineKeyboardButton(text='💰 Add Reseller', callback_data='/addreseller'), InlineKeyboardButton(text='⛔ Remove Reseller', callback_data='/removereseller'))
    markup.add(InlineKeyboardButton(text='📝 Reseller List', callback_data='/resellerlist'))

    TXT = f"""
👋 Welcome {message.from_user.first_name} 🎉

━━━━━━━━━━━━━━━
🤖 Bot Status : {botSta}
━━━━━━━━━━━━━━━
"""

    if str(message.text)=="/admin":
        bot.replyText(u,TXT,reply_markup=markup)
        raise ReturnCommand()
    
    if params or params!=None or options== "AP" or params=="AP":
        try:
            bot.editMessageText(chat_id=u, message_id=message.message_id,text=TXT,reply_markup=markup)
        except:
            pass
        raise ReturnCommand()
    
    bot.replyText(u,TXT,reply_markup=markup)

def cmd__approve_inr(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    bot.deleteMessage(message.chat.id, message.message_id)

    parts = params.split()
    user_id = parts[0]
    amount = float(parts[1])

    libs.Resources.anotherRes("Balance", user=user_id).add(amount)

    bot.sendMessage(chat_id=user_id, text=f"✅ Deposit Approved!\n💰 ₹{amount} Added to your balance.")
    bot.sendMessage("✅ Deposit Completed.")

def cmd__autobuy1(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amount = User.getData("last_deposit_amount")
    pt = User.getData("last_product1")
    plan = User.getData("last_plan") or "Unknown"

    if not amount:
        bot.sendMessage("❌ Amount missing")
        raise ReturnCommand()

    balance = libs.Resources.anotherRes("Balance", user=u).value()
    need = float(amount) - float(balance)
    if need < 0:
        need = 0

    upi = "bablu.xyztb@fam"
    url = "https://fampay.anujbots.xyz/qr.php?upi=" + upi + "&amount=" + str(amount)

    try:
        resp = HTTP.get(url)
        data = resp.json()
    except:
        bot.sendMessage("❌ API ERROR")
        raise ReturnCommand()

    if not data or data.get("status") != "success":
        bot.sendMessage("❌ QR GENERATION FAILED")
        raise ReturnCommand()

    order_id = data["data"]["order_id"]
    qr_url = data["data"]["qr_url"]

    User.saveData("last_order_id", order_id)

    caption = (
    "💰 INSUFFICIENT BALANCE\n\n"
    f"┣ Product: {pt}\n"
    f"┣ Plan:{plan}\n"
    f"┣ Price: ₹{amount}\n"
    f"┣ Your Balance: ₹{balance}\n"
    f"┗ Need: ₹{need}"
    )

    bot.sendPhoto(
        photo=qr_url,
        caption=caption,
        parse_mode="HTML",
        reply_markup={
            "inline_keyboard": [
                [{"text": "VERIFY PAYMENT", "callback_data": "/autobuyi"}],
                [{"text": "CANCEL", "callback_data": "/cancel"}]
            ]
        }
    )

    raise ReturnCommand()

def cmd__autobuyi(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    order_id = User.getData("last_order_id")

    if not order_id:
        bot.sendMessage("❌ No active payment found.")
        raise ReturnCommand()

    url = "https://fampay.anujbots.xyz/verify.php?order_id=" + str(order_id) + "&api_key=FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8"

    resp = HTTP.get(url)

    try:
        data = resp.json()
    except:
        bot.sendMessage("❌ API ERROR")
        raise ReturnCommand()

    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        bal = libs.Resources.anotherRes("Balance", user=u)
        bal.add(amount)
        User.saveData("last_order_id", "")

        bot.sendMessage(
            "✅ Payment Success!\n\n"
            "💰 Added ₹" + str(amount) + "\n"
            "💳 New Balance: ₹" + str(bal.value()),
            parse_mode="HTML"
        )
        AllBotAdminss = Bot.getData("AllBotAdminss") or []
        for admin in AllBotAdminss:
            bot.sendMessage(
                chat_id=admin,
                text=
                "✅ New Payment Received!\n\n"
                "👤 User ID: <code>" + str(u) + "</code>\n"
                "💰 Amount: ₹" + str(amount) + "\n"
                "🧾 Order ID: <code>" + str(order_id) + "</code>\n"
                "💳 User Balance: ₹" + str(bal.value()),
                parse_mode="HTML")
    else:
        bot.sendMessage("❌ Payment Not Received\n\nPlease complete the payment and try again.", parse_mode="HTML")

def cmd__backkkk(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    balance = libs.Resources.anotherRes("Balance", user=u).value()

    text = (
        "🌟 WELCOME TO HACK STORE 🌙\n\n"
        "✨ Your ultimate destination for premium mods, cheats & clients!\n\n"
        "🚀 PREMIUM FEATURES\n\n"
        "⚡ Instant Key Delivery\n"
        "💳 Secure Auto-Payment System\n"
        "🛡 100% Anti-Ban Support\n\n"
        f"💰 Your Balance: ₹{balance}"
    )

    try:
        bot.editMessageText(
            chat_id=u,
            message_id=message.message_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup={
                "inline_keyboard": [
                    [{"text": "BUY HACK", "callback_data": "/shopnawkk"}],
                    [{"text": "MY KEY", "callback_data": "/orderksk"}, {"text": "PROFILE", "callback_data": "/profilemmm"}],
                    [{"text": "HOW TO USE", "callback_data": "/spinj"}, {"text": "SUPPORT", "callback_data": "/supportj"}],
                    [{"text": "ADD FUND", "callback_data": "/addpayment"}],
                    [{"text": "PAY PROOF", "url": "https://t.me/subhajit_feedback"}, {"text": "DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl"}]
                ]
            }
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

    raise ReturnCommand()

def cmd__broadResult(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    try:
        get = options.json
        total = get.total
        success = get.total_success
        fail = get.total_errors
    
        txt = f"""
🎙️ Broadcast Done

👥 Total: {total}
✅ Success: {success}
❌ Failed: {fail}
"""
        bot.sendMessage(txt)
    except:
        bot.sendMessage("❌ Broadcast Data Process Failed")

def cmd__broadcast(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    admins = Bot.getData("AllBotAdminss") or []
    if str(u) not in admins:
        raise ReturnCommand()

    if options == None:
        bot.replyText(u, "🎙️ Send Any Message To Broadcast in HTML\n\nTo Cancel: /cancel", parse_mode="html")
        Bot.handleNextCommand("/broadcast", options=True)
        raise ReturnCommand()
    else:
        if message.text == "/cancel":
            bot.sendMessage("❌ Cancelled", parse_mode="html")
            raise ReturnCommand()

    def broadcast(method, txt, fileId):
        typ = method.lower()
        if method == "Message":
            code = f"""bot.sendMessage(chat_id=u, text='''{txt}''', parse_mode="html")"""
        elif str(txt) == "None":
            code = f"""bot.send{method}(chat_id=u, {typ}="{fileId}")"""
        else:
            code = f"""bot.send{method}(chat_id=u, {typ}="{fileId}", caption='''{txt}''', parse_mode="html")"""
        return code

    txt = message.caption if message.caption else message.text
    entities = message.caption_entities if message.caption else message.entities
    if entities:
        txt = apply_html_entities(txt, entities, {})

    if message.photo:
        code = broadcast("Photo", txt, message.photo[-1].file_id)
    elif message.text:
        code = broadcast("Message", txt, None)
    elif message.video:
        code = broadcast("Video", txt, message.video.file_id)
    elif message.audio:
        code = broadcast("Audio", txt, message.audio.file_id)
    elif message.document:
        code = broadcast("Document", txt, message.document.file_id)
    elif message.sticker:
        code = broadcast("Sticker", txt, message.sticker.file_id)
    elif message.animation:
        code = broadcast("Animation", txt, message.animation.file_id)
    else:
        bot.sendMessage("❌ Wrong File Format!", parse_mode="html")
        raise ReturnCommand()

    url = libs.Webhook.getUrlFor("/broadResult", u)
    task = Bot.broadcast(code=code, callback_url=url)
    Bot.saveData(task, None)
    bot.sendMessage("🔁 Broadcast Processing...", parse_mode="html")

def cmd__buybahha(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    now = libs.DateAndTime.now("Asia/Kolkata")
    date = now["date"]
    time = now["time"][:5]
    year, month, day = date.split("-")
    hour, minute = time.split(":")
    hour = int(hour)
    ampm = "am"
    if hour >= 12:
        ampm = "pm"
    if hour > 12:
        hour -= 12
    if hour == 0:
        hour = 12

    MONTHS = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
    }

    EasyTime = f"{int(day)} {MONTHS[month]}, {hour:02}:{minute} {ampm}"

    price_name = options.get("price")
    key_name = options.get("key")
    title = options.get("title")

    if not price_name or not key_name or not title:
        bot.sendMessage("❌ Product configuration error.")
        raise ReturnCommand()

    price = Bot.getData(price_name) or 0

    try:
        price = float(price)
    except:
        bot.sendMessage("❌ Invalid price.")
        raise ReturnCommand()

    if price <= 0:
        bot.sendMessage("❌ Price not set.")
        raise ReturnCommand()

    keys = Bot.getData(key_name) or []

    if len(keys) == 0:
        bot.sendMessage("❌ Out of Stock.")
        raise ReturnCommand()

    balance = libs.Resources.anotherRes("Balance", user=u)

    if balance.value() < price:
        User.saveData("last_deposit_amount", price)
        User.saveData("last_product", title)
        Bot.runCommand("/autobuy1")
        raise ReturnCommand()

    libs.Resources.anotherRes("Balance", user=u).cut(price)
    libs.Resources.anotherRes("Order", user=u).add(1)

    key = str(keys[0])
    keys.pop(0)
    Bot.saveData(key_name, keys)

    bot.sendMessage(
        f"🛒 {title}\n\n"
        f"🔑 <b>Your Key:</b>\n<code>{key}</code>\n\n"
        f"💰 Deducted: ₹{price}\n"
        f"📦 Remaining Stock: {len(keys)}\n"
        f"📦 Time: {EasyTime}\n\n"
        f"📢 <b>ALL FILES UPDATE</b>\n"
        f"@SUBHAJIT_UPDATES",
        parse_mode="HTML"
    )

    AdmAC = User.getData("userhAC") or []
    AdmAC.append(
        f"📆 {EasyTime}\n"
        f"👤 {message.from_user.first_name} [{u}]\n"
        f"💰 ₹{price}\n"
        f"🔑 {key}\n"
    )
    User.saveData("userhAC", AdmAC)

    admin_id = Bot.getData("admin_id")
    if admin_id:
        try:
            bot.sendMessage(chat_id=admin_id, text=f"🛒 New Sale\n\n👤 {u}\n📦 {title}\n💰 ₹{price}")
        except:
            pass

    raise ReturnCommand()

def cmd__buyjai(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    if not params:
        bot.sendMessage("❌ Invalid Product")
        raise ReturnCommand()

    if params == "1":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","1 Day")
        Bot.runCommand("/buybahha", options={"price": "drip_1d_price", "key": "drip_1d_keys", "title": "DRIP CLIENT APK MOD\n1 Day"})
        raise ReturnCommand()
    if params == "2":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","3 Day")
        Bot.runCommand("/buybahha", options={"price": "drip_3d_price", "key": "drip_3d_keys", "title": "DRIP CLIENT APK MOD\n3 Days"})
        raise ReturnCommand()
    if params == "3":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","7 Day")
        Bot.runCommand("/buybahha", options={"price": "drip_7d_price", "key": "drip_7d_keys", "title": "DRIP CLIENT APK MOD\n7 Days"})
        raise ReturnCommand()
    if params == "4":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","15 Day")
        Bot.runCommand("/buybahha", options={"price": "drip_15d_price", "key": "drip_15d_keys", "title": "DRIP CLIENT APK MOD\n15 Days"})
        raise ReturnCommand()
    if params == "5":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","30 Day")
        Bot.runCommand("/buybahha", options={"price": "drip_30d_price", "key": "drip_30d_keys", "title": "DRIP CLIENT APK MOD\n30 Days"})
        raise ReturnCommand()
    if params == "6":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","1 Day")
        Bot.runCommand("/buybahha", options={"price": "PATO_1d_price", "key": "PATO_1d_keys", "title": "PROXY SERVER [DR-CL]\n1 Day"})
        raise ReturnCommand()
    if params == "7":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","3 Day")
        Bot.runCommand("/buybahha", options={"price": "PATO_3d_price", "key": "PATO_3d_keys", "title": "PROXY SERVER [DR-CL]\n3 Days"})
        raise ReturnCommand()
    if params == "8":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","7 Day")
        Bot.runCommand("/buybahha", options={"price": "PATO_7d_price", "key": "PATO_7d_keys", "title": "PROXY SERVER [DR-CL]\n7 Days"})
        raise ReturnCommand()
    if params == "9":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","10 Day")
        Bot.runCommand("/buybahha", options={"price": "PATO_15d_price", "key": "PATO_15d_keys", "title": "PROXY SERVER [DR-CL]\n10 Days"})
        raise ReturnCommand()
    if params == "10":
        User.saveData("last_product1", "PRIME MOD")
        User.saveData("last_plan","1 Day")
        Bot.runCommand("/buybahha", options={"price": "HG_1d_price", "key": "HG_1d_keys", "title": "PRIME-HOOK\n1 Day"})
        raise ReturnCommand()
    elif params == "11":
        User.saveData("last_product1", "PRIME MOD")
        User.saveData("last_plan","3 Day")
        Bot.runCommand("/buybahha", options={"price": "HG_3d_price", "key": "HG_3d_keys", "title": "PRIME-HOOK\n3 Days"})
        raise ReturnCommand()
    elif params == "12":
        User.saveData("last_product1", "HG-CHEATS ANDROID")
        User.saveData("last_plan","7 Day")
        Bot.runCommand("/buybahha", options={"price": "HG_7d_price", "key": "HG_7d_keys", "title": "PRIME-HOOK\n7 Days"})
        raise ReturnCommand()
    elif params == "13":
        User.saveData("last_product1", "PRIME MOD")
        User.saveData("last_plan","14 Day")
        Bot.runCommand("/buybahha", options={"price": "HG_14d_price", "key": "HG_14d_keys", "title": "PRIME-HOOK\n14 Days"})
        raise ReturnCommand()
    elif params == "14":
        User.saveData("last_product1", "PRIME MOD")
        User.saveData("last_plan","21 Day")
        Bot.runCommand("/buybahha", options={"price": "HG_21d_price", "key": "HG_21d_keys", "title": "PRIME-HOOK\n21 Days"})
        raise ReturnCommand()

    bot.sendMessage("❌ Invalid Product ID")

def cmd__buyjai_reseller(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    if not params:
        bot.sendMessage("❌ Invalid Product")
        raise ReturnCommand()

    if params == "1":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","1 Day")
        Bot.runCommand("/buybahha", options={"price": "drip_1d_reseller_price", "key": "drip_1d_keys", "title": "🎮 DRIP CLIENT APK MOD\n1 Day"})
        raise ReturnCommand()
    if params == "2":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","3 Day")
        Bot.runCommand("/buybahha", options={"price": "drip_3d_reseller_price", "key": "drip_3d_keys", "title": "🎮 DRIP CLIENT APK MOD\n3 Days"})
        raise ReturnCommand()
    if params == "3":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","7 Day")
        Bot.runCommand("/buybahha", options={"price": "drip_7d_reseller_price", "key": "drip_7d_keys", "title": "🎮 DRIP CLIENT APK MOD\n7 Days"})
        raise ReturnCommand()
    if params == "4":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","15 Day")
        Bot.runCommand("/buybahha", options={"price": "drip_15d_reseller_price", "key": "drip_15d_keys", "title": "🎮 DRIP CLIENT APK MOD\n15 Days"})
        raise ReturnCommand()
    if params == "5":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","30 Day")
        Bot.runCommand("/buybahha", options={"price": "drip_30d_reseller_price", "key": "drip_30d_keys", "title": "🎮 DRIP CLIENT APK MOD\n30 Days"})
        raise ReturnCommand()
    if params == "6":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","1 Day")
        Bot.runCommand("/buybahha", options={"price": "PATO_1d_reseller_price", "key": "PATO_1d_keys", "title": "📦 PROXY SERVER [DR-CL]\n1 Day"})
        raise ReturnCommand()
    if params == "7":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","3 Day")
        Bot.runCommand("/buybahha", options={"price": "PATO_3d_reseller_price", "key": "PATO_3d_keys", "title": "📦 PROXY SERVER [DR-CL]\n3 Days"})
        raise ReturnCommand()
    if params == "8":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","7 Day")
        Bot.runCommand("/buybahha", options={"price": "PATO_7d_reseller_price", "key": "PATO_7d_keys", "title": "📦 PROXY SERVER [DR-CL]\n7 Days"})
        raise ReturnCommand()
    if params == "9":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","10 Day")
        Bot.runCommand("/buybahha", options={"price": "PATO_15d_reseller_price", "key": "PATO_15d_keys", "title": "📦 PROXY SERVER [DR-CL]\n10 Days"})
        raise ReturnCommand()
    if params == "10":
        User.saveData("last_product1", "PRIME MOD 💀")
        User.saveData("last_plan","1 Day")
        Bot.runCommand("/buybahha", options={"price": "HG_1d_reseller_price", "key": "HG_1d_keys", "title": "🛒 PRIME MOD 💀\n1 Day"})
        raise ReturnCommand()
    elif params == "11":
        User.saveData("last_product1", "PRIME MOD 💀")
        User.saveData("last_plan","3 Day")
        Bot.runCommand("/buybahha", options={"price": "HG_3d_reseller_price", "key": "HG_3d_keys", "title": "🛒 PRIME MOD 💀\n3 Days"})
        raise ReturnCommand()
    elif params == "12":
        User.saveData("last_product1", "HG-CHEATS ANDROID")
        User.saveData("last_plan","7 Day")
        Bot.runCommand("/buybahha", options={"price": "HG_7d_reseller_price", "key": "HG_7d_keys", "title": "🛒 PRIME MOD 💀\n7 Days"})
        raise ReturnCommand()
    elif params == "13":
        User.saveData("last_product1", "PRIME MOD 💀")
        User.saveData("last_plan","14 Day")
        Bot.runCommand("/buybahha", options={"price": "HG_14d_reseller_price", "key": "HG_14d_keys", "title": "🛒 PRIME MOD 💀\n14 Days"})
        raise ReturnCommand()
    elif params == "14":
        User.saveData("last_product1", "PRIME MOD 💀")
        User.saveData("last_plan","21 Day")
        Bot.runCommand("/buybahha", options={"price": "HG_21d_reseller_price", "key": "HG_21d_keys", "title": "🛒 PRIME MOD 💀\n21 Days"})
        raise ReturnCommand()

    bot.sendMessage("❌ Invalid Product ID")

def cmd__cancel(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    msg_id = message.message_id

    try:
        bot.deleteMessage(chat_id=u, message_id=msg_id)
    except:
        pass

    bot.sendMessage(chat_id=u, text="❌ Cancelled", parse_mode="HTML")

def cmd__clearamt(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = User.getData("pay_amount") or ""

    if amt == "":
        raise ReturnCommand()

    User.saveData("pay_amount", "")

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text="💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹0\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__done(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = User.getData("pay_amount")

    if not amt:
        bot.sendMessage("❌ Enter amount first")
        raise ReturnCommand()

    User.saveData("last_deposit_amount", amt)
    Bot.runCommand("/addpayment_qr")

# Number buttons
def cmd__num0(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "") + "0"
    User.saveData("pay_amount", amt)
    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=f"💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__num1(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "") + "1"
    User.saveData("pay_amount", amt)
    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=f"💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__num2(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "") + "2"
    User.saveData("pay_amount", amt)
    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=f"💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__num3(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "") + "3"
    User.saveData("pay_amount", amt)
    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=f"💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__num4(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "") + "4"
    User.saveData("pay_amount", amt)
    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=f"💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__num5(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "") + "5"
    User.saveData("pay_amount", amt)
    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=f"💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__num6(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "") + "6"
    User.saveData("pay_amount", amt)
    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=f"💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__num7(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "") + "7"
    User.saveData("pay_amount", amt)
    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=f"💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__num8(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "") + "8"
    User.saveData("pay_amount", amt)
    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=f"💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__num9(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "") + "9"
    User.saveData("pay_amount", amt)
    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=f"💰 ENTER CUSTOM AMOUNT\n\nAmount: ₹{amt}\n\nUse the keypad below to enter amount.",
        parse_mode="HTML",
        reply_markup=message.reply_markup
    )

def cmd__orderksk(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    textn = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📦 MY ORDERS\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "You haven't placed any orders yet.\n"
        "Tap 🛒 Shop Now to get started!"
    )

    AdmAC = User.getData("userhAC") or []

    if not AdmAC:
        try:
            bot.editMessageText(
                chat_id=u,
                message_id=message.message_id,
                text=textn,
                parse_mode="HTML",
                reply_markup={"inline_keyboard": [[{"text": "BACK", "callback_data": "/backkkk"}]]}
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                raise e
    else:
        latest_10 = AdmAC[-10:][::-1]
        safe_list = []
        for item in latest_10:
            if item:
                safe_list.append(str(item))

        if not safe_list:
            bot.sendMessage("No valid entries found.")
        else:
            text = "\n\n".join(safe_list)
            try:
                bot.editMessageText(
                    chat_id=u,
                    message_id=message.message_id,
                    text=text,
                    reply_markup={"inline_keyboard": [[{"text": "BACK", "callback_data": "/backkkk"}]]}
                )
            except Exception as e:
                if "message is not modified" not in str(e):
                    raise e

    raise ReturnCommand()

def cmd__profilemmm(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    balance = libs.Resources.anotherRes("Balance", user=u).value()
    hh = libs.Resources.anotherRes("Order", user=u).value()
    first_name = message.from_user.first_name or "User"

    joined = User.getData("joined_date")
    if not joined:
        member_since = "Today"
    else:
        diff = int(message.date) - int(joined)
        if diff < 86400:
            member_since = "Today"
        elif diff < 86400 * 7:
            member_since = str(diff // 86400) + " days ago"
        elif diff < 86400 * 30:
            member_since = str(diff // (86400 * 7)) + " weeks ago"
        else:
            member_since = str(diff // (86400 * 30)) + " months ago"

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👤 YOUR PROFILE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 Name: {first_name}\n"
        f"🆔 User ID: {u}\n"
        f"💰 Balance: ₹{balance}\n"
        f"📅 Member Since: {member_since}\n"
        f"🛒 Total Orders: {hh}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    try:
        bot.editMessageText(
            chat_id=u,
            message_id=message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "BUY HACK", "callback_data": "/shopnawkk"}, {"text": "MY KEY", "callback_data": "/orderksk"}],
                    [{"text": "BACK", "callback_data": "/backkkk"}]
                ]
            }
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

    raise ReturnCommand()

def cmd__reject_inr(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    bot.deleteMessage(message.chat.id, message.message_id)
    try:
        parts = params.split()
        user_id = parts[0]
        amount = parts[1]

        bot.sendMessage(chat_id=user_id, text=f"❌ Deposit Rejected!\n💰 ₹{amount} Request has been declined.")
        bot.sendMessage("❌ Deposit Rejected.")
    except:
        bot.sendMessage("⚠️ Error: Invalid format.\nUse: /reject user_id amount")

def cmd__remove_reseller_process(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    try:
        target_user = str(int(message.text))
    except:
        bot.sendMessage("❌ Invalid User ID.")
        raise ReturnCommand()

    resellers = Bot.getData("resellers_list") or []
    if target_user not in [str(u) for u in resellers]:
        bot.sendMessage("⚠️ User is not a reseller.")
        raise ReturnCommand()

    resellers = [u for u in resellers if str(u) != target_user]
    Bot.saveData("resellers_list", resellers)

    bot.sendMessage(f"✅ User <code>{target_user}</code> removed from Resellers.", parse_mode="html")

    try:
        bot.sendMessage(chat_id=target_user, text="❌ You are no longer a Reseller.")
    except:
        pass

def cmd__removereseller(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    bot.sendMessage(u, "📩 Send me reseller id to remove")
    Bot.handleNextCommand("/remove_reseller_process")

def cmd__resellerlist(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    resellers = Bot.getData("resellers_list") or []

    if not resellers:
        bot.sendMessage("📭 No resellers found.")
        raise ReturnCommand()

    text = "👑 <b>Reseller List</b>\n"
    text += "━━━━━━━━━━━━━━━━━━\n\n"

    count = 1
    for user_id in resellers:
        text += f"{count}. 🆔 <code>{user_id}</code>\n"
        count += 1

    text += "\n━━━━━━━━━━━━━━━━━━"
    text += f"\n📊 Total Resellers: {len(resellers)}"

    bot.sendMessage(text, parse_mode="html")

def cmd__setMyCommands(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    bot_token = Bot.info().token

    commands = [{'command': 'start', 'description': ' START TO BUY'}]
    url = f'https://api.telegram.org/bot{bot_token}/setMyCommands'
    headers = {'Content-type': 'application/json'}
    data = {'commands': commands}
    res = HTTP.post(url, headers=headers, json=data).json()
    bot.replyText(u, str(res))

def cmd__setshop_psue(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    if AllBotAdminss == []:
        MAIN_ADMIN = u
        AllBotAdminss.append(MAIN_ADMIN)
        Bot.saveData("AllBotAdminss", AllBotAdminss)
        Bot.saveData("Owner", u)
        is_Admin = True
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break
    if is_Admin != True:
        bot.replyText(u, "🚫 You Are Not This Bot Admin", parse_mode="html")
        raise ReturnCommand()

    now = libs.DateAndTime.now("Asia/Kolkata")
    date = now["date"]  
    time = now["time"][:5] 
    year, month, day = date.split("-")
    hour, minute = time.split(":")
    hour = int(hour)
    ampm = "am"
    if hour >= 12:
        ampm = "pm"
    if hour > 12:
        hour -= 12
    if hour == 0:
        hour = 12

    MONTHS = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr","05": "May", "06": "Jun", "07": "Jul", "08": "Aug","09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}

    EasyTime = f"{int(day)} {MONTHS[month]}, {hour:02}:{minute} {ampm}"
    AdmAC=Bot.getData("AdmAC") or []

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text='DRIP CLIENT MOD✅', callback_data='/SHOPADMIN_P1'))
    markup.add(InlineKeyboardButton(text='PROXY SERVER [DR-CL]', callback_data='/SHOPADMIN_P3'))
    markup.add(InlineKeyboardButton(text='PRIME MOD 💀', callback_data='/SHOPADMIN_P2'))
    markup.add(InlineKeyboardButton(text='🔙Back',callback_data='/admin AP'))

    TXT = f"""
👋 Welcome {message.from_user.first_name} 🎉

━━━━━━━━━━━━━━━
SHOP 🛍️ MOOD
━━━━━━━━━━━━━━━
"""

    if str(message.text)=="/setshop_psue":
        bot.replyText(u,TXT,reply_markup=markup)
        raise ReturnCommand()
    
    if params or params!=None or options== "AP" or params=="AP":
        try:
            bot.editMessageText(chat_id=u, message_id=message.message_id,text=TXT,reply_markup=markup)
        except:
            pass
        raise ReturnCommand()
    
    bot.replyText(u,TXT,reply_markup=markup)

def cmd__shopnawkk(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    text = """
    ━━━━━━━━━━━━━━━━━━━━
    🛒 PANNEL STORE — SHOP
    ━━━━━━━━━━━━━━━━━━━━

    📦 Choose a product:
    """

    try:
        bot.editMessageText(
            chat_id=u,
            message_id=message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "DRIP CLIENT NON-ROOT", "callback_data": "/SHOP_P1"}],
                    [{"text": "PROXY SERVER [DR-CL]", "callback_data": "/SHOP_P2"}],
                    [{"text": "PRIME HOOK", "callback_data": "/SHOP_P4"}],
                    [{"text": "BACK", "callback_data": "/backkkk"}]
                ]
            }
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

    raise ReturnCommand()

def cmd__spinj(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    text = """
    🎥 Watch the full tutorial video below

    👇
    """

    try:
        bot.editMessageText(
            chat_id=u,
            message_id=message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "Watch Tutorial", "url": "https://t.me/hehehehhhsljg/162"}],
                    [{"text": "BACK", "callback_data": "/backkkk"}]
                ]
            }
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

    raise ReturnCommand()

def cmd__start(ctx):
    cmd__START(ctx)

def cmd__supportj(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    
    text = """
    ━━━━━━━━━━━━━━━━━━━━
    💬 Support — Seller 🛡
    ━━━━━━━━━━━━━━━━━━━━

    Need help? We're here for you! ⚡

    📩 Telegram: ⭐

    <a href="https://t.me/UR_SUBHAJIT0">𝐒υʜᴀᎫιт</a> ⭐

    💡 Include your User ID (from Profile)
    when contacting for faster help.
    """

    try:
        bot.editMessageText(
            chat_id=u,
            message_id=message.message_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup={
                "inline_keyboard": [
                    [{"text": "WHATSAPP", "url": "https://wa.me/917908696630"}],
                    [{"text": "BACK", "callback_data": "/backkkk"}]
                ]
            }
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

    raise ReturnCommand()

def cmd__verify_addpay(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    order_id = User.getData("addpay_order_id")

    if not order_id:
        bot.sendMessage("❌ No active payment found.")
        raise ReturnCommand()

    url = "https://fampay.anujbots.xyz/verify.php?order_id=" + str(order_id) + "&api_key=FAM_71926bab274bc0d39d201e6730983da3163651ddb106b6c8"

    resp = HTTP.get(url)
    data = resp.json()

    if data.get("status") == "success":
        amount = float(data["data"]["amount"])
        bal = libs.Resources.anotherRes("Balance", user=u)
        bal.add(amount)
        User.saveData("addpay_order_id", "")
        bot.sendMessage("✅ Payment Success\n\n💰 Added ₹" + str(amount))
    else:
        bot.sendMessage("❌ Payment Not Received")

# ======================================================================
# COMMAND REGISTRY
# ======================================================================
COMMANDS = {
    "/ChangeAnyUserBal": cmd__ChangeAnyUserBal,
    "/ChangeAnyUserBal2": cmd__ChangeAnyUserBal2,
    "/SHOPADDKEY": cmd__SHOPADDKEY,
    "/SHOPADDKEY1": cmd__SHOPADDKEY1,
    "/SHOPADD_PM": cmd__SHOPADD_PM,
    "/SHOPADD_PM1": cmd__SHOPADD_PM1,
    "/SHOPADD_PM2": cmd__SHOPADD_PM2,
    "/SHOPADMIN_P1": cmd__SHOPADMIN_P1,
    "/SHOPADMIN_P2": cmd__SHOPADMIN_P2,
    "/SHOPADMIN_P3": cmd__SHOPADMIN_P3,
    "/SHOPADMIN_P4": cmd__SHOPADMIN_P4,
    "/SHOPADMIN_P5": cmd__SHOPADMIN_P5,
    "/SHOP_P1": cmd__SHOP_P1,
    "/SHOP_P2": cmd__SHOP_P2,
    "/SHOP_P3": cmd__SHOP_P3,
    "/SHOP_P4": cmd__SHOP_P4,
    "/SHOP_P5": cmd__SHOP_P5,
    "/START": cmd__START,
    "/Start": cmd__Start,
    "/TUSHAR_AddAdmin": cmd__TUSHAR_AddAdmin,
    "/TUSHAR_AddAdmin1": cmd__TUSHAR_AddAdmin1,
    "/TUSHAR_AdminAction": cmd__TUSHAR_AdminAction,
    "/TUSHAR_Admins": cmd__TUSHAR_Admins,
    "/add_reseller_process": cmd__add_reseller_process,
    "/addpayment": cmd__addpayment,
    "/addpayment_qr": cmd__addpayment_qr,
    "/addreseller": cmd__addreseller,
    "/admin": cmd__admin,
    "/approve_inr": cmd__approve_inr,
    "/autobuy1": cmd__autobuy1,
    "/autobuyi": cmd__autobuyi,
    "/backkkk": cmd__backkkk,
    "/broadResult": cmd__broadResult,
    "/broadcast": cmd__broadcast,
    "/buybahha": cmd__buybahha,
    "/buyjai": cmd__buyjai,
    "/buyjai_reseller": cmd__buyjai_reseller,
    "/cancel": cmd__cancel,
    "/clearamt": cmd__clearamt,
    "/done": cmd__done,
    "/num0": cmd__num0,
    "/num1": cmd__num1,
    "/num2": cmd__num2,
    "/num3": cmd__num3,
    "/num4": cmd__num4,
    "/num5": cmd__num5,
    "/num6": cmd__num6,
    "/num7": cmd__num7,
    "/num8": cmd__num8,
    "/num9": cmd__num9,
    "/orderksk": cmd__orderksk,
    "/profilemmm": cmd__profilemmm,
    "/reject_inr": cmd__reject_inr,
    "/remove_reseller_process": cmd__remove_reseller_process,
    "/removereseller": cmd__removereseller,
    "/resellerlist": cmd__resellerlist,
    "/setMyCommands": cmd__setMyCommands,
    "/setshop_psue": cmd__setshop_psue,
    "/shopnawkk": cmd__shopnawkk,
    "/spinj": cmd__spinj,
    "/start": cmd__start,
    "/supportj": cmd__supportj,
    "/verify_addpay": cmd__verify_addpay,
}

# ======================================================================
# DISPATCHER
# ======================================================================
def _invoke(cmd_name, uid, message_proxy, params, options):
    fn = COMMANDS.get(cmd_name)
    if fn is None:
        return
    token = CURRENT_USER.set(str(uid))
    try:
        ctx = _build_ctx(uid, message_proxy, params, options)
        fn(ctx)
    except ReturnCommand:
        pass
    except Exception as e:
        print(f"[command error] {cmd_name} for user {uid}: {e}")
    finally:
        CURRENT_USER.reset(token)

@bot_client.message_handler(func=lambda m: True, content_types=[
    "text", "photo", "video", "audio", "document", "sticker", "animation"
])
def on_message(message):
    uid = str(message.from_user.id)
    _mark_known_user(uid)

    text = message.text or message.caption or ""

    if text.startswith("/"):
        cmd, _, params = text.partition(" ")
        _clear_pending(uid) if cmd == "/cancel" else None
        proxy = _MessageProxy(chat=message.chat, message_id=message.message_id,
                               from_user=message.from_user, text=message.text,
                               date=message.date, real_message=message)
        _invoke(cmd, uid, proxy, params, None)
        return

    pending = _get_pending(uid)
    if pending and pending.get("cmd"):
        _clear_pending(uid)
        proxy = _MessageProxy(chat=message.chat, message_id=message.message_id,
                               from_user=message.from_user, text=message.text,
                               date=message.date, real_message=message)
        _invoke(pending["cmd"], uid, proxy, "", pending.get("options"))

@bot_client.callback_query_handler(func=lambda c: True)
def on_callback(call):
    uid = str(call.from_user.id)
    _mark_known_user(uid)

    data = call.data or ""
    cmd, _, params = data.partition(" ")

    proxy = _MessageProxy(chat=call.message.chat, message_id=call.message.message_id,
                           from_user=call.from_user, text=data,
                           date=call.message.date, real_message=call.message)

    try:
        bot_client.answer_callback_query(call.id)
    except Exception:
        pass

    _invoke(cmd, uid, proxy, params, None)

# ======================================================================
# MAIN
# ======================================================================
import time

def main():
    print("🤖 Bot Starting...")
    print(f"📡 Bot Token: {BOT_TOKEN[:10]}...")
    print(f"🔥 Firebase URL: {FIREBASE_DB_URL}")
    print("📁 Service Account: " + ("✅ Found" if os.path.exists(FIREBASE_CRED_PATH) else "❌ NOT FOUND!"))
    print("🔄 Starting Long Polling...")
    while True:
        try:
            bot_client.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"[polling crashed, restarting in 5s] {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
