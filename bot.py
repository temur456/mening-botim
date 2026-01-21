import telebot
from telebot import types
import yt_dlp
import os
from flask import Flask
from threading import Thread

# Render uchun Web Server
app = Flask('')

@app.route('/')
def home():
    return "Bot yoniq!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# Bot sozlamalari
TOKEN = "7713870666:AAGEs_OJsrFTDVCNjgSVVedsiQfwII7K_Q0"
bot = telebot.TeleBot(TOKEN)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@bot.message_handler(commands=['start', 'help'])
def start(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎵 Musiqa", "🎬 Video")
    bot.send_message(message.chat.id, "👋 Salom! Yo'nalishni tanlang 👇", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🎵 Musiqa")
def ask_music(message):
    bot.send_message(message.chat.id, "🎵 Qo'shiq nomi yoki YouTube link yuboring")
    bot.register_next_step_handler(message, download_music)

@bot.message_handler(func=lambda m: m.text == "🎬 Video")
def ask_video(message):
    bot.send_message(message.chat.id, "🎬 YouTube video link yuboring")
    bot.register_next_step_handler(message, download_video)

def download_music(message):
    query = message.text
    bot.send_message(message.chat.id, "🎵 Yuklanmoqda...")
    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}],
        'quiet': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}" if "http" not in query else query, download=True)
            file_path = f"{DOWNLOAD_DIR}/{info['title']}.mp3"
        with open(file_path, 'rb') as f:
            bot.send_audio(message.chat.id, f)
        os.remove(file_path)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")

def download_video(message):
    url = message.text
    bot.send_message(message.chat.id, "🎬 Video yuklanmoqda...")
    ydl_opts = {'format': 'best', 'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s', 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        with open(file_path, 'rb') as f:
            bot.send_video(message.chat.id, f)
        os.remove(file_path)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")

if __name__ == "__main__":
    keep_alive()
    print("🤖 Bot ishlamoqda...")
    bot.infinity_polling()

