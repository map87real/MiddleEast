# -*- coding: utf-8 -*-

import os
import json
import telebot
from telebot.apihelper import ApiTelegramException

# ==========================
# BOT TOKEN
# ==========================
TOKEN = "8742898125:AAG4UuvNZRHLLFedtm1h-mQeqBNJqAsEPQ4"

# فقط این کاربر اجازه Broadcast دارد
ADMIN_IDS = [
	6368497114,
	5408605464,
	5589292203
]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

GROUPS_FILE = "groups.json"


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
# Save Groups
# ==========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "زنده باد میدل ایست!")

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "سیکتیر")

@bot.message_handler(
    func=lambda m: m.chat.type in ["group", "supergroup"]
    and m.text
    and m.text.startswith("بیانیه")
)
def bayanieh(message):

    # فقط ادمین‌های مجاز
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

    # جلوگیری از پاسخ به همه پیام‌ها
    if not message.text:
        return

    if not message.text.startswith("/broadcast"):
        return

    # فقط ادمین
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not allowed.")
        return

    groups = load_groups()

    if len(groups) == 0:
        bot.reply_to(message, "No groups found.")
        return

    sent = 0
    removed = 0

    # ======================
    # حالت ریپلای
    # ======================
    if message.reply_to_message:

        source_chat = message.chat.id
        source_message = message.reply_to_message.message_id

        valid_groups = []

        for gid in groups:
            try:
                bot.copy_message(
                    gid,
                    source_chat,
                    source_message
                )
                sent += 1
                valid_groups.append(gid)

            except ApiTelegramException:
                removed += 1

            except Exception:
                removed += 1

        save_groups(valid_groups)

        bot.reply_to(
            message,
            f"✅ Finished\n\n"
            f"Sent: {sent}\n"
            f"Removed: {removed}"
        )

        return

    # ======================
    # حالت متن
    # ======================

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

    bot.reply_to(
        message,
        f"✅ Finished\n\n"
        f"Sent: {sent}\n"
        f"Removed: {removed}"
    )


print("Bot Started...")
bot.infinity_polling(skip_pending=True)