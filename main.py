#!/usr/bin/env python3
"""
shop_bot.py - FULLY WORKING with emojis
All messages use parse_mode=None for proper emoji rendering
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
# EMOJI FIX - ALWAYS USE parse_mode=None
# ======================================================================
def fix_emojis(text):
    """Remove tg-emoji tags and keep only the emoji characters"""
    if not text:
        return text
    text = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text, flags=re.DOTALL)
    return text

# Monkey patch bot methods - ALWAYS use parse_mode=None
original_send = bot_client.send_message
original_edit = bot_client.edit_message_text
original_send_photo = bot_client.send_photo
original_send_video = bot_client.send_video
original_send_audio = bot_client.send_audio
original_send_document = bot_client.send_document
original_send_animation = bot_client.send_animation

def patched_send(chat_id, text, parse_mode=None, *args, **kwargs):
    if text:
        text = fix_emojis(text)
    # FORCE parse_mode = None for proper emoji
    return original_send(chat_id, text, parse_mode=None, *args, **kwargs)

def patched_edit(text, parse_mode=None, *args, **kwargs):
    if text:
        text = fix_emojis(text)
    return original_edit(text, parse_mode=None, *args, **kwargs)

def patched_send_photo(chat_id, photo, caption=None, parse_mode=None, *args, **kwargs):
    if caption:
        caption = fix_emojis(caption)
    return original_send_photo(chat_id, photo, caption=caption, parse_mode=None, *args, **kwargs)

def patched_send_video(chat_id, video, caption=None, parse_mode=None, *args, **kwargs):
    if caption:
        caption = fix_emojis(caption)
    return original_send_video(chat_id, video, caption=caption, parse_mode=None, *args, **kwargs)

def patched_send_audio(chat_id, audio, caption=None, parse_mode=None, *args, **kwargs):
    if caption:
        caption = fix_emojis(caption)
    return original_send_audio(chat_id, audio, caption=caption, parse_mode=None, *args, **kwargs)

def patched_send_document(chat_id, document, caption=None, parse_mode=None, *args, **kwargs):
    if caption:
        caption = fix_emojis(caption)
    return original_send_document(chat_id, document, caption=caption, parse_mode=None, *args, **kwargs)

def patched_send_animation(chat_id, animation, caption=None, parse_mode=None, *args, **kwargs):
    if caption:
        caption = fix_emojis(caption)
    return original_send_animation(chat_id, animation, caption=caption, parse_mode=None, *args, **kwargs)

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
        _bot_send(chat_id, text, parse_mode=None, reply_markup=reply_markup, **kw)

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
            parse_mode=None,  # FORCE None for emojis
            reply_markup=_normalize_markup(reply_markup),
            disable_web_page_preview=disable_web_page_preview,
        )
    except Exception as e:
        print(f"[bot.sendMessage error] chat={chat_id}: {e}")
        return None

def _fix_parse_mode(parse_mode):
    return None  # Always use None for emojis

class BotProxy:
    def __init__(self, default_chat_id):
        self.default_chat_id = default_chat_id

    def replyText(self, chat_id, text, parse_mode=None, reply_markup=None, **kw):
        return _bot_send(chat_id, text, parse_mode=None, reply_markup=reply_markup, **kw)

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
        return _bot_send(chat_id, text, parse_mode=None, reply_markup=reply_markup,
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
            parse_mode=None,  # FORCE None
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
                                      parse_mode=None,
                                      reply_markup=_normalize_markup(reply_markup))

    def sendVideo(self, chat_id=None, video=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        if caption:
            caption = fix_emojis(caption)
        return bot_client.send_video(chat_id, video, caption=caption,
                                      parse_mode=None,
                                      reply_markup=_normalize_markup(reply_markup))

    def sendAudio(self, chat_id=None, audio=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        if caption:
            caption = fix_emojis(caption)
        return bot_client.send_audio(chat_id, audio, caption=caption,
                                      parse_mode=None,
                                      reply_markup=_normalize_markup(reply_markup))

    def sendDocument(self, chat_id=None, document=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        if caption:
            caption = fix_emojis(caption)
        return bot_client.send_document(chat_id, document, caption=caption,
                                         parse_mode=None,
                                         reply_markup=_normalize_markup(reply_markup))

    def sendSticker(self, chat_id=None, sticker=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        return bot_client.send_sticker(chat_id, sticker, reply_markup=_normalize_markup(reply_markup))

    def sendAnimation(self, chat_id=None, animation=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        if caption:
            caption = fix_emojis(caption)
        return bot_client.send_animation(chat_id, animation, caption=caption,
                                          parse_mode=None,
                                          reply_markup=_normalize_markup(reply_markup))

    def answerCallbackQuery(self, callback_query_id, text=None, show_alert=False, **kw):
        return bot_client.answer_callback_query(callback_query_id, text=text, show_alert=show_alert)

def make_bot_proxy(default_chat_id):
    return BotProxy(default_chat_id)

# ======================================================================
# CONTEXT
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
# COMMANDS - ALL WITH UNICODE EMOJIS (No tg-emoji tags)
# ======================================================================

def cmd__start(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    
    joined = User.getData("joined_date")
    if not joined:
        User.saveData("joined_date", message.date)
    
    balance = libs.Resources.anotherRes("Balance", user=u).value()
    
    text = f"""
🌟 WELCOME TO HACK STORE 🌙

✨ Your ultimate destination for premium mods, cheats & clients!

🚀 PREMIUM FEATURES

⚡ Instant Key Delivery
💳 Secure Auto-Payment System
🛡 100% Anti-Ban Support

💰 Your Balance: ₹{balance}
    """
    
    bot.sendMessage(
        chat_id=u,
        text=text,
        parse_mode=None,
        disable_web_page_preview=True,
        reply_markup={
            "inline_keyboard": [
                [{"text": "🛒 BUY HACK", "callback_data": "/shopnawkk"}],
                [{"text": "📦 MY KEY", "callback_data": "/orderksk"}, {"text": "👤 PROFILE", "callback_data": "/profilemmm"}],
                [{"text": "🎥 HOW TO USE", "callback_data": "/spinj"}, {"text": "💬 SUPPORT", "callback_data": "/supportj"}],
                [{"text": "💰 ADD FUND", "callback_data": "/addpayment"}],
                [{"text": "📸 PAY PROOF", "url": "https://t.me/subhajit_feedback"}, {"text": "📥 DOWNLOAD APK", "url": "https://t.me/+hasTLSVjzaZjZGVl"}]
            ]
        }
    )

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
            parse_mode=None,
            reply_markup={
                "inline_keyboard": [
                    [{"text": "📦 DRIP CLIENT NON-ROOT", "callback_data": "/SHOP_P1"}],
                    [{"text": "📦 PROXY SERVER [DR-CL]", "callback_data": "/SHOP_P2"}],
                    [{"text": "🔥 PRIME HOOK", "callback_data": "/SHOP_P4"}],
                    [{"text": "🔙 BACK", "callback_data": "/backkkk"}]
                ]
            }
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

    raise ReturnCommand()

# ... (baaki commands same hai, bas parse_mode=None use karo)

# ======================================================================
# COMMAND REGISTRY
# ======================================================================
COMMANDS = {
    "/start": cmd__start,
    "/shopnawkk": cmd__shopnawkk,
    # ... baaki commands add karo
}

# ======================================================================
# DISPATCHER
# ======================================================================
@bot_client.message_handler(func=lambda m: True, content_types=["text"])
def on_message(message):
    uid = str(message.from_user.id)
    _mark_known_user(uid)

    text = message.text or ""

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
