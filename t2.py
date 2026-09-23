# -*- coding: utf-8 -*-

import os
import json
import threading
import time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import telebot
from telebot.apihelper import ApiTelegramException

# ==========================
# BOT TOKEN
# ==========================
TOKEN = "8742898125:AAG4UuvNZRHLLFedtm1h-mQeqBNJqAsEPQ4"

# فقط این کاربرها اجازه استفاده از دستورات ادمین دارند
ADMIN_IDS = [
    6368497114,
    5408605464,
    5589292203,
    6648642399
]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

GROUPS_FILE = "groups.json"

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
    valid_groups = []

    for gid in groups:
        try:
            bot.send_message(gid, text)
            valid_groups.append(gid)
        except Exception:
            pass

    save_groups(valid_groups)
    print(f"[Countdown] Sent to {len(valid_groups)} groups | School: {school_days} | Konkur: {konkur_days}")


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
# شروع بات + زمان‌بند
# ==========================
if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=daily_scheduler, daemon=True)
    scheduler_thread.start()

    print("Bot Started...")
    bot.infinity_polling(skip_pending=True)