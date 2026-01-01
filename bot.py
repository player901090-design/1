#!/usr/bin/env python3
import asyncio
import logging
import re
import sqlite3
import os
import json
from threading import Lock
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiohttp import web, ClientSession, ClientTimeout
from bs4 import BeautifulSoup

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = os.getenv('BOT_TOKEN', '8374381970:AAG1VU-oEibrut-7kjm0_p6fXZyKinqG2cU')
ADMIN_ID = int(os.getenv('ADMIN_ID', '8524070856'))
WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://one-qh1w.onrender.com')
WEB_PORT = int(os.getenv('PORT', 10000))
# ==================================

logging.basicConfig(level=logging.INFO)

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
                    user_id INTEGER NOT NULL,
                    nft_name TEXT NOT NULL,
                    nft_link TEXT NOT NULL,
                    icon_url TEXT,
                    PRIMARY KEY (user_id, nft_name)
                )
            ''')
            conn.commit()
            conn.close()

    def add_nft(self, user_id, nft_name, nft_link, icon_url=None):
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO inventory (user_id, nft_name, nft_link, icon_url)
                VALUES (?, ?, ?, ?)
            ''', (user_id, nft_name, nft_link, icon_url))
            conn.commit()
            conn.close()

    def get_user_inventory(self, user_id):
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT nft_name, nft_link, icon_url FROM inventory WHERE user_id = ?
            ''', (user_id,))
            rows = cursor.fetchall()
            conn.close()
            return [{"id": row[0], "link": row[1], "icon": row[2]} for row in rows]

db = Database()

# ========== ПАРСИНГ OPEN GRAPH ==========
async def fetch_nft_preview(url: str) -> str:
    """Получаем og:image из страницы NFT"""
    default_icon = "https://cdn-icons-png.flaticon.com/512/5968/5968804.png"
    timeout = ClientTimeout(total=5)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        async with ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return default_icon
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                
                # Ищем og:image
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    return og_image['content']
                
                # Ищем twitter:image
                twitter_image = soup.find('meta', {'name': 'twitter:image'})
                if twitter_image and twitter_image.get('content'):
                    return twitter_image['content']
                
                # Ищем favicon
                favicon = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
                if favicon and favicon.get('href'):
                    icon_url = favicon['href']
                    if not icon_url.startswith('http'):
                        # Преобразуем относительную ссылку в абсолютную
                        from urllib.parse import urljoin
                        icon_url = urljoin(url, icon_url)
                    return icon_url
                
                return default_icon
    except Exception as e:
        logging.error(f"Failed to fetch preview for {url}: {e}")
        return default_icon

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

def parse_nft_link(link: str):
    pattern = r't\.me/nft/([a-zA-Z0-9_-]+-?\d*)'
    match = re.search(pattern, link)
    if match:
        nft_name = match.group(1)
        full_link = f"https://t.me/nft/{nft_name}"
        return nft_name, full_link
    return None, None

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    args = message.text.split()[1] if len(message.text.split()) > 1 else ''
    if args == "inventory":
        web_app_url_with_params = f"{WEB_APP_URL}?user_id={message.from_user.id}"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🎒 Inventory", web_app=types.WebAppInfo(url=web_app_url_with_params))]
        ])
        await message.answer("<b>✨ You've already claimed this NFT. You can check it in your inventory.</b>", reply_markup=keyboard)
        return

    welcome_text = """<b>💎 Welcome to ForGifts!</b> This bot allows you to anonymously and securely transfer NFTs to another user.

<blockquote expandable><b>💼 What does the bot do?</b>
📤 Helps transfer NFTs directly
🔐 Uses escrow to protect both parties
🥷 Anonymity when transferring NFTs
🤖 Prevents NFT transfers from being tracked by parser bots</blockquote>

<b>📤 To send an NFT, use the command</b> <code>/create t.me/nft/PlushPepe-1</code>"""
    await message.answer(welcome_text)

@dp.message(Command('create'))
async def cmd_create(message: types.Message):
    args = message.text.split()[1] if len(message.text.split()) > 1 else ''
    if not args:
        await message.answer("<b>❌ Usage:</b> <code>/create t.me/nft/PlushPepe-1</code>")
        return
    
    nft_name, full_link = parse_nft_link(args)
    if not nft_name:
        await message.answer("<b>❌ Invalid NFT link format.</b> Use: <code>t.me/nft/Name-Number</code>")
        return
    
    user_id = message.from_user.id
    # Парсим иконку
    icon_url = await fetch_nft_preview(full_link)
    db.add_nft(user_id, nft_name, full_link, icon_url)
    
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
        await message.answer("<b>🛠 Admin panel active.</b>\n/stats")
    else:
        await message.answer("<b>🚫 Access denied.</b>")

# ========== ВЕБ-СЕРВЕР ==========
async def handle_index(request):
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    return web.Response(text=html, content_type='text/html')

async def handle_style(request):
    with open('style.css', 'r', encoding='utf-8') as f:
        css = f.read()
    return web.Response(text=css, content_type='text/css')

async def handle_script(request):
    with open('script.js', 'r', encoding='utf-8') as f:
        js = f.read()
    return web.Response(text=js, content_type='application/javascript')

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

async def start_web_app():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/style.css', handle_style)
    app.router.add_get('/script.js', handle_script)
    app.router.add_get('/api/inventory', handle_api_inventory)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEB_PORT)
    await site.start()
    logging.info(f"Web app started on port {WEB_PORT}")
    return runner

# ========== ЗАПУСК ==========
async def main():
    await set_commands(bot)
    web_runner = await start_web_app()
    logging.info(f"Bot starting. Web App URL: {WEB_APP_URL}")
    await dp.start_polling(bot)
    await web_runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
