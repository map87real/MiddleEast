# -*- coding: utf-8 -*-

import os
import json
import threading
import time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot.apihelper import ApiTelegramException

# ==========================
# BOT TOKEN
# ==========================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

# فقط این کاربرها اجازه استفاده از دستورات ادمین دارند
ADMIN_IDS = [
    6368497114,
    5408605464,
    5589292203,
    6648642399
]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

GROUPS_FILE = "groups.json"
MUTED_FILE = "muted_groups.json"

# ==========================
# تاریخ‌های هدف (میلادی)
# ==========================
SCHOOL_END = date(2027, 3, 21)      # ۱ فروردین ۱۴۰۶ (عید نوروز)
KONKUR_DATE = date(2027, 7, 2)      # ۱۱ تیر ۱۴۰۶


# ==========================
# Groups File
# ==========================

def load_groups():
    if not os.path.exists(GROUPS_FILE):
        return []
    try:
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_groups(groups):
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)


def add_group(chat_id):
    groups = load_groups()
    if chat_id not in groups:
        groups.append(chat_id)
        save_groups(groups)


# ==========================
# Muted Groups
# ==========================

def load_muted():
    if not os.path.exists(MUTED_FILE):
        return []
    try:
        with open(MUTED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_muted(muted):
    with open(MUTED_FILE, "w", encoding="utf-8") as f:
        json.dump(muted, f, ensure_ascii=False, indent=2)


def mute_group(chat_id):
    muted = load_muted()
    if chat_id not in muted:
        muted.append(chat_id)
        save_muted(muted)


def unmute_group(chat_id):
    muted = load_muted()
    if chat_id in muted:
        muted.remove(chat_id)
        save_muted(muted)


# ==========================
# محاسبه روزهای باقی‌مانده
# ==========================
def get_remaining_days():
    today = datetime.now(ZoneInfo("Asia/Tehran")).date()
    school_days = (SCHOOL_END - today).days
    konkur_days = (KONKUR_DATE - today).days
    return school_days, konkur_days


def send_daily_countdown():
    school_days, konkur_days = get_remaining_days()

    if school_days < 0 and konkur_days < 0:
        return

    text = ""
    if school_days >= 0:
        text += f"<b>{school_days}</b> روز تا پایان سال تحصیلی (عید نوروز) باقی مانده\n"
    if konkur_days >= 0:
        text += f"<b>{konkur_days}</b> روز تا کنکور سراسری ۱۴۰۶ باقی مانده"

    if not text:
        return

    groups = load_groups()
    muted = load_muted()
    valid_groups = []

    for gid in groups:
        if gid in muted:
            valid_groups.append(gid)
            continue

        try:
            bot.send_message(gid, text)
            valid_groups.append(gid)
        except Exception:
            pass

    save_groups(valid_groups)
    print(f"[Countdown] Sent to {len(valid_groups) - len(muted)} groups | School: {school_days} | Konkur: {konkur_days}")


# ==========================
# زمان‌بند شبانه (هر شب ۰۰:۰۰ تهران)
# ==========================
def daily_scheduler():
    tehran = ZoneInfo("Asia/Tehran")

    while True:
        now = datetime.now(tehran)
        next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if now >= next_run:
            next_run += timedelta(days=1)

        sleep_seconds = (next_run - now).total_seconds()
        print(f"[Scheduler] Next countdown at {next_run} (in {int(sleep_seconds)} seconds)")

        time.sleep(sleep_seconds)

        try:
            send_daily_countdown()
        except Exception as e:
            print(f"[Scheduler Error] {e}")

        time.sleep(60)


# ==========================
# Handlers
# ==========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "زنده باد میدل ایست!")


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "سیکتیر")


@bot.message_handler(commands=['countdown'])
def test_countdown(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    school_days, konkur_days = get_remaining_days()
    text = (
        f"<b>{school_days}</b> روز تا پایان سال تحصیلی (عید نوروز) باقی مانده\n"
        f"<b>{konkur_days}</b> روز تا کنکور سراسری ۱۴۰۶ باقی مانده"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=['mute'])
def mute_command(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if message.chat.type not in ["group", "supergroup"]:
        bot.reply_to(message, "این دستور فقط تو گروه کار می‌کنه.")
        return

    mute_group(message.chat.id)
    bot.reply_to(message, "روزشمار برای این گروه خاموش شد ✅")


@bot.message_handler(commands=['unmute'])
def unmute_command(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if message.chat.type not in ["group", "supergroup"]:
        bot.reply_to(message, "این دستور فقط تو گروه کار می‌کنه.")
        return

    unmute_group(message.chat.id)
    bot.reply_to(message, "روزشمار برای این گروه دوباره فعال شد ✅")


@bot.message_handler(
    func=lambda m: m.chat.type in ["group", "supergroup"]
    and m.text
    and m.text.startswith("بیانیه")
)
def bayanieh(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    text = message.text[len("بیانیه"):].strip()
    if not text:
        return

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    if message.reply_to_message:
        bot.send_message(
            message.chat.id,
            text,
            reply_to_message_id=message.reply_to_message.message_id
        )
    else:
        bot.send_message(message.chat.id, text)


@bot.message_handler(content_types=[
    'text',
    'photo',
    'video',
    'document',
    'audio',
    'voice',
    'sticker',
    'animation'
])
def save_chat(message):

    if message.chat.type in ["group", "supergroup"]:
        add_group(message.chat.id)

    if not message.text:
        return

    if not message.text.startswith("/broadcast"):
        return

    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not allowed.")
        return

    groups = load_groups()

    if len(groups) == 0:
        bot.reply_to(message, "No groups found.")
        return

    sent = 0
    removed = 0

    # حالت ریپلای
    if message.reply_to_message:
        source_chat = message.chat.id
        source_message = message.reply_to_message.message_id
        valid_groups = []

        for gid in groups:
            try:
                bot.copy_message(gid, source_chat, source_message)
                sent += 1
                valid_groups.append(gid)
            except ApiTelegramException:
                removed += 1
            except Exception:
                removed += 1

        save_groups(valid_groups)
        bot.reply_to(message, f"✅ Finished\n\nSent: {sent}\nRemoved: {removed}")
        return

    # حالت متن
    text = message.text.replace("/broadcast", "", 1).strip()

    if text == "":
        bot.reply_to(
            message,
            "Usage:\n"
            "/broadcast Your Text\n\n"
            "or reply to a message and send /broadcast"
        )
        return

    valid_groups = []

    for gid in groups:
        try:
            bot.send_message(gid, text)
            sent += 1
            valid_groups.append(gid)
        except ApiTelegramException:
            removed += 1
        except Exception:
            removed += 1

    save_groups(valid_groups)
    bot.reply_to(message, f"✅ Finished\n\nSent: {sent}\nRemoved: {removed}")


# ==========================
# سرور Health Check برای Render
# ==========================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        return  # جلوگیری از لاگ‌های اضافی


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health server running on port {port}")
    server.serve_forever()


# ==========================
# شروع بات + زمان‌بند + سرور HTTP
# ==========================
if __name__ == "__main__":
    # سرور HTTP برای Render و UptimeRobot
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # زمان‌بند روزانه
    scheduler_thread = threading.Thread(target=daily_scheduler, daemon=True)
    scheduler_thread.start()

    print("Bot Started...")
    bot.infinity_polling(skip_pending=True)