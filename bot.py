"""
╔══════════════════════════════════════════════════════════════════╗
║                    🎬 KODLI KINO BOT                            ║
║              To'liq O'zbek tilida Telegram Bot                  ║
║                   Barcha huquqlar himoyalangan                   ║
╚══════════════════════════════════════════════════════════════════╝

Texnologiya: Python + aiogram 3.x + SQLite
"""

import asyncio
import logging
import sqlite3
import json
import time
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, BotCommand
)

# ═══════════════════════════════════════════════════════
#                  ⚙️  SOZLAMALAR
# ═══════════════════════════════════════════════════════

# 🔑 BOT TOKEN - @BotFather dan oling
BOT_TOKEN = "8645831230:AAGhNicNKsdjhVeRb5CzhfyPXVJ6566AALM"

# 👑 ADMIN ID - @userinfobot dan oling
ADMIN_IDS = [7357676486]  # Bir nechta admin qo'shish mumkin

# 📢 MAJBURIY OBUNA KANALLARI
REQUIRED_CHANNELS = [
    {"id": -1001234567890, "username": "@sleep_filmz", "name": "Asosiy Kanal"},
    # {"id": -1009876543210, "username": "@your_channel2", "name": "Ikkinchi Kanal"},
]

# ⏱️ SPAM HIMOYA (sekundda nechta so'rov)
SPAM_LIMIT = 5  # Har 10 soniyada max so'rovlar soni
SPAM_TIME = 10  # Soniya

# 🎁 KUNLIK BONUS BALL
DAILY_BONUS_POINTS = 10

# 💎 VIP/PREMIUM narxlari (ball)
VIP_PRICE = 100
PREMIUM_PRICE = 200

# 🎬 KINO BAZASI (misol ma'lumotlar - admin orqali qo'shing)
MOVIES_DB = {
    "101": {
        "name": "Avengers: Endgame",
        "description": "Marvel kinematic olamining eng katta filmi. Qahramonlar oxirgi jangga tayyorlanadi.",
        "category": "action",
        "file_id": None,  # Admin kino qo'shganda to'ldiriladi
        "vip_only": False,
        "premium_only": False,
        "views": 0,
        "rating": 4.8,
        "added_date": "2024-01-01",
        "demo_url": None
    },
    "202": {
        "name": "Inception",
        "description": "Tush ichida tush - ong va haqiqat o'rtasidagi sirli sayohat.",
        "category": "thriller",
        "file_id": None,
        "vip_only": True,
        "premium_only": False,
        "views": 0,
        "rating": 4.9,
        "added_date": "2024-01-02",
        "demo_url": None
    },
    "303": {
        "name": "The Dark Knight",
        "description": "Batman va Joker o'rtasidagi epik jang. Barcha zamonlar eng yaxshi superhero filmi.",
        "category": "action",
        "file_id": None,
        "vip_only": False,
        "premium_only": False,
        "views": 0,
        "rating": 4.9,
        "added_date": "2024-01-03",
        "demo_url": None
    },
}

# ═══════════════════════════════════════════════════════
#                  📝 LOGGING SOZLASH
# ═══════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
#                  💾 DATABASE KLASSI
# ═══════════════════════════════════════════════════════

class Database:
    """SQLite ma'lumotlar bazasi boshqaruvchisi"""
    
    def __init__(self, db_name: str = "kinobaz.db"):
        self.db_name = db_name
        self.create_tables()
        self.load_movies_to_db()
    
    def get_conn(self):
        """Database ulanish olish"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_tables(self):
        """Barcha jadvallarni yaratish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Foydalanuvchilar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                status TEXT DEFAULT 'user',  -- user, vip, premium, admin
                points INTEGER DEFAULT 0,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                join_date TEXT,
                last_active TEXT,
                last_bonus TEXT,
                total_movies_watched INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0
            )
        """)
        
        # Kinolar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                movie_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT DEFAULT 'other',
                file_id TEXT,
                file_type TEXT DEFAULT 'video',
                vip_only INTEGER DEFAULT 0,
                premium_only INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                rating REAL DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                added_by INTEGER,
                added_date TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Reyting jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                movie_code TEXT,
                rating INTEGER,
                date TEXT,
                UNIQUE(user_id, movie_code)
            )
        """)
        
        # Spam himoya jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spam_control (
                user_id INTEGER PRIMARY KEY,
                request_count INTEGER DEFAULT 0,
                last_reset TEXT
            )
        """)
        
        # Kanallar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER UNIQUE,
                channel_username TEXT,
                channel_name TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Referallar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                date TEXT,
                bonus_given INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ Database jadvallari yaratildi")
    
    def load_movies_to_db(self):
        """Boshlang'ich kinolarni DB ga yuklash"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        for code, movie in MOVIES_DB.items():
            cursor.execute("""
                INSERT OR IGNORE INTO movies 
                (movie_code, name, description, category, file_id, vip_only, premium_only, views, rating, added_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                code, movie['name'], movie['description'],
                movie.get('category', 'other'), movie.get('file_id'),
                1 if movie.get('vip_only') else 0,
                1 if movie.get('premium_only') else 0,
                movie.get('views', 0), movie.get('rating', 0),
                movie.get('added_date', datetime.now().strftime('%Y-%m-%d'))
            ))
        
        conn.commit()
        conn.close()
    
    # ─── FOYDALANUVCHI FUNKSIYALARI ───
    
    def register_user(self, user_id: int, username: str, full_name: str, referred_by: int = None) -> bool:
        """Yangi foydalanuvchini ro'yxatdan o'tkazish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Mavjudligini tekshirish
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        if not exists:
            referral_code = f"REF{user_id}{random.randint(100, 999)}"
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, referral_code, referred_by, join_date, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, full_name, referral_code, referred_by, now, now))
            
            conn.commit()
            conn.close()
            return True  # Yangi foydalanuvchi
        else:
            # Faollik vaqtini yangilash
            cursor.execute("""
                UPDATE users SET last_active = ?, username = ?, full_name = ? WHERE user_id = ?
            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username, full_name, user_id))
            conn.commit()
            conn.close()
            return False  # Eski foydalanuvchi
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Foydalanuvchi ma'lumotlarini olish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
    
    def update_user_status(self, user_id: int, status: str) -> bool:
        """Foydalanuvchi statusini o'zgartirish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
        conn.commit()
        conn.close()
        return True
    
    def add_points(self, user_id: int, points: int) -> int:
        """Foydalanuvchiga ball qo'shish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        new_points = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return new_points
    
    def get_all_users(self) -> List[dict]:
        """Barcha foydalanuvchilarni olish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE is_banned = 0")
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    def get_users_count(self) -> Dict:
        """Foydalanuvchilar statistikasi"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'vip'")
        vip = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'premium'")
        premium = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'admin'")
        admins = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
        banned = cursor.fetchone()[0]
        
        conn.close()
        return {"total": total, "vip": vip, "premium": premium, "admins": admins, "banned": banned}
    
    def claim_daily_bonus(self, user_id: int) -> tuple:
        """Kunlik bonus olish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT last_bonus, points FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False, 0
        
        last_bonus = row[0]
        current_points = row[1]
        today = datetime.now().strftime('%Y-%m-%d')
        
        if last_bonus == today:
            conn.close()
            return False, current_points  # Bugun allaqachon olgan
        
        # Bonus berish
        cursor.execute("""
            UPDATE users SET points = points + ?, last_bonus = ? WHERE user_id = ?
        """, (DAILY_BONUS_POINTS, today, user_id))
        
        cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
        new_points = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        return True, new_points
    
    def ban_user(self, user_id: int) -> bool:
        """Foydalanuvchini bloklash"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    
    def unban_user(self, user_id: int) -> bool:
        """Foydalanuvchini blokdan chiqarish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    
    def get_user_by_referral(self, referral_code: str) -> Optional[dict]:
        """Referal kod bo'yicha foydalanuvchi topish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE referral_code = ?", (referral_code,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
    
    # ─── KINO FUNKSIYALARI ───
    
    def get_movie(self, code: str) -> Optional[dict]:
        """Kino kodini qidirish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM movies WHERE movie_code = ? AND is_active = 1", (code,))
        movie = cursor.fetchone()
        if movie:
            # Ko'rishlar sonini oshirish
            cursor.execute("UPDATE movies SET views = views + 1 WHERE movie_code = ?", (code,))
            conn.commit()
        conn.close()
        return dict(movie) if movie else None
    
    def add_movie(self, code: str, name: str, description: str, file_id: str, 
                   file_type: str, category: str, admin_id: int,
                   vip_only: bool = False, premium_only: bool = False) -> bool:
        """Yangi kino qo'shish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        try:
            now = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                INSERT OR REPLACE INTO movies 
                (movie_code, name, description, file_id, file_type, category, vip_only, premium_only, added_by, added_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name, description, file_id, file_type, category,
                  1 if vip_only else 0, 1 if premium_only else 0, admin_id, now))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Kino qo'shishda xatolik: {e}")
            conn.close()
            return False
    
    def delete_movie(self, code: str) -> bool:
        """Kinoni o'chirish (deactivate)"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE movies SET is_active = 0 WHERE movie_code = ?", (code,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    def get_movies_by_category(self, category: str) -> List[dict]:
        """Kategoriya bo'yicha kinolar"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM movies WHERE category = ? AND is_active = 1 ORDER BY views DESC LIMIT 10
        """, (category,))
        movies = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return movies
    
    def get_popular_movies(self, limit: int = 10) -> List[dict]:
        """Eng mashhur kinolar"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM movies WHERE is_active = 1 AND vip_only = 0 AND premium_only = 0
            ORDER BY views DESC LIMIT ?
        """, (limit,))
        movies = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return movies
    
    def get_recent_movies(self, limit: int = 10) -> List[dict]:
        """So'nggi qo'shilgan kinolar"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM movies WHERE is_active = 1
            ORDER BY added_date DESC LIMIT ?
        """, (limit,))
        movies = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return movies
    
    def search_movies(self, query: str) -> List[dict]:
        """Kino qidirish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM movies WHERE is_active = 1 AND 
            (LOWER(name) LIKE LOWER(?) OR movie_code = ?)
            ORDER BY views DESC LIMIT 10
        """, (f"%{query}%", query))
        movies = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return movies
    
    def rate_movie(self, user_id: int, movie_code: str, rating: int) -> bool:
        """Kinoga reyting berish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT OR REPLACE INTO ratings (user_id, movie_code, rating, date)
                VALUES (?, ?, ?, ?)
            """, (user_id, movie_code, rating, now))
            
            # O'rtacha reytingni yangilash
            cursor.execute("""
                SELECT AVG(rating), COUNT(*) FROM ratings WHERE movie_code = ?
            """, (movie_code,))
            avg_rating, count = cursor.fetchone()
            
            cursor.execute("""
                UPDATE movies SET rating = ?, rating_count = ? WHERE movie_code = ?
            """, (round(avg_rating, 1), count, movie_code))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Reyting berishda xatolik: {e}")
            conn.close()
            return False
    
    def get_movies_count(self) -> int:
        """Kinolar soni"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies WHERE is_active = 1")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # ─── SPAM HIMOYA ───
    
    def check_spam(self, user_id: int) -> bool:
        """Spam tekshirish - True = spam, False = ruxsat"""
        conn = self.get_conn()
        cursor = conn.cursor()
        now = datetime.now()
        
        cursor.execute("SELECT request_count, last_reset FROM spam_control WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("""
                INSERT INTO spam_control (user_id, request_count, last_reset) VALUES (?, 1, ?)
            """, (user_id, now.strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            conn.close()
            return False
        
        last_reset = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
        count = row[0]
        
        if (now - last_reset).seconds >= SPAM_TIME:
            # Hisoblagichni tiklash
            cursor.execute("""
                UPDATE spam_control SET request_count = 1, last_reset = ? WHERE user_id = ?
            """, (now.strftime('%Y-%m-%d %H:%M:%S'), user_id))
            conn.commit()
            conn.close()
            return False
        
        if count >= SPAM_LIMIT:
            conn.close()
            return True  # Spam!
        
        cursor.execute("""
            UPDATE spam_control SET request_count = request_count + 1 WHERE user_id = ?
        """, (user_id,))
        conn.commit()
        conn.close()
        return False
    
    # ─── KANALLAR ───
    
    def get_channels(self) -> List[dict]:
        """Faol kanallar ro'yxati"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels WHERE is_active = 1")
        channels = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return channels
    
    def add_channel(self, channel_id: int, username: str, name: str) -> bool:
        """Kanal qo'shish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO channels (channel_id, channel_username, channel_name)
                VALUES (?, ?, ?)
            """, (channel_id, username, name))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False
    
    def remove_channel(self, channel_id: int) -> bool:
        """Kanalni o'chirish"""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE channels SET is_active = 0 WHERE channel_id = ?", (channel_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0


# ═══════════════════════════════════════════════════════
#                  📋 FSM HOLATLARI
# ═══════════════════════════════════════════════════════

class AdminStates(StatesGroup):
    """Admin panel holatlari"""
    waiting_movie_code = State()
    waiting_movie_name = State()
    waiting_movie_desc = State()
    waiting_movie_file = State()
    waiting_movie_category = State()
    waiting_delete_code = State()
    waiting_broadcast = State()
    waiting_give_status = State()
    waiting_give_user_id = State()
    waiting_ban_id = State()
    waiting_channel_add = State()

class UserStates(StatesGroup):
    """Foydalanuvchi holatlari"""
    searching = State()
    rating_movie = State()


# ═══════════════════════════════════════════════════════
#                  🎹 KLAVIATURA FUNKSIYALARI
# ═══════════════════════════════════════════════════════

def main_menu_keyboard(status: str = 'user') -> ReplyKeyboardMarkup:
    """Asosiy menyu klaviaturasi"""
    buttons = [
        [KeyboardButton(text="🎬 Kino qidirish"), KeyboardButton(text="🔍 Qidiruv")],
        [KeyboardButton(text="🏆 Mashhur kinolar"), KeyboardButton(text="🆕 Yangi kinolar")],
        [KeyboardButton(text="📂 Kategoriyalar"), KeyboardButton(text="👤 Profilim")],
        [KeyboardButton(text="🎁 Kunlik bonus"), KeyboardButton(text="👥 Referal")],
    ]
    
    if status in ['vip', 'premium']:
        buttons.append([KeyboardButton(text="💎 VIP Kinolar"), KeyboardButton(text="⭐ Reyting berish")])
    
    if status in ['admin'] or True:  # Admin doim ko'radi
        pass
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Admin panel klaviaturasi"""
    buttons = [
        [KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="❌ Kino o'chirish")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Foydalanuvchilar")],
        [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="💎 Status berish")],
        [KeyboardButton(text="🔒 Ban/Unban"), KeyboardButton(text="📺 Kanal sozlash")],
        [KeyboardButton(text="🔙 Asosiy menyu")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def subscription_keyboard(channels: List[dict]) -> InlineKeyboardMarkup:
    """Obuna tekshirish tugmalari"""
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(
            text=f"📢 {ch.get('channel_name', ch.get('name', 'Kanal'))}ga obuna bo'ling",
            url=f"https://t.me/{ch.get('channel_username', ch.get('username', '')).replace('@', '')}"
        )])
    
    # Agar DB kanallar bo'sh bo'lsa, config dan olish
    if not channels:
        for ch in REQUIRED_CHANNELS:
            buttons.append([InlineKeyboardButton(
                text=f"📢 {ch['name']}ga obuna bo'ling",
                url=f"https://t.me/{ch['username'].replace('@', '')}"
            )])
    
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def categories_keyboard() -> InlineKeyboardMarkup:
    """Kategoriyalar klaviaturasi"""
    buttons = [
        [
            InlineKeyboardButton(text="🎬 Action", callback_data="cat_action"),
            InlineKeyboardButton(text="😂 Komediya", callback_data="cat_comedy"),
        ],
        [
            InlineKeyboardButton(text="😱 Triller", callback_data="cat_thriller"),
            InlineKeyboardButton(text="❤️ Romantik", callback_data="cat_romance"),
        ],
        [
            InlineKeyboardButton(text="🚀 Fantastika", callback_data="cat_scifi"),
            InlineKeyboardButton(text="👻 Dahshat", callback_data="cat_horror"),
        ],
        [
            InlineKeyboardButton(text="🎭 Drama", callback_data="cat_drama"),
            InlineKeyboardButton(text="🌍 Boshqalar", callback_data="cat_other"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def movie_actions_keyboard(movie_code: str) -> InlineKeyboardMarkup:
    """Kino amallar tugmalari"""
    buttons = [
        [
            InlineKeyboardButton(text="⭐ 5", callback_data=f"rate_{movie_code}_5"),
            InlineKeyboardButton(text="⭐ 4", callback_data=f"rate_{movie_code}_4"),
            InlineKeyboardButton(text="⭐ 3", callback_data=f"rate_{movie_code}_3"),
        ],
        [InlineKeyboardButton(text="📤 Do'stlarga ulashish", callback_data=f"share_{movie_code}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def status_keyboard() -> InlineKeyboardMarkup:
    """Status tanlash klaviaturasi"""
    buttons = [
        [
            InlineKeyboardButton(text="👤 Oddiy", callback_data="set_status_user"),
            InlineKeyboardButton(text="💎 VIP", callback_data="set_status_vip"),
        ],
        [
            InlineKeyboardButton(text="👑 Premium", callback_data="set_status_premium"),
            InlineKeyboardButton(text="🔧 Admin", callback_data="set_status_admin"),
        ],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def profile_keyboard(referral_code: str) -> InlineKeyboardMarkup:
    """Profil tugmalari"""
    buttons = [
        [InlineKeyboardButton(text="🎁 Bonus ol", callback_data="daily_bonus")],
        [InlineKeyboardButton(text="👥 Referal havolam", callback_data=f"referral_{referral_code}")],
        [InlineKeyboardButton(text="📊 Statistikam", callback_data="my_stats")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ═══════════════════════════════════════════════════════
#                  🤖 BOT OBYEKTI VA DISPATCHER
# ═══════════════════════════════════════════════════════

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())
db = Database()
router = Router()


# ═══════════════════════════════════════════════════════
#                  🛡️ YORDAMCHI FUNKSIYALAR
# ═══════════════════════════════════════════════════════

async def check_subscription(user_id: int) -> bool:
    """Foydalanuvchi kanalga obuna bo'lganini tekshirish"""
    # DB dan kanallar olish
    db_channels = db.get_channels()
    channels_to_check = db_channels if db_channels else REQUIRED_CHANNELS
    
    for channel in channels_to_check:
        try:
            channel_id = channel.get('channel_id') or channel.get('id')
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in ['left', 'kicked', 'banned']:
                return False
        except Exception as e:
            logger.warning(f"Kanal tekshirishda xatolik ({channel_id}): {e}")
            # Agar kanal ID noto'g'ri bo'lsa, o'tkazib yuborish
            continue
    
    return True

def is_admin(user_id: int) -> bool:
    """Admin ekanligini tekshirish"""
    if user_id in ADMIN_IDS:
        return True
    user = db.get_user(user_id)
    return user and user.get('status') == 'admin'

def get_status_emoji(status: str) -> str:
    """Status emoji"""
    emojis = {
        'user': '👤',
        'vip': '💎',
        'premium': '👑',
        'admin': '🔧'
    }
    return emojis.get(status, '👤')

def get_status_text(status: str) -> str:
    """Status matnini olish"""
    texts = {
        'user': 'Oddiy foydalanuvchi',
        'vip': 'VIP foydalanuvchi',
        'premium': 'PREMIUM foydalanuvchi',
        'admin': 'Administrator'
    }
    return texts.get(status, 'Oddiy foydalanuvchi')

def get_stars(rating: float) -> str:
    """Reytingni yulduzlarga aylantirish"""
    full = int(rating)
    half = 1 if (rating - full) >= 0.5 else 0
    empty = 5 - full - half
    return '⭐' * full + '✨' * half + '☆' * empty


# ═══════════════════════════════════════════════════════
#                  📱 ASOSIY HANDLERLAR
# ═══════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    /start komandasi - Botni boshlash
    Referal tizimi bilan ishlaydi
    """
    await state.clear()
    user = message.from_user
    
    # Referal tekshirish
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        if ref_code.startswith('ref_'):
            ref_user = db.get_user_by_referral(ref_code.replace('ref_', 'REF', 1))
            if ref_user and ref_user['user_id'] != user.id:
                referred_by = ref_user['user_id']
    
    # Ro'yxatdan o'tkazish
    is_new = db.register_user(
        user_id=user.id,
        username=user.username or '',
        full_name=user.full_name,
        referred_by=referred_by
    )
    
    # Referal bonus
    if is_new and referred_by:
        db.add_points(referred_by, 20)
        db.add_points(user.id, 10)
        try:
            await bot.send_message(
                referred_by,
                f"🎉 <b>Referal bonus!</b>\n\n"
                f"Siz taklif qilgan <b>{user.full_name}</b> botga qo'shildi!\n"
                f"Sizga <b>+20 ball</b> qo'shildi! 🎁"
            )
        except:
            pass
    
    # Obuna tekshirish
    is_subscribed = await check_subscription(user.id)
    
    if not is_subscribed:
        await send_subscription_message(message)
        return
    
    # Xush kelibsiz xabar
    db_user = db.get_user(user.id)
    status = db_user.get('status', 'user') if db_user else 'user'
    
    welcome_text = (
        f"🎬 <b>KODLI KINO BOT</b>ga xush kelibsiz!\n\n"
        f"{'🌟 Siz yangi foydalanuvchisiz!' if is_new else '👋 Qaytib keldingiz!'}\n\n"
        f"<b>Ism:</b> {user.full_name}\n"
        f"<b>Status:</b> {get_status_emoji(status)} {get_status_text(status)}\n\n"
        f"📌 <b>Qanday ishlaydi?</b>\n"
        f"▶️ Kino kodini yozing (masalan: <code>101</code>)\n"
        f"▶️ Bot shu kinoni sizga yuboradi!\n\n"
        f"💡 <i>Barcha funksiyalar pastdagi menyuda</i>"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=main_menu_keyboard(status)
    )
    
    logger.info(f"{'Yangi' if is_new else 'Qaytgan'} foydalanuvchi: {user.id} - {user.full_name}")

async def send_subscription_message(message: Message):
    """Obuna xabarini yuborish"""
    db_channels = db.get_channels()
    channels = db_channels if db_channels else REQUIRED_CHANNELS
    
    text = (
        "🔒 <b>Botdan foydalanish uchun avval kanalga obuna bo'ling!</b>\n\n"
        "📢 Quyidagi kanallarga obuna bo'ling:\n\n"
    )
    
    for ch in channels:
        name = ch.get('channel_name') or ch.get('name', 'Kanal')
        username = ch.get('channel_username') or ch.get('username', '')
        text += f"✅ {name} - {username}\n"
    
    text += "\n<i>Obuna bo'lgandan so'ng ✅ Tekshirish tugmasini bosing</i>"
    
    await message.answer(text, reply_markup=subscription_keyboard(channels))

@router.callback_query(F.data == "check_subscription")
async def check_sub_callback(callback: CallbackQuery):
    """Obunani tekshirish tugmasi"""
    user = callback.from_user
    is_subscribed = await check_subscription(user.id)
    
    if is_subscribed:
        db_user = db.get_user(user.id)
        status = db_user.get('status', 'user') if db_user else 'user'
        
        await callback.message.edit_text(
            "✅ <b>Obuna tasdiqlandi!</b>\n\n"
            "Endi botdan to'liq foydalanishingiz mumkin.\n"
            "Kino kodini yozing yoki pastdagi menyudan tanlang! 🎬"
        )
        await callback.message.answer(
            "🎬 <b>KODLI KINO BOT</b>\n\nMenyudan foydalaning yoki kino kodini kiriting:",
            reply_markup=main_menu_keyboard(status)
        )
    else:
        await callback.answer(
            "❌ Hali ham barcha kanallarga obuna bo'lmadingiz!",
            show_alert=True
        )


# ═══════════════════════════════════════════════════════
#                  🎬 KINO FUNKSIYALARI
# ═══════════════════════════════════════════════════════

async def send_movie(message: Message, movie_code: str):
    """Kinoni foydalanuvchiga yuborish"""
    user_id = message.from_user.id
    
    # Spam tekshirish
    if db.check_spam(user_id):
        await message.answer(
            "⏱️ <b>Sekinroq!</b>\n\n"
            "Juda ko'p so'rov yubordingiz.\n"
            f"{SPAM_TIME} soniya kutib turing."
        )
        return
    
    # Obuna tekshirish
    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        await send_subscription_message(message)
        return
    
    # Kinoni topish
    movie = db.get_movie(movie_code)
    
    if not movie:
        await message.answer(
            f"❌ <b>{movie_code}</b> kodli kino topilmadi!\n\n"
            "🔍 Qidiruv uchun to'g'ri kino kodini kiriting\n"
            "💡 Mashhur kinolar: /popular"
        )
        return
    
    # Status tekshirish
    db_user = db.get_user(user_id)
    user_status = db_user.get('status', 'user') if db_user else 'user'
    
    if movie['premium_only'] and user_status not in ['premium', 'admin'] and not is_admin(user_id):
        await message.answer(
            "👑 <b>Bu kino PREMIUM foydalanuvchilar uchun!</b>\n\n"
            "Premium status olish uchun adminga murojaat qiling:\n"
            "💰 Narxi: 200 ball\n\n"
            f"Sizning ballingiz: {db_user.get('points', 0)} 💠"
        )
        return
    
    if movie['vip_only'] and user_status not in ['vip', 'premium', 'admin'] and not is_admin(user_id):
        await message.answer(
            "💎 <b>Bu kino VIP foydalanuvchilar uchun!</b>\n\n"
            "VIP status olish uchun adminga murojaat qiling:\n"
            "💰 Narxi: 100 ball\n\n"
            f"Sizning ballingiz: {db_user.get('points', 0)} 💠"
        )
        return
    
    # Kino ma'lumotlari
    category_names = {
        'action': '🎬 Action', 'comedy': '😂 Komediya',
        'thriller': '😱 Triller', 'romance': '❤️ Romantik',
        'scifi': '🚀 Fantastika', 'horror': '👻 Dahshat',
        'drama': '🎭 Drama', 'other': '🌍 Boshqa'
    }
    
    vip_badge = ""
    if movie['premium_only']:
        vip_badge = "👑 PREMIUM | "
    elif movie['vip_only']:
        vip_badge = "💎 VIP | "
    
    caption = (
        f"🎬 <b>{movie['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Tavsif:</b> {movie['description']}\n\n"
        f"🏷️ <b>Kategoriya:</b> {category_names.get(movie['category'], '🌍 Boshqa')}\n"
        f"⭐ <b>Reyting:</b> {get_stars(movie['rating'])} ({movie['rating']}/5)\n"
        f"👁️ <b>Ko'rishlar:</b> {movie['views']:,}\n"
        f"🔢 <b>Kod:</b> <code>{movie['movie_code']}</code>\n"
        f"{vip_badge}━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⭐ Reytingni qo'ying:"
    )
    
    # Reklama (faqat oddiy foydalanuvchilar uchun)
    if user_status == 'user':
        ad_text = "\n\n📢 <i>Reklamasiz foydalanish uchun VIP bo'ling!</i>"
        caption += ad_text
    
    # Kino yuborish
    if movie.get('file_id'):
        try:
            file_type = movie.get('file_type', 'video')
            if file_type == 'video':
                await message.answer_video(
                    video=movie['file_id'],
                    caption=caption,
                    reply_markup=movie_actions_keyboard(movie_code)
                )
            elif file_type == 'document':
                await message.answer_document(
                    document=movie['file_id'],
                    caption=caption,
                    reply_markup=movie_actions_keyboard(movie_code)
                )
            elif file_type == 'photo':
                await message.answer_photo(
                    photo=movie['file_id'],
                    caption=caption,
                    reply_markup=movie_actions_keyboard(movie_code)
                )
            else:
                await message.answer_video(
                    video=movie['file_id'],
                    caption=caption,
                    reply_markup=movie_actions_keyboard(movie_code)
                )
        except Exception as e:
            logger.error(f"Kino yuborishda xatolik: {e}")
            await message.answer(
                caption + f"\n\n⚠️ <i>Kino faylini yuborishda xatolik. Admin bilan bog'laning.</i>",
                reply_markup=movie_actions_keyboard(movie_code)
            )
    else:
        # File ID yo'q - demo rejim
        await message.answer(
            f"{caption}\n\n"
            f"⚠️ <i>Bu kino hali yuklanmagan. Admin tez orada qo'shadi.</i>",
            reply_markup=movie_actions_keyboard(movie_code)
        )
    
    # Ko'rishlar statistikasi
    if db_user:
        conn = sqlite3.connect('kinobaz.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET total_movies_watched = total_movies_watched + 1 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()
    
    logger.info(f"Kino yuborildi: {movie_code} → {user_id}")

@router.callback_query(F.data.startswith("rate_"))
async def rate_movie_callback(callback: CallbackQuery):
    """Kino reytingi berish"""
    parts = callback.data.split("_")
    movie_code = parts[1]
    rating = int(parts[2])
    
    success = db.rate_movie(callback.from_user.id, movie_code, rating)
    
    if success:
        stars = "⭐" * rating
        await callback.answer(f"✅ {stars} Reyting qo'yildi!", show_alert=False)
        db.add_points(callback.from_user.id, 2)
    else:
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("share_"))
async def share_movie_callback(callback: CallbackQuery):
    """Kinoni ulashish"""
    movie_code = callback.data.split("_")[1]
    bot_info = await bot.get_me()
    share_link = f"https://t.me/{bot_info.username}?start={movie_code}"
    
    await callback.answer(
        f"🔗 Ulashish havolasi:\n{share_link}",
        show_alert=True
    )


# ═══════════════════════════════════════════════════════
#                  📱 MENYU HANDLERLAR
# ═══════════════════════════════════════════════════════

@router.message(F.text == "🎬 Kino qidirish")
async def movie_search_btn(message: Message):
    """Kino qidirish tugmasi"""
    await message.answer(
        "🎬 <b>Kino kodini kiriting</b>\n\n"
        "Masalan: <code>101</code>, <code>202</code>, <code>303</code>\n\n"
        "💡 <i>Kino kodi odatda 3-6 raqamdan iborat</i>"
    )

@router.message(F.text == "🔍 Qidiruv")
async def search_btn(message: Message, state: FSMContext):
    """Qidiruv tugmasi"""
    await state.set_state(UserStates.searching)
    await message.answer(
        "🔍 <b>Kino nomini kiriting</b>\n\n"
        "Izlash uchun kino nomini yoki bir qismini kiriting:\n"
        "<i>Masalan: Avengers, Batman, Spider...</i>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
            resize_keyboard=True
        )
    )

@router.message(UserStates.searching)
async def process_search(message: Message, state: FSMContext):
    """Qidiruv natijasini ko'rsatish"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        db_user = db.get_user(message.from_user.id)
        status = db_user.get('status', 'user') if db_user else 'user'
        await message.answer("❌ Qidiruv bekor qilindi", reply_markup=main_menu_keyboard(status))
        return
    
    query = message.text.strip()
    movies = db.search_movies(query)
    
    await state.clear()
    db_user = db.get_user(message.from_user.id)
    status = db_user.get('status', 'user') if db_user else 'user'
    
    if not movies:
        await message.answer(
            f"❌ <b>'{query}'</b> bo'yicha hech narsa topilmadi\n\n"
            "🔍 Boshqa nom bilan urinib ko'ring",
            reply_markup=main_menu_keyboard(status)
        )
        return
    
    result = f"🔍 <b>'{query}'</b> bo'yicha natijalar:\n\n"
    for i, movie in enumerate(movies[:10], 1):
        vip_badge = "💎 " if movie['vip_only'] else ""
        premium_badge = "👑 " if movie['premium_only'] else ""
        result += (
            f"{i}. {premium_badge}{vip_badge}<b>{movie['name']}</b>\n"
            f"   🔢 Kod: <code>{movie['movie_code']}</code> | "
            f"⭐ {movie['rating']} | 👁️ {movie['views']}\n\n"
        )
    
    result += "💡 <i>Kino kodini yozing va kinoni oling!</i>"
    
    await message.answer(result, reply_markup=main_menu_keyboard(status))

@router.message(F.text == "🏆 Mashhur kinolar")
async def popular_movies_btn(message: Message):
    """Eng mashhur kinolar"""
    movies = db.get_popular_movies(10)
    
    if not movies:
        await message.answer("📭 Hozircha kinolar mavjud emas")
        return
    
    text = "🏆 <b>ENG MASHHUR KINOLAR</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, movie in enumerate(movies, 1):
        text += (
            f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'{i}.'}"
            f" <b>{movie['name']}</b>\n"
            f"   🔢 <code>{movie['movie_code']}</code> | "
            f"⭐ {movie['rating']} | 👁️ {movie['views']:,}\n\n"
        )
    
    await message.answer(text)

@router.message(F.text == "🆕 Yangi kinolar")
async def recent_movies_btn(message: Message):
    """So'nggi qo'shilgan kinolar"""
    movies = db.get_recent_movies(10)
    
    if not movies:
        await message.answer("📭 Hozircha kinolar mavjud emas")
        return
    
    text = "🆕 <b>YANGI QO'SHILGAN KINOLAR</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, movie in enumerate(movies, 1):
        vip_badge = "💎 " if movie['vip_only'] else ""
        premium_badge = "👑 " if movie['premium_only'] else ""
        text += (
            f"{i}. {premium_badge}{vip_badge}<b>{movie['name']}</b>\n"
            f"   🔢 <code>{movie['movie_code']}</code> | "
            f"📅 {movie['added_date']}\n\n"
        )
    
    await message.answer(text)

@router.message(F.text == "📂 Kategoriyalar")
async def categories_btn(message: Message):
    """Kategoriyalar menyusi"""
    await message.answer(
        "📂 <b>KINO KATEGORIYALARI</b>\n\n"
        "Qiziqtiradigan kategoriyani tanlang:",
        reply_markup=categories_keyboard()
    )

@router.callback_query(F.data.startswith("cat_"))
async def category_callback(callback: CallbackQuery):
    """Kategoriya kinolarini ko'rsatish"""
    category = callback.data.replace("cat_", "")
    
    category_names = {
        'action': '🎬 Action', 'comedy': '😂 Komediya',
        'thriller': '😱 Triller', 'romance': '❤️ Romantik',
        'scifi': '🚀 Fantastika', 'horror': '👻 Dahshat',
        'drama': '🎭 Drama', 'other': '🌍 Boshqa'
    }
    
    movies = db.get_movies_by_category(category)
    cat_name = category_names.get(category, category)
    
    if not movies:
        await callback.message.edit_text(
            f"📭 {cat_name} kategoriyasida hozircha kinolar yo'q"
        )
        return
    
    text = f"{cat_name} <b>KINOLARI</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, movie in enumerate(movies, 1):
        vip_badge = "💎 " if movie['vip_only'] else ""
        text += (
            f"{i}. {vip_badge}<b>{movie['name']}</b>\n"
            f"   🔢 <code>{movie['movie_code']}</code> | "
            f"⭐ {movie['rating']} | 👁️ {movie['views']}\n\n"
        )
    
    text += "💡 <i>Kino kodini yozing va kinoni oling!</i>"
    await callback.message.edit_text(text)

@router.message(F.text == "💎 VIP Kinolar")
async def vip_movies_btn(message: Message):
    """VIP kinolar ro'yxati"""
    db_user = db.get_user(message.from_user.id)
    status = db_user.get('status', 'user') if db_user else 'user'
    
    if status not in ['vip', 'premium', 'admin'] and not is_admin(message.from_user.id):
        await message.answer(
            "💎 <b>Bu bo'lim faqat VIP va PREMIUM foydalanuvchilar uchun!</b>\n\n"
            "VIP bo'lish uchun adminga murojaat qiling."
        )
        return
    
    conn = sqlite3.connect('kinobaz.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM movies WHERE (vip_only = 1 OR premium_only = 1) AND is_active = 1")
    movies = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
    conn.close()
    
    if not movies:
        await message.answer("📭 Maxsus kinolar hali qo'shilmagan")
        return
    
    text = "💎 <b>VIP VA PREMIUM KINOLAR</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, movie in enumerate(movies, 1):
        badge = "👑 PREMIUM" if movie['premium_only'] else "💎 VIP"
        text += (
            f"{i}. [{badge}] <b>{movie['name']}</b>\n"
            f"   🔢 <code>{movie['movie_code']}</code> | ⭐ {movie['rating']}\n\n"
        )
    
    await message.answer(text)


# ═══════════════════════════════════════════════════════
#                  👤 PROFIL VA BONUS
# ═══════════════════════════════════════════════════════

@router.message(F.text == "👤 Profilim")
async def profile_btn(message: Message):
    """Foydalanuvchi profili"""
    db_user = db.get_user(message.from_user.id)
    
    if not db_user:
        await message.answer("❌ Profil topilmadi. /start ni bosing")
        return
    
    status = db_user.get('status', 'user')
    status_emoji = get_status_emoji(status)
    status_text = get_status_text(status)
    
    # Referallar soni
    conn = sqlite3.connect('kinobaz.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (message.from_user.id,))
    referral_count = cursor.fetchone()[0]
    conn.close()
    
    profile_text = (
        f"👤 <b>SIZNING PROFILINGIZ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"📛 <b>Ism:</b> {message.from_user.full_name}\n"
        f"👤 <b>Username:</b> @{message.from_user.username or 'Yo\'q'}\n\n"
        f"{status_emoji} <b>Status:</b> {status_text}\n"
        f"💠 <b>Ballar:</b> {db_user.get('points', 0)}\n"
        f"🎬 <b>Ko'rilgan kinolar:</b> {db_user.get('total_movies_watched', 0)}\n\n"
        f"👥 <b>Referallar:</b> {referral_count} kishi\n"
        f"📅 <b>Qo'shilgan:</b> {db_user.get('join_date', 'Noma\'lum')[:10]}\n\n"
        f"🎁 <b>Kunlik bonus:</b> {DAILY_BONUS_POINTS} ball\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    await message.answer(
        profile_text,
        reply_markup=profile_keyboard(db_user.get('referral_code', ''))
    )

@router.message(F.text == "🎁 Kunlik bonus")
@router.callback_query(F.data == "daily_bonus")
async def daily_bonus(event):
    """Kunlik bonus olish"""
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        answer_method = event.message.answer
        answer_alert = lambda text: event.answer(text, show_alert=True)
    else:
        user_id = event.from_user.id
        answer_method = event.answer
        answer_alert = None
    
    success, points = db.claim_daily_bonus(user_id)
    
    if success:
        text = (
            f"🎁 <b>Kunlik bonus olindi!</b>\n\n"
            f"✅ <b>+{DAILY_BONUS_POINTS} ball</b> qo'shildi!\n"
            f"💠 <b>Jami ballar:</b> {points}\n\n"
            f"🕐 <i>Ertaga yana keling!</i>"
        )
    else:
        text = (
            f"⏰ <b>Bugun bonusni allaqachon oldingiz!</b>\n\n"
            f"💠 <b>Ballaringiz:</b> {points}\n"
            f"🕐 <i>Ertaga yana keling!</i>"
        )
    
    if isinstance(event, CallbackQuery):
        await event.answer(
            "✅ Bonus olindi!" if success else "⏰ Bugun allaqachon oldingiz!",
            show_alert=True
        )
        await event.message.answer(text)
    else:
        await event.answer(text)

@router.message(F.text == "👥 Referal")
@router.callback_query(F.data.startswith("referral_"))
async def referral_info(event):
    """Referal ma'lumotlari"""
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        db_user = db.get_user(user_id)
        ref_code = event.data.split("_", 1)[1] if len(event.data.split("_")) > 1 else db_user.get('referral_code', '')
    else:
        user_id = event.from_user.id
        db_user = db.get_user(user_id)
        ref_code = db_user.get('referral_code', '') if db_user else ''
    
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{ref_code.lower()}"
    
    # Referallar soni
    conn = sqlite3.connect('kinobaz.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
    referral_count = cursor.fetchone()[0]
    conn.close()
    
    text = (
        f"👥 <b>REFERAL TIZIMI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📨 Do'stlaringizni taklif qiling va ball yig'ing!\n\n"
        f"🎁 <b>Siz olasiz:</b> +20 ball\n"
        f"🎁 <b>Do'stingiz oladi:</b> +10 ball\n\n"
        f"🔗 <b>Sizning havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 <b>Taklif qilganlar:</b> {referral_count} kishi\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text)
    else:
        await event.answer(text)


# ═══════════════════════════════════════════════════════
#                  👑 ADMIN PANEL
# ═══════════════════════════════════════════════════════

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Admin panel kirish"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Sizda admin huquqi yo'q!")
        return
    
    users_count = db.get_users_count()
    movies_count = db.get_movies_count()
    
    text = (
        f"👑 <b>ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>Umumiy statistika:</b>\n"
        f"👥 Foydalanuvchilar: {users_count['total']}\n"
        f"💎 VIP: {users_count['vip']}\n"
        f"👑 Premium: {users_count['premium']}\n"
        f"🎬 Kinolar: {movies_count}\n\n"
        f"🔧 <i>Admin menyusidan foydalaning:</i>"
    )
    
    await message.answer(text, reply_markup=admin_menu_keyboard())

@router.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    """Admin statistikasi"""
    if not is_admin(message.from_user.id):
        return
    
    users = db.get_users_count()
    movies_count = db.get_movies_count()
    
    # So'nggi 24 soat faol
    conn = sqlite3.connect('kinobaz.db')
    cursor = conn.cursor()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_active > ?", (yesterday,))
    active_today = cursor.fetchone()[0]
    
    # Umumiy ko'rishlar
    cursor.execute("SELECT SUM(views) FROM movies WHERE is_active = 1")
    total_views = cursor.fetchone()[0] or 0
    conn.close()
    
    text = (
        f"📊 <b>TO'LIQ STATISTIKA</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f"   ├ Jami: {users['total']}\n"
        f"   ├ Bugun faol: {active_today}\n"
        f"   ├ VIP: {users['vip']}\n"
        f"   ├ Premium: {users['premium']}\n"
        f"   ├ Adminlar: {users['admins']}\n"
        f"   └ Bloklangan: {users['banned']}\n\n"
        f"🎬 <b>Kinolar:</b>\n"
        f"   ├ Jami: {movies_count}\n"
        f"   └ Jami ko'rishlar: {total_views:,}\n\n"
        f"📅 <b>Sana:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    await message.answer(text)

@router.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: Message):
    """Foydalanuvchilar ro'yxati (admin)"""
    if not is_admin(message.from_user.id):
        return
    
    users = db.get_users_count()
    await message.answer(
        f"👥 <b>FOYDALANUVCHILAR</b>\n\n"
        f"Jami: {users['total']}\n"
        f"VIP: {users['vip']}\n"
        f"Premium: {users['premium']}\n\n"
        f"ID bo'yicha qidirish: /getuser [ID]"
    )

@router.message(Command("getuser"))
async def get_user_info(message: Message):
    """Foydalanuvchi ma'lumotlarini ko'rish"""
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Foydalanuvchi ID kiriting: /getuser 123456789")
        return
    
    try:
        user_id = int(parts[1])
        user = db.get_user(user_id)
        
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi")
            return
        
        status_emoji = get_status_emoji(user['status'])
        text = (
            f"👤 <b>Foydalanuvchi ma'lumotlari</b>\n\n"
            f"🆔 ID: <code>{user['user_id']}</code>\n"
            f"📛 Ism: {user['full_name']}\n"
            f"👤 Username: @{user.get('username', 'Yo\'q')}\n"
            f"{status_emoji} Status: {get_status_text(user['status'])}\n"
            f"💠 Ballar: {user.get('points', 0)}\n"
            f"🎬 Ko'rgan kinolari: {user.get('total_movies_watched', 0)}\n"
            f"📅 Qo'shilgan: {user.get('join_date', 'Noma\'lum')[:10]}\n"
            f"🚫 Bloklangan: {'Ha' if user.get('is_banned') else 'Yo\'q'}"
        )
        await message.answer(text)
    except ValueError:
        await message.answer("❌ Noto'g'ri ID format")

# ─── KINO QO'SHISH ───

@router.message(F.text == "➕ Kino qo'shish")
async def add_movie_start(message: Message, state: FSMContext):
    """Kino qo'shish jarayoni boshlash"""
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_movie_code)
    await message.answer(
        "➕ <b>YANGI KINO QO'SHISH</b>\n\n"
        "1️⃣ Kino kodini kiriting (masalan: 101, 505):\n"
        "<i>Bekor qilish: /cancel</i>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor")]],
            resize_keyboard=True
        )
    )

@router.message(AdminStates.waiting_movie_code)
async def add_movie_code(message: Message, state: FSMContext):
    """Kino kodi"""
    if message.text == "❌ Bekor":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_menu_keyboard())
        return
    
    await state.update_data(code=message.text.strip())
    await state.set_state(AdminStates.waiting_movie_name)
    await message.answer("2️⃣ Kino nomini kiriting:")

@router.message(AdminStates.waiting_movie_name)
async def add_movie_name(message: Message, state: FSMContext):
    """Kino nomi"""
    if message.text == "❌ Bekor":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_menu_keyboard())
        return
    
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminStates.waiting_movie_desc)
    await message.answer("3️⃣ Kino tavsifini kiriting:")

@router.message(AdminStates.waiting_movie_desc)
async def add_movie_desc(message: Message, state: FSMContext):
    """Kino tavsifi"""
    if message.text == "❌ Bekor":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_menu_keyboard())
        return
    
    await state.update_data(description=message.text.strip())
    await state.set_state(AdminStates.waiting_movie_category)
    
    cat_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Action", callback_data="addcat_action"),
            InlineKeyboardButton(text="😂 Komediya", callback_data="addcat_comedy"),
        ],
        [
            InlineKeyboardButton(text="😱 Triller", callback_data="addcat_thriller"),
            InlineKeyboardButton(text="❤️ Romantik", callback_data="addcat_romance"),
        ],
        [
            InlineKeyboardButton(text="🚀 Fantastika", callback_data="addcat_scifi"),
            InlineKeyboardButton(text="👻 Dahshat", callback_data="addcat_horror"),
        ],
        [
            InlineKeyboardButton(text="🎭 Drama", callback_data="addcat_drama"),
            InlineKeyboardButton(text="🌍 Boshqa", callback_data="addcat_other"),
        ],
    ])
    
    await message.answer("4️⃣ Kategoriyani tanlang:", reply_markup=cat_kb)

@router.callback_query(F.data.startswith("addcat_"))
async def add_movie_category(callback: CallbackQuery, state: FSMContext):
    """Kino kategoriyasi"""
    category = callback.data.replace("addcat_", "")
    await state.update_data(category=category)
    await state.set_state(AdminStates.waiting_movie_file)
    await callback.message.edit_text(
        "5️⃣ Kino faylini yuboring (video, document yoki photo):\n\n"
        "<i>Agar hozir fayl bo'lmasa, /skip yozing</i>"
    )

@router.message(AdminStates.waiting_movie_file, F.text == "/skip")
async def add_movie_skip_file(message: Message, state: FSMContext):
    """Fayl o'tkazib yuborish"""
    data = await state.get_data()
    success = db.add_movie(
        code=data['code'],
        name=data['name'],
        description=data['description'],
        file_id=None,
        file_type='video',
        category=data['category'],
        admin_id=message.from_user.id
    )
    await state.clear()
    
    if success:
        await message.answer(
            f"✅ <b>Kino qo'shildi!</b>\n\n"
            f"🔢 Kod: <code>{data['code']}</code>\n"
            f"📛 Nom: {data['name']}\n"
            f"⚠️ Kino fayli keyinroq qo'shiladi",
            reply_markup=admin_menu_keyboard()
        )
    else:
        await message.answer("❌ Xatolik yuz berdi", reply_markup=admin_menu_keyboard())

@router.message(AdminStates.waiting_movie_file, F.video | F.document | F.photo)
async def add_movie_file(message: Message, state: FSMContext):
    """Kino faylini saqlash"""
    data = await state.get_data()
    
    if message.video:
        file_id = message.video.file_id
        file_type = 'video'
    elif message.document:
        file_id = message.document.file_id
        file_type = 'document'
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'
    else:
        await message.answer("❌ Noto'g'ri fayl turi")
        return
    
    # VIP/Premium tanlash
    vip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Oddiy", callback_data="addvip_normal"),
            InlineKeyboardButton(text="💎 VIP", callback_data="addvip_vip"),
            InlineKeyboardButton(text="👑 Premium", callback_data="addvip_premium"),
        ]
    ])
    
    await state.update_data(file_id=file_id, file_type=file_type)
    await message.answer("6️⃣ Bu kino kim uchun?", reply_markup=vip_kb)

@router.callback_query(F.data.startswith("addvip_"))
async def add_movie_vip_choice(callback: CallbackQuery, state: FSMContext):
    """VIP tanlash"""
    choice = callback.data.replace("addvip_", "")
    data = await state.get_data()
    
    vip_only = choice == 'vip'
    premium_only = choice == 'premium'
    
    success = db.add_movie(
        code=data['code'],
        name=data['name'],
        description=data['description'],
        file_id=data.get('file_id'),
        file_type=data.get('file_type', 'video'),
        category=data['category'],
        admin_id=callback.from_user.id,
        vip_only=vip_only,
        premium_only=premium_only
    )
    
    await state.clear()
    
    badge = "👑 Premium" if premium_only else "💎 VIP" if vip_only else "👤 Oddiy"
    
    if success:
        await callback.message.edit_text(
            f"✅ <b>Kino muvaffaqiyatli qo'shildi!</b>\n\n"
            f"🔢 Kod: <code>{data['code']}</code>\n"
            f"📛 Nom: {data['name']}\n"
            f"🏷️ Kategoriya: {data['category']}\n"
            f"🔑 Kirish: {badge}"
        )
        await callback.message.answer("✅ Tayyor!", reply_markup=admin_menu_keyboard())
    else:
        await callback.message.edit_text("❌ Xatolik yuz berdi. Bu kod allaqachon mavjud bo'lishi mumkin.")
        await callback.message.answer("Admin menyusi:", reply_markup=admin_menu_keyboard())

# ─── KINO O'CHIRISH ───

@router.message(F.text == "❌ Kino o'chirish")
async def delete_movie_start(message: Message, state: FSMContext):
    """Kino o'chirish"""
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_delete_code)
    await message.answer(
        "❌ <b>KINO O'CHIRISH</b>\n\n"
        "O'chirmoqchi bo'lgan kino kodini kiriting:\n"
        "<i>Bekor qilish: /cancel</i>"
    )

@router.message(AdminStates.waiting_delete_code)
async def delete_movie_process(message: Message, state: FSMContext):
    """Kinoni o'chirish"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_menu_keyboard())
        return
    
    code = message.text.strip()
    movie = db.get_movie(code)
    
    if not movie:
        await message.answer(f"❌ <code>{code}</code> kodli kino topilmadi")
        return
    
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_delete_{code}"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_delete"),
        ]
    ])
    
    await state.clear()
    await message.answer(
        f"⚠️ <b>Rostdan ham o'chirasizmi?</b>\n\n"
        f"📛 Nom: {movie['name']}\n"
        f"🔢 Kod: {code}",
        reply_markup=confirm_kb
    )

@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete(callback: CallbackQuery):
    """O'chirishni tasdiqlash"""
    code = callback.data.replace("confirm_delete_", "")
    success = db.delete_movie(code)
    
    if success:
        await callback.message.edit_text(f"✅ <code>{code}</code> kodli kino o'chirildi!")
    else:
        await callback.message.edit_text("❌ Xatolik yuz berdi")
    
    await callback.message.answer("Admin menyusi:", reply_markup=admin_menu_keyboard())

@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    """O'chirishni bekor qilish"""
    await callback.message.edit_text("❌ Bekor qilindi")
    await callback.message.answer("Admin menyusi:", reply_markup=admin_menu_keyboard())

# ─── BROADCAST ───

@router.message(F.text == "📢 Broadcast")
async def broadcast_start(message: Message, state: FSMContext):
    """Broadcast boshlash"""
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_broadcast)
    await message.answer(
        "📢 <b>BROADCAST XABAR</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:\n"
        "<i>Bekor qilish: /cancel</i>"
    )

@router.message(AdminStates.waiting_broadcast)
async def broadcast_process(message: Message, state: FSMContext):
    """Broadcast yuborish"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_menu_keyboard())
        return
    
    await state.clear()
    users = db.get_all_users()
    
    success_count = 0
    fail_count = 0
    
    status_msg = await message.answer(f"📢 Yuborilmoqda... (0/{len(users)})")
    
    for i, user in enumerate(users):
        try:
            await bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 <b>YANGILIK</b>\n\n{message.text}"
            )
            success_count += 1
            await asyncio.sleep(0.05)  # Flood limitdan himoya
        except Exception:
            fail_count += 1
        
        # Har 50 ta foydalanuvchida yangilash
        if (i + 1) % 50 == 0:
            try:
                await status_msg.edit_text(f"📢 Yuborilmoqda... ({i+1}/{len(users)})")
            except:
                pass
    
    await status_msg.edit_text(
        f"✅ <b>Broadcast yakunlandi!</b>\n\n"
        f"✅ Muvaffaqiyat: {success_count}\n"
        f"❌ Xatolik: {fail_count}\n"
        f"📊 Jami: {len(users)}"
    )
    logger.info(f"Broadcast yuborildi: {success_count} success, {fail_count} fail")

# ─── STATUS BERISH ───

@router.message(F.text == "💎 Status berish")
async def give_status_start(message: Message, state: FSMContext):
    """Status berish boshlash"""
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminStates.waiting_give_user_id)
    await message.answer(
        "💎 <b>STATUS BERISH</b>\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "<i>Bekor qilish: /cancel</i>"
    )

@router.message(AdminStates.waiting_give_user_id)
async def give_status_user_id(message: Message, state: FSMContext):
    """Foydalanuvchi ID olish"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_menu_keyboard())
        return
    
    try:
        user_id = int(message.text.strip())
        user = db.get_user(user_id)
        
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi")
            return
        
        await state.update_data(target_user_id=user_id)
        await state.set_state(AdminStates.waiting_give_status)
        
        await message.answer(
            f"👤 Foydalanuvchi: <b>{user['full_name']}</b>\n"
            f"Hozirgi status: {get_status_emoji(user['status'])} {get_status_text(user['status'])}\n\n"
            f"Yangi statusni tanlang:",
            reply_markup=status_keyboard()
        )
    except ValueError:
        await message.answer("❌ Noto'g'ri ID format. Faqat raqam kiriting.")

@router.callback_query(F.data.startswith("set_status_"))
async def set_status(callback: CallbackQuery, state: FSMContext):
    """Status o'rnatish"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    
    new_status = callback.data.replace("set_status_", "")
    data = await state.get_data()
    target_id = data.get('target_user_id')
    
    if not target_id:
        await callback.answer("❌ Xatolik", show_alert=True)
        return
    
    db.update_user_status(target_id, new_status)
    await state.clear()
    
    status_emoji = get_status_emoji(new_status)
    status_text = get_status_text(new_status)
    
    await callback.message.edit_text(
        f"✅ Status berildi!\n\n"
        f"👤 ID: {target_id}\n"
        f"🆕 Yangi status: {status_emoji} {status_text}"
    )
    
    # Foydalanuvchiga xabar
    try:
        await bot.send_message(
            target_id,
            f"🎉 <b>Tabriklaymiz!</b>\n\n"
            f"Sizga {status_emoji} <b>{status_text}</b> berildi!\n\n"
            f"Yangi imkoniyatlardan foydalaning! 🚀"
        )
    except:
        pass
    
    await callback.message.answer("Admin menyusi:", reply_markup=admin_menu_keyboard())
    logger.info(f"Status berildi: {target_id} → {new_status} (admin: {callback.from_user.id})")

# ─── BAN/UNBAN ───

@router.message(F.text == "🔒 Ban/Unban")
async def ban_menu(message: Message, state: FSMContext):
    """Ban menyusi"""
    if not is_admin(message.from_user.id):
        return
    
    ban_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔒 Bloklash", callback_data="action_ban"),
            InlineKeyboardButton(text="🔓 Blokdan chiqarish", callback_data="action_unban"),
        ]
    ])
    
    await message.answer("🔒 <b>BAN BOSHQARUVI</b>\n\nAmalni tanlang:", reply_markup=ban_kb)

@router.callback_query(F.data.startswith("action_ban") | F.data.startswith("action_unban"))
async def ban_action(callback: CallbackQuery, state: FSMContext):
    """Ban amalini boshlash"""
    action = "ban" if "ban" in callback.data and "unban" not in callback.data else "unban"
    await state.update_data(ban_action=action)
    await state.set_state(AdminStates.waiting_ban_id)
    
    action_text = "bloklash" if action == "ban" else "blokdan chiqarish"
    await callback.message.edit_text(
        f"Kimni {action_text} kerak?\n"
        f"Foydalanuvchi ID sini kiriting:"
    )

@router.message(AdminStates.waiting_ban_id)
async def ban_process(message: Message, state: FSMContext):
    """Ban/unban bajarish"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_menu_keyboard())
        return
    
    data = await state.get_data()
    action = data.get('ban_action', 'ban')
    
    try:
        user_id = int(message.text.strip())
        
        if action == 'ban':
            db.ban_user(user_id)
            await message.answer(f"🔒 {user_id} bloklandi")
            try:
                await bot.send_message(user_id, "🚫 Siz botdan bloklanding!")
            except:
                pass
        else:
            db.unban_user(user_id)
            await message.answer(f"🔓 {user_id} blokdan chiqarildi")
            try:
                await bot.send_message(user_id, "✅ Sizning blokingiz olib tashlandi!")
            except:
                pass
        
        await state.clear()
        await message.answer("Admin menyusi:", reply_markup=admin_menu_keyboard())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID format")

# ─── KANAL SOZLASH ───

@router.message(F.text == "📺 Kanal sozlash")
async def channel_settings(message: Message, state: FSMContext):
    """Kanal sozlamalari"""
    if not is_admin(message.from_user.id):
        return
    
    channels = db.get_channels()
    
    text = "📺 <b>KANAL SOZLAMALARI</b>\n\n"
    if channels:
        text += "Hozirgi kanallar:\n"
        for ch in channels:
            text += f"• {ch['channel_name']} ({ch['channel_username']})\n"
    else:
        text += "Hozircha hech qanday kanal qo'shilmagan\n"
        text += "Config faylidagi kanallar ishlatilmoqda\n"
    
    channel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel"),
            InlineKeyboardButton(text="❌ Kanal o'chirish", callback_data="remove_channel"),
        ]
    ])
    
    await message.answer(text, reply_markup=channel_kb)

@router.callback_query(F.data == "add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    """Kanal qo'shish"""
    await state.set_state(AdminStates.waiting_channel_add)
    await callback.message.edit_text(
        "📺 Kanal ma'lumotlarini kiriting (quyidagi formatda):\n\n"
        "<code>-100123456789 @kanal_username Kanal nomi</code>\n\n"
        "Masalan: <code>-1001234567890 @mykino_uz Mening Kino Kanalim</code>"
    )

@router.message(AdminStates.waiting_channel_add)
async def add_channel_process(message: Message, state: FSMContext):
    """Kanalni qo'shish"""
    try:
        parts = message.text.strip().split(maxsplit=2)
        channel_id = int(parts[0])
        username = parts[1]
        name = parts[2] if len(parts) > 2 else username
        
        success = db.add_channel(channel_id, username, name)
        await state.clear()
        
        if success:
            await message.answer(
                f"✅ Kanal qo'shildi!\n\n"
                f"📺 {name}\n"
                f"🔗 {username}",
                reply_markup=admin_menu_keyboard()
            )
        else:
            await message.answer("❌ Kanal qo'shishda xatolik", reply_markup=admin_menu_keyboard())
    except Exception as e:
        await message.answer(f"❌ Noto'g'ri format: {e}\n\nTo'g'ri format: -100ID @username Kanal nomi")

@router.message(F.text == "🔙 Asosiy menyu")
async def back_to_main(message: Message, state: FSMContext):
    """Asosiy menyuga qaytish"""
    await state.clear()
    db_user = db.get_user(message.from_user.id)
    status = db_user.get('status', 'user') if db_user else 'user'
    await message.answer(
        "🏠 <b>Asosiy menyu</b>",
        reply_markup=main_menu_keyboard(status)
    )


# ═══════════════════════════════════════════════════════
#                  📝 BUYRUQLAR
# ═══════════════════════════════════════════════════════

@router.message(Command("popular"))
async def cmd_popular(message: Message):
    """Mashhur kinolar buyrug'i"""
    movies = db.get_popular_movies(10)
    if not movies:
        await message.answer("📭 Hozircha kinolar mavjud emas")
        return
    
    text = "🏆 <b>ENG MASHHUR KINOLAR</b>\n\n"
    for i, movie in enumerate(movies, 1):
        text += f"{i}. <b>{movie['name']}</b> — <code>{movie['movie_code']}</code> (👁️ {movie['views']})\n"
    
    await message.answer(text)

@router.message(Command("new"))
async def cmd_new(message: Message):
    """Yangi kinolar buyrug'i"""
    movies = db.get_recent_movies(10)
    if not movies:
        await message.answer("📭 Hozircha kinolar mavjud emas")
        return
    
    text = "🆕 <b>YANGI KINOLAR</b>\n\n"
    for i, movie in enumerate(movies, 1):
        text += f"{i}. <b>{movie['name']}</b> — <code>{movie['movie_code']}</code>\n"
    
    await message.answer(text)

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Status ko'rish"""
    db_user = db.get_user(message.from_user.id)
    if not db_user:
        await message.answer("❌ Avval /start ni bosing")
        return
    
    status = db_user.get('status', 'user')
    await message.answer(
        f"{get_status_emoji(status)} <b>Sizning statusingiz:</b> {get_status_text(status)}\n"
        f"💠 <b>Ballar:</b> {db_user.get('points', 0)}"
    )

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Holатni bekor qilish"""
    await state.clear()
    db_user = db.get_user(message.from_user.id)
    status = db_user.get('status', 'user') if db_user else 'user'
    await message.answer("❌ Bekor qilindi", reply_markup=main_menu_keyboard(status))

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Yordam"""
    help_text = (
        "📚 <b>YORDAM</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎬 <b>Kino olish:</b>\n"
        "Shunchaki kino kodini yozing!\n"
        "Misol: <code>101</code>, <code>202</code>\n\n"
        "📋 <b>Buyruqlar:</b>\n"
        "/start — Botni boshlash\n"
        "/popular — Mashhur kinolar\n"
        "/new — Yangi kinolar\n"
        "/status — Statusingiz\n"
        "/help — Yordam\n\n"
        "💎 <b>Statuslar:</b>\n"
        "👤 Oddiy — Barcha bepul kinolar\n"
        "💎 VIP — VIP + bepul kinolar\n"
        "👑 Premium — Hamma kinolar + tezkor\n\n"
        "❓ Savollar uchun admin bilan bog'laning"
    )
    await message.answer(help_text)


# ═══════════════════════════════════════════════════════
#            📨 ASOSIY XABAR HANDLERI (KOD QIDIRISH)
# ═══════════════════════════════════════════════════════

@router.message(F.text)
async def handle_message(message: Message, state: FSMContext):
    """
    Barcha matnli xabarlarni ushlash
    Agar kino kodi bo'lsa — kinoni yuborish
    """
    # State da bo'lsa, o'tkazib yuborish
    current_state = await state.get_state()
    if current_state:
        return
    
    text = message.text.strip()
    
    # Admin menyu tugmalarini tekshirish
    if is_admin(message.from_user.id):
        if text in ["➕ Kino qo'shish", "❌ Kino o'chirish", "📊 Statistika",
                    "👥 Foydalanuvchilar", "📢 Broadcast", "💎 Status berish",
                    "🔒 Ban/Unban", "📺 Kanal sozlash", "🔙 Asosiy menyu"]:
            return  # Bu tugmalar o'z handlerlariga ega
    
    # Kino kodi yoki matn qidirish
    if text.isdigit() or (len(text) <= 10 and text.replace('-', '').isdigit()):
        # Kino kodi
        await send_movie(message, text)
    elif len(text) >= 2:
        # Matn qidirish
        movies = db.search_movies(text)
        if movies:
            result = f"🔍 <b>'{text}'</b> bo'yicha:\n\n"
            for movie in movies[:5]:
                result += f"• <b>{movie['name']}</b> — <code>{movie['movie_code']}</code>\n"
            result += "\n💡 Kino kodini yozing!"
            await message.answer(result)
        else:
            await message.answer(
                f"❓ <code>{text}</code> — tushunmadim\n\n"
                "🎬 Kino kodini yozing (masalan: <code>101</code>)\n"
                "💡 Yordam uchun /help"
            )


# ═══════════════════════════════════════════════════════
#                  🚀 BOTNI ISHGA TUSHIRISH
# ═══════════════════════════════════════════════════════

async def set_bot_commands():
    """Bot komandalari ro'yxatini o'rnatish"""
    commands = [
        BotCommand(command="start", description="🤖 Botni boshlash"),
        BotCommand(command="help", description="📚 Yordam"),
        BotCommand(command="popular", description="🏆 Mashhur kinolar"),
        BotCommand(command="new", description="🆕 Yangi kinolar"),
        BotCommand(command="status", description="👤 Mening statusim"),
        BotCommand(command="cancel", description="❌ Bekor qilish"),
    ]
    await bot.set_my_commands(commands)
    logger.info("✅ Bot komandalari o'rnatildi")

async def on_startup():
    """Bot ishga tushganda"""
    logger.info("🚀 KODLI KINO BOT ishga tushmoqda...")
    await set_bot_commands()
    
    # Admin ga xabar yuborish
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                "✅ <b>Bot muvaffaqiyatli ishga tushdi!</b>\n\n"
                f"🕐 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🎬 Kinolar: {db.get_movies_count()}\n"
                f"👥 Foydalanuvchilar: {db.get_users_count()['total']}"
            )
        except Exception as e:
            logger.warning(f"Admin ga xabar yuborishda xatolik: {e}")
    
    logger.info("✅ Bot tayyor!")

async def on_shutdown():
    """Bot to'xtaganda"""
    logger.info("⛔ Bot to'xtatilmoqda...")
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "⛔ <b>Bot to'xtatildi!</b>")
        except:
            pass

async def main():
    """Asosiy funksiya"""
    # Handlerlarni ro'yxatdan o'tkazish
    dp.include_router(router)
    
    # Startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Polling boshlash
    logger.info("🤖 Polling boshlandi...")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Kritik xatolik: {e}", exc_info=True)
