#!/usr/bin/env python3
"""
shop_bot.py
===========
SINGLE-FILE standalone Python conversion of the original bot-builder
command export (63 commands). Real pyTelegramBotAPI + Firebase underneath,
zero dependency on the old platform.

Setup:
    pip install pyTelegramBotAPI firebase-admin requests

Environment variables:
    BOT_TOKEN           - BotFather token
    FIREBASE_DB_URL     - https://<project>-default-rtdb.firebaseio.com/
    FIREBASE_CRED_PATH  - path to serviceAccountKey.json (optional)
    FIREBASE_CRED_JSON  - serviceAccountKey.json content as a raw JSON string (optional)
    PUBLIC_BASE_URL     - optional, only used by libs.Webhook.getUrlFor()

Run:
    python3 shop_bot.py
"""

# ======================================================================
# PART 1: RUNTIME (Bot / User / bot / libs / HTTP / ReturnCommand)
# ======================================================================

"""
runtime.py
----------
Compatibility layer that re-implements every object the original
bot-builder-platform DSL used (Bot, User, bot, libs, HTTP, ReturnCommand,
InlineKeyboardMarkup/Button) using ONLY real, standalone libraries:

    - pyTelegramBotAPI (telebot)  -> actual Telegram calls
    - firebase-admin              -> persistent storage (Realtime Database)
    - requests                    -> HTTP.get / HTTP.post

This lets every original command's code run completely unchanged logic-wise,
while now being 100% plain Python with zero dependency on the old platform.
"""

import os
import json
import threading
from datetime import datetime

import requests
import telebot
from telebot import types
from telebot.formatting import apply_html_entities  # noqa: F401  (used by command code)

import firebase_admin
from firebase_admin import credentials, db

try:
    from zoneinfo import ZoneInfo
except ImportError:  # py<3.9 fallback
    from backports.zoneinfo import ZoneInfo


# --------------------------------------------------------------------------- #
# CONFIG (env vars first, hardcoded fallback kept for quick local testing)
# --------------------------------------------------------------------------- #
BOT_TOKEN = "8644946592:AAGqcXNTd0TRpYSkK3XkwGjXVQMwxTZKoao"
FIREBASE_DB_URL = os.environ.get("FIREBASE_DB_URL", "https://your-project-default-rtdb.firebaseio.com/")
FIREBASE_CRED_JSON = os.environ.get("FIREBASE_CRED_JSON")  # raw JSON string (optional)
FIREBASE_CRED_PATH = os.environ.get("FIREBASE_CRED_PATH", "/home/claude/bot/serviceAccountKey.json")

bot_client = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# --------------------------------------------------------------------------- #
# FIREBASE INIT
# --------------------------------------------------------------------------- #
if not firebase_admin._apps:
    if FIREBASE_CRED_JSON:
        cred = credentials.Certificate(json.loads(FIREBASE_CRED_JSON))
    elif os.path.exists(FIREBASE_CRED_PATH):
        cred = credentials.Certificate(FIREBASE_CRED_PATH)
    else:
        cred = None

    if cred:
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
    else:
        # allow module import / syntax-check without real Firebase creds present
        firebase_admin.initialize_app(options={"databaseURL": FIREBASE_DB_URL}, name="uninit")


def _safe_ref(path):
    try:
        return db.reference(path)
    except Exception:
        return None


class ReturnCommand(Exception):
    """Raised to stop executing the current command handler early."""
    pass


# --------------------------------------------------------------------------- #
# Bot.getData / Bot.saveData  -> global bot-wide key/value store
# --------------------------------------------------------------------------- #
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
        """Immediately execute another command in-line (no waiting for a message)."""
        run_command_now(cmd_name, options)

    def handleNextCommand(self, cmd_name, options=None):
        """Mark that the NEXT plain-text message from the current user should
        be routed to cmd_name, with the given options attached."""
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
        """Fire-and-forget broadcast: runs `code` once per known user id in a
        background thread, then invokes /broadResult with the tally."""
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
    """Mimics the original webhook payload shape used by /broadResult:
    options.json.total / .total_success / .total_errors"""
    def __init__(self, total, success, errors):
        self.json = _BroadcastResultData(total, success, errors)


Bot = _BotData()


# --------------------------------------------------------------------------- #
# User.getData / User.saveData -> per-user key/value store
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# libs.DateAndTime / libs.Resources / libs.Webhook
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# HTTP.get / HTTP.post  -> thin requests wrapper (already returns .json())
# --------------------------------------------------------------------------- #
class _HTTP:
    @staticmethod
    def get(url, **kw):
        return requests.get(url, timeout=kw.pop("timeout", 20), **kw)

    @staticmethod
    def post(url, **kw):
        return requests.post(url, timeout=kw.pop("timeout", 20), **kw)


HTTP = _HTTP()


# --------------------------------------------------------------------------- #
# InlineKeyboardMarkup / InlineKeyboardButton -> real telebot types
# --------------------------------------------------------------------------- #
InlineKeyboardMarkup = types.InlineKeyboardMarkup
InlineKeyboardButton = types.InlineKeyboardButton


def _dict_markup_to_telebot(markup_dict):
    """Convert the platform's raw dict reply_markup (which may include the
    non-standard 'style' / 'icon_custom_emoji_id' keys) into a real
    telebot InlineKeyboardMarkup. Unsupported keys are simply dropped since
    plain Telegram Bot API has no button-color / icon concept."""
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
    return reply_markup  # already a real telebot InlineKeyboardMarkup object


# --------------------------------------------------------------------------- #
# bot.* wrapper  (bound to whichever chat the current update belongs to)
# --------------------------------------------------------------------------- #
def _bot_send(chat_id, text, parse_mode=None, reply_markup=None, disable_web_page_preview=None, **kw):
    try:
        return bot_client.send_message(
            chat_id,
            text,
            parse_mode=_fix_parse_mode(parse_mode),
            reply_markup=_normalize_markup(reply_markup),
            disable_web_page_preview=disable_web_page_preview,
        )
    except Exception as e:
        # Never let a broadcast/notification crash the whole handler
        print(f"[bot.sendMessage error] chat={chat_id}: {e}")
        return None


def _fix_parse_mode(parse_mode):
    if parse_mode is None:
        return None
    return parse_mode.upper() if parse_mode.lower() == "html" else parse_mode


class BotProxy:
    """Per-update proxy exposing replyText / sendMessage / editMessageText /
    deleteMessage / sendPhoto / sendVideo / ... matching the original DSL."""

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

    def _send_media(self, method_name, chat_id=None, caption=None, parse_mode=None,
                     reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        fn = getattr(bot_client, method_name)
        return fn(chat_id, caption=caption, parse_mode=_fix_parse_mode(parse_mode),
                   reply_markup=_normalize_markup(reply_markup), **kw)

    def sendPhoto(self, chat_id=None, photo=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        return bot_client.send_photo(chat_id, photo, caption=caption,
                                      parse_mode=_fix_parse_mode(parse_mode),
                                      reply_markup=_normalize_markup(reply_markup))

    def sendVideo(self, chat_id=None, video=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        return bot_client.send_video(chat_id, video, caption=caption,
                                      parse_mode=_fix_parse_mode(parse_mode),
                                      reply_markup=_normalize_markup(reply_markup))

    def sendAudio(self, chat_id=None, audio=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        return bot_client.send_audio(chat_id, audio, caption=caption,
                                      parse_mode=_fix_parse_mode(parse_mode),
                                      reply_markup=_normalize_markup(reply_markup))

    def sendDocument(self, chat_id=None, document=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        return bot_client.send_document(chat_id, document, caption=caption,
                                         parse_mode=_fix_parse_mode(parse_mode),
                                         reply_markup=_normalize_markup(reply_markup))

    def sendSticker(self, chat_id=None, sticker=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        return bot_client.send_sticker(chat_id, sticker, reply_markup=_normalize_markup(reply_markup))

    def sendAnimation(self, chat_id=None, animation=None, caption=None, parse_mode=None, reply_markup=None, **kw):
        chat_id = chat_id or self.default_chat_id
        return bot_client.send_animation(chat_id, animation, caption=caption,
                                          parse_mode=_fix_parse_mode(parse_mode),
                                          reply_markup=_normalize_markup(reply_markup))

    def answerCallbackQuery(self, callback_query_id, text=None, show_alert=False, **kw):
        return bot_client.answer_callback_query(callback_query_id, text=text, show_alert=show_alert)


def make_bot_proxy(default_chat_id):
    return BotProxy(default_chat_id)


# ======================================================================
# PART 2: ALL 63 COMMANDS (original logic, unchanged)
# ======================================================================

def cmd__ChangeAnyUserBal(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    #

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break
    if is_Admin != True:
        bot.replyText(
            u,
            "<b><i>🚫 You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        raise ReturnCommand()

    

    bot.replyText( chat_id = message.chat.id,
        text = f"""<b>💡 Send User Telegram Id & Amount

    ⚠️ Use Format : <code>{message.chat.id} 10</code>

    Add - Before Amount To Deduct Balance Like -10</b>""",
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
            "<b><i>🚫 You Are Not This Bot Admin</i></b>",
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

    bot.replyText(u,f"""<b>💴 Account Of {user} Was Increased By {amt}

    💰 Final Balance = {libs.Resources.anotherRes('Balance', user=usr).value()}</b>""")
 


    ADBT=Bot.getData("ADBT") or "0"
    if ADBT!="0":
        bot.replyText(usr,f"""<b>{ADBT}</b>""")
    




    r=Bot.getData("PerRefer") or 0
    act=f"Added {amt} Rs To {usr} Account"
    AdmAC.append(f"<b>📆 Time:</b> {EasyTime}\n👥 <b>By {message.from_user.first_name}</b> [ID: <code>{u}</code>]\n🔍<b> Action: </b> {act}")

    Bot.saveData("AdmAC",AdmAC)




    bot.replyText(usr,f"""<b>💰 Admin Gave You A Increase In Balance By {amt}</b>""")



def cmd__SHOPADDKEY(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    # -------- Admin Check --------

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False

    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break


    if is_Admin != True:
        bot.replyText(
            u,
            "<b><i>🚫 You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        raise ReturnCommand()


    # -------- PARAM CHECK --------

    if not params:
        bot.sendMessage(
            "Usage:\n\n"
            "/SHOPADDKEY 1 → Drip 1d\n"
            "/SHOPADDKEY 2 → Stricks 10d"
        )
        raise ReturnCommand()


    # -------- OPTIONS --------

    if params == "1":

        bot.sendMessage(
            "🛒 <b>DRIP CLIENT APK MOD</b>\n\n"
            "Send 1d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "drip_1d_keys",
                "title": "🛒 DRIP CLIENT APK MOD\n1d Key"
            }
        )

        raise ReturnCommand()




    elif params == "2":

        bot.sendMessage(
            "🛒 <b>DRIP CLIENT APK MOD</b>\n\n"
            "Send 3d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "drip_3d_keys",
                "title": "🛒 DRIP CLIENT APK MOD\n3d Key"
            }
        )

        raise ReturnCommand()

    elif params == "3":

        bot.sendMessage(
            "🛒 <b>DRIP CLIENT APK MOD</b>\n\n"
            "Send 7d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "drip_7d_keys",
                "title": "🛒 DRIP CLIENT APK MOD\n7d Key"
            }
        )

        raise ReturnCommand()
 
 
     
    elif params == "4":

        bot.sendMessage(
            "🛒 <b>DRIP CLIENT APK MOD</b>\n\n"
            "Send 15d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "drip_15d_keys",
                "title": "🛒 DRIP CLIENT APK MOD\n15d Key"
            }
        )

        raise ReturnCommand()
 
 
     
    elif params == "5":

        bot.sendMessage(
            "🛒 <b>DRIP CLIENT APK MOD</b>\n\n"
            "Send 30d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "drip_30d_keys",
                "title": "🛒 DRIP CLIENT APK MOD\n30d Key"
            }
        )

        raise ReturnCommand()
 
     
    elif params == "6":

        bot.sendMessage(
            "🛒 <b>PRIME-HOOK-MOD</b>\n\n"
            "Send 1d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "HG_1d_keys",
                "title": "🛒PRIME-HOOK-MOD\n1d Key"
            }
        )

        raise ReturnCommand()
    
    elif params == "7":

        bot.sendMessage(
            "🛒 <b>PRIME-HOOK-MOD</b>\n\n"
            "Send 7d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "HG_7d_keys",
                "title": "🛒HG-CHEATS ANDROID\n7d Key"
            }
        )

        raise ReturnCommand()
 
     
    elif params == "8":

        bot.sendMessage(
            "🛒 <b>PRIME-HOOK-MOD</b>\n\n"
            "Send 10d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "HG_10d_keys",
                "title": "🛒HG-CHEATS ANDROID\n10d Key"
            }
        )

        raise ReturnCommand()
 
     
    elif params == "9":

        bot.sendMessage(
            "🛒 <b>PRIME-HOOK-MOD</b>\n\n"
            "Send 30d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "HG_30d_keys",
                "title": "🛒HG-CHEATS ANDROID\n30d Key"
            }
        )

        raise ReturnCommand()
 
 
     
    elif params == "101":

        bot.sendMessage(
            "🛒 <b>PROXY SERVER [DR-CL]</b>\n\n"
            "Send 1d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "PATO_1d_keys",
                "title": "🛒PROXY SERVER [DR-CL]\n1d Key"
            }
        )

        raise ReturnCommand()
 
 
 
    elif params == "10":

        bot.sendMessage(
            "🛒 <b>PROXY SERVER [DR-CL]</b>\n\n"
            "Send 3d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "PATO_3d_keys",
                "title": "🛒PROXY SERVER [DR-CL]\n3d Key"
            }
        )

        raise ReturnCommand()
 
 
     
    elif params == "11":

        bot.sendMessage(
            "🛒 <b>PROXY SERVER [DR-CL]</b>\n\n"
            "Send 7d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "PATO_7d_keys",
                "title": "🛒PROXY SERVER [DR-CL]\n7d Key"
            }
        )

        raise ReturnCommand()
 
 
     
    elif params == "12":

        bot.sendMessage(
            "🛒 <b>PROXY SERVER [DR-CL]</b>\n\n"
            "Send 15d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "PATO_15d_keys",
                "title": "🛒PROXY SERVER [DR-CL]\n10d Key"
            }
        )

        raise ReturnCommand()
 
     
    elif params == "13":

        bot.sendMessage(
            "🛒 <b>PRIME-HOOK-MOD APK</b>\n\n"
            "Send 5d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "PRIME_5d_keys",
                "title": "🛒PRIME-HOOK-MOD APK\n5d Key"
            }
        )

        raise ReturnCommand()
 
 
     
    elif params == "14":

        bot.sendMessage(
            "🛒 <b>PRIME-HOOK-MOD APK</b>\n\n"
            "Send 10d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "PRIME_10d_keys",
                "title": "🛒PRIME-HOOK-MOD APK\n10d Key"
            }
        )

        raise ReturnCommand()
 
 
     
    elif params == "15":

        bot.sendMessage(
            "🛒 <b>BR MOD ROOT</b>\n\n"
            "Send 10d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "ROOT_10d_keys",
                "title": "🛒 BR MOD ROOT\n10d Key"
            }
        )

        raise ReturnCommand()
 
 
    elif params == "306":

        bot.sendMessage(
            "🛒 <b> 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀</b>\n\n"
            "Send 1d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "HG_1d_keys",
                "title": "🛒 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n1d Key"
            }
        )

        raise ReturnCommand()


    elif params == "307":

        bot.sendMessage(
            "🛒 <b> 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀</b>\n\n"
            "Send 3d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "HG_3d_keys",
                "title": "🛒 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n3d Key"
            }
        )

        raise ReturnCommand()


    elif params == "308":

        bot.sendMessage(
            "🛒 <b> 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀</b>\n\n"
            "Send 7d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "HG_7d_keys",
                "title": "🛒 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n7d Key"
            }
        )

        raise ReturnCommand()


    elif params == "309":

        bot.sendMessage(
            "🛒 <b> 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀</b>\n\n"
            "Send 14d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "HG_14d_keys",
                "title": "🛒 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n14d Key"
            }
        )

        raise ReturnCommand()


    elif params == "310":

        bot.sendMessage(
            "🛒 <b> 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀</b>\n\n"
            "Send 21d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "HG_21d_keys",
                "title": "🛒 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n21d Key"
            }
        )

        raise ReturnCommand()
 
 
     
    elif params == "16":

        bot.sendMessage(
            "🛒 <b>BR MOD ROOT</b>\n\n"
            "Send 20d key\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

        Bot.handleNextCommand(
            "/SHOPADDKEY1",
            options={
                "key": "ROOT_20d_keys",
                "title": "🛒 BR MOD ROOT\n20d Key"
            }
        )

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
    # Cancel
    if message.text == "/cancel":
        bot.sendMessage("<b>❌ Cancelled</b>", parse_mode="html")
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

        # Get existing data
        existing_data = Bot.getData(stock_key)

        # 🔥 FIX PART
        if not existing_data:
            keys_list = []
        elif isinstance(existing_data, str):
            # Convert old single string into list
            keys_list = [existing_data]
        else:
            keys_list = existing_data

        # Add new key
        keys_list.append(key_value)

        Bot.saveData(stock_key, keys_list)

        bot.sendMessage(
            f"✅ <b>Key Added Successfully</b>\n\n"
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

    # DRIP CLIENT APK MOD
    "1":  ("drip_1d_price",  "DRIP CLIENT APK MOD\n1 Days"),
    "2":  ("drip_3d_price",  "DRIP CLIENT APK MOD\n3 Days"),
    "3":  ("drip_7d_price",  "DRIP CLIENT APK MOD\n7 Days"),
    "4":  ("drip_15d_price",  "DRIP CLIENT APK MOD\n15 Days"),
    "5":  ("drip_30d_price",  "DRIP CLIENT APK MOD\n30 Days"),
    "6":  ("drip_1d_reseller_price",  "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n1 Days"),
    "7":  ("drip_3d_reseller_price",  "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n3 Days"),
    "8":  ("drip_7d_reseller_price",  "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n7 Days"),
    "9":  ("drip_15d_reseller_price",  "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n15 Days"),
    "10":  ("drip_30d_reseller_price",  "👑 RESELLER PANEL\n🛒 DRIP CLIENT APK MOD\n30 Days"),
    # HG-CHEATS ANDROID

    "11":  ("HG_1d_price",  "🛒 HG-CHEATS ANDROID\n1 Days"),

    "12":  ("HG_7d_price",  "🛒 HG-CHEATS ANDROID\n7 Days"),

    "13":  ("HG_10d_price",  "🛒 HG-CHEATS ANDROID\n10 Days"),

    "14":  ("HG_30d_price",  "🛒 HG-CHEATS ANDROID\n30 Days"),

    "14":  ("HG_30d_price",  "🛒 HG-CHEATS ANDROID\n30 Days"),

    "15":  ("HG_1d_reseller_price",  " 👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n1 Days"),

    "16":  ("HG_7d_reseller_price",  " 👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n7 Days"),

    "17":  ("HG_10d_reseller_price",  " 👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n10 Days"),

    "18":  ("HG_30d_reseller_price",  " 👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n30 Days"),

    "18":  ("HG_30d_reseller_price",  " 👑 RESELLER PANEL\n🛒 HG-CHEATS ANDROID\n30 Days"),

    #  PATO BLUE APK MOD
    "191":  ("PATO_1d_price",  "🛒PROXY SERVER [DR-CL] \n1 Days"),
    "19":  ("PATO_3d_price",  "🛒  PROXY SERVER [DR-CL]\n3 Days"),
    "20":  ("PATO_7d_price",  "🛒  PROXY SERVER [DR-CL] \n7 Days"),
    "21":  ("PATO_15d_price",  "🛒  PROXY SERVER [DR-CL] \n10 Days"),

    "221":  ("PATO_1d_reseller_price",  " 👑 RESELLER PANEL\n🛒  PROXY SERVER [DR-CL]\n1 Days"),

    "22":  ("PATO_3d_reseller_price",  " 👑 RESELLER PANEL\n🛒  PROXY SERVER [DR-CL]\n3 Days"),

    "23":  ("PATO_7d_reseller_price",  " 👑 RESELLER PANEL\n🛒  PROXY SERVER [DR-CL] \n7 Days"),

    "24":  ("PATO_15d_reseller_price",  " 👑 RESELLER PANEL\n🛒  PROXY SERVER [DR-CL]\n10 Days"),

    # PRIME-HOOK-MOD APK

    "25":  ("PRIME_5d_price",  "🛒 PRIME-HOOK-MOD APK \n5 Days"),

    "26":  ("PRIME_10d_price",  "🛒 PRIME-HOOK-MOD APK \n10 Days"),

    "27":  ("PRIME_5d_reseller_price",  " 👑 RESELLER PANEL\n🛒 PRIME-HOOK-MOD APK\n5 Days"),

    "28":  ("PRIME_10d_reseller_price",  " 👑 RESELLER PANEL\n🛒 PRIME-HOOK-MOD APK\n10 Days"),
    #BR MOD ROOT


    "29":  ("ROOT_10d_price",  "🛒 BR MOD ROOT\n10 Days"),

    "30":  ("ROOT_20d_price",  "🛒 BR MOD ROOT\n20 Days"),

    "31":  ("ROOT_10d_reseller_price",  " 👑 RESELLER PANEL\n🛒 BR MOD ROOT\n10 Days"),

    "32":  ("ROOT_20d_reseller_price",  " 👑 RESELLER PANEL\n🛒 BR MOD ROOT\n20 Days"),
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

    # -------- EXECUTION --------

    if params in products:

        data_name, title = products[params]

        Bot.runCommand(
            "/SHOPADD_PM1",
            options={
                "key": data_name,
                "title": title
            }
        )
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
    # =========================================
    # BUYBAHHA RESELLER COMMAND
    # =========================================

    #price_name = options.get("price")
    key_name = options.get("key")
    title = options.get("title")

    if not key_name or not key_name:
        bot.sendMessage("❌ Product configuration error.")
        raise ReturnCommand()

    # -------------------------
    # GET PRICE
    # -------------------------

    bot.sendMessage(
            f"🛒 <b>{title}</b>\n\n"
            "Send key price (numbers only).\n\n"
            "Type /cancel to stop.",
            parse_mode="html"
        )

    Bot.handleNextCommand(
            "/SHOPADD_PM2",
            options={
                "key": key_name,
                "title": title
            }
        )



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
        bot.sendMessage("<b>❌ Cancelled</b>", parse_mode="html")
        raise ReturnCommand()

    try:
        rate = float(message.text)

        price_key = options["key"]
        title = options["title"]

        Bot.saveData(price_key, rate)

        bot.sendMessage(
            f"✅ <b>Successfully Set</b>\n\n"
            f"{title} Price = ₹{rate}",
            parse_mode="html"
        )
        act = f"{title} Price = ₹{rate}"
        AdmAC.append(
            f"<b>📆 Time:</b> {EasyTime}\n"
            f"👥 <b>By {message.from_user.first_name}</b> "
            f"[ID: <code>{u}</code>]\n"
            f"🔍<b> Action: </b> {act}"
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
    # 🔘 BUTTONS (same as before)
    markup = InlineKeyboardMarkup()

    # 1D
    markup.add(InlineKeyboardButton('👑 RESELLER 1D', callback_data='/SHOPADD_PM 6'))
    markup.add(
        InlineKeyboardButton('1D Price', callback_data='/SHOPADD_PM 1'),
        InlineKeyboardButton('Add 1D Key', callback_data='/SHOPADDKEY 1')
    )

    # 3D
    markup.add(InlineKeyboardButton('👑 RESELLER 3D', callback_data='/SHOPADD_PM 7'))
    markup.add(
        InlineKeyboardButton('3D Price', callback_data='/SHOPADD_PM 2'),
        InlineKeyboardButton('Add 3D Key', callback_data='/SHOPADDKEY 2')
    )

    # 7D
    markup.add(InlineKeyboardButton('👑 RESELLER 7D', callback_data='/SHOPADD_PM 8'))
    markup.add(
        InlineKeyboardButton('7D Price', callback_data='/SHOPADD_PM 3'),
        InlineKeyboardButton('Add 7D Key', callback_data='/SHOPADDKEY 3')
    )

    # 15D
    markup.add(InlineKeyboardButton('👑 RESELLER 15D', callback_data='/SHOPADD_PM 9'))
    markup.add(
        InlineKeyboardButton('15D Price', callback_data='/SHOPADD_PM 4'),
        InlineKeyboardButton('Add 15D Key', callback_data='/SHOPADDKEY 4')
    )

    # 30D
    markup.add(InlineKeyboardButton('👑 RESELLER 30D', callback_data='/SHOPADD_PM 10'))
    markup.add(
        InlineKeyboardButton('30D Price', callback_data='/SHOPADD_PM 5'),
        InlineKeyboardButton('Add 30D Key', callback_data='/SHOPADDKEY 5')
    )

    markup.add(InlineKeyboardButton('🔙 Back', callback_data='/setshop_psue'))

    # 📦 GET OLD DATA
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


    # 📊 DATA
    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p15, r15, s15 = get_old(15)
    p30, r30, s30 = get_old(30)

    # 📝 TEXT
    TXT = (
        "🎮 🛒  𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗✅\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👑 1D Reseller: ₹{r1}\n"
        f"💰 1D Price: ₹{p1}\n📦 {s1}\n\n"

        f"👑 3D Reseller: ₹{r3}\n"
        f"💰 3D Price: ₹{p3}\n📦 {s3}\n\n"

        f"👑 7D Reseller: ₹{r7}\n"
        f"💰 7D Price: ₹{p7}\n📦 {s7}\n\n"

        f"👑 15D Reseller: ₹{r15}\n"
        f"💰 15D Price: ₹{p15}\n📦 {s15}\n\n"

        f"👑 30D Reseller: ₹{r30}\n"
        f"💰 30D Price: ₹{p30}\n📦 {s30}\n\n"

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
    # 🔘 BUTTONS

    markup = InlineKeyboardMarkup()

    # 1D
    markup.add(
        InlineKeyboardButton(
            '👑 RESELLER 1D',
            callback_data='/SHOPADD_PM 316'
        )
    )

    markup.add(
        InlineKeyboardButton(
            '1D Price',
            callback_data='/SHOPADD_PM 311'
        ),
        InlineKeyboardButton(
            'Add 1D Key',
            callback_data='/SHOPADDKEY 306'
        )
    )

    # 3D
    markup.add(
        InlineKeyboardButton(
            '👑 RESELLER 3D',
            callback_data='/SHOPADD_PM 317'
        )
    )

    markup.add(
        InlineKeyboardButton(
            '3D Price',
            callback_data='/SHOPADD_PM 312'
        ),
        InlineKeyboardButton(
            'Add 3D Key',
            callback_data='/SHOPADDKEY 307'
        )
    )

    # 7D
    markup.add(
        InlineKeyboardButton(
            '👑 RESELLER 7D',
            callback_data='/SHOPADD_PM 318'
        )
    )

    markup.add(
        InlineKeyboardButton(
            '7D Price',
            callback_data='/SHOPADD_PM 313'
        ),
        InlineKeyboardButton(
            'Add 7D Key',
            callback_data='/SHOPADDKEY 308'
        )
    )

    # 10D
    markup.add(
        InlineKeyboardButton(
            '👑 RESELLER 14D',
            callback_data='/SHOPADD_PM 319'
        )
    )

    markup.add(
        InlineKeyboardButton(
            '14D Price',
            callback_data='/SHOPADD_PM 314'
        ),
        InlineKeyboardButton(
            'Add 14D Key',
            callback_data='/SHOPADDKEY 309'
        )
    )
    # 10D
    markup.add(
        InlineKeyboardButton(
            '👑 RESELLER 21D',
            callback_data='/SHOPADD_PM 320'
        )
    )

    markup.add(
        InlineKeyboardButton(
            '21D Price',
            callback_data='/SHOPADD_PM 315'
        ),
        InlineKeyboardButton(
            'Add 21D Key',
            callback_data='/SHOPADDKEY 310'
        )
    )

    # BACK
    markup.add(
        InlineKeyboardButton(
            '🔙 Back',
            callback_data='/setshop_psue'
        )
    )

    # 📦 GET DATA

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

    # 📊 DATA

    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p10, r10, s10 = get_old(14)
    p21, r21, s21 = get_old(21)

    # 📝 TEXT

    TXT = (
        "📦 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👑 1D Reseller: ₹{r1}\n"
        f"💰 1D Price: ₹{p1}\n"
        f"📦 {s1}\n\n"

        f"👑 3D Reseller: ₹{r3}\n"
        f"💰 3D Price: ₹{p3}\n"
        f"📦 {s3}\n\n"

        f"👑 7D Reseller: ₹{r7}\n"
        f"💰 7D Price: ₹{p7}\n"
        f"📦 {s7}\n\n"

        f"👑 14D Reseller: ₹{r10}\n"
        f"💰 14D Price: ₹{p10}\n"
        f"📦 {s10}\n\n"

        f"👑 21D Reseller: ₹{r21}\n"
        f"💰 21D Price: ₹{p21}\n"
        f"📦 {s21}\n\n"
    
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
    # 🔘 BUTTONS (same as before)
    markup = InlineKeyboardMarkup()

    # 3D
    markup.add(InlineKeyboardButton('👑 RESELLER 1D', callback_data='/SHOPADD_PM 221'))
    markup.add(
        InlineKeyboardButton('1D Price', callback_data='/SHOPADD_PM 191'),
        InlineKeyboardButton('Add 1D Key', callback_data='/SHOPADDKEY 101')
    )

    # 3D
    markup.add(InlineKeyboardButton('👑 RESELLER 3D', callback_data='/SHOPADD_PM 22'))
    markup.add(
        InlineKeyboardButton('3D Price', callback_data='/SHOPADD_PM 19'),
        InlineKeyboardButton('Add 3D Key', callback_data='/SHOPADDKEY 10')
    )

    # 7D
    markup.add(InlineKeyboardButton('👑 RESELLER 7D', callback_data='/SHOPADD_PM 23'))
    markup.add(
        InlineKeyboardButton('7D Price', callback_data='/SHOPADD_PM 20'),
        InlineKeyboardButton('Add 7D Key', callback_data='/SHOPADDKEY 11')
    )

    # 15D
    markup.add(InlineKeyboardButton('👑 RESELLER 15D', callback_data='/SHOPADD_PM 24'))
    markup.add(
        InlineKeyboardButton('15D Price', callback_data='/SHOPADD_PM 21'),
        InlineKeyboardButton('Add 15D Key', callback_data='/SHOPADDKEY 12')
    )

    markup.add(InlineKeyboardButton('🔙 Back', callback_data='/setshop_psue'))

    # 📦 GET OLD DATA
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


    # 📊 DATA

    p1, r1, s1 = get_old(1)
    p3, r3, s3 = get_old(3)
    p7, r7, s7 = get_old(7)
    p15, r15, s15 = get_old(15)


    # 📝 TEXT
    TXT = (
        "🎮 PROXY SERVER [DR-CL]\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👑 1D Reseller: ₹{r1}\n"
        f"💰 1D Price: ₹{p1}\n📦 {s1}\n\n"
    
        f"👑 3D Reseller: ₹{r3}\n"
        f"💰 3D Price: ₹{p3}\n📦 {s3}\n\n"

        f"👑 7D Reseller: ₹{r7}\n"
        f"💰 7D Price: ₹{p7}\n📦 {s7}\n\n"

        f"👑 15D Reseller: ₹{r15}\n"
        f"💰 15D Price: ₹{p15}\n📦 {s15}\n\n"

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
    # 🔘 BUTTONS (same as before)
    markup = InlineKeyboardMarkup()

    # 5D
    markup.add(InlineKeyboardButton('👑 RESELLER 5D', callback_data='/SHOPADD_PM 27'))
    markup.add(
        InlineKeyboardButton('5D Price', callback_data='/SHOPADD_PM 25'),
        InlineKeyboardButton('Add 5D Key', callback_data='/SHOPADDKEY 13')
    )

    # 10D
    markup.add(InlineKeyboardButton('👑 RESELLER 10D', callback_data='/SHOPADD_PM 28'))
    markup.add(
        InlineKeyboardButton('10D Price', callback_data='/SHOPADD_PM 26'),
        InlineKeyboardButton('Add 10D Key', callback_data='/SHOPADDKEY 14')
    )


    markup.add(InlineKeyboardButton('🔙 Back', callback_data='/setshop_psue'))

    # 📦 GET OLD DATA
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


    # 📊 DATA
    p5, r5, s5 = get_old(5)
    p10, r10, s10 = get_old(10)

    # 📝 TEXT
    TXT = (
        "🎮 🛒 PRIME-HOOK-MOD APK\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👑 5D Reseller: ₹{r5}\n"
        f"💰 5D Price: ₹{p5}\n📦 {s5}\n\n"

        f"👑 10D Reseller: ₹{r10}\n"
        f"💰 10D Price: ₹{p10}\n📦 {s10}\n\n"

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
    # 🔘 BUTTONS (same as before)
    markup = InlineKeyboardMarkup()

    # 10D
    markup.add(InlineKeyboardButton('👑 RESELLER 10D', callback_data='/SHOPADD_PM 31'))
    markup.add(
        InlineKeyboardButton('10D Price', callback_data='/SHOPADD_PM 29'),
        InlineKeyboardButton('Add 10D Key', callback_data='/SHOPADDKEY 15')
    )

    # 20D
    markup.add(InlineKeyboardButton('👑 RESELLER 20D', callback_data='/SHOPADD_PM 32'))
    markup.add(
        InlineKeyboardButton('20D Price', callback_data='/SHOPADD_PM 30'),
        InlineKeyboardButton('Add 20D Key', callback_data='/SHOPADDKEY 16')
    )


    markup.add(InlineKeyboardButton('🔙 Back', callback_data='/setshop_psue'))

    # 📦 GET OLD DATA
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


    # 📊 DATA
    p10, r10, s10 = get_old(10)
    p20, r20, s20 = get_old(20)

    # 📝 TEXT
    TXT = (
        "🎮 🛒 BR MOD ROOT\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👑 10D Reseller: ₹{r10}\n"
        f"💰 10D Price: ₹{p10}\n📦 {s10}\n\n"

        f"👑 20D Reseller: ₹{r20}\n"
        f"💰 20D Price: ₹{p20}\n📦 {s20}\n\n"

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
    # -------------------------
    # Reseller Check
    # -------------------------

    resellers = Bot.getData("resellers_list") or []
    is_reseller = u in resellers

    # -------------------------
    # NORMAL PRICES
    # -------------------------

    p1 = Bot.getData("drip_1d_price") or 108
    p3 = Bot.getData("drip_3d_price") or 260
    p7 = Bot.getData("drip_7d_price") or 360
    p15 = Bot.getData("drip_15d_price") or 560
    p30 = Bot.getData("drip_30d_price") or 810

    # -------------------------
    # RESELLER PRICES
    # -------------------------

    rp1 = Bot.getData("drip_1d_reseller_price") or 95
    rp3 = Bot.getData("drip_3d_reseller_price") or 220
    rp7 = Bot.getData("drip_7d_reseller_price") or 320
    rp15 = Bot.getData("drip_15d_reseller_price") or 480
    rp30 = Bot.getData("drip_30d_reseller_price") or 750

    if is_reseller:
        p1, p3, p7, p15, p30 = rp1, rp3, rp7, rp15, rp30

    buy_command = "/buyjai_reseller" if is_reseller else "/buyjai"

    # -------------------------
    # MESSAGE
    # -------------------------

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<tg-emoji emoji-id='6323104647636589287'>📦</tg-emoji> "
        "𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗"
        "<tg-emoji emoji-id='6179339404906079822'>✅</tg-emoji> "
        "( 𝘉𝘌𝘚𝘛 𝘚𝘌𝘓𝘓𝘌𝘙"
        "<tg-emoji emoji-id='5841693351249710667'>💫</tg-emoji> )\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "<i><tg-emoji emoji-id='5258134813302332906'>📦</tg-emoji> Extra 2% discount applied</i>\n"

        "Choose a plan <tg-emoji emoji-id='5258336354642697821'>👇</tg-emoji>"
    )

    # -------------------------
    # KEYBOARD
    # -------------------------

    keyboard = [
        [{
            "text": f"1 DAY - ₹{p1}",
            "callback_data": f"{buy_command} 1",
            "style": "success"
        }],
        [{
            "text": f"3 DAYS - ₹{p3}",
            "callback_data": f"{buy_command} 2",
            "style": "success"
        }],
        [{
            "text": f"7 DAYS - ₹{p7}",
            "callback_data": f"{buy_command} 3",
            "style": "success"
        }],
        [{
            "text": f"15 DAYS - ₹{p15}",
            "callback_data": f"{buy_command} 4",
            "style": "success"
        }],
        [{
            "text": f"30 DAYS - ₹{p30}",
            "callback_data": f"{buy_command} 5",
            "style": "success"
        }],
        [{
            "text": "BACK",
            "callback_data": "/shopnawkk",
            "style": "danger",
            "icon_custom_emoji_id": "6039539366177541657"
        }]
    ]

    # -------------------------
    # EDIT MESSAGE
    # -------------------------

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
    # -------------------------
    # Reseller Check
    # -------------------------

    resellers = Bot.getData("resellers_list") or []
    is_reseller = u in resellers

    # -------------------------
    # NORMAL PRICES
    # -------------------------

    p1 = Bot.getData("PATO_1d_price") or 108
    p7 = Bot.getData("PATO_3d_price") or 360
    p10 = Bot.getData("PATO_7d_price") or 560
    p30 = Bot.getData("PATO_15d_price") or 810

    # -------------------------
    # RESELLER PRICES
    # -------------------------

    rp1 = Bot.getData("PATO_1d_reseller_price") or 95
    rp7 = Bot.getData("PATO_3d_reseller_price") or 320
    rp10 = Bot.getData("PATO_7d_reseller_price") or 520
    rp30 = Bot.getData("PATO_15d_reseller_price") or 750

    if is_reseller:
        p1, p7, p10, p30 = rp1, rp7, rp10, rp30

    buy_command = "/buyjai_reseller" if is_reseller else "/buyjai"

    text = """
    ━━━━━━━━━━━━━━━━━━━━
    <tg-emoji emoji-id="6212942266957310140">📦</tg-emoji> PROXY SERVER [DR-CL]
    ━━━━━━━━━━━━━━━━━━━━

    Choose a plan <tg-emoji emoji-id="5258336354642697821">👇</tg-emoji>
    """

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=text,
        reply_markup={
            "inline_keyboard": [
                [
                    {
                        "text": f"1 Day - ₹{p1}",
                        "callback_data": f"{buy_command} 6",
                        "style": "success"
                    }
                ],
                [
                    {
                        "text": f"3 Days - ₹{p7}",
                        "callback_data": f"{buy_command} 7",
                        "style": "success"
                    }
                ],
                [
                    {
                        "text": f"7 Days - ₹{p10}",
                        "callback_data": f"{buy_command} 8",
                        "style": "success"
                    }
                ],
                [
                    {
                        "text": f"15 Days - ₹{p30}",
                        "callback_data": f"{buy_command} 9",
                        "style": "success"
                    }
                ],
                [
                    {
                        "text": "BACK",
                        "callback_data": "/shopnawkk",
                        "style": "danger",
                        "icon_custom_emoji_id": "6039539366177541657"
                    }
                ]
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

    # -------------------------
    # Reseller Check
    # -------------------------

    resellers = Bot.getData("resellers_list") or []
    is_reseller = u in resellers

    # -------------------------
    # NORMAL PRICES
    # -------------------------

    p3 = Bot.getData("PATO_3d_price") or 260
    p7 = Bot.getData("PATO_7d_price") or 360
    p15 = Bot.getData("PATO_15d_price") or 560

    # -------------------------
    # RESELLER PRICES
    # -------------------------

    rp3= Bot.getData("PATO_3d_reseller_price") or 220
    rp7 = Bot.getData("PATO_7d_reseller_price") or 320
    rp15 = Bot.getData("PATO_15d_reseller_price") or 320

    if is_reseller:
        p3 = rp3
        p7 = rp7
        p15 = rp15

    buy_command = "/buyjai_reseller" if is_reseller else "/buyjai"
    title_tag = "👑 Reseller Panel\n" if is_reseller else ""

    # -------------------------
    # Build Message
    # -------------------------

    text = """
    ━━━━━━━━━━━━━━━━━━━━
    🏷 <b>PATO BLUE APK MOD</b>
    ━━━━━━━━━━━━━━━━━━━━

    Choose a plan 👇
    """

    # -------------------------
    # Inline Keyboard
    # -------------------------

    keyboard = [
        [{"text": f"3 Days - ₹{p3}", "callback_data": f"{buy_command} 10"}],
        [{"text": f"7 Days - ₹{p7}", "callback_data": f"{buy_command} 11"}],
        [{"text": f"15 Days - ₹{p15}", "callback_data": f"{buy_command} 12"}],
        [{"text": "🔙 Back To Menu", "callback_data": "/shopnawkk"}]
    ]

    # -------------------------
    # Edit Message
    # -------------------------

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
    # -------------------------
    # Reseller Check
    # -------------------------

    resellers = Bot.getData("resellers_list") or []
    is_reseller = u in resellers


    # -------------------------
    # NORMAL PRICES
    # -------------------------

    p1 = Bot.getData("HG_1d_price") or 108
    p3 = Bot.getData("HG_3d_price") or 200
    p7 = Bot.getData("HG_7d_price") or 360
    p14 = Bot.getData("HG_14d_price") or 600
    p21 = Bot.getData("HG_21d_price") or 700


    # -------------------------
    # RESELLER PRICES
    # -------------------------

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
    <tg-emoji emoji-id="6210705396449944693">🔥</tg-emoji> PRIME HOOK
    ━━━━━━━━━━━━━━━━━━━━

    Choose a plan <tg-emoji emoji-id="5258336354642697821">👇</tg-emoji>
    """


    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=text,
        reply_markup={
            "inline_keyboard": [
                [
                    {
                        "text": f"1 Day - ₹{p1}",
                        "callback_data": f"{buy_command} 10",
                        "style": "success"
                    }
                ],
                [
                    {
                        "text": f"3 Days - ₹{p3}",
                        "callback_data": f"{buy_command} 11",
                        "style": "success"
                    }
                ],
                [
                    {
                        "text": f"7 Days - ₹{p7}",
                        "callback_data": f"{buy_command} 12",
                        "style": "success"
                    }
                ],
                [
                    {
                        "text": f"14 Days - ₹{p14}",
                        "callback_data": f"{buy_command} 13",
                        "style": "success"
                    }
                ],
                [
                    {
                        "text": f"21 Days - ₹{p21}",
                        "callback_data": f"{buy_command} 14",
                        "style": "success"
                    }
                ],
                [
                    {
                        "text": "BACK",
                        "callback_data": "/shopnawkk",
                        "style": "danger",
                        "icon_custom_emoji_id": "6039539366177541657"
                    }
                ]
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

    # -------------------------
    # Reseller Check
    # -------------------------

    resellers = Bot.getData("resellers_list") or []
    is_reseller = u in resellers

    # -------------------------
    # NORMAL PRICES
    # -------------------------

    p10 = Bot.getData("ROOT_10d_price") or 560
    p20 = Bot.getData("ROOT_20d_price") or 810

    # -------------------------
    # RESELLER PRICES
    # -------------------------

    rp10 = Bot.getData("ROOT_10d_reseller_price") or 320
    rp20 = Bot.getData("ROOT_20d_reseller_price") or 750

    if is_reseller:
        p10 = rp10
        p20 = rp20

    buy_command = "/buyjai_reseller" if is_reseller else "/buyjai"
    title_tag = "👑 Reseller Panel\n" if is_reseller else ""

    # -------------------------
    # Build Message
    # -------------------------

    text = """
    ━━━━━━━━━━━━━━━━━━━━
    🏷 <b>BR MOD ROOT</b>
    ━━━━━━━━━━━━━━━━━━━━

    Choose a plan 👇
    """

    # -------------------------
    # Inline Keyboard
    # -------------------------

    keyboard = [
        [{"text": f"10 Days - ₹{p10}", "callback_data": f"{buy_command} 15"}],
        [{"text": f"20 Days - ₹{p20}", "callback_data": f"{buy_command} 16"}],
        [{"text": "🔙 Back To Menu", "callback_data": "/shopnawkk"}]
    ]

    # -------------------------
    # Edit Message
    # -------------------------

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

    first_name = message.from_user.first_name or "User"
    balance = libs.Resources.anotherRes("Balance", user=u).value()

    text = (
        "<blockquote>"
        "<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> "
        "WELCOME TO HACK STORE "
        "<tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji>"
        "</blockquote>\n\n"

        "<i>"
        "<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> "
        "Your ultimate destination for premium mods, cheats & clients!"
        "</i>\n\n"

        "<blockquote>"
        "<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> PREMIUM FEATURES\n\n"

        "<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Instant Key Delivery\n"

        "<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Secure Auto-Payment System\n"

        "<tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji> 100% Anti-Ban Support"
        "</blockquote>\n\n"

        "<blockquote>"
        "<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Your Balance: ₹" + str(balance) +
        "</blockquote>"
    )

    bot.sendMessage(
        chat_id=u,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup={
            "inline_keyboard": [

                [
                    {
                        "text": "BUY HACK",
                        "callback_data": "/shopnawkk",
                        "style": "success",
                        "icon_custom_emoji_id": "6093739864883207194"
                    }
                ],

                [
                    {
                        "text": "MY KEY",
                        "callback_data": "/orderksk",
                        "style": "success",
                        "icon_custom_emoji_id": "5967456680940671207"
                    },
                    {
                        "text": "PROFILE",
                        "callback_data": "/profilemmm",
                        "style": "success",
                        "icon_custom_emoji_id": "5346136537123801643"
                    }
                ],

                [
                    {
                        "text": "HOW TO USE",
                        "callback_data": "/spinj",
                        "style": "success",
                        "icon_custom_emoji_id": "5345783284653636765"
                    },
                    {
                        "text": "SUPPORT",
                        "callback_data": "/supportj",
                        "style": "success",
                        "icon_custom_emoji_id": "5897567714674741148"
                    }
                ],

                [
                    {
                        "text": "ADD FUND",
                        "callback_data": "/addpayment",
                        "style": "success",
                        "icon_custom_emoji_id": "6278302366303260172"
                    }
                ],

                [
                    {
                        "text": "PAY PROOF",
                        "url": "https://t.me/subhajit_feedback",
                        "style": "success",
                        "icon_custom_emoji_id": "5258134813302332906"
                    },
                    {
                        "text": "DOWNLOAD APK",
                        "url": "https://t.me/+hasTLSVjzaZjZGVl",
                        "style": "success",
                        "icon_custom_emoji_id": "6028115612163641653"
                    }
                ]

            ]
        }
    )



def cmd__Start(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    joined = User.getData("joined_date")

    if not joined:
        User.saveData("joined_date", message.date)

    first_name = message.from_user.first_name or "User"
    balance = libs.Resources.anotherRes("Balance", user=u).value()

    text = (
        "<blockquote>"
        "<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> "
        "WELCOME TO HACK STORE "
        "<tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji>"
        "</blockquote>\n\n"

        "<i>"
        "<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> "
        "Your ultimate destination for premium mods, cheats & clients!"
        "</i>\n\n"

        "<blockquote>"
        "<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> PREMIUM FEATURES\n\n"

        "<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Instant Key Delivery\n"

        "<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Secure Auto-Payment System\n"

        "<tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji> 100% Anti-Ban Support"
        "</blockquote>\n\n"

        "<blockquote>"
        "<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Your Balance: ₹" + str(balance) +
        "</blockquote>"
    )

    bot.sendMessage(
        chat_id=u,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup={
            "inline_keyboard": [

                [
                    {
                        "text": "BUY HACK",
                        "callback_data": "/shopnawkk",
                        "style": "success",
                        "icon_custom_emoji_id": "6093739864883207194"
                    }
                ],

                [
                    {
                        "text": "MY KEY",
                        "callback_data": "/orderksk",
                        "style": "success",
                        "icon_custom_emoji_id": "5967456680940671207"
                    },
                    {
                        "text": "PROFILE",
                        "callback_data": "/profilemmm",
                        "style": "success",
                        "icon_custom_emoji_id": "5346136537123801643"
                    }
                ],

                [
                    {
                        "text": "HOW TO USE",
                        "callback_data": "/spinj",
                        "style": "success",
                        "icon_custom_emoji_id": "5345783284653636765"
                    },
                    {
                        "text": "SUPPORT",
                        "callback_data": "/supportj",
                        "style": "success",
                        "icon_custom_emoji_id": "5897567714674741148"
                    }
                ],

                [
                    {
                        "text": "ADD FUND",
                        "callback_data": "/addpayment",
                        "style": "success",
                        "icon_custom_emoji_id": "6278302366303260172"
                    }
                ],

                [
                    {
                        "text": "PAY PROOF",
                        "url": "https://t.me/subhajit_feedback",
                        "style": "success",
                        "icon_custom_emoji_id": "5258134813302332906"
                    },
                    {
                        "text": "DOWNLOAD APK",
                        "url": "https://t.me/+hasTLSVjzaZjZGVl",
                        "style": "success",
                        "icon_custom_emoji_id": "6028115612163641653"
                    }
                ]

            ]
        }
    )



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
        bot.replyText(
            u,
            "<b><i>🚫 You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        raise ReturnCommand()


    bot.replyText(chat_id=message.chat.id,text=f"""<b>Send UserID of Admin You Want To Add</b>""",parse_mode="html")

    User.saveData("EDMsgID",message.message_id) 

    Bot.handleNextCommand("/TUSHAR_AddAdmin1")



def cmd__TUSHAR_AddAdmin1(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]

    ##🚫NoResale #🧠RealDeveloper #⚡OwnerBuild #💎OriginalMind

    AllBotAdminss = Bot.getData("AllBotAdminss") or []
    is_Admin = False
    for userid in AllBotAdminss:
        if str(u) == str(userid):
            is_Admin = True
            break
    if is_Admin != True:
        bot.replyText(
            u,
            "<b><i>🚫 You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        raise ReturnCommand()


    check_user = AllBotAdminss.count(message.text)
    if check_user > 0:
        """user_exist"""
        T="Admin Already Exists"
    else:
        AllBotAdminss.append(message.text)
        Bot.saveData("AllBotAdminss", AllBotAdminss)
        T="Admin Added Successfully"


    Bot.runCommand("/TUSHAR_Admins",options=f"<b>{T}</b>")











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
    AdmAC.append(f"<b>📆 Time:</b> {EasyTime}\n👥 <b>By {message.from_user.first_name}</b> [ID: <code>{u}</code>]\n🔍<b> Action: </b> {act}")

    Bot.saveData("AdmAC",AdmAC)









    Bot.sendMessage(f"<b>{T}</b>")



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
        bot.replyText(
            u,
            "<b><i>🚫 You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
        raise ReturnCommand()

    AdmAC=Bot.getData("AdmAC") or []


    x=int(len(AdmAC)) 
    latest_10 = AdmAC[-10:][::-1]

    # Join and print them
    bot.sendMessage("\n\n".join(latest_10))

    #bot.sendMessage(AdmAC)



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
        bot.replyText(
            u,
            "<b><i>🚫 You Are Not This Bot Admin</i></b>",
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










    if str(params)!="None":
        AllBotAdminss.remove(params)
        act=f"Removed {params} from Bot Admin"
        AdmAC.append(f"<b>📆 Time:</b> {EasyTime}\n👥 <b>By {message.from_user.first_name}</b> [ID: <code>{u}</code>]\n🔍<b> Action: </b> {act}")

        Bot.saveData("AdmAC",AdmAC)



    markup = InlineKeyboardMarkup()

    for admin in AllBotAdminss:
        markup.add(InlineKeyboardButton(text=admin,callback_data="/TUSHAR_Admins "+str(admin) ),InlineKeyboardButton(text="❌",callback_data="/TUSHAR_Admins "+str(admin)))

    markup.add(InlineKeyboardButton(text='➕Add Admin',callback_data='/TUSHAR_AddAdmin'))


    markup.add(InlineKeyboardButton(text='🔙Back',callback_data='/admin AP'))

    Bot.saveData("AllBotAdminss",AllBotAdminss)


    e="y"
    T="<b>Here You Can Manage Your Admins</b>"
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
        target_user = str(int(message.text))  # convert to string
    except:
        bot.sendMessage("❌ Invalid User ID.")
        raise ReturnCommand()

    # Get current resellers list
    resellers = Bot.getData("resellers_list") or []

    # Ensure comparison is string-based
    if target_user in [str(u) for u in resellers]:
        bot.sendMessage("⚠️ User already a reseller.")
        raise ReturnCommand()

    # Append as string
    resellers.append(target_user)
    Bot.saveData("resellers_list", resellers)

    bot.sendMessage(
        f"✅ User <code>{target_user}</code> added as Reseller.",
        parse_mode="html"
    )

    # Optional: notify the new reseller
    try:
        bot.sendMessage(
            chat_id=target_user,
            text="🎉 You are now a Reseller 👑"
        )
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
                "<blockquote>"
                "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> ENTER CUSTOM AMOUNT"
                "</blockquote>\n\n"
                "Amount: ₹0\n\n"
                "Use the keypad below to enter amount."
            ),
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [
                    [
                        {"text": "1", "callback_data": "/num1"},
                        {"text": "2", "callback_data": "/num2"},
                        {"text": "3", "callback_data": "/num3"}
                    ],
                    [
                        {"text": "4", "callback_data": "/num4"},
                        {"text": "5", "callback_data": "/num5"},
                        {"text": "6", "callback_data": "/num6"}
                    ],
                    [
                        {"text": "7", "callback_data": "/num7"},
                        {"text": "8", "callback_data": "/num8"},
                        {"text": "9", "callback_data": "/num9"}
                    ],
                    [
                        {
                            "text": "❌ CLEAR",
                            "callback_data": "/clearamt",
                            "style": "danger"
                        },
                        {"text": "0", "callback_data": "/num0"},
                        {
                            "text": "✅ CONFIRM",
                            "callback_data": "/done",
                            "style": "success"
                        }
                    ],
                    [
                        {
                            "text": "BACK",
                            "callback_data": "/backkkk",
                            "style": "danger",
                            "icon_custom_emoji_id": "6039539366177541657"
                        }
                    ]
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
        caption="<blockquote><tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> PAYMENT QR GENERATED</blockquote>\nScan the QR and complete payment.\n\nAmount: ₹" + str(amount),
        parse_mode="HTML",
        reply_markup={
        "inline_keyboard": [
            [
                {
                    "text": "VERIFY PAYMENT",
                    "callback_data": "/verify_addpay",
                    "style": "success",
                    "icon_custom_emoji_id": "6278302366303260172"
                }
            ],
            [
                {
                    "text": "CANCEL",
                    "callback_data": "/cancel",
                    "style": "danger",
                    "icon_custom_emoji_id": "6278116707751956084"
                }
            ]
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
        bot.replyText(
            u,
            "<b><i>🚫 You Are Not This Bot Admin</i></b>",
            parse_mode="html"
        )
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
        bot.replyText(
            u,
            "<b><i>🚫 You Are Not This Bot Admin</i></b>",
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






    
    
    

    if "BotMode" in str(params):
        P=params.split(" ")
        Bot.saveData("BotMode",str(P[1]))

        act=f"But Mode Turned {P[1]}"
        AdmAC.append(f"<b>📆 Time:</b> {EasyTime}\n👥 <b>By {message.from_user.first_name}</b> [ID: <code>{u}</code>]\n🔍<b> Action: </b> {act}")

        Bot.saveData("AdmAC",AdmAC)



    BOT_MODE = Bot.getData("BotMode") or "ON"

    botSta = "🟢 On"
    botStatChngeBut = "BotMode OFF"

    if BOT_MODE == "OFF":
        botSta = "🔴 Off"
        botStatChngeBut = "BotMode ON"
    


    markup = InlineKeyboardMarkup()

    markup.add(
        InlineKeyboardButton(text='👑 Aᴅᴍɪɴs', callback_data='/TUSHAR_Admins'))
    markup.add(
        InlineKeyboardButton(text='📣 Bʀᴏᴀᴅᴄᴀsᴛ', callback_data='/broadcast'),
        InlineKeyboardButton(text='🤖 Bᴏᴛ: ' + str(botSta), callback_data='/admin ' + botStatChngeBut)
    )

    markup.add(
        InlineKeyboardButton(text='💰 Aᴅᴅ Bᴀʟᴀɴᴄᴇ', callback_data='/ChangeAnyUserBal'),
        InlineKeyboardButton(text='📝 Rᴇᴄᴇɴᴛ Aᴅᴍɪɴ Aᴄᴛɪᴏɴs', callback_data='/TUSHAR_AdminAction')
    )
    markup.add(
        InlineKeyboardButton(text='📊 Shop setup', callback_data='/setshop_psue')
    )
    markup.add(
        InlineKeyboardButton(text='💰 Aᴅᴅ Reseller', callback_data='/addreseller'),
        InlineKeyboardButton(text='⛔ Remove Reseller', callback_data='/removereseller')
    )

    markup.add(
        InlineKeyboardButton(text='📝 Reseller List', callback_data='/resellerlist')
    )


    TXT = f"""<b>
    👋 Welcome {message.from_user.first_name} 🎉

    ━━━━━━━━━━━━━━━
    🤖 Bᴏᴛ Sᴛᴀᴛᴜs : {botSta}
    ━━━━━━━━━━━━━━━
    </b>"""


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
    # Command: /approve_inr

    bot.deleteMessage(message.chat.id, message.message_id)

    parts = params.split()

    user_id = parts[0]
    amount = float(parts[1])

    libs.Resources.anotherRes("Balance", user=user_id).add(amount)

    bot.sendMessage(
        chat_id=user_id,
        text=f"✅ Deposit Approved!\n💰 ₹{amount} Added to your balance."
    )

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
    "<blockquote><tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> INSUFFICIENT BALANCE</blockquote>\n\n"
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
                [
                    {
                        "text": "VERIFY PAYMENT",
                        "callback_data": "/autobuyi",
                        "style": "success",
                        "icon_custom_emoji_id": "6278302366303260172"
                    }
                ],
                [
                    {
                        "text": "CANCEL",
                        "callback_data": "/cancel",
                        "style": "danger",
                        "icon_custom_emoji_id": "6278116707751956084"
                    }
                ]
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
            "<tg-emoji emoji-id='5348129380474306311'>✅</tg-emoji> Payment Success!\n\n"
            "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> Added ₹" + str(amount) + "\n"
            "<tg-emoji emoji-id='5346227465876423936'>💳</tg-emoji> New Balance: ₹" + str(bal.value()),
            parse_mode="HTML"
        )
        AllBotAdminss = Bot.getData("AllBotAdminss") or []
        for admin in AllBotAdminss:
            bot.sendMessage(
                chat_id=admin,
                text=
                "<tg-emoji emoji-id='5348129380474306311'>✅</tg-emoji> New Payment Received!\n\n"
                "👤 User ID: <code>" + str(u) + "</code>\n"
                "💰 Amount: ₹" + str(amount) + "\n"
                "🧾 Order ID: <code>" + str(order_id) + "</code>\n"
                "💳 User Balance: ₹" + str(bal.value()),
                parse_mode="HTML")

    else:
        bot.sendMessage(
            "<tg-emoji emoji-id='6278116707751956084'>❌</tg-emoji> Payment Not Received\n\nPlease complete the payment and try again.",
            parse_mode="HTML"
        )



def cmd__backkkk(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    first_name = message.from_user.first_name or "User"
    balance = libs.Resources.anotherRes("Balance", user=u).value()

    text = (
        "<blockquote>"
        "<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> "
        "WELCOME TO HACK STORE "
        "<tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji>"
        "</blockquote>\n\n"

        "<i>"
        "<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> "
        "Your ultimate destination for premium mods, cheats & clients!"
        "</i>\n\n"

        "<blockquote>"
        "<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> PREMIUM FEATURES\n\n"

        "<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Instant Key Delivery\n"

        "<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Secure Auto-Payment System\n"

        "<tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji> 100% Anti-Ban Support"
        "</blockquote>\n\n"

        "<blockquote>"
        "<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Your Balance: ₹" + str(balance) +
        "</blockquote>"
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
                    [
                        {
                            "text": "BUY HACK",
                            "callback_data": "/shopnawkk",
                            "style": "success",
                            "icon_custom_emoji_id": "6093739864883207194"
                        }
                    ],
                    [
                        {
                            "text": "MY KEY",
                            "callback_data": "/orderksk",
                            "style": "success",
                            "icon_custom_emoji_id": "5967456680940671207"
                        },
                        {
                            "text": "PROFILE",
                            "callback_data": "/profilemmm",
                            "style": "success",
                            "icon_custom_emoji_id": "5346136537123801643"
                        }
                    ],
                    [
                        {
                            "text": "HOW TO USE",
                            "callback_data": "/spinj",
                            "style": "success",
                            "icon_custom_emoji_id": "5345783284653636765"
                        },
                        {
                            "text": "SUPPORT",
                            "callback_data": "/supportj",
                            "style": "success",
                            "icon_custom_emoji_id": "5897567714674741148"
                        }
                    ],
                    [
                        {
                            "text": "ADD FUND",
                            "callback_data": "/addpayment",
                            "style": "success",
                            "icon_custom_emoji_id": "6278302366303260172"
                        }
                    ],
                    [
                        {
                            "text": "PAY PROOF",
                            "url": "https://t.me/subhajit_feedback",
                            "style": "success",
                            "icon_custom_emoji_id": "5258134813302332906"
                        },
                        {
                            "text": "DOWNLOAD APK",
                            "url": "https://t.me/+hasTLSVjzaZjZGVl",
                            "style": "success",
                            "icon_custom_emoji_id": "6028115612163641653"
                        }
                    ]
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
    
        txt = f"""<b>
    🎙️ Broadcast Done
    
    👥 Total: {total}
    ✅ Success: {success}
    ❌ Failed: {fail}
    </b>"""
        bot.sendMessage(txt)
    except:
        bot.sendMessage("<b>❌ Broadcast Data Process Failed</b>")



def cmd__broadcast(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    admins = ["6204125653", "8102646437"]
    if str(u) not in admins:
        raise ReturnCommand()

    if options == None:
        bot.replyText(u, "<b>🎙️ Send Any Message To Broadcast in HTML\n\nTo Cancel: /cancel</b>", parse_mode="html")
        Bot.handleNextCommand("/broadcast", options=True)
        raise ReturnCommand()
    else:
        if message.text == "/cancel":
            bot.sendMessage("<b>❌ Cancelled</b>", parse_mode="html")
            raise ReturnCommand()

    # Function to create broadcast code
    def broadcast(method, txt, fileId):
        typ = method.lower()
        if method == "Message":
            code = f"""bot.sendMessage(chat_id=u, text='''{txt}''', parse_mode="html")"""
        elif str(txt) == "None":
            code = f"""bot.send{method}(chat_id=u, {typ}="{fileId}")"""
        else:
            code = f"""bot.send{method}(chat_id=u, {typ}="{fileId}", caption='''{txt}''', parse_mode="html")"""
        return code

    # Detect content and apply HTML formatting
    txt = message.caption if message.caption else message.text
    entities = message.caption_entities if message.caption else message.entities
    txt = apply_html_entities(txt, entities, {})  # Corrected with third param

    # Identify message type and prepare broadcast
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
        bot.sendMessage("<b>❌ Wrong File Format!</b>", parse_mode="html")
        raise ReturnCommand()

    # Launch the broadcast
    url = libs.Webhook.getUrlFor("/broadResult", u)
    task = Bot.broadcast(code=code, callback_url=url)
    Bot.saveData(task, None)
    bot.sendMessage("<b>🔁 Broadcast Processing...</b>", parse_mode="html")



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

    # -------------------------
    # OPTIONS
    # -------------------------
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

    # -------------------------
    # STOCK CHECK
    # -------------------------
    keys = Bot.getData(key_name) or []

    if len(keys) == 0:
        bot.sendMessage("❌ Out of Stock.")
        raise ReturnCommand()

    # -------------------------
    # WALLET CHECK
    # -------------------------
    balance = libs.Resources.anotherRes("Balance", user=u)

    if balance.value() < price:

        User.saveData("last_deposit_amount", price)
        User.saveData("last_product", title)

        Bot.runCommand("/autobuy1")

        raise ReturnCommand()

    # -------------------------
    # DEDUCT BALANCE
    # -------------------------
    libs.Resources.anotherRes("Balance", user=u).cut(price)

    libs.Resources.anotherRes("Order", user=u).add(1)

    # -------------------------
    # GIVE KEY
    # -------------------------
    key = str(keys[0])
    keys.pop(0)

    Bot.saveData(key_name, keys)

    # -------------------------
    # SUCCESS MESSAGE
    # -------------------------
    bot.sendMessage(
        f"<tg-emoji emoji-id='6172208745582433583'>🛒</tg-emoji> {title}\n\n"
        f"<tg-emoji emoji-id='6005570495603282482'>🔑</tg-emoji> <b>Your Key:</b>\n<code>{key}</code>\n\n"
        f"<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> Deducted: ₹{price}\n"
        f"<tg-emoji emoji-id='5967456680940671207'>📦</tg-emoji> Remaining Stock: {len(keys)}\n"
        f"<tg-emoji emoji-id='6278102040438640835'>📦</tg-emoji> Time: {EasyTime}\n\n"
        f"<tg-emoji emoji-id='6264989131621798851'>📢</tg-emoji> <b>ALL FILES UPDATE</b>\n"
        f"@SUBHAJIT_UPDATES",
        parse_mode="HTML"
    )

    # -------------------------
    # USER LOG
    # -------------------------
    AdmAC = User.getData("userhAC") or []

    AdmAC.append(
        f"📆 {EasyTime}\n"
        f"👤 {message.from_user.first_name} [{u}]\n"
        f"💰 ₹{price}\n"
        f"🔑 {key}\n"
    )

    User.saveData("userhAC", AdmAC)

    # -------------------------
    # ADMIN NOTIFY
    # -------------------------
    admin_id = Bot.getData("admin_id")

    if admin_id:
        try:
            bot.sendMessage(
                chat_id=admin_id,
                text=f"🛒 New Sale\n\n👤 {u}\n📦 {title}\n💰 ₹{price}"
            )
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
    # PARAM CHECK

    if not params:
        bot.sendMessage("❌ Invalid Product")
        raise ReturnCommand()

    # DRIP CLIENT
    # =========================
    # DRIP CLIENT APK MOD
    # =========================

    if params == "1":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","1 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "drip_1d_price",
                "key": "drip_1d_keys",
                "title": "DRIP CLIENT APK MOD\n1 Day"
            }
        )
        raise ReturnCommand()

    if params == "2":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","3 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "drip_3d_price",
                "key": "drip_3d_keys",
                "title": "DRIP CLIENT APK MOD\n3 Days"
            }
        )
        raise ReturnCommand()

    if params == "3":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","7 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "drip_7d_price",
                "key": "drip_7d_keys",
                "title": "DRIP CLIENT APK MOD\n7 Days"
            }
        )
        raise ReturnCommand()

    if params == "4":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","15 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "drip_15d_price",
                "key": "drip_15d_keys",
                "title": "DRIP CLIENT APK MOD\n15 Days"
            }
        )
        raise ReturnCommand()

    if params == "5":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","30 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "drip_30d_price",
                "key": "drip_30d_keys",
                "title": "DRIP CLIENT APK MOD\n30 Days"
            }
        )
        raise ReturnCommand()

    # =========================
    # PROXY SERVER [DR-CL]
    # =========================

    if params == "6":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","1 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "PATO_1d_price",
                "key": "PATO_1d_keys",
                "title": "PROXY SERVER [DR-CL]\n1 Day"
            }
        )
        raise ReturnCommand()

    if params == "7":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","3 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "PATO_3d_price",
                "key": "PATO_3d_keys",
                "title": "PROXY SERVER [DR-CL]\n3 Days"
            }
        )
        raise ReturnCommand()

    if params == "8":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","7 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "PATO_7d_price",
                "key": "PATO_7d_keys",
                "title": "PROXY SERVER [DR-CL]\n7 Days"
            }
        )
        raise ReturnCommand()

    if params == "9":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","10 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "PATO_15d_price",
                "key": "PATO_15d_keys",
                "title": "PROXY SERVER [DR-CL]\n10 Days"
            }
        )
        raise ReturnCommand()
    
    if params == "10":
        User.saveData("last_product1", "𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗")
        User.saveData("last_plan","1 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "HG_1d_price",
                "key": "HG_1d_keys",
                "title": "PRIME-HOOK\n1 Day"
            }
        )
        raise ReturnCommand()


    elif params == "11":
        User.saveData("last_product1", "𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗")
        User.saveData("last_plan","3 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "HG_3d_price",
                "key": "HG_3d_keys",
                "title": "PRIME-HOOK\n3 Days"
            }
        )
        raise ReturnCommand()


    elif params == "12":
        User.saveData("last_product1", "HG-CHEATS ANDROID")
        User.saveData("last_plan","7 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "HG_7d_price",
                "key": "HG_7d_keys",
                "title": "PRIME-HOOK\n7 Days"
            }
        )
        raise ReturnCommand()


    elif params == "13":
        User.saveData("last_product1", "𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗")
        User.saveData("last_plan","14 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "HG_14d_price",
                "key": "HG_14d_keys",
                "title": "PRIME-HOOK\n14 Days"
            }
        )
        raise ReturnCommand()


    elif params == "14":
        User.saveData("last_product1", "𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗")
        User.saveData("last_plan","21 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "HG_21d_price",
                "key": "HG_21d_keys",
                "title": "PRIME-HOOK\n21 Days"
            }
        )
        raise ReturnCommand()

    bot.sendMessage("❌ Invalid Product ID")



def cmd__buyjai_reseller(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    # PARAM CHECK

    if not params:
        bot.sendMessage("❌ Invalid Product")
        raise ReturnCommand()

    # DRIP CLIENT
    # =========================
    # DRIP CLIENT APK MOD
    # =========================

    if params == "1":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","1 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "drip_1d_reseller_price",
                "key": "drip_1d_keys",
                "title": "🎮 DRIP CLIENT APK MOD\n1 Day"
            }
        )
        raise ReturnCommand()

    if params == "2":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","3 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "drip_3d_reseller_price",
                "key": "drip_3d_keys",
                "title": "🎮 DRIP CLIENT APK MOD\n3 Days"
            }
        )
        raise ReturnCommand()

    if params == "3":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","7 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "drip_7d_reseller_price",
                "key": "drip_7d_keys",
                "title": "🎮 DRIP CLIENT APK MOD\n7 Days"
            }
        )
        raise ReturnCommand()

    if params == "4":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","15 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "drip_15d_reseller_price",
                "key": "drip_15d_keys",
                "title": "🎮 DRIP CLIENT APK MOD\n15 Days"
            }
        )
        raise ReturnCommand()

    if params == "5":
        User.saveData("last_product1", "DRIP CLIENT APK MOD")
        User.saveData("last_plan","30 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "drip_30d_reseller_price",
                "key": "drip_30d_keys",
                "title": "🎮 DRIP CLIENT APK MOD\n30 Days"
            }
        )
        raise ReturnCommand()

    # =========================
    # PROXY SERVER [DR-CL]
    # =========================

    if params == "6":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","1 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "PATO_1d_reseller_price",
                "key": "PATO_1d_keys",
                "title": "📦 PROXY SERVER [DR-CL]\n1 Day"
            }
        )
        raise ReturnCommand()

    if params == "7":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","3 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "PATO_3d_reseller_price",
                "key": "PATO_3d_keys",
                "title": "📦 PROXY SERVER [DR-CL]\n3 Days"
            }
        )
        raise ReturnCommand()

    if params == "8":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","7 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "PATO_7d_reseller_price",
                "key": "PATO_7d_keys",
                "title": "📦 PROXY SERVER [DR-CL]\n7 Days"
            }
        )
        raise ReturnCommand()

    if params == "9":
        User.saveData("last_product1", "PROXY SERVER [DR-CL]")
        User.saveData("last_plan","10 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "PATO_15d_reseller_price",
                "key": "PATO_15d_keys",
                "title": "📦 PROXY SERVER [DR-CL]\n10 Days"
            }
        )
        raise ReturnCommand()
    
    if params == "10":
        User.saveData("last_product1", "𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀")
        User.saveData("last_plan","1 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "HG_1d_reseller_price",
                "key": "HG_1d_keys",
                "title": "🛒 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n1 Day"
            }
        )
        raise ReturnCommand()


    elif params == "11":
        User.saveData("last_product1", "𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀")
        User.saveData("last_plan","3 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "HG_3d_reseller_price",
                "key": "HG_3d_keys",
                "title": "🛒 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n3 Days"
            }
        )
        raise ReturnCommand()


    elif params == "12":
        User.saveData("last_product1", "HG-CHEATS ANDROID")
        User.saveData("last_plan","7 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "HG_7d_reseller_price",
                "key": "HG_7d_keys",
                "title": "🛒 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n7 Days"
            }
        )
        raise ReturnCommand()


    elif params == "13":
        User.saveData("last_product1", "𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀")
        User.saveData("last_plan","14 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "HG_14d_reseller_price",
                "key": "HG_14d_keys",
                "title": "🛒 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n14 Days"
            }
        )
        raise ReturnCommand()


    elif params == "14":
        User.saveData("last_product1", "𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀")
        User.saveData("last_plan","21 Day")
        Bot.runCommand(
            "/buybahha",
            options={
                "price": "HG_21d_reseller_price",
                "key": "HG_21d_keys",
                "title": "🛒 𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀\n21 Days"
            }
        )
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

    bot.sendMessage(
        chat_id=u,
        text="<tg-emoji emoji-id='6278116707751956084'>❌</tg-emoji> Cancelled",
        parse_mode="HTML"
    )



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
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹0\n\n"
        "Use the keypad below to enter amount.",
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



def cmd__num0(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    amt = str(User.getData("pay_amount") or "")
    amt += "0"

    User.saveData("pay_amount", amt)

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount.",
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
    amt = str(User.getData("pay_amount") or "")
    amt += "1"

    User.saveData("pay_amount", amt)

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount.",
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
    amt = str(User.getData("pay_amount") or "")
    amt += "2"

    User.saveData("pay_amount", amt)

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount.",
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
    amt = str(User.getData("pay_amount") or "")
    amt += "3"

    User.saveData("pay_amount", amt)

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount.",
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
    amt = str(User.getData("pay_amount") or "")
    amt += "4"

    User.saveData("pay_amount", amt)

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount.",
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
    amt = str(User.getData("pay_amount") or "")
    amt += "5"

    User.saveData("pay_amount", amt)

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount.",
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
    amt = str(User.getData("pay_amount") or "")
    amt += "6"

    User.saveData("pay_amount", amt)

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount.",
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
    amt = str(User.getData("pay_amount") or "")
    amt += "7"

    User.saveData("pay_amount", amt)

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount.",
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
    amt = str(User.getData("pay_amount") or "")
    amt += "8"

    User.saveData("pay_amount", amt)

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount.",
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
    amt = str(User.getData("pay_amount") or "")
    amt += "9"

    User.saveData("pay_amount", amt)

    bot.editMessageText(
        chat_id=u,
        message_id=message.message_id,
        text=
        "<blockquote>"
        "<tg-emoji emoji-id='6089104607328342288'>💰</tg-emoji> "
        "ENTER CUSTOM AMOUNT"
        "</blockquote>\n\n"
        "Amount: ₹" + amt +
        "\n\nUse the keypad below to enter amount.",
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
        "<tg-emoji emoji-id='6008118472066732010'>📦</tg-emoji> <b>MY ORDERS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "You haven't placed any orders yet.\n"
        "Tap <tg-emoji emoji-id='6093562529978522804'>🛒</tg-emoji> Shop Now to get started!"
    )

    AdmAC = User.getData("userhAC") or []

    if not AdmAC:

        try:
            bot.editMessageText(
                chat_id=u,
                message_id=message.message_id,
                text=textn,
                parse_mode="HTML",
                reply_markup={
                    "inline_keyboard": [
                        [
                            {
                                "text": "BACK",
                                "callback_data": "/backkkk",
                                "style": "danger",
                                "icon_custom_emoji_id": "6039539366177541657"
                            }
                        ]
                    ]
                }
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
                    reply_markup={
                        "inline_keyboard": [
                            [
                                {
                                    "text": "BACK",
                                    "callback_data": "/backkkk",
                                    "style": "danger",
                                    "icon_custom_emoji_id": "6039539366177541657"
                                }
                            ]
                        ]
                    }
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
    hh = libs.Resources.anotherRes("Oder", user=u).value()

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
        "<tg-emoji emoji-id='5346136537123801643'>👤</tg-emoji> YOUR PROFILE\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "<tg-emoji emoji-id='6008118472066732010'>📛</tg-emoji> Name: " + str(first_name) + "\n"

        "<tg-emoji emoji-id='5841693351249710667'>🆔</tg-emoji> User ID: " + str(u) + "\n"

        "<tg-emoji emoji-id='5348374038991357363'>💰</tg-emoji> Balance: ₹" + str(balance) + "\n"

        "<tg-emoji emoji-id='5348490024583185697'>📅</tg-emoji> Member Since: " + str(member_since) + "\n"

        "<tg-emoji emoji-id='6093562529978522804'>🛒</tg-emoji> Total Orders: " + str(hh) + "\n\n"

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
                    [
                        {
                            "text": "BUY HACK",
                            "callback_data": "/shopnawkk",
                            "style": "success",
                            "icon_custom_emoji_id": "6093739864883207194"
                        },
                        {
                            "text": "MY KEY",
                            "callback_data": "/orderksk",
                            "style": "success",
                            "icon_custom_emoji_id": "5967456680940671207"
                        }
                    ],
                    [
                        {
                            "text": "BACK",
                            "callback_data": "/backkkk",
                            "style": "danger",
                            "icon_custom_emoji_id": "6039539366177541657"
                        }
                    ]
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
    # Command: /reject
    bot.deleteMessage(message.chat.id, message.message_id)
    try:
        parts = params.split()

        user_id = parts[0]
        amount = parts[1]

        # ❌ No balance added (reject case)

        bot.sendMessage(
            chat_id=user_id,
            text=f"❌ Deposit Rejected!\n💰 ₹{amount} Request has been declined."
        )

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
        target_user = str(int(message.text))  # convert input to string
    except:
        bot.sendMessage("❌ Invalid User ID.")
        raise ReturnCommand()

    # Get current resellers list
    resellers = Bot.getData("resellers_list") or []

    # Ensure the user exists before attempting removal
    if target_user not in [str(u) for u in resellers]:
        bot.sendMessage("⚠️ User is not a reseller.")
        raise ReturnCommand()

    # Remove the user
    resellers = [u for u in resellers if str(u) != target_user]
    Bot.saveData("resellers_list", resellers)

    bot.sendMessage(
        f"✅ User <code>{target_user}</code> removed from Resellers.",
        parse_mode="html"
    )

    # Optional: notify the user
    try:
        bot.sendMessage(
            chat_id=target_user,
            text="❌ You are no longer a Reseller."
        )
    except:
        pass



def cmd__removereseller(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    bot.sendMessage(
        u,
        "📩 Send me reseller id to remove"
    )

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

    commands = [
        {'command': 'start', 'description': ' START TO BUY'},
    ]

    url = f'https://api.telegram.org/bot{bot_token}/setMyCommands'
    headers = {'Content-type': 'application/json'}

    data = {
        'commands': commands
    }

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
        bot.replyText(
            u,
            "<b><i>🚫 You Are Not This Bot Admin</i></b>",
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



   


    markup = InlineKeyboardMarkup()


    markup.add(
        InlineKeyboardButton(text=' 𝗗𝗥𝗜𝗣 𝗖𝗟𝗜𝗘𝗡𝗧 𝗠𝗢𝗗✅', callback_data='/SHOPADMIN_P1'))
    markup.add(
        InlineKeyboardButton(text='PROXY SERVER [DR-CL]', callback_data='/SHOPADMIN_P3'))
    
    markup.add(
        InlineKeyboardButton(text='𝗣𝗥𝗜𝗠𝗘 𝗠𝗢𝗗 💀', callback_data='/SHOPADMIN_P2'))

 
    
    markup.add(InlineKeyboardButton(text='🔙Back',callback_data='/admin AP'))


    TXT = f"""<b>
    👋 Welcome {message.from_user.first_name} 🎉

    ━━━━━━━━━━━━━━━
    SHOP 🛍️ MOOD
    ━━━━━━━━━━━━━━━
    </b>"""


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
    text = f"""
    ━━━━━━━━━━━━━━━━━━━━
    <tg-emoji emoji-id="6093562529978522804">🛒</tg-emoji> <b>PANNEL STORE — SHOP</b>
    ━━━━━━━━━━━━━━━━━━━━

    <tg-emoji emoji-id="6179339404906079822">📦</tg-emoji> Choose a product:
    """

    try:
        bot.editMessageText(
            chat_id=u,
            message_id=message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [
                    [
                        {
                            "text": "DRIP CLIENT NON-ROOT",
                            "callback_data": "/SHOP_P1",
                            "style": "success",
                            "icon_custom_emoji_id": "6323104647636589287"
                        }
                    ],
                    [
                        {
                            "text": "PROXY SERVER [DR-CL]",
                            "callback_data": "/SHOP_P2",
                            "style": "success",
                            "icon_custom_emoji_id": "6212942266957310140"
                        }
                    ],
                    [
                        {
                            "text": "PRIME HOOK",
                            "callback_data": "/SHOP_P4",
                            "style": "success",
                            "icon_custom_emoji_id": "6210705396449944693"
                        }
                    ],
                    [
                        {
                            "text": "BACK",
                            "callback_data": "/backkkk",
                            "style": "danger",
                            "icon_custom_emoji_id": "6039539366177541657"
                        }
                    ]
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
    <tg-emoji emoji-id='5368653135101310687'>🎥</tg-emoji> <b>Watch the full tutorial video below</b>

    <tg-emoji emoji-id='6222198028854367391'>👇</tg-emoji>
    """

    try:
        bot.editMessageText(
            chat_id=u,
            message_id=message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [
                    [
                        {
                            "text": "Watch Tutorial",
                            "url": "https://t.me/hehehehhhsljg/162",
                            "style": "success",
                            "icon_custom_emoji_id": "6179339404906079822"
                        }
                    ],
                    [
                        {
                            "text": "BACK",
                            "callback_data": "/backkkk",
                            "style": "danger",
                            "icon_custom_emoji_id": "6039539366177541657"
                        }
                    ]
                ]
            }
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise e

    raise ReturnCommand()



def cmd__start(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    joined = User.getData("joined_date")

    if not joined:
        User.saveData("joined_date", message.date)

    first_name = message.from_user.first_name or "User"
    balance = libs.Resources.anotherRes("Balance", user=u).value()

    text = (
        "<blockquote>"
        "<tg-emoji emoji-id='5345976085735558094'>🌟</tg-emoji> "
        "WELCOME TO HACK STORE "
        "<tg-emoji emoji-id='5348292765325212780'>🌙</tg-emoji>"
        "</blockquote>\n\n"

        "<i>"
        "<tg-emoji emoji-id='5346024644635804737'>✨</tg-emoji> "
        "Your ultimate destination for premium mods, cheats & clients!"
        "</i>\n\n"

        "<blockquote>"
        "<tg-emoji emoji-id='5316571734604790521'>🚀</tg-emoji> PREMIUM FEATURES\n\n"

        "<tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji> Instant Key Delivery\n"

        "<tg-emoji emoji-id='6120544300511007571'>💳</tg-emoji> Secure Auto-Payment System\n"

        "<tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji> 100% Anti-Ban Support"
        "</blockquote>\n\n"

        "<blockquote>"
        "<tg-emoji emoji-id='5348392971207194994'>💰</tg-emoji> Your Balance: ₹" + str(balance) +
        "</blockquote>"
    )

    bot.sendMessage(
        chat_id=u,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup={
            "inline_keyboard": [

                [
                    {
                        "text": "BUY HACK",
                        "callback_data": "/shopnawkk",
                        "style": "success",
                        "icon_custom_emoji_id": "6093739864883207194"
                    }
                ],

                [
                    {
                        "text": "MY KEY",
                        "callback_data": "/orderksk",
                        "style": "success",
                        "icon_custom_emoji_id": "5967456680940671207"
                    },
                    {
                        "text": "PROFILE",
                        "callback_data": "/profilemmm",
                        "style": "success",
                        "icon_custom_emoji_id": "5346136537123801643"
                    }
                ],

                [
                    {
                        "text": "HOW TO USE",
                        "callback_data": "/spinj",
                        "style": "success",
                        "icon_custom_emoji_id": "5345783284653636765"
                    },
                    {
                        "text": "SUPPORT",
                        "callback_data": "/supportj",
                        "style": "success",
                        "icon_custom_emoji_id": "5897567714674741148"
                    }
                ],

                [
                    {
                        "text": "ADD FUND",
                        "callback_data": "/addpayment",
                        "style": "success",
                        "icon_custom_emoji_id": "6278302366303260172"
                    }
                ],

                [
                    {
                        "text": "PAY PROOF",
                        "url": "https://t.me/subhajit_feedback",
                        "style": "success",
                        "icon_custom_emoji_id": "5258134813302332906"
                    },
                    {
                        "text": "DOWNLOAD APK",
                        "url": "https://t.me/+hasTLSVjzaZjZGVl",
                        "style": "success",
                        "icon_custom_emoji_id": "6028115612163641653"
                    }
                ]

            ]
        }
    )



def cmd__supportj(ctx):
    bot = ctx["bot"]
    User = ctx["User"]
    u = ctx["u"]
    message = ctx["message"]
    params = ctx["params"]
    options = ctx["options"]
    text = """
    ━━━━━━━━━━━━━━━━━━━━
    <tg-emoji emoji-id='5891120964468480450'>💬</tg-emoji> <b>Support — Seller</b> <tg-emoji emoji-id='5346160971192747426'>🛡</tg-emoji>
    ━━━━━━━━━━━━━━━━━━━━

    Need help? We're here for you! <tg-emoji emoji-id='5346289416484699504'>⚡</tg-emoji>

    📩 <b>Telegram:</b> <tg-emoji emoji-id='5776182936638329359'>⭐</tg-emoji>

    <a href="https://t.me/UR_SUBHAJIT0">𝐒υʜᴀᎫιт</a> <tg-emoji emoji-id='6118314396440596568'>⭐</tg-emoji>

    <tg-emoji emoji-id='5891120964468480450'>💡</tg-emoji> <i>Include your User ID (from Profile)
    when contacting for faster help.</i>
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
                    [
                        {
                            "text": "WHATSAPP",
                            "url": "https://wa.me/917908696630",
                            "style": "success",
                            "icon_custom_emoji_id": "6109296665926047025"
                        }
                    ],
                    [
                        {
                            "text": "BACK",
                            "callback_data": "/backkkk",
                            "style": "danger",
                            "icon_custom_emoji_id": "6039539366177541657"
                        }
                    ]
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
# PART 3: DISPATCHER (routes Telegram updates to the commands above)
# ======================================================================

import contextvars
import json


# Lets Bot.handleNextCommand() know which user it's being called for.
CURRENT_USER = contextvars.ContextVar("CURRENT_USER", default=None)


class _MessageProxy:
    """Normalizes text-message and callback-query updates into one shape:
    from_user is always the ACTING human, chat/message_id point at the
    message to edit/reply to, and .text mirrors the triggering string."""

    def __init__(self, chat, message_id, from_user, text, date=None, real_message=None):
        self.chat = chat
        self.message_id = message_id
        self.from_user = from_user
        self.text = text
        self.date = date
        self._real = real_message  # underlying telebot Message, for photo/video/etc access

    def __getattr__(self, item):
        # fall through to the real underlying message for photo/video/document/etc.
        if self._real is not None:
            return getattr(self._real, item)
        raise AttributeError(item)


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
    """Used by Bot.runCommand()/Bot.broadcast() to invoke a command outside
    the normal update flow. `options` may itself carry a target chat id via
    the caller's context; here we fall back to the currently-set user."""
    uid = CURRENT_USER.get()
    if uid is None:
        return
    proxy = _MessageProxy(chat=_FakeChat(int(uid)), message_id=None,
                           from_user=_FakeUser(uid), text=cmd_name)
    _invoke(cmd_name, uid, proxy, "", options)


class _FakeChat:
    def __init__(self, chat_id):
        self.id = chat_id


class _FakeUser:
    def __init__(self, uid):
        self.id = int(uid)
        self.first_name = "User"


def _mark_known_user(uid):
    ref = _safe_ref(f"users/{uid}/known")
    if ref is not None:
        try:
            ref.set(True)
        except Exception:
            pass


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

    # Not a command -> check for a pending "next command" state
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
# PART 4: MAIN
# ======================================================================

import time
def main():
    print("Bot starting (long polling)...")
    while True:
        try:
            bot_client.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"[polling crashed, restarting in 5s] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
